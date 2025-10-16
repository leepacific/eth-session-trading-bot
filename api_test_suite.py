#!/usr/bin/env python3
"""
API 테스트 스위트
- API 기능 테스트
- IP 제한 테스트
- 성능 테스트
- 보안 테스트
"""

import requests
import time
import json
import threading
from datetime import datetime
import concurrent.futures
import random
import sys

class APITester:
    def __init__(self, base_url):
        """API 테스터 초기화"""
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.results = {
            'basic_tests': [],
            'rate_limit_tests': [],
            'security_tests': [],
            'performance_tests': []
        }
        
        print(f"🧪 API 테스트 스위트 초기화")
        print(f"   대상 URL: {self.base_url}")
        print(f"   테스트 시작: {datetime.now()}")
    
    def test_basic_functionality(self):
        """기본 기능 테스트"""
        print("\n🔍 기본 기능 테스트 시작...")
        
        tests = [
            {
                'name': '헬스체크 엔드포인트',
                'endpoint': '/health',
                'method': 'GET',
                'expected_status': 200
            },
            {
                'name': '상태 확인 엔드포인트',
                'endpoint': '/status',
                'method': 'GET',
                'expected_status': 200
            },
            {
                'name': '존재하지 않는 엔드포인트',
                'endpoint': '/nonexistent',
                'method': 'GET',
                'expected_status': 404
            }
        ]
        
        for test in tests:
            try:
                url = f"{self.base_url}{test['endpoint']}"
                response = self.session.request(test['method'], url, timeout=10)
                
                result = {
                    'test': test['name'],
                    'url': url,
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds(),
                    'success': response.status_code == test['expected_status']
                }
                
                if response.headers.get('content-type', '').startswith('application/json'):
                    try:
                        result['response_data'] = response.json()
                    except:
                        result['response_data'] = None
                
                self.results['basic_tests'].append(result)
                
                status = "✅" if result['success'] else "❌"
                print(f"   {status} {test['name']}: {response.status_code} ({response.elapsed.total_seconds():.3f}s)")
                
            except Exception as e:
                result = {
                    'test': test['name'],
                    'url': url,
                    'error': str(e),
                    'success': False
                }
                self.results['basic_tests'].append(result)
                print(f"   ❌ {test['name']}: 오류 - {e}")
    
    def test_rate_limiting(self):
        """Rate Limiting 테스트"""
        print("\n⚡ Rate Limiting 테스트 시작...")
        
        # 빠른 연속 요청으로 Rate Limit 테스트
        url = f"{self.base_url}/health"
        requests_count = 50
        time_window = 10  # 10초 내에 50개 요청
        
        print(f"   {time_window}초 내에 {requests_count}개 요청 전송...")
        
        start_time = time.time()
        responses = []
        
        def make_request(i):
            try:
                response = requests.get(url, timeout=5)
                return {
                    'request_id': i,
                    'status_code': response.status_code,
                    'timestamp': time.time(),
                    'response_time': response.elapsed.total_seconds(),
                    'headers': dict(response.headers)
                }
            except Exception as e:
                return {
                    'request_id': i,
                    'error': str(e),
                    'timestamp': time.time()
                }
        
        # 병렬 요청 실행
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(requests_count)]
            responses = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 결과 분석
        successful_requests = [r for r in responses if 'status_code' in r and r['status_code'] == 200]
        rate_limited_requests = [r for r in responses if 'status_code' in r and r['status_code'] == 429]
        error_requests = [r for r in responses if 'error' in r]
        
        rate_limit_result = {
            'total_requests': requests_count,
            'successful_requests': len(successful_requests),
            'rate_limited_requests': len(rate_limited_requests),
            'error_requests': len(error_requests),
            'total_time': total_time,
            'requests_per_second': requests_count / total_time,
            'rate_limiting_active': len(rate_limited_requests) > 0
        }
        
        self.results['rate_limit_tests'].append(rate_limit_result)
        
        print(f"   📊 결과:")
        print(f"      성공한 요청: {len(successful_requests)}")
        print(f"      Rate Limited: {len(rate_limited_requests)}")
        print(f"      오류 요청: {len(error_requests)}")
        print(f"      총 시간: {total_time:.2f}초")
        print(f"      초당 요청: {requests_count/total_time:.2f} req/s")
        
        if len(rate_limited_requests) > 0:
            print("   ✅ Rate Limiting이 정상 작동 중")
        else:
            print("   ⚠️ Rate Limiting이 감지되지 않음 (설정 확인 필요)")
    
    def test_security_headers(self):
        """보안 헤더 테스트"""
        print("\n🛡️ 보안 헤더 테스트 시작...")
        
        url = f"{self.base_url}/health"
        
        try:
            response = self.session.get(url, timeout=10)
            headers = response.headers
            
            security_checks = {
                'HTTPS': url.startswith('https://'),
                'Cloudflare': 'cloudflare' in headers.get('server', '').lower(),
                'X-Frame-Options': 'x-frame-options' in headers,
                'X-Content-Type-Options': 'x-content-type-options' in headers,
                'Strict-Transport-Security': 'strict-transport-security' in headers,
                'Content-Security-Policy': 'content-security-policy' in headers,
                'CF-Ray': 'cf-ray' in headers  # Cloudflare 식별자
            }
            
            security_result = {
                'url': url,
                'headers': dict(headers),
                'security_checks': security_checks,
                'cloudflare_detected': security_checks['Cloudflare'] or security_checks['CF-Ray']
            }
            
            self.results['security_tests'].append(security_result)
            
            print(f"   📋 보안 검사 결과:")
            for check, passed in security_checks.items():
                status = "✅" if passed else "❌"
                print(f"      {status} {check}")
            
            if security_result['cloudflare_detected']:
                print("   🌐 Cloudflare 프록시 감지됨")
            else:
                print("   ⚠️ Cloudflare 프록시가 감지되지 않음")
                
        except Exception as e:
            print(f"   ❌ 보안 헤더 테스트 실패: {e}")
    
    def test_performance(self):
        """성능 테스트"""
        print("\n⚡ 성능 테스트 시작...")
        
        url = f"{self.base_url}/health"
        test_count = 20
        
        print(f"   {test_count}회 연속 요청으로 성능 측정...")
        
        response_times = []
        
        for i in range(test_count):
            try:
                start = time.time()
                response = self.session.get(url, timeout=10)
                end = time.time()
                
                response_time = end - start
                response_times.append(response_time)
                
                if i % 5 == 0:
                    print(f"   진행률: {i+1}/{test_count}")
                    
            except Exception as e:
                print(f"   ❌ 요청 {i+1} 실패: {e}")
        
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            
            performance_result = {
                'test_count': test_count,
                'successful_requests': len(response_times),
                'average_response_time': avg_time,
                'min_response_time': min_time,
                'max_response_time': max_time,
                'response_times': response_times
            }
            
            self.results['performance_tests'].append(performance_result)
            
            print(f"   📊 성능 결과:")
            print(f"      평균 응답시간: {avg_time*1000:.2f}ms")
            print(f"      최소 응답시간: {min_time*1000:.2f}ms")
            print(f"      최대 응답시간: {max_time*1000:.2f}ms")
            
            if avg_time < 0.5:
                print("   ✅ 우수한 성능")
            elif avg_time < 1.0:
                print("   ✅ 양호한 성능")
            else:
                print("   ⚠️ 성능 개선 필요")
    
    def test_different_ips(self):
        """다양한 IP에서 접속 테스트 (프록시 사용)"""
        print("\n🌍 다양한 지역에서 접속 테스트...")
        
        # 무료 프록시 서비스들 (테스트용)
        proxy_list = [
            # 실제 환경에서는 유료 프록시 서비스 사용 권장
            None,  # 직접 연결
        ]
        
        url = f"{self.base_url}/health"
        
        for i, proxy in enumerate(proxy_list):
            try:
                if proxy:
                    proxies = {'http': proxy, 'https': proxy}
                    print(f"   프록시 {i+1} 테스트: {proxy}")
                else:
                    proxies = None
                    print(f"   직접 연결 테스트")
                
                response = requests.get(url, proxies=proxies, timeout=15)
                
                print(f"      ✅ 응답 코드: {response.status_code}")
                print(f"      ⏱️ 응답 시간: {response.elapsed.total_seconds():.3f}s")
                
                # CF-IPCountry 헤더로 지역 확인
                if 'cf-ipcountry' in response.headers:
                    print(f"      🌍 감지된 국가: {response.headers['cf-ipcountry']}")
                
            except Exception as e:
                print(f"      ❌ 연결 실패: {e}")
    
    def generate_report(self):
        """테스트 결과 리포트 생성"""
        print("\n" + "="*80)
        print("📊 API 테스트 결과 리포트")
        print("="*80)
        
        # 기본 기능 테스트 요약
        basic_success = sum(1 for test in self.results['basic_tests'] if test.get('success', False))
        basic_total = len(self.results['basic_tests'])
        
        print(f"\n🔍 기본 기능 테스트: {basic_success}/{basic_total} 통과")
        
        # Rate Limiting 테스트 요약
        if self.results['rate_limit_tests']:
            rate_test = self.results['rate_limit_tests'][0]
            print(f"\n⚡ Rate Limiting: {'활성화' if rate_test['rate_limiting_active'] else '비활성화'}")
            print(f"   성공률: {rate_test['successful_requests']}/{rate_test['total_requests']}")
        
        # 보안 테스트 요약
        if self.results['security_tests']:
            security_test = self.results['security_tests'][0]
            security_score = sum(security_test['security_checks'].values())
            security_total = len(security_test['security_checks'])
            print(f"\n🛡️ 보안 검사: {security_score}/{security_total} 통과")
        
        # 성능 테스트 요약
        if self.results['performance_tests']:
            perf_test = self.results['performance_tests'][0]
            avg_time = perf_test['average_response_time']
            print(f"\n⚡ 평균 응답시간: {avg_time*1000:.2f}ms")
        
        # 전체 점수 계산
        total_score = 0
        max_score = 0
        
        if basic_total > 0:
            total_score += (basic_success / basic_total) * 25
            max_score += 25
        
        if self.results['rate_limit_tests']:
            if self.results['rate_limit_tests'][0]['rate_limiting_active']:
                total_score += 25
            max_score += 25
        
        if self.results['security_tests']:
            security_ratio = security_score / security_total
            total_score += security_ratio * 25
            max_score += 25
        
        if self.results['performance_tests']:
            if avg_time < 0.5:
                total_score += 25
            elif avg_time < 1.0:
                total_score += 15
            else:
                total_score += 5
            max_score += 25
        
        final_score = (total_score / max_score) * 100 if max_score > 0 else 0
        
        print(f"\n🎯 전체 점수: {final_score:.1f}/100")
        
        if final_score >= 90:
            print("🎉 우수! API가 완벽하게 작동합니다.")
        elif final_score >= 70:
            print("✅ 양호! 대부분의 기능이 정상 작동합니다.")
        elif final_score >= 50:
            print("⚠️ 보통! 일부 개선이 필요합니다.")
        else:
            print("❌ 문제! 설정을 다시 확인해주세요.")
        
        # JSON 리포트 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"api_test_report_{timestamp}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'base_url': self.base_url,
                'final_score': final_score,
                'results': self.results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 상세 리포트 저장: {report_file}")
    
    def run_all_tests(self):
        """모든 테스트 실행"""
        print("🚀 전체 API 테스트 시작")
        print("="*80)
        
        try:
            self.test_basic_functionality()
            self.test_security_headers()
            self.test_performance()
            self.test_rate_limiting()
            self.test_different_ips()
            self.generate_report()
            
        except KeyboardInterrupt:
            print("\n⚠️ 테스트가 사용자에 의해 중단되었습니다.")
        except Exception as e:
            print(f"\n❌ 테스트 실행 중 오류: {e}")
            import traceback
            traceback.print_exc()

def main():
    """메인 실행 함수"""
    if len(sys.argv) != 2:
        print("사용법: python api_test_suite.py <API_URL>")
        print("예시: python api_test_suite.py https://api.eth-trading-bot.com")
        sys.exit(1)
    
    api_url = sys.argv[1]
    
    tester = APITester(api_url)
    tester.run_all_tests()

if __name__ == "__main__":
    main()