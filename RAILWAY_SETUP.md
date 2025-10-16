# 🚂 Railway 배포 가이드

## 📋 배포 단계별 가이드

### 1. 🔗 GitHub 저장소 연결

1. [Railway 대시보드](https://railway.app/dashboard) 접속
2. "New Project" 클릭
3. "Deploy from GitHub repo" 선택
4. `eth-session-trading-bot` 저장소 선택
5. "Deploy Now" 클릭

### 2. ⚙️ 환경변수 설정

Railway 프로젝트 → Settings → Environment Variables에서 다음 변수들을 설정:

#### 필수 환경변수
```env
BINANCE_API_KEY=your_actual_api_key
BINANCE_SECRET_KEY=your_actual_secret_key
BINANCE_TESTNET=false
DATA_SYMBOL=ETHUSDT
DATA_INTERVAL=15m
DATA_POINTS_TARGET=500000
INITIAL_BALANCE=100000
MAX_ACCOUNT_RISK_PER_TRADE=0.05
LIQUIDATION_PROBABILITY=0.07
MAX_LEVERAGE=125
PORT=8080
RAILWAY_ENVIRONMENT=production
```

### 3. 🔧 서비스 설정

#### 포트 설정
- Railway가 자동으로 `PORT` 환경변수를 제공
- 헬스체크 서버가 해당 포트에서 실행됨

#### 헬스체크
- 경로: `/health`
- 응답: JSON 형태의 상태 정보
- 타임아웃: 300초

### 4. 📊 모니터링

#### 헬스체크 엔드포인트
- `GET /health` - 서비스 상태 확인
- `GET /status` - 봇 상태 확인

#### 로그 확인
Railway 대시보드에서 실시간 로그 확인 가능:
- 배포 로그
- 애플리케이션 로그
- 오류 로그

### 5. 🔄 자동 배포

GitHub에 푸시할 때마다 자동 배포:
```bash
git add .
git commit -m "Update trading strategy"
git push origin main
```

### 6. 🛡️ 보안 설정

#### API 키 보안
- `.env` 파일은 Git에 포함되지 않음
- 모든 민감한 정보는 Railway 환경변수로 관리
- GitHub Secrets를 통한 CI/CD 보안

#### 네트워크 보안
- HTTPS 자동 적용
- Railway 도메인 자동 할당
- 커스텀 도메인 설정 가능

### 7. 📈 성능 최적화

#### 리소스 설정
- CPU: 자동 스케일링
- 메모리: 512MB ~ 8GB
- 디스크: 1GB (로그 및 임시 파일)

#### 캐싱
- pip 의존성 캐싱 자동 적용
- 빌드 시간 단축

### 8. 🚨 문제 해결

#### 일반적인 문제들

**1. 배포 실패**
```bash
# 로그 확인
railway logs

# 환경변수 확인
railway variables
```

**2. 헬스체크 실패**
- `/health` 엔드포인트 응답 확인
- 포트 설정 확인 (Railway가 제공하는 PORT 사용)

**3. API 연결 오류**
- 바이낸스 API 키 유효성 확인
- 네트워크 연결 상태 확인
- API 제한 확인

**4. 메모리 부족**
- 데이터 크기 확인
- 메모리 사용량 최적화
- Railway 플랜 업그레이드 고려

### 9. 📞 지원

#### Railway 지원
- [Railway 문서](https://docs.railway.app/)
- [Railway Discord](https://discord.gg/railway)
- [Railway 지원팀](https://railway.app/help)

#### 프로젝트 지원
- GitHub Issues
- 프로젝트 README.md

### 10. 💡 팁

#### 개발 워크플로우
1. 로컬에서 개발 및 테스트
2. GitHub에 푸시
3. Railway 자동 배포
4. 프로덕션 모니터링

#### 비용 최적화
- 무료 플랜: $5 크레딧/월
- 사용량 기반 과금
- 불필요한 서비스 정리

#### 백업
- GitHub에 코드 백업
- Railway 데이터베이스 백업 (필요시)
- 환경변수 별도 백업

---

## 🎯 배포 체크리스트

- [ ] GitHub 저장소 생성 및 코드 푸시
- [ ] Railway 프로젝트 생성
- [ ] GitHub 저장소 연결
- [ ] 환경변수 설정
- [ ] 첫 배포 실행
- [ ] 헬스체크 확인 (`/health`)
- [ ] 로그 모니터링
- [ ] 백테스트 결과 확인
- [ ] 자동 배포 테스트

배포 완료 후 Railway 대시보드에서 실시간 모니터링이 가능합니다! 🎉