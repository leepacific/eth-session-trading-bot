"""
Railway 배포용 트레이딩 봇
헬스체크 서버와 트레이딩 로직을 함께 실행
"""

import os
import threading
import time
import signal
import sys
from datetime import datetime

# 헬스체크 서버 import
from health_server import start_health_server

# 트레이딩 전략 import
from eth_session_strategy import ETHSessionStrategy

# Cloudflare 통합 import
from cloudflare_integration import CloudflareManager

# 파라미터 관리 import
from parameter_manager import ParameterManager

class RailwayTradingBot:
    def __init__(self):
        """Railway 트레이딩 봇 초기화"""
        self.running = True
        self.strategy = None
        self.cloudflare = None
        self.param_manager = ParameterManager()
        
        print("🚀 Railway 트레이딩 봇 초기화")
        print(f"   환경: {os.getenv('RAILWAY_ENVIRONMENT', 'development')}")
        print(f"   시작 시간: {datetime.now()}")
        
        # Cloudflare 통합 초기화
        if os.getenv('USE_CLOUDFLARE', 'false').lower() == 'true':
            self.cloudflare = CloudflareManager()
        
        # 신호 핸들러 설정
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """종료 신호 처리"""
        print(f"\n🛑 종료 신호 수신: {signum}")
        self.running = False
        sys.exit(0)
    
    def run_backtest(self):
        """백테스트 실행"""
        try:
            print("📊 백테스트 시작...")
            
            # 데이터 파일 확인
            data_files = [f for f in os.listdir('data') if f.endswith('.csv')]
            if not data_files:
                print("❌ 데이터 파일이 없습니다.")
                return
            
            # 가장 최신 데이터 파일 사용
            latest_file = max(data_files, key=lambda x: os.path.getctime(f'data/{x}'))
            data_path = f'data/{latest_file}'
            
            print(f"📁 데이터 파일: {data_path}")
            
            # 전략 실행
            self.strategy = ETHSessionStrategy(data_path)
            trades = self.strategy.run_full_backtest()
            
            print(f"✅ 백테스트 완료: {len(trades) if trades else 0}개 거래")
            
            return trades
            
        except Exception as e:
            print(f"❌ 백테스트 오류: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def run_continuous(self):
        """지속적 실행 모드"""
        print("🔄 지속적 실행 모드 시작")
        
        while self.running:
            try:
                # 새로운 최적화 결과 확인
                self.param_manager.check_for_new_optimization_results()
                
                # 주기적으로 백테스트 실행 (예: 1시간마다)
                self.run_backtest()
                
                # 1시간 대기
                for _ in range(3600):  # 3600초 = 1시간
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                print(f"❌ 실행 오류: {e}")
                time.sleep(60)  # 1분 대기 후 재시도
    
    def start(self):
        """봇 시작"""
        try:
            # Cloudflare 설정 (Railway 환경에서만)
            if self.cloudflare and os.getenv('RAILWAY_ENVIRONMENT'):
                print("🌐 Cloudflare 설정 중...")
                self.cloudflare.full_setup()
            
            # 헬스체크 서버를 별도 스레드에서 시작
            health_thread = threading.Thread(target=start_health_server, daemon=True)
            health_thread.start()
            
            # Railway 환경에서는 한 번만 실행
            if os.getenv('RAILWAY_ENVIRONMENT'):
                print("🏭 Railway 환경에서 백테스트 실행")
                self.run_backtest()
                
                # 서버 유지를 위해 대기
                print("⏳ 서버 유지 중...")
                while self.running:
                    time.sleep(10)
            else:
                # 로컬 환경에서는 지속적 실행
                print("💻 로컬 환경에서 지속적 실행")
                self.run_continuous()
                
        except KeyboardInterrupt:
            print("\n🛑 사용자에 의해 중단됨")
        except Exception as e:
            print(f"❌ 봇 실행 오류: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print("👋 봇 종료")

def main():
    """메인 실행 함수"""
    bot = RailwayTradingBot()
    bot.start()

if __name__ == "__main__":
    main()