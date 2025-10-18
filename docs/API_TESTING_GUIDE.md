# 🧪 API 테스트 가이드

## 🎯 목표
Railway에 배포된 트레이딩 봇 API의 작동 상태, IP 제한, 보안 기능을 종합적으로 테스트

## 🛠️ 테스트 도구들

### 1. 📱 웹 기반 테스트 도구 (추천)
**파일**: `web_test_tool.html`

#### 사용 방법:
1. `web_test_tool.html` 파일을 브라우저에서 열기
2. API URL 입력 (예: `https://api.your-domain.com`)
3. 원하는 테스트 버튼 클릭
4. 실시간 결과 확인

#### 테스트 기능:
- ✅ 기본 기능 테스트 (헬스체크, 상태 확인)
- ⚡ Rate Limiting 테스트
- 🛡️ 보안 헤더 확인
- ⚡ 성능 측정
- 📊 실시간 통계

### 2. 🖥️ 명령줄 테스트 도구
**파일**: `api_test_suite.py`

#### 사용 방법:
```bash
# Python 스크립트 실행
python api_test_suite.py https://api.your-domain.com

# 또는 Railway 도메인으로 테스트
python api_test_suite.py https://your-app.railway.app
```

#### 출력 예시:
```
🧪 API 테스트 스위트 초기화
   대상 URL: https://api.your-domain.com
   테스트 시작: 2025-10-15 12:00:00

🔍 기본 기능 테스트 시작...
   ✅ 헬스체크 엔드포인트: 200 (0.234s)
   ✅ 상태 확인 엔드포인트: 200 (0.189s)
   ✅ 존재하지 않는 엔드포인트: 404 (0.156s)

🛡️ 보안 헤더 테스트 시작...
   📋 보안 검사 결과:
      ✅ HTTPS
      ✅ Cloudflare
      ✅ CF-Ray
      ❌ X-Frame-Options
      ❌ X-Content-Type-Options
   🌐 Cloudflare 프록시 감지됨

⚡ 성능 테스트 시작...
   📊 성능 결과:
      평균 응답시간: 234.56ms
      최소 응답시간: 189.23ms
      최대 응답시간: 345.67ms
   ✅ 양호한 성능

⚡ Rate Limiting 테스트 시작...
   📊 결과:
      성공한 요청: 45
      Rate Limited: 5
      오류 요청: 0
      총 시간: 8.45초
      초당 요청: 5.92 req/s
   ✅ Rate Limiting이 정상 작동 중

📊 API 테스트 결과 리포트
================================================================================
🔍 기본 기능 테스트: 3/3 통과
⚡ Rate Limiting: 활성화
🛡️ 보안 검사: 3/5 통과
⚡ 평균 응답시간: 234.56ms
🎯 전체 점수: 85.2/100
✅ 양호! 대부분의 기능이 정상 작동합니다.
```

## 🔍 테스트 항목별 상세 설명

### 1. 기본 기능 테스트
#### 헬스체크 (`/health`)
```json
{
  "status": "healthy",
  "timestamp": "2025-10-15T12:00:00Z",
  "service": "eth-session-trading-bot",
  "version": "1.0.0"
}
```

#### 상태 확인 (`/status`)
```json
{
  "bot_status": "running",
  "last_update": "2025-10-15T12:00:00Z",
  "environment": "production"
}
```

### 2. Rate Limiting 테스트
- **목적**: DDoS 공격 방지 확인
- **방법**: 짧은 시간 내 대량 요청 전송
- **기대 결과**: 429 (Too Many Requests) 응답
- **Cloudflare 기본값**: 100 req/min

### 3. 보안 테스트
#### 확인 항목:
- ✅ **HTTPS**: SSL/TLS 암호화
- ✅ **Cloudflare**: 프록시 활성화
- ✅ **CF-Ray**: Cloudflare 식별자
- ⚠️ **HSTS**: HTTP Strict Transport Security
- ⚠️ **X-Frame-Options**: 클릭재킹 방지
- ⚠️ **X-Content-Type-Options**: MIME 타입 스니핑 방지

### 4. 성능 테스트
#### 측정 지표:
- **응답 시간**: 평균, 최소, 최대
- **처리량**: 초당 요청 수 (req/s)
- **안정성**: 연속 요청 성공률

#### 성능 기준:
- 🟢 **우수**: < 500ms
- 🟡 **양호**: 500ms - 1000ms
- 🔴 **개선 필요**: > 1000ms

## 🚨 문제 해결 가이드

### 일반적인 문제들:

#### 1. 연결 실패 (Connection Failed)
**원인**:
- 잘못된 URL
- DNS 전파 미완료
- 서버 다운

**해결책**:
```bash
# DNS 확인
nslookup api.your-domain.com

# Railway 앱 상태 확인
railway status

# 직접 Railway URL로 테스트
python api_test_suite.py https://your-app.railway.app
```

#### 2. SSL 인증서 오류
**원인**:
- 인증서 발급 미완료
- 도메인 불일치

**해결책**:
- Railway 커스텀 도메인 재설정
- Cloudflare SSL 설정 확인

#### 3. Rate Limiting 미작동
**원인**:
- Cloudflare 설정 누락
- 프록시 비활성화

**해결책**:
- Cloudflare DNS에서 프록시 활성화 (주황색 구름)
- Page Rules 또는 Rate Limiting 규칙 추가

#### 4. 느린 응답 시간
**원인**:
- 서버 리소스 부족
- 네트워크 지연
- 코드 최적화 필요

**해결책**:
- Railway 리소스 모니터링
- Cloudflare 캐싱 설정
- 코드 프로파일링

## 📊 테스트 결과 해석

### 점수 체계:
- **90-100점**: 🎉 우수 - 프로덕션 준비 완료
- **70-89점**: ✅ 양호 - 일부 개선 권장
- **50-69점**: ⚠️ 보통 - 개선 필요
- **0-49점**: ❌ 문제 - 설정 재검토 필요

### 우선순위:
1. **기본 기능** (필수): 헬스체크, 상태 확인
2. **보안** (중요): HTTPS, Cloudflare
3. **성능** (중요): 응답 시간 < 1초
4. **Rate Limiting** (권장): DDoS 방지

## 🔄 정기 테스트 권장사항

### 일일 테스트:
- 기본 기능 확인
- 응답 시간 모니터링

### 주간 테스트:
- 전체 보안 검사
- 성능 벤치마크

### 월간 테스트:
- Rate Limiting 효과성
- 새로운 보안 헤더 적용

## 📞 지원

### 문제 발생 시:
1. **테스트 결과 저장**: JSON 리포트 파일
2. **로그 수집**: Railway 배포 로그
3. **스크린샷**: 웹 테스트 도구 결과
4. **GitHub Issues**: 프로젝트 저장소에 문제 보고

---

## 🎯 빠른 시작

### 1분 테스트:
```bash
# 웹 도구 열기
open web_test_tool.html

# 또는 명령줄 테스트
python api_test_suite.py https://your-api-url.com
```

이제 API가 제대로 작동하는지 확인해보세요! 🚀
##
 🔗 바이낸스 연결 테스트

### 새로운 엔드포인트: `/test-binance`

#### 테스트 항목:
- ✅ **서버 시간 동기화**: 바이낸스 서버와 시간 차이 확인
- 🌐 **Cloudflare 프록시**: IP 프록시 정상 작동 확인
- 🛡️ **IP 제한/Rate Limiting**: API 사용량 제한 테스트
- 👤 **계정 정보 조회**: API 키 유효성 및 권한 확인

#### 사용 방법:
```bash
# 웹 브라우저
https://api.your-domain.com/test-binance

# 또는 curl
curl https://api.your-domain.com/test-binance
```

#### 응답 예시:
```json
{
  "timestamp": "2025-10-15T14:00:00Z",
  "test_results": {
    "server_time": true,
    "cloudflare": true,
    "ip_restrictions": true,
    "account_info": true
  },
  "passed_tests": 4,
  "total_tests": 4,
  "success_rate": 100.0,
  "status": "completed"
}
```

### 단발성 주문 테스트

#### 수동 실행 (Railway 환경):
```bash
# Railway 컨테이너에서 실행
python run_binance_test.py

# 또는 직접 테스트
python binance_connection_test.py
```

#### 테스트 주문 특징:
- **심볼**: ETHUSDT
- **수량**: 0.001 ETH (최소 수량)
- **가격**: 현재가 대비 -10% (체결되지 않음)
- **타입**: LIMIT GTC 주문
- **목적**: API 연결 및 IP 제한 테스트

#### ⚠️ 주의사항:
1. **실제 주문 전송**: 테스트넷이 아닌 실제 거래소
2. **수동 취소 필요**: 바이낸스에서 직접 주문 취소
3. **체결 방지**: 현재가에서 멀리 떨어진 가격 설정
4. **최소 수량**: 0.001 ETH로 영향 최소화

### 테스트 결과 해석

#### 성공률 기준:
- **100%**: 🎉 완벽한 연결 상태
- **75-99%**: ✅ 양호한 연결 상태  
- **50-74%**: ⚠️ 일부 문제 있음
- **50% 미만**: ❌ 심각한 연결 문제

#### 일반적인 문제들:

**1. 서버 시간 동기화 실패**
- 원인: 시스템 시간 차이
- 해결: Railway 환경에서는 자동 동기화됨

**2. Cloudflare 프록시 미감지**
- 원인: DNS 설정 문제
- 해결: Cloudflare DNS 프록시 활성화 확인

**3. 계정 정보 조회 실패**
- 원인: API 키 오류 또는 권한 부족
- 해결: 바이낸스 API 키 재생성

**4. IP 제한 테스트 실패**
- 원인: Rate Limiting 미작동
- 해결: 바이낸스 IP 제한 설정 확인