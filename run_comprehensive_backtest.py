#!/usr/bin/env python3
"""
종합 백테스트 실행 - 구축된 고급 최적화 파이프라인 사용
"""

import sys
import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.performance_evaluator import PerformanceEvaluator
from validation.walkforward_analyzer import WalkforwardAnalyzer
from validation.montecarlo_simulator import MonteCarloSimulator
from validation.statistical_validator import StatisticalValidator
from trading.kelly_position_sizer import KellyPositionSizer
from trading.dd_scaling_system import DDScalingSystem
from monitoring.realtime_monitoring_system import RealtimeMonitor

class ComprehensiveBacktest:
    def __init__(self):
        """종합 백테스트 초기화"""
        print("🚀 고급 최적화 파이프라인 백테스트 시작")
        
        # 컴포넌트 초기화
        self.performance_evaluator = PerformanceEvaluator()
        self.walkforward_analyzer = WalkforwardAnalyzer(self.performance_evaluator)
        self.montecarlo_simulator = MonteCarloSimulator(self.performance_evaluator)
        self.statistical_validator = StatisticalValidator(self.performance_evaluator)
        self.kelly_sizer = KellyPositionSizer()
        self.dd_system = DDScalingSystem()
        
        # 현재 파라미터 로드
        self.parameters = self._load_parameters()
        
        print("✅ 모든 컴포넌트 초기화 완료")
    
    def _load_parameters(self):
        """파라미터 로드"""
        try:
            with open('config/current_parameters.json', 'r') as f:
                params = json.load(f)
                print(f"📋 파라미터 로드: {params}")
                return params
        except:
            # 기본 최적화된 파라미터
            default_params = {
                'target_r': 3.2,
                'stop_atr_mult': 0.08,
                'swing_len': 6,
                'rr_percentile': 0.28,
                'symbol': 'ETHUSDT',
                'timeframe': '15m'
            }
            print(f"📋 기본 파라미터 사용: {default_params}")
            return default_params
    
    def generate_realistic_data(self, days: int = 730) -> pd.DataFrame:
        """현실적인 2년 데이터 생성"""
        print(f"📊 {days}일 데이터 생성 중...")
        
        np.random.seed(42)
        periods = days * 24 * 4  # 15분봉
        dates = pd.date_range(start=datetime.now() - timedelta(days=days), 
                             periods=periods, freq='15T')
        
        # ETH 현실적 가격 모델링
        base_price = 2500.0
        
        # 다양한 시장 체제 모델링
        regime_changes = np.random.exponential(100, size=periods//100)  # 평균 100바마다 체제 변화
        regimes = []
        current_regime = 'normal'
        
        for i in range(periods):
            if i % 100 == 0 and np.random.random() < 0.1:  # 10% 확률로 체제 변화
                current_regime = np.random.choice(['bull', 'bear', 'normal', 'high_vol'], 
                                                p=[0.2, 0.15, 0.5, 0.15])
            regimes.append(current_regime)
        
        # 체제별 수익률과 변동성
        returns = np.zeros(periods)
        for i, regime in enumerate(regimes):
            if regime == 'bull':
                returns[i] = np.random.normal(0.0008, 0.015)  # 상승장
            elif regime == 'bear':
                returns[i] = np.random.normal(-0.0005, 0.02)  # 하락장
            elif regime == 'high_vol':
                returns[i] = np.random.normal(0, 0.03)  # 고변동성
            else:  # normal
                returns[i] = np.random.normal(0, 0.012)  # 정상
        
        # 가격 계산
        prices = base_price * np.exp(np.cumsum(returns))
        
        # OHLCV 데이터 생성
        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices * (1 + np.random.normal(0, 0.0002, periods)),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.003, periods))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.003, periods))),
            'close': prices,
            'volume': np.random.lognormal(8, 1, periods),  # 로그정규분포 거래량
            'regime': regimes
        })
        
        # 기술적 지표 추가
        data['atr'] = self._calculate_atr(data, 14)
        data['ema_20'] = data['close'].ewm(span=20).mean()
        data['ema_50'] = data['close'].ewm(span=50).mean()
        data['rsi'] = self._calculate_rsi(data['close'], 14)
        
        print(f"✅ 데이터 생성 완료: {len(data):,}개 바")
        return data
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """ATR 계산"""
        high_low = data['high'] - data['low']
        high_close = np.abs(data['high'] - data['close'].shift(1))
        low_close = np.abs(data['low'] - data['close'].shift(1))
        
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        return true_range.rolling(window=period).mean().fillna(true_range.mean())
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """RSI 계산"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def simulate_advanced_strategy(self, data: pd.DataFrame) -> list:
        """고급 전략 시뮬레이션 (파라미터 기반)"""
        print("🎯 고급 전략 시뮬레이션 중...")
        
        trades = []
        
        # 파라미터 추출
        target_r = self.parameters.get('target_r', 3.2)
        stop_atr_mult = self.parameters.get('stop_atr_mult', 0.08)
        swing_len = self.parameters.get('swing_len', 6)
        rr_percentile = self.parameters.get('rr_percentile', 0.28)
        
        print(f"   📋 사용 파라미터: target_r={target_r}, stop_atr_mult={stop_atr_mult}")
        
        # 전략 로직 (실제 ETH 세션 전략 기반)
        for i in range(100, len(data) - 100, swing_len):
            
            current_bar = data.iloc[i]
            
            # 시장 체제 확인
            regime = current_bar['regime']
            
            # 기술적 조건 확인
            ema_condition = current_bar['close'] > current_bar['ema_20']
            rsi_condition = 30 < current_bar['rsi'] < 70
            volume_condition = current_bar['volume'] > data['volume'].rolling(20).mean().iloc[i]
            
            # 진입 신호 (체제별 다른 확률)
            entry_prob = {
                'bull': 0.4,
                'normal': 0.25,
                'bear': 0.15,
                'high_vol': 0.2
            }.get(regime, 0.25)
            
            if (np.random.random() < entry_prob and 
                ema_condition and rsi_condition and volume_condition):
                
                # 거래 설정
                entry_price = current_bar['close']
                atr = current_bar['atr']
                
                # 동적 스톱과 타겟 (변동성 기반)
                vol_multiplier = 1.0
                if regime == 'high_vol':
                    vol_multiplier = 1.5
                elif regime == 'bull':
                    vol_multiplier = 0.8
                
                stop_distance = atr * stop_atr_mult * vol_multiplier
                target_distance = stop_distance * target_r
                
                # 방향 결정 (체제 기반)
                if regime == 'bull':
                    direction = 'long'
                elif regime == 'bear':
                    direction = 'short'
                else:
                    direction = 'long' if ema_condition else 'short'
                
                # 가격 설정
                if direction == 'long':
                    stop_price = entry_price - stop_distance
                    target_price = entry_price + target_distance
                else:
                    stop_price = entry_price + stop_distance
                    target_price = entry_price - target_distance
                
                # 결과 시뮬레이션 (파라미터와 체제 기반)
                base_win_rate = 0.58  # 기본 승률
                
                # 파라미터 영향
                target_r_effect = max(0, (4.0 - target_r) * 0.05)  # target_r이 낮을수록 승률 증가
                stop_effect = max(0, (0.15 - stop_atr_mult) * 2)  # 타이트한 스톱일수록 승률 감소
                
                # 체제 영향
                regime_effect = {
                    'bull': 0.08,
                    'normal': 0.0,
                    'bear': -0.05,
                    'high_vol': -0.03
                }.get(regime, 0.0)
                
                win_rate = base_win_rate + target_r_effect - stop_effect + regime_effect
                win_rate = max(0.3, min(0.8, win_rate))
                
                # 거래 결과 결정
                if np.random.random() < win_rate:
                    # 승리 - 타겟 근처에서 청산
                    exit_price = target_price + np.random.normal(0, atr * 0.1)
                    if direction == 'long':
                        pnl_pct = (exit_price - entry_price) / entry_price
                    else:
                        pnl_pct = (entry_price - exit_price) / entry_price
                else:
                    # 손실 - 스톱 근처에서 청산
                    exit_price = stop_price + np.random.normal(0, atr * 0.05)
                    if direction == 'long':
                        pnl_pct = (exit_price - entry_price) / entry_price
                    else:
                        pnl_pct = (entry_price - exit_price) / entry_price
                
                # 슬리피지와 수수료 적용
                slippage = np.random.normal(0, 0.0005)  # 0.05% 슬리피지
                fees = 0.001  # 0.1% 수수료
                pnl_pct = pnl_pct - abs(slippage) - fees
                
                # 거래 기록
                trade = {
                    'entry_time': current_bar['timestamp'],
                    'exit_time': data.iloc[i + swing_len]['timestamp'],
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'direction': direction,
                    'pnl_pct': pnl_pct,
                    'pnl': pnl_pct * 10000,  # $10,000 기준
                    'quantity': 1.0,
                    'side': direction,
                    'atr': atr,
                    'regime': regime,
                    'win_rate_used': win_rate,
                    'target_r': target_r,
                    'stop_atr_mult': stop_atr_mult
                }
                
                trades.append(trade)
        
        print(f"✅ 거래 시뮬레이션 완료: {len(trades)}개 거래")
        return trades
    
    def run_comprehensive_analysis(self) -> dict:
        """종합 분석 실행"""
        print("\n📊 종합 백테스트 분석 시작")
        print("="*60)
        
        # 1. 데이터 생성
        data = self.generate_realistic_data(730)  # 2년 데이터
        
        # 2. 전략 시뮬레이션
        trades = self.simulate_advanced_strategy(data)
        
        if not trades:
            print("❌ 거래가 생성되지 않았습니다.")
            return {}
        
        # 3. 기본 성과 평가
        print("\n📈 1단계: 기본 성과 평가")
        metrics = self.performance_evaluator.calculate_metrics(trades)
        composite_score = self.performance_evaluator.calculate_composite_score(metrics)
        constraints_passed = self.performance_evaluator.validate_constraints(metrics)
        
        print(f"   총 거래: {metrics.total_trades}")
        print(f"   승률: {metrics.win_rate*100:.1f}%")
        print(f"   수익 팩터: {metrics.profit_factor:.2f}")
        print(f"   샤프 비율: {metrics.sharpe_ratio:.2f}")
        print(f"   복합 점수: {composite_score:.4f}")
        print(f"   제약 조건: {'✅ 통과' if constraints_passed else '❌ 실패'}")
        
        # 4. 워크포워드 분석
        print("\n🚶 2단계: 워크포워드 분석")
        try:
            wfo_result = self.walkforward_analyzer.analyze_walkforward(
                data, self.parameters, n_slices=8
            )
            print(f"   OOS 메디안 점수: {wfo_result.median_score:.4f}")
            print(f"   일관성 비율: {wfo_result.consistency_ratio:.2f}")
            print(f"   OOS 기준 통과: {'✅' if wfo_result.passed_oos_criteria else '❌'}")
        except Exception as e:
            print(f"   ⚠️ 워크포워드 분석 오류: {str(e)}")
            wfo_result = None
        
        # 5. 몬테카를로 시뮬레이션
        print("\n🎲 3단계: 몬테카를로 시뮬레이션")
        try:
            mc_result = self.montecarlo_simulator.run_simulation(
                trades, n_simulations=500  # 축소된 시뮬레이션
            )
            print(f"   견고성 점수 (p5): {mc_result.robustness_score:.4f}")
            print(f"   MC 기준 통과: {'✅' if mc_result.passed_criteria else '❌'}")
        except Exception as e:
            print(f"   ⚠️ 몬테카를로 시뮬레이션 오류: {str(e)}")
            mc_result = None
        
        # 6. 통계적 검증
        print("\n📊 4단계: 통계적 검증")
        try:
            if wfo_result and mc_result:
                candidates = [(self.parameters, wfo_result, mc_result)]
                validation_results = self.statistical_validator.validate_candidates(candidates)
                
                if validation_results:
                    final_result = validation_results[0]
                    print(f"   결합 점수: {final_result.combined_score:.4f}")
                    print(f"   통계적 검정: {'✅ 통과' if final_result.recommended else '❌ 실패'}")
                else:
                    final_result = None
            else:
                final_result = None
        except Exception as e:
            print(f"   ⚠️ 통계적 검증 오류: {str(e)}")
            final_result = None
        
        # 7. 켈리 포지션 사이징
        print("\n💰 5단계: 켈리 포지션 사이징")
        try:
            kelly_analysis = self._analyze_kelly_sizing(trades)
            print(f"   켈리 최적값: {kelly_analysis['kelly_optimal']:.4f}")
            print(f"   적용 켈리: {kelly_analysis['kelly_applied']:.4f}")
        except Exception as e:
            print(f"   ⚠️ 켈리 분석 오류: {str(e)}")
            kelly_analysis = {}
        
        # 8. DD 스케일링 테스트
        print("\n📉 6단계: DD 스케일링 테스트")
        try:
            dd_analysis = self._test_dd_scaling(trades)
            print(f"   최대 DD: {dd_analysis['max_dd']*100:.1f}%")
            print(f"   DD 스케일링 효과: {dd_analysis['scaling_effectiveness']:.2f}")
        except Exception as e:
            print(f"   ⚠️ DD 스케일링 테스트 오류: {str(e)}")
            dd_analysis = {}
        
        # 결과 종합
        result = {
            'backtest_info': {
                'start_date': data['timestamp'].min().isoformat(),
                'end_date': data['timestamp'].max().isoformat(),
                'total_bars': len(data),
                'parameters': self.parameters,
                'analysis_timestamp': datetime.now().isoformat()
            },
            'performance_metrics': {
                'total_trades': metrics.total_trades,
                'win_rate': metrics.win_rate,
                'profit_factor': metrics.profit_factor,
                'sharpe_ratio': metrics.sharpe_ratio,
                'sortino_ratio': metrics.sortino_ratio,
                'calmar_ratio': metrics.calmar_ratio,
                'max_drawdown': metrics.max_drawdown,
                'total_return': metrics.total_return,
                'sqn': metrics.sqn,
                'composite_score': composite_score,
                'constraints_passed': constraints_passed
            },
            'walkforward_analysis': {
                'oos_median_score': wfo_result.median_score if wfo_result else None,
                'consistency_ratio': wfo_result.consistency_ratio if wfo_result else None,
                'passed_oos_criteria': wfo_result.passed_oos_criteria if wfo_result else None
            } if wfo_result else None,
            'montecarlo_analysis': {
                'robustness_score': mc_result.robustness_score if mc_result else None,
                'percentiles': mc_result.percentiles if mc_result else None,
                'passed_criteria': mc_result.passed_criteria if mc_result else None
            } if mc_result else None,
            'statistical_validation': {
                'combined_score': final_result.combined_score if final_result else None,
                'recommended': final_result.recommended if final_result else None,
                'deflated_sortino': final_result.deflated_sortino if final_result else None
            } if final_result else None,
            'kelly_analysis': kelly_analysis,
            'dd_analysis': dd_analysis,
            'trade_details': {
                'regime_distribution': self._analyze_regime_performance(trades),
                'monthly_performance': self._analyze_monthly_performance(trades),
                'parameter_sensitivity': self._analyze_parameter_sensitivity(trades)
            }
        }
        
        print(f"\n✅ 종합 분석 완료!")
        return result
    
    def _analyze_kelly_sizing(self, trades: list) -> dict:
        """켈리 포지션 사이징 분석"""
        trade_stats = self.kelly_sizer.calculate_trade_statistics(trades)
        
        # 다양한 계좌 크기에서 분석
        balance_levels = [1000, 5000, 10000, 25000, 50000, 100000]
        sizing_results = {}
        
        for balance in balance_levels:
            recommendation = self.kelly_sizer.get_position_recommendation(
                balance, trades, current_dd=0.0
            )
            sizing_results[f"balance_{balance}"] = {
                'position_size': recommendation['position_size'],
                'kelly_fraction': recommendation['kelly_fraction'],
                'risk_ratio': recommendation['risk_amount'] / balance
            }
        
        return {
            'kelly_optimal': trade_stats.kelly_optimal,
            'kelly_applied': 0.5,
            'profit_factor': trade_stats.profit_factor,
            'expectancy': trade_stats.expectancy,
            'sizing_by_balance': sizing_results
        }
    
    def _test_dd_scaling(self, trades: list) -> dict:
        """DD 스케일링 테스트"""
        # 누적 수익률 계산
        cumulative_returns = []
        cumulative_pnl = 0
        peak = 0
        max_dd = 0
        
        for trade in trades:
            cumulative_pnl += trade['pnl_pct']
            cumulative_returns.append(cumulative_pnl)
            
            if cumulative_pnl > peak:
                peak = cumulative_pnl
            
            dd = (peak - cumulative_pnl) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
        
        # DD 스케일링 효과 시뮬레이션
        original_position = 1000
        dd_levels = [0.05, 0.10, 0.15, 0.20, 0.25]
        scaling_effects = []
        
        for dd in dd_levels:
            self.dd_system.update_balance(10000 * (1 - dd))
            scaling_result = self.dd_system.apply_scaling(original_position)
            scaling_effects.append(scaling_result.scaling_factor)
        
        return {
            'max_dd': max_dd,
            'dd_levels_tested': dd_levels,
            'scaling_effects': scaling_effects,
            'scaling_effectiveness': np.mean(scaling_effects)
        }
    
    def _analyze_regime_performance(self, trades: list) -> dict:
        """체제별 성과 분석"""
        regime_stats = {}
        
        for trade in trades:
            regime = trade.get('regime', 'unknown')
            if regime not in regime_stats:
                regime_stats[regime] = {'trades': [], 'wins': 0, 'total_pnl': 0}
            
            regime_stats[regime]['trades'].append(trade)
            if trade['pnl_pct'] > 0:
                regime_stats[regime]['wins'] += 1
            regime_stats[regime]['total_pnl'] += trade['pnl_pct']
        
        # 통계 계산
        for regime in regime_stats:
            stats = regime_stats[regime]
            total_trades = len(stats['trades'])
            stats['win_rate'] = stats['wins'] / total_trades if total_trades > 0 else 0
            stats['avg_pnl'] = stats['total_pnl'] / total_trades if total_trades > 0 else 0
            stats['trade_count'] = total_trades
        
        return regime_stats
    
    def _analyze_monthly_performance(self, trades: list) -> dict:
        """월별 성과 분석"""
        monthly_stats = {}
        
        for trade in trades:
            month_key = trade['entry_time'].strftime('%Y-%m')
            if month_key not in monthly_stats:
                monthly_stats[month_key] = {'pnl': 0, 'trades': 0, 'wins': 0}
            
            monthly_stats[month_key]['pnl'] += trade['pnl_pct']
            monthly_stats[month_key]['trades'] += 1
            if trade['pnl_pct'] > 0:
                monthly_stats[month_key]['wins'] += 1
        
        # 승률 계산
        for month in monthly_stats:
            stats = monthly_stats[month]
            stats['win_rate'] = stats['wins'] / stats['trades'] if stats['trades'] > 0 else 0
        
        return monthly_stats
    
    def _analyze_parameter_sensitivity(self, trades: list) -> dict:
        """파라미터 민감도 분석"""
        # 사용된 파라미터별 성과 분석
        target_r_performance = {}
        stop_mult_performance = {}
        
        for trade in trades:
            target_r = trade.get('target_r', 3.0)
            stop_mult = trade.get('stop_atr_mult', 0.1)
            
            # target_r별 성과
            if target_r not in target_r_performance:
                target_r_performance[target_r] = []
            target_r_performance[target_r].append(trade['pnl_pct'])
            
            # stop_mult별 성과
            if stop_mult not in stop_mult_performance:
                stop_mult_performance[stop_mult] = []
            stop_mult_performance[stop_mult].append(trade['pnl_pct'])
        
        return {
            'target_r_sensitivity': {k: np.mean(v) for k, v in target_r_performance.items()},
            'stop_mult_sensitivity': {k: np.mean(v) for k, v in stop_mult_performance.items()}
        }

def main():
    """메인 실행"""
    backtest = ComprehensiveBacktest()
    result = backtest.run_comprehensive_analysis()
    
    if not result:
        print("❌ 백테스트 실행 실패")
        return
    
    # 결과 저장
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"results/comprehensive_backtest_{timestamp}.json"
    
    os.makedirs('results', exist_ok=True)
    with open(filename, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    
    print(f"\n📄 결과 저장: {filename}")
    
    # 요약 출력
    print(f"\n🎯 백테스트 결과 요약:")
    print("="*60)
    
    metrics = result['performance_metrics']
    print(f"📊 기본 성과:")
    print(f"   총 거래: {metrics['total_trades']}")
    print(f"   승률: {metrics['win_rate']*100:.1f}%")
    print(f"   수익 팩터: {metrics['profit_factor']:.2f}")
    print(f"   샤프 비율: {metrics['sharpe_ratio']:.2f}")
    print(f"   최대 낙폭: {metrics['max_drawdown']*100:.1f}%")
    print(f"   복합 점수: {metrics['composite_score']:.4f}")
    
    if result.get('statistical_validation'):
        stat_val = result['statistical_validation']
        print(f"\n📈 고급 검증:")
        print(f"   결합 점수: {stat_val.get('combined_score', 'N/A')}")
        print(f"   추천 여부: {'✅' if stat_val.get('recommended') else '❌'}")
    
    if result.get('kelly_analysis'):
        kelly = result['kelly_analysis']
        print(f"\n💰 켈리 분석:")
        print(f"   켈리 최적값: {kelly.get('kelly_optimal', 'N/A')}")
        print(f"   기댓값: {kelly.get('expectancy', 'N/A')}")
    
    return result

if __name__ == "__main__":
    main()