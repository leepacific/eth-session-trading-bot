"""
Cloudflare 통합 모듈
- 고정 IP 관리
- 도메인 연결
- SSL/TLS 처리
"""

import os
import requests
import json
from datetime import datetime
import logging

class CloudflareManager:
    def __init__(self):
        """Cloudflare 관리자 초기화"""
        self.api_token = os.getenv('CLOUDFLARE_API_TOKEN')
        self.zone_id = os.getenv('CLOUDFLARE_ZONE_ID')
        self.domain = os.getenv('CUSTOM_DOMAIN', 'api.eth-trading-bot.com')
        self.tunnel_token = os.getenv('CLOUDFLARE_TUNNEL_TOKEN')
        
        self.base_url = "https://api.cloudflare.com/client/v4"
        self.headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }
        
        print("🌐 Cloudflare 통합 초기화")
        print(f"   도메인: {self.domain}")
        print(f"   터널 토큰: {'설정됨' if self.tunnel_token else '미설정'}")
    
    def get_zone_info(self):
        """Zone 정보 조회"""
        try:
            url = f"{self.base_url}/zones/{self.zone_id}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                return data['result']
            else:
                print(f"❌ Zone 정보 조회 실패: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Zone 정보 조회 오류: {e}")
            return None
    
    def create_dns_record(self, record_type='CNAME', name='api', content=None):
        """DNS 레코드 생성"""
        try:
            if not content:
                # Railway 앱 URL을 기본값으로 사용
                railway_url = os.getenv('RAILWAY_PUBLIC_DOMAIN')
                if not railway_url:
                    print("❌ Railway 도메인이 설정되지 않았습니다.")
                    return None
                content = railway_url
            
            url = f"{self.base_url}/zones/{self.zone_id}/dns_records"
            data = {
                'type': record_type,
                'name': name,
                'content': content,
                'proxied': True,  # Cloudflare 프록시 활성화
                'ttl': 1  # 자동 TTL
            }
            
            response = requests.post(url, headers=self.headers, json=data)
            
            if response.status_code == 200:
                result = response.json()['result']
                print(f"✅ DNS 레코드 생성 성공: {name}.{self.domain}")
                return result
            else:
                print(f"❌ DNS 레코드 생성 실패: {response.status_code}")
                print(response.text)
                return None
                
        except Exception as e:
            print(f"❌ DNS 레코드 생성 오류: {e}")
            return None
    
    def update_dns_record(self, record_id, content):
        """DNS 레코드 업데이트"""
        try:
            url = f"{self.base_url}/zones/{self.zone_id}/dns_records/{record_id}"
            data = {
                'content': content,
                'proxied': True
            }
            
            response = requests.patch(url, headers=self.headers, json=data)
            
            if response.status_code == 200:
                print(f"✅ DNS 레코드 업데이트 성공")
                return response.json()['result']
            else:
                print(f"❌ DNS 레코드 업데이트 실패: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ DNS 레코드 업데이트 오류: {e}")
            return None
    
    def get_dns_records(self):
        """DNS 레코드 목록 조회"""
        try:
            url = f"{self.base_url}/zones/{self.zone_id}/dns_records"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                return response.json()['result']
            else:
                print(f"❌ DNS 레코드 조회 실패: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ DNS 레코드 조회 오류: {e}")
            return []
    
    def setup_ssl_settings(self):
        """SSL/TLS 설정"""
        try:
            # SSL 모드를 Full (strict)로 설정
            url = f"{self.base_url}/zones/{self.zone_id}/settings/ssl"
            data = {'value': 'strict'}
            
            response = requests.patch(url, headers=self.headers, json=data)
            
            if response.status_code == 200:
                print("✅ SSL 설정 완료: Full (strict)")
            
            # Always Use HTTPS 활성화
            url = f"{self.base_url}/zones/{self.zone_id}/settings/always_use_https"
            data = {'value': 'on'}
            
            response = requests.patch(url, headers=self.headers, json=data)
            
            if response.status_code == 200:
                print("✅ Always Use HTTPS 활성화")
                
        except Exception as e:
            print(f"❌ SSL 설정 오류: {e}")
    
    def create_page_rule(self, url_pattern, settings):
        """페이지 규칙 생성"""
        try:
            url = f"{self.base_url}/zones/{self.zone_id}/pagerules"
            data = {
                'targets': [{'target': 'url', 'constraint': {'operator': 'matches', 'value': url_pattern}}],
                'actions': settings,
                'status': 'active'
            }
            
            response = requests.post(url, headers=self.headers, json=data)
            
            if response.status_code == 200:
                print(f"✅ 페이지 규칙 생성: {url_pattern}")
                return response.json()['result']
            else:
                print(f"❌ 페이지 규칙 생성 실패: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ 페이지 규칙 생성 오류: {e}")
            return None
    
    def setup_caching_rules(self):
        """캐싱 규칙 설정"""
        try:
            # 헬스체크 엔드포인트는 캐시 우회
            health_rule = self.create_page_rule(
                f"{self.domain}/health*",
                [{'id': 'cache_level', 'value': 'bypass'}]
            )
            
            # API 엔드포인트는 짧은 캐시
            api_rule = self.create_page_rule(
                f"{self.domain}/api/*",
                [
                    {'id': 'cache_level', 'value': 'cache_everything'},
                    {'id': 'edge_cache_ttl', 'value': 300}  # 5분
                ]
            )
            
            return health_rule and api_rule
            
        except Exception as e:
            print(f"❌ 캐싱 규칙 설정 오류: {e}")
            return False
    
    def get_analytics(self):
        """Cloudflare 분석 데이터 조회"""
        try:
            url = f"{self.base_url}/zones/{self.zone_id}/analytics/dashboard"
            params = {
                'since': -1440,  # 최근 24시간
                'until': 0
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                return response.json()['result']
            else:
                print(f"❌ 분석 데이터 조회 실패: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ 분석 데이터 조회 오류: {e}")
            return None
    
    def setup_firewall_rules(self):
        """방화벽 규칙 설정"""
        try:
            # Rate limiting 규칙
            url = f"{self.base_url}/zones/{self.zone_id}/rate_limits"
            data = {
                'threshold': 100,
                'period': 60,
                'match': {
                    'request': {
                        'url': f"{self.domain}/api/*"
                    }
                },
                'action': {
                    'mode': 'ban',
                    'timeout': 600
                },
                'disabled': False
            }
            
            response = requests.post(url, headers=self.headers, json=data)
            
            if response.status_code == 200:
                print("✅ Rate limiting 규칙 생성")
                return True
            else:
                print(f"❌ Rate limiting 규칙 생성 실패: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 방화벽 규칙 설정 오류: {e}")
            return False
    
    def full_setup(self):
        """전체 Cloudflare 설정"""
        print("🚀 Cloudflare 전체 설정 시작")
        
        # 1. Zone 정보 확인
        zone_info = self.get_zone_info()
        if not zone_info:
            print("❌ Zone 정보를 가져올 수 없습니다.")
            return False
        
        print(f"✅ Zone 확인: {zone_info['name']}")
        
        # 2. DNS 레코드 생성/업데이트
        dns_records = self.get_dns_records()
        api_record = None
        
        for record in dns_records:
            if record['name'] == f"api.{zone_info['name']}":
                api_record = record
                break
        
        if not api_record:
            api_record = self.create_dns_record()
        
        if not api_record:
            print("❌ DNS 레코드 설정 실패")
            return False
        
        # 3. SSL 설정
        self.setup_ssl_settings()
        
        # 4. 캐싱 규칙 설정
        self.setup_caching_rules()
        
        # 5. 방화벽 규칙 설정
        self.setup_firewall_rules()
        
        print("🎉 Cloudflare 설정 완료!")
        print(f"   도메인: https://{self.domain}")
        print(f"   헬스체크: https://{self.domain}/health")
        
        return True

def main():
    """테스트 실행"""
    cf = CloudflareManager()
    
    if cf.api_token and cf.zone_id:
        cf.full_setup()
    else:
        print("❌ Cloudflare API 토큰 또는 Zone ID가 설정되지 않았습니다.")
        print("   환경변수를 확인하세요:")
        print("   - CLOUDFLARE_API_TOKEN")
        print("   - CLOUDFLARE_ZONE_ID")

if __name__ == "__main__":
    main()