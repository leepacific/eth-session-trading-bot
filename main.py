#!/usr/bin/env python3
"""
Advanced Optimization Pipeline - Main Entry Point
고급 최적화 파이프라인 메인 실행 파일
"""

import sys
import os
import argparse
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from optimization.optimization_pipeline import OptimizationPipeline, PipelineConfig
from trading.trading_bot import TradingBot
from tests.run_all_tests import ComprehensiveTestRunner

def run_optimization(config_file: str = None):
    """최적화 실행"""
    print("🚀 고급 최적화 파이프라인 시작")
    
    # 설정 로드
    if config_file:
        # TODO: 설정 파일에서 로드
        pass
    
    config = PipelineConfig(
        symbol="ETHUSDT",
        timeframe="15m",
        data_length=50000,
        global_search_samples=120,
        local_refinement_steps=40,
        mc_simulations=1000
    )
    
    # 파라미터 공간 정의
    parameter_space = {
        'target_r': (2.0, 4.0),
        'stop_atr_mult': (0.05, 0.2),
        'swing_len': (3, 10),
        'rr_percentile': (0.1, 0.4)
    }
    
    # 최적화 실행
    pipeline = OptimizationPipeline(config)
    result = pipeline.run_pipeline(parameter_space)
    
    print(f"✅ 최적화 완료: {result.status.value}")
    return result

def run_backtest():
    """백테스트 실행"""
    print("📊 백테스트 실행")
    # TODO: 백테스트 구현
    pass

def run_trading():
    """실제 트레이딩 실행"""
    print("💰 실제 트레이딩 시작")
    
    bot = TradingBot()
    bot.start()

def run_tests():
    """테스트 실행"""
    print("🧪 테스트 실행")
    
    runner = ComprehensiveTestRunner()
    results = runner.run_all_tests()
    
    return results['overall']['success_rate'] >= 0.8

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='고급 최적화 파이프라인')
    parser.add_argument('command', choices=['optimize', 'backtest', 'trade', 'test'],
                       help='실행할 명령')
    parser.add_argument('--config', help='설정 파일 경로')
    parser.add_argument('--symbol', default='ETHUSDT', help='거래 심볼')
    
    args = parser.parse_args()
    
    try:
        if args.command == 'optimize':
            result = run_optimization(args.config)
            sys.exit(0 if result.status.value == 'completed' else 1)
        
        elif args.command == 'backtest':
            run_backtest()
            sys.exit(0)
        
        elif args.command == 'trade':
            run_trading()
            sys.exit(0)
        
        elif args.command == 'test':
            success = run_tests()
            sys.exit(0 if success else 1)
    
    except KeyboardInterrupt:
        print("\n⏹️ 사용자에 의해 중단됨")
        sys.exit(2)
    
    except Exception as e:
        print(f"\n💥 오류 발생: {str(e)}")
        sys.exit(3)

if __name__ == "__main__":
    main()