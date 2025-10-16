# 🚀 ETH Session Strategy Trading Bot

고급 리스크 관리가 적용된 ETHUSDT 세션 스윕 리버설 트레이딩 봇

## 📊 전략 개요

- **타겟**: ETHUSDT 선물 (15분봉)
- **전략**: 세션 스윕 리버설 + 리퀴데이션 모멘텀
- **리스크 관리**: 포지션당 5% 리스크, 청산 확률 7%
- **레버리지**: 최대 125x (동적 조정)

## 🎯 핵심 성과

- **승률**: 60.8%
- **Profit Factor**: 2.29+
- **월 평균 거래**: 9.3개
- **최적화된 파라미터** 적용

## 🛠️ 주요 기능

### 📈 전략 구성요소
- 아시아/런던/뉴욕 세션 분석
- 스윙 고저점 기반 스윕 감지
- ATR 기반 변동성 필터
- 디스플레이스먼트 확인
- 펀딩 시간 회피

### 🛡️ 고급 리스크 관리
- 동적 레버리지 계산
- 청산 확률 기반 포지션 사이징
- 변동성 기반 리스크 조정
- 실시간 계좌 잔고 관리

## 📁 파일 구조

```
├── eth_session_strategy.py      # 메인 전략 엔진
├── advanced_risk_system.py      # 고급 리스크 관리
├── fixed_risk_management.py     # 기본 리스크 관리
├── binance_data_collector.py    # 데이터 수집기
├── requirements.txt             # 의존성 패키지
├── .env.example                # 환경변수 예시
└── data/                       # 가격 데이터
```

## 🚀 설치 및 실행

### 1. 환경 설정
```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정
`.env` 파일 생성:
```env
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET_KEY=your_secret_key_here
BINANCE_TESTNET=false
DATA_SYMBOL=ETHUSDT
DATA_INTERVAL=15m
DATA_POINTS_TARGET=500000
```

### 3. 데이터 수집
```bash
python binance_data_collector.py
```

### 4. 백테스트 실행
```bash
python eth_session_strategy.py
```

## ⚙️ 최적화된 파라미터

```python
{
    'swing_len': 5,
    'rr_percentile': 0.2956456168878421,
    'disp_mult': 1.1007752243798252,
    'sweep_wick_mult': 0.5391008387578328,
    'atr_len': 32,
    'stop_atr_mult': 0.07468310011731281,
    'target_r': 3.0721376531107074,
    'time_stop_bars': 1,
    'min_volatility_rank': 0.41615733983481445,
    'session_strength': 1.6815393680831972,
    'volume_filter': 1.2163453246372455,
    'trend_filter_len': 32
}
```

## 🔧 리스크 관리 설정

- **포지션당 리스크**: 계좌의 5%
- **청산 확률**: 7%
- **최대 레버리지**: 125x
- **유지증거금률**: 0.4%

## 📊 백테스트 결과

- **기간**: 2019-2025 (5.9년)
- **총 거래**: 659개
- **승률**: 60.8%
- **수익률**: 15,049,002%+ (이론적)

## ⚠️ 주의사항

1. **백테스트 결과는 과거 데이터 기반**이며 미래 성과를 보장하지 않습니다
2. **실제 거래 시 슬리피지, 수수료, 시장 충격** 등을 고려해야 합니다
3. **높은 레버리지는 높은 리스크**를 동반합니다
4. **충분한 테스트 후 소액으로 시작**하세요

## 🔄 CI/CD

GitHub Actions를 통한 자동 테스트 및 배포:
- 코드 품질 검사
- 백테스트 실행
- Railway 자동 배포

## 📞 지원

이슈나 질문이 있으시면 GitHub Issues를 이용해주세요.

## 📄 라이선스

MIT License

---

⚠️ **투자 경고**: 이 봇은 교육 및 연구 목적으로 제작되었습니다. 실제 투자 시 발생하는 손실에 대해 책임지지 않습니다.