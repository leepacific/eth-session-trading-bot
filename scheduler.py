#!/usr/bin/env python3
"""
매주 일요일 자동 최적화 스케줄러
Railway 환경에서 실행되는 백그라운드 서비스
"""

import schedule
import time
import os
import json
import logging
from datetime import datetime, timedelta
import subprocess
import requests
from pathlib import Path

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AutoOptimizationScheduler:
    def __init__(self):
        self.railway_api_url = os.getenv('RAILWAY_API_URL', 'https://api.railway.app')
        self.webhook_url = os.getenv('DISCORD_WEBHOOK_URL', '')
        self.trading_bot_url = os.getenv('TRADING_BOT_URL', 'http://localhost:8000')
        
        # 디렉토리 생성
        os.makedirs('logs', exist_ok=True)
        os.makedirs('config', exist_ok=True)
        os.makedirs('results', exist_ok=True)
        
    def send_notification(self, message, is_error=False):
        """Discord 웹훅으로 알림 전송"""
        if not self.webhook_url:
            logger.info(f"알림: {message}")
            return
            
        color = 0xFF0000 if is_error else 0x00FF00
        
        payload = {
            "embeds": [{
                "title": "🤖 자동 최적화 시스템",
                "description": message,
                "color": color,
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {"text": "Trading Bot Auto-Optimizer"}
            }]
        }
        
        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"알림 전송 실패: {e}")
    
    def run_optimization(self):
        """최적화 실행"""
        logger.info("🚀 주간 자동 최적화 시작")
        self.send_notification("📊 주간 자동 최적화를 시작합니다...")
        
        try:
            # 1. 최적화 실행
            logger.info("최적화 파이프라인 실행 중...")
            result = subprocess.run(
                ['python', 'run_optimization.py'],
                capture_output=True,
                text=True,
                timeout=1800  # 30분 타임아웃
            )
            
            if result.returncode != 0:
                error_msg = f"최적화 실패: {result.stderr}"
                logger.error(error_msg)
                self.send_notification(f"❌ {error_msg}", is_error=True)
                return False
            
            # 2. 백테스팅 검증
            logger.info("백테스팅 검증 중...")
            backtest_result = subprocess.run(
                ['python', 'run_full_backtest.py'],
                capture_output=True,
                text=True,
                timeout=600  # 10분 타임아웃
            )
            
            if backtest_result.returncode != 0:
                error_msg = f"백테스팅 검증 실패: {backtest_result.stderr}"
                logger.error(error_msg)
                self.send_notification(f"⚠️ {error_msg}", is_error=True)
                return False
            
            # 3. 결과 분석
            success_msg = self.analyze_results()
            
            # 4. Trading Bot에 새 파라미터 전송
            if self.update_trading_bot():
                logger.info("✅ 주간 자동 최적화 완료")
                self.send_notification(f"✅ 주간 최적화 완료!\n{success_msg}")
                return True
            else:
                self.send_notification("⚠️ 파라미터 업데이트 실패", is_error=True)
                return False
                
        except subprocess.TimeoutExpired:
            error_msg = "최적화 타임아웃 (30분 초과)"
            logger.error(error_msg)
            self.send_notification(f"⏰ {error_msg}", is_error=True)
            return False
        except Exception as e:
            error_msg = f"예상치 못한 오류: {str(e)}"
            logger.error(error_msg)
            self.send_notification(f"💥 {error_msg}", is_error=True)
            return False
    
    def analyze_results(self):
        """최적화 결과 분석"""
        try:
            # 최신 백테스팅 결과 로드
            results_dir = Path('results')
            backtest_files = list(results_dir.glob('full_backtest_*.json'))
            
            if not backtest_files:
                return "결과 파일을 찾을 수 없음"
            
            latest_file = max(backtest_files, key=os.path.getctime)
            
            with open(latest_file, 'r') as f:
                results = json.load(f)
            
            metrics = results['analysis']['basic_metrics']
            
            # 성과 요약
            summary = f"""
📊 **최적화 결과 요약**
• 총 거래: {metrics['total_trades']:,}개
• 승률: {metrics['win_rate']*100:.1f}%
• 수익 팩터: {metrics['profit_factor']:.2f}
• 총 수익률: {metrics['total_return']*100:.1f}%
• 최대 낙폭: {metrics['max_drawdown']*100:.1f}%
• 샤프 비율: {metrics['sharpe_ratio']:.2f}
• 소르티노 비율: {metrics['sortino_ratio']:.2f}
            """
            
            return summary.strip()
            
        except Exception as e:
            logger.error(f"결과 분석 실패: {e}")
            return "결과 분석 실패"
    
    def update_trading_bot(self):
        """Trading Bot에 새 파라미터 전송"""
        try:
            # 현재 파라미터 로드
            with open('config/current_parameters.json', 'r') as f:
                params_data = json.load(f)
            
            # Trading Bot API로 파라미터 업데이트
            update_url = f"{self.trading_bot_url}/api/update-parameters"
            
            payload = {
                'parameters': params_data['parameters'],
                'timestamp': params_data['timestamp'],
                'source': 'weekly_auto_optimization',
                'score': params_data.get('score', 0)
            }
            
            response = requests.post(
                update_url,
                json=payload,
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                logger.info("✅ Trading Bot 파라미터 업데이트 성공")
                return True
            else:
                logger.error(f"Trading Bot 업데이트 실패: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Trading Bot 업데이트 오류: {e}")
            return False
    
    def health_check(self):
        """시스템 상태 확인"""
        try:
            # 필수 파일 존재 확인
            required_files = [
                'run_optimization.py',
                'run_full_backtest.py',
                'data/ETHUSDT_15m_206319points_20251015_202539.csv'
            ]
            
            for file_path in required_files:
                if not os.path.exists(file_path):
                    logger.error(f"필수 파일 누락: {file_path}")
                    return False
            
            # 디스크 공간 확인 (최소 1GB)
            disk_usage = os.statvfs('.')
            free_space = disk_usage.f_bavail * disk_usage.f_frsize
            
            if free_space < 1024**3:  # 1GB
                logger.warning(f"디스크 공간 부족: {free_space / 1024**3:.1f}GB")
            
            logger.info("✅ 시스템 상태 정상")
            return True
            
        except Exception as e:
            logger.error(f"상태 확인 실패: {e}")
            return False
    
    def start_scheduler(self):
        """스케줄러 시작"""
        logger.info("🕐 자동 최적화 스케줄러 시작")
        
        # 매주 일요일 오전 3시 (UTC) 실행
        schedule.every().sunday.at("03:00").do(self.run_optimization)
        
        # 매일 상태 확인
        schedule.every().day.at("12:00").do(self.health_check)
        
        # 시작 알림
        self.send_notification("🚀 자동 최적화 스케줄러가 시작되었습니다.\n매주 일요일 03:00 UTC에 실행됩니다.")
        
        # 메인 루프
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # 1분마다 체크
            except KeyboardInterrupt:
                logger.info("스케줄러 종료")
                self.send_notification("⏹️ 자동 최적화 스케줄러가 종료되었습니다.")
                break
            except Exception as e:
                logger.error(f"스케줄러 오류: {e}")
                time.sleep(300)  # 5분 대기 후 재시도

def main():
    """메인 실행"""
    scheduler = AutoOptimizationScheduler()
    
    # 환경 변수 확인
    required_env_vars = ['TRADING_BOT_URL']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"필수 환경 변수 누락: {missing_vars}")
        return 1
    
    # 초기 상태 확인
    if not scheduler.health_check():
        logger.error("초기 상태 확인 실패")
        return 1
    
    # 스케줄러 시작
    scheduler.start_scheduler()
    
    return 0

if __name__ == "__main__":
    exit(main())