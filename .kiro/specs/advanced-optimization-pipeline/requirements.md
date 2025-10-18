# Requirements Document

## Introduction

이 기능은 기존의 느린 최적화 프로세스를 대체하여 워크포워드 분석과 몬테카를로 시뮬레이션을 결합한 고속 최적화 파이프라인을 구현합니다. 업계 표준 기법들을 활용하여 현실적으로 가장 빠르고 정확한 최적화를 제공하며, 켈리 0.5 기준의 포지션 사이징을 적용합니다.

## Requirements

### Requirement 1

**User Story:** 트레이더로서, 기존 최적화가 너무 오래 걸리므로 고속 데이터 처리 엔진을 원한다.

#### Acceptance Criteria

1. WHEN 데이터를 로드할 때 THEN 시스템은 Parquet 형식으로 저장하고 float32로 다운캐스트해야 한다
2. WHEN 지표를 계산할 때 THEN 시스템은 EMA/ATR/RSI를 사전계산하여 ndarray로 캐시해야 한다
3. WHEN 백테스팅을 실행할 때 THEN 시스템은 numpy 벡터화와 numba @njit를 사용해야 한다
4. WHEN 병렬 처리할 때 THEN 시스템은 Ray/Joblib을 사용하고 MKL_NUM_THREADS=1로 설정해야 한다

### Requirement 2

**User Story:** 트레이더로서, 명확한 성과 기준과 제약 조건을 통해 최적화 품질을 보장받고 싶다.

#### Acceptance Criteria

1. WHEN 성과를 평가할 때 THEN 시스템은 Score = 0.35·Sortino + 0.25·Calmar + 0.20·PF + 0.20·SQN − λ·MaxDD 공식을 사용해야 한다
2. WHEN 제약 조건을 확인할 때 THEN 시스템은 PF≥1.8, Sortino≥1.5, Calmar≥1.5, SQN≥2.0, MaxDD≤30%, MinTrades≥200을 만족해야 한다
3. WHEN 집계할 때 THEN 시스템은 각 구간의 메디안을 사용하고 동률이면 IQR 우선해야 한다
4. WHEN DD 패널티를 적용할 때 THEN 시스템은 λ=0.5~1.0 범위를 사용해야 한다

### Requirement 3

**User Story:** 트레이더로서, 2단계 탐색 전략을 통해 효율적인 파라미터 최적화를 원한다.

#### Acceptance Criteria

1. WHEN 초기 전역 탐색할 때 THEN 시스템은 Sobol/LHS 120점 샘플링을 사용해야 한다
2. WHEN 다중충실도를 적용할 때 THEN 시스템은 10k→30k→50k 데이터 길이로 진행해야 한다
3. WHEN ASHA 조기중단을 적용할 때 THEN 시스템은 η=3으로 하위70%→60% 순차 컷해야 한다
4. WHEN 국소 정밀 탐색할 때 THEN 시스템은 TPE/GP + EI 40스텝을 사용해야 한다
5. WHEN 최종 후보를 선별할 때 THEN 시스템은 Top-12를 풀 데이터로 평가하여 Top-5를 추려야 한다

### Requirement 4

**User Story:** 트레이더로서, 시계열 검증을 통해 데이터 누수 없는 신뢰할 수 있는 결과를 원한다.

#### Acceptance Criteria

1. WHEN 내부 검증할 때 THEN 시스템은 Purged K-Fold=5 + Embargo=평균보유기간×2를 사용해야 한다
2. WHEN fold별 평가할 때 THEN 시스템은 Score 메디안 − DD 패널티로 랭크해야 한다
3. WHEN 승급 기준을 적용할 때 THEN 시스템은 Top-3 파라미터만 다음 단계로 승급시켜야 한다

### Requirement 5

**User Story:** 트레이더로서, 워크포워드 분석을 통해 실전과 동일한 조건에서 검증받고 싶다.

#### Acceptance Criteria

1. WHEN 슬라이스를 설계할 때 THEN 시스템은 Train 9개월 / Test 2개월, 총 8슬라이스 롤링을 사용해야 한다
2. WHEN 각 슬라이스를 처리할 때 THEN 시스템은 Train에서 최적 파라를 도출하고 Test(OOS)에서 평가해야 한다
3. WHEN OOS 합격선을 적용할 때 THEN 시스템은 PF_OOS≥1.8, Sortino_OOS≥1.5, Calmar_OOS≥1.5, MaxDD_OOS≤30%, MinTrades_OOS≥200을 만족해야 한다
4. WHEN 최종 선택할 때 THEN 시스템은 OOS 메디안 기준으로 선택해야 한다

### Requirement 6

**User Story:** 트레이더로서, 몬테카를로 시뮬레이션을 통해 견고성과 민감도를 검증받고 싶다.

#### Acceptance Criteria

1. WHEN 부트스트랩을 적용할 때 THEN 시스템은 Block Bootstrap(블록길이=ACF 반감기)을 사용해야 한다
2. WHEN 트레이드 리샘플링할 때 THEN 시스템은 승/패·익절/손절 구조를 보존해야 한다
3. WHEN 실행 노이즈를 추가할 때 THEN 시스템은 슬리피지 ±σ, 스프레드 확장 이벤트를 적용해야 한다
4. WHEN 파라미터 섭동을 적용할 때 THEN 시스템은 최종 파라 ±10%를 사용해야 한다
5. WHEN 시뮬레이션을 실행할 때 THEN 시스템은 1,000–2,000회 반복해야 한다
6. WHEN 합격선을 적용할 때 THEN 시스템은 PF_p5≥1.5, Sortino_p5≥1.2, Calmar_p5≥1.2, MaxDD_p95≤30%, SQN_median≥3.0을 만족해야 한다

### Requirement 7

**User Story:** 트레이더로서, 다중가설 보정을 통해 통계적으로 유의한 결과만 채택하고 싶다.

#### Acceptance Criteria

1. WHEN 보정을 적용할 때 THEN 시스템은 Deflated Sortino(Bailey)로 테스트·후보 수를 보정해야 한다
2. WHEN 우연성을 검정할 때 THEN 시스템은 White's Reality Check / SPA를 사용해야 한다
3. WHEN 최종 선택할 때 THEN 시스템은 0.6·(MC p5) + 0.4·(WFO-OOS median) 가중합이 최대인 Top-1~2 시스템을 선택해야 한다

### Requirement 8

**User Story:** 트레이더로서, 켈리 0.5 기준의 포지션 사이징을 통해 안전한 자금 관리를 원한다.

#### Acceptance Criteria

1. WHEN 계좌 잔고가 1000USDT 미만일 때 THEN 시스템은 최소 주문금액 20USDT를 사용해야 한다
2. WHEN 계좌 잔고가 1000USDT 이상일 때 THEN 시스템은 켈리 0.5 기준으로 포지션을 계산해야 한다
3. WHEN 켈리 계산 결과가 20USDT 미만일 때 THEN 시스템은 최소 주문금액 20USDT를 사용해야 한다
4. WHEN DD가 발생할 때 THEN 시스템은 DD 10%마다 베팅을 20% 축소해야 한다

### Requirement 9

**User Story:** 트레이더로서, 실전 운영을 위한 안전장치와 모니터링을 원한다.

#### Acceptance Criteria

1. WHEN 일중 손실한도를 설정할 때 THEN 시스템은 연속손실 n회 시 자동 정지해야 한다
2. WHEN 유동성을 필터링할 때 THEN 시스템은 스프레드·체결량을 확인해야 한다
3. WHEN 비용 스트레스 테스트할 때 THEN 시스템은 비용 2× 조건에서 재검증해야 한다
4. WHEN 실시간 처리할 때 THEN 시스템은 지연 < 바 주기 20%를 유지해야 한다
5. WHEN 장애가 발생할 때 THEN 시스템은 안전축소/청산 플래그를 활성화해야 한다