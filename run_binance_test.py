#!/usr/bin/env python3
"""
Railway 환경에서 바이낸스 테스트 실행
- 단발성 테스트 주문 포함
- 수동 실행용 스크립트
"""

import os
import sys
from binance_connection_test import BinanceConnectionTester

def main():
    """메인 실행 함수"""
    print("🚀 Railway 바이낸스 연결 테스트")
    print("=" * 80)
    
    # Railway 환경 확인
    if os.getenv('RAILWAY_ENVIRONMENT'):
        print("🚂 Railway 환경에서 실행 중")
    else:
        print("💻 로컬 환경에서 실행 중")
    
    # 환경변수 확인
    required_vars = ['BINANCE_API_KEY', 'BINANCE_SECRET_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ 필수 환경변수가 설정되지 않았습니다: {', '.join(missing_vars)}")
        sys.exit(1)
    
    # 테스트 실행
    tester = BinanceConnectionTester()
    
    print("\n⚠️ 주의사항:")
    print("   - 이 테스트는 실제 바이낸스 API에 연결합니다")
    print("   - 테스트 주문이 전송될 수 있습니다")
    print("   - 주문은 체결되지 않는 가격으로 설정됩니다")
    print("   - 테스트 후 바이낸스에서 수동으로 주문을 취소해주세요")
    
    confirm = input("\n계속 진행하시겠습니까? (y/N): ")
    if confirm.lower() != 'y':
        print("테스트가 취소되었습니다.")
        sys.exit(0)
    
    # 전체 테스트 실행
    results = tester.run_full_test()
    
    # Railway 환경에서 결과 요약
    if os.getenv('RAILWAY_ENVIRONMENT'):
        print("\n🚂 Railway 환경 테스트 완료!")
        print("   결과는 Railway 로그에서 확인할 수 있습니다.")
        
        # 간단한 상태 출력
        passed = sum(results.values())
        total = len(results)
        
        if passed == total:
            print("   ✅ 모든 테스트 통과")
        elif passed >= total * 0.8:
            print("   ⚠️ 일부 테스트 실패")
        else:
            print("   ❌ 다수 테스트 실패")

if __name__ == "__main__":
    main()