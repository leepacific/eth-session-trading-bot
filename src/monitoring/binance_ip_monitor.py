#!/usr/bin/env python3
"""
바이낸스 API IP 모니터링 및 자동 알림 시스템
- Railway IP 변경 감지
- 바이낸스 API 연결 상태 모니터링
- IP 변경 시 알림
"""

import requests
import json
import os
import time
import hmac
import hashlib
from datetime import datetime
from urllib.parse import urlencode

class BinanceIPMonitor:
    def __init__(self):
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.secret_key = os.getenv('BINANCE_SECRET_KEY')
        self.last_known_ip = None
        self.ip_history = []
        
        # 바이낸스 API 설정
        self.base_url = "https://api.binance.com"
        if not (self.api_key and self.secret_key):
            print("⚠️ 바이낸스 API 키가 설정되지 않았습니다")
    
    def get_current_ip(self):
        """현재 외부 IP 확인"""
        ip_services = [
            "https://api.ipify.org?format=json",
            "https://httpbin.org/ip",
            "https://ipapi.co/json/"
        ]
        
        for service in ip_services:
            try:
                response = requests.get(service, timeout=5)
                data = response.json()
                
                # IP 추출
                ip = data.get('ip') or data.get('origin')
                if ip:
                    return ip.strip()
                    
            except Exception as e:
                continue
        
        return None
    
    def get_ip_location(self, ip):
        """IP 위치 정보 확인"""
        try:
            response = requests.get(f"https://ipapi.co/{ip}/json/", timeout=5)
            data = response.json()
            
            return {
                'country': data.get('country_name', 'Unknown'),
                'region': data.get('region', 'Unknown'),
                'city': data.get('city', 'Unknown'),
                'org': data.get('org', 'Unknown'),
                'timezone': data.get('timezone', 'Unknown')
            }
        except:
            return {'country': 'Unknown', 'region': 'Unknown', 'city': 'Unknown', 'org': 'Unknown', 'timezone': 'Unknown'}
    
    def _generate_signature(self, params):
        """API 서명 생성"""
        query_string = urlencode(params)
        return hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def test_binance_connection(self):
        """바이낸스 API 연결 테스트"""
        if not (self.api_key and self.secret_key):
            return {'status': 'no_client', 'error': 'API 키가 설정되지 않음'}
        
        try:
            # 1. 서버 시간 테스트 (인증 불필요)
            response = requests.get(f"{self.base_url}/api/v3/time", timeout=10)
            
            if response.status_code != 200:
                return {
                    'status': 'server_time_failed',
                    'error': f'서버 시간 조회 실패: {response.status_code}'
                }
            
            server_time = response.json()
            
            # 2. 계정 정보 테스트 (인증 필요 - IP 제한 확인)
            timestamp = int(time.time() * 1000)
            params = {'timestamp': timestamp}
            signature = self._generate_signature(params)
            params['signature'] = signature
            
            headers = {'X-MBX-APIKEY': self.api_key}
            
            response = requests.get(
                f"{self.base_url}/api/v3/account",
                params=params,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                account_info = response.json()
                return {
                    'status': 'success',
                    'server_time': server_time,
                    'account_status': account_info.get('accountType', 'Unknown'),
                    'can_trade': account_info.get('canTrade', False),
                    'permissions': account_info.get('permissions', [])
                }
            else:
                # API 오류 처리
                try:
                    error_data = response.json()
                    error_code = error_data.get('code', response.status_code)
                    error_msg = error_data.get('msg', 'Unknown error')
                except:
                    error_code = response.status_code
                    error_msg = response.text
                
                # IP 제한 관련 에러 코드들
                ip_restriction_codes = [-2015, -1021, -1022, 403]
                
                return {
                    'status': 'api_error',
                    'error_code': error_code,
                    'error_message': error_msg,
                    'is_ip_restriction': error_code in ip_restriction_codes
                }
            
        except Exception as e:
            return {
                'status': 'connection_error',
                'error': str(e)
            }
    
    def check_ip_change(self):
        """IP 변경 확인"""
        current_ip = self.get_current_ip()
        
        if not current_ip:
            return {'status': 'ip_check_failed'}
        
        # IP 히스토리 업데이트
        timestamp = datetime.now()
        ip_info = {
            'ip': current_ip,
            'timestamp': timestamp.isoformat(),
            'location': self.get_ip_location(current_ip)
        }
        
        # IP 변경 감지
        ip_changed = self.last_known_ip and self.last_known_ip != current_ip
        
        if ip_changed:
            print(f"🚨 IP 변경 감지!")
            print(f"   이전 IP: {self.last_known_ip}")
            print(f"   현재 IP: {current_ip}")
        
        self.last_known_ip = current_ip
        self.ip_history.append(ip_info)
        
        # 히스토리 크기 제한 (최근 100개)
        if len(self.ip_history) > 100:
            self.ip_history = self.ip_history[-100:]
        
        return {
            'status': 'success',
            'current_ip': current_ip,
            'ip_changed': ip_changed,
            'location': ip_info['location']
        }
    
    def generate_ip_report(self):
        """IP 및 연결 상태 보고서 생성"""
        print("🔍 바이낸스 IP 모니터링 보고서")
        print("=" * 80)
        print(f"실행 시간: {datetime.now()}")
        
        # 1. 현재 IP 확인
        ip_result = self.check_ip_change()
        
        if ip_result['status'] == 'success':
            current_ip = ip_result['current_ip']
            location = ip_result['location']
            
            print(f"\n🌐 현재 Railway IP 정보:")
            print(f"   IP 주소: {current_ip}")
            print(f"   위치: {location['city']}, {location['region']}, {location['country']}")
            print(f"   ISP: {location['org']}")
            print(f"   시간대: {location['timezone']}")
            
            if ip_result['ip_changed']:
                print(f"   🚨 IP가 변경되었습니다!")
            else:
                print(f"   ✅ IP가 안정적입니다")
        
        # 2. 바이낸스 연결 테스트
        print(f"\n🔗 바이낸스 API 연결 테스트:")
        binance_result = self.test_binance_connection()
        
        if binance_result['status'] == 'success':
            print(f"   ✅ 연결 성공")
            print(f"   계정 타입: {binance_result['account_status']}")
            print(f"   거래 가능: {binance_result['can_trade']}")
            print(f"   권한: {', '.join(binance_result['permissions'])}")
            
        elif binance_result['status'] == 'api_error':
            print(f"   ❌ API 오류")
            print(f"   오류 코드: {binance_result['error_code']}")
            print(f"   오류 메시지: {binance_result['error_message']}")
            
            if binance_result['is_ip_restriction']:
                print(f"   🚨 IP 제한 관련 오류입니다!")
                print(f"   바이낸스 API 관리에서 현재 IP를 허용 목록에 추가하세요: {current_ip}")
            
        elif binance_result['status'] == 'connection_error':
            print(f"   ❌ 연결 오류: {binance_result['error']}")
            
        elif binance_result['status'] == 'no_client':
            print(f"   ⚠️ {binance_result['error']}")
        
        # 3. IP 히스토리 (최근 5개)
        if len(self.ip_history) > 1:
            print(f"\n📊 최근 IP 히스토리:")
            for i, record in enumerate(self.ip_history[-5:], 1):
                timestamp = datetime.fromisoformat(record['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                print(f"   {i}. {record['ip']} ({timestamp})")
        
        # 4. 권장사항
        print(f"\n💡 권장사항:")
        
        if ip_result['status'] == 'success':
            current_ip = ip_result['current_ip']
            print(f"1. 바이낸스 API 관리에서 다음 IP를 허용 목록에 추가:")
            print(f"   {current_ip}")
            
        print(f"2. Railway IP는 변경될 수 있으므로 정기적으로 모니터링")
        print(f"3. IP 변경 시 바이낸스 허용 목록 업데이트 필요")
        print(f"4. 중요한 거래 전에는 반드시 연결 테스트 실행")
        
        # 결과 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = f"binance_ip_monitor_{timestamp}.json"
        
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'ip_result': ip_result,
            'binance_result': binance_result,
            'ip_history': self.ip_history[-10:],  # 최근 10개만 저장
            'recommendations': {
                'current_ip_to_whitelist': ip_result.get('current_ip'),
                'monitor_frequency': 'hourly',
                'update_binance_on_change': True
            }
        }
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 상세 보고서 저장: {result_file}")
        
        return report_data

def main():
    """메인 실행"""
    monitor = BinanceIPMonitor()
    monitor.generate_ip_report()

if __name__ == "__main__":
    main()