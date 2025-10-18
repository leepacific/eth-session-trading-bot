#!/usr/bin/env python3
"""
전체 테스트 실행기
- 단위 테스트, 통합 테스트, 성능 테스트 통합 실행
- 테스트 결과 종합 리포트 생성
- CI/CD 파이프라인 지원
"""

import sys
import time
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 테스트 모듈들 import
from test_unit_tests import TestSuite as UnitTestSuite
from test_integration_tests import TestIntegrationSuite
from test_performance_validation import TestPerformanceValidationSuite

class ComprehensiveTestRunner:
    """종합 테스트 실행기"""
    
    def __init__(self):
        """테스트 실행기 초기화"""
        self.unit_test_suite = UnitTestSuite()
        self.integration_test_suite = TestIntegrationSuite()
        self.performance_test_suite = TestPerformanceValidationSuite()
        
        self.results = {
            'unit_tests': None,
            'integration_tests': None,
            'performance_tests': None,
            'overall': None
        }
    
    def run_all_tests(self, include_performance: bool = True):
        """모든 테스트 실행"""
        print("🚀 고급 최적화 파이프라인 - 종합 테스트 실행")
        print("="*100)
        print(f"   시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   성능 테스트 포함: {'예' if include_performance else '아니오'}")
        
        overall_start_time = time.time()
        
        # 1. 단위 테스트 실행
        print(f"\n{'='*20} 1단계: 단위 테스트 {'='*20}")
        unit_start_time = time.time()
        
        try:
            self.results['unit_tests'] = self.unit_test_suite.run_all_tests()
            unit_duration = time.time() - unit_start_time
            print(f"✅ 단위 테스트 완료 ({unit_duration:.1f}초)")
        except Exception as e:
            print(f"❌ 단위 테스트 실행 중 오류: {str(e)}")
            self.results['unit_tests'] = {'total_tests': 0, 'passed_tests': 0, 'failed_tests': 0, 'success_rate': 0.0}
        
        # 2. 통합 테스트 실행
        print(f"\n{'='*20} 2단계: 통합 테스트 {'='*20}")
        integration_start_time = time.time()
        
        try:
            self.results['integration_tests'] = self.integration_test_suite.run_all_integration_tests()
            integration_duration = time.time() - integration_start_time
            print(f"✅ 통합 테스트 완료 ({integration_duration:.1f}초)")
        except Exception as e:
            print(f"❌ 통합 테스트 실행 중 오류: {str(e)}")
            self.results['integration_tests'] = {'total_tests': 0, 'passed_tests': 0, 'failed_tests': 0, 'success_rate': 0.0}
        
        # 3. 성능 테스트 실행 (선택적)
        if include_performance:
            print(f"\n{'='*20} 3단계: 성능 테스트 {'='*20}")
            performance_start_time = time.time()
            
            try:
                self.results['performance_tests'] = self.performance_test_suite.run_all_performance_tests()
                performance_duration = time.time() - performance_start_time
                print(f"✅ 성능 테스트 완료 ({performance_duration:.1f}초)")
            except Exception as e:
                print(f"❌ 성능 테스트 실행 중 오류: {str(e)}")
                self.results['performance_tests'] = {'total_tests': 0, 'passed_tests': 0, 'failed_tests': 0, 'success_rate': 0.0}
        else:
            print(f"\n⏭️ 성능 테스트 건너뜀")
            self.results['performance_tests'] = {'total_tests': 0, 'passed_tests': 0, 'failed_tests': 0, 'success_rate': 1.0}
        
        # 전체 결과 계산
        overall_duration = time.time() - overall_start_time
        self._calculate_overall_results(overall_duration)
        
        # 종합 리포트 생성
        self._generate_comprehensive_report()
        
        return self.results
    
    def _calculate_overall_results(self, duration: float):
        """전체 결과 계산"""
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        
        for test_type, result in self.results.items():
            if result and test_type != 'overall':
                total_tests += result.get('total_tests', 0)
                passed_tests += result.get('passed_tests', 0)
                failed_tests += result.get('failed_tests', 0)
        
        overall_success_rate = passed_tests / total_tests if total_tests > 0 else 0.0
        
        self.results['overall'] = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': overall_success_rate,
            'duration': duration
        }
    
    def _generate_comprehensive_report(self):
        """종합 리포트 생성"""
        print(f"\n{'='*30} 종합 테스트 리포트 {'='*30}")
        
        # 전체 요약
        overall = self.results['overall']
        print(f"\n📊 전체 요약:")
        print(f"   총 테스트: {overall['total_tests']}개")
        print(f"   통과: {overall['passed_tests']}개 ({overall['success_rate']*100:.1f}%)")
        print(f"   실패: {overall['failed_tests']}개")
        print(f"   총 소요 시간: {overall['duration']:.1f}초")
        
        # 테스트 유형별 상세
        print(f"\n📋 테스트 유형별 결과:")
        
        test_types = [
            ('unit_tests', '단위 테스트'),
            ('integration_tests', '통합 테스트'),
            ('performance_tests', '성능 테스트')
        ]
        
        for test_key, test_name in test_types:
            result = self.results[test_key]
            if result:
                status_icon = "✅" if result['success_rate'] >= 0.8 else "⚠️" if result['success_rate'] >= 0.6 else "❌"
                print(f"   {status_icon} {test_name}: {result['passed_tests']}/{result['total_tests']} "
                      f"({result['success_rate']*100:.1f}%)")
        
        # 품질 등급
        print(f"\n🏆 전체 품질 등급:")
        success_rate = overall['success_rate']
        
        if success_rate >= 0.95:
            grade = "A+ (최우수)"
            emoji = "🌟"
        elif success_rate >= 0.90:
            grade = "A (우수)"
            emoji = "🎉"
        elif success_rate >= 0.85:
            grade = "B+ (양호)"
            emoji = "✅"
        elif success_rate >= 0.80:
            grade = "B (보통)"
            emoji = "👍"
        elif success_rate >= 0.70:
            grade = "C (개선 필요)"
            emoji = "⚠️"
        else:
            grade = "D (불합격)"
            emoji = "❌"
        
        print(f"   {emoji} {grade} ({success_rate*100:.1f}%)")
        
        # 권장사항
        print(f"\n💡 권장사항:")
        
        if success_rate >= 0.95:
            print(f"   • 모든 테스트가 우수한 결과를 보입니다")
            print(f"   • 현재 품질 수준을 유지하세요")
        elif success_rate >= 0.85:
            print(f"   • 대부분의 테스트가 양호한 결과를 보입니다")
            print(f"   • 실패한 테스트들을 검토하여 개선하세요")
        elif success_rate >= 0.70:
            print(f"   • 일부 테스트에서 문제가 발견되었습니다")
            print(f"   • 실패 원인을 분석하고 코드를 개선하세요")
        else:
            print(f"   • 심각한 품질 문제가 있습니다")
            print(f"   • 전면적인 코드 검토와 수정이 필요합니다")
        
        # 성능 관련 권장사항
        if self.results['performance_tests'] and self.results['performance_tests']['success_rate'] < 0.8:
            print(f"   • 성능 최적화가 필요합니다")
            print(f"   • 메모리 사용량과 처리 속도를 개선하세요")
        
        # CI/CD 결과 코드
        print(f"\n🔧 CI/CD 결과 코드:")
        exit_code = 0 if success_rate >= 0.8 else 1
        print(f"   Exit Code: {exit_code} ({'PASS' if exit_code == 0 else 'FAIL'})")
        
        # 상세 로그 파일 생성
        self._save_detailed_report()
        
        return exit_code
    
    def _save_detailed_report(self):
        """상세 리포트 파일 저장"""
        try:
            import json
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"test_report_{timestamp}.json"
            
            report_data = {
                'timestamp': datetime.now().isoformat(),
                'results': self.results,
                'summary': {
                    'total_tests': self.results['overall']['total_tests'],
                    'success_rate': self.results['overall']['success_rate'],
                    'duration': self.results['overall']['duration']
                }
            }
            
            with open(filename, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            print(f"   📄 상세 리포트 저장: {filename}")
            
        except Exception as e:
            print(f"   ⚠️ 리포트 저장 실패: {str(e)}")
    
    def run_quick_tests(self):
        """빠른 테스트 실행 (성능 테스트 제외)"""
        print("⚡ 빠른 테스트 모드")
        return self.run_all_tests(include_performance=False)
    
    def run_ci_tests(self):
        """CI/CD용 테스트 실행"""
        print("🔧 CI/CD 테스트 모드")
        results = self.run_all_tests(include_performance=True)
        
        # CI/CD 환경변수 설정
        import os
        
        success_rate = results['overall']['success_rate']
        os.environ['TEST_SUCCESS_RATE'] = str(success_rate)
        os.environ['TEST_TOTAL_COUNT'] = str(results['overall']['total_tests'])
        os.environ['TEST_PASSED_COUNT'] = str(results['overall']['passed_tests'])
        
        # 종료 코드 반환
        return 0 if success_rate >= 0.8 else 1

def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='고급 최적화 파이프라인 테스트 실행기')
    parser.add_argument('--mode', choices=['full', 'quick', 'ci'], default='full',
                       help='테스트 실행 모드')
    parser.add_argument('--no-performance', action='store_true',
                       help='성능 테스트 제외')
    
    args = parser.parse_args()
    
    # 테스트 실행기 초기화
    runner = ComprehensiveTestRunner()
    
    try:
        if args.mode == 'quick' or args.no_performance:
            exit_code = runner.run_quick_tests()
        elif args.mode == 'ci':
            exit_code = runner.run_ci_tests()
        else:
            results = runner.run_all_tests()
            exit_code = 0 if results['overall']['success_rate'] >= 0.8 else 1
        
        print(f"\n🏁 테스트 실행 완료 (종료 코드: {exit_code})")
        
        # 시스템 종료 코드 설정
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print(f"\n⏹️ 사용자에 의해 테스트가 중단되었습니다")
        sys.exit(2)
    
    except Exception as e:
        print(f"\n💥 테스트 실행 중 예상치 못한 오류 발생: {str(e)}")
        sys.exit(3)

if __name__ == "__main__":
    main()