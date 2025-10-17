#!/usr/bin/env python3
"""
바이낸스 연결 디버깅 스크립트
- 상세한 오류 정보 확인
- 네트워크 연결 테스트
- API 키 검증
"""

import requests
import json
import os
import time
import hmac
import hashlib
from datetime import datetime
from urllib.parse import urlencode

def test_basic_connectivity():
    """기본 네트워크 연결 테스트"""
    print("🌐 기본 네트워크 연결 테스트")
    print("=" * 50)
    
    test_urls = [
        "https://api.binance.com/api/v3/ping",
        "https://api.binance.com/api/v3/time",
        "https://httpbin.org/ip",
        "https://google.com"
    ]
    
    results = {}
    
    for url in test_urls:
        try:
            print(f"테스트 중: {url}")
            response = requests.get(url, timeout=10)
            
            results[url] = {
                'status_code': response.status_code,
                'success': response.status_code == 200,
                'response_time': response.elapsed.total_seconds(),
                'content_length': len(response.content)
            }
            
            status = "✅" if response.status_code == 200 else "❌"
            print(f"   {status} {response.status_code} ({response.elapsed.total_seconds():.3f}s)")
            
            # 특별한 응답 처리
            if 'binance.com/api/v3/time' in url and response.status_code == 200:
                server_time = response.json()
                print(f"      서버 시간: {server_time}")
            elif 'httpbin.org/ip' in url and response.status_code == 200:
                ip_info = response.json()
                print(f"      현재 IP: {ip_info.get('origin', 'Unknown')}")
                
        except Exception as e:
            results[url] = {'error': str(e), 'success': False}
            print(f"   ❌ 오류: {e}")
    
    return results

def test_api_key_format():
    """API 키 형식 검증"""
    print(f"\n🔑 API 키 형식 검증")
    print("=" * 50)
    
    api_key = os.getenv('BINANCE_API_KEY')
    secret_key = os.getenv('BINANCE_SECRET_KEY')
    
    if not api_key:
        print("❌ BINANCE_API_KEY 환경변수가 설정되지 않았습니다")
        return False
    
    if not secret_key:
        print("❌ BINANCE_SECRET_KEY 환경변수가 설정되지 않았습니다")
        return False
    
    # API 키 형식 검증
    print(f"API Key 길이: {len(api_key)}")
    print(f"API Key 시작: {api_key[:8]}...")
    print(f"Secret Key 길이: {len(secret_key)}")
    print(f"Secret Key 시작: {secret_key[:8]}...")
    
    # 일반적인 바이낸스 API 키 형식 확인
    if len(api_key) != 64:
        print("⚠️ API 키 길이가 일반적이지 않습니다 (64자 예상)")
    
    if len(secret_key) != 64:
        print("⚠️ Secret 키 길이가 일반적이지 않습니다 (64자 예상)")
    
    # 키에 특수문자나 공백 확인
    if ' ' in api_key or ' ' in secret_key:
        print("❌ API 키에 공백이 포함되어 있습니다")
        return False
    
    print("✅ API 키 형식이 올바른 것 같습니다")
    return True

def test_signature_generation():
    """서명 생성 테스트"""
    print(f"\n🔐 서명 생성 테스트")
    print("=" * 50)
    
    secret_key = os.getenv('BINANCE_SECRET_KEY')
    if not secret_key:
        print("❌ Secret 키가 없어서 서명 테스트를 할 수 없습니다")
        return False
    
    # 테스트 파라미터
    test_params = {
        'symbol': 'BTCUSDT',
        'timestamp': int(time.time() * 1000)
    }
    
    try:
        # 서명 생성
        query_string = urlencode(test_params)
        signature = hmac.new(
            secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        print(f"테스트 파라미터: {test_params}")
        print(f"쿼리 스트링: {query_string}")
        print(f"생성된 서명: {signature[:16]}...")
        print("✅ 서명 생성 성공")
        return True
        
    except Exception as e:
        print(f"❌ 서명 생성 실패: {e}")
        return False

def test_authenticated_request():
    """인증된 요청 테스트"""
    print(f"\n🔒 인증된 API 요청 테스트")
    print("=" * 50)
    
    api_key = os.getenv('BINANCE_API_KEY')
    secret_key = os.getenv('BINANCE_SECRET_KEY')
    
    if not (api_key and secret_key):
        print("❌ API 키가 설정되지 않았습니다")
        return False
    
    try:
        # 타임스탬프 생성
        timestamp = int(time.time() * 1000)
        params = {'timestamp': timestamp}
        
        # 서명 생성
        query_string = urlencode(params)
        signature = hmac.new(
            secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        params['signature'] = signature
        
        # 헤더 설정
        headers = {
            'X-MBX-APIKEY': api_key,
            'Content-Type': 'application/json'
        }
        
        print(f"요청 URL: https://api.binance.com/api/v3/account")
        print(f"헤더: X-MBX-APIKEY: {api_key[:8]}...")
        print(f"파라미터: timestamp={timestamp}, signature={signature[:16]}...")
        
        # API 요청
        response = requests.get(
            "https://api.binance.com/api/v3/account",
            params=params,
            headers=headers,
            timeout=15
        )
        
        print(f"응답 상태: {response.status_code}")
        print(f"응답 헤더: {dict(response.headers)}")
        
        if response.status_code == 200:
            account_info = response.json()
            print("✅ 인증 성공!")
            print(f"   계정 타입: {account_info.get('accountType', 'Unknown')}")
            print(f"   거래 가능: {account_info.get('canTrade', False)}")
            print(f"   권한: {account_info.get('permissions', [])}")
            return True
            
        else:
            print(f"❌ 인증 실패: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   오류 코드: {error_data.get('code', 'Unknown')}")
                print(f"   오류 메시지: {error_data.get('msg', 'Unknown')}")
                
                # 일반적인 오류 코드 해석
                error_code = error_data.get('code')
                if error_code == -2015:
                    print("   💡 해석: API 키가 유효하지 않거나 IP가 제한되었습니다")
                elif error_code == -1021:
                    print("   💡 해석: 타임스탬프가 서버 시간과 너무 차이납니다")
                elif error_code == -1022:
                    print("   💡 해석: 서명이 유효하지 않습니다")
                elif error_code == -2014:
                    print("   💡 해석: API 키 형식이 잘못되었습니다")
                    
            except:
                print(f"   응답 내용: {response.text}")
            
            return False
            
    except Exception as e:
        print(f"❌ 요청 실패: {e}")
        return False

def test_ip_restrictions():
    """IP 제한 테스트"""
    print(f"\n🌐 IP 제한 테스트")
    print("=" * 50)
    
    try:
        # 현재 IP 확인
        response = requests.get("https://httpbin.org/ip", timeout=10)
        if response.status_code == 200:
            current_ip = response.json().get('origin', 'Unknown')
            print(f"현재 IP: {current_ip}")
        else:
            print("❌ 현재 IP를 확인할 수 없습니다")
            return False
        
        # 바이낸스 서버에서 보는 IP 확인 (간접적)
        response = requests.get("https://api.binance.com/api/v3/time", timeout=10)
        if response.status_code == 200:
            print("✅ 바이낸스 서버에 접근 가능")
        else:
            print("❌ 바이낸스 서버에 접근할 수 없습니다")
            return False
        
        print(f"💡 바이낸스 API 관리에서 다음 IP가 허용되어 있는지 확인하세요: {current_ip}")
        return True
        
    except Exception as e:
        print(f"❌ IP 테스트 실패: {e}")
        return False

def main():
    """메인 디버깅 실행"""
    print("🔍 바이낸스 연결 디버깅")
    print("=" * 80)
    print(f"실행 시간: {datetime.now()}")
    
    results = {}
    
    # 1. 기본 네트워크 연결
    results['network'] = test_basic_connectivity()
    
    # 2. API 키 형식 검증
    results['api_key_format'] = test_api_key_format()
    
    # 3. 서명 생성 테스트
    results['signature'] = test_signature_generation()
    
    # 4. IP 제한 테스트
    results['ip_restrictions'] = test_ip_restrictions()
    
    # 5. 인증된 요청 테스트
    results['authenticated_request'] = test_authenticated_request()
    
    # 결과 요약
    print(f"\n" + "=" * 80)
    print("📊 디버깅 결과 요약")
    print("=" * 80)
    
    network_success = sum(1 for r in results['network'].values() if r.get('success', False))
    network_total = len(results['network'])
    
    print(f"🌐 네트워크 연결: {network_success}/{network_total}")
    print(f"🔑 API 키 형식: {'✅' if results['api_key_format'] else '❌'}")
    print(f"🔐 서명 생성: {'✅' if results['signature'] else '❌'}")
    print(f"🌍 IP 접근: {'✅' if results['ip_restrictions'] else '❌'}")
    print(f"🔒 인증 요청: {'✅' if results['authenticated_request'] else '❌'}")
    
    # 문제 해결 가이드
    print(f"\n💡 문제 해결 가이드:")
    
    if not results['api_key_format']:
        print("1. Railway 환경변수에서 BINANCE_API_KEY, BINANCE_SECRET_KEY 확인")
        print("2. API 키에 공백이나 특수문자가 없는지 확인")
    
    if not results['authenticated_request']:
        print("3. 바이낸스 API 관리에서 IP 제한 설정 확인")
        print("4. API 키 권한 설정 확인 (Reading, Trading 활성화)")
        print("5. API 키가 활성화되어 있는지 확인")
    
    if network_success < network_total:
        print("6. Railway 서버의 인터넷 연결 상태 확인")
        print("7. 방화벽이나 네트워크 제한 확인")
    
    # 결과 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f"binance_debug_{timestamp}.json"
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'results': results,
            'summary': {
                'network_success': network_success,
                'network_total': network_total,
                'api_key_format_ok': results['api_key_format'],
                'signature_ok': results['signature'],
                'ip_restrictions_ok': results['ip_restrictions'],
                'authenticated_request_ok': results['authenticated_request']
            }
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 상세 결과 저장: {result_file}")

if __name__ == "__main__":
    main()