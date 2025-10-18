#!/usr/bin/env python3
"""
통계적 검증 시스템 구현
- Deflated Sortino (Bailey) 다중가설 보정
- White's Reality Check / SPA 우연성 검정
- 0.6·(MC p5) + 0.4·(WFO-OOS median) 가중합 선택
- Top-1~2 시스템 최종 선택
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

from ..core.performance_evaluator import PerformanceEvaluator, PerformanceMetrics
from montecarlo_simulator import MonteCarloResult
from walkforward_analyzer import WalkForwardResult

@dataclass
class StatisticalTestResult:
    """통계적 검정 결과"""
    test_name: str
    statistic: float
    p_value: float
    critical_value: float
    passed: bool
    confidence_level: float

@dataclass
class ValidationResult:
    """검증 결과"""
    candidate_id: int
    params: Dict
    wfo_score: float
    mc_score: float
    combined_score: float
    statistical_tests: List[StatisticalTestResult]
    deflated_sortino: float
    reality_check_passed: bool
    spa_test_passed: bool
    final_ranking: int
    recommended: bool

class StatisticalValidator:
    def __init__(self, performance_evaluator: PerformanceEvaluator):
        """통계적 검증자 초기화"""
        self.performance_evaluator = performance_evaluator
        
        # 검정 설정
        self.test_config = {
            'confidence_level': 0.05,      # 5% 유의수준
            'deflated_threshold': 0.05,    # Deflated Sortino 임계값
            'reality_check_alpha': 0.05,   # Reality Check 유의수준
            'spa_alpha': 0.05,             # SPA 테스트 유의수준
            'bootstrap_samples': 1000      # 부트스트랩 샘플 수
        }
        
        # 가중치 설정
        self.weight_config = {
            'mc_weight': 0.6,              # 몬테카를로 가중치
            'wfo_weight': 0.4              # 워크포워드 가중치
        }
        
        print("📊 통계적 검증 시스템 초기화")
        print(f"   유의수준: {self.test_config['confidence_level']*100}%")
        print(f"   가중치: MC({self.weight_config['mc_weight']}) + WFO({self.weight_config['wfo_weight']})")
    
    def calculate_deflated_sortino(self, sortino_ratio: float, 
                                 n_tests: int, n_observations: int) -> Tuple[float, bool]:
        """Deflated Sortino Ratio 계산 (Bailey et al.)"""
        if n_tests <= 1 or n_observations <= 1:
            return sortino_ratio, True
        
        # 다중 테스트 보정
        # Bailey의 공식: DSR = SR * sqrt((1 - γ) / (1 - γ * ρ))
        # 여기서는 간소화된 버전 사용
        
        # 독립성 가정하에 보정 계수 계산
        correction_factor = np.sqrt(np.log(n_tests))
        
        # Deflated Sortino Ratio
        deflated_sortino = sortino_ratio / correction_factor
        
        # 임계값과 비교
        threshold = stats.norm.ppf(1 - self.test_config['deflated_threshold'])
        passed = deflated_sortino >= threshold
        
        print(f"📉 Deflated Sortino: {deflated_sortino:.4f} (원본: {sortino_ratio:.4f})")
        print(f"   테스트 수: {n_tests}, 관측치: {n_observations}")
        print(f"   임계값: {threshold:.4f}, 통과: {'✅' if passed else '❌'}")
        
        return deflated_sortino, passed
    
    def whites_reality_check(self, benchmark_returns: np.ndarray, 
                           strategy_returns: List[np.ndarray]) -> Tuple[float, bool]:
        """White's Reality Check 검정"""
        if len(strategy_returns) == 0:
            return 0.0, False
        
        n_strategies = len(strategy_returns)
        n_obs = len(benchmark_returns)
        
        # 각 전략의 초과 수익률 계산
        excess_returns = []
        for strategy_ret in strategy_returns:
            if len(strategy_ret) == len(benchmark_returns):
                excess = strategy_ret - benchmark_returns
                excess_returns.append(excess)
        
        if len(excess_returns) == 0:
            return 0.0, False
        
        # 최대 초과 수익률
        max_excess = np.max([np.mean(excess) for excess in excess_returns])
        
        # 부트스트랩 분포 생성
        bootstrap_max = []
        for _ in range(self.test_config['bootstrap_samples']):
            # 시간 순서를 유지한 블록 부트스트랩
            block_size = max(1, int(np.sqrt(n_obs)))
            n_blocks = (n_obs + block_size - 1) // block_size
            
            bootstrap_excess = []
            for excess in excess_returns:
                boot_series = []
                for _ in range(n_blocks):
                    start_idx = np.random.randint(0, max(1, len(excess) - block_size + 1))
                    block = excess[start_idx:start_idx + block_size]
                    boot_series.extend(block)
                
                boot_series = np.array(boot_series[:n_obs])
                # 평균을 0으로 조정 (귀무가설 하에서)
                boot_series = boot_series - np.mean(boot_series)
                bootstrap_excess.append(np.mean(boot_series))
            
            bootstrap_max.append(np.max(bootstrap_excess))
        
        # p-value 계산
        p_value = np.mean(np.array(bootstrap_max) >= max_excess)
        passed = p_value <= self.test_config['reality_check_alpha']
        
        print(f"🎯 White's Reality Check:")
        print(f"   최대 초과수익률: {max_excess:.6f}")
        print(f"   p-value: {p_value:.4f}")
        print(f"   통과: {'✅' if passed else '❌'}")
        
        return p_value, passed
    
    def spa_test(self, benchmark_returns: np.ndarray, 
                strategy_returns: List[np.ndarray]) -> Tuple[float, bool]:
        """Superior Predictive Ability (SPA) 테스트"""
        if len(strategy_returns) == 0:
            return 0.0, False
        
        n_strategies = len(strategy_returns)
        n_obs = len(benchmark_returns)
        
        # 각 전략의 초과 수익률 계산
        excess_returns = []
        for strategy_ret in strategy_returns:
            if len(strategy_ret) == len(benchmark_returns):
                excess = strategy_ret - benchmark_returns
                excess_returns.append(excess)
        
        if len(excess_returns) == 0:
            return 0.0, False
        
        # 평균 초과 수익률과 표준오차
        mean_excess = np.array([np.mean(excess) for excess in excess_returns])
        std_excess = np.array([np.std(excess) / np.sqrt(len(excess)) for excess in excess_returns])
        
        # t-통계량 계산
        t_stats = mean_excess / (std_excess + 1e-8)  # 0으로 나누기 방지
        max_t_stat = np.max(t_stats)
        
        # 부트스트랩 분포 (SPA 방법)
        bootstrap_max_t = []
        for _ in range(self.test_config['bootstrap_samples']):
            boot_t_stats = []
            
            for i, excess in enumerate(excess_returns):
                # 평균 중심화된 부트스트랩
                centered_excess = excess - np.mean(excess)
                boot_sample = np.random.choice(centered_excess, size=len(excess), replace=True)
                
                boot_mean = np.mean(boot_sample)
                boot_std = np.std(boot_sample) / np.sqrt(len(boot_sample))
                
                # 원래 표준오차로 정규화 (SPA의 핵심)
                boot_t = boot_mean / (std_excess[i] + 1e-8)
                boot_t_stats.append(boot_t)
            
            bootstrap_max_t.append(np.max(boot_t_stats))
        
        # p-value 계산
        p_value = np.mean(np.array(bootstrap_max_t) >= max_t_stat)
        passed = p_value <= self.test_config['spa_alpha']
        
        print(f"🔬 SPA Test:")
        print(f"   최대 t-통계량: {max_t_stat:.4f}")
        print(f"   p-value: {p_value:.4f}")
        print(f"   통과: {'✅' if passed else '❌'}")
        
        return p_value, passed
    
    def calculate_combined_score(self, wfo_result: WalkForwardResult, 
                               mc_result: MonteCarloResult) -> float:
        """가중 결합 점수 계산"""
        # WFO OOS 메디안 점수
        wfo_score = wfo_result.median_score
        
        # MC 5분위 점수 (견고성 기준)
        mc_score = mc_result.robustness_score
        
        # 가중 결합
        combined_score = (self.weight_config['mc_weight'] * mc_score + 
                         self.weight_config['wfo_weight'] * wfo_score)
        
        return combined_score
    
    def validate_candidates(self, candidates: List[Tuple[Dict, WalkForwardResult, MonteCarloResult]]) -> List[ValidationResult]:
        """후보들에 대한 통계적 검증 실행"""
        print(f"\n📊 통계적 검증 시작 ({len(candidates)}개 후보)")
        
        validation_results = []
        
        # 벤치마크 수익률 (첫 번째 후보를 벤치마크로 사용)
        if candidates:
            benchmark_returns = self._extract_returns(candidates[0][1])
        else:
            benchmark_returns = np.array([])
        
        # 모든 전략의 수익률 수집
        all_strategy_returns = []
        for params, wfo_result, mc_result in candidates:
            strategy_returns = self._extract_returns(wfo_result)
            all_strategy_returns.append(strategy_returns)
        
        # 각 후보 검증
        for i, (params, wfo_result, mc_result) in enumerate(candidates):
            print(f"\n🔍 후보 {i+1} 검증 중...")
            
            # 결합 점수 계산
            combined_score = self.calculate_combined_score(wfo_result, mc_result)
            
            # 통계적 검정들
            statistical_tests = []
            
            # 1. Deflated Sortino
            original_sortino = wfo_result.aggregated_metrics.sortino_ratio
            deflated_sortino, deflated_passed = self.calculate_deflated_sortino(
                original_sortino, len(candidates), len(wfo_result.slices)
            )
            
            statistical_tests.append(StatisticalTestResult(
                test_name="Deflated Sortino",
                statistic=deflated_sortino,
                p_value=0.0,  # N/A for this test
                critical_value=stats.norm.ppf(1 - self.test_config['deflated_threshold']),
                passed=deflated_passed,
                confidence_level=self.test_config['confidence_level']
            ))
            
            # 2. White's Reality Check
            wrc_p_value, wrc_passed = self.whites_reality_check(
                benchmark_returns, all_strategy_returns
            )
            
            statistical_tests.append(StatisticalTestResult(
                test_name="White's Reality Check",
                statistic=0.0,  # N/A
                p_value=wrc_p_value,
                critical_value=self.test_config['reality_check_alpha'],
                passed=wrc_passed,
                confidence_level=self.test_config['confidence_level']
            ))
            
            # 3. SPA Test
            spa_p_value, spa_passed = self.spa_test(
                benchmark_returns, all_strategy_returns
            )
            
            statistical_tests.append(StatisticalTestResult(
                test_name="SPA Test",
                statistic=0.0,  # N/A
                p_value=spa_p_value,
                critical_value=self.test_config['spa_alpha'],
                passed=spa_passed,
                confidence_level=self.test_config['confidence_level']
            ))
            
            # 검증 결과 생성
            result = ValidationResult(
                candidate_id=i,
                params=params,
                wfo_score=wfo_result.median_score,
                mc_score=mc_result.robustness_score,
                combined_score=combined_score,
                statistical_tests=statistical_tests,
                deflated_sortino=deflated_sortino,
                reality_check_passed=wrc_passed,
                spa_test_passed=spa_passed,
                final_ranking=0,  # 나중에 설정
                recommended=False  # 나중에 설정
            )
            
            validation_results.append(result)
        
        # 최종 랭킹 및 추천 설정
        validation_results = self._rank_and_recommend(validation_results)
        
        print(f"\n✅ 통계적 검증 완료")
        return validation_results
    
    def _extract_returns(self, wfo_result: WalkForwardResult) -> np.ndarray:
        """워크포워드 결과에서 수익률 추출"""
        returns = []
        for slice_obj in wfo_result.slices:
            if slice_obj.oos_metrics and slice_obj.oos_metrics.total_return:
                returns.append(slice_obj.oos_metrics.total_return)
        
        return np.array(returns) if returns else np.array([0])
    
    def _rank_and_recommend(self, results: List[ValidationResult]) -> List[ValidationResult]:
        """결과 랭킹 및 추천 설정"""
        # 통계적 검정을 모두 통과한 후보들만 필터링
        valid_results = []
        for result in results:
            all_tests_passed = all(test.passed for test in result.statistical_tests)
            if all_tests_passed:
                valid_results.append(result)
        
        if not valid_results:
            print("⚠️ 모든 통계적 검정을 통과한 후보가 없습니다")
            # 그래도 최고 점수 후보는 포함
            if results:
                best_result = max(results, key=lambda x: x.combined_score)
                valid_results = [best_result]
        
        # 결합 점수 기준 정렬
        valid_results.sort(key=lambda x: x.combined_score, reverse=True)
        
        # 랭킹 설정
        for i, result in enumerate(valid_results):
            result.final_ranking = i + 1
        
        # Top-1~2만 추천
        for i, result in enumerate(valid_results):
            result.recommended = i < 2  # Top-2
        
        # 원래 리스트에 업데이트
        for original_result in results:
            for valid_result in valid_results:
                if original_result.candidate_id == valid_result.candidate_id:
                    original_result.final_ranking = valid_result.final_ranking
                    original_result.recommended = valid_result.recommended
                    break
        
        return results
    
    def print_validation_results(self, results: List[ValidationResult], 
                               title: str = "통계적 검증 결과"):
        """검증 결과 출력"""
        print(f"\n📊 {title}")
        print("=" * 80)
        
        # 추천 후보들만 먼저 출력
        recommended = [r for r in results if r.recommended]
        if recommended:
            print(f"🏆 추천 후보 ({len(recommended)}개):")
            for result in recommended:
                self._print_single_result(result)
        
        # 나머지 후보들
        others = [r for r in results if not r.recommended]
        if others:
            print(f"\n📋 기타 후보 ({len(others)}개):")
            for result in others[:3]:  # 상위 3개만
                self._print_single_result(result, brief=True)
    
    def _print_single_result(self, result: ValidationResult, brief: bool = False):
        """단일 결과 출력"""
        status = "🌟 추천" if result.recommended else f"#{result.final_ranking}"
        
        print(f"\n{status} 후보 {result.candidate_id + 1}:")
        print(f"   결합 점수: {result.combined_score:.4f}")
        print(f"   WFO 점수: {result.wfo_score:.4f}")
        print(f"   MC 점수: {result.mc_score:.4f}")
        
        if not brief:
            # 통계적 검정 결과
            print(f"   통계적 검정:")
            for test in result.statistical_tests:
                status_icon = "✅" if test.passed else "❌"
                if test.test_name == "Deflated Sortino":
                    print(f"     {test.test_name}: {test.statistic:.4f} {status_icon}")
                else:
                    print(f"     {test.test_name}: p={test.p_value:.4f} {status_icon}")
            
            # 주요 파라미터
            key_params = ['target_r', 'stop_atr_mult', 'swing_len', 'rr_percentile']
            param_str = ", ".join([f"{k}: {result.params.get(k, 'N/A'):.3f}" if isinstance(result.params.get(k), float) 
                                 else f"{k}: {result.params.get(k, 'N/A')}" for k in key_params])
            print(f"   파라미터: {param_str}")
    
    def get_final_recommendations(self, results: List[ValidationResult]) -> List[ValidationResult]:
        """최종 추천 후보 반환"""
        return [r for r in results if r.recommended]

def main():
    """테스트 실행"""
    # 성과 평가자 초기화
    performance_evaluator = PerformanceEvaluator()
    
    # 통계적 검증자 초기화
    validator = StatisticalValidator(performance_evaluator)
    
    # 가상의 후보 데이터 생성 (실제로는 이전 단계에서 받아옴)
    from walkforward_analyzer import WalkForwardResult, WalkForwardSlice
    from montecarlo_simulator import MonteCarloResult
    
    # 테스트용 가상 데이터
    test_candidates = []
    
    for i in range(3):
        # 가상 파라미터
        params = {
            'target_r': 2.5 + i * 0.2,
            'stop_atr_mult': 0.1 + i * 0.01,
            'swing_len': 5 + i,
            'rr_percentile': 0.2 + i * 0.05
        }
        
        # 가상 WFO 결과
        slices = []
        for j in range(8):
            slice_obj = WalkForwardSlice(
                slice_id=j+1, train_start=0, train_end=1000, test_start=1000, test_end=1200,
                train_period="", test_period="", regime="normal"
            )
            slice_obj.oos_metrics = performance_evaluator._empty_metrics()
            slice_obj.oos_metrics.total_return = np.random.normal(0.1, 0.05)  # 10% ± 5%
            slice_obj.oos_score = np.random.normal(0.5, 0.1)
            slices.append(slice_obj)
        
        wfo_result = WalkForwardResult(
            slices=slices,
            aggregated_metrics=performance_evaluator._empty_metrics(),
            median_score=0.5 + i * 0.1,
            consistency_ratio=0.8,
            regime_performance={},
            passed_oos_criteria=True
        )
        wfo_result.aggregated_metrics.sortino_ratio = 2.0 + i * 0.2
        
        # 가상 MC 결과
        mc_result = MonteCarloResult(
            percentiles={'profit_factor_p5': 1.5 + i * 0.1},
            stability_metrics={'profit_factor_cv': 0.1},
            robustness_score=0.7 + i * 0.1,
            passed_criteria=True,
            simulation_count=1000,
            original_metrics=performance_evaluator._empty_metrics()
        )
        
        test_candidates.append((params, wfo_result, mc_result))
    
    # 통계적 검증 실행
    results = validator.validate_candidates(test_candidates)
    
    # 결과 출력
    validator.print_validation_results(results)
    
    # 최종 추천
    recommendations = validator.get_final_recommendations(results)
    print(f"\n🎯 최종 추천: {len(recommendations)}개 시스템")

if __name__ == "__main__":
    main()