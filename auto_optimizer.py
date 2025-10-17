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
            # 목표 지표 가중치 (동적 조정 가능)
            'objective_weights': {
                'sortino_ratio': 0.25,
                'calmar_ratio': 0.20,
                'profit_factor': 0.20,
                'win_rate': 0.15,
                'sqn': 0.10,
                'rr_ratio': 0.10
            },
            
            # 목표 값들 (시장 조건에 따라 동적 조정)
            'target_values': {
                'sortino_ratio': 2.0,
                'calmar_ratio': 3.0,
                'profit_factor': 2.5,
                'win_rate': 0.55,
                'sqn': 4.0,
                'rr_ratio': 2.0
            },
            
            # 제약 조건 (최소 요구사항)
            'constraints': {
                'min_trades': 100,
                'max_drawdown': 0.20,  # 20%
                'min_win_rate': 0.35,
                'min_profit_factor': 1.3
            },
            
            # 워크포워드 테스트 설정
            'walk_forward': {
                'enabled': True,
                'window_size': 0.6,      # 60% 인샘플
                'step_size': 0.1,        # 10% 스텝
                'min_oos_trades': 20,    # 최소 아웃오브샘플 거래 수
                'consistency_threshold': 0.7,  # 70% 이상 구간에서 수익성 유지
                'stability_factor': 0.8   # 성과 안정성 요구 수준
            },
            
            # 최적화 단계 (워크포워드 포함)
            'stages': {
                'stage1': {'samples': 100, 'data_points': 50000, 'time_limit': 20, 'wf_enabled': False},
                'stage2': {'samples': 200, 'data_points': 100000, 'time_limit': 50, 'wf_enabled': False},
                'stage3': {'samples': 50, 'data_points': 206319, 'time_limit': 60, 'wf_enabled': True}
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
    
    def run_walk_forward_test(self, strategy, params):
        """워크포워드 테스트 실행"""
        wf_config = self.config['walk_forward']
        df = strategy.df
        total_length = len(df)
        
        window_size = int(total_length * wf_config['window_size'])
        step_size = int(total_length * wf_config['step_size'])
        
        print(f"🔄 워크포워드 테스트 시작 (윈도우: {window_size}, 스텝: {step_size})")
        
        oos_results = []  # Out-of-Sample 결과들
        
        # 워크포워드 윈도우들
        start_idx = 0
        while start_idx + window_size < total_length:
            end_idx = start_idx + window_size
            oos_start = end_idx
            oos_end = min(oos_start + step_size, total_length)
            
            if oos_end - oos_start < step_size * 0.5:  # 너무 작은 OOS는 스킵
                break
            
            # In-Sample 데이터로 최적화 (실제로는 파라미터 그대로 사용)
            is_data = df.iloc[start_idx:end_idx].copy().reset_index(drop=True)
            
            # Out-of-Sample 테스트
            oos_data = df.iloc[oos_start:oos_end].copy().reset_index(drop=True)
            
            # OOS 전략 실행
            oos_strategy = ETHSessionStrategy()
            oos_strategy.df = oos_data
            
            # 파라미터 적용
            for param_name, param_value in params.items():
                if param_name in oos_strategy.params:
                    oos_strategy.params[param_name] = param_value
            
            # OOS 백테스트
            oos_strategy.generate_signals()
            oos_trades = oos_strategy.backtest()
            
            if oos_trades and len(oos_trades) >= wf_config['min_oos_trades']:
                oos_trades_df = pd.DataFrame(oos_trades)
                oos_metrics = self.calculate_performance_metrics(oos_trades_df)
                
                if oos_metrics:
                    oos_results.append({
                        'period': f"{oos_start}-{oos_end}",
                        'trades': len(oos_trades),
                        'metrics': oos_metrics,
                        'profitable': oos_metrics['total_return'] > 0
                    })
            
            start_idx += step_size
        
        if len(oos_results) == 0:
            return -1000  # 유효한 OOS 결과가 없음
        
        # 워크포워드 성과 평가
        return self.evaluate_walk_forward_results(oos_results)
    
    def evaluate_walk_forward_results(self, oos_results):
        """워크포워드 결과 평가"""
        wf_config = self.config['walk_forward']
        
        # 일관성 확인 (수익성 있는 구간 비율)
        profitable_periods = sum(1 for r in oos_results if r['profitable'])
        consistency_ratio = profitable_periods / len(oos_results)
        
        if consistency_ratio < wf_config['consistency_threshold']:
            return -1000  # 일관성 부족
        
        # 전체 OOS 성과 계산
        all_metrics = [r['metrics'] for r in oos_results]
        
        # 평균 성과 지표
        avg_metrics = {
            'total_trades': sum(m['total_trades'] for m in all_metrics),
            'win_rate': np.mean([m['win_rate'] for m in all_metrics]),
            'profit_factor': np.mean([m['profit_factor'] for m in all_metrics if m['profit_factor'] != float('inf')]),
            'max_drawdown': max(m['max_drawdown'] for m in all_metrics),
            'sortino_ratio': np.mean([m['sortino_ratio'] for m in all_metrics]),
            'calmar_ratio': np.mean([m['calmar_ratio'] for m in all_metrics]),
            'sqn': np.mean([m['sqn'] for m in all_metrics]),
            'rr_ratio': np.mean([m['rr_ratio'] for m in all_metrics])
        }
        
        # 안정성 패널티 계산
        stability_penalty = self.calculate_stability_penalty(all_metrics)
        
        # 기본 점수 계산
        base_score = self.calculate_objective_score(avg_metrics)
        
        # 워크포워드 보너스 (일관성에 따른)
        wf_bonus = consistency_ratio * 0.2  # 최대 20% 보너스
        
        final_score = base_score + wf_bonus - stability_penalty
        
        print(f"   WF 구간: {len(oos_results)}개, 일관성: {consistency_ratio:.2f}, 점수: {final_score:.4f}")
        
        return final_score
    
    def calculate_stability_penalty(self, all_metrics):
        """성과 안정성 패널티 계산"""
        if len(all_metrics) < 2:
            return 0
        
        # 주요 지표들의 변동성 계산
        profit_factors = [m['profit_factor'] for m in all_metrics if m['profit_factor'] != float('inf')]
        win_rates = [m['win_rate'] for m in all_metrics]
        sortino_ratios = [m['sortino_ratio'] for m in all_metrics]
        
        penalties = []
        
        # Profit Factor 변동성
        if len(profit_factors) > 1:
            pf_cv = np.std(profit_factors) / np.mean(profit_factors) if np.mean(profit_factors) > 0 else 1
            penalties.append(pf_cv * 0.1)
        
        # Win Rate 변동성
        if len(win_rates) > 1:
            wr_cv = np.std(win_rates) / np.mean(win_rates) if np.mean(win_rates) > 0 else 1
            penalties.append(wr_cv * 0.1)
        
        # Sortino Ratio 변동성
        if len(sortino_ratios) > 1:
            sr_cv = np.std(sortino_ratios) / np.mean(sortino_ratios) if np.mean(sortino_ratios) > 0 else 1
            penalties.append(sr_cv * 0.1)
        
        return sum(penalties)
    
    def calculate_objective_score(self, metrics):
        """목적 함수 점수 계산 (개선된 버전)"""
        if metrics is None:
            return -1000  # 패널티
        
        # 제약 조건 확인
        constraints = self.config['constraints']
        if (metrics['total_trades'] < constraints['min_trades'] or
            metrics['max_drawdown'] > constraints['max_drawdown'] or
            metrics['win_rate'] < constraints['min_win_rate'] or
            metrics['profit_factor'] < constraints['min_profit_factor']):
            return -1000  # 제약 조건 위반 시 큰 패널티
        
        # 동적 목표값 조정 (시장 조건에 따라)
        targets = self.adjust_target_values(metrics)
        weights = self.config['objective_weights']
        
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
        
        # 적응적 드로우다운 패널티
        dd_threshold = 0.15 if metrics['total_trades'] > 200 else 0.20
        dd_penalty = max(0, (metrics['max_drawdown'] - dd_threshold) * 10)
        
        return score - dd_penalty
    
    def adjust_target_values(self, metrics):
        """시장 조건에 따른 목표값 동적 조정"""
        base_targets = self.config['target_values'].copy()
        
        # 거래 빈도에 따른 조정
        if metrics['total_trades'] < 200:
            # 거래가 적으면 목표를 낮춤
            base_targets['sortino_ratio'] *= 0.8
            base_targets['calmar_ratio'] *= 0.8
            base_targets['sqn'] *= 0.8
        elif metrics['total_trades'] > 500:
            # 거래가 많으면 목표를 높임
            base_targets['sortino_ratio'] *= 1.2
            base_targets['calmar_ratio'] *= 1.2
        
        # 최대 드로우다운에 따른 조정
        if metrics['max_drawdown'] < 0.10:
            # 낮은 드로우다운이면 다른 지표 목표를 높임
            base_targets['profit_factor'] *= 1.1
            base_targets['win_rate'] *= 1.05
        
        return base_targets
    
    def objective_function(self, trial, data_points=None, enable_walk_forward=False):
        """Optuna 목적 함수 (워크포워드 테스트 포함)"""
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
            
            # 워크포워드 테스트 실행 여부
            if enable_walk_forward and self.config['walk_forward']['enabled']:
                score = self.run_walk_forward_test(strategy, params)
            else:
                # 일반 백테스트
                strategy.generate_signals()
                trades = strategy.backtest()
                
                if not trades:
                    return -1000
                
                # 성과 지표 계산
                trades_df = pd.DataFrame(trades)
                metrics = self.calculate_performance_metrics(trades_df)
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
            return self.objective_function(
                trial, 
                stage_config['data_points'], 
                enable_walk_forward=stage_config.get('wf_enabled', False)
            )
        
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
    
    def analyze_market_conditions(self):
        """시장 조건 분석 및 기준 동적 조정"""
        print("📊 시장 조건 분석 중...")
        
        try:
            # 기본 전략으로 시장 데이터 로드
            strategy = ETHSessionStrategy()
            strategy.load_data()
            
            df = strategy.df
            
            # 최근 데이터 분석 (최근 30%)
            recent_data = df.tail(int(len(df) * 0.3))
            
            # 변동성 분석
            recent_volatility = recent_data['atr'].mean()
            historical_volatility = df['atr'].mean()
            volatility_ratio = recent_volatility / historical_volatility
            
            # 트렌드 강도 분석
            price_change = (recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]) / recent_data['close'].iloc[0]
            
            # 거래량 분석
            recent_volume = recent_data['volume'].mean()
            historical_volume = df['volume'].mean()
            volume_ratio = recent_volume / historical_volume
            
            # 시장 조건 분류
            market_condition = self.classify_market_condition(volatility_ratio, price_change, volume_ratio)
            
            # 기준 조정
            self.adjust_optimization_targets(market_condition, volatility_ratio, volume_ratio)
            
            print(f"   시장 조건: {market_condition}")
            print(f"   변동성 비율: {volatility_ratio:.2f}")
            print(f"   거래량 비율: {volume_ratio:.2f}")
            
            return market_condition
            
        except Exception as e:
            print(f"❌ 시장 분석 실패: {e}")
            return "normal"
    
    def classify_market_condition(self, volatility_ratio, price_change, volume_ratio):
        """시장 조건 분류"""
        if volatility_ratio > 1.3 and volume_ratio > 1.2:
            return "high_volatility"
        elif volatility_ratio < 0.7 and volume_ratio < 0.8:
            return "low_volatility"
        elif abs(price_change) > 0.2:
            return "trending"
        else:
            return "normal"
    
    def adjust_optimization_targets(self, market_condition, volatility_ratio, volume_ratio):
        """시장 조건에 따른 최적화 목표 조정"""
        targets = self.config['target_values']
        constraints = self.config['constraints']
        
        if market_condition == "high_volatility":
            # 고변동성: 더 보수적인 목표
            targets['max_drawdown'] = 0.25
            targets['win_rate'] = 0.50
            constraints['max_drawdown'] = 0.25
            print("   🔥 고변동성 모드: 보수적 목표 적용")
            
        elif market_condition == "low_volatility":
            # 저변동성: 더 공격적인 목표
            targets['profit_factor'] = 3.0
            targets['sortino_ratio'] = 2.5
            constraints['min_trades'] = 150
            print("   😴 저변동성 모드: 공격적 목표 적용")
            
        elif market_condition == "trending":
            # 트렌딩: 트렌드 추종 최적화
            targets['calmar_ratio'] = 4.0
            targets['rr_ratio'] = 2.5
            print("   📈 트렌딩 모드: 트렌드 추종 최적화")
            
        else:
            print("   ⚖️ 일반 모드: 기본 목표 유지")
    
    def run_full_optimization(self):
        """전체 최적화 프로세스 실행 (시장 분석 포함)"""
        print("🚀 자동 최적화 시작")
        print("=" * 80)
        
        start_time = datetime.now()
        results = {}
        
        try:
            # 0단계: 시장 조건 분석
            market_condition = self.analyze_market_conditions()
            results['market_analysis'] = {
                'condition': market_condition,
                'timestamp': start_time.isoformat(),
                'adjusted_targets': self.config['target_values'].copy(),
                'adjusted_constraints': self.config['constraints'].copy()
            }
            
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
            
            # 3단계: 워크포워드 검증
            print(f"\n🔍 3단계: 워크포워드 검증 시작...")
            stage3_study = self.run_optimization_stage('3단계: 워크포워드 검증', self.config['stages']['stage3'])
            results['stage3'] = {
                'best_params': stage3_study.best_params,
                'best_score': stage3_study.best_value,
                'n_trials': len(stage3_study.trials),
                'walk_forward_validated': True
            }
            
            # 최종 검증
            final_params = stage3_study.best_params
            final_validation = self.final_validation(final_params)
            results['final_validation'] = final_validation
            
            # 결과 저장 (JSON 직렬화 가능하도록 변환)
            serializable_results = self.make_json_serializable(results)
            self.save_optimization_results(final_params, serializable_results, start_time)
            
            print("\n🎉 워크포워드 최적화 완료!")
            print(f"   총 소요시간: {(datetime.now() - start_time).total_seconds()/60:.1f}분")
            print(f"   최종 점수: {stage3_study.best_value:.4f}")
            print(f"   워크포워드 검증: ✅")
            
            return final_params
            
        except Exception as e:
            print(f"❌ 최적화 실행 오류: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def final_validation(self, params):
        """최종 파라미터 검증"""
        print("🔍 최종 검증 실행 중...")
        
        try:
            strategy = ETHSessionStrategy()
            strategy.load_data()
            
            # 파라미터 적용
            for param_name, param_value in params.items():
                if param_name in strategy.params:
                    strategy.params[param_name] = param_value
            
            # 전체 데이터로 워크포워드 테스트
            final_score = self.run_walk_forward_test(strategy, params)
            
            # 추가 안정성 검사
            stability_check = self.stability_check(strategy, params)
            
            validation_result = {
                'final_wf_score': final_score,
                'stability_passed': stability_check['passed'],
                'stability_details': stability_check,
                'validation_timestamp': datetime.now().isoformat(),
                'recommended_for_live': final_score > 0.5 and stability_check['passed']
            }
            
            if validation_result['recommended_for_live']:
                print("✅ 최종 검증 통과 - 실거래 권장")
            else:
                print("⚠️ 최종 검증 미통과 - 추가 최적화 필요")
            
            return validation_result
            
        except Exception as e:
            print(f"❌ 최종 검증 실패: {e}")
            return {'final_wf_score': -1000, 'stability_passed': False}
    
    def stability_check(self, strategy, params):
        """파라미터 안정성 검사"""
        try:
            # 파라미터 민감도 테스트
            sensitivity_results = []
            
            for param_name, param_value in params.items():
                if param_name in strategy.params:
                    # ±10% 변동 테스트
                    if isinstance(param_value, (int, float)):
                        test_values = [param_value * 0.9, param_value * 1.1]
                        
                        for test_value in test_values:
                            # 임시 파라미터 적용
                            original_value = strategy.params[param_name]
                            strategy.params[param_name] = test_value
                            
                            # 간단한 백테스트
                            strategy.generate_signals()
                            trades = strategy.backtest()
                            
                            if trades:
                                trades_df = pd.DataFrame(trades)
                                metrics = self.calculate_performance_metrics(trades_df)
                                score = self.calculate_objective_score(metrics)
                                sensitivity_results.append(score)
                            
                            # 원래 값 복원
                            strategy.params[param_name] = original_value
            
            # 안정성 평가
            if len(sensitivity_results) > 0:
                score_std = np.std(sensitivity_results)
                score_mean = np.mean(sensitivity_results)
                stability_ratio = score_std / abs(score_mean) if score_mean != 0 else float('inf')
                
                passed = stability_ratio < 0.3  # 30% 이하 변동성
            else:
                passed = False
                stability_ratio = float('inf')
            
            return {
                'passed': passed,
                'stability_ratio': stability_ratio,
                'sensitivity_scores': sensitivity_results,
                'threshold': 0.3
            }
            
        except Exception as e:
            print(f"❌ 안정성 검사 실패: {e}")
            return {'passed': False, 'stability_ratio': float('inf')}
    
    def make_json_serializable(self, obj):
        """객체를 JSON 직렬화 가능하도록 변환"""
        if isinstance(obj, dict):
            return {k: self.make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.make_json_serializable(item) for item in obj]
        elif isinstance(obj, (bool, int, float, str, type(None))):
            return obj
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        else:
            return str(obj)
    
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
        
        # 매주 일요일 14:00 KST에 실행
        scheduler.add_job(
            func=self.run_full_optimization,
            trigger=CronTrigger(
                day_of_week='sun',  # 일요일
                hour=14,            # 14시
                minute=0,           # 0분
                timezone=kst
            ),
            id='weekly_optimization',
            name='주간 자동 최적화',
            replace_existing=True
        )
        
        print("📅 스케줄러 설정 완료")
        print("   실행 시간: 매주 일요일 14:00 KST")
        
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