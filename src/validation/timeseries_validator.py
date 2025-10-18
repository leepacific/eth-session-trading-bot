#!/usr/bin/env python3
"""
시계열 검증 시스템 구현
- Purged K-Fold=5 + Embargo=평균보유기간×2
- fold별 Score 메디안 − DD 패널티 랭킹
- Top-3 파라미터 승급 시스템
- 데이터 누수 방지 검증 로직
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
class FoldResult:
    """Fold 결과 데이터 클래스"""

    fold_id: int
    train_start: int
    train_end: int
    test_start: int
    test_end: int
    metrics: PerformanceMetrics
    score: float
    params: Dict


class TimeSeriesValidator:
    def __init__(self, data_engine: FastDataEngine, performance_evaluator: PerformanceEvaluator):
        """시계열 검증자 초기화"""
        self.data_engine = data_engine
        self.performance_evaluator = performance_evaluator

        # Purged K-Fold 설정
        self.kfold_config = {
            "n_splits": 5,  # K=5
            "test_size": 0.2,  # 각 fold에서 테스트 비율
            "purge_pct": 0.01,  # 퍼지 비율 (1%)
            "embargo_multiplier": 2,  # 엠바고 = 평균보유기간 × 2
        }

        # 검증 설정
        self.validation_config = {
            "min_test_trades": 20,  # 최소 테스트 거래 수
            "consistency_threshold": 0.6,  # 60% 이상 fold에서 수익성 유지
            "stability_weight": 0.3,  # 안정성 가중치
        }

        print("🔍 시계열 검증 시스템 초기화")
        print(f"   Purged K-Fold: {self.kfold_config['n_splits']}개 fold")
        print(f"   퍼지 비율: {self.kfold_config['purge_pct']*100}%")
        print(f"   엠바고 배수: {self.kfold_config['embargo_multiplier']}×")

    def estimate_average_holding_period(self, sample_trades: List[Dict]) -> int:
        """평균 보유 기간 추정 (바 단위)"""
        if not sample_trades:
            return 4  # 기본값: 4바 (1시간)

        holding_periods = []
        for trade in sample_trades:
            if "bars_held" in trade:
                holding_periods.append(trade["bars_held"])
            elif "entry_time" in trade and "exit_time" in trade:
                # 시간 차이로 계산 (15분봉 기준)
                entry_time = pd.to_datetime(trade["entry_time"])
                exit_time = pd.to_datetime(trade["exit_time"])
                time_diff = (exit_time - entry_time).total_seconds() / 900  # 15분 = 900초
                holding_periods.append(max(1, int(time_diff)))

        if holding_periods:
            avg_holding = int(np.mean(holding_periods))
            print(f"📊 평균 보유 기간: {avg_holding}바 ({avg_holding*15}분)")
            return max(2, avg_holding)  # 최소 2바
        else:
            return 4  # 기본값

    def create_purged_kfold_splits(self, data_length: int, avg_holding_period: int) -> List[Tuple[np.ndarray, np.ndarray]]:
        """Purged K-Fold 분할 생성"""
        n_splits = self.kfold_config["n_splits"]
        test_size = self.kfold_config["test_size"]
        purge_pct = self.kfold_config["purge_pct"]
        embargo_bars = avg_holding_period * self.kfold_config["embargo_multiplier"]

        print(f"🔄 Purged K-Fold 분할 생성:")
        print(f"   데이터 길이: {data_length}")
        print(f"   엠바고: {embargo_bars}바")

        splits = []

        # 각 fold의 테스트 구간 크기
        test_size_bars = int(data_length * test_size / n_splits)

        for fold in range(n_splits):
            # 테스트 구간 정의
            test_start = fold * test_size_bars
            test_end = min(test_start + test_size_bars, data_length)

            # 퍼지 구간 계산
            purge_bars = max(1, int(data_length * purge_pct))

            # 훈련 구간 정의 (테스트 구간 제외 + 퍼지 + 엠바고)
            train_indices = []

            # 테스트 구간 이전 데이터
            if test_start > purge_bars + embargo_bars:
                train_start_1 = 0
                train_end_1 = test_start - purge_bars - embargo_bars
                train_indices.extend(range(train_start_1, train_end_1))

            # 테스트 구간 이후 데이터
            if test_end + purge_bars + embargo_bars < data_length:
                train_start_2 = test_end + purge_bars + embargo_bars
                train_end_2 = data_length
                train_indices.extend(range(train_start_2, train_end_2))

            # 인덱스 배열 생성
            train_idx = np.array(train_indices)
            test_idx = np.array(range(test_start, test_end))

            # 유효성 검사
            if len(train_idx) > 0 and len(test_idx) > 0:
                splits.append((train_idx, test_idx))

                print(f"   Fold {fold+1}: Train {len(train_idx)}, Test {len(test_idx)}")
                print(
                    f"     Train: {train_idx[0] if len(train_idx) > 0 else 'N/A'}-{train_idx[-1] if len(train_idx) > 0 else 'N/A'}"
                )
                print(f"     Test: {test_idx[0]}-{test_idx[-1]}")
            else:
                print(f"   Fold {fold+1}: 스킵 (데이터 부족)")

        return splits

    def validate_no_data_leakage(self, train_idx: np.ndarray, test_idx: np.ndarray, embargo_bars: int) -> bool:
        """데이터 누수 검증"""
        if len(train_idx) == 0 or len(test_idx) == 0:
            return False

        # 테스트 구간
        test_min = test_idx.min()
        test_max = test_idx.max()

        # 훈련 데이터가 테스트 구간과 겹치는지 확인
        for train_point in train_idx:
            # 테스트 구간과 겹침
            if test_min <= train_point <= test_max:
                return False

            # 엠바고 구간 침범 (테스트 구간 전후 embargo_bars 범위)
            if (test_min - embargo_bars <= train_point < test_min) or (test_max < train_point <= test_max + embargo_bars):
                return False

        return True

    def run_fold_validation(
        self, params: Dict, train_idx: np.ndarray, test_idx: np.ndarray, fold_id: int, strategy_func: Callable
    ) -> Optional[FoldResult]:
        """단일 fold 검증 실행"""
        try:
            # 데이터 누수 검증
            embargo_bars = self.estimate_average_holding_period([]) * self.kfold_config["embargo_multiplier"]
            if not self.validate_no_data_leakage(train_idx, test_idx, embargo_bars):
                print(f"❌ Fold {fold_id}: 데이터 누수 감지")
                return None

            # 테스트 데이터로 전략 실행 (시뮬레이션)
            test_metrics = self._simulate_fold_strategy(params, len(test_idx), fold_id)

            # 최소 거래 수 확인
            if test_metrics.total_trades < self.validation_config["min_test_trades"]:
                print(f"⚠️ Fold {fold_id}: 거래 수 부족 ({test_metrics.total_trades})")
                return None

            # 점수 계산
            base_score = self.performance_evaluator.calculate_score(test_metrics)

            # DD 패널티 적용
            dd_penalty = max(0, test_metrics.max_drawdown - 0.15) * 10  # 15% 초과시 패널티
            final_score = base_score - dd_penalty

            return FoldResult(
                fold_id=fold_id,
                train_start=train_idx[0] if len(train_idx) > 0 else 0,
                train_end=train_idx[-1] if len(train_idx) > 0 else 0,
                test_start=test_idx[0],
                test_end=test_idx[-1],
                metrics=test_metrics,
                score=final_score,
                params=params,
            )

        except Exception as e:
            print(f"❌ Fold {fold_id} 검증 실패: {e}")
            return None

    def _simulate_fold_strategy(self, params: Dict, test_length: int, fold_id: int) -> PerformanceMetrics:
        """Fold 전략 시뮬레이션"""
        # 시드 설정 (fold별로 다른 시드)
        np.random.seed(hash(str(params)) % 1000 + fold_id * 100)

        # 거래 수 (테스트 길이에 비례)
        base_trades = max(20, int(test_length / 100))  # 100바당 1거래
        total_trades = base_trades + np.random.randint(-5, 5)

        # 파라미터 영향 (fold별 변동성 추가)
        target_r = params.get("target_r", 2.0)
        stop_mult = params.get("stop_atr_mult", 0.1)

        # Fold별 시장 조건 시뮬레이션
        market_condition = np.random.choice(["bull", "bear", "sideways"], p=[0.3, 0.3, 0.4])

        if market_condition == "bull":
            win_rate_adj = 0.05  # 상승장에서 승률 증가
            volatility_adj = 0.8  # 변동성 감소
        elif market_condition == "bear":
            win_rate_adj = -0.03  # 하락장에서 승률 감소
            volatility_adj = 1.2  # 변동성 증가
        else:  # sideways
            win_rate_adj = 0.0
            volatility_adj = 1.0

        # 승률 계산
        base_win_rate = 0.55 - (target_r - 2.0) * 0.02
        win_rate = max(0.35, min(0.75, base_win_rate + win_rate_adj + np.random.normal(0, 0.03)))

        # 평균 손익
        avg_win = target_r * 50 * (1 + np.random.normal(0, 0.1))
        avg_loss = -50 * (1 + np.random.normal(0, 0.1))

        # 변동성 (시장 조건 반영)
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

    def calculate_cross_validation_score(self, fold_results: List[FoldResult]) -> Tuple[float, Dict]:
        """교차 검증 점수 계산"""
        if not fold_results:
            return -10000, {}

        # 각 fold의 점수 수집
        scores = [result.score for result in fold_results]
        metrics_list = [result.metrics for result in fold_results]

        # 메디안 점수
        median_score = np.median(scores)

        # 일관성 확인 (수익성 있는 fold 비율)
        profitable_folds = sum(1 for result in fold_results if result.metrics.total_return > 0)
        consistency_ratio = profitable_folds / len(fold_results)

        # 안정성 계산 (점수의 IQR)
        q75, q25 = np.percentile(scores, [75, 25])
        iqr = q75 - q25
        stability_penalty = iqr * self.validation_config["stability_weight"]

        # 최종 점수
        final_score = median_score - stability_penalty

        # 일관성 패널티
        if consistency_ratio < self.validation_config["consistency_threshold"]:
            consistency_penalty = (self.validation_config["consistency_threshold"] - consistency_ratio) * 1000
            final_score -= consistency_penalty

        # 통계 정보
        stats = {
            "median_score": median_score,
            "score_std": np.std(scores),
            "score_iqr": iqr,
            "consistency_ratio": consistency_ratio,
            "profitable_folds": profitable_folds,
            "total_folds": len(fold_results),
            "stability_penalty": stability_penalty,
            "final_score": final_score,
        }

        return final_score, stats

    def run_timeseries_validation(
        self, candidates: List[Tuple[Dict, float, PerformanceMetrics]], strategy_func: Callable, data_length: int = 50000
    ) -> List[Tuple[Dict, float, Dict]]:
        """시계열 검증 실행"""
        print(f"\n🔍 시계열 검증 시작 ({len(candidates)}개 후보)")

        # 평균 보유 기간 추정 (샘플 데이터 기반)
        avg_holding_period = self.estimate_average_holding_period([])

        # Purged K-Fold 분할 생성
        splits = self.create_purged_kfold_splits(data_length, avg_holding_period)

        if len(splits) == 0:
            print("❌ 유효한 fold가 없습니다")
            return []

        validated_candidates = []

        for i, (params, original_score, original_metrics) in enumerate(candidates):
            print(f"\n📊 후보 {i+1}/{len(candidates)} 검증 중...")

            fold_results = []

            # 각 fold에서 검증
            for fold_id, (train_idx, test_idx) in enumerate(splits):
                fold_result = self.run_fold_validation(params, train_idx, test_idx, fold_id + 1, strategy_func)

                if fold_result:
                    fold_results.append(fold_result)
                    print(
                        f"   Fold {fold_id+1}: Score {fold_result.score:.4f}, "
                        f"PF {fold_result.metrics.profit_factor:.2f}, "
                        f"거래 {fold_result.metrics.total_trades}개"
                    )

            # 교차 검증 점수 계산
            if len(fold_results) >= 3:  # 최소 3개 fold 필요
                cv_score, stats = self.calculate_cross_validation_score(fold_results)

                validated_candidates.append((params, cv_score, stats))

                print(f"   CV 점수: {cv_score:.4f} (메디안: {stats['median_score']:.4f})")
                print(f"   일관성: {stats['consistency_ratio']:.1%} ({stats['profitable_folds']}/{stats['total_folds']})")
            else:
                print(f"   ❌ 유효한 fold 부족 ({len(fold_results)}/5)")

        # 점수 기준 정렬
        validated_candidates.sort(key=lambda x: x[1], reverse=True)

        # Top-3 선별
        top_3 = validated_candidates[:3]

        print(f"\n✅ 시계열 검증 완료")
        print(f"   검증된 후보: {len(validated_candidates)}개")
        print(f"   Top-3 승급: {len(top_3)}개")

        return top_3

    def print_validation_results(self, results: List[Tuple[Dict, float, Dict]], title: str = "시계열 검증 결과"):
        """검증 결과 출력"""
        print(f"\n📊 {title}")
        print("=" * 80)

        for i, (params, cv_score, stats) in enumerate(results):
            print(f"\n🏆 순위 {i+1}: CV 점수 {cv_score:.4f}")
            print(f"   메디안 점수: {stats['median_score']:.4f}")
            print(f"   점수 표준편차: {stats['score_std']:.4f}")
            print(f"   일관성: {stats['consistency_ratio']:.1%} ({stats['profitable_folds']}/{stats['total_folds']})")
            print(f"   안정성 패널티: {stats['stability_penalty']:.4f}")

            # 주요 파라미터
            key_params = ["target_r", "stop_atr_mult", "swing_len", "rr_percentile"]
            param_str = ", ".join(
                [
                    f"{k}: {params.get(k, 'N/A'):.3f}" if isinstance(params.get(k), float) else f"{k}: {params.get(k, 'N/A')}"
                    for k in key_params
                ]
            )
            print(f"   파라미터: {param_str}")


def main():
    """테스트 실행"""
    # 데이터 엔진 초기화
    data_engine = FastDataEngine()

    # 성과 평가자 초기화
    performance_evaluator = PerformanceEvaluator()

    # 시계열 검증자 초기화
    validator = TimeSeriesValidator(data_engine, performance_evaluator)

    # 가상의 후보들
    test_candidates = [
        ({"target_r": 2.5, "stop_atr_mult": 0.1, "swing_len": 5, "rr_percentile": 0.2}, 0.8, None),
        ({"target_r": 3.0, "stop_atr_mult": 0.08, "swing_len": 4, "rr_percentile": 0.15}, 0.7, None),
        ({"target_r": 2.2, "stop_atr_mult": 0.12, "swing_len": 6, "rr_percentile": 0.25}, 0.6, None),
        ({"target_r": 2.8, "stop_atr_mult": 0.09, "swing_len": 3, "rr_percentile": 0.18}, 0.5, None),
        ({"target_r": 3.2, "stop_atr_mult": 0.07, "swing_len": 7, "rr_percentile": 0.22}, 0.4, None),
    ]

    # 가상의 전략 함수
    def dummy_strategy_func(params):
        return params

    # 시계열 검증 실행
    results = validator.run_timeseries_validation(test_candidates, dummy_strategy_func)

    # 결과 출력
    validator.print_validation_results(results)


if __name__ == "__main__":
    main()
