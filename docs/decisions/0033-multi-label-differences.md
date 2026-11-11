# 0033. 오답 분석을 다중 라벨로 바꾸고, 컬럼 사실을 더하고, 이름을 바꾼다

- 날짜: 2026-11-11
- 상태: 채택 (0031의 결과 카테고리 부분을 대체)
- 결정자: 사용자
- AI 관여: 사용자 지시를 구현하면서 세부 설계를 Claude가 정함 (행 수 검사를 별도 라벨로 분리, 컬럼 비교 방식). 사용자가 PR 검토 후 merge를 지시함
- 관련 결정 ID: D18 후속

## 맥락
0031은 오답마다 결과 카테고리를 정확히 하나만 붙였다. 사용자는 오답이 여러 문제를 함께 가질 수 있다고 보았다. 또 잘못된 테이블과 잘못된 컬럼 사용을 알 수 있기를 원했다. 테이블은 이미 `tables_joins`로 보고되고 있었고, 컬럼은 보고되지 않았다.

## 선택지
| 안 | 장점 | 단점 |
| --- | --- | --- |
| 카테고리 하나 유지 | 단순함, 합계가 오답 수와 같음 | 한 오답의 여러 문제 중 하나만 보임 |
| 다중 라벨 (채택) | 오답의 여러 측면이 함께 보임 | 라벨 합계가 오답 수보다 커짐 |

## 결정

**1. 출력 차이(Output difference)는 다중 라벨이다.** 각 검사가 결과의 한 측면만 본다.

| 코드 | 조건 | 리포트 설명 |
| --- | --- | --- |
| `execution_failed` | 쿼리가 실패함. 이때는 이 라벨만 붙음 | 실행 실패 |
| `empty_result` | 예측 결과가 0행이고 정답은 0행이 아님. 이때 행 내용 검사는 하지 않음 | 빈 결과 |
| `column_mismatch` | 컬럼 수가 다름 (SQL이 없어 컬럼이 0개인 경우는 제외) | 컬럼 수가 다름 |
| `row_count_differs` | 서로 다른 행의 수가 다름 (EX가 집합 비교이므로 중복 행은 세지 않음) | 행 수가 다름 |
| `single_value_differs` | 둘 다 값 하나(1행 1열)인데 값이 다름 | 값 하나가 다름 |
| `row_set_differs` | 행 내용이 다름. 폭이 같으면 행 집합이 다르고, 폭이 다르면 어떤 컬럼 사영으로도 정답 행이 예측 안에서 나오지 않음 | 행 내용이 다름 |

`row_count_differs`는 새로 분리한 라벨이다. 0031의 `row_set_differs`는 행 수 차이와 내용 차이를 한데 묶고 있었는데, 다중 라벨에서는 둘을 따로 볼 수 있어야 조합에 의미가 생긴다. 예: 동점 문제 #802는 `row_count_differs + row_set_differs`.

**2. SQL 구조 차이(SQL structure difference)에 `columns`를 더한다.** 정답과 예측이 쓴 컬럼 집합(모든 절, 서브쿼리 포함)을 비교하고, 한쪽만 쓴 컬럼을 근거로 보여 준다. 컬럼 이름은 테이블 한정자를 떼고 소문자로 비교하며, SELECT 별칭은 컬럼으로 세지 않는다. 테이블 사용 차이는 기존 `tables_joins`가 보고한다.

**3. 이름을 바꾼다.**
- CLI 요약: "Wrong by category" → "Output difference", "Structural facts" → "SQL structure difference"
- `--json` 키: `output_differences`, `sql_structure_differences`
- 실행 파일: `diff.output.differences`, `diff.sql_structure.differences` (`schema_version` 3)
- 코드: `facts/result.py` → `facts/output.py`, `ResultDiff` → `OutputDiff`

## 이유
> "오답마다 하나 이상의 카테고리가 있을 수 있고, 잘못된 테이블 혹은 잘못된 컬럼 사용도 있으면 좋겠어. 이미 있나?"
>
> "그리고, "wrong by category" -> "output difference", "structural facts" -> "SQL structure difference" 이렇게 명칭 바꿔줘."

## 결과
- 라벨 수의 합은 오답 수보다 크다. CLI 요약 옆에 이 점을 적는다.
- baseline evidence 있음 오답 165건 중 61건(37%)이 출력 차이를 2개 이상 가진다. 가장 흔한 조합은 `row_count_differs + row_set_differs`(23건)와 `column_mismatch + row_set_differs`(20건)다.
- 컬럼 비교는 한정자를 떼므로, 두 테이블의 같은 이름 컬럼(예: `superhero.id`와 `hero_power.id`)은 구분하지 못한다. 스키마를 읽어 컬럼을 완전히 한정하는 방식은 로드맵에 둔다.
