#!/usr/bin/env python3
"""
파라미터 관리 시스템
- 최적화 결과를 자동으로 전략에 적용
- Railway 도메인에서 파라미터 조회 가능
- 파라미터 히스토리 관리
"""

import os
import json
import glob
from datetime import datetime
from typing import Dict, Any, Optional


class ParameterManager:
    def __init__(self):
        """파라미터 관리자 초기화"""
        self.current_params_file = "current_parameters.json"
        self.params_history_file = "parameters_history.json"

        # 워크포워드 테스트 통과 최적 파라미터 (2025.10.17 검증됨)
        self.default_optimal_params = {
            "swing_len": 3,
            "rr_percentile": 0.1278554501836069,
            "disp_mult": 1.3107139215624644,
            "sweep_wick_mult": 0.6490576952390765,
            "atr_len": 41,
            "stop_atr_mult": 0.0549414233732278,
            "target_r": 2.862429365474845,
            "time_stop_bars": 8,
            "funding_avoid_bars": 1,
            "min_volatility_rank": 0.3052228633363352,
            "session_strength": 1.9322268126535338,
            "volume_filter": 1.8994566274211397,
            "trend_filter_len": 13,
        }

        print("📊 파라미터 관리 시스템 초기화")
        self.initialize_current_params()

    def initialize_current_params(self):
        """현재 파라미터 초기화"""
        if not os.path.exists(self.current_params_file):
            self.save_current_params(
                params=self.default_optimal_params,
                source="default_optimal",
                score=None,
                notes="Initial optimal parameters from manual optimization",
            )
            print("✅ 기본 최적 파라미터로 초기화")
        else:
            print("✅ 기존 파라미터 파일 발견")

    def save_current_params(self, params: Dict[str, Any], source: str, score: Optional[float] = None, notes: str = ""):
        """현재 파라미터 저장"""
        param_data = {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "score": score,
            "notes": notes,
            "parameters": params,
        }

        # 현재 파라미터 저장
        with open(self.current_params_file, "w", encoding="utf-8") as f:
            json.dump(param_data, f, indent=2, ensure_ascii=False)

        # 히스토리에 추가
        self.add_to_history(param_data)

        print(f"💾 파라미터 저장 완료: {source}")

    def add_to_history(self, param_data: Dict[str, Any]):
        """파라미터 히스토리에 추가"""
        history = []

        # 기존 히스토리 로드
        if os.path.exists(self.params_history_file):
            try:
                with open(self.params_history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except:
                history = []

        # 새 데이터 추가
        history.append(param_data)

        # 최근 50개만 유지
        history = history[-50:]

        # 히스토리 저장
        with open(self.params_history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

    def load_current_params(self) -> Dict[str, Any]:
        """현재 파라미터 로드"""
        try:
            with open(self.current_params_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            # 파일이 없으면 기본값 반환
            return {"timestamp": datetime.now().isoformat(), "source": "default", "parameters": self.default_optimal_params}

    def update_from_optimization_result(self, result_file: str) -> bool:
        """최적화 결과에서 파라미터 업데이트"""
        try:
            with open(result_file, "r", encoding="utf-8") as f:
                result_data = json.load(f)

            best_params = result_data.get("best_parameters", {})
            final_score = result_data.get("stage_results", {}).get("stage3", {}).get("best_score")

            if best_params:
                self.save_current_params(
                    params=best_params,
                    source=f"auto_optimization_{result_data.get('timestamp')}",
                    score=final_score,
                    notes=f"Automated optimization result from {result_file}",
                )

                # 전략 파일 업데이트
                self.update_strategy_file(best_params)

                print(f"✅ 최적화 결과로 파라미터 업데이트: {result_file}")
                return True

        except Exception as e:
            print(f"❌ 최적화 결과 업데이트 실패: {e}")

        return False

    def update_strategy_file(self, params: Dict[str, Any]):
        """전략 파일의 파라미터 직접 업데이트"""
        try:
            # eth_session_strategy.py 파일 읽기
            with open("eth_session_strategy.py", "r", encoding="utf-8") as f:
                content = f.read()

            # 파라미터 섹션 찾기 및 업데이트
            # 실제 구현에서는 더 정교한 파싱이 필요할 수 있음
            print("📝 전략 파일 파라미터 업데이트 준비")

            # 여기서는 로그만 출력 (실제 파일 수정은 위험할 수 있음)
            print("⚠️ 전략 파일 직접 수정은 수동으로 진행하세요")

        except Exception as e:
            print(f"❌ 전략 파일 업데이트 실패: {e}")

    def get_parameter_comparison(self) -> Dict[str, Any]:
        """현재 파라미터와 기본값 비교"""
        current = self.load_current_params()
        current_params = current.get("parameters", {})

        comparison = {
            "timestamp": datetime.now().isoformat(),
            "current_source": current.get("source", "unknown"),
            "current_score": current.get("score"),
            "comparison": {},
        }

        for param_name, default_value in self.default_optimal_params.items():
            current_value = current_params.get(param_name, default_value)

            comparison["comparison"][param_name] = {
                "default": default_value,
                "current": current_value,
                "changed": current_value != default_value,
                "change_percent": (
                    ((current_value - default_value) / default_value * 100)
                    if isinstance(current_value, (int, float)) and default_value != 0
                    else 0
                ),
            }

        return comparison

    def check_for_new_optimization_results(self):
        """새로운 최적화 결과 확인 및 자동 업데이트"""
        try:
            # 최적화 결과 파일들 찾기
            result_files = glob.glob("optimization_result_*.json")
            result_files.sort(reverse=True)  # 최신 순

            if not result_files:
                return False

            # 가장 최근 결과 파일
            latest_result = result_files[0]

            # 현재 파라미터 정보
            current = self.load_current_params()
            current_timestamp = current.get("timestamp", "")

            # 결과 파일의 타임스탬프 확인
            with open(latest_result, "r", encoding="utf-8") as f:
                result_data = json.load(f)

            result_timestamp = result_data.get("end_time", "")

            # 새로운 결과인지 확인
            if result_timestamp > current_timestamp:
                print(f"🔄 새로운 최적화 결과 발견: {latest_result}")
                return self.update_from_optimization_result(latest_result)

        except Exception as e:
            print(f"❌ 최적화 결과 확인 실패: {e}")

        return False

    def get_api_response(self) -> Dict[str, Any]:
        """API 응답용 데이터 생성"""
        current = self.load_current_params()
        comparison = self.get_parameter_comparison()

        return {
            "timestamp": datetime.now().isoformat(),
            "current_parameters": current,
            "parameter_comparison": comparison,
            "optimization_schedule": "Every Sunday 14:00 KST",
            "auto_update_enabled": True,
            "parameter_source": current.get("source", "unknown"),
            "last_optimization_score": current.get("score"),
            "notes": current.get("notes", ""),
        }


def main():
    """테스트 실행"""
    manager = ParameterManager()

    # 현재 파라미터 출력
    current = manager.load_current_params()
    print("\n📊 현재 파라미터:")
    for param, value in current["parameters"].items():
        print(f"   {param}: {value}")

    # 새 최적화 결과 확인
    print("\n🔍 새 최적화 결과 확인 중...")
    updated = manager.check_for_new_optimization_results()

    if updated:
        print("✅ 파라미터가 업데이트되었습니다!")
    else:
        print("ℹ️ 새로운 최적화 결과가 없습니다.")


if __name__ == "__main__":
    main()
