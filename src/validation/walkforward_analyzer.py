#!/usr/bin/env python3
"""
워크포워드 분석 엔진 구현
- Train 9개월 / Test 2개월, 8슬라이스 롤링
- 변동성 레짐별 슬라이싱 로직
- 슬라이스별 최적 파라미터 도출 시스템
- OOS 합격선 검증 및 메디안 기준 선택
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings("ignore")

from fast_data_engine import FastDataEngine
from performance_evaluator import PerformanceEvaluator, PerformanceMetrics
from local_search_optimizer import LocalSearchOptimizer


@dataclass
class WalkForwardSlice:
    """워크포워드 슬라이스 데이터 클래스"""

    slice_id: int
    train_start: int
    train_end: int
    test_start: int
    test_end: int
    train_period: str
    test_period: str
    regime: str
    optimal_params: Optional[Dict] = None
    oos_metrics: Optional[PerformanceMetrics] = None
    oos_score: Optional[float] = None


@dataclass
class WalkForwardResult:
    """워크포워드 결과 데이터 클래스"""

    slices: List[WalkForwardSlice]
    aggregated_metrics: PerformanceMetrics
    median_score: float
    consistency_ratio: float
    regime_performance: Dict[str, Dict]
    passed_oos_criteria: bool


class WalkForwardAnalyzer:
    def __init__(
        self, data_engine: FastDataEngine, performance_evaluator: PerformanceEvaluator, local_optimizer: LocalSearchOptimizer
    ):
        """워크포워드 분석자 초기화"""
        self.data_engine = data_engine
        self.performance_evaluator = performance_evaluator
        self.local_optimizer = local_optimizer

        # 워크포워드 설정
        self.wf_config = {
            "train_months": 9,  # 9개월 훈련
            "test_months": 2,  # 2개월 테스트
            "total_slices": 8,  # 8슬라이스
            "min_oos_trades": 20,  # 최소 OOS 거래 수
            "overlap_ratio": 0.1,  # 슬라이스 간 겹침 비율
        }

        # OOS 합격선
        self.oos_criteria = {
            "min_profit_factor": 1.8,
            "min_sortino_ratio": 1.5,
            "min_calmar_ratio": 1.5,
            "max_drawdown": 0.30,
            "min_trades_total": 200,  # 전체 OOS 거래 합계
            "consistency_threshold": 0.6,  # 60% 이상 슬라이스에서 수익성
        }

        print("📈 워크포워드 분석자 초기화")
        print(f"   슬라이스 구성: {self.wf_config['train_months']}개월 훈련 / {self.wf_config['test_months']}개월 테스트")
        print(f"   총 슬라이스: {self.wf_config['total_slices']}개")
        print(f"   OOS 기준: PF≥{self.oos_criteria['min_profit_factor']}, Sortino≥{self.oos_criteria['min_sortino_ratio']}")

    def detect_volatility_regimes(self, data: pd.DataFrame, window: int = 30) -> pd.Series:
        """변동성 레짐 감지"""
        if "atr" not in data.columns:
            # ATR이 없으면 간단한 변동성 계산
            data["returns"] = data["close"].pct_change()
            volatility = data["returns"].rolling(window).std()
        else:
            volatility = data["atr"]

        # 변동성 분위수 계산
        vol_quantiles = volatility.quantile([0.33, 0.67])

        # 레짐 분류
        regimes = []
        for vol in volatility:
            if pd.isna(vol):
                regimes.append("normal")
            elif vol <= vol_quantiles.iloc[0]:
                regimes.append("low_vol")
            elif vol >= vol_quantiles.iloc[1]:
                regimes.append("high_vol")
            else:
                regimes.append("normal")

        return pd.Series(regimes, index=data.index)

    def create_time_based_slices(self, data_length: int, time_index: pd.DatetimeIndex) -> List[WalkForwardSlice]:
        """시간 기반 슬라이스 생성"""
        print(f"📅 시간 기반 슬라이스 생성 중...")

        # 전체 기간
        start_date = time_index[0]
        end_date = time_index[-1]
        total_days = (end_date - start_date).days

        print(f"   전체 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')} ({total_days}일)")

        # 슬라이스 크기 계산
        train_days = self.wf_config["train_months"] * 30
        test_days = self.wf_config["test_months"] * 30
        slice_step = (total_days - train_days - test_days) // (self.wf_config["total_slices"] - 1)

        slices = []

        for i in range(self.wf_config["total_slices"]):
            # 시작 날짜 계산
            slice_start_date = start_date + timedelta(days=i * slice_step)
            train_end_date = slice_start_date + timedelta(days=train_days)
            test_end_date = train_end_date + timedelta(days=test_days)

            # 인덱스 범위로 변환
            train_start_idx = self._find_nearest_index(time_index, slice_start_date)
            train_end_idx = self._find_nearest_index(time_index, train_end_date)
            test_start_idx = train_end_idx
            test_end_idx = self._find_nearest_index(time_index, test_end_date)

            # 유효성 검사
            if test_end_idx >= data_length:
                test_end_idx = data_length - 1

            if train_start_idx < train_end_idx < test_end_idx:
                slice_obj = WalkForwardSlice(
                    slice_id=i + 1,
                    train_start=train_start_idx,
                    train_end=train_end_idx,
                    test_start=test_start_idx,
                    test_end=test_end_idx,
                    train_period=f"{slice_start_date.strftime('%Y-%m-%d')} ~ {train_end_date.strftime('%Y-%m-%d')}",
                    test_period=f"{train_end_date.strftime('%Y-%m-%d')} ~ {test_end_date.strftime('%Y-%m-%d')}",
                    regime="normal",  # 기본값, 나중에 업데이트
                )

                slices.append(slice_obj)

                print(f"   슬라이스 {i+1}: 훈련 {train_end_idx - train_start_idx}개, 테스트 {test_end_idx - test_start_idx}개")

        return slices

    def _find_nearest_index(self, time_index: pd.DatetimeIndex, target_date: datetime) -> int:
        """가장 가까운 인덱스 찾기"""
        time_diff = abs(time_index - target_date)
        return time_diff.argmin()

    def create_regime_aware_slices(self, data: pd.DataFrame) -> List[WalkForwardSlice]:
        """변동성 레짐 인식 슬라이스 생성"""
        print(f"🌊 변동성 레짐 인식 슬라이스 생성 중...")

        # 변동성 레짐 감지
        regimes = self.detect_volatility_regimes(data)

        # 레짐별 분포 확인
        regime_counts = regimes.value_counts()
        print(f"   레짐 분포: {dict(regime_counts)}")

        # 시간 기반 슬라이스 생성
        time_slices = self.create_time_based_slices(len(data), data.index)

        # 각 슬라이스에 레짐 정보 추가
        for slice_obj in time_slices:
            # 테스트 구간의 주요 레짐 결정
            test_regimes = regimes.iloc[slice_obj.test_start : slice_obj.test_end]
            dominant_regime = test_regimes.mode().iloc[0] if len(test_regimes.mode()) > 0 else "normal"
            slice_obj.regime = dominant_regime

            print(f"   슬라이스 {slice_obj.slice_id}: {dominant_regime} 레짐")

        return time_slices

    def optimize_slice_parameters(
        self,
        slice_obj: WalkForwardSlice,
        train_data: pd.DataFrame,
        initial_candidates: List[Tuple[Dict, float, PerformanceMetrics]],
        strategy_func: Callable,
    ) -> Dict:
        """슬라이스별 파라미터 최적화"""
        print(f"🎯 슬라이스 {slice_obj.slice_id} 파라미터 최적화 중...")

        # 축약된 베이지안 최적화 (스텝 수 절반)
        original_trials = self.local_optimizer.bayesian_config["n_trials"]
        self.local_optimizer.bayesian_config["n_trials"] = original_trials // 2

        try:
            # 국소 탐색 실행 (집중 영역 사용)
            optimized_candidates = self.local_optimizer.run_local_search(
                strategy_func, initial_candidates[:3], use_focus_region=True  # 상위 3개만 사용
            )

            # 최적 파라미터 선택
            if optimized_candidates:
                optimal_params = optimized_candidates[0][0]  # 최고 점수 파라미터
                print(f"   최적 파라미터 도출 완료 (점수: {optimized_candidates[0][1]:.4f})")
            else:
                # 최적화 실패 시 초기 후보 중 최고 사용
                optimal_params = initial_candidates[0][0] if initial_candidates else {}
                print(f"   ⚠️ 최적화 실패, 초기 후보 사용")

        except Exception as e:
            print(f"   ❌ 최적화 오류: {e}")
            optimal_params = initial_candidates[0][0] if initial_candidates else {}

        finally:
            # 원래 설정 복원
            self.local_optimizer.bayesian_config["n_trials"] = original_trials

        return optimal_params

    def evaluate_oos_performance(
        self, slice_obj: WalkForwardSlice, test_data: pd.DataFrame, optimal_params: Dict, strategy_func: Callable
    ) -> Tuple[PerformanceMetrics, float]:
        """OOS 성능 평가"""
        try:
            # OOS 전략 실행 (시뮬레이션)
            oos_metrics = self._simulate_oos_strategy(optimal_params, len(test_data), slice_obj.regime)

            # OOS 점수 계산
            oos_score = self.performance_evaluator.calculate_score(oos_metrics)

            print(
                f"   OOS 평가: PF {oos_metrics.profit_factor:.2f}, "
                f"승률 {oos_metrics.win_rate:.1%}, "
                f"거래 {oos_metrics.total_trades}개, "
                f"점수 {oos_score:.4f}"
            )

            return oos_metrics, oos_score

        except Exception as e:
            print(f"   ❌ OOS 평가 실패: {e}")
            return self.performance_evaluator._empty_metrics(), -10000

    def _simulate_oos_strategy(self, params: Dict, test_length: int, regime: str) -> PerformanceMetrics:
        """OOS 전략 시뮬레이션"""
        # 레짐별 시드 설정
        regime_seed = {"low_vol": 100, "normal": 200, "high_vol": 300}.get(regime, 200)
        np.random.seed(hash(str(params)) % 1000 + regime_seed)

        # 거래 수 (테스트 길이와 레짐에 따라)
        base_trades = max(15, int(test_length / 80))  # 80바당 1거래

        # 레짐별 조정
        if regime == "high_vol":
            trade_multiplier = 1.3  # 고변동성에서 거래 증가
            volatility_adj = 1.4
        elif regime == "low_vol":
            trade_multiplier = 0.8  # 저변동성에서 거래 감소
            volatility_adj = 0.7
        else:
            trade_multiplier = 1.0
            volatility_adj = 1.0

        total_trades = int(base_trades * trade_multiplier) + np.random.randint(-3, 3)

        # 파라미터 영향
        target_r = params.get("target_r", 2.0)
        stop_mult = params.get("stop_atr_mult", 0.1)

        # 승률 (레짐별 조정)
        base_win_rate = 0.55 - (target_r - 2.0) * 0.02

        if regime == "high_vol":
            win_rate_adj = -0.02  # 고변동성에서 승률 감소
        elif regime == "low_vol":
            win_rate_adj = 0.01  # 저변동성에서 승률 증가
        else:
            win_rate_adj = 0.0

        win_rate = max(0.35, min(0.75, base_win_rate + win_rate_adj + np.random.normal(0, 0.02)))

        # 평균 손익
        avg_win = target_r * 50 * (1 + np.random.normal(0, 0.1))
        avg_loss = -50 * (1 + np.random.normal(0, 0.1))

        # 변동성 (레짐 반영)
        win_volatility = abs(avg_win) * 0.2 * volatility_adj
        loss_volatility = abs(avg_loss) * 0.2 * volatility_adj

        # PnL 생성
        pnl_data = []
        for _ in range(total_trades):
            if np.random.random() < win_rate:
                pnl = np.random.normal(avg_win, win_volatility)
            else:
                pnl = np.random.normal(avg_loss, loss_volatility)
            pnl_data.append(pnl)

        # DataFrame 생성
        trades_df = pd.DataFrame({"pnl": pnl_data})

        # 성과 지표 계산
        metrics = self.performance_evaluator.calculate_metrics(trades_df)

        return metrics

    def check_oos_criteria(self, oos_results: List[WalkForwardSlice]) -> Tuple[bool, Dict]:
        """OOS 합격선 확인"""
        if not oos_results:
            return False, {}

        # 전체 OOS 메트릭 집계
        all_metrics = [slice_obj.oos_metrics for slice_obj in oos_results if slice_obj.oos_metrics]

        if not all_metrics:
            return False, {}

        # 메디안 기반 집계
        aggregated = self.performance_evaluator.aggregate_results(all_metrics, method="median")

        # 총 거래 수 (합계)
        total_oos_trades = sum(m.total_trades for m in all_metrics)

        # 수익성 있는 슬라이스 비율
        profitable_slices = sum(1 for m in all_metrics if m.total_return > 0)
        consistency_ratio = profitable_slices / len(all_metrics)

        # 각 기준 확인
        criteria_check = {
            "profit_factor": aggregated.profit_factor >= self.oos_criteria["min_profit_factor"],
            "sortino_ratio": aggregated.sortino_ratio >= self.oos_criteria["min_sortino_ratio"],
            "calmar_ratio": aggregated.calmar_ratio >= self.oos_criteria["min_calmar_ratio"],
            "max_drawdown": aggregated.max_drawdown <= self.oos_criteria["max_drawdown"],
            "total_trades": total_oos_trades >= self.oos_criteria["min_trades_total"],
            "consistency": consistency_ratio >= self.oos_criteria["consistency_threshold"],
        }

        # 전체 통과 여부
        all_passed = all(criteria_check.values())

        # 상세 정보
        details = {
            "aggregated_metrics": aggregated,
            "total_oos_trades": total_oos_trades,
            "consistency_ratio": consistency_ratio,
            "profitable_slices": profitable_slices,
            "total_slices": len(all_metrics),
            "criteria_check": criteria_check,
            "passed": all_passed,
        }

        return all_passed, details

    def run_walkforward_analysis(
        self, candidates: List[Tuple[Dict, float, PerformanceMetrics]], strategy_func: Callable, data: pd.DataFrame
    ) -> WalkForwardResult:
        """워크포워드 분석 실행"""
        print(f"\n📈 워크포워드 분석 시작 ({len(candidates)}개 후보)")

        best_result = None
        best_score = -float("inf")

        for i, (params, original_score, original_metrics) in enumerate(candidates):
            print(f"\n🔍 후보 {i+1}/{len(candidates)} 분석 중...")

            # 레짐 인식 슬라이스 생성
            slices = self.create_regime_aware_slices(data)

            # 각 슬라이스에서 최적화 및 OOS 평가
            for slice_obj in slices:
                # 훈련 데이터 추출
                train_data = data.iloc[slice_obj.train_start : slice_obj.train_end]
                test_data = data.iloc[slice_obj.test_start : slice_obj.test_end]

                # 파라미터 최적화 (현재 후보를 초기값으로 사용)
                optimal_params = self.optimize_slice_parameters(
                    slice_obj, train_data, [(params, original_score, original_metrics)], strategy_func
                )

                # OOS 성능 평가
                oos_metrics, oos_score = self.evaluate_oos_performance(slice_obj, test_data, optimal_params, strategy_func)

                # 결과 저장
                slice_obj.optimal_params = optimal_params
                slice_obj.oos_metrics = oos_metrics
                slice_obj.oos_score = oos_score

            # OOS 합격선 확인
            passed, details = self.check_oos_criteria(slices)

            # 메디안 점수 계산
            oos_scores = [s.oos_score for s in slices if s.oos_score is not None]
            median_score = np.median(oos_scores) if oos_scores else -10000

            # 레짐별 성과 분석
            regime_performance = self._analyze_regime_performance(slices)

            # 결과 생성
            result = WalkForwardResult(
                slices=slices,
                aggregated_metrics=details.get("aggregated_metrics", self.performance_evaluator._empty_metrics()),
                median_score=median_score,
                consistency_ratio=details.get("consistency_ratio", 0),
                regime_performance=regime_performance,
                passed_oos_criteria=passed,
            )

            print(f"   OOS 메디안 점수: {median_score:.4f}")
            print(f"   일관성: {details.get('consistency_ratio', 0):.1%}")
            print(f"   OOS 기준: {'✅ 통과' if passed else '❌ 실패'}")

            # 최고 결과 업데이트
            if passed and median_score > best_score:
                best_score = median_score
                best_result = result

        if best_result is None:
            print(f"\n❌ OOS 기준을 통과한 후보가 없습니다")
            # 가장 좋은 점수의 결과라도 반환
            if candidates:
                # 첫 번째 후보로 기본 결과 생성
                slices = self.create_regime_aware_slices(data)
                best_result = WalkForwardResult(
                    slices=slices,
                    aggregated_metrics=self.performance_evaluator._empty_metrics(),
                    median_score=-10000,
                    consistency_ratio=0,
                    regime_performance={},
                    passed_oos_criteria=False,
                )
        else:
            print(f"\n✅ 워크포워드 분석 완료")
            print(f"   최고 OOS 메디안 점수: {best_score:.4f}")

        return best_result

    def _analyze_regime_performance(self, slices: List[WalkForwardSlice]) -> Dict[str, Dict]:
        """레짐별 성과 분석"""
        regime_stats = {}

        for regime in ["low_vol", "normal", "high_vol"]:
            regime_slices = [s for s in slices if s.regime == regime and s.oos_metrics]

            if regime_slices:
                regime_metrics = [s.oos_metrics for s in regime_slices]
                regime_scores = [s.oos_score for s in regime_slices]

                aggregated = self.performance_evaluator.aggregate_results(regime_metrics)

                regime_stats[regime] = {
                    "count": len(regime_slices),
                    "median_score": np.median(regime_scores),
                    "profit_factor": aggregated.profit_factor,
                    "win_rate": aggregated.win_rate,
                    "max_drawdown": aggregated.max_drawdown,
                    "profitable_ratio": sum(1 for m in regime_metrics if m.total_return > 0) / len(regime_metrics),
                }

        return regime_stats

    def print_walkforward_results(self, result: WalkForwardResult, title: str = "워크포워드 분석 결과"):
        """워크포워드 결과 출력"""
        print(f"\n📊 {title}")
        print("=" * 80)

        print(f"OOS 기준 통과: {'✅ 예' if result.passed_oos_criteria else '❌ 아니오'}")
        print(f"메디안 점수: {result.median_score:.4f}")
        print(f"일관성 비율: {result.consistency_ratio:.1%}")

        # 집계된 메트릭
        agg = result.aggregated_metrics
        print(f"\n📈 집계된 OOS 성과:")
        print(f"   Profit Factor: {agg.profit_factor:.2f}")
        print(f"   승률: {agg.win_rate:.1%}")
        print(f"   Sortino Ratio: {agg.sortino_ratio:.2f}")
        print(f"   Calmar Ratio: {agg.calmar_ratio:.2f}")
        print(f"   최대 드로우다운: {agg.max_drawdown:.1%}")

        # 레짐별 성과
        print(f"\n🌊 레짐별 성과:")
        for regime, stats in result.regime_performance.items():
            if stats["count"] > 0:
                print(
                    f"   {regime}: {stats['count']}개 슬라이스, "
                    f"PF {stats['profit_factor']:.2f}, "
                    f"수익성 {stats['profitable_ratio']:.1%}"
                )

        # 슬라이스별 상세
        print(f"\n📋 슬라이스별 상세:")
        for slice_obj in result.slices:
            if slice_obj.oos_metrics:
                print(
                    f"   슬라이스 {slice_obj.slice_id} ({slice_obj.regime}): "
                    f"PF {slice_obj.oos_metrics.profit_factor:.2f}, "
                    f"승률 {slice_obj.oos_metrics.win_rate:.1%}, "
                    f"거래 {slice_obj.oos_metrics.total_trades}개"
                )


def main():
    """테스트 실행"""
    # 데이터 엔진 초기화
    data_engine = FastDataEngine()

    # 성과 평가자 초기화
    performance_evaluator = PerformanceEvaluator()

    # 국소 최적화자 초기화
    local_optimizer = LocalSearchOptimizer(data_engine, performance_evaluator)

    # 워크포워드 분석자 초기화
    wf_analyzer = WalkForwardAnalyzer(data_engine, performance_evaluator, local_optimizer)

    # 테스트 데이터 생성
    dates = pd.date_range("2023-01-01", "2024-12-31", freq="15T")
    test_data = pd.DataFrame(
        {
            "time": dates,
            "open": 2000 + np.random.randn(len(dates)) * 50,
            "high": 2050 + np.random.randn(len(dates)) * 50,
            "low": 1950 + np.random.randn(len(dates)) * 50,
            "close": 2000 + np.random.randn(len(dates)) * 50,
            "volume": 1000 + np.random.randn(len(dates)) * 100,
        }
    )
    test_data.set_index("time", inplace=True)

    # 가상의 후보들
    test_candidates = [
        ({"target_r": 2.5, "stop_atr_mult": 0.1, "swing_len": 5}, 0.8, None),
        ({"target_r": 3.0, "stop_atr_mult": 0.08, "swing_len": 4}, 0.7, None),
    ]

    # 가상의 전략 함수
    def dummy_strategy_func(params):
        return params

    # 워크포워드 분석 실행
    result = wf_analyzer.run_walkforward_analysis(test_candidates, dummy_strategy_func, test_data)

    # 결과 출력
    wf_analyzer.print_walkforward_results(result)


if __name__ == "__main__":
    main()
