# 🚂 Railway 환경변수 설정 가이드

## 🎯 목표
Railway 프로젝트에 Cloudflare 연동을 위한 환경변수 설정

## 📋 1단계: Railway 대시보드 접속

### 1. Railway 프로젝트 접속
1. https://railway.app/dashboard 접속
2. `eth-trading-bot` 프로젝트 클릭
3. 배포된 서비스 클릭

### 2. Variables 탭 이동
- 상단 메뉴에서 "Variables" 탭 클릭

## 📋 2단계: 환경변수 추가

### 필수 환경변수 목록:

#### 🔐 Binance API (실제 거래용)
```
BINANCE_API_KEY=your_actual_binance_api_key
BINANCE_SECRET_KEY=your_actual_binance_secret_key
BINANCE_TESTNET=false

```

#### 📊 데이터 설정
```
DATA_SYMBOL=ETHUSDT
DATA_INTERVAL=15m
DATA_POINTS_TARGET=500000
```

#### 💰 트레이딩 설정
```
INITIAL_BALANCE=100
MAX_ACCOUNT_RISK_PER_TRADE=0.05
LIQUIDATION_PROBABILITY=0.07
MAX_LEVERAGE=125
```

#### 🌐 Cloudflare 설정
```
USE_CLOUDFLARE=true
CLOUDFLARE_API_TOKEN=your_cloudflare_api_token_here
CLOUDFLARE_ZONE_ID=your_zone_id_here
CUSTOM_DOMAIN=api.구입한도메인.com
```

**실제 예시** (도메인이 `eth-trading-bot.com`인 경우):
```
CUSTOM_DOMAIN=api.eth-trading-bot.com
```

#### 🚂 Railway 설정
```
RAILWAY_ENVIRONMENT=production
PORT=8080
```

## 📋 3단계: 환경변수 입력 방법

### 각 환경변수 추가:
1. "New Variable" 버튼 클릭
2. **Variable Name** 입력 (예: `CLOUDFLARE_API_TOKEN`)
3. **Value** 입력 (실제 토큰 값)
4. "Add" 클릭
5. 모든 변수에 대해 반복

### ⚠️ 중요 주의사항:
- **API 키는 절대 공개하지 마세요**
- **토큰 값에 공백이 없는지 확인**
- **도메인명은 정확히 입력** (예: `api.eth-trading-bot.com`)

## 📋 4단계: 실제 값 입력 예시

### 예시 (실제 값으로 교체 필요):
```
CLOUDFLARE_API_TOKEN=1234567890abcdef1234567890abcdef12345678
CLOUDFLARE_ZONE_ID=abcdef1234567890abcdef1234567890
CUSTOM_DOMAIN=api.eth-trading-bot.com
BINANCE_API_KEY=your_binance_api_key_from_binance_dashboard
BINANCE_SECRET_KEY=your_binance_secret_key_from_binance_dashboard
```

## 📋 5단계: 배포 확인

### 자동 재배포:
- 환경변수 저장 시 Railway가 자동으로 재배포
- "Deployments" 탭에서 배포 상태 확인
- 로그에서 오류 없는지 확인

### 배포 로그 확인:
```
🌐 Cloudflare 통합 초기화
   도메인: api.your-domain.com
   터널 토큰: 설정됨
🚀 Railway 트레이딩 봇 초기화
   환경: production
```

## 🔍 6단계: 테스트

### 헬스체크 테스트:
1. Railway에서 제공하는 임시 URL 확인
2. 브라우저에서 `https://your-app.railway.app/health` 접속
3. JSON 응답 확인:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-15T...",
  "service": "eth-session-trading-bot",
  "version": "1.0.0"
}
```

## ✅ 완료 확인

### 체크리스트:
- [ ] 모든 환경변수 입력 완료
- [ ] Railway 재배포 성공
- [ ] 헬스체크 엔드포인트 정상 응답
- [ ] 배포 로그에 오류 없음
- [ ] Cloudflare 통합 메시지 확인

### 다음 단계:
도메인 연결 및 최종 테스트