#!/usr/bin/env python3
"""
Cloudflare Workers 바이낸스 프록시 설정 스크립트
"""

import requests
import json
import os
from datetime import datetime

def create_worker_script():
    """Cloudflare Worker 스크립트 생성"""
    
    worker_script = '''
// Cloudflare Worker - 바이낸스 API 프록시
export default {
  async fetch(request, env, ctx) {
    // CORS 헤더 설정
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, X-MBX-APIKEY, X-API-Key, Authorization',
    };

    // OPTIONS 요청 처리 (CORS preflight)
    if (request.method === 'OPTIONS') {
      return new Response(null, { 
        status: 200,
        headers: corsHeaders 
      });
    }

    try {
      const url = new URL(request.url);
      
      // 바이낸스 API URL 구성
      const binanceBaseUrl = 'https://api.binance.com';
      const targetUrl = binanceBaseUrl + url.pathname + url.search;
      
      console.log(`Proxying request to: ${targetUrl}`);
      
      // 원본 요청 헤더 복사
      const headers = new Headers();
      
      // 중요한 헤더들만 복사
      const allowedHeaders = [
        'x-mbx-apikey',
        'content-type',
        'user-agent'
      ];
      
      for (const [key, value] of request.headers) {
        const lowerKey = key.toLowerCase();
        if (allowedHeaders.includes(lowerKey)) {
          headers.set(key, value);
        }
      }
      
      // User-Agent 설정 (바이낸스 요구사항)
      if (!headers.has('User-Agent')) {
        headers.set('User-Agent', 'Cloudflare-Worker-Binance-Proxy/1.0');
      }
      
      // 요청 생성
      const proxyRequest = new Request(targetUrl, {
        method: request.method,
        headers: headers,
        body: request.method !== 'GET' && request.method !== 'HEAD' ? request.body : null,
      });

      // 바이낸스 API 호출
      const response = await fetch(proxyRequest);
      
      // 응답 헤더 설정
      const responseHeaders = new Headers(response.headers);
      
      // CORS 헤더 추가
      Object.entries(corsHeaders).forEach(([key, value]) => {
        responseHeaders.set(key, value);
      });
      
      // 프록시 정보 헤더 추가
      responseHeaders.set('X-Proxy-By', 'Cloudflare-Workers');
      responseHeaders.set('X-Proxy-Timestamp', new Date().toISOString());
      responseHeaders.set('X-Proxy-Target', targetUrl);
      
      // 응답 반환
      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: responseHeaders,
      });
      
    } catch (error) {
      console.error('Proxy error:', error);
      
      return new Response(JSON.stringify({
        error: 'Proxy Error',
        message: error.message,
        timestamp: new Date().toISOString(),
        worker: 'binance-api-proxy'
      }), {
        status: 500,
        headers: {
          'Content-Type': 'application/json',
          ...corsHeaders
        }
      });
    }
  },
};
'''
    
    return worker_script

def get_cloudflare_ips():
    """Cloudflare IP 범위 조회"""
    try:
        print("🌐 Cloudflare IP 범위 조회 중...")
        
        # IPv4 범위
        ipv4_response = requests.get("https://www.cloudflare.com/ips-v4", timeout=10)
        ipv4_ranges = ipv4_response.text.strip().split('\n') if ipv4_response.status_code == 200 else []
        
        print(f"✅ Cloudflare IPv4 범위: {len(ipv4_ranges)}개")
        for ip_range in ipv4_ranges[:5]:  # 처음 5개만 표시
            print(f"   {ip_range}")
        
        if len(ipv4_ranges) > 5:
            print(f"   ... 및 {len(ipv4_ranges) - 5}개 더")
        
        return ipv4_ranges
        
    except Exception as e:
        print(f"❌ Cloudflare IP 조회 실패: {e}")
        return []

def create_binance_proxy_client():
    """바이낸스 프록시 클라이언트 코드 생성"""
    
    client_code = '''
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
'''
    
    return client_code

def main():
    """메인 실행"""
    print("🌐 Cloudflare Workers 바이낸스 프록시 설정")
    print("=" * 80)
    
    # 1. Worker 스크립트 생성
    print("📝 Cloudflare Worker 스크립트 생성 중...")
    worker_script = create_worker_script()
    
    with open('binance_proxy_worker.js', 'w', encoding='utf-8') as f:
        f.write(worker_script)
    
    print("✅ Worker 스크립트 저장: binance_proxy_worker.js")
    
    # 2. 클라이언트 코드 생성
    print("📝 바이낸스 프록시 클라이언트 생성 중...")
    client_code = create_binance_proxy_client()
    
    with open('binance_proxy_client.py', 'w', encoding='utf-8') as f:
        f.write(client_code)
    
    print("✅ 클라이언트 코드 저장: binance_proxy_client.py")
    
    # 3. Cloudflare IP 범위 조회
    cloudflare_ips = get_cloudflare_ips()
    
    # 4. 설정 가이드 출력
    print(f"\n" + "=" * 80)
    print("📋 다음 단계 가이드")
    print("=" * 80)
    
    print("1. Cloudflare Workers 배포:")
    print("   - https://dash.cloudflare.com → Workers & Pages")
    print("   - Create application → Create Worker")
    print("   - binance_proxy_worker.js 내용을 복사하여 붙여넣기")
    print("   - Save and Deploy")
    
    print("\\n2. Worker URL 확인:")
    print("   - 배포 후 Worker URL 복사 (예: https://binance-proxy.your-account.workers.dev)")
    
    print("\\n3. Railway 환경변수 설정:")
    print("   railway variables --set \"BINANCE_PROXY_URL=https://your-worker-url\"")
    print("   railway variables --set \"USE_CLOUDFLARE_PROXY=true\"")
    
    print("\\n4. 바이낸스 API 키 IP 제한 설정:")
    print("   - 바이낸스 API 관리에서 다음 IP 범위들을 허용 목록에 추가:")
    
    if cloudflare_ips:
        for ip_range in cloudflare_ips[:10]:  # 처음 10개만 표시
            print(f"     {ip_range}")
        
        if len(cloudflare_ips) > 10:
            print(f"     ... 및 {len(cloudflare_ips) - 10}개 더")
            print("     (전체 목록은 https://www.cloudflare.com/ips-v4 참조)")
    
    print("\\n5. 테스트:")
    print("   python binance_proxy_client.py")
    
    # 결과 저장
    setup_info = {
        'timestamp': datetime.now().isoformat(),
        'worker_script_file': 'binance_proxy_worker.js',
        'client_code_file': 'binance_proxy_client.py',
        'cloudflare_ip_ranges': cloudflare_ips,
        'setup_steps': [
            'Deploy Cloudflare Worker',
            'Set Railway environment variables',
            'Configure Binance API IP restrictions',
            'Test connection'
        ]
    }
    
    with open('cloudflare_proxy_setup.json', 'w', encoding='utf-8') as f:
        json.dump(setup_info, f, indent=2, ensure_ascii=False)
    
    print(f"\\n📄 설정 정보 저장: cloudflare_proxy_setup.json")

if __name__ == "__main__":
    main()