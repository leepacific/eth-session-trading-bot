# Railway 배포 가이드

## 1. 환경 변수 설정

Railway 대시보드에서 다음 환경 변수들을 설정하세요:

### 필수 환경 변수
```
BINANCE_API_KEY=your_actual_api_key
BINANCE_SECRET_KEY=your_actual_secret_key
BINANCE_TESTNET=true  # 테스트용, 실제 거래시 false
```

### 선택적 환경 변수
```
SYMBOL=ETHUSDT
INTERVAL=15m
INITIAL_BALANCE=100000
MAX_ACCOUNT_RISK_PER_TRADE=0.05
LIQUIDATION_PROBABILITY=0.07
MAX_LEVERAGE=125
LOG_LEVEL=INFO
```

## 2. 바이낸스 API 키 생성

1. 바이낸스 계정 로그인
2. API Management 페이지 이동
3. 새 API 키 생성
4. 다음 권한 활성화:
   - ✅ Enable Reading
   - ✅ Enable Futures
   - ✅ Enable Spot & Margin Trading (필요시)

## 3. 테스트넷 설정 (권장)

실제 자금을 사용하기 전에 테스트넷에서 테스트:

1. https://testnet.binancefuture.com 방문
2. 테스트넷 API 키 생성
3. `BINANCE_TESTNET=true` 설정

## 4. Railway 배포

```bash
# 프로젝트 배포
railway up

# 로그 확인
railway logs

# 환경 변수 설정
railway variables set BINANCE_API_KEY=your_key
railway variables set BINANCE_SECRET_KEY=your_secret
```

## 5. 모니터링

- Railway 대시보드에서 로그 모니터링
- 거래 실행 상태 확인
- 계좌 잔고 변화 추적

## 6. 주의사항

⚠️ **중요**: 
- 처음에는 반드시 테스트넷 사용
- 소액으로 시작
- 24시간 모니터링 필요
- API 키 보안 유지

## 7. 문제 해결

### 일반적인 오류들:
- API 키 권한 부족
- 네트워크 연결 문제
- 잔고 부족
- 레버리지 제한

### 로그 확인:
```bash
railway logs --tail
```