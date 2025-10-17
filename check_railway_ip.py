#!/usr/bin/env python3
"""
Railway IP 확인 및 바이낸스 연결 테스트
"""

import requests
import json
from datetime import datetime

def check_current_ip():
    """현재 Railway 서버의 외부 IP 확인"""
    print("🌐 Railway 서버 IP 확인")
    print("=" * 50)
    
    ip_services = [
        "https://api.ipify.org?format=json",
        "https://httpbin.org/ip",
        "https://api.myip.com",
        "https://ipapi.co/json/"
    ]
    
    ips = []
    
    for service in ip_services:
        try:
            response = requests.get(service, timeout=10)
            data = response.json()
            
            # 각 서비스마다 IP 키가 다름
            ip = None
            if 'ip' in data:
                ip = data['ip']
            elif 'origin' in data:
                ip = data['origin']
            
            if ip:
                ips.append(ip)
                print(f"✅ {service}: {ip}")
            else:
                print(f"⚠️ {service}: IP 추출 실패 - {data}")
                
        except Exception as e:
            print(f"❌ {service}: {e}")
    
    # IP 통계
    if ips:
        unique_ips = list(set(ips))
        print(f"\n📊 발견된 IP: {len(unique_ips)}개")
        for ip in unique_ips:
            count = ips.count(ip)
            print(f"   {ip} ({count}회 확인)")
        
        return unique_ips[0] if unique_ips else None
    
    return None

def test_binance_connectivity(ip=None):
    """바이낸스 연결 테스트"""
    print(f"\n🔗 바이낸스 연결 테스트")
    print("=" * 50)
    
    if ip:
        print(f"현재 IP: {ip}")
    
    # 바이낸스 API 엔드포인트들
    endpoints = [
        "https://api.binance.com/api/v3/ping",
        "https://api.binance.com/api/v3/time",
        "https://api.binance.com/api/v3/exchangeInfo"
    ]
    
    results = {}
    
    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, timeout=10)
            results[endpoint] = {
                'status_code': response.status_code,
                'success': response.status_code == 200,
                'response_time': response.elapsed.total_seconds()
            }
            
            status = "✅" if response.status_code == 200 else "❌"
            print(f"{status} {endpoint.split('/')[-1]}: {response.status_code} ({response.elapsed.total_seconds():.3f}s)")
            
        except Exception as e:
            results[endpoint] = {'error': str(e), 'success': False}
            print(f"❌ {endpoint.split('/')[-1]}: {e}")
    
    return results

def check_railway_region():
    """Railway 리전 정보 확인"""
    print(f"\n🌏 Railway 리전 정보")
    print("=" * 50)
    
    try:
        # Railway 헤더에서 리전 정보 확인
        response = requests.get("https://eth-trading-bot-production.up.railway.app/debug", timeout=10)
        
        if response.status_code == 200:
            # Railway 헤더 확인
            railway_headers = {k: v for k, v in response.headers.items() if 'railway' in k.lower()}
            
            if railway_headers:
                print("Railway 헤더 정보:")
                for key, value in railway_headers.items():
                    print(f"   {key}: {value}")
            
            # 응답에서 리전 정보 추출
            try:
                data = response.json()
                env_vars = data.get('environment_variables', {})
                
                railway_info = {k: v for k, v in env_vars.items() if k.startswith('RAILWAY_')}
                
                if railway_info:
                    print(f"\nRailway 환경 정보:")
                    for key, value in railway_info.items():
                        if value:
                            print(f"   {key}: {value}")
                            
            except:
                pass
                
    except Exception as e:
        print(f"❌ Railway 정보 확인 실패: {e}")

def main():
    """메인 실행"""
    print("🚂 Railway IP 및 바이낸스 연결 분석")
    print("=" * 80)
    print(f"실행 시간: {datetime.now()}")
    
    # 1. 현재 IP 확인
    current_ip = check_current_ip()
    
    # 2. 바이낸스 연결 테스트
    binance_results = test_binance_connectivity(current_ip)
    
    # 3. Railway 리전 정보
    check_railway_region()
    
    # 4. 결과 요약
    print(f"\n" + "=" * 80)
    print("📋 분석 결과 요약")
    print("=" * 80)
    
    if current_ip:
        print(f"🌐 현재 Railway IP: {current_ip}")
        print(f"   ⚠️ 주의: Railway IP는 동적으로 변경될 수 있습니다")
    
    binance_success = sum(1 for r in binance_results.values() if r.get('success', False))
    binance_total = len(binance_results)
    
    print(f"🔗 바이낸스 연결: {binance_success}/{binance_total} 성공")
    
    if binance_success == binance_total:
        print("   ✅ 바이낸스 API에 정상 접근 가능")
    else:
        print("   ❌ 바이낸스 API 접근에 문제 있음")
    
    print(f"\n💡 권장사항:")
    print(f"1. Railway IP는 변경될 수 있으므로 바이낸스 IP 제한 설정 시 주의")
    print(f"2. Cloudflare Workers를 통한 고정 IP 프록시 사용 고려")
    print(f"3. 바이낸스 API 키에 IP 제한 대신 권한 제한 사용 권장")
    
    # 결과 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f"railway_ip_check_{timestamp}.json"
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'current_ip': current_ip,
            'binance_results': binance_results,
            'summary': {
                'binance_success': binance_success,
                'binance_total': binance_total
            }
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 상세 결과 저장: {result_file}")

if __name__ == "__main__":
    main()