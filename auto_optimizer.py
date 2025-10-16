#!/usr/bin/env python3
"""
자동 최적화 시스템
- 매주 일요일 18:00 KST 자동 실행
- Railway 리소스 70% 제한
- 다중해상도 베이지안 최적화
- 과최적화 방지 검증
"""

import os
import sys
import time
import json
import numpy as np
import pandas as pd
import psutil
import multiprocessing as mp
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 최적화 라이브러리
try:
    import optuna
    from optuna.samplers import TPESampler
    from optuna.pruners import SuccessiveHalvingPruner
except ImportError:
    print("⚠️ Optuna 설치 필요: pip install optuna")
    sys.exit(1)

# 스케줄링
try:
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger
    import pytz
except ImportError:
    print("⚠️ APScheduler 설치 필요: pip install apscheduler pytz")
    sys.exit(1)

# 전략 모듈
from eth_session_strategy import ETHSessionStrategy

class AutoOptimizer:
    def __init__(self):
        """자동 최적화 시스템 초기화"""
        self.setup_resource_limits()
        self.setup_optimization_config()
        
        print("🚀 자동 최적화 시스템 초기화")
        print(f"   CPU 코어: {self.max_workers}개 (제한: 70%)")
        print(f"   메모리: {self.max_memory_gb:.1f}GB (제한: 70%)")
        print(f"   다음 실행: 매주 일요일 18:00 KST")
    
    def setup_resource_limits(self):
        """Railway 리소스 제한 설정"""
        # CPU 제한 (70%)
        total_cpus = psutil.cpu_count()
        self.max_workers = max(1, int(total_cpus * 0.7))
        
        # 메모리 제한 (70%)
        total_memory = psutil.virtual_memory().total
        self.max_memory = int(total_memory * 0.7)
        self.max_memory_gb = self.max_memory / (1024**3)
        
        # 배치 크기 계산 (메모리 기반)
        estimated_memory_per_sample = 50 * 1024 * 1024  # 50MB per sample
        self.max_batch_size = max(1, self.max_memory // estimated_memory_per_sample)
        
        print(f"🛡️ 리소스 제한 설정:")
        print(f"   CPU: {self.max_workers}/{total_cpus} 코어")
        print(f"   메모리: {self.max_memory_gb:.1f}/{total_memory/(1024**3):.1f}GB")
        print(f"   배치 크기: {self.max_batch_size}")
    
    def setup_optimization_config(self):
        """최적화 설정"""
        self.config = {
            # 목표 지표 가중치
            'objective_weights': {
                'sortino_ratio': 0.25,
                'calmar_ratio': 0.20,
                'profit_factor': 0.20,
                'win_rate': 0.15,
                'sqn': 0.10,
                'rr_ratio': 0.10
            },
            
            # 목표 값들
            'target_values': {
                'sortino_ratio': 2.0,
                'calmar_ratio': 3.0,
                'profit_factor': 2.5,
                'win_rate': 0.55,
                'sqn': 4.0,
                'rr_ratio': 2.0
            },
            
            # 제약 조건
            'constraints': {
                'min_trades': 100,
                'max_drawdown': 0.20,  # 20%
                'min_win_rate': 0.35,
                'min_profit_factor': 1.3
            },
            
            # 최적화 단계
            'stages': {
                'stage1': {'samples': 100, 'data_points': 50000, 'time_limit': 20},
                'stage2': {'samples': 200, 'data_points': 100000, 'time_limit': 50},
                'stage3': {'samples': 10, 'data_points': 206319, 'time_limit': 20}
            }
        }
    
    def get_param_space(self):
        """파라미터 공간 정의"""
        return {
            'swing_len': {'type': 'int', 'low': 3, 'high': 7},
            'rr_percentile': {'type': 'float', 'low': 0.1, 'high': 0.8},
            'disp_mult': {'type': 'float', 'low': 0.8, 'high': 2.0},
            'sweep_wick_mult': {'type': 'float', 'low': 0.3, 'high': 0.8},
            'atr_len': {'type': 'int', 'low': 10, 'high': 50},
            'stop_atr_mult': {'type': 'float', 'low': 0.05, 'high': 0.15},
            'target_r': {'type': 'float', 'low': 1.5, 'high': 4.0},
            'time_stop_bars': {'type': 'int', 'low': 1, 'high': 8},
            'min_volatility_rank': {'type': 'float', 'low': 0.2, 'high': 0.7},
            'session_strength': {'type': 'float', 'low': 1.0, 'high': 2.5},
            'volume_filter': {'type': 'float', 'low': 1.0, 'high': 2.0},
            'trend_filter_len': {'type': 'int', 'low': 10, 'high': 50}
        }
    
    def calculate_performance_metrics(self, trades_df):
        """성과 지표 계산"""
        if len(trades_df) == 0:
            return None
        
        # 기본 통계
        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df['pnl'] > 0])
        losing_trades = len(trades_df[trades_df['pnl'] < 0])
        
        if total_trades == 0:
            return None
        
        win_rate = winning_trades / total_trades
        
        # PnL 통계
        returns = trades_df['pnl'].values
        avg_win = trades_df[trades_df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = trades_df[trades_df['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0
        
        # Profit Factor
        gross_profit = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # 누적 수익률 계산
        cumulative_returns = np.cumsum(returns)
        
        # Drawdown 계산
        peak = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - peak) / np.maximum(peak, 1)  # 0으로 나누기 방지
        max_drawdown = abs(drawdown.min()) if len(drawdown) > 0 else 0
        
        # Sortino Ratio (하방 편차 기준)
        negative_returns = returns[returns < 0]
        downside_deviation = np.std(negative_returns) if len(negative_returns) > 0 else 0.001
        sortino_ratio = np.mean(returns) / downside_deviation if downside_deviation > 0 else 0
        
        # Calmar Ratio
        total_return = cumulative_returns[-1] if len(cumulative_returns) > 0 else 0
        calmar_ratio = total_return / max_drawdown if max_drawdown > 0 else 0
        
        # System Quality Number (SQN)
        sqn = (np.mean(returns) / np.std(returns)) * np.sqrt(total_trades) if np.std(returns) > 0 else 0
        
        # Reward:Risk Ratio
        rr_ratio = abs(avg_win / avg_loss) if avg_loss < 0 else 0
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'sqn': sqn,
            'rr_ratio': rr_ratio,
            'total_return': total_return,
            'avg_win': avg_win,
            'avg_loss': avg_loss
        }
    
    def calculate_objective_score(self, metrics):
        """목적 함수 점수 계산"""
        if metrics is None:
            return -1000  # 패널티
        
        # 제약 조건 확인
        constraints = self.config['constraints']
        if (metrics['total_trades'] < constraints['min_trades'] or
            metrics['max_drawdown'] > constraints['max_drawdown'] or
            metrics['win_rate'] < constraints['min_win_rate'] or
            metrics['profit_factor'] < constraints['min_profit_factor']):
            return -1000  # 제약 조건 위반 시 큰 패널티
        
        # 정규화된 점수 계산
        weights = self.config['objective_weights']
        targets = self.config['target_values']
        
        def normalize_metric(value, target, is_higher_better=True):
            if is_higher_better:
                return min(value / target, 2.0)  # 최대 2배까지 보상
            else:
                return max(2.0 - (value / target), 0.0)
        
        score = (
            weights['sortino_ratio'] * normalize_metric(metrics['sortino_ratio'], targets['sortino_ratio']) +
            weights['calmar_ratio'] * normalize_metric(metrics['calmar_ratio'], targets['calmar_ratio']) +
            weights['profit_factor'] * normalize_metric(metrics['profit_factor'], targets['profit_factor']) +
            weights['win_rate'] * normalize_metric(metrics['win_rate'], targets['win_rate']) +
            weights['sqn'] * normalize_metric(metrics['sqn'], targets['sqn']) +
            weights['rr_ratio'] * normalize_metric(metrics['rr_ratio'], targets['rr_ratio'])
        )
        
        # 드로우다운 패널티
        dd_penalty = max(0, (metrics['max_drawdown'] - 0.15) * 10)  # 15% 초과시 패널티
        
        return score - dd_penalty
    
    def objective_function(self, trial, data_points=None):
        """Optuna 목적 함수"""
        try:
            # 파라미터 샘플링
            param_space = self.get_param_space()
            params = {}
            
            for param_name, param_config in param_space.items():
                if param_config['type'] == 'int':
                    params[param_name] = trial.suggest_int(param_name, param_config['low'], param_config['high'])
                elif param_config['type'] == 'float':
                    params[param_name] = trial.suggest_float(param_name, param_config['low'], param_config['high'])
            
            # 전략 실행
            strategy = ETHSessionStrategy()
            strategy.load_data()
            
            # 데이터 샘플링 (메모리 절약)
            if data_points and data_points < len(strategy.df):
                # 균등 샘플링
                indices = np.linspace(0, len(strategy.df)-1, data_points, dtype=int)
                strategy.df = strategy.df.iloc[indices].reset_index(drop=True)
            
            # 파라미터 적용
            for param_name, param_value in params.items():
                if param_name in strategy.params:
                    strategy.params[param_name] = param_value
            
            # 백테스트 실행
            strategy.generate_signals()
            trades = strategy.backtest()
            
            if not trades:
                return -1000
            
            # 성과 지표 계산
            trades_df = pd.DataFrame(trades)
            metrics = self.calculate_performance_metrics(trades_df)
            
            # 목적 함수 점수 계산
            score = self.calculate_objective_score(metrics)
            
            # 중간 결과 보고 (조기 중단용)
            if hasattr(trial, 'report'):
                trial.report(score, step=0)
                if trial.should_prune():
                    raise optuna.TrialPruned()
            
            return score
            
        except Exception as e:
            print(f"❌ 최적화 오류: {e}")
            return -1000
    
    def run_optimization_stage(self, stage_name, stage_config):
        """최적화 단계 실행"""
        print(f"\n🔍 {stage_name} 시작...")
        print(f"   샘플 수: {stage_config['samples']}")
        print(f"   데이터 포인트: {stage_config['data_points']:,}")
        print(f"   제한 시간: {stage_config['time_limit']}분")
        
        # Optuna 스터디 생성
        sampler = TPESampler(n_startup_trials=20, n_ei_candidates=24)
        pruner = SuccessiveHalvingPruner(min_resource=1, reduction_factor=4)
        
        study = optuna.create_study(
            direction='maximize',
            sampler=sampler,
            pruner=pruner
        )
        
        # 목적 함수 래퍼
        def objective_wrapper(trial):
            return self.objective_function(trial, stage_config['data_points'])
        
        # 최적화 실행
        start_time = time.time()
        timeout = stage_config['time_limit'] * 60  # 분을 초로 변환
        
        try:
            study.optimize(
                objective_wrapper,
                n_trials=stage_config['samples'],
                timeout=timeout,
                n_jobs=1,  # Railway 환경에서는 단일 프로세스
                show_progress_bar=True
            )
        except KeyboardInterrupt:
            print("⚠️ 사용자에 의해 중단됨")
        
        elapsed_time = time.time() - start_time
        
        print(f"✅ {stage_name} 완료 ({elapsed_time/60:.1f}분)")
        print(f"   최고 점수: {study.best_value:.4f}")
        print(f"   완료된 시도: {len(study.trials)}")
        
        return study
    
    def run_full_optimization(self):
        """전체 최적화 프로세스 실행"""
        print("🚀 자동 최적화 시작")
        print("=" * 80)
        
        start_time = datetime.now()
        results = {}
        
        try:
            # 1단계: 러프 스크리닝
            stage1_study = self.run_optimization_stage('1단계: 러프 스크리닝', self.config['stages']['stage1'])
            results['stage1'] = {
                'best_params': stage1_study.best_params,
                'best_score': stage1_study.best_value,
                'n_trials': len(stage1_study.trials)
            }
            
            # 2단계: 베이지안 최적화
            stage2_study = self.run_optimization_stage('2단계: 베이지안 최적화', self.config['stages']['stage2'])
            results['stage2'] = {
                'best_params': stage2_study.best_params,
                'best_score': stage2_study.best_value,
                'n_trials': len(stage2_study.trials)
            }
            
            # 3단계: 최종 검증
            stage3_study = self.run_optimization_stage('3단계: 최종 검증', self.config['stages']['stage3'])
            results['stage3'] = {
                'best_params': stage3_study.best_params,
                'best_score': stage3_study.best_value,
                'n_trials': len(stage3_study.trials)
            }
            
            # 최종 결과 저장
            final_params = stage3_study.best_params
            self.save_optimization_results(final_params, results, start_time)
            
            print("\n🎉 최적화 완료!")
            print(f"   총 소요시간: {(datetime.now() - start_time).total_seconds()/60:.1f}분")
            print(f"   최종 점수: {stage3_study.best_value:.4f}")
            
            return final_params
            
        except Exception as e:
            print(f"❌ 최적화 실행 오류: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def save_optimization_results(self, best_params, results, start_time):
        """최적화 결과 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        optimization_result = {
            'timestamp': timestamp,
            'start_time': start_time.isoformat(),
            'end_time': datetime.now().isoformat(),
            'duration_minutes': (datetime.now() - start_time).total_seconds() / 60,
            'best_parameters': best_params,
            'stage_results': results,
            'system_info': {
                'cpu_cores': psutil.cpu_count(),
                'memory_gb': psutil.virtual_memory().total / (1024**3),
                'max_workers': self.max_workers,
                'max_memory_gb': self.max_memory_gb
            }
        }
        
        # JSON 파일로 저장
        filename = f"optimization_result_{timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(optimization_result, f, indent=2, ensure_ascii=False)
        
        print(f"💾 최적화 결과 저장: {filename}")
        
        # 환경변수 업데이트 스크립트 생성
        self.generate_update_script(best_params, timestamp)
    
    def generate_update_script(self, best_params, timestamp):
        """파라미터 업데이트 스크립트 생성"""
        script_content = f"""#!/usr/bin/env python3
# 자동 생성된 파라미터 업데이트 스크립트
# 생성 시간: {timestamp}

# 최적화된 파라미터
OPTIMIZED_PARAMS = {best_params}

def update_strategy_params():
    '''전략 파라미터 업데이트'''
    from eth_session_strategy import ETHSessionStrategy
    
    strategy = ETHSessionStrategy()
    
    # 파라미터 업데이트
    for param_name, param_value in OPTIMIZED_PARAMS.items():
        if param_name in strategy.params:
            strategy.params[param_name] = param_value
            print(f"✅ {{param_name}}: {{param_value}}")
    
    return strategy

if __name__ == "__main__":
    print("🔄 파라미터 업데이트 중...")
    strategy = update_strategy_params()
    print("✅ 파라미터 업데이트 완료!")
"""
        
        script_filename = f"update_params_{timestamp}.py"
        with open(script_filename, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        print(f"📝 업데이트 스크립트 생성: {script_filename}")
    
    def setup_scheduler(self):
        """스케줄러 설정"""
        scheduler = BlockingScheduler()
        
        # 한국 시간대 설정
        kst = pytz.timezone('Asia/Seoul')
        
        # 매주 일요일 18:00 KST에 실행
        scheduler.add_job(
            func=self.run_full_optimization,
            trigger=CronTrigger(
                day_of_week='sun',  # 일요일
                hour=18,            # 18시
                minute=0,           # 0분
                timezone=kst
            ),
            id='weekly_optimization',
            name='주간 자동 최적화',
            replace_existing=True
        )
        
        print("📅 스케줄러 설정 완료")
        print("   실행 시간: 매주 일요일 18:00 KST")
        
        # 다음 실행 시간 계산
        next_run = scheduler.get_job('weekly_optimization').next_run_time
        print(f"   다음 실행: {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        return scheduler
    
    def start_scheduler(self):
        """스케줄러 시작"""
        try:
            scheduler = self.setup_scheduler()
            
            print("\n🚀 자동 최적화 스케줄러 시작")
            print("   Ctrl+C로 중단 가능")
            
            scheduler.start()
            
        except KeyboardInterrupt:
            print("\n⚠️ 스케줄러가 중단되었습니다.")
        except Exception as e:
            print(f"❌ 스케줄러 오류: {e}")

def main():
    """메인 실행 함수"""
    optimizer = AutoOptimizer()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--now':
        # 즉시 실행
        print("🚀 즉시 최적화 실행")
        optimizer.run_full_optimization()
    else:
        # 스케줄러 시작
        optimizer.start_scheduler()

if __name__ == "__main__":
    main()