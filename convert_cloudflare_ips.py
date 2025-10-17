#!/usr/bin/env python3
"""
Cloudflare CIDR 범위를 개별 IP 주소로 변환
바이낸스 API 허용 목록에 추가할 수 있는 형태로 변환
"""

import ipaddress
import requests

def get_cloudflare_ip_ranges():
    """Cloudflare IP 범위 조회"""
    try:
        response = requests.get("https://www.cloudflare.com/ips-v4", timeout=10)
        if response.status_code == 200:
            return response.text.strip().split('\n')
        return []
    except:
        return []

def convert_cidr_to_ips(cidr_ranges, max_ips_per_range=10):
    """CIDR 범위를 개별 IP로 변환 (제한된 수만)"""
    
    all_ips = []
    
    for cidr in cidr_ranges:
        try:
            network = ipaddress.IPv4Network(cidr, strict=False)
            
            # 네트워크 크기 확인
            total_ips = network.num_addresses
            
            print(f"📊 {cidr}: {total_ips:,}개 IP 주소")
            
            if total_ips > 1000:
                print(f"   ⚠️ 너무 많은 IP ({total_ips:,}개) - 처음 {max_ips_per_range}개만 추출")
                # 처음 몇 개만 추출
                ips = list(network.hosts())[:max_ips_per_range]
            else:
                # 모든 IP 추출 (호스트 주소만)
                ips = list(network.hosts())
            
            for ip in ips:
                all_ips.append(str(ip))
                
        except Exception as e:
            print(f"❌ {cidr} 변환 실패: {e}")
    
    return all_ips

def find_cloudflare_gateway_ips():
    """Cloudflare Gateway IP 찾기 (더 제한적인 범위)"""
    
    # Cloudflare의 주요 게이트웨이 IP들 (예시)
    gateway_ips = [
        "104.16.0.1",
        "104.16.1.1", 
        "104.17.0.1",
        "104.18.0.1",
        "172.64.0.1",
        "172.65.0.1",
        "173.245.48.1",
        "173.245.49.1",
        "198.41.128.1",
        "198.41.129.1"
    ]
    
    return gateway_ips

def main():
    """메인 실행"""
    print("🌐 Cloudflare IP 범위 → 개별 IP 변환")
    print("=" * 80)
    
    # Cloudflare IP 범위 조회
    print("📡 Cloudflare IP 범위 조회 중...")
    cidr_ranges = get_cloudflare_ip_ranges()
    
    if not cidr_ranges:
        print("❌ Cloudflare IP 범위를 가져올 수 없습니다")
        return
    
    print(f"✅ {len(cidr_ranges)}개 CIDR 범위 발견")
    
    # 총 IP 수 계산
    total_possible_ips = 0
    for cidr in cidr_ranges:
        try:
            network = ipaddress.IPv4Network(cidr, strict=False)
            total_possible_ips += network.num_addresses
        except:
            pass
    
    print(f"📊 총 가능한 IP 수: {total_possible_ips:,}개")
    print(f"⚠️ 바이낸스는 개별 IP만 허용하므로 모든 IP를 추가하는 것은 비현실적입니다")
    
    print(f"\n💡 권장 해결책:")
    print("=" * 80)
    
    print("1. 🚫 IP 제한 사용하지 않기 (가장 간단)")
    print("   - 바이낸스 API 키에서 IP 제한을 비활성화")
    print("   - 대신 API 키 권한을 최소화 (Reading, Trading만)")
    print("   - 출금 권한은 절대 활성화하지 않기")
    
    print("\\n2. 🎯 특정 Cloudflare IP만 사용")
    print("   - Cloudflare Workers에서 특정 IP로 고정")
    print("   - 또는 Cloudflare의 주요 게이트웨이 IP만 허용")
    
    print("\\n3. 🔄 동적 IP 관리")
    print("   - Railway IP 변경 시 자동으로 바이낸스 설정 업데이트")
    print("   - 바이낸스 API를 통한 자동 IP 관리 (가능한 경우)")
    
    # 주요 게이트웨이 IP 제안
    print(f"\\n🎯 Cloudflare 주요 게이트웨이 IP (제한적 목록):")
    print("=" * 80)
    
    gateway_ips = find_cloudflare_gateway_ips()
    
    print("바이낸스 허용 목록에 추가할 IP들:")
    for i, ip in enumerate(gateway_ips, 1):
        print(f"{i:2d}. {ip}")
    
    print(f"\\n⚠️ 주의사항:")
    print("- 이 IP들이 실제로 Cloudflare Workers에서 사용되는지 보장할 수 없습니다")
    print("- 가장 안전한 방법은 IP 제한을 사용하지 않는 것입니다")
    
    # 대안 제안
    print(f"\\n🔧 실용적인 대안:")
    print("=" * 80)
    
    print("1. 바이낸스 API 키 설정:")
    print("   ✅ Enable Reading")
    print("   ✅ Enable Spot & Margin Trading")
    print("   ❌ Enable Futures (필요시만)")
    print("   ❌ Enable Withdrawals (절대 비활성화)")
    print("   ❌ Restrict access to trusted IPs only (비활성화)")
    
    print("\\n2. 추가 보안 조치:")
    print("   - API 키를 정기적으로 갱신")
    print("   - 거래 로그 모니터링")
    print("   - 비정상적인 활동 감지 시 즉시 API 키 비활성화")
    
    print("\\n3. Railway 환경변수 보안:")
    print("   - API 키를 코드에 하드코딩하지 않기")
    print("   - .env 파일을 .gitignore에 추가")
    print("   - Railway 환경변수만 사용")

if __name__ == "__main__":
    main()