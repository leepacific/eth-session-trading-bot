#!/usr/bin/env python3
"""
Cloudflare를 통한 실제 송신 IP 확인
"""

import requests
import json
import time
from datetime import datetime

def test_cloudflare_egress_ip():
    """Cloudflare를 통한 송신 IP 테스트"""
    
    print("🌐 Cloudflare 터널 송신 IP 확인")
    print("=" * 80)
    
    # 여러 IP 확인 서비스를 통해 테스트
    ip_services = [
        {
            'name': 'httpbin.org',
            'url': 'https://httpbin.org/ip',
            'ip_key': 'origin'
        },
        {
            'name': 'ipify.org', 
            'url': 'https://api.ipify.org?format=json',
            'ip_key': 'ip'
        },
        {
            'name': 'ipapi.co',
            'url': 'https://ipapi.co/json/',
            'ip_key': 'ip'
        }
    ]
    
    results = {}
    
    # 1. 직접 연결로 IP 확인
    print("1️⃣ 직접 연결 IP 확인:")
    direct_ips = []
    
    for service in ip_services:
        try:
            response = requests.get(service['url'], timeout=10)
            if response.status_code == 200:
                data = response.json()
                ip = data.get(service['ip_key'], 'unknown')
                direct_ips.append(ip)
                print(f"   ✅ {service['name']}: {ip}")
            else:
                print(f"   ❌ {service['name']}: HTTP {response.status_code}")
        except Exception as e:
            print(f"   ❌ {service['name']}: {e}")
    
    # 가장 많이 나온 IP를 직접 IP로 사용
    if direct_ips:
        direct_ip = max(set(direct_ips), key=direct_ips.count)
        print(f"   📍 직접 연결 IP: {direct_ip}")
        results['direct_ip'] = direct_ip
    
    # 2. Cloudflare 프록시를 통한 IP 확인 (간접적)
    print(f"\n2️⃣ Cloudflare 터널을 통한 연결:")
    
    proxy_url = "https://binance-proxy.leepacific-eth-trading-bot.site"
    
    try:
        # 바이낸스 API를 통해 연결 테스트
        response = requests.get(f"{proxy_url}/api/v3/time", timeout=15)
        
        if response.status_code == 200:
            print(f"   ✅ 터널 연결 성공")
            
            # 응답 헤더에서 Cloudflare 정보 확인
            cf_headers = {}
            for key, value in response.headers.items():
                if 'cf-' in key.lower() or 'cloudflare' in key.lower():
                    cf_headers[key] = value
            
            if cf_headers:
                print(f"   🌐 Cloudflare 헤더:")
                for key, value in cf_headers.items():
                    print(f"      {key}: {value}")
            
            # CF-Connecting-IP 헤더가 있으면 실제 송신 IP
            connecting_ip = response.headers.get('CF-Connecting-IP')
            if connecting_ip:
                print(f"   📍 Cloudflare 송신 IP: {connecting_ip}")
                results['cloudflare_ip'] = connecting_ip
            
            results['tunnel_working'] = True
            
        else:
            print(f"   ❌ 터널 연결 실패: HTTP {response.status_code}")
            results['tunnel_working'] = False
            
    except Exception as e:
        print(f"   ❌ 터널 테스트 오류: {e}")
        results['tunnel_working'] = False
    
    # 3. Cloudflare IP 범위 확인
    print(f"\n3️⃣ Cloudflare IP 범위 분석:")
    
    try:
        cf_response = requests.get("https://www.cloudflare.com/ips-v4", timeout=10)
        if cf_response.status_code == 200:
            cf_ranges = cf_response.text.strip().split('\n')
            print(f"   📊 Cloudflare IPv4 범위: {len(cf_ranges)}개")
            
            # 직접 IP가 Cloudflare 범위에 포함되는지 확인
            if 'direct_ip' in results:
                import ipaddress
                direct_ip_obj = ipaddress.IPv4Address(results['direct_ip'])
                
                in_cf_range = False
                for cf_range in cf_ranges:
                    try:
                        network = ipaddress.IPv4Network(cf_range, strict=False)
                        if direct_ip_obj in network:
                            print(f"   ✅ 직접 IP {results['direct_ip']}가 Cloudflare 범위 {cf_range}에 포함됨")
                            in_cf_range = True
                            break
                    except:
                        continue
                
                if not in_cf_range:
                    print(f"   ❌ 직접 IP {results['direct_ip']}가 Cloudflare 범위에 포함되지 않음")
            
            results['cloudflare_ranges'] = cf_ranges
            
    except Exception as e:
        print(f"   ❌ Cloudflare 범위 조회 실패: {e}")
    
    # 4. 바이낸스 허용 IP와 비교
    print(f"\n4️⃣ 바이낸스 허용 IP 분석:")
    
    binance_allowed_ips = [
        "104.16.0.1", "104.16.1.1", "104.16.2.1", "104.16.3.1", "104.16.4.1",
        "104.17.0.1", "104.17.1.1", "104.17.2.1", "104.17.3.1", "104.17.4.1",
        "104.18.0.1", "104.18.1.1", "104.18.2.1", "104.18.3.1", "104.18.4.1",
        "172.64.0.1", "172.64.1.1", "172.64.2.1", "172.64.3.1", "172.64.4.1",
        "173.245.48.1", "173.245.49.1", "173.245.50.1", "173.245.51.1", "173.245.52.1",
        "198.41.128.1", "198.41.129.1", "198.41.130.1", "198.41.131.1", "198.41.132.1",
        "208.77.246.81"  # Railway 직접 IP
    ]
    
    print(f"   📋 바이낸스 허용 IP: {len(binance_allowed_ips)}개")
    
    # 실제 사용 IP가 허용 목록에 있는지 확인
    if 'direct_ip' in results:
        if results['direct_ip'] in binance_allowed_ips:
            print(f"   ✅ 직접 IP {results['direct_ip']}가 바이낸스 허용 목록에 있음")
        else:
            print(f"   ❌ 직접 IP {results['direct_ip']}가 바이낸스 허용 목록에 없음")
    
    if 'cloudflare_ip' in results:
        if results['cloudflare_ip'] in binance_allowed_ips:
            print(f"   ✅ Cloudflare IP {results['cloudflare_ip']}가 바이낸스 허용 목록에 있음")
        else:
            print(f"   ❌ Cloudflare IP {results['cloudflare_ip']}가 바이낸스 허용 목록에 없음")
    
    # 5. 결과 요약 및 권장사항
    print(f"\n" + "=" * 80)
    print("📊 결과 요약 및 권장사항")
    print("=" * 80)
    
    if results.get('tunnel_working', False):
        print("✅ Cloudflare 터널이 정상 작동 중")
        
        if 'cloudflare_ip' in results:
            cf_ip = results['cloudflare_ip']
            if cf_ip in binance_allowed_ips:
                print(f"✅ 송신 IP {cf_ip}가 바이낸스에서 허용됨")
                print("💡 권장: Cloudflare 터널 사용 계속")
            else:
                print(f"❌ 송신 IP {cf_ip}가 바이낸스에서 허용되지 않음")
                print(f"💡 권장: 바이낸스에 {cf_ip} 추가 또는 더 많은 Cloudflare IP 추가")
        else:
            print("⚠️ Cloudflare 송신 IP를 직접 확인할 수 없음")
            print("💡 권장: 더 많은 Cloudflare IP 범위를 바이낸스에 추가")
    else:
        print("❌ Cloudflare 터널 연결 실패")
        direct_ip = results.get('direct_ip', 'unknown')
        print(f"💡 권장: 직접 IP {direct_ip} 사용 또는 터널 설정 수정")
    
    # 결과 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f"cloudflare_egress_test_{timestamp}.json"
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'results': results,
            'binance_allowed_ips': binance_allowed_ips,
            'test_summary': {
                'tunnel_working': results.get('tunnel_working', False),
                'direct_ip': results.get('direct_ip', 'unknown'),
                'cloudflare_ip': results.get('cloudflare_ip', 'unknown')
            }
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 상세 결과 저장: {result_file}")
    
    return results

if __name__ == "__main__":
    test_cloudflare_egress_ip()