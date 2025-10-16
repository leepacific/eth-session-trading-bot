# 🚀 자동 최적화 시스템 가이드

## 🎯 시스템 개요

### 📊 최적화 목표
- **Profit Factor**: ≥ 2.5 (목표: 3.5+)
- **Sortino Ratio**: ≥ 2.0 (목표: 3.0+)
- **Win Rate**: 45-65% (목표: 55%)
- **Max Drawdown**: ≤ 20% (목표: ≤15%)
- **SQN**: ≥ 3.0 (목표: 4.0+)
- **Calmar Ratio**: ≥ 3.0 (목표: 4.0+)

### ⏰ 실행 스케줄
- **시간**: 매주 일요일 14:00 KST
- **소요시간**: 약 90분
- **완료시간**: 15:30 KST (일요일 오후)

## 🛠️ 설치 및 설정

### 1. Railway 환경변수 추가
```env
ENABLE_AUTO_OPTIMIZATION=true
OPTIMIZATION_SCHEDULE=weekly
RESOURCE_LIMIT_CPU=0.7
RESOURCE_LIMIT_MEMORY=0.7
OPTIMIZATION_TIMEZONE=Asia/Seoul
```

### 2. 필요한 라이브러리 (자동 설치됨)
- `optuna`: 베이지안 최적화
- `apscheduler`: 스케줄링
- `pytz`: 시간대 처리
- `psutil`: 시스템 리소스 모니터링

## 🔄 최적화 프로세스

### 3단계 다중해상도 최적화:

#### 1단계: 러프 스크리닝 (20분)
```
데이터: 50,000 포인트 (샘플링)
방법: Sobol 시퀀스 100 샘플
목표: 상위 30% 후보 선별
```

#### 2단계: 베이지안 최적화 (50분)
```
데이터: 100,000 포인트
방법: TPE + ASHA 조기중단
반복: 200 스텝
목표: 상위 10개 후보 선별
```

#### 3단계: 최종 검증 (20분)
```
데이터: 전체 206,319 포인트
방법: Walk-Forward 검증
후보: 상위 5개
목표: 최종 파라미터 확정
```

## 📊 최적화 파라미터

### 12개 핵심 파라미터:
```python
{
    'swing_len': [3, 7],           # 스윙 길이
    'rr_percentile': [0.1, 0.8],  # 변동성 필터
    'disp_mult': [0.8, 2.0],      # 디스플레이스먼트
    'sweep_wick_mult': [0.3, 0.8], # 스윕 꼬리
    'atr_len': [10, 50],          # ATR 길이
    'stop_atr_mult': [0.05, 0.15], # 스톱 배수
    'target_r': [1.5, 4.0],       # 목표 R배수
    'time_stop_bars': [1, 8],     # 시간 스톱
    'min_volatility_rank': [0.2, 0.7],
    'session_strength': [1.0, 2.5],
    'volume_filter': [1.0, 2.0],
    'trend_filter_len': [10, 50]
}
```

## 🚀 실행 방법

### 자동 실행 (권장)
Railway에 배포하면 자동으로 매주 일요일 14:00에 실행됩니다.

### 수동 실행 (테스트용)
```bash
# 즉시 최적화 실행
python auto_optimizer.py --now

# 스케줄러 시작 (대기 모드)
python auto_optimizer.py
```

## 📋 결과 파일

### 자동 생성되는 파일들:
1. **`optimization_result_YYYYMMDD_HHMMSS.json`**
   - 전체 최적화 결과
   - 각 단계별 성과
   - 시스템 정보

2. **`update_params_YYYYMMDD_HHMMSS.py`**
   - 파라미터 업데이트 스크립트
   - 즉시 적용 가능

### 결과 예시:
```json
{
  "timestamp": "20251015_180000",
  "duration_minutes": 87.5,
  "best_parameters": {
    "swing_len": 5,
    "rr_percentile": 0.295,
    "disp_mult": 1.101,
    "sweep_wick_mult": 0.539,
    "atr_len": 32,
    "stop_atr_mult": 0.075,
    "target_r": 3.072,
    "time_stop_bars": 1
  },
  "stage_results": {
    "stage1": {"best_score": 0.85},
    "stage2": {"best_score": 0.92},
    "stage3": {"best_score": 0.94}
  }
}
```

## 🛡️ 리소스 관리

### Railway 리소스 제한 (70%):
- **CPU**: 최대 70% 사용
- **메모리**: 최대 70% 사용
- **배치 크기**: 메모리 기반 자동 조정
- **워커 수**: CPU 코어 수의 70%

### 모니터링:
```python
# 실시간 리소스 사용률 확인
import psutil

print(f"CPU: {psutil.cpu_percent()}%")
print(f"메모리: {psutil.virtual_memory().percent}%")
```

## ⚠️ 주의사항

### 1. 시스템 안정성
- Railway 무료 플랜: 월 500시간 제한
- 최적화 1회당 약 1.5시간 소요
- 월 4회 실행 = 6시간 사용

### 2. 과최적화 방지
- Walk-Forward 검증
- Out-of-Sample 테스트
- 파라미터 민감도 분석
- 제약 조건 강제 적용

### 3. 오류 처리
- 메모리 부족 시 배치 크기 자동 감소
- CPU 과부하 시 워커 수 자동 조정
- 네트워크 오류 시 재시도 로직

## 📊 성과 모니터링

### 주간 리포트 내용:
1. **최적화 전후 비교**
2. **핵심 지표 변화**
3. **파라미터 변경 사항**
4. **시스템 리소스 사용률**
5. **다음 주 예상 성과**

### 알림 시스템:
- 최적화 완료 시 결과 요약
- 오류 발생 시 알림
- 성과 개선/악화 시 경고

## 🔧 문제 해결

### 일반적인 문제들:

#### 1. 메모리 부족
```
증상: "MemoryError" 또는 프로세스 종료
해결: 배치 크기 자동 감소, 데이터 샘플링 증가
```

#### 2. 시간 초과
```
증상: 90분 내 완료되지 않음
해결: 샘플 수 감소, 조기 중단 임계값 조정
```

#### 3. 최적화 실패
```
증상: 모든 시도가 제약 조건 위반
해결: 제약 조건 완화, 파라미터 범위 조정
```

## 📈 예상 개선 효과

### 현재 vs 최적화 후:
```
현재 성과:
- Profit Factor: 3.03
- Win Rate: 60.8%
- Sortino Ratio: ~1.8

예상 최적화 후:
- Profit Factor: 3.5-4.0
- Win Rate: 55-65%
- Sortino Ratio: 2.5-3.0
- Max DD: 15% 이하
- SQN: 4.0+
```

## 🎯 성공 지표

### 최적화 성공 기준:
- [ ] 복합 점수 0.9 이상
- [ ] 모든 제약 조건 만족
- [ ] 3단계 모두 완료
- [ ] 90분 내 완료
- [ ] 파라미터 안정성 확인

---

## 🚀 시작하기

1. **Railway 환경변수 설정**
2. **코드 배포 및 확인**
3. **첫 실행 대기** (다음 일요일 18:00)
4. **결과 확인 및 분석**
5. **지속적 모니터링**

매주 자동으로 전략이 개선되어 더 나은 성과를 기대할 수 있습니다! 🎉