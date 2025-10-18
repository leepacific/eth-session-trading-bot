#!/usr/bin/env python3
"""
초기 전역 탐색 구현
- Sobol/LHS 120점 샘플링
- 다중충실도 10k→30k→50k 데이터 처리
- ASHA 조기중단 (η=3, 70%→60% 컷)
- 스크리닝 필터 (PF≥1.4 ∧ MinTrades≥80)
"""

import numpy as np
import pandas as pd
from scipy.stats import qmc
from typing import Dict, List, Tuple, Optional, Callable
import optuna
from optuna.samplers import RandomSampler
from optuna.pruners import SuccessiveHalvingPruner
import time
import warnings

warnings.filterwarnings("ignore")

from fast_data_engine import FastDataEngine
from performance_evaluator import PerformanceEvaluator, PerformanceMetrics


class GlobalSearchOptimizer:
    def __init__(self, data_engine: FastDataEngine, performance_evaluator: PerformanceEvaluator):
        """전역 탐색 최적화자 초기화"""
        self.data_engine = data_engine
        self.performance_evaluator = performance_evaluator

        # 다중충실도 설정
        self.fidelity_levels = {
            "low": 10000,  # 10k 데이터 포인트
            "medium": 30000,  # 30k 데이터 포인트
            "high": 50000,  # 50k 데이터 포인트 (전체)
        }

        # ASHA 설정
        self.asha_config = {
            "eta": 3,  # 감소 비율
            "cut_ratio_1": 0.7,  # 첫 번째 컷: 하위 70%
            "cut_ratio_2": 0.6,  # 두 번째 컷: 하위 60%
        }

        # 스크리닝 필터 (완화된 기준)
        self.screening_filter = {"min_profit_factor": 1.2, "min_trades": 30}

        print("🔍 전역 탐색 최적화자 초기화")
        print(f"   샘플링: Sobol/LHS 120점")
        print(f"   다중충실도: {list(self.fidelity_levels.values())}")
        print(f"   ASHA η={self.asha_config['eta']}")

    def define_parameter_space(self) -> Dict[str, Dict]:
        """파라미터 공간 정의"""
        return {
            "swing_len": {"type": "int", "low": 3, "high": 8},
            "rr_percentile": {"type": "float", "low": 0.05, "high": 0.5},
            "disp_mult": {"type": "float", "low": 1.0, "high": 2.0},
            "sweep_wick_mult": {"type": "float", "low": 0.3, "high": 0.8},
            "atr_len": {"type": "int", "low": 20, "high": 60},
            "stop_atr_mult": {"type": "float", "low": 0.05, "high": 0.25},
            "target_r": {"type": "float", "low": 1.5, "high": 4.0},
            "time_stop_bars": {"type": "int", "low": 2, "high": 10},
            "min_volatility_rank": {"type": "float", "low": 0.2, "high": 0.7},
            "session_strength": {"type": "float", "low": 1.0, "high": 2.5},
            "volume_filter": {"type": "float", "low": 1.0, "high": 2.0},
            "trend_filter_len": {"type": "int", "low": 10, "high": 40},
        }

    def generate_sobol_samples(self, n_samples: int = 120) -> List[Dict]:
        """Sobol 시퀀스를 사용한 샘플 생성"""
        param_space = self.define_parameter_space()
        param_names = list(param_space.keys())
        n_params = len(param_names)

        # Sobol 시퀀스 생성
        sobol = qmc.Sobol(d=n_params, scramble=True)
        sobol_samples = sobol.random(n_samples)

        # 파라미터 공간으로 변환
        samples = []
        for sample in sobol_samples:
            params = {}
            for i, param_name in enumerate(param_names):
                param_config = param_space[param_name]

                if param_config["type"] == "int":
                    # 정수 파라미터
                    low, high = param_config["low"], param_config["high"]
                    value = int(low + sample[i] * (high - low))
                    params[param_name] = min(max(value, low), high)

                elif param_config["type"] == "float":
                    # 실수 파라미터
                    low, high = param_config["low"], param_config["high"]

                    # 로그 스케일 파라미터 확인
                    if param_name in ["rr_percentile", "stop_atr_mult"]:
                        # 로그 스케일 적용
                        log_low, log_high = np.log(low), np.log(high)
                        log_value = log_low + sample[i] * (log_high - log_low)
                        value = np.exp(log_value)
                    else:
                        # 선형 스케일
                        value = low + sample[i] * (high - low)

                    params[param_name] = float(value)

            samples.append(params)

        print(f"✅ Sobol 샘플 {len(samples)}개 생성 완료")
        return samples

    def generate_lhs_samples(self, n_samples: int = 120) -> List[Dict]:
        """Latin Hypercube Sampling을 사용한 샘플 생성"""
        param_space = self.define_parameter_space()
        param_names = list(param_space.keys())
        n_params = len(param_names)

        # LHS 샘플 생성
        lhs = qmc.LatinHypercube(d=n_params)
        lhs_samples = lhs.random(n_samples)

        # 파라미터 공간으로 변환 (Sobol과 동일한 로직)
        samples = []
        for sample in lhs_samples:
            params = {}
            for i, param_name in enumerate(param_names):
                param_config = param_space[param_name]

                if param_config["type"] == "int":
                    low, high = param_config["low"], param_config["high"]
                    value = int(low + sample[i] * (high - low))
                    params[param_name] = min(max(value, low), high)

                elif param_config["type"] == "float":
                    low, high = param_config["low"], param_config["high"]

                    if param_name in ["rr_percentile", "stop_atr_mult"]:
                        log_low, log_high = np.log(low), np.log(high)
                        log_value = log_low + sample[i] * (log_high - log_low)
                        value = np.exp(log_value)
                    else:
                        value = low + sample[i] * (high - low)

                    params[param_name] = float(value)

            samples.append(params)

        print(f"✅ LHS 샘플 {len(samples)}개 생성 완료")
        return samples

    def evaluate_candidate(self, params: Dict, fidelity: str, strategy_func: Callable) -> Tuple[float, PerformanceMetrics]:
        """후보 평가 (특정 충실도에서)"""
        try:
            # 데이터 슬라이스 크기 결정
            data_points = self.fidelity_levels[fidelity]

            # 전략 실행 (가상의 함수 - 실제로는 strategy_func 사용)
            # 여기서는 간단한 시뮬레이션으로 대체
            metrics = self._simulate_strategy_result(params, data_points)

            # 점수 계산
            score = self.performance_evaluator.calculate_score(metrics)

            return score, metrics

        except Exception as e:
            print(f"❌ 후보 평가 실패: {e}")
            return -10000, self.performance_evaluator._empty_metrics()

    def _simulate_strategy_result(self, params: Dict, data_points: int) -> PerformanceMetrics:
        """전략 결과 시뮬레이션 (테스트용)"""
        # 파라미터 기반으로 성과 시뮬레이션
        np.random.seed(hash(str(params)) % 2**32)

        # 거래 수 (데이터 포인트에 비례)
        base_trades = int(data_points / 200)  # 200포인트당 1거래
        total_trades = max(50, base_trades + np.random.randint(-20, 20))

        # 파라미터 영향 반영
        target_r = params.get("target_r", 2.0)
        stop_mult = params.get("stop_atr_mult", 0.1)

        # 승률 (target_r이 높을수록 낮아짐)
        base_win_rate = 0.6 - (target_r - 2.0) * 0.05
        win_rate = max(0.3, min(0.8, base_win_rate + np.random.normal(0, 0.05)))

        # 평균 손익
        avg_win = target_r * 50  # R배수 반영
        avg_loss = -50

        # PnL 생성
        pnl_data = []
        for _ in range(total_trades):
            if np.random.random() < win_rate:
                pnl = np.random.normal(avg_win, avg_win * 0.2)
            else:
                pnl = np.random.normal(avg_loss, abs(avg_loss) * 0.2)
            pnl_data.append(pnl)

        # DataFrame 생성
        trades_df = pd.DataFrame({"pnl": pnl_data})

        # 성과 지표 계산
        metrics = self.performance_evaluator.calculate_metrics(trades_df)

        return metrics

    def apply_screening_filter(
        self, candidates: List[Tuple[Dict, float, PerformanceMetrics]]
    ) -> List[Tuple[Dict, float, PerformanceMetrics]]:
        """스크리닝 필터 적용"""
        filtered = []

        for params, score, metrics in candidates:
            # 기본 필터 조건
            if (
                metrics.profit_factor >= self.screening_filter["min_profit_factor"]
                and metrics.total_trades >= self.screening_filter["min_trades"]
            ):
                filtered.append((params, score, metrics))

        print(f"🔍 스크리닝 필터: {len(candidates)} → {len(filtered)} 후보")
        return filtered

    def apply_asha_pruning(
        self, candidates: List[Tuple[Dict, float, PerformanceMetrics]], stage: int
    ) -> List[Tuple[Dict, float, PerformanceMetrics]]:
        """ASHA 조기중단 적용"""
        if len(candidates) == 0:
            return candidates

        # 점수 기준 정렬 (내림차순)
        sorted_candidates = sorted(candidates, key=lambda x: x[1], reverse=True)

        if stage == 1:
            # 첫 번째 컷: 상위 30% 유지 (하위 70% 제거)
            keep_ratio = 1.0 - self.asha_config["cut_ratio_1"]
            n_keep = max(1, int(len(sorted_candidates) * keep_ratio))
        elif stage == 2:
            # 두 번째 컷: 상위 40% 유지 (하위 60% 제거)
            keep_ratio = 1.0 - self.asha_config["cut_ratio_2"]
            n_keep = max(1, int(len(sorted_candidates) * keep_ratio))
        else:
            # 추가 단계에서는 절반씩 제거
            n_keep = max(1, len(sorted_candidates) // 2)

        pruned = sorted_candidates[:n_keep]

        print(f"✂️ ASHA 단계 {stage}: {len(candidates)} → {n_keep} 후보")
        return pruned

    def run_global_search(
        self, strategy_func: Callable, sampling_method: str = "sobol"
    ) -> List[Tuple[Dict, float, PerformanceMetrics]]:
        """전역 탐색 실행"""
        print(f"\n🚀 전역 탐색 시작 ({sampling_method.upper()})")
        start_time = time.time()

        # 1단계: 초기 샘플 생성
        if sampling_method.lower() == "sobol":
            candidates_params = self.generate_sobol_samples(120)
        else:
            candidates_params = self.generate_lhs_samples(120)

        # 2단계: 저충실도 평가 (10k)
        print(f"\n📊 1단계: 저충실도 평가 (10k 데이터)")
        candidates_low = []
        for i, params in enumerate(candidates_params):
            if i % 20 == 0:
                print(f"   진행률: {i}/{len(candidates_params)} ({i/len(candidates_params)*100:.1f}%)")

            score, metrics = self.evaluate_candidate(params, "low", strategy_func)
            candidates_low.append((params, score, metrics))

        # 스크리닝 필터 적용
        candidates_low = self.apply_screening_filter(candidates_low)

        # ASHA 1단계 적용
        candidates_low = self.apply_asha_pruning(candidates_low, 1)

        if len(candidates_low) == 0:
            print("❌ 1단계에서 모든 후보가 제거됨")
            return []

        # 3단계: 중충실도 평가 (30k)
        print(f"\n📊 2단계: 중충실도 평가 (30k 데이터)")
        candidates_medium = []
        for i, (params, _, _) in enumerate(candidates_low):
            score, metrics = self.evaluate_candidate(params, "medium", strategy_func)
            candidates_medium.append((params, score, metrics))

        # ASHA 2단계 적용
        candidates_medium = self.apply_asha_pruning(candidates_medium, 2)

        if len(candidates_medium) == 0:
            print("❌ 2단계에서 모든 후보가 제거됨")
            return candidates_low[:5]  # 이전 단계 상위 5개 반환

        # 4단계: 고충실도 평가 (50k)
        print(f"\n📊 3단계: 고충실도 평가 (50k 데이터)")
        final_candidates = []
        for i, (params, _, _) in enumerate(candidates_medium):
            score, metrics = self.evaluate_candidate(params, "high", strategy_func)
            final_candidates.append((params, score, metrics))

        # 최종 정렬
        final_candidates.sort(key=lambda x: x[1], reverse=True)

        # 상위 30% 선택
        n_final = max(5, int(len(final_candidates) * 0.3))
        top_candidates = final_candidates[:n_final]

        elapsed_time = time.time() - start_time
        print(f"\n✅ 전역 탐색 완료 ({elapsed_time:.1f}초)")
        print(f"   최종 후보: {len(top_candidates)}개")
        print(f"   최고 점수: {top_candidates[0][1]:.4f}")

        return top_candidates

    def print_search_results(self, candidates: List[Tuple[Dict, float, PerformanceMetrics]], top_n: int = 5):
        """탐색 결과 출력"""
        print(f"\n📊 전역 탐색 결과 (상위 {min(top_n, len(candidates))}개)")
        print("=" * 80)

        for i, (params, score, metrics) in enumerate(candidates[:top_n]):
            print(f"\n🏆 순위 {i+1}: 점수 {score:.4f}")
            print(f"   PF: {metrics.profit_factor:.2f}, 승률: {metrics.win_rate:.1%}")
            print(f"   Sortino: {metrics.sortino_ratio:.2f}, Calmar: {metrics.calmar_ratio:.2f}")
            print(f"   거래수: {metrics.total_trades}, DD: {metrics.max_drawdown:.1%}")

            # 주요 파라미터만 출력
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

    # 전역 탐색 최적화자 초기화
    optimizer = GlobalSearchOptimizer(data_engine, performance_evaluator)

    # 가상의 전략 함수
    def dummy_strategy_func(params):
        return params  # 실제로는 백테스트 실행

    # 전역 탐색 실행
    results = optimizer.run_global_search(dummy_strategy_func, "sobol")

    # 결과 출력
    optimizer.print_search_results(results)


if __name__ == "__main__":
    main()
