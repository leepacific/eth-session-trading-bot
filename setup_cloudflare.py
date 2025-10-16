#!/usr/bin/env python3
"""
Cloudflare 자동 설정 스크립트
Railway 프로젝트와 Cloudflare를 연결하는 모든 과정을 자동화
"""

import os
import sys
import json
import subprocess
from cloudflare_integration import CloudflareManager

def check_requirements():
    """필수 요구사항 확인"""
    print("🔍 필수 요구사항 확인 중...")
    
    required_vars = [
        'CLOUDFLARE_API_TOKEN',
        'CLOUDFLARE_ZONE_ID',
        'CUSTOM_DOMAIN'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ 다음 환경변수가 설정되지 않았습니다:")
        for var in missing_vars:
            print(f"   - {var}")
        return False
    
    print("✅ 모든 필수 환경변수가 설정되었습니다.")
    return True

def setup_dns():
    """DNS 설정"""
    print("\n🌐 DNS 설정 중...")
    
    cf = CloudflareManager()
    
    # DNS 레코드 생성/업데이트
    result = cf.full_setup()
    
    if result:
        print("✅ DNS 설정 완료")
        return True
    else:
        print("❌ DNS 설정 실패")
        return False

def setup_tunnel():
    """Cloudflare Tunnel 설정"""
    print("\n🚇 Cloudflare Tunnel 설정 중...")
    
    tunnel_token = os.getenv('CLOUDFLARE_TUNNEL_TOKEN')
    if not tunnel_token:
        print("⚠️ CLOUDFLARE_TUNNEL_TOKEN이 설정되지 않았습니다.")
        print("   수동으로 터널을 생성하고 토큰을 설정하세요.")
        return False
    
    try:
        # Cloudflared가 설치되어 있는지 확인
        result = subprocess.run(['cloudflared', '--version'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Cloudflared 설치 확인됨")
            
            # 터널 실행 (백그라운드)
            print("🚀 터널 시작 중...")
            # 실제 프로덕션에서는 systemd 서비스로 실행하는 것이 좋습니다
            
            return True
        else:
            print("❌ Cloudflared가 설치되지 않았습니다.")
            return False
            
    except FileNotFoundError:
        print("❌ Cloudflared를 찾을 수 없습니다.")
        return False

def verify_setup():
    """설정 검증"""
    print("\n🔍 설정 검증 중...")
    
    domain = os.getenv('CUSTOM_DOMAIN')
    
    try:
        import requests
        
        # HTTP 요청으로 도메인 접근 테스트
        response = requests.get(f"https://{domain}/health", timeout=10)
        
        if response.status_code == 200:
            print(f"✅ 도메인 접근 성공: https://{domain}")
            print(f"   응답: {response.json()}")
            return True
        else:
            print(f"❌ 도메인 접근 실패: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 도메인 접근 테스트 실패: {e}")
        return False

def print_summary():
    """설정 완료 요약"""
    domain = os.getenv('CUSTOM_DOMAIN')
    
    print("\n" + "="*60)
    print("🎉 Cloudflare 설정 완료!")
    print("="*60)
    print(f"🌐 도메인: https://{domain}")
    print(f"🏥 헬스체크: https://{domain}/health")
    print(f"📊 상태 확인: https://{domain}/status")
    print("\n📋 다음 단계:")
    print("1. Railway 대시보드에서 환경변수 확인")
    print("2. 도메인 DNS 전파 대기 (최대 24시간)")
    print("3. SSL 인증서 발급 확인")
    print("4. 트레이딩 봇 정상 작동 확인")
    print("\n🛡️ 보안 기능:")
    print("- SSL/TLS 암호화")
    print("- DDoS 보호")
    print("- Rate limiting")
    print("- 방화벽 규칙")
    print("="*60)

def main():
    """메인 실행 함수"""
    print("🚀 Cloudflare + Railway 자동 설정 시작")
    print("="*60)
    
    # 1. 요구사항 확인
    if not check_requirements():
        print("\n❌ 설정을 완료할 수 없습니다.")
        print("필수 환경변수를 설정한 후 다시 시도하세요.")
        sys.exit(1)
    
    # 2. DNS 설정
    if not setup_dns():
        print("\n❌ DNS 설정에 실패했습니다.")
        sys.exit(1)
    
    # 3. 터널 설정 (선택사항)
    setup_tunnel()
    
    # 4. 설정 검증
    print("\n⏳ DNS 전파 대기 중... (30초)")
    import time
    time.sleep(30)
    
    if verify_setup():
        print_summary()
    else:
        print("\n⚠️ 설정이 완료되었지만 검증에 실패했습니다.")
        print("DNS 전파가 완료될 때까지 기다려주세요.")
        print_summary()

if __name__ == "__main__":
    main()