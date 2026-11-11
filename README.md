# Mini NPU Simulator

`Mini NPU Simulator`는 `data.json`에 저장된 필터와 패턴을 읽어,  
각 패턴이 `Cross` 또는 `X` 중 어느 쪽에 더 가까운지 MAC(Multiply-Accumulate) 점수로 판정하는 프로그램입니다.

---

## 1. 실행 방법

### 1-1. 준비 파일
아래 파일들이 같은 폴더에 있어야 합니다.

- `main.py`
- `data.json`

### 1-2. 실행
터미널에서 아래 명령을 실행합니다.

```bash
python main.py
```

### 1-3. 메뉴 선택
실행 후 다음 메뉴가 표시됩니다.

```text
Mini NPU Simulator
1) 사용자 입력(3×3)
2) data.json 분석
입력 방식 선택 (1/2):
```

- `1` : 사용자가 직접 3×3 필터와 패턴을 입력
- `2` : `data.json`을 읽어서 자동 분석

---

## 2. 프로그램 동작 방식

이 프로그램은 두 가지 모드로 동작합니다.

### 2-1. 사용자 입력 모드
- 3×3 필터 A, 필터 B, 패턴을 직접 입력
- 패턴과 각 필터의 MAC 점수를 비교
- 더 큰 점수의 쪽으로 판정

### 2-2. JSON 분석 모드
- `data.json`을 읽어 여러 테스트 케이스를 자동 판정
- 각 케이스의 정답(`expected`)과 예측(`predicted`)을 비교
- 결과를 `result.json`으로 저장

---

## 3. 판정 기준

판정은 다음 규칙으로 수행됩니다.

- `Cross` 점수 > `X` 점수 → 예측 = `Cross`
- `X` 점수 > `Cross` 점수 → 예측 = `X`
- 두 점수가 거의 같으면 → `UNDECIDED`

정답 라벨은 `expected` 값을 기준으로 정규화합니다.

- `"+"` → `Cross`
- `"Cross"` / `"cross"` → `Cross`
- `"X"` / `"x"` → `X`

비교 기준은 `EPS = 1e-9`입니다.

---

## 4. `data.json` 형식

코드는 `patterns`와 `filters`를 여러 형태로 읽을 수 있도록 작성되어 있습니다.

### 4-1. `patterns` 예시

#### 형태 1: 리스트
```json
{
  "patterns": [
    {
      "size": 5,
      "pattern": [[...], [...], [...], [...], [...]],
      "expected": "Cross"
    }
  ]
}
```

#### 형태 2: `cases` 포함 객체
```json
{
  "patterns": {
    "cases": [
      {
        "size": 5,
        "pattern": [[...], [...], [...], [...], [...]],
        "expected": "+"
      }
    ]
  }
}
```

#### 허용 필드
- `size`
- `pattern`
- `input`
- `expected`
- `label`

---

### 4-2. `filters` 예시

#### 형태 1: size별 객체
```json
{
  "filters": {
    "5": {
      "cross": [[...], [...], [...], [...], [...]],
      "x": [[...], [...], [...], [...], [...]]
    }
  }
}
```

#### 형태 2: 리스트
```json
{
  "filters": [
    {
      "size": 5,
      "label": "Cross",
      "matrix": [[...], [...], [...], [...], [...]]
    },
    {
      "size": 5,
      "label": "X",
      "matrix": [[...], [...], [...], [...], [...]]
    }
  ]
}
```

#### 허용 라벨
- `Cross`
- `X`
- `cross`
- `x`
- `+`

---

## 5. 사용자 입력 모드

메뉴에서 `1`을 선택하면 실행됩니다.

### 동작
1. 3×3 필터 A 입력
2. 3×3 필터 B 입력
3. 3×3 패턴 입력
4. 각 입력을 다시 화면에 출력
5. 사용자 확인 후 MAC 점수 계산
6. A/B 중 더 큰 점수로 판정

### 입력 형식
각 행을 공백으로 구분하여 입력합니다.

예:
```text
1 0 1
0 1 0
1 0 1
```

### 출력 내용
- A 점수
- B 점수
- A 연산 시간(평균)
- B 연산 시간(평균)
- 판정 결과
- 연산 횟수 (`N^2`)

### 주의사항
- 이 모드는 **항상 3×3만 지원**합니다.
- 입력 확인에서 `y`, `yes`, `1`만 참으로 처리합니다.

---

## 6. 성능 측정

코드는 MAC 연산 시간을 측정합니다.

### 측정 함수
- `benchmark_mac_2d(pattern, filt, repeat=10)`
- `benchmark_mac_flat(pattern, filt, repeat=10)`

### 기본 반복 횟수
```python
BENCH_REPEAT = 10
```

### 반환값
- 평균 실행 시간(ms)
- 연산 횟수(`N^2`)

---

## 7. `result.json` 형식

JSON 분석 모드 실행 후 결과는 `result.json`에 저장됩니다.

### 저장 예시
```json
{
  "summary": {
    "total": 4,
    "pass": 3,
    "fail": 1
  },
  "results": [
    {
      "case": 1,
      "size": 5,
      "expected": "X",
      "predicted": "Cross",
      "cross_score": 0.9,
      "x_score": 0.5,
      "avg_ms": 0.0021,
      "ops": 25,
      "result": "FAIL"
    }
  ]
}
```

### summary 항목
- `total`: 전체 케이스 수
- `pass`: 통과 수
- `fail`: 실패 수

### results 항목
각 케이스별:
- `case`
- `size`
- `expected`
- `predicted`
- `cross_score`
- `x_score`
- `avg_ms`
- `ops`
- `result`

---

## 8. 예외 처리

프로그램은 다음과 같은 오류를 처리합니다.

- 파일이 없을 때
- JSON 파싱 실패
- 정사각 행렬이 아닐 때
- 크기 불일치
- 필수 키(`patterns`, `filters`) 누락
- 숫자가 아닌 입력

오류가 발생하면 콘솔에 메시지를 출력하고 종료합니다.

---

## 9. 파일 구성 예시

```text
main.py
data.json
result.json
README.md
```

---

## 10. 간단 요약

이 프로그램은 입력된 패턴과 필터를 MAC 연산으로 비교하여  
`Cross` / `X` 판정을 수행하는 Mini NPU 시뮬레이터입니다.
