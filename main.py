#!/usr/bin/env python3
"""
Railway 통합 서비스 - Trading Bot + Optimization Pipeline
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# FastAPI 및 웹 서비스
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# 프로젝트 모듈
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="ETH Trading Bot with Auto Optimization",
    description="Railway에서 실행되는 통합 트레이딩 시스템",
    version="2.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 데이터 모델
class OptimizationRequest(BaseModel):
    force_run: bool = False
    
class ParameterUpdate(BaseModel):
    parameters: dict
    source: str = "manual"

class SystemStatus(BaseModel):
    trading_active: bool
    last_optimization: str
    current_parameters: dict
    system_health: str

# 글로벌 상태
class SystemState:
    def __init__(self):
        self.trading_active = False
        self.optimization_running = False
        self.current_parameters = {}
        self.last_optimization = None
        self.load_parameters()
        
    def load_parameters(self):
        """저장된 파라미터 로드"""
        try:
            config_file = 'config/current_parameters.json'
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    data = json.load(f)
                    self.current_parameters = data.get('parameters', {})
                    self.last_optimization = data.get('timestamp', '')
                    logger.info(f"파라미터 로드 완료: {len(self.current_parameters)}개")
        except Exception as e:
            logger.error(f"파라미터 로드 실패: {e}")
            self.set_default_parameters()
    
    def set_default_parameters(self):
        """기본 파라미터 설정"""
        self.current_parameters = {
            'target_r': 2.536,
            'stop_atr_mult': 0.0734,
            'swing_len': 5.49,
            'rr_percentile': 0.168,
            'atr_len': 13.84,
            'session_strength': 1.397,
            'volume_filter': 1.521
        }
        self.last_optimization = datetime.now().isoformat()

# 글로벌 시스템 상태
system_state = SystemState()

# API 엔드포인트
@app.get("/")
async def root():
    return {
        "service": "ETH Trading Bot with Auto Optimization",
        "version": "2.0.0",
        "status": "running",
        "features": ["live_trading", "auto_optimization", "parameter_management"]
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "trading_active": system_state.trading_active,
        "optimization_running": system_state.optimization_running,
        "last_optimization": system_state.last_optimization
    }

@app.get("/status")
async def get_status():
    try:
        # 트레이딩 봇 상태 포함
        bot_status = {}
        try:
            bot = get_trading_bot()
            bot_status = bot.get_status()
        except Exception as e:
            logger.error(f"봇 상태 조회 실패: {e}")
        
        return {
            "trading_active": system_state.trading_active,
            "last_optimization": system_state.last_optimization or "",
            "current_parameters": system_state.current_parameters,
            "system_health": "healthy",
            "bot_status": bot_status,
            "optimization_running": system_state.optimization_running
        }
    except Exception as e:
        logger.error(f"상태 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/parameters")
async def get_parameters():
    return {
        "parameters": system_state.current_parameters,
        "last_update": system_state.last_optimization,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/update-parameters")
async def update_parameters(update: ParameterUpdate):
    try:
        # 파라미터 검증
        required_params = ['target_r', 'stop_atr_mult', 'swing_len']
        for param in required_params:
            if param not in update.parameters:
                raise HTTPException(status_code=400, detail=f"필수 파라미터 누락: {param}")
        
        # 파라미터 업데이트
        system_state.current_parameters.update(update.parameters)
        system_state.last_optimization = datetime.now().isoformat()
        
        # 파일 저장
        os.makedirs('config', exist_ok=True)
        config_data = {
            'timestamp': system_state.last_optimization,
            'source': update.source,
            'parameters': system_state.current_parameters
        }
        
        with open('config/current_parameters.json', 'w') as f:
            json.dump(config_data, f, indent=2)
        
        logger.info(f"파라미터 업데이트 완료 ({update.source})")
        
        return {
            "success": True,
            "message": "파라미터 업데이트 완료",
            "timestamp": system_state.last_optimization
        }
        
    except Exception as e:
        logger.error(f"파라미터 업데이트 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/run-optimization")
async def run_optimization(request: OptimizationRequest, background_tasks: BackgroundTasks):
    if system_state.optimization_running and not request.force_run:
        raise HTTPException(status_code=409, detail="최적화가 이미 실행 중입니다")
    
    background_tasks.add_task(execute_optimization)
    
    return {
        "success": True,
        "message": "최적화 시작됨",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/run-backtest")
async def run_backtest(background_tasks: BackgroundTasks):
    background_tasks.add_task(execute_backtest)
    
    return {
        "success": True,
        "message": "백테스트 시작됨",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/leverage-info")
async def get_leverage_info():
    """레버리지 최적화 정보 조회"""
    try:
        bot = get_trading_bot()
        
        # 현재 계좌 잔고 기준 레버리지 정보
        balance = bot.account_balance
        
        # 샘플 계산 (ETH 현재가 기준)
        sample_entry = 2500.0
        sample_stop = 2480.0
        sample_atr = 25.0
        
        long_position = bot.leverage_optimizer.calculate_optimal_position(
            sample_entry, sample_stop, sample_atr, 'long'
        )
        
        return {
            "account_balance": balance,
            "leverage_mode": "advanced_optimization",
            "rules": {
                "under_1000": "20 USDT 최소 주문",
                "over_1000": "0.5 Kelly 기반 포지션 사이징",
                "liquidation_probability": "5%",
                "max_leverage": 125
            },
            "sample_calculation": {
                "entry_price": sample_entry,
                "stop_price": sample_stop,
                "atr": sample_atr,
                "position_info": long_position
            },
            "risk_management": {
                "max_account_risk": bot.leverage_optimizer.max_account_risk * 100,
                "liquidation_probability": bot.leverage_optimizer.liquidation_probability * 100,
                "kelly_fraction": bot.leverage_optimizer.kelly_fraction
            }
        }
        
    except Exception as e:
        logger.error(f"레버리지 정보 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/start-trading")
async def start_trading():
    try:
        bot = get_trading_bot()
        bot.start_trading()
        system_state.trading_active = True
        
        # 백그라운드에서 거래 루프 시작
        asyncio.create_task(bot.run_trading_loop())
        
        logger.info("🚀 고급 레버리지 최적화 거래 시작")
        return {"success": True, "message": "고급 레버리지 최적화 거래 시작"}
        
    except Exception as e:
        logger.error(f"거래 시작 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stop-trading")
async def stop_trading():
    try:
        bot = get_trading_bot()
        bot.stop_trading()
        system_state.trading_active = False
        
        logger.info("⏹️ 거래 중지")
        return {"success": True, "message": "거래 중지"}
        
    except Exception as e:
        logger.error(f"거래 중지 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 트레이딩 봇 통합
from railway_trading_bot import get_trading_bot

# 백그라운드 작업
async def execute_optimization():
    """백그라운드에서 최적화 실행"""
    system_state.optimization_running = True
    logger.info("🚀 최적화 시작")
    
    try:
        # 최적화 실행
        import subprocess
        result = subprocess.run(
            [sys.executable, 'run_optimization.py'],
            capture_output=True,
            text=True,
            timeout=7200  # 2시간 타임아웃
        )
        
        if result.returncode == 0:
            logger.info("✅ 최적화 완료")
            system_state.load_parameters()  # 새 파라미터 로드
            
            # 트레이딩 봇에 새 파라미터 적용
            try:
                bot = get_trading_bot()
                bot.update_parameters(system_state.current_parameters)
                logger.info("🔄 트레이딩 봇 파라미터 업데이트 완료")
            except Exception as e:
                logger.error(f"트레이딩 봇 파라미터 업데이트 실패: {e}")
        else:
            logger.error(f"❌ 최적화 실패: {result.stderr}")
            
    except Exception as e:
        logger.error(f"❌ 최적화 오류: {e}")
    finally:
        system_state.optimization_running = False

async def execute_backtest():
    """백그라운드에서 백테스트 실행"""
    logger.info("📊 백테스트 시작")
    
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, 'run_full_backtest.py'],
            capture_output=True,
            text=True,
            timeout=1800  # 30분 타임아웃
        )
        
        if result.returncode == 0:
            logger.info("✅ 백테스트 완료")
        else:
            logger.error(f"❌ 백테스트 실패: {result.stderr}")
            
    except Exception as e:
        logger.error(f"❌ 백테스트 오류: {e}")

@app.on_event("startup")
async def startup_event():
    """앱 시작시 실행"""
    logger.info("🚀 ETH Trading Bot with Advanced Leverage Optimization 시작")
    
    # 디렉토리 생성
    os.makedirs('config', exist_ok=True)
    os.makedirs('results', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    
    # 트레이딩 봇 초기화 및 시작
    try:
        bot = get_trading_bot()
        logger.info(f"💰 계좌 잔고: ${bot.account_balance:.2f}")
        
        # 자동으로 거래 시작 (Railway 환경에서)
        if os.getenv('RAILWAY_ENVIRONMENT'):
            bot.start_trading()
            system_state.trading_active = True
            asyncio.create_task(bot.run_trading_loop())
            logger.info("🚀 자동 거래 시작 (Railway 환경)")
            
    except Exception as e:
        logger.error(f"트레이딩 봇 초기화 실패: {e}")
    
    # 스케줄러 시작 (백그라운드)
    if os.getenv('ENABLE_SCHEDULER', 'true').lower() == 'true':
        asyncio.create_task(start_scheduler())

async def start_scheduler():
    """스케줄러 시작"""
    try:
        import schedule
        import time
        
        # 매주 일요일 14:00 KST (05:00 UTC) 최적화 실행
        schedule.every().sunday.at("05:00").do(lambda: asyncio.create_task(execute_optimization()))
        
        logger.info("📅 스케줄러 시작: 매주 일요일 14:00 KST 최적화 실행")
        
        while True:
            schedule.run_pending()
            await asyncio.sleep(60)  # 1분마다 체크
            
    except Exception as e:
        logger.error(f"❌ 스케줄러 오류: {e}")

def main():
    """메인 실행"""
    port = int(os.getenv("PORT", 8000))
    
    # Railway 환경에서는 0.0.0.0으로 바인딩
    host = "0.0.0.0" if os.getenv("RAILWAY_ENVIRONMENT") else "127.0.0.1"
    
    logger.info(f"🚀 서버 시작: {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        log_level="info",
        reload=False
    )

if __name__ == "__main__":
    main()