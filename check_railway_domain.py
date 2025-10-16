#!/usr/bin/env python3
"""
Railway 도메인 상태 확인 도구
- 기본 도메인과 커스텀 도메인 모두 테스트
- DNS 설정 및 SSL 상태 확인
"""

import requests
import json
import os
from datetime import datetime

def test_domain(domain, name):
    """도메인 테스트"""
    print(f"\n🔍 {name} 테스트: {domain}")
    
    endpoints = ['/', '/health', '/status']
    results = {}
    
    for endpoint in endpoints:
        url = f"https://{domain}{endpoint}"
        
        try:
            response = requests.get(url, timeout=10)
            results[endpoint] = {
                'status_code': response.status_code,
                'success': response.status_code == 200,
                'response_time': response.elapsed.total_seconds(),
                'headers': dict(response.headers)
            }
            
            status = "✅" if response.status_code == 200 else "❌"
            print(f"   {status} {endpoint}: {response.status_code} ({response.elapsed.total_seconds():.3f}s)")
            
        except Exception as e:
            results[endpoint] = {
                'error': str(e),
                'success': False
            }
            print(f"   ❌ {endpoint}: {e}")
    
    return results

def check_dns_settings():
    """DNS 설정 확인"""
    print("\n🌐 DNS 설정 확인...")
    
    domains_to_check = [
        "api.leepacific-eth-trading-bot.site",
        "leepacific-eth-trading-bot.site"
    ]
    
    for domain in domains_to_check:
        try:
            # nslookup 대신 간단한 HTTP 요청으로 확인
            response = requests.get(f"https://{domain}", timeout=5)
            print(f"   ✅ {domain}: 연결 가능")
        except Exception as e:
            print(f"   ❌ {domain}: {e}")

def main():
    """메인 실행"""
    print("🚂 Railway 도메인 상태 확인")
    print("=" * 80)
    
    # 환경변수에서 도메인 정보 확인
    custom_domain = os.getenv('CUSTOM_DOMAIN', 'api.leepacific-eth-trading-bot.site')
    railway_domain = os.getenv('RAILWAY_PUBLIC_DOMAIN', 'unknown.railway.app')
    
    print(f"📋 설정된 도메인:")
    print(f"   커스텀 도메인: {custom_domain}")
    print(f"   Railway 도메인: {railway_domain}")
    
    # DNS 설정 확인
    check_dns_settings()
    
    # 커스텀 도메인 테스트
    custom_results = test_domain(custom_domain, "커스텀 도메인")
    
    # Railway 기본 도메인 테스트 (알려진 경우)
    railway_results = None
    if railway_domain != 'unknown.railway.app':
        railway_results = test_domain(railway_domain, "Railway 기본 도메인")
    
    # 결과 요약
    print("\n" + "=" * 80)
    print("📊 테스트 결과 요약")
    print("=" * 80)
    
    custom_success = sum(1 for r in custom_results.values() if r.get('success', False))
    custom_total = len(custom_results)
    
    print(f"커스텀 도메인: {custom_success}/{custom_total} 성공")
    
    if railway_results:
        railway_success = sum(1 for r in railway_results.values() if r.get('success', False))
        railway_total = len(railway_results)
        print(f"Railway 도메인: {railway_success}/{railway_total} 성공")
    
    # 권장사항
    print(f"\n💡 권장사항:")
    
    if custom_success == 0:
        print("   ❌ 커스텀 도메인이 작동하지 않습니다")
        print("   🔧 Railway 대시보드에서 커스텀 도메인 설정을 확인하세요")
        print("   🌐 Cloudflare DNS 설정을 확인하세요")
        
        if railway_results and sum(1 for r in railway_results.values() if r.get('success', False)) > 0:
            print("   ✅ Railway 기본 도메인은 작동합니다")
            print(f"   🔗 임시로 이 도메인을 사용하세요: https://{railway_domain}")
    
    elif custom_success < custom_total:
        print("   ⚠️ 커스텀 도메인이 부분적으로 작동합니다")
        print("   🔧 일부 엔드포인트에 문제가 있을 수 있습니다")
    
    else:
        print("   ✅ 커스텀 도메인이 정상 작동합니다!")
    
    # 결과 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f"domain_check_result_{timestamp}.json"
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'custom_domain': custom_domain,
            'railway_domain': railway_domain,
            'custom_results': custom_results,
            'railway_results': railway_results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 상세 결과 저장: {result_file}")

if __name__ == "__main__":
    main()