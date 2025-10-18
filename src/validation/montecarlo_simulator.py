#!/usr/bin/env python3
"""
몬테카를로 시뮬레이션 엔진 구현
- Block Bootstrap (블록길이=ACF 반감기)
- Trade Resampling (승/패·익절/손절 구조 보존)
- Execution Noise (슬리피지 ±σ, 스프레드 확장)
- Parameter Perturbation (최종 파라 ±10%)
- 1,000–2,000회 반복 시뮬레이션
- 합격선 검증 (PF_p5≥1.5, Sortino_p5≥1.2, etc.)
"""

import warnings
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from fast_data_engine import FastDataEngine
from performance_evaluator import PerformanceEvaluator, PerformanceMetrics


@dataclass
class MonteCarloConfig:
    """몬테카를로 설정"""

    n_simulations: int = 1500  # 시뮬레이션 횟수
    block_bootstrap_enabled: bool = True
    trade_resampling_enabled: bool = True
    execution_noise_enabled: bool = True
    param_perturbation_enabled: bool = True

    # 부트스트랩 설정
    min_block_size: int = 5  # 최소 블록 크기
    max_block_size: int = 50  # 최대 블록 크기

    # 실행 노이즈 설정
    slippage_std: float = 0.02  # 슬리피지 표준편차 (2%)
    spread_expansion_rate: float = 0.1  # 스프레드 확장 비율 (10%)
    spread_event_lambda: float = 0.05  # 스프레드 이벤트 발생률

    # 파라미터 섭동 설정
    param_noise_std: float = 0.1  # 파라미터 노이즈 (±10%)


@dataclass
class MonteCarloResult:
    """몬테카를로 결과"""

    percentiles: Dict[str, float]  # p5, p25, p50, p75, p95
    stability_metrics: Dict[str, float]
    robustness_score: float
    passed_criteria: bool
    simulation_count: int
    original_metrics: PerformanceMetrics


class MonteCarloSimulator:
    def __init__(self, performance_evaluator: PerformanceEvaluator, config: MonteCarloConfig = None):
        """몬테카를로 시뮬레이터 초기화"""
        self.performance_evaluator = performance_evaluator
        self.config = config or MonteCarloConfig()

        # 합격선 (보수적 p-분위 기준)
        self.criteria = {
            "pf_p5": 1.5,  # PF 5분위 ≥ 1.5
            "sortino_p5": 1.2,  # Sortino 5분위 ≥ 1.2
            "calmar_p5": 1.2,  # Calmar 5분위 ≥ 1.2
            "max_dd_p95": 0.30,  # MaxDD 95분위 ≤ 30%
            "sqn_median": 3.0,  # SQN 중앙값 ≥ 3.0
        }

        print("🎲 몬테카를로 시뮬레이터 초기화")
        print(f"   시뮬레이션 횟수: {self.config.n_simulations}회")
        print(f"   부트스트랩 방법: Block + Trade + Noise + Param")
        print(f"   합격선: PF_p5≥{self.criteria['pf_p5']}, Sortino_p5≥{self.criteria['sortino_p5']}")

    def calculate_acf_half_life(self, returns: np.ndarray, max_lags: int = 50) -> int:
        """자기상관함수 반감기 계산"""
        if len(returns) < max_lags * 2:
            return self.config.min_block_size

        # 자기상관함수 계산
        acf_values = []
        for lag in range(1, min(max_lags, len(returns) // 2)):
            if lag >= len(returns):
                break

            # 피어슨 상관계수 계산
            x = returns[:-lag]
            y = returns[lag:]

            if len(x) > 1 and len(y) > 1:
                corr = np.corrcoef(x, y)[0, 1]
                if not np.isnan(corr):
                    acf_values.append(abs(corr))
                else:
                    acf_values.append(0)
            else:
                acf_values.append(0)

        if not acf_values:
            return self.config.min_block_size

        # 반감기 찾기 (ACF가 최대값의 50% 이하로 떨어지는 지점)
        max_acf = max(acf_values) if acf_values else 0
        half_threshold = max_acf * 0.5

        for i, acf in enumerate(acf_values):
            if acf <= half_threshold:
                half_life = i + 1
                break
        else:
            half_life = len(acf_values)

        # 범위 제한
        half_life = max(self.config.min_block_size, min(half_life, self.config.max_block_size))

        # ACF 반감기 출력 (첫 번째만)
        if not hasattr(self, "_acf_printed"):
            print(f"📊 ACF 반감기: {half_life}바 (최대 ACF: {max_acf:.3f})")
            self._acf_printed = True
        return half_life

    def block_bootstrap(self, returns: np.ndarray, block_size: int) -> np.ndarray:
        """블록 부트스트랩"""
        n = len(returns)
        if n <= block_size:
            return np.random.permutation(returns)

        # 블록 생성
        n_blocks = (n + block_size - 1) // block_size  # 올림
        bootstrapped = []

        for _ in range(n_blocks):
            # 랜덤 시작점 선택
            start_idx = np.random.randint(0, max(1, n - block_size + 1))
            end_idx = min(start_idx + block_size, n)

            block = returns[start_idx:end_idx]
            bootstrapped.extend(block)

        # 원래 길이로 자르기
        bootstrapped = np.array(bootstrapped[:n])

        return bootstrapped

    def resample_trades(self, trades_df: pd.DataFrame) -> pd.DataFrame:
        """거래 리샘플링 (승/패·익절/손절 구조 보존)"""
        if len(trades_df) == 0:
            return trades_df.copy()

        # 거래 분류
        winning_trades = trades_df[trades_df["pnl"] > 0].copy()
        losing_trades = trades_df[trades_df["pnl"] <= 0].copy()

        # 각 그룹에서 복원 추출
        resampled_trades = []

        # 승리 거래 리샘플링
        if len(winning_trades) > 0:
            n_wins = len(winning_trades)
            win_indices = np.random.choice(len(winning_trades), size=n_wins, replace=True)
            resampled_wins = winning_trades.iloc[win_indices].copy()
            resampled_trades.append(resampled_wins)

        # 손실 거래 리샘플링
        if len(losing_trades) > 0:
            n_losses = len(losing_trades)
            loss_indices = np.random.choice(len(losing_trades), size=n_losses, replace=True)
            resampled_losses = losing_trades.iloc[loss_indices].copy()
            resampled_trades.append(resampled_losses)

        if resampled_trades:
            result = pd.concat(resampled_trades, ignore_index=True)
            # 원래 순서 섞기
            result = result.sample(frac=1).reset_index(drop=True)
            return result
        else:
            return trades_df.copy()

    def add_execution_noise(self, trades_df: pd.DataFrame) -> pd.DataFrame:
        """실행 노이즈 추가"""
        if len(trades_df) == 0:
            return trades_df.copy()

        noisy_trades = trades_df.copy()

        # 슬리피지 노이즈 (정규분포)
        slippage_noise = np.random.normal(0, self.config.slippage_std, len(noisy_trades))

        # 스프레드 확장 이벤트 (포아송 분포)
        spread_events = np.random.poisson(self.config.spread_event_lambda, len(noisy_trades))
        spread_penalty = spread_events * self.config.spread_expansion_rate

        # PnL에 노이즈 적용
        for i in range(len(noisy_trades)):
            original_pnl = noisy_trades.iloc[i]["pnl"]

            # 슬리피지 적용 (절댓값에 비례)
            slippage_impact = abs(original_pnl) * slippage_noise[i]

            # 스프레드 패널티 (항상 음수)
            spread_impact = -abs(original_pnl) * spread_penalty[i]

            # 최종 PnL
            noisy_pnl = original_pnl + slippage_impact + spread_impact
            noisy_trades.iloc[i, noisy_trades.columns.get_loc("pnl")] = noisy_pnl

        return noisy_trades

    def perturb_parameters(self, params: Dict[str, float]) -> Dict[str, float]:
        """파라미터 섭동 (±10%)"""
        perturbed = {}

        for key, value in params.items():
            if isinstance(value, (int, float)):
                # 정규분포 노이즈 추가
                noise = np.random.normal(0, self.config.param_noise_std)
                perturbed_value = value * (1 + noise)

                # 타입 보존
                if isinstance(value, int):
                    perturbed_value = int(round(perturbed_value))
                    # 정수 파라미터는 최소값 보장
                    if key in ["swing_len", "atr_len", "time_stop_bars", "trend_filter_len"]:
                        perturbed_value = max(1, perturbed_value)
                else:
                    # 실수 파라미터는 양수 보장
                    if key in ["rr_percentile", "stop_atr_mult", "target_r"]:
                        perturbed_value = max(0.01, perturbed_value)

                perturbed[key] = perturbed_value
            else:
                perturbed[key] = value

        return perturbed

    def run_single_simulation(self, trades_df: pd.DataFrame, params: Dict[str, float], sim_id: int) -> PerformanceMetrics:
        """단일 시뮬레이션 실행"""
        try:
            current_trades = trades_df.copy()

            # 1. 파라미터 섭동
            if self.config.param_perturbation_enabled:
                perturbed_params = self.perturb_parameters(params)
            else:
                perturbed_params = params

            # 2. 블록 부트스트랩
            if self.config.block_bootstrap_enabled and len(current_trades) > 0:
                returns = current_trades["pnl"].values
                block_size = self.calculate_acf_half_life(returns)
                bootstrapped_returns = self.block_bootstrap(returns, block_size)
                current_trades["pnl"] = bootstrapped_returns

            # 3. 거래 리샘플링
            if self.config.trade_resampling_enabled:
                current_trades = self.resample_trades(current_trades)

            # 4. 실행 노이즈 추가
            if self.config.execution_noise_enabled:
                current_trades = self.add_execution_noise(current_trades)

            # 5. 성과 지표 계산
            metrics = self.performance_evaluator.calculate_metrics(current_trades)

            return metrics

        except Exception as e:
            print(f"❌ 시뮬레이션 {sim_id} 실패: {e}")
            return self.performance_evaluator._empty_metrics()

    def run_monte_carlo(self, trades_df: pd.DataFrame, params: Dict[str, float]) -> MonteCarloResult:
        """몬테카를로 시뮬레이션 실행"""
        print(f"\n🎲 몬테카를로 시뮬레이션 시작")
        print(f"   원본 거래 수: {len(trades_df)}")
        print(f"   시뮬레이션 횟수: {self.config.n_simulations}")

        # 원본 성과 계산
        original_metrics = self.performance_evaluator.calculate_metrics(trades_df)

        # 시뮬레이션 실행
        simulation_results = []

        for i in range(self.config.n_simulations):
            if i % 200 == 0 and i > 0:
                print(f"   진행률: {i}/{self.config.n_simulations} ({i/self.config.n_simulations*100:.1f}%)")

            sim_metrics = self.run_single_simulation(trades_df, params, i)
            simulation_results.append(sim_metrics)

        # 결과 분석
        result = self._analyze_simulation_results(simulation_results, original_metrics)

        print(f"\n✅ 몬테카를로 시뮬레이션 완료")
        print(f"   유효 시뮬레이션: {result.simulation_count}개")
        print(f"   견고성 점수: {result.robustness_score:.4f}")
        print(f"   합격 여부: {'✅ 통과' if result.passed_criteria else '❌ 실패'}")

        return result

    def _analyze_simulation_results(self, results: List[PerformanceMetrics], original: PerformanceMetrics) -> MonteCarloResult:
        """시뮬레이션 결과 분석"""
        # 유효한 결과만 필터링
        valid_results = [r for r in results if r.total_trades > 0]

        if len(valid_results) == 0:
            return MonteCarloResult(
                percentiles={},
                stability_metrics={},
                robustness_score=0,
                passed_criteria=False,
                simulation_count=0,
                original_metrics=original,
            )

        # 각 지표별 분포 계산
        metrics_arrays = {
            "profit_factor": [r.profit_factor for r in valid_results if r.profit_factor != float("inf")],
            "sortino_ratio": [r.sortino_ratio for r in valid_results],
            "calmar_ratio": [r.calmar_ratio for r in valid_results],
            "max_drawdown": [r.max_drawdown for r in valid_results],
            "sqn": [r.sqn for r in valid_results],
            "win_rate": [r.win_rate for r in valid_results],
            "total_return": [r.total_return for r in valid_results],
        }

        # 분위수 계산
        percentiles = {}
        for metric, values in metrics_arrays.items():
            if values:
                percentiles[f"{metric}_p5"] = np.percentile(values, 5)
                percentiles[f"{metric}_p25"] = np.percentile(values, 25)
                percentiles[f"{metric}_p50"] = np.percentile(values, 50)
                percentiles[f"{metric}_p75"] = np.percentile(values, 75)
                percentiles[f"{metric}_p95"] = np.percentile(values, 95)

        # 안정성 지표 계산
        stability_metrics = self._calculate_stability_metrics(metrics_arrays)

        # 견고성 점수 계산
        robustness_score = self._calculate_robustness_score(percentiles, stability_metrics)

        # 합격 기준 확인
        passed_criteria = self._check_monte_carlo_criteria(percentiles)

        return MonteCarloResult(
            percentiles=percentiles,
            stability_metrics=stability_metrics,
            robustness_score=robustness_score,
            passed_criteria=passed_criteria,
            simulation_count=len(valid_results),
            original_metrics=original,
        )

    def _calculate_stability_metrics(self, metrics_arrays: Dict[str, List[float]]) -> Dict[str, float]:
        """안정성 지표 계산"""
        stability = {}

        for metric, values in metrics_arrays.items():
            if values and len(values) > 1:
                mean_val = np.mean(values)
                std_val = np.std(values)

                # 변동계수 (CV)
                cv = std_val / mean_val if mean_val != 0 else float("inf")
                stability[f"{metric}_cv"] = cv

                # IQR 기반 안정성
                q75, q25 = np.percentile(values, [75, 25])
                iqr = q75 - q25
                iqr_stability = iqr / np.median(values) if np.median(values) != 0 else float("inf")
                stability[f"{metric}_iqr_stability"] = iqr_stability

        return stability

    def _calculate_robustness_score(self, percentiles: Dict[str, float], stability_metrics: Dict[str, float]) -> float:
        """견고성 점수 계산"""
        score_components = []

        # 성과 지표 점수 (5분위 기준)
        pf_p5 = percentiles.get("profit_factor_p5", 0)
        if pf_p5 > 0:
            score_components.append(min(pf_p5 / 2.0, 1.0))  # PF 2.0 기준

        sortino_p5 = percentiles.get("sortino_ratio_p5", 0)
        if sortino_p5 > 0:
            score_components.append(min(sortino_p5 / 1.5, 1.0))  # Sortino 1.5 기준

        # 안정성 점수 (낮은 변동성이 좋음)
        pf_cv = stability_metrics.get("profit_factor_cv", float("inf"))
        if pf_cv < float("inf"):
            stability_score = 1.0 / (1.0 + pf_cv)  # CV가 낮을수록 높은 점수
            score_components.append(stability_score)

        # 드로우다운 점수 (95분위 기준)
        dd_p95 = percentiles.get("max_drawdown_p95", 1.0)
        dd_score = max(0, 1.0 - dd_p95 / 0.3)  # 30% 기준
        score_components.append(dd_score)

        # 전체 점수 (평균)
        if score_components:
            return np.mean(score_components)
        else:
            return 0.0

    def _check_monte_carlo_criteria(self, percentiles: Dict[str, float]) -> bool:
        """몬테카를로 합격 기준 확인"""
        checks = []

        # PF 5분위 ≥ 1.5
        pf_p5 = percentiles.get("profit_factor_p5", 0)
        checks.append(pf_p5 >= self.criteria["pf_p5"])

        # Sortino 5분위 ≥ 1.2
        sortino_p5 = percentiles.get("sortino_ratio_p5", 0)
        checks.append(sortino_p5 >= self.criteria["sortino_p5"])

        # Calmar 5분위 ≥ 1.2
        calmar_p5 = percentiles.get("calmar_ratio_p5", 0)
        checks.append(calmar_p5 >= self.criteria["calmar_p5"])

        # MaxDD 95분위 ≤ 30%
        dd_p95 = percentiles.get("max_drawdown_p95", 1.0)
        checks.append(dd_p95 <= self.criteria["max_dd_p95"])

        # SQN 중앙값 ≥ 3.0
        sqn_median = percentiles.get("sqn_p50", 0)
        checks.append(sqn_median >= self.criteria["sqn_median"])

        return all(checks)

    def print_monte_carlo_results(self, result: MonteCarloResult, title: str = "몬테카를로 시뮬레이션 결과"):
        """몬테카를로 결과 출력"""
        print(f"\n🎲 {title}")
        print("=" * 80)

        print(f"시뮬레이션 횟수: {result.simulation_count}")
        print(f"견고성 점수: {result.robustness_score:.4f}")
        print(f"합격 여부: {'✅ 통과' if result.passed_criteria else '❌ 실패'}")

        # 원본 vs 시뮬레이션 비교
        orig = result.original_metrics
        print(f"\n📊 원본 vs 시뮬레이션 비교:")
        print(f"   Profit Factor: {orig.profit_factor:.2f} → p5: {result.percentiles.get('profit_factor_p5', 0):.2f}")
        print(f"   Sortino Ratio: {orig.sortino_ratio:.2f} → p5: {result.percentiles.get('sortino_ratio_p5', 0):.2f}")
        print(f"   Max Drawdown: {orig.max_drawdown:.1%} → p95: {result.percentiles.get('max_drawdown_p95', 0):.1%}")

        # 분위수 분포
        print(f"\n📈 주요 지표 분위수:")
        key_metrics = ["profit_factor", "sortino_ratio", "calmar_ratio", "sqn"]
        for metric in key_metrics:
            p5 = result.percentiles.get(f"{metric}_p5", 0)
            p50 = result.percentiles.get(f"{metric}_p50", 0)
            p95 = result.percentiles.get(f"{metric}_p95", 0)
            print(f"   {metric}: p5={p5:.2f}, p50={p50:.2f}, p95={p95:.2f}")

        # 안정성 지표
        print(f"\n🔒 안정성 지표:")
        pf_cv = result.stability_metrics.get("profit_factor_cv", 0)
        sr_cv = result.stability_metrics.get("sortino_ratio_cv", 0)
        print(f"   Profit Factor CV: {pf_cv:.3f}")
        print(f"   Sortino Ratio CV: {sr_cv:.3f}")

        # 합격 기준 상세
        print(f"\n✅ 합격 기준 확인:")
        criteria_results = [
            ("PF p5 ≥ 1.5", result.percentiles.get("profit_factor_p5", 0), 1.5),
            ("Sortino p5 ≥ 1.2", result.percentiles.get("sortino_ratio_p5", 0), 1.2),
            ("Calmar p5 ≥ 1.2", result.percentiles.get("calmar_ratio_p5", 0), 1.2),
            ("MaxDD p95 ≤ 30%", result.percentiles.get("max_drawdown_p95", 0), 0.30),
            ("SQN median ≥ 3.0", result.percentiles.get("sqn_p50", 0), 3.0),
        ]

        for desc, value, threshold in criteria_results:
            if "MaxDD" in desc:
                passed = value <= threshold
                print(f"   {desc}: {value:.1%} {'✅' if passed else '❌'}")
            else:
                passed = value >= threshold
                print(f"   {desc}: {value:.2f} {'✅' if passed else '❌'}")


def main():
    """테스트 실행"""
    # 성과 평가자 초기화
    performance_evaluator = PerformanceEvaluator()

    # 몬테카를로 시뮬레이터 초기화
    config = MonteCarloConfig(n_simulations=500)  # 테스트용으로 500회
    simulator = MonteCarloSimulator(performance_evaluator, config)

    # 테스트 거래 데이터 생성
    np.random.seed(42)
    n_trades = 200

    # 현실적인 거래 결과 생성
    win_rate = 0.55
    avg_win = 100
    avg_loss = -60

    pnl_data = []
    for _ in range(n_trades):
        if np.random.random() < win_rate:
            pnl = np.random.normal(avg_win, avg_win * 0.3)
        else:
            pnl = np.random.normal(avg_loss, abs(avg_loss) * 0.3)
        pnl_data.append(pnl)

    test_trades = pd.DataFrame({"pnl": pnl_data})

    # 테스트 파라미터
    test_params = {"target_r": 2.5, "stop_atr_mult": 0.1, "swing_len": 5, "rr_percentile": 0.2}

    # 몬테카를로 시뮬레이션 실행
    result = simulator.run_monte_carlo(test_trades, test_params)

    # 결과 출력
    simulator.print_monte_carlo_results(result)


if __name__ == "__main__":
    main()
