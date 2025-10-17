# 🌐 Cloudflare Tunnel을 통한 바이낸스 API 안정적 연결

## 📋 개요

Cloudflare Tunnel을 사용하여 Railway → Cloudflare → 바이낸스 API 경로로 안정적인 고정 IP 연결을 구성합니다.

## 🎯 장점

- **고정 IP**: Cloudflare의 안정적인 IP 범위 사용
- **보안**: 터널을 통한 암호화된 연결
- **안정성**: Railway IP 변경에 영향받지 않음
- **성능**: Cloudflare의 글로벌 CDN 활용

## 🛠️ 설정 단계

### 1단계: Cloudflare CLI 설치 (로컬)

Windows에서 Cloudflare CLI 설치:

```powershell
# Chocolatey 사용 (권장)
choco install cloudflared

# 또는 직접 다운로드
# https://github.com/cloudflare/cloudflared/releases
# cloudflared-windows-amd64.exe를 다운로드하고 PATH에 추가
```

### 2단계: Cloudflare 계정 인증

```bash
# Cloudflare 로그인
cloudflared tunnel login
```

브라우저가 열리면 Cloudflare 계정으로 로그인하고 도메인을 선택합니다.

### 3단계: 터널 생성

```bash
# 터널 생성
cloudflared tunnel create binance-proxy-tunnel

# 터널 목록 확인
cloudflared tunnel list
```

### 4단계: 터널 설정 파일 생성

`config.yml` 파일을 생성합니다:

```yaml
# ~/.cloudflared/config.yml
tunnel: binance-proxy-tunnel
credentials-file: /path/to/your/tunnel/credentials.json

ingress:
  # 바이낸스 API 프록시
  - hostname: binance-proxy.yourdomain.com
    service: https://api.binance.com
    originRequest:
      httpHostHeader: api.binance.com
      
  # Railway 앱 연결 (선택사항)
  - hostname: app.yourdomain.com  
    service: https://eth-trading-bot-production.up.railway.app
    
  # 기본 규칙 (필수)
  - service: http_status:404
```

### 5단계: DNS 레코드 설정

```bash
# DNS 레코드 자동 생성
cloudflared tunnel route dns binance-proxy-tunnel binance-proxy.yourdomain.com
cloudflared tunnel route dns binance-proxy-tunnel app.yourdomain.com
```

## 🚂 Railway에서 Cloudflare Tunnel 사용

### Railway용 환경변수 설정

```bash
# Railway 환경변수 설정
railway variables --set "USE_CLOUDFLARE_TUNNEL=true"
railway variables --set "BINANCE_PROXY_URL=https://binance-proxy.yourdomain.com"
railway variables --set "CLOUDFLARE_TUNNEL_TOKEN=your_tunnel_token"
```

### Railway에서 터널 실행

Railway에서 터널을 실행하기 위한 스크립트를 만들어보겠습니다.

## 🔧 더 간단한 방법: Cloudflare Zero Trust

실제로는 더 간단한 방법이 있습니다. Cloudflare Zero Trust의 WARP를 사용하는 것입니다.

### Zero Trust 설정

1. **Cloudflare Zero Trust 대시보드**
   - https://one.dash.cloudflare.com
   - 팀 생성 또는 기존 팀 선택

2. **Gateway 정책 설정**
   - `Gateway` → `Policies` → `HTTP`
   - 바이낸스 API 접근 정책 생성

3. **WARP 클라이언트 설정**
   - Railway에서 WARP 클라이언트 실행
   - 고정 IP를 통한 인터넷 접근

## 💡 가장 실용적인 해결책

실제로는 다음 방법이 가장 실용적입니다:

### 방법 1: Cloudflare Workers 프록시 (권장)

```javascript
// Cloudflare Worker 코드
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    
    // 바이낸스 API로 프록시
    const targetUrl = 'https://api.binance.com' + url.pathname + url.search;
    
    const modifiedRequest = new Request(targetUrl, {
      method: request.method,
      headers: request.headers,
      body: request.body,
    });

    const response = await fetch(modifiedRequest);
    
    // CORS 헤더 추가
    const modifiedResponse = new Response(response.body, response);
    modifiedResponse.headers.set('Access-Control-Allow-Origin', '*');
    
    return modifiedResponse;
  },
};
```

### 방법 2: Railway에서 HTTP 프록시 사용

Railway에서 HTTP 프록시를 통해 고정 IP로 나가는 방법입니다.