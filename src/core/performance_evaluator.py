#!/usr/bin/env python3
"""
성과 평가 및 제약 시스템
- Score = 0.35·Sortino + 0.25·Calmar + 0.20·PF + 0.20·SQN − λ·MaxDD
- 제약 조건 검증 (PF≥1.8, Sortino≥1.5, etc.)
- 메디안 기반 집계 및 IQR 우선순위
- DD 패널티 λ=0.5~1.0 적용
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

@dataclass
class PerformanceMetrics:
    """성과 지표 데이터 클래스"""
    total_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown: float
    sortino_ratio: float
    sharpe_ratio: float
    calmar_ratio: float
    sqn: float
    rr_ratio: float
    expectancy: float
    mar_ratio: float
    total_return: float
    annual_return: float
    volatility: float
    avg_win: float
    avg_loss: float

@dataclass
class ConstraintConfig:
    """제약 조건 설정 - 이상적 기준"""
    min_trades: int = 200
    max_drawdown: float = 0.20  # ≤20% (이상적)
    min_win_rate: float = 0.45  # 45%-65%
    max_win_rate: float = 0.65  # 45%-65%
    min_profit_factor: float = 2.0  # ≥2.0-3.0+
    min_rr_ratio: float = 2.0  # ≥2.0
    min_expectancy: float = 0.3  # ≥+0.3R
    min_sortino_ratio: float = 2.0  # ≥2.0
    min_sharpe_ratio: float = 1.5  # ≥1.5
    min_calmar_ratio: float = 3.0  # ≥3.0
    min_mar_ratio: float = 2.5  # ≥2.5
    min_sqn: float = 3.0  # ≥3.0-5.0+
    min_r_exp_var_ratio: float = 1.5  # ≥1.5

@dataclass
class ScoreConfig:
    """점수 계산 설정"""
    # 가중치
    sortino_weight: float = 0.35
    calmar_weight: float = 0.25
    profit_factor_weight: float = 0.20
    sqn_weight: float = 0.20
    
    # DD 패널티
    dd_penalty_lambda: float = 1.0
    dd_threshold: float = 0.15  # 15% 초과시 패널티
    
    # 목표값 (정규화용)
    target_sortino: float = 2.0
    target_calmar: float = 3.0
    target_profit_factor: float = 2.0
    target_sqn: float = 3.0

class PerformanceEvaluator:
    def __init__(self, constraint_config: ConstraintConfig = None, 
                 score_config: ScoreConfig = None):
        """성과 평가자 초기화"""
        self.constraints = constraint_config or ConstraintConfig()
        self.score_config = score_config or ScoreConfig()
        
        print("📊 성과 평가 시스템 초기화")
        print(f"   제약 조건: PF≥{self.constraints.min_profit_factor}, Sortino≥{self.constraints.min_sortino_ratio}")
        print(f"   점수 가중치: Sortino({self.score_config.sortino_weight}), Calmar({self.score_config.calmar_weight})")
    
    def calculate_metrics(self, trades_df: pd.DataFrame, 
                         initial_balance: float = 100000) -> PerformanceMetrics:
        """성과 지표 계산"""
        if len(trades_df) == 0:
            return self._empty_metrics()
        
        # 기본 통계
        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df['pnl'] > 0])
        losing_trades = len(trades_df[trades_df['pnl'] < 0])
        
        if total_trades == 0:
            return self._empty_metrics()
        
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
        equity_curve = cumulative_returns + initial_balance
        peak = np.maximum.accumulate(equity_curve)
        drawdown = (equity_curve - peak) / peak
        max_drawdown = abs(drawdown.min()) if len(drawdown) > 0 else 0
        
        # 수익률 통계
        mean_return = np.mean(returns)
        volatility = np.std(returns) if len(returns) > 1 else 0.001
        
        # Sortino Ratio (하방 편차 기준)
        negative_returns = returns[returns < 0]
        downside_deviation = np.std(negative_returns) if len(negative_returns) > 0 else 0.001
        sortino_ratio = mean_return / downside_deviation if downside_deviation > 0 else 0
        
        # Sharpe Ratio
        risk_free_rate = 0.05 / 365  # 연 5% 일간 환산
        excess_return = mean_return - risk_free_rate
        sharpe_ratio = excess_return / volatility if volatility > 0 else 0
        
        # Calmar Ratio
        total_return = cumulative_returns[-1] if len(cumulative_returns) > 0 else 0
        annual_return = (total_return / initial_balance) * (365 / len(trades_df)) if len(trades_df) > 0 else 0
        calmar_ratio = annual_return / max_drawdown if max_drawdown > 0 else 0
        
        # System Quality Number (SQN)
        sqn = (mean_return / volatility) * np.sqrt(total_trades) if volatility > 0 else 0
        
        # Reward:Risk Ratio
        rr_ratio = abs(avg_win / avg_loss) if avg_loss < 0 else 0
        
        # Expectancy
        expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
        expectancy_r = expectancy / abs(avg_loss) if avg_loss != 0 else 0
        
        # MAR Ratio
        mar_ratio = annual_return / max_drawdown if max_drawdown > 0 else 0
        
        return PerformanceMetrics(
            total_trades=total_trades,
            win_rate=win_rate,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            sortino_ratio=sortino_ratio,
            sharpe_ratio=sharpe_ratio,
            calmar_ratio=calmar_ratio,
            sqn=sqn,
            rr_ratio=rr_ratio,
            expectancy=expectancy_r,
            mar_ratio=mar_ratio,
            total_return=total_return,
            annual_return=annual_return,
            volatility=volatility,
            avg_win=avg_win,
            avg_loss=avg_loss
        )
    
    def _empty_metrics(self) -> PerformanceMetrics:
        """빈 메트릭 반환"""
        return PerformanceMetrics(
            total_trades=0, win_rate=0, profit_factor=0, max_drawdown=1.0,
            sortino_ratio=0, sharpe_ratio=0, calmar_ratio=0, sqn=0,
            rr_ratio=0, expectancy=0, mar_ratio=0, total_return=0,
            annual_return=0, volatility=0, avg_win=0, avg_loss=0
        )
    
    def check_constraints(self, metrics: PerformanceMetrics) -> Tuple[bool, List[str]]:
        """제약 조건 확인"""
        violations = []
        
        # 기본 제약 조건
        if metrics.total_trades < self.constraints.min_trades:
            violations.append(f"거래 수 부족: {metrics.total_trades} < {self.constraints.min_trades}")
        
        if metrics.max_drawdown > self.constraints.max_drawdown:
            violations.append(f"최대 드로우다운 초과: {metrics.max_drawdown:.3f} > {self.constraints.max_drawdown}")
        
        if metrics.win_rate < self.constraints.min_win_rate:
            violations.append(f"승률 부족: {metrics.win_rate:.3f} < {self.constraints.min_win_rate}")
        
        if metrics.win_rate > self.constraints.max_win_rate:
            violations.append(f"승률 과다: {metrics.win_rate:.3f} > {self.constraints.max_win_rate}")
        
        if metrics.profit_factor < self.constraints.min_profit_factor:
            violations.append(f"Profit Factor 부족: {metrics.profit_factor:.3f} < {self.constraints.min_profit_factor}")
        
        # 추가 제약 조건
        if metrics.sortino_ratio < self.constraints.min_sortino_ratio:
            violations.append(f"Sortino Ratio 부족: {metrics.sortino_ratio:.3f} < {self.constraints.min_sortino_ratio}")
        
        if metrics.sharpe_ratio < self.constraints.min_sharpe_ratio:
            violations.append(f"Sharpe Ratio 부족: {metrics.sharpe_ratio:.3f} < {self.constraints.min_sharpe_ratio}")
        
        if metrics.rr_ratio < self.constraints.min_rr_ratio:
            violations.append(f"R:R Ratio 부족: {metrics.rr_ratio:.3f} < {self.constraints.min_rr_ratio}")
        
        if metrics.sqn < self.constraints.min_sqn:
            violations.append(f"SQN 부족: {metrics.sqn:.3f} < {self.constraints.min_sqn}")
        
        if metrics.calmar_ratio < self.constraints.min_calmar_ratio:
            violations.append(f"Calmar Ratio 부족: {metrics.calmar_ratio:.3f} < {self.constraints.min_calmar_ratio}")
        
        if metrics.mar_ratio < self.constraints.min_mar_ratio:
            violations.append(f"MAR Ratio 부족: {metrics.mar_ratio:.3f} < {self.constraints.min_mar_ratio}")
        
        if metrics.expectancy < self.constraints.min_expectancy:
            violations.append(f"Expectancy 부족: {metrics.expectancy:.3f} < {self.constraints.min_expectancy}")
        
        # R Expectancy / Variance Ratio 추가 (간단히 expectancy/volatility로 계산)
        r_exp_var_ratio = metrics.expectancy / metrics.volatility if metrics.volatility > 0 else 0
        if r_exp_var_ratio < self.constraints.min_r_exp_var_ratio:
            violations.append(f"R Exp/Var Ratio 부족: {r_exp_var_ratio:.3f} < {self.constraints.min_r_exp_var_ratio}")
        
        passed = len(violations) == 0
        return passed, violations
    
    def calculate_score(self, metrics: PerformanceMetrics) -> float:
        """점수 계산 - Score = 0.35·Sortino + 0.25·Calmar + 0.20·PF + 0.20·SQN − λ·MaxDD"""
        
        # 제약 조건 확인
        passed, violations = self.check_constraints(metrics)
        if not passed:
            return -10000  # 제약 조건 위반 시 큰 음수 반환
        
        # 정규화된 지표 계산
        def normalize_metric(value: float, target: float, max_multiplier: float = 3.0) -> float:
            """지표를 목표값 기준으로 정규화"""
            return min(value / target, max_multiplier) if target > 0 else 0
        
        # 각 지표 정규화
        norm_sortino = normalize_metric(metrics.sortino_ratio, self.score_config.target_sortino)
        norm_calmar = normalize_metric(metrics.calmar_ratio, self.score_config.target_calmar)
        norm_pf = normalize_metric(metrics.profit_factor, self.score_config.target_profit_factor)
        norm_sqn = normalize_metric(metrics.sqn, self.score_config.target_sqn)
        
        # 가중 점수 계산
        base_score = (
            self.score_config.sortino_weight * norm_sortino +
            self.score_config.calmar_weight * norm_calmar +
            self.score_config.profit_factor_weight * norm_pf +
            self.score_config.sqn_weight * norm_sqn
        )
        
        # DD 패널티 계산
        dd_penalty = 0
        if metrics.max_drawdown > self.score_config.dd_threshold:
            excess_dd = metrics.max_drawdown - self.score_config.dd_threshold
            dd_penalty = self.score_config.dd_penalty_lambda * excess_dd * 10  # 10배 패널티
        
        # 최종 점수
        final_score = base_score - dd_penalty
        
        return final_score
    
    def aggregate_results(self, results_list: List[PerformanceMetrics], 
                         method: str = "median") -> PerformanceMetrics:
        """결과 집계 - 메디안 기반"""
        if not results_list:
            return self._empty_metrics()
        
        if len(results_list) == 1:
            return results_list[0]
        
        # 각 지표별로 집계
        if method == "median":
            aggregated = PerformanceMetrics(
                total_trades=int(np.median([r.total_trades for r in results_list])),
                win_rate=np.median([r.win_rate for r in results_list]),
                profit_factor=np.median([r.profit_factor for r in results_list if r.profit_factor != float('inf')]),
                max_drawdown=np.median([r.max_drawdown for r in results_list]),
                sortino_ratio=np.median([r.sortino_ratio for r in results_list]),
                sharpe_ratio=np.median([r.sharpe_ratio for r in results_list]),
                calmar_ratio=np.median([r.calmar_ratio for r in results_list]),
                sqn=np.median([r.sqn for r in results_list]),
                rr_ratio=np.median([r.rr_ratio for r in results_list]),
                expectancy=np.median([r.expectancy for r in results_list]),
                mar_ratio=np.median([r.mar_ratio for r in results_list]),
                total_return=np.median([r.total_return for r in results_list]),
                annual_return=np.median([r.annual_return for r in results_list]),
                volatility=np.median([r.volatility for r in results_list]),
                avg_win=np.median([r.avg_win for r in results_list]),
                avg_loss=np.median([r.avg_loss for r in results_list])
            )
        else:  # mean
            aggregated = PerformanceMetrics(
                total_trades=int(np.mean([r.total_trades for r in results_list])),
                win_rate=np.mean([r.win_rate for r in results_list]),
                profit_factor=np.mean([r.profit_factor for r in results_list if r.profit_factor != float('inf')]),
                max_drawdown=np.mean([r.max_drawdown for r in results_list]),
                sortino_ratio=np.mean([r.sortino_ratio for r in results_list]),
                sharpe_ratio=np.mean([r.sharpe_ratio for r in results_list]),
                calmar_ratio=np.mean([r.calmar_ratio for r in results_list]),
                sqn=np.mean([r.sqn for r in results_list]),
                rr_ratio=np.mean([r.rr_ratio for r in results_list]),
                expectancy=np.mean([r.expectancy for r in results_list]),
                mar_ratio=np.mean([r.mar_ratio for r in results_list]),
                total_return=np.mean([r.total_return for r in results_list]),
                annual_return=np.mean([r.annual_return for r in results_list]),
                volatility=np.mean([r.volatility for r in results_list]),
                avg_win=np.mean([r.avg_win for r in results_list]),
                avg_loss=np.mean([r.avg_loss for r in results_list])
            )
        
        return aggregated
    
    def calculate_iqr_stability(self, results_list: List[PerformanceMetrics]) -> Dict[str, float]:
        """IQR 기반 안정성 계산"""
        if len(results_list) < 3:
            return {"stability_score": 0.0}
        
        # 주요 지표들의 IQR 계산
        profit_factors = [r.profit_factor for r in results_list if r.profit_factor != float('inf')]
        sortino_ratios = [r.sortino_ratio for r in results_list]
        win_rates = [r.win_rate for r in results_list]
        
        stability_metrics = {}
        
        # IQR 계산 (낮을수록 안정적)
        if len(profit_factors) > 2:
            pf_q75, pf_q25 = np.percentile(profit_factors, [75, 25])
            pf_iqr = pf_q75 - pf_q25
            pf_median = np.median(profit_factors)
            stability_metrics['pf_cv'] = pf_iqr / pf_median if pf_median > 0 else 1.0
        
        if len(sortino_ratios) > 2:
            sr_q75, sr_q25 = np.percentile(sortino_ratios, [75, 25])
            sr_iqr = sr_q75 - sr_q25
            sr_median = np.median(sortino_ratios)
            stability_metrics['sr_cv'] = sr_iqr / sr_median if sr_median > 0 else 1.0
        
        if len(win_rates) > 2:
            wr_q75, wr_q25 = np.percentile(win_rates, [75, 25])
            wr_iqr = wr_q75 - wr_q25
            wr_median = np.median(win_rates)
            stability_metrics['wr_cv'] = wr_iqr / wr_median if wr_median > 0 else 1.0
        
        # 전체 안정성 점수 (낮을수록 좋음)
        cv_values = [v for v in stability_metrics.values() if v < 2.0]  # 이상치 제거
        stability_score = np.mean(cv_values) if cv_values else 1.0
        
        stability_metrics['stability_score'] = stability_score
        stability_metrics['stability_rank'] = 1.0 / (1.0 + stability_score)  # 높을수록 좋음
        
        return stability_metrics
    
    def rank_candidates(self, candidates: List[Tuple[Dict, PerformanceMetrics]], 
                       use_stability: bool = True) -> List[Tuple[Dict, PerformanceMetrics, float]]:
        """후보들을 점수 기준으로 랭킹"""
        ranked_candidates = []
        
        for params, metrics in candidates:
            base_score = self.calculate_score(metrics)
            
            # 안정성 보너스 (사용하는 경우)
            stability_bonus = 0
            if use_stability and hasattr(metrics, 'stability_rank'):
                stability_bonus = metrics.stability_rank * 0.1  # 최대 10% 보너스
            
            final_score = base_score + stability_bonus
            ranked_candidates.append((params, metrics, final_score))
        
        # 점수 기준 내림차순 정렬
        ranked_candidates.sort(key=lambda x: x[2], reverse=True)
        
        return ranked_candidates
    
    def print_metrics_report(self, metrics: PerformanceMetrics, title: str = "성과 리포트"):
        """성과 지표 리포트 출력"""
        print(f"\n📊 {title}")
        print("=" * 60)
        
        print(f"거래 통계:")
        print(f"  총 거래 수: {metrics.total_trades}")
        print(f"  승률: {metrics.win_rate:.1%}")
        print(f"  평균 승리: ${metrics.avg_win:.2f}")
        print(f"  평균 손실: ${metrics.avg_loss:.2f}")
        
        print(f"\n수익성 지표:")
        print(f"  Profit Factor: {metrics.profit_factor:.2f}")
        print(f"  R:R Ratio: {metrics.rr_ratio:.2f}")
        print(f"  Expectancy: {metrics.expectancy:.3f}R")
        print(f"  총 수익률: {metrics.total_return:.2f}%")
        
        print(f"\n리스크 조정 지표:")
        print(f"  Sortino Ratio: {metrics.sortino_ratio:.2f}")
        print(f"  Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
        print(f"  Calmar Ratio: {metrics.calmar_ratio:.2f}")
        print(f"  SQN: {metrics.sqn:.2f}")
        print(f"  최대 드로우다운: {metrics.max_drawdown:.1%}")
        
        # 제약 조건 확인
        passed, violations = self.check_constraints(metrics)
        print(f"\n제약 조건: {'✅ 통과' if passed else '❌ 위반'}")
        if violations:
            for violation in violations:
                print(f"  - {violation}")
        
        # 점수 계산
        score = self.calculate_score(metrics)
        print(f"\n최종 점수: {score:.4f}")

def main():
    """테스트 실행"""
    evaluator = PerformanceEvaluator()
    
    # 테스트 거래 데이터 생성
    np.random.seed(42)
    n_trades = 300
    
    # 가상의 거래 결과 생성 (기본 테스트용)
    win_rate = 0.55
    avg_win = 150
    avg_loss = -80
    
    pnl_data = []
    for i in range(n_trades):
        if np.random.random() < win_rate:
            pnl = np.random.normal(avg_win, avg_win * 0.3)
        else:
            pnl = np.random.normal(avg_loss, abs(avg_loss) * 0.3)
        pnl_data.append(pnl)
    
    # DataFrame 생성
    test_trades = pd.DataFrame({
        'pnl': pnl_data,
        'entry_time': pd.date_range('2024-01-01', periods=n_trades, freq='4H'),
        'exit_time': pd.date_range('2024-01-01 01:00', periods=n_trades, freq='4H')
    })
    
    # 성과 지표 계산
    metrics = evaluator.calculate_metrics(test_trades)
    
    # 리포트 출력
    evaluator.print_metrics_report(metrics, "테스트 성과 리포트")
    
    # 여러 결과 집계 테스트
    print(f"\n🔄 집계 테스트:")
    metrics_list = [metrics] * 5  # 동일한 메트릭 5개
    aggregated = evaluator.aggregate_results(metrics_list)
    print(f"집계된 Profit Factor: {aggregated.profit_factor:.2f}")
    
    # 안정성 계산 테스트
    stability = evaluator.calculate_iqr_stability(metrics_list)
    print(f"안정성 점수: {stability['stability_score']:.4f}")

if __name__ == "__main__":
    main()