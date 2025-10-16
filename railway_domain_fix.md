# 🚂 Railway 커스텀 도메인 문제 해결 가이드

## 🔍 문제 진단

`https://api.leepacific-eth-trading-bot.site/`에서 404 오류가 발생하는 이유:

### 가능한 원인들:
1. **Railway 커스텀 도메인 미설정**
2. **Cloudflare DNS 설정 오류**
3. **SSL 인증서 발급 대기 중**
4. **Railway 서비스 연결 문제**

## 🛠️ 해결 단계

### 1단계: Railway 환경변수 확인

Railway 대시보드에서 다음 환경변수들이 올바르게 설정되어 있는지 확인:

```env
# 필수 환경변수
RAILWAY_ENVIRONMENT=production
PORT=8080

# Cloudflare 설정
USE_CLOUDFLARE=true
CUSTOM_DOMAIN=api.leepacific-eth-trading-bot.site
CLOUDFLARE_API_TOKEN=your_actual_token
CLOUDFLARE_ZONE_ID=your_actual_zone_id

# 바이낸스 API (실제 값으로 설정)
BINANCE_API_KEY=your_actual_api_key
BINANCE_SECRET_KEY=your_actual_secret_key
BINANCE_TESTNET=false
```

### 2단계: Railway 커스텀 도메인 설정

1. **Railway 대시보드 접속**
   - https://railway.app/dashboard
   - 프로젝트 선택

2. **서비스 설정**
   - 서비스 클릭 → Settings → Domains

3. **커스텀 도메인 추가**
   ```
   Domain: api.leepacific-eth-trading-bot.site
   ```

4. **SSL 인증서 확인**
   - 녹색 체크마크가 나타날 때까지 대기 (최대 10분)

### 3단계: Cloudflare DNS 설정 확인

1. **Cloudflare 대시보드**
   - https://dash.cloudflare.com
   - 도메인 선택

2. **DNS 레코드 확인**
   ```
   Type: CNAME
   Name: api
   Target: your-railway-app.up.railway.app
   Proxy: Enabled (주황색 구름 ✅)
   ```

3. **SSL/TLS 설정**
   - SSL/TLS → Overview
   - Encryption mode: Full (strict)

### 4단계: Railway 기본 도메인으로 테스트

커스텀 도메인 문제를 우회하여 Railway 기본 도메인으로 먼저 테스트:

```
https://your-project-name.up.railway.app/
```

## 🔧 임시 해결책

커스텀 도메인 설정이 완료될 때까지 Railway 기본 도메인 사용:

1. **Railway 대시보드에서 기본 도메인 확인**
2. **해당 도메인으로 접속 테스트**
3. **정상 작동 확인 후 커스텀 도메인 재설정**

## 📋 체크리스트

- [ ] Railway 환경변수 모두 설정됨
- [ ] Railway 커스텀 도메인 추가됨
- [ ] SSL 인증서 발급 완료 (녹색 체크)
- [ ] Cloudflare DNS 레코드 설정됨
- [ ] Cloudflare 프록시 활성화됨
- [ ] Railway 기본 도메인으로 테스트 성공

## 🚨 긴급 해결 방법

만약 계속 문제가 발생하면:

1. **Railway 커스텀 도메인 삭제 후 재추가**
2. **Cloudflare DNS 레코드 삭제 후 재생성**
3. **Railway 서비스 재배포**