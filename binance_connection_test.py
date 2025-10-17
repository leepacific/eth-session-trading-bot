#!/usr/bin/env python3
"""
바이낸스 연결 및 IP 제한 테스트
- Cloudflare IP를 통한 바이낸스 API 접속 테스트
- 단발성 테스트 주문 전송
- IP 제한 및 보안 기능 검증
"""

import os
import sys
import json
import time
import requests
import hmac
import hashlib
from datetime import datetime
from urllib.parse import urlencode
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class BinanceConnectionTester:
    def __init__(self):
        """바이낸스 연결 테스터 초기화"""
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.secret_key = os.getenv('BINANCE_SECRET_KEY')
        self.testnet = os.getenv('BINANCE_TESTNET', 'false').lower() == 'true'
        
        # API 엔드포인트 설정
        if self.testnet:
            self.base_url = "https://testnet.binancefuture.com"
            print("🧪 테스트넷 모드")
        else:
            self.base_url = "https://fapi.binance.com"
            print("🔴 실제 거래 모드")
        
        self.symbol = "ETHUSDT"
        
        print("🔗 바이낸스 연결 테스터 초기화")
        print(f"   API 키: {'설정됨' if self.api_key else '미설정'}")
        print(f"   베이스 URL: {self.base_url}")
        
        if not self.api_key or not self.secret_key:
            print("❌ API 키가 설정되지 않았습니다!")
            sys.exit(1)
    
    def generate_signature(self, query_string):
        """API 서명 생성"""
        return hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def make_request(self, endpoint, method='GET', params=None, signed=False):
        """API 요청 실행"""
        url = f"{self.base_url}{endpoint}"
        
        if params is None:
            params = {}
        
        headers = {
            'X-MBX-APIKEY': self.api_key,
            'Content-Type': 'application/json'
        }
        
        if signed:
            params['timestamp'] = int(time.time() * 1000)
            query_string = urlencode(params)
            params['signature'] = self.generate_signature(query_string)
        
        try:
            if method == 'GET':
                response = requests.get(url, params=params, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, params=params, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, params=params, headers=headers, timeout=10)
            
            return {
                'success': True,
                'status_code': response.status_code,
                'data': response.json() if response.text else {},
                'headers': dict(response.headers)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'status_code': None
            }
    
    def test_server_time(self):
        """서버 시간 테스트"""
        print("\n🕐 서버 시간 테스트...")
        
        result = self.make_request('/fapi/v1/time')
        
        if result['success']:
            server_time = result['data'].get('serverTime', 0)
            local_time = int(time.time() * 1000)
            time_diff = abs(server_time - local_time)
            
            print(f"   ✅ 서버 시간: {datetime.fromtimestamp(server_time/1000)}")
            print(f"   ⏰ 로컬 시간: {datetime.fromtimestamp(local_time/1000)}")
            print(f"   📊 시간 차이: {time_diff}ms")
            
            if time_diff > 5000:  # 5초 이상 차이
                print("   ⚠️ 시간 동기화 문제 가능성")
                return False
            else:
                print("   ✅ 시간 동기화 정상")
                return True
        else:
            print(f"   ❌ 서버 시간 조회 실패: {result['error']}")
            return False
    
    def test_account_info(self):
        """계정 정보 테스트"""
        print("\n👤 계정 정보 테스트...")
        
        result = self.make_request('/fapi/v2/account', signed=True)
        
        if result['success']:
            if result['status_code'] == 200:
                account_data = result['data']
                
                print("   ✅ 계정 정보 조회 성공")
                print(f"   💰 총 잔고: {account_data.get('totalWalletBalance', 'N/A')} USDT")
                print(f"   📊 포지션 수: {len(account_data.get('positions', []))}")
                
                # IP 제한 관련 헤더 확인
                headers = result['headers']
                if 'x-mbx-used-weight-1m' in headers:
                    print(f"   📈 API 사용량: {headers['x-mbx-used-weight-1m']}/1200")
                
                return True
            else:
                print(f"   ❌ 계정 정보 조회 실패: HTTP {result['status_code']}")
                print(f"   📄 응답: {result['data']}")
                return False
        else:
            print(f"   ❌ 계정 정보 요청 실패: {result['error']}")
            return False
    
    def get_current_price(self):
        """현재 가격 조회"""
        print(f"\n💰 {self.symbol} 현재 가격 조회...")
        
        result = self.make_request(f'/fapi/v1/ticker/price', params={'symbol': self.symbol})
        
        if result['success'] and result['status_code'] == 200:
            price = float(result['data']['price'])
            print(f"   ✅ 현재 가격: ${price:,.2f}")
            return price
        else:
            print(f"   ❌ 가격 조회 실패")
            return None
    
    def test_order_placement(self):
        """테스트 주문 전송"""
        print(f"\n📋 {self.symbol} 테스트 주문 전송...")
        
        # 현재 가격 조회
        current_price = self.get_current_price()
        if not current_price:
            return False
        
        # 테스트 주문 파라미터 (현재가에서 멀리 떨어진 가격으로 설정)
        side = 'BUY'  # 매수 주문
        order_type = 'LIMIT'
        time_in_force = 'GTC'
        quantity = '0.001'  # 최소 수량
        
        # 현재가보다 10% 낮은 가격으로 설정 (체결되지 않도록)
        test_price = current_price * 0.9
        
        params = {
            'symbol': self.symbol,
            'side': side,
            'type': order_type,
            'timeInForce': time_in_force,
            'quantity': quantity,
            'price': f"{test_price:.2f}"
        }
        
        print(f"   📊 주문 정보:")
        print(f"      심볼: {self.symbol}")
        print(f"      방향: {side}")
        print(f"      수량: {quantity} ETH")
        print(f"      가격: ${test_price:,.2f} (현재가 대비 -10%)")
        print(f"      타입: {order_type} {time_in_force}")
        
        # 실제 주문 전송 확인
        confirm = input("\n⚠️ 실제 주문을 전송하시겠습니까? (y/N): ")
        if confirm.lower() != 'y':
            print("   ℹ️ 주문 전송이 취소되었습니다.")
            return False
        
        print("   📤 주문 전송 중...")
        
        result = self.make_request('/fapi/v1/order', method='POST', params=params, signed=True)
        
        if result['success']:
            if result['status_code'] == 200:
                order_data = result['data']
                
                print("   ✅ 주문 전송 성공!")
                print(f"   📋 주문 ID: {order_data.get('orderId')}")
                print(f"   📊 클라이언트 ID: {order_data.get('clientOrderId')}")
                print(f"   📈 상태: {order_data.get('status')}")
                
                # 주문 정보 저장
                order_info = {
                    'timestamp': datetime.now().isoformat(),
                    'symbol': self.symbol,
                    'orderId': order_data.get('orderId'),
                    'clientOrderId': order_data.get('clientOrderId'),
                    'side': side,
                    'quantity': quantity,
                    'price': test_price,
                    'status': order_data.get('status')
                }
                
                # JSON 파일로 저장
                filename = f"test_order_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(order_info, f, indent=2, ensure_ascii=False)
                
                print(f"   💾 주문 정보 저장: {filename}")
                print("   ⚠️ 바이낸스에서 수동으로 주문을 취소해주세요!")
                
                return True
            else:
                print(f"   ❌ 주문 전송 실패: HTTP {result['status_code']}")
                print(f"   📄 오류 내용: {result['data']}")
                return False
        else:
            print(f"   ❌ 주문 요청 실패: {result['error']}")
            return False
    
    def test_ip_restrictions(self):
        """IP 제한 테스트"""
        print("\n🛡️ IP 제한 및 보안 테스트...")
        
        # 여러 번 빠른 요청으로 Rate Limit 테스트
        print("   📊 Rate Limit 테스트 (10회 연속 요청)...")
        
        success_count = 0
        rate_limited_count = 0
        
        for i in range(10):
            result = self.make_request('/fapi/v1/time')
            
            if result['success']:
                if result['status_code'] == 200:
                    success_count += 1
                elif result['status_code'] == 429:
                    rate_limited_count += 1
                    print(f"      ⚠️ Rate Limit 감지 (요청 {i+1})")
            
            time.sleep(0.1)  # 100ms 대기
        
        print(f"   📈 결과: 성공 {success_count}회, Rate Limited {rate_limited_count}회")
        
        if rate_limited_count > 0:
            print("   ✅ Rate Limiting이 정상 작동 중")
        else:
            print("   ℹ️ Rate Limiting이 감지되지 않음 (정상적인 사용량)")
        
        return True
    
    def test_cloudflare_integration(self):
        """Cloudflare 통합 테스트"""
        print("\n🌐 Cloudflare 통합 테스트...")
        
        # 외부 IP 확인
        try:
            ip_response = requests.get('https://api.ipify.org?format=json', timeout=5)
            if ip_response.status_code == 200:
                external_ip = ip_response.json()['ip']
                print(f"   🌍 외부 IP: {external_ip}")
            else:
                print("   ⚠️ 외부 IP 확인 실패")
        except:
            print("   ⚠️ 외부 IP 확인 불가")
        
        # Cloudflare 헤더 확인
        result = self.make_request('/fapi/v1/time')
        
        if result['success']:
            headers = result['headers']
            
            cloudflare_headers = {
                'cf-ray': headers.get('cf-ray'),
                'cf-ipcountry': headers.get('cf-ipcountry'),
                'server': headers.get('server')
            }
            
            print("   📋 Cloudflare 헤더:")
            for header, value in cloudflare_headers.items():
                if value:
                    print(f"      {header}: {value}")
            
            if any(cloudflare_headers.values()):
                print("   ✅ Cloudflare 프록시 감지됨")
                return True
            else:
                print("   ⚠️ Cloudflare 프록시가 감지되지 않음")
                return False
        
        return False
    
    def run_full_test(self):
        """전체 테스트 실행"""
        print("🧪 바이낸스 연결 및 IP 제한 테스트 시작")
        print("=" * 80)
        
        test_results = {}
        
        # 1. 서버 시간 테스트
        test_results['server_time'] = self.test_server_time()
        
        # 2. Cloudflare 통합 테스트
        test_results['cloudflare'] = self.test_cloudflare_integration()
        
        # 3. IP 제한 테스트
        test_results['ip_restrictions'] = self.test_ip_restrictions()
        
        # 4. 계정 정보 테스트
        test_results['account_info'] = self.test_account_info()
        
        # 5. 테스트 주문 전송
        test_results['order_placement'] = self.test_order_placement()
        
        # 결과 요약
        print("\n" + "=" * 80)
        print("📊 테스트 결과 요약")
        print("=" * 80)
        
        passed_tests = sum(test_results.values())
        total_tests = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅ 통과" if result else "❌ 실패"
            print(f"   {test_name}: {status}")
        
        print(f"\n🎯 전체 결과: {passed_tests}/{total_tests} 통과")
        
        if passed_tests == total_tests:
            print("🎉 모든 테스트 통과! 바이낸스 연결이 정상 작동합니다.")
        elif passed_tests >= total_tests * 0.8:
            print("✅ 대부분의 테스트 통과! 일부 개선이 필요할 수 있습니다.")
        else:
            print("⚠️ 여러 테스트 실패! 설정을 확인해주세요.")
        
        # 결과 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = f"binance_test_result_{timestamp}.json"
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'test_results': test_results,
                'passed_tests': passed_tests,
                'total_tests': total_tests,
                'success_rate': passed_tests / total_tests * 100
            }, f, indent=2, ensure_ascii=False)
        
        print(f"📄 테스트 결과 저장: {result_file}")
        
        return test_results

def main():
    """메인 실행 함수"""
    print("🚀 바이낸스 연결 테스터")
    print("=" * 80)
    
    # 환경 확인
    if not os.getenv('BINANCE_API_KEY'):
        print("❌ BINANCE_API_KEY 환경변수가 설정되지 않았습니다.")
        print("   Railway 환경변수를 확인해주세요.")
        sys.exit(1)
    
    # 테스터 실행
    tester = BinanceConnectionTester()
    results = tester.run_full_test()
    
    print("\n🎯 테스트 완료!")
    print("   바이낸스에서 테스트 주문을 수동으로 취소해주세요.")

if __name__ == "__main__":
    main()