#!/usr/bin/env python3
"""
Railway API 테스트 스크립트
- Railway 기본 도메인으로 모든 엔드포인트 테스트
"""

import requests
import json
from datetime import datetime

def test_railway_api():
    """Railway API 테스트"""
    base_url = "https://eth-trading-bot-production.up.railway.app"
    
    endpoints = [
        '/',
        '/health',
        '/status',
        '/parameters',
        '/optimization',
        '/test-binance',
        '/debug'
    ]
    
    print("🚂 Railway API 테스트")
    print("=" * 80)
    print(f"기본 URL: {base_url}")
    print(f"테스트 시간: {datetime.now()}")
    print()
    
    results = {}
    
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        
        try:
            print(f"🔍 테스트 중: {endpoint}")
            response = requests.get(url, timeout=10)
            
            results[endpoint] = {
                'status_code': response.status_code,
                'success': response.status_code == 200,
                'response_time': response.elapsed.total_seconds(),
                'content_type': response.headers.get('content-type', 'unknown')
            }
            
            status_icon = "✅" if response.status_code == 200 else "❌"
            print(f"   {status_icon} {response.status_code} ({response.elapsed.total_seconds():.3f}s)")
            
            # JSON 응답인 경우 일부 내용 표시
            if 'application/json' in response.headers.get('content-type', ''):
                try:
                    data = response.json()
                    if isinstance(data, dict):
                        # 주요 키만 표시
                        key_info = []
                        for key in ['status', 'bot_status', 'timestamp', 'service']:
                            if key in data:
                                key_info.append(f"{key}: {data[key]}")
                        if key_info:
                            print(f"      {', '.join(key_info)}")
                except:
                    pass
            
        except Exception as e:
            results[endpoint] = {
                'error': str(e),
                'success': False
            }
            print(f"   ❌ 오류: {e}")
        
        print()
    
    # 결과 요약
    print("=" * 80)
    print("📊 테스트 결과 요약")
    print("=" * 80)
    
    successful = sum(1 for r in results.values() if r.get('success', False))
    total = len(results)
    
    print(f"성공: {successful}/{total} ({successful/total*100:.1f}%)")
    
    if successful == total:
        print("🎉 모든 엔드포인트가 정상 작동합니다!")
    elif successful > 0:
        print("⚠️ 일부 엔드포인트에 문제가 있습니다.")
        failed_endpoints = [ep for ep, result in results.items() if not result.get('success', False)]
        print(f"   실패한 엔드포인트: {', '.join(failed_endpoints)}")
    else:
        print("❌ 모든 엔드포인트가 실패했습니다.")
    
    print(f"\n🔗 사용 가능한 URL:")
    print(f"   메인 페이지: {base_url}/")
    print(f"   API 테스트 도구: {base_url}/test-tool")
    print(f"   헬스체크: {base_url}/health")
    
    # 결과 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f"railway_api_test_{timestamp}.json"
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'base_url': base_url,
            'results': results,
            'summary': {
                'successful': successful,
                'total': total,
                'success_rate': successful/total*100
            }
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 상세 결과 저장: {result_file}")

if __name__ == "__main__":
    test_railway_api()