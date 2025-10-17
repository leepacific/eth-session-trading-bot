
import requests
import hmac
import hashlib
import time
import os
from urllib.parse import urlencode

class BinanceProxyClient:
    """Cloudflare Workers를 통한 바이낸스 API 클라이언트"""
    
    def __init__(self, proxy_url=None):
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.secret_key = os.getenv('BINANCE_SECRET_KEY')
        
        # 프록시 URL 설정
        self.proxy_url = proxy_url or os.getenv('BINANCE_PROXY_URL', 'https://binance-proxy.your-worker.workers.dev')
        self.proxy_url = self.proxy_url.rstrip('/')
        
        print(f"🌐 바이낸스 프록시 클라이언트 초기화")
        print(f"   프록시 URL: {self.proxy_url}")
        print(f"   API 키 설정: {'✅' if self.api_key else '❌'}")
        
    def _generate_signature(self, params):
        """API 서명 생성"""
        query_string = urlencode(params)
        return hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _make_request(self, method, endpoint, params=None, signed=False):
        """프록시를 통한 API 요청"""
        if params is None:
            params = {}
            
        # 서명이 필요한 요청
        if signed:
            if not (self.api_key and self.secret_key):
                raise ValueError("API 키가 설정되지 않았습니다")
                
            params['timestamp'] = int(time.time() * 1000)
            params['signature'] = self._generate_signature(params)
        
        # 헤더 설정
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Railway-Binance-Bot/1.0'
        }
        
        if self.api_key:
            headers['X-MBX-APIKEY'] = self.api_key
        
        # 프록시 URL 구성
        url = f"{self.proxy_url}{endpoint}"
        
        print(f"🔗 API 요청: {method} {endpoint}")
        print(f"   프록시 경유: {url}")
        
        # 요청 실행
        try:
            if method == 'GET':
                response = requests.get(url, params=params, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=params, headers=headers, timeout=30)
            else:
                raise ValueError(f"지원하지 않는 메서드: {method}")
            
            print(f"   응답: {response.status_code}")
            
            # 프록시 정보 확인
            if 'X-Proxy-By' in response.headers:
                print(f"   프록시: {response.headers.get('X-Proxy-By')}")
            
            return response
            
        except Exception as e:
            print(f"❌ 요청 실패: {e}")
            raise
    
    def test_connection(self):
        """연결 테스트"""
        print("🧪 바이낸스 프록시 연결 테스트")
        
        try:
            # 1. 서버 시간 테스트
            response = self._make_request('GET', '/api/v3/time')
            if response.status_code == 200:
                server_time = response.json()
                print(f"✅ 서버 시간: {server_time}")
            else:
                print(f"❌ 서버 시간 조회 실패: {response.status_code}")
                return False
            
            # 2. 계정 정보 테스트 (API 키 필요)
            if self.api_key and self.secret_key:
                response = self._make_request('GET', '/api/v3/account', signed=True)
                if response.status_code == 200:
                    account_info = response.json()
                    print(f"✅ 계정 인증 성공")
                    print(f"   계정 타입: {account_info.get('accountType')}")
                    print(f"   거래 가능: {account_info.get('canTrade')}")
                    return True
                else:
                    print(f"❌ 계정 인증 실패: {response.status_code}")
                    try:
                        error = response.json()
                        print(f"   오류: {error}")
                    except:
                        print(f"   응답: {response.text}")
                    return False
            else:
                print("⚠️ API 키가 없어서 계정 테스트를 건너뜁니다")
                return True
                
        except Exception as e:
            print(f"❌ 연결 테스트 실패: {e}")
            return False
    
    def get_account_info(self):
        """계정 정보 조회"""
        return self._make_request('GET', '/api/v3/account', signed=True)
    
    def get_server_time(self):
        """서버 시간 조회"""
        return self._make_request('GET', '/api/v3/time')
    
    def get_exchange_info(self):
        """거래소 정보 조회"""
        return self._make_request('GET', '/api/v3/exchangeInfo')
    
    def place_order(self, symbol, side, type, quantity, **kwargs):
        """주문 실행"""
        params = {
            'symbol': symbol,
            'side': side,
            'type': type,
            'quantity': quantity,
            **kwargs
        }
        return self._make_request('POST', '/api/v3/order', params, signed=True)

# 사용 예시
if __name__ == "__main__":
    client = BinanceProxyClient()
    client.test_connection()
