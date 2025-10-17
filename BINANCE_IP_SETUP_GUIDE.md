# 🔐 바이낸스 API IP 제한 설정 가이드

## 📊 현재 Railway IP 정보

```
🌐 Railway 서버 IP: 175.223.10.67
📍 위치: Seoul, South Korea  
🏢 ISP: Korea Telecom
🌏 리전: Asia-Southeast1 (Railway)
```

## 🎯 바이낸스 API 키 IP 제한 설정

### 1단계: 바이낸스 계정 접속

1. **바이낸스 로그인**
   - https://www.binance.com 접속
   - 계정 로그인

2. **API 관리 페이지 접속**
   - 우측 상단 프로필 아이콘 클릭
   - `API Management` 선택
   - 또는 직접 링크: https://www.binance.com/en/my/settings/api-management

### 2단계: API 키 생성 또는 편집

#### 새 API 키 생성하는 경우:
1. `Create API` 버튼 클릭
2. API 키 라벨 입력 (예: "Railway-Trading-Bot")
3. 보안 인증 완료 (SMS, 이메일, Google Authenticator)

#### 기존 API 키 편집하는 경우:
1. 기존 API 키 옆의 `Edit` 버튼 클릭
2. 보안 인증 완료

### 3단계: IP 제한 설정

1. **IP Access Restrictions 섹션에서:**
   - `Restrict access to trusted IPs only` 체크박스 활성화

2. **IP 주소 추가:**
   ```
   175.223.10.67
   ```
   - 위 IP 주소를 입력 필드에 추가
   - `Confirm` 버튼 클릭

3. **권한 설정:**
   - ✅ `Enable Reading` (필수)
   - ✅ `Enable Spot & Margin Trading` (거래 필요시)
   - ✅ `Enable Futures` (선물 거래 필요시)
   - ❌ `Enable Withdrawals` (보안상 비활성화 권장)

### 4단계: API 키 정보 저장

생성된 API 키 정보를 안전하게 저장:
- **API Key**: 공개 키 (Railway 환경변수에 설정)
- **Secret Key**: 비밀 키 (Railway 환경변수에 설정)

## 🚂 Railway 환경변수 설정

Railway 대시보드에서 환경변수 설정:

```bash
# Railway CLI로 설정
railway variables --set "BINANCE_API_KEY=your_actual_api_key_here"
railway variables --set "BINANCE_SECRET_KEY=your_actual_secret_key_here"
railway variables --set "BINANCE_TESTNET=false"
```

또는 Railway 대시보드에서:
1. 프로젝트 → 서비스 → Settings → Variables
2. 다음 변수들 추가:
   - `BINANCE_API_KEY`: 바이낸스 API 키
   - `BINANCE_SECRET_KEY`: 바이낸스 시크릿 키
   - `BINANCE_TESTNET`: `false` (실제 거래용)

## 🧪 연결 테스트

환경변수 설정 후 연결 테스트:

```bash
python binance_ip_monitor.py
```

성공적인 연결 시 출력 예시:
```
🔗 바이낸스 API 연결 테스트:
   ✅ 연결 성공
   계정 타입: SPOT
   거래 가능: True
   권한: ['SPOT']
```

## ⚠️ IP 변경 모니터링

Railway IP는 다음 상황에서 변경될 수 있습니다:
- 서비스 재배포
- Railway 인프라 변경
- 리전 변경

### 자동 모니터링 설정

1. **정기적 IP 체크**
   ```python
   # cron job 또는 스케줄러로 실행
   python binance_ip_monitor.py
   ```

2. **IP 변경 감지 시 알림**
   - 로그 파일 모니터링
   - 이메일/슬랙 알림 설정 (선택사항)

## 🚨 IP 변경 시 대응 방법

IP가 변경된 경우:

1. **새 IP 확인**
   ```bash
   python check_railway_ip.py
   ```

2. **바이낸스 API 설정 업데이트**
   - 바이낸스 API 관리 페이지 접속
   - 기존 IP 삭제
   - 새 IP 추가

3. **연결 테스트**
   ```bash
   python binance_ip_monitor.py
   ```

## 🔒 보안 권장사항

### API 키 보안
- ✅ IP 제한 활성화
- ✅ 최소 권한 원칙 (필요한 권한만)
- ❌ 출금 권한 비활성화
- ✅ 정기적인 API 키 갱신

### 환경변수 보안
- ✅ Railway 환경변수 사용 (코드에 하드코딩 금지)
- ✅ .env 파일을 .gitignore에 추가
- ✅ API 키 노출 방지

### 모니터링
- ✅ 정기적인 IP 확인
- ✅ API 연결 상태 모니터링
- ✅ 비정상적인 거래 활동 감시

## 📋 체크리스트

### 초기 설정
- [ ] 바이낸스 API 키 생성
- [ ] IP 제한 설정 (175.223.10.67)
- [ ] 적절한 권한 설정
- [ ] Railway 환경변수 설정
- [ ] 연결 테스트 성공

### 정기 점검
- [ ] 주간 IP 확인
- [ ] 월간 API 키 상태 점검
- [ ] 거래 로그 검토
- [ ] 보안 설정 재확인

## 🆘 문제 해결

### 일반적인 오류들

1. **IP 제한 오류 (-2015, -1021)**
   - 현재 IP가 허용 목록에 없음
   - 바이낸스에서 IP 업데이트 필요

2. **API 키 오류 (-1022)**
   - 잘못된 API 키 또는 시크릿
   - 환경변수 확인 필요

3. **권한 오류**
   - API 키 권한 부족
   - 바이낸스에서 권한 설정 확인

### 지원 연락처
- 바이낸스 고객지원: https://www.binance.com/en/support
- Railway 지원: https://railway.app/help

## 🎉 완료!

이제 Railway에서 바이낸스 API에 안전하게 접근할 수 있습니다:
- ✅ 고정 IP 제한으로 보안 강화
- ✅ 자동 모니터링으로 IP 변경 감지
- ✅ 안전한 환경변수 관리

정기적으로 `python binance_ip_monitor.py`를 실행하여 연결 상태를 확인하세요!