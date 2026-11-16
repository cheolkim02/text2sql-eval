# 0034. 판정 신뢰도 플래그는 6개로 한다

- 날짜: 2026-11-11
- 상태: 채택 (0012의 "필수 플래그 2개"를 대체)
- 결정자: 사용자
- AI 관여: baseline 결과로 후보 8개의 건수를 세고 추천 (Claude 추천: 아래 6개, 채택 여부: 예)
- 관련 결정 ID: D19

## 맥락
플래그는 판정을 바꾸지 않고, 공식 EX 규칙이 놓치는 경우를 "의심"으로 표시한다(0023, 0024). 0012에서 필수로 정한 2개(정답 결과가 빈 집합, 정답 결과가 값 하나)는 bird-mini에서 각각 0건, 247건(57%)이라 그대로는 쓸모가 적었다(2026-11-07 개발 기록). 2026-11-11 baseline 두 실행으로 후보를 다시 셌다.

## 선택지
| 후보 | evidence 있음 | evidence 없음 | 판단 |
| --- | --- | --- | --- |
| `empty_prediction_correct` (0023) | 0 | 0 | 유지 |
| `tied_alternative_exists` (0024) | 13 | 13 | 유지 |
| `matches_tied_alternative_only` (0024) | 5 | 1 | 유지 |
| `gold_rows_with_extra_columns` | 25 | 20 | 추가 |
| `gold_columns_concatenated` | 8 | 2 | 추가 |
| `gold_empty_correct` | 0 | 0 | 추가 |
| `superset_rows` (정답 행 전부 + 더 많은 행) | 8 | 5 | 제외 |
| `single_value_coincidence` (값 하나짜리 정답인데 구조가 다름) | 57/171 | 35/104 | 제외 |

## 결정
플래그는 6개다.

| 코드 | 붙는 판정 | 조건 | 의미 |
| --- | --- | --- | --- |
| `empty_prediction_correct` | correct | 빈 예측(또는 누락)이 정답 처리됨 | 거짓 정답 의심 |
| `gold_empty_correct` | correct | 정답 결과가 빈 집합이고, 예측 SQL이 있음 | 거짓 정답 의심 (결과가 비기만 하면 정답) |
| `matches_tied_alternative_only` | incorrect | 동점 대체 정답과만 일치 | 거짓 오답 의심 |
| `gold_rows_with_extra_columns` | incorrect | 예측 컬럼이 더 많고, 어떤 컬럼 사영으로 정답 행 집합이 그대로 나옴 | 거짓 오답 의심 |
| `gold_columns_concatenated` | incorrect | 정답은 여러 컬럼, 예측은 한 컬럼이고, 정답 각 행의 값을 같은 구분자(공백, `", "`, 없음)로 이어 붙이면 예측 값 집합과 같음 | 거짓 오답 의심 |
| `tied_alternative_exists` | 모두 | 동점 대체 정답이 있는 문제 | 정보 |

## 이유
추천안을 채택했다.

보충: 제외 이유는 다음과 같다.
- `superset_rows`: 동점 때문인 경우는 `matches_tied_alternative_only`가 이미 잡는다. 나머지는 대부분 필터나 LIMIT이 빠진 진짜 오답이다.
- `single_value_coincidence`: 지금 정규화로는 같은 뜻의 다른 SQL과 우연히 맞은 SQL을 구분할 수 없어, 대부분 가짜 경보가 된다.

## 결과
- 거짓 오답 의심 플래그 3개는 "공식 규칙으로는 틀렸지만 사람이 보면 맞을 수 있는" 오답을 HTML 리포트에서 따로 모아 보여 주는 근거가 된다.
- `single_value_coincidence`는 정규화가 강해진 뒤(로드맵)에 다시 본다.
