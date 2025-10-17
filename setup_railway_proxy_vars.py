#!/usr/bin/env python3
"""
Railway 프록시 환경변수 설정 스크립트
"""

import os

def generate_railway_commands(worker_url):
    """Railway 환경변수 설정 명령어 생성"""
    
    print("🚂 Railway 환경변수 설정 명령어")
    print("=" * 60)
    
    commands = [
        f'railway variables --set "BINANCE_PROXY_URL={worker_url}"',
        'railway variables --set "USE_CLOUDFLARE_PROXY=true"',
        'railway variables --set "PROXY_TIMEOUT=30"',
        'railway variables --set "PROXY_RETRIES=3"'
    ]
    
    print("다음 명령어들을 실행하세요:")
    print()
    
    for i, cmd in enumerate(commands, 1):
        print(f"{i}. {cmd}")
    
    print(f"\n💡 참고:")
    print(f"- Worker URL은 Cloudflare Workers 배포 후 확인 가능")
    print(f"- 예시: https://binance-api-proxy.your-account.workers.dev")

def main():
    """메인 실행"""
    print("🌐 Cloudflare Workers 프록시 Railway 설정")
    print("=" * 80)
    
    # 사용자 입력 받기
    print("Cloudflare Worker URL을 입력하세요:")
    print("(예: https://binance-api-proxy.your-account.workers.dev)")
    
    worker_url = input("Worker URL: ").strip()
    
    if not worker_url:
        print("❌ Worker URL이 입력되지 않았습니다")
        print("기본 명령어를 생성합니다...")
        worker_url = "https://your-worker-url.workers.dev"
    
    if not worker_url.startswith('http'):
        worker_url = f"https://{worker_url}"
    
    generate_railway_commands(worker_url)
    
    print(f"\n🧪 테스트 방법:")
    print(f"1. 위 명령어들 실행")
    print(f"2. Railway 재배포: railway up --detach")
    print(f"3. 프록시 테스트: python binance_proxy_client.py")

if __name__ == "__main__":
    main()