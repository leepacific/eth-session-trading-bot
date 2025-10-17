#!/usr/bin/env python3
"""
Cloudflare Tunnel을 통한 바이낸스 API 클라이언트
"""

import requests
import hmac
import hashlib
import time
import os
from urllib.parse import urlencode

class BinanceCloudflareClient:
    def __init__(self):
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.secret_key = os.getenv('BINANCE_SECRET_KEY')
        self.proxy_url = os.getenv('BINANCE_PROXY_URL', 'https://binance-proxy.leepacific-eth-trading-bot.site')
        self.use_proxy = os.getenv('USE_CLOUDFLARE_PROXY', 'false').lower() == 'true'
        
        if self.use_proxy:
            self.base_url = self.proxy_url.rstrip('/')
            print(f"🌐 Cloudflare Tunnel 사용: {self.base_url}")
        else:
            self.base_url = "https://api.binance.com"
            print(f"🔗 직접 연결 사용: {self.base_url}")
    
    def _generate_signature(self, params):
        """API 서명 생성"""
        query_string = urlencode(params)
        return hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _make_request(self, method, endpoint, params=None, signed=False):
        """API 요청 실행"""
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
        
        # URL 구성
        url = f"{self.base_url}{endpoint}"
        
        # 요청 실행
        if method == 'GET':
            response = requests.get(url, params=params, headers=headers, timeout=30)
        elif method == 'POST':
            response = requests.post(url, json=params, headers=headers, timeout=30)
        else:
            raise ValueError(f"지원하지 않는 메서드: {method}")
        
        return response
    
    def test_connection(self):
        """연결 테스트"""
        print("🧪 바이낸스 연결 테스트")
        
        try:
            # 1. 서버 시간 테스트
            print("1. 서버 시간 테스트...")
            response = self._make_request('GET', '/api/v3/time')
            
            if response.status_code == 200:
                server_time = response.json()
                print(f"   ✅ 성공: {server_time}")
            else:
                print(f"   ❌ 실패: {response.status_code}")
                return False
            
            # 2. 계정 정보 테스트 (API 키 필요)
            if self.api_key and self.secret_key:
                print("2. 계정 정보 테스트...")
                response = self._make_request('GET', '/api/v3/account', signed=True)
                
                if response.status_code == 200:
                    account_info = response.json()
                    print(f"   ✅ 인증 성공")
                    print(f"   계정 타입: {account_info.get('accountType')}")
                    print(f"   거래 가능: {account_info.get('canTrade')}")
                    return True
                else:
                    print(f"   ❌ 인증 실패: {response.status_code}")
                    try:
                        error = response.json()
                        print(f"   오류: {error}")
                    except:
                        print(f"   응답: {response.text}")
                    return False
            else:
                print("2. API 키가 없어서 계정 테스트를 건너뜁니다")
                return True
        
        except Exception as e:
            print(f"❌ 연결 테스트 실패: {e}")
            return False
    
    def get_server_time(self):
        """서버 시간 조회"""
        return self._make_request('GET', '/api/v3/time')
    
    def get_account_info(self):
        """계정 정보 조회"""
        return self._make_request('GET', '/api/v3/account', signed=True)
    
    def get_exchange_info(self):
        """거래소 정보 조회"""
        return self._make_request('GET', '/api/v3/exchangeInfo')

if __name__ == "__main__":
    client = BinanceCloudflareClient()
    client.test_connection()