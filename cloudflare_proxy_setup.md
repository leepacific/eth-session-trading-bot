# 🌐 Cloudflare Workers를 통한 바이낸스 API 고정 IP 프록시

## 📋 개요

Railway의 동적 IP 문제를 해결하기 위해 Cloudflare Workers를 프록시로 사용하여 고정 IP에서 바이낸스 API에 접근하는 방법입니다.

## 🎯 목표

- Railway → Cloudflare Workers → 바이낸스 API
- 고정된 Cloudflare IP를 통해 바이낸스 접근
- 바이낸스 API 키에 IP 제한 설정 가능

## 🔧 설정 단계

### 1단계: Cloudflare Workers 생성

1. **Cloudflare 대시보드 접속**
   - https://dash.cloudflare.com
   - `Workers & Pages` 메뉴 클릭

2. **새 Worker 생성**
   - `Create application` 클릭
   - `Create Worker` 선택
   - 이름: `binance-api-proxy`

### 2단계: Worker 코드 작성

```javascript
// Cloudflare Worker - 바이낸스 API 프록시
export default {
  async fetch(request, env, ctx) {
    // CORS 헤더 설정
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, X-API-Key, X-API-Secret, X-API-Timestamp, X-API-Signature',
    };

    // OPTIONS 요청 처리 (CORS preflight)
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    try {
      const url = new URL(request.url);
      
      // 바이낸스 API URL 구성
      const binanceBaseUrl = 'https://api.binance.com';
      const targetUrl = binanceBaseUrl + url.pathname + url.search;
      
      // 원본 요청 헤더 복사
      const headers = new Headers(request.headers);
      
      // User-Agent 설정
      headers.set('User-Agent', 'Cloudflare-Worker-Binance-Proxy/1.0');
      
      // 요청 생성
      const proxyRequest = new Request(targetUrl, {
        method: request.method,
        headers: headers,
        body: request.method !== 'GET' && request.method !== 'HEAD' ? request.body : null,
      });

      // 바이낸스 API 호출
      const response = await fetch(proxyRequest);
      
      // 응답 헤더에 CORS 추가
      const responseHeaders = new Headers(response.headers);
      Object.entries(corsHeaders).forEach(([key, value]) => {
        responseHeaders.set(key, value);
      });
      
      // 프록시 정보 헤더 추가
      responseHeaders.set('X-Proxy-By', 'Cloudflare-Workers');
      responseHeaders.set('X-Proxy-Timestamp', new Date().toISOString());
      
      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: responseHeaders,
      });
      
    } catch (error) {
      return new Response(JSON.stringify({
        error: 'Proxy Error',
        message: error.message,
        timestamp: new Date().toISOString()
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
```

### 3단계: Worker 배포 및 도메인 설정

1. **Worker 배포**
   - 코드 입력 후 `Save and Deploy` 클릭
   - Worker URL 확인: `https://binance-api-proxy.your-account.workers.dev`

2. **커스텀 도메인 설정** (선택사항)
   - `Settings` → `Triggers` → `Custom Domains`
   - 예: `binance-proxy.yourdomain.com`

### 4단계: Cloudflare IP 범위 확인

Cloudflare의 고정 IP 범위를 확인합니다:

```bash
# Cloudflare IPv4 범위
curl https://www.cloudflare.com/ips-v4

# 주요 IP 범위 (예시):
# 173.245.48.0/20
# 103.21.244.0/22
# 103.22.200.0/22
# 103.31.4.0/22
# 141.101.64.0/18
# 108.162.192.0/18
# 190.93.240.0/20
# 188.114.96.0/20
# 197.234.240.0/22
# 198.41.128.0/17
# 162.158.0.0/15
# 104.16.0.0/13
# 104.24.0.0/14
# 172.64.0.0/13
# 131.0.72.0/22
```

## 🔧 Railway 봇 코드 수정

Railway 봇에서 Cloudflare 프록시를 사용하도록 수정:

```python
# binance_proxy_client.py
import requests
import hmac
import hashlib
import time
from urllib.parse import urlencode

class BinanceProxyClient:
    def __init__(self, api_key, secret_key, proxy_url):
        self.api_key = api_key
        self.secret_key = secret_key
        self.proxy_url = proxy_url.rstrip('/')
        
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
            params['timestamp'] = int(time.time() * 1000)
            params['signature'] = self._generate_signature(params)
        
        # 헤더 설정
        headers = {
            'X-MBX-APIKEY': self.api_key,
            'Content-Type': 'application/json'
        }
        
        # 프록시 URL 구성
        url = f"{self.proxy_url}{endpoint}"
        
        # 요청 실행
        if method == 'GET':
            response = requests.get(url, params=params, headers=headers)
        elif method == 'POST':
            response = requests.post(url, json=params, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")
            
        return response
    
    def get_account_info(self):
        """계정 정보 조회"""
        return self._make_request('GET', '/api/v3/account', signed=True)
    
    def get_server_time(self):
        """서버 시간 조회"""
        return self._make_request('GET', '/api/v3/time')
    
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
```

## 🔐 바이낸스 API 키 IP 제한 설정

### 1. 바이낸스 계정 설정

1. **바이낸스 계정 로그인**
   - https://www.binance.com
   - API Management 페이지 접속

2. **API 키 편집**
   - 기존 API 키 선택 또는 새로 생성
   - `Edit restrictions` 클릭

3. **IP 제한 설정**
   - `Restrict access to trusted IPs only` 활성화
   - Cloudflare IP 범위 추가:
     ```
     173.245.48.0/20
     103.21.244.0/22
     103.22.200.0/22
     141.101.64.0/18
     108.162.192.0/18
     162.158.0.0/15
     104.16.0.0/13
     172.64.0.0/13
     ```

### 2. 권한 설정
- `Enable Reading` ✅
- `Enable Spot & Margin Trading` ✅ (필요시)
- `Enable Futures` ✅ (필요시)
- `Enable Withdrawals` ❌ (보안상 비활성화 권장)

## 🧪 테스트 방법

### 1. 프록시 테스트
```python
# test_cloudflare_proxy.py
from binance_proxy_client import BinanceProxyClient

# 프록시 클라이언트 생성
client = BinanceProxyClient(
    api_key="your_api_key",
    secret_key="your_secret_key", 
    proxy_url="https://binance-api-proxy.your-account.workers.dev"
)

# 서버 시간 테스트
response = client.get_server_time()
print(f"Server Time: {response.json()}")

# 계정 정보 테스트 (IP 제한 확인)
response = client.get_account_info()
print(f"Account Info: {response.status_code}")
```

### 2. IP 확인
```python
# Cloudflare Worker를 통한 IP 확인
import requests

response = requests.get("https://httpbin.org/ip", 
                       proxies={"https": "https://your-proxy.workers.dev"})
print(f"Proxy IP: {response.json()}")
```

## 📊 장점과 단점

### ✅ 장점
- **고정 IP**: Cloudflare의 안정적인 IP 범위 사용
- **글로벌 CDN**: 전 세계 어디서나 빠른 접근
- **무료**: Cloudflare Workers 무료 플랜 사용 가능
- **보안**: 바이낸스 API 키에 IP 제한 설정 가능

### ⚠️ 단점
- **추가 복잡성**: 프록시 설정 및 관리 필요
- **지연시간**: 프록시를 거치면서 약간의 지연 발생
- **의존성**: Cloudflare 서비스에 의존

## 🚀 다음 단계

1. Cloudflare Workers 설정
2. 프록시 코드 배포
3. Railway 봇 코드 수정
4. 바이낸스 API 키 IP 제한 설정
5. 테스트 및 모니터링

이 방법으로 Railway의 동적 IP 문제를 해결하고 바이낸스 API에 안전하게 접근할 수 있습니다!