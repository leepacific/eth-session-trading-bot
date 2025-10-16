# 🌐 Cloudflare + Railway 통합 가이드

## 📋 개요
Railway 프로젝트에 Cloudflare를 통해 고정 IP와 커스텀 도메인을 설정하는 방법

## 🎯 목표
- 고정 IP 주소 제공
- 커스텀 도메인 연결
- SSL/TLS 자동 적용
- DDoS 보호 및 CDN 활용

## 🚀 1단계: Cloudflare 계정 생성

1. **Cloudflare 가입**
   - https://dash.cloudflare.com/sign-up 접속
   - 무료 계정 생성

2. **도메인 추가**
   - "Add a Site" 클릭
   - 도메인 입력 (예: `eth-trading-bot.com`)
   - Free 플랜 선택

## 🔧 2단계: DNS 설정

### A. 네임서버 변경
도메인 등록업체에서 네임서버를 Cloudflare로 변경:
```
ns1.cloudflare.com
ns2.cloudflare.com
```

### B. DNS 레코드 추가
Cloudflare 대시보드 → DNS → Records:
```
Type: CNAME
Name: api (또는 원하는 서브도메인)
Content: your-railway-app.railway.app
Proxy: Enabled (주황색 구름)
```

## 🚇 3단계: Cloudflare Tunnel 설정

### A. Cloudflare Tunnel 생성
```bash
# Cloudflared 설치 (Windows)
winget install --id Cloudflare.cloudflared

# 로그인
cloudflared tunnel login

# 터널 생성
cloudflared tunnel create eth-trading-bot

# 터널 라우팅 설정
cloudflared tunnel route dns eth-trading-bot api.your-domain.com
```

### B. 터널 설정 파일 생성
`config.yml` 파일:
```yaml
tunnel: eth-trading-bot
credentials-file: /path/to/credentials.json

ingress:
  - hostname: api.your-domain.com
    service: https://your-railway-app.railway.app
  - service: http_status:404
```

## 🚂 4단계: Railway 프로젝트 설정

### A. Railway에서 커스텀 도메인 추가
1. Railway 대시보드 → 프로젝트 선택
2. Settings → Domains
3. "Custom Domain" 추가: `api.your-domain.com`

### B. 환경변수 추가
Railway Variables에 추가:
```env
CLOUDFLARE_TUNNEL_TOKEN=your_tunnel_token
CUSTOM_DOMAIN=api.your-domain.com
USE_CLOUDFLARE=true
```

## 🔒 5단계: SSL/TLS 설정

Cloudflare 대시보드 → SSL/TLS:
- **Encryption Mode**: Full (strict)
- **Edge Certificates**: Universal SSL 활성화
- **Always Use HTTPS**: 활성화

## 📊 6단계: 성능 최적화

### A. Caching Rules
Cloudflare 대시보드 → Caching → Configuration:
```
Cache Level: Standard
Browser Cache TTL: 4 hours
```

### B. Page Rules
```
URL: api.your-domain.com/health*
Settings: Cache Level = Bypass
```

## 🛡️ 7단계: 보안 설정

### A. Firewall Rules
```
Field: Country
Operator: does not equal
Value: [허용할 국가 목록]
Action: Block
```

### B. Rate Limiting
```
URL: api.your-domain.com/api/*
Requests: 100 per minute
Action: Block
```

## 🔧 8단계: Railway 프로젝트 업데이트

Cloudflare 통합을 위한 코드 수정이 필요합니다.