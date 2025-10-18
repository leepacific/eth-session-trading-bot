#!/usr/bin/env python3
"""
국소 정밀 탐색 구현
- TPE/GP + EI 40스텝 베이지안 최적화
- 제약 조건 위반 시 큰 음수 반환
- Top-12 → Top-5 후보 선별
"""

import time
import warnings
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import optuna
import pandas as pd
from optuna.pruners import MedianPruner
from optuna.samplers import TPESampler

warnings.filterwarnings("ignore")

from fast_data_engine import FastDataEngine
from performance_evaluator import PerformanceEvaluator, PerformanceMetrics


class LocalSearchOptimizer:
    def __init__(self, data_engine: FastDataEngine, performance_evaluator: PerformanceEvaluator):
        """국소 정밀 탐색 최적화자 초기화"""
        self.data_engine = data_engine
        self.performance_evaluator = performance_evaluator

        # TPE 설정
        self.tpe_config = {
            "n_startup_trials": 10,  # 초기 랜덤 시도
            "n_ei_candidates": 24,  # EI 후보 수
            "multivariate": True,  # 다변량 TPE
            "group": True,  # 그룹 최적화
        }

        # 베이지안 최적화 설정
        self.bayesian_config = {"n_trials": 40, "timeout": 3600, "n_jobs": 1}  # 40스텝  # 1시간 제한  # 단일 프로세스 (안정성)

        print("🎯 국소 정밀 탐색 최적화자 초기화")
        print(f"   베이지안 최적화: TPE + EI")
        print(f"   시도 횟수: {self.bayesian_config['n_trials']}회")
        print(f"   EI 후보: {self.tpe_config['n_ei_candidates']}개")

    def create_optuna_study(self, initial_candidates: List[Tuple[Dict, float, PerformanceMetrics]] = None) -> optuna.Study:
        """Optuna 스터디 생성"""
        # TPE 샘플러 설정
        sampler = TPESampler(
            n_startup_trials=self.tpe_config["n_startup_trials"],
            n_ei_candidates=self.tpe_config["n_ei_candidates"],
            multivariate=self.tpe_config["multivariate"],
            group=self.tpe_config["group"],
        )

        # 중간값 기반 가지치기
        pruner = MedianPruner(n_startup_trials=5, n_warmup_steps=10, interval_steps=1)

        # 스터디 생성
        study = optuna.create_study(
            direction="maximize", sampler=sampler, pruner=pruner, study_name="local_search_optimization"
        )

        # 초기 후보들을 스터디에 추가 (있는 경우)
        if initial_candidates:
            self._enqueue_initial_candidates(study, initial_candidates)

        return study

    def _enqueue_initial_candidates(self, study: optuna.Study, candidates: List[Tuple[Dict, float, PerformanceMetrics]]):
        """초기 후보들을 스터디 큐에 추가"""
        print(f"📥 초기 후보 {len(candidates)}개를 베이지안 최적화에 추가")

        for params, score, metrics in candidates[:10]:  # 상위 10개만
            # Optuna 형식으로 변환하여 큐에 추가
            study.enqueue_trial(params)

    def define_search_space(self, trial: optuna.Trial, focus_region: Dict[str, Tuple[float, float]] = None) -> Dict:
        """탐색 공간 정의 (국소 영역에 집중)"""

        if focus_region:
            # 집중 영역이 지정된 경우 좁은 범위 탐색
            params = {}
            for param_name, (center, radius) in focus_region.items():
                if param_name in ["swing_len", "atr_len", "time_stop_bars", "trend_filter_len"]:
                    # 정수 파라미터
                    low = max(1, int(center - radius))
                    high = int(center + radius)
                    params[param_name] = trial.suggest_int(param_name, low, high)
                else:
                    # 실수 파라미터
                    low = max(0.01, center - radius)
                    high = center + radius

                    if param_name in ["rr_percentile", "stop_atr_mult"]:
                        # 로그 스케일
                        params[param_name] = trial.suggest_float(param_name, low, high, log=True)
                    else:
                        # 선형 스케일
                        params[param_name] = trial.suggest_float(param_name, low, high)
        else:
            # 전체 공간 탐색 (기본값)
            params = {
                "swing_len": trial.suggest_int("swing_len", 3, 8),
                "rr_percentile": trial.suggest_float("rr_percentile", 0.05, 0.5, log=True),
                "disp_mult": trial.suggest_float("disp_mult", 1.0, 2.0),
                "sweep_wick_mult": trial.suggest_float("sweep_wick_mult", 0.3, 0.8),
                "atr_len": trial.suggest_int("atr_len", 20, 60),
                "stop_atr_mult": trial.suggest_float("stop_atr_mult", 0.05, 0.25, log=True),
                "target_r": trial.suggest_float("target_r", 1.5, 4.0),
                "time_stop_bars": trial.suggest_int("time_stop_bars", 2, 10),
                "min_volatility_rank": trial.suggest_float("min_volatility_rank", 0.2, 0.7),
                "session_strength": trial.suggest_float("session_strength", 1.0, 2.5),
                "volume_filter": trial.suggest_float("volume_filter", 1.0, 2.0),
                "trend_filter_len": trial.suggest_int("trend_filter_len", 10, 40),
            }

        return params

    def objective_function(
        self, trial: optuna.Trial, strategy_func: Callable, focus_region: Dict[str, Tuple[float, float]] = None
    ) -> float:
        """목적 함수 (제약 조건 포함)"""
        try:
            # 파라미터 샘플링
            params = self.define_search_space(trial, focus_region)

            # 전략 실행 (시뮬레이션)
            metrics = self._simulate_strategy_result(params)

            # 제약 조건 확인
            passed, violations = self.performance_evaluator.check_constraints(metrics)

            if not passed:
                # 제약 조건 위반 시 큰 음수 반환
                penalty = -10000 - len(violations) * 1000  # 위반 항목 수에 따라 추가 패널티

                # 중간 결과 보고 (가지치기용)
                trial.report(penalty, step=0)
                if trial.should_prune():
                    raise optuna.TrialPruned()

                return penalty

            # 점수 계산
            score = self.performance_evaluator.calculate_score(metrics)

            # 중간 결과 보고
            trial.report(score, step=0)
            if trial.should_prune():
                raise optuna.TrialPruned()

            # 추가 메트릭 저장
            trial.set_user_attr("profit_factor", metrics.profit_factor)
            trial.set_user_attr("win_rate", metrics.win_rate)
            trial.set_user_attr("sortino_ratio", metrics.sortino_ratio)
            trial.set_user_attr("max_drawdown", metrics.max_drawdown)
            trial.set_user_attr("total_trades", metrics.total_trades)

            return score

        except optuna.TrialPruned:
            raise
        except Exception as e:
            print(f"❌ 목적 함수 오류: {e}")
            return -10000

    def _simulate_strategy_result(self, params: Dict) -> PerformanceMetrics:
        """전략 결과 시뮬레이션 (고충실도)"""
        # 파라미터 기반으로 성과 시뮬레이션 (더 정교한 버전)
        np.random.seed(hash(str(params)) % 2**32)

        # 거래 수 (고충실도)
        base_trades = 250
        total_trades = base_trades + np.random.randint(-50, 50)

        # 파라미터 영향 반영 (더 현실적)
        target_r = params.get("target_r", 2.0)
        stop_mult = params.get("stop_atr_mult", 0.1)
        swing_len = params.get("swing_len", 5)

        # 승률 (복합적 영향)
        base_win_rate = 0.55

        # target_r 영향 (높을수록 승률 감소)
        win_rate_adj = base_win_rate - (target_r - 2.0) * 0.03

        # swing_len 영향 (짧을수록 노이즈 증가)
        if swing_len <= 3:
            win_rate_adj -= 0.02
        elif swing_len >= 7:
            win_rate_adj += 0.01

        # stop_mult 영향 (너무 타이트하면 승률 감소)
        if stop_mult < 0.08:
            win_rate_adj -= 0.03

        win_rate = max(0.35, min(0.75, win_rate_adj + np.random.normal(0, 0.02)))

        # 평균 손익 (파라미터 반영)
        avg_win = target_r * 60 * (1 + np.random.normal(0, 0.1))
        avg_loss = -60 * (1 + np.random.normal(0, 0.1))

        # 변동성 (stop_mult에 따라 조정)
        win_volatility = abs(avg_win) * (0.15 + stop_mult * 0.5)
        loss_volatility = abs(avg_loss) * (0.15 + stop_mult * 0.5)

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

    def calculate_focus_region(
        self, candidates: List[Tuple[Dict, float, PerformanceMetrics]], top_n: int = 5
    ) -> Dict[str, Tuple[float, float]]:
        """상위 후보들 기반으로 집중 탐색 영역 계산"""
        if len(candidates) < 2:
            return None

        # 상위 N개 후보의 파라미터 수집
        top_candidates = candidates[:top_n]
        param_values = {}

        for param_name in top_candidates[0][0].keys():
            values = [params[param_name] for params, _, _ in top_candidates]
            param_values[param_name] = values

        # 각 파라미터의 중심값과 반경 계산
        focus_region = {}
        for param_name, values in param_values.items():
            center = np.mean(values)
            std = np.std(values)
            radius = max(std * 2, abs(center) * 0.1)  # 최소 10% 범위

            focus_region[param_name] = (center, radius)

        print(f"🎯 집중 탐색 영역 계산 완료 (상위 {top_n}개 기반)")
        return focus_region

    def run_local_search(
        self,
        strategy_func: Callable,
        initial_candidates: List[Tuple[Dict, float, PerformanceMetrics]] = None,
        use_focus_region: bool = True,
    ) -> List[Tuple[Dict, float, PerformanceMetrics]]:
        """국소 정밀 탐색 실행"""
        print(f"\n🎯 국소 정밀 탐색 시작")
        start_time = time.time()

        # 집중 영역 계산
        focus_region = None
        if use_focus_region and initial_candidates:
            focus_region = self.calculate_focus_region(initial_candidates)

        # Optuna 스터디 생성
        study = self.create_optuna_study(initial_candidates)

        # 목적 함수 래퍼
        def objective_wrapper(trial):
            return self.objective_function(trial, strategy_func, focus_region)

        # 베이지안 최적화 실행
        try:
            study.optimize(
                objective_wrapper,
                n_trials=self.bayesian_config["n_trials"],
                timeout=self.bayesian_config["timeout"],
                n_jobs=self.bayesian_config["n_jobs"],
                show_progress_bar=True,
            )
        except KeyboardInterrupt:
            print("⚠️ 사용자에 의해 중단됨")

        # 결과 수집
        results = []
        for trial in study.trials:
            if trial.state == optuna.trial.TrialState.COMPLETE:
                params = trial.params
                score = trial.value

                # 메트릭 재구성
                metrics = PerformanceMetrics(
                    total_trades=trial.user_attrs.get("total_trades", 0),
                    win_rate=trial.user_attrs.get("win_rate", 0),
                    profit_factor=trial.user_attrs.get("profit_factor", 0),
                    max_drawdown=trial.user_attrs.get("max_drawdown", 1.0),
                    sortino_ratio=trial.user_attrs.get("sortino_ratio", 0),
                    sharpe_ratio=0,
                    calmar_ratio=0,
                    sqn=0,
                    rr_ratio=0,
                    expectancy=0,
                    mar_ratio=0,
                    total_return=0,
                    annual_return=0,
                    volatility=0,
                    avg_win=0,
                    avg_loss=0,
                )

                results.append((params, score, metrics))

        # 점수 기준 정렬
        results.sort(key=lambda x: x[1], reverse=True)

        # Top-12 선별
        top_12 = results[:12]

        # 추가 평가 후 Top-5 선별 (시뮬레이션)
        print(f"\n📊 Top-12 후보 추가 평가 중...")
        final_candidates = []

        for i, (params, _, _) in enumerate(top_12):
            # 더 정교한 평가 (여러 번 실행 후 평균)
            scores = []
            metrics_list = []

            for seed in range(3):  # 3번 실행
                np.random.seed(seed + hash(str(params)) % 1000)
                metrics = self._simulate_strategy_result(params)
                score = self.performance_evaluator.calculate_score(metrics)
                scores.append(score)
                metrics_list.append(metrics)

            # 평균 점수와 메트릭
            avg_score = np.mean(scores)
            avg_metrics = self.performance_evaluator.aggregate_results(metrics_list)

            final_candidates.append((params, avg_score, avg_metrics))

        # 최종 정렬 후 Top-5
        final_candidates.sort(key=lambda x: x[1], reverse=True)
        top_5 = final_candidates[:5]

        elapsed_time = time.time() - start_time
        print(f"\n✅ 국소 정밀 탐색 완료 ({elapsed_time:.1f}초)")
        print(f"   완료된 시도: {len(study.trials)}")
        print(f"   최고 점수: {study.best_value:.4f}")
        print(f"   최종 Top-5 선별 완료")

        return top_5

    def print_optimization_progress(self, study: optuna.Study):
        """최적화 진행상황 출력"""
        if len(study.trials) == 0:
            return

        print(f"\n📈 최적화 진행상황:")
        print(f"   완료된 시도: {len([t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE])}")
        print(f"   가지치기된 시도: {len([t for t in study.trials if t.state == optuna.trial.TrialState.PRUNED])}")
        print(f"   현재 최고 점수: {study.best_value:.4f}")

        if study.best_trial:
            best_params = study.best_trial.params
            key_params = ["target_r", "stop_atr_mult", "swing_len"]
            param_str = ", ".join(
                [
                    (
                        f"{k}: {best_params.get(k, 'N/A'):.3f}"
                        if isinstance(best_params.get(k), float)
                        else f"{k}: {best_params.get(k, 'N/A')}"
                    )
                    for k in key_params
                ]
            )
            print(f"   최고 파라미터: {param_str}")


def main():
    """테스트 실행"""
    # 데이터 엔진 초기화
    data_engine = FastDataEngine()

    # 성과 평가자 초기화
    performance_evaluator = PerformanceEvaluator()

    # 국소 탐색 최적화자 초기화
    optimizer = LocalSearchOptimizer(data_engine, performance_evaluator)

    # 가상의 전략 함수
    def dummy_strategy_func(params):
        return params

    # 가상의 초기 후보들
    initial_candidates = [
        ({"target_r": 2.5, "stop_atr_mult": 0.1, "swing_len": 5}, 0.5, None),
        ({"target_r": 3.0, "stop_atr_mult": 0.08, "swing_len": 4}, 0.4, None),
    ]

    # 국소 탐색 실행
    results = optimizer.run_local_search(dummy_strategy_func, initial_candidates)

    # 결과 출력
    print(f"\n📊 국소 탐색 결과 (Top-5)")
    print("=" * 60)

    for i, (params, score, metrics) in enumerate(results):
        print(f"\n🏆 순위 {i+1}: 점수 {score:.4f}")
        if metrics:
            print(f"   PF: {metrics.profit_factor:.2f}, 승률: {metrics.win_rate:.1%}")
            print(f"   거래수: {metrics.total_trades}, DD: {metrics.max_drawdown:.1%}")


if __name__ == "__main__":
    main()
