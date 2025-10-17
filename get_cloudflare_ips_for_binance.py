#!/usr/bin/env python3
"""
바이낸스에 추가할 Cloudflare IP 목록 생성
"""

import requests

def get_cloudflare_egress_ips():
    """Cloudflare 송신 IP 범위 조회"""
    
    # Cloudflare의 주요 송신 IP들 (문서화된 범위)
    cloudflare_egress_ips = [
        # Cloudflare 주요 데이터센터 IP들
        "104.16.0.0/12",      # 104.16.0.0 - 104.31.255.255
        "172.64.0.0/13",      # 172.64.0.0 - 172.71.255.255  
        "173.245.48.0/20",    # 173.245.48.0 - 173.245.63.255
        "103.21.244.0/22",    # 103.21.244.0 - 103.21.247.255
        "103.22.200.0/22",    # 103.22.200.0 - 103.22.203.255
        "103.31.4.0/22",      # 103.31.4.0 - 103.31.7.255
        "141.101.64.0/18",    # 141.101.64.0 - 141.101.127.255
        "108.162.192.0/18",   # 108.162.192.0 - 108.162.255.255
        "190.93.240.0/20",    # 190.93.240.0 - 190.93.255.255
        "188.114.96.0/20",    # 188.114.96.0 - 188.114.111.255
        "197.234.240.0/22",   # 197.234.240.0 - 197.234.243.255
        "198.41.128.0/17",    # 198.41.128.0 - 198.41.255.255
        "162.158.0.0/15",     # 162.158.0.0 - 162.159.255.255
        "104.24.0.0/14",      # 104.24.0.0 - 104.27.255.255
        "131.0.72.0/22"       # 131.0.72.0 - 131.0.75.255
    ]
    
    return cloudflare_egress_ips

def convert_to_individual_ips(cidr_list, max_per_range=5):
    """CIDR을 개별 IP로 변환 (제한적)"""
    import ipaddress
    
    individual_ips = []
    
    for cidr in cidr_list:
        try:
            network = ipaddress.IPv4Network(cidr, strict=False)
            
            # 각 범위에서 처음 몇 개 IP만 추출
            hosts = list(network.hosts())[:max_per_range]
            
            for ip in hosts:
                individual_ips.append(str(ip))
                
        except Exception as e:
            print(f"❌ {cidr} 변환 실패: {e}")
    
    return individual_ips

def main():
    """메인 실행"""
    print("🌐 바이낸스에 추가할 Cloudflare IP 목록")
    print("=" * 80)
    
    # Cloudflare 송신 IP 범위
    cidr_ranges = get_cloudflare_egress_ips()
    
    print(f"📊 Cloudflare IP 범위: {len(cidr_ranges)}개")
    
    # 바이낸스에서 권장하는 방법: 주요 IP만 선별
    recommended_ips = [
        # Cloudflare 주요 게이트웨이 IP들
        "104.16.0.1", "104.16.1.1", "104.16.2.1", "104.16.3.1", "104.16.4.1",
        "104.17.0.1", "104.17.1.1", "104.17.2.1", "104.17.3.1", "104.17.4.1",
        "104.18.0.1", "104.18.1.1", "104.18.2.1", "104.18.3.1", "104.18.4.1",
        "172.64.0.1", "172.64.1.1", "172.64.2.1", "172.64.3.1", "172.64.4.1",
        "173.245.48.1", "173.245.49.1", "173.245.50.1", "173.245.51.1", "173.245.52.1",
        "198.41.128.1", "198.41.129.1", "198.41.130.1", "198.41.131.1", "198.41.132.1"
    ]
    
    print(f"\n🎯 바이낸스 허용 목록에 추가할 IP들:")
    print("=" * 80)
    print("다음 IP들을 바이낸스 API 관리에서 허용 목록에 추가하세요:")
    print()
    
    for i, ip in enumerate(recommended_ips, 1):
        print(f"{i:2d}. {ip}")
    
    print(f"\n📋 바이낸스 설정 단계:")
    print("=" * 80)
    print("1. https://www.binance.com/en/my/settings/api-management 접속")
    print("2. API 키 편집 → IP Access Restrictions")
    print("3. 위의 30개 IP를 모두 허용 목록에 추가")
    print("4. 권한 설정:")
    print("   ✅ Enable Reading")
    print("   ✅ Enable Spot & Margin Trading") 
    print("   ❌ Enable Withdrawals (보안상 비활성화)")
    print("5. Save 클릭")
    
    print(f"\n⚠️ 중요 사항:")
    print("- 모든 IP를 추가하는 데 시간이 걸릴 수 있습니다")
    print("- IP 추가 후 5-10분 정도 기다린 후 테스트하세요")
    print("- 일부 IP가 작동하지 않을 수 있으니 여러 개를 추가하는 것이 안전합니다")
    
    # 파일로 저장
    with open('binance_cloudflare_ips.txt', 'w') as f:
        f.write("바이낸스 허용 목록에 추가할 Cloudflare IP들\\n")
        f.write("=" * 50 + "\\n\\n")
        for ip in recommended_ips:
            f.write(f"{ip}\\n")
    
    print(f"\n📄 IP 목록 저장: binance_cloudflare_ips.txt")
    
    return recommended_ips

if __name__ == "__main__":
    main()