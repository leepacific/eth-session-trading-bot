#!/usr/bin/env python3
"""
Railway에서 프록시 설정 테스트
"""

import os
import requests

def test_proxy_settings():
    """프록시 설정 확인"""
    print("🔍 Railway 프록시 설정 확인")
    print("=" * 60)
    
    # 환경변수 확인
    proxy_url = os.getenv('BINANCE_PROXY_URL')
    use_proxy = os.getenv('USE_CLOUDFLARE_PROXY')
    
    print(f"BINANCE_PROXY_URL: {proxy_url}")
    print(f"USE_CLOUDFLARE_PROXY: {use_proxy}")
    
    if not proxy_url:
        print("❌ BINANCE_PROXY_URL이 설정되지 않았습니다")
        return False
    
    if use_proxy != 'true':
        print("❌ USE_CLOUDFLARE_PROXY가 'true'로 설정되지 않았습니다")
        return False
    
    # 프록시 연결 테스트
    print(f"\n🧪 프록시 연결 테스트: {proxy_url}")
    
    try:
        # 바이낸스 서버 시간 테스트
        response = requests.get(f"{proxy_url}/api/v3/time", timeout=15)
        
        if response.status_code == 200:
            server_time = response.json()
            print(f"✅ 프록시 연결 성공: {server_time}")
            
            # 응답 헤더 확인
            print(f"\n📋 응답 헤더:")
            for key, value in response.headers.items():
                if 'cloudflare' in key.lower() or 'cf-' in key.lower():
                    print(f"   {key}: {value}")
            
            return True
        else:
            print(f"❌ 프록시 연결 실패: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 프록시 테스트 오류: {e}")
        return False

def test_direct_vs_proxy():
    """직접 연결 vs 프록시 연결 비교"""
    print(f"\n🔄 직접 연결 vs 프록시 연결 비교")
    print("=" * 60)
    
    # 1. 직접 연결
    try:
        print("1. 직접 바이낸스 연결...")
        response = requests.get("https://api.binance.com/api/v3/time", timeout=10)
        if response.status_code == 200:
            print(f"   ✅ 직접 연결 성공")
        else:
            print(f"   ❌ 직접 연결 실패: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 직접 연결 오류: {e}")
    
    # 2. 프록시 연결
    proxy_url = os.getenv('BINANCE_PROXY_URL')
    if proxy_url:
        try:
            print("2. 프록시를 통한 바이낸스 연결...")
            response = requests.get(f"{proxy_url}/api/v3/time", timeout=10)
            if response.status_code == 200:
                print(f"   ✅ 프록시 연결 성공")
            else:
                print(f"   ❌ 프록시 연결 실패: {response.status_code}")
        except Exception as e:
            print(f"   ❌ 프록시 연결 오류: {e}")
    else:
        print("2. 프록시 URL이 설정되지 않았습니다")

def main():
    """메인 실행"""
    print("🚂 Railway 프록시 설정 디버깅")
    print("=" * 80)
    
    # 프록시 설정 확인
    proxy_ok = test_proxy_settings()
    
    # 연결 비교 테스트
    test_direct_vs_proxy()
    
    # 결과 요약
    print(f"\n📊 결과 요약")
    print("=" * 60)
    
    if proxy_ok:
        print("✅ 프록시 설정이 올바르게 구성되었습니다")
        print("💡 Railway 봇 코드에서 프록시를 사용하도록 설정되어야 합니다")
    else:
        print("❌ 프록시 설정에 문제가 있습니다")
        print("💡 환경변수를 다시 확인하고 Railway를 재배포하세요")

if __name__ == "__main__":
    main()