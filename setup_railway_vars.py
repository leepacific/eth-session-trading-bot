#!/usr/bin/env python3
"""
Railway 환경변수 자동 설정 스크립트
- 필수 환경변수 확인 및 설정 가이드
- 커스텀 도메인 설정 검증
"""

import os
import json
from datetime import datetime

def check_environment_variables():
    """환경변수 확인"""
    print("🔍 Railway 환경변수 확인")
    print("=" * 80)
    
    # 필수 환경변수 목록
    required_vars = {
        'RAILWAY_ENVIRONMENT': 'production',
        'PORT': '8080',
        'CUSTOM_DOMAIN': 'api.leepacific-eth-trading-bot.site',
        'USE_CLOUDFLARE': 'true'
    }
    
    # 선택적 환경변수
    optional_vars = {
        'CLOUDFLARE_API_TOKEN': 'Cloudflare API 토큰',
        'CLOUDFLARE_ZONE_ID': 'Cloudflare Zone ID',
        'BINANCE_API_KEY': '바이낸스 API 키',
        'BINANCE_SECRET_KEY': '바이낸스 시크릿 키',
        'RAILWAY_PUBLIC_DOMAIN': 'Railway 기본 도메인'
    }
    
    print("📋 필수 환경변수:")
    missing_required = []
    
    for var, default_value in required_vars.items():
        current_value = os.getenv(var)
        if current_value:
            print(f"   ✅ {var}: {current_value}")
        else:
            print(f"   ❌ {var}: 미설정 (권장값: {default_value})")
            missing_required.append(var)
    
    print(f"\n📋 선택적 환경변수:")
    missing_optional = []
    
    for var, description in optional_vars.items():
        current_value = os.getenv(var)
        if current_value:
            # 민감한 정보는 일부만 표시
            if 'KEY' in var or 'TOKEN' in var:
                display_value = current_value[:8] + "..." if len(current_value) > 8 else current_value
            else:
                display_value = current_value
            print(f"   ✅ {var}: {display_value}")
        else:
            print(f"   ⚠️ {var}: 미설정 ({description})")
            missing_optional.append(var)
    
    return missing_required, missing_optional

def generate_railway_commands():
    """Railway CLI 명령어 생성"""
    print(f"\n🚂 Railway 환경변수 설정 명령어:")
    print("=" * 80)
    
    commands = [
        'railway variables --set "RAILWAY_ENVIRONMENT=production"',
        'railway variables --set "PORT=8080"',
        'railway variables --set "CUSTOM_DOMAIN=api.leepacific-eth-trading-bot.site"',
        'railway variables --set "USE_CLOUDFLARE=true"',
        'railway variables --set "BINANCE_TESTNET=false"',
        'railway variables --set "DATA_SYMBOL=ETHUSDT"',
        'railway variables --set "DATA_INTERVAL=15m"',
        'railway variables --set "DATA_POINTS_TARGET=500000"',
        'railway variables --set "INITIAL_BALANCE=100000"',
        'railway variables --set "MAX_ACCOUNT_RISK_PER_TRADE=0.05"',
        'railway variables --set "LIQUIDATION_PROBABILITY=0.07"',
        'railway variables --set "MAX_LEVERAGE=125"'
    ]
    
    print("다음 명령어들을 Railway CLI에서 실행하세요:")
    print()
    
    for i, cmd in enumerate(commands, 1):
        print(f"{i:2d}. {cmd}")
    
    print(f"\n⚠️ 추가로 설정해야 할 민감한 환경변수:")
    sensitive_vars = [
        'CLOUDFLARE_API_TOKEN=your_actual_cloudflare_token',
        'CLOUDFLARE_ZONE_ID=your_actual_zone_id', 
        'BINANCE_API_KEY=your_actual_binance_api_key',
        'BINANCE_SECRET_KEY=your_actual_binance_secret_key'
    ]
    
    for i, var in enumerate(sensitive_vars, 1):
        print(f"{i}. railway variables --set \"{var}\"")

def check_domain_configuration():
    """도메인 설정 확인"""
    print(f"\n🌐 도메인 설정 확인")
    print("=" * 80)
    
    custom_domain = os.getenv('CUSTOM_DOMAIN')
    
    if custom_domain:
        print(f"✅ 커스텀 도메인 설정됨: {custom_domain}")
        
        print(f"\n📋 Railway 대시보드에서 확인할 사항:")
        print(f"1. Settings → Domains에서 '{custom_domain}' 추가됨")
        print(f"2. SSL 인증서 상태가 '✅ Active'")
        print(f"3. 도메인 상태가 '✅ Connected'")
        
        print(f"\n📋 Cloudflare에서 확인할 사항:")
        print(f"1. DNS → Records에서 CNAME 레코드 존재")
        print(f"2. Name: api, Target: your-app.railway.app")
        print(f"3. Proxy status: Enabled (주황색 구름)")
        
    else:
        print(f"❌ 커스텀 도메인이 설정되지 않았습니다")
        print(f"   CUSTOM_DOMAIN 환경변수를 설정하세요")

def main():
    """메인 실행"""
    print("🚂 Railway 환경변수 및 도메인 설정 검증")
    print("=" * 80)
    
    # 환경변수 확인
    missing_required, missing_optional = check_environment_variables()
    
    # 도메인 설정 확인
    check_domain_configuration()
    
    # Railway 명령어 생성
    generate_railway_commands()
    
    # 요약
    print(f"\n📊 설정 상태 요약")
    print("=" * 80)
    
    if not missing_required:
        print("✅ 모든 필수 환경변수가 설정되었습니다")
    else:
        print(f"❌ {len(missing_required)}개 필수 환경변수가 누락되었습니다")
        print(f"   누락된 변수: {', '.join(missing_required)}")
    
    if not missing_optional:
        print("✅ 모든 선택적 환경변수가 설정되었습니다")
    else:
        print(f"⚠️ {len(missing_optional)}개 선택적 환경변수가 누락되었습니다")
    
    print(f"\n🎯 다음 단계:")
    if missing_required:
        print("1. 위의 Railway CLI 명령어로 필수 환경변수 설정")
        print("2. Railway 대시보드에서 커스텀 도메인 추가")
        print("3. Cloudflare DNS 설정 확인")
        print("4. 도메인 테스트 실행")
    else:
        print("1. Railway 대시보드에서 커스텀 도메인 상태 확인")
        print("2. python check_railway_domain.py 실행하여 도메인 테스트")
        print("3. 문제 발생 시 Railway 서비스 재배포")

if __name__ == "__main__":
    main()