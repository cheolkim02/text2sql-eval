# 결과 읽기

`eval`이 케이스마다 남기는 것은 세 가지다.

1. **판정:** 공식 규칙대로 맞았는가
2. **차이:** 틀렸다면 정답과 무엇이 다른가
3. **플래그:** 그 판정을 의심할 이유가 있는가

차이와 플래그는 모두 규칙으로 계산한다. LLM을 쓰지 않으므로 같은 입력이면 언제나 같은 결과가 나온다. 예시의 `#번호`는 저장소에 커밋된 evidence 있음 실행([examples/results](../../examples/results/README.md))의 케이스다.

## 1. 판정

| 상태 | 뜻 |
| --- | --- |
| `correct` | 예측 결과의 행 집합이 정답과 같다 |
| `incorrect` | 두 쿼리가 모두 실행됐고 행 집합이 다르다 |
| `error` | 쿼리가 실패했다(SQLite 오류, 시간 초과, 행 수 제한). 0점이다 |

EX(실행 정확도)는 `correct`의 비율이다. 행을 비교하는 규칙은 BIRD 공식 평가 스크립트와 똑같이 `set(예측 행) == set(정답 행)`이다([ADR 0022](../decisions/0022-ex-set-comparison.md)).

- 행 순서와 중복 행은 무시한다. 그래서 `ORDER BY`가 달라도 맞을 수 있다.
- 행 안의 값 순서는 따진다. `SELECT name, id`와 `SELECT id, name`은 다르다.
- 컬럼 이름은 보지 않는다.
- 값은 Python의 `==`로 비교한다. `1`과 `1.0`은 같고, `'Fly'`와 `'fly'`는 다르다.

같은 예측을 공식 스크립트로도 채점해 EX 8개 숫자가 모두 같은 것을 확인했다([기록](../../examples/results/README.md#bird-공식-스크립트와의-일치-2026-11-09)). 그래도 결과가 달라질 수 있는 경우가 두 가지 있다([ADR 0021](../decisions/0021-execution-defaults.md)).

- **시간 제한:** 공식 스크립트는 두 쿼리를 합친 시간에, 이 도구는 쿼리 하나하나에 제한(기본 30초)을 둔다. 느린 쿼리는 기계 속도에 따라 판정이 바뀔 수 있다([사례](../../examples/results/README.md#시간-제한에-민감한-케이스)).
- **쓰기 쿼리:** 이 도구는 DB를 읽기 전용으로 열기 때문에, DB를 바꾸는 예측은 실행 오류가 된다. 공식 스크립트는 DB를 쓰기 가능하게 연다.

`error`의 `side`는 실패한 쪽이다. 정답 SQL이 실패한 케이스(`side: gold`)는 데이터셋 문제이므로 차이를 계산하지 않는다.

## 2. 차이: 무엇이 다른가

정답이 아닌 케이스(오답과 예측 쪽 실행 실패)에만 차이를 붙인다([ADR 0031](../decisions/0031-error-facts-v1.md)). 차이는 두 갈래다. 한 오답에 여러 개가 붙을 수 있어서 종류별 개수의 합은 오답 수보다 크다([ADR 0033](../decisions/0033-multi-label-differences.md)).

### 출력 차이 (Output difference)

두 쿼리의 **실행 결과**를 비교한다. SQL을 파싱하지 않으므로 어떤 SQL에도 항상 계산된다.

| 코드 | 설명 | 조건 |
| --- | --- | --- |
| `execution_failed` | 실행 실패 | 쿼리가 실패했다. 이때는 이 차이만 붙는다 |
| `empty_result` | 빈 결과 | 예측은 0행, 정답은 1행 이상. 이때 행 내용은 비교하지 않는다 |
| `column_mismatch` | 컬럼 수가 다름 | 컬럼 수가 다르다. 예측 SQL이 없어 컬럼이 0개인 경우는 빼고 센다 |
| `row_count_differs` | 행 수가 다름 | 중복을 뺀 행 수가 다르다(EX가 집합 비교라서) |
| `single_value_differs` | 값 하나가 다름 | 둘 다 1행 1열인데 값이 다르다 |
| `row_set_differs` | 행 내용이 다름 | 컬럼 수가 같으면 행 집합이 다르다. 컬럼 수가 다르면 예측 컬럼을 어떻게 골라도 정답 행이 나오지 않는다 |

예:

- **#225** `empty_result`: 정답은 `bond_type = '='`, 예측은 `bond_type = ' = '`(앞뒤 공백)라서 결과가 비었다.
- **#200** `column_mismatch`: 질문은 분자 id만 물었는데, 예측이 `label` 컬럼을 하나 더 냈다.
- **#197** `single_value_differs`: 평균값 하나를 내는 질문에서 값이 달랐다.

리포트와 실행 파일에는 판단 근거가 되는 숫자도 함께 남는다. 양쪽의 컬럼 수, 중복을 뺀 행 수, 행 집합의 관계(`subset`: 예측이 정답의 일부, `superset`: 정답을 다 포함하고 더 있음, `overlap`, `disjoint`)다.

### SQL 구조 차이 (SQL structure difference)

정답·예측 **SQL을 파싱해서**(sqlglot, [ADR 0032](../decisions/0032-sqlglot.md)) 구조를 비교한다. 출력 차이가 "결과가 어떻게 다른가"라면, 구조 차이는 "SQL의 어디가 다른가"에 대한 힌트다.

| 코드 | 설명 | 조건 | 근거로 보여 주는 것 |
| --- | --- | --- | --- |
| `where_value` | WHERE 조건의 값이 다름 | 같은 컬럼, 같은 연산자의 조건인데 비교하는 값(리터럴)이 다르다 | 양쪽 조건 |
| `tables_joins` | 테이블·JOIN 구성이 다름 | 쓴 테이블의 집합이나 JOIN 수가 다르다 | 양쪽 테이블 목록과 JOIN 수 |
| `columns` | 사용한 컬럼이 다름 | 모든 절(서브쿼리 포함)에서 쓴 컬럼의 집합이 다르다 | 한쪽에만 있는 컬럼 |
| `aggregation` | 집계 함수가 다름 | 집계식(`COUNT`, `SUM`, `AVG`, `MIN`, `MAX` 등)의 집합이 다르다 | 양쪽 집계식 |
| `order_limit` | ORDER BY/LIMIT이 다름 | 바깥 쿼리의 `ORDER BY`나 `LIMIT`이 다르다 | 양쪽 절 |

예:

- **#225** `where_value`: 정답 `bond.bond_type = '='`, 예측 `bond.bond_type = ' = '`
- **#197** `aggregation`: 정답 `AVG(oxygen_count), COUNT(element)`, 예측 `AVG(oxygen_count), COUNT(atom_id)`
- **#300** `columns`: 정답에 없는 `element`를 예측이 썼다

비교하기 전에 쓰는 방식만 다른 것은 같게 맞춘다(정규화).

- 식별자(테이블·컬럼 이름)의 대소문자, 공백, 끝의 세미콜론
- 테이블 별칭: `T1.name`과 `s.name`은 별칭을 실제 테이블 이름으로 바꾼 뒤 비교한다
- 컬럼 앞의 테이블 이름: `COUNT(bond.bond_id)`와 `COUNT(bond_id)`는 같다
- `SELECT ... AS 별칭`의 별칭은 컬럼으로 세지 않는다

**문자열 값의 대소문자는 바꾸지 않는다.** `'Cryokinesis'`와 `'cryokinesis'`처럼 값이 대소문자만 다른 것이 바로 찾고 싶은 오답이기 때문이다. 조건의 순서, `IN`과 `EXISTS`, 서브쿼리와 JOIN처럼 뜻은 같고 모양이 다른 SQL은 아직 같게 보지 않는다. 그래서 정답과 같은 뜻인데도 구조 차이가 나올 수 있다.

어느 한쪽 SQL을 파싱하지 못하면 구조 차이를 계산하지 않고 그 사실(`parse_failed`)을 기록한다. 출력 차이는 그래도 계산된다.

## 3. 판정 신뢰도 플래그

BIRD 공식 규칙은 행 집합만 비교하므로, 사람이 보면 맞는 답을 틀렸다고 하거나 그 반대일 때가 있다. 플래그는 그런 케이스를 **표시만** 한다. 판정과 EX는 공식 규칙 그대로 둔다([ADR 0034](../decisions/0034-reliability-flags.md)).

| 코드 | 붙는 판정 | 조건 | 의미 |
| --- | --- | --- | --- |
| `empty_prediction_correct` | correct | 빈 예측(또는 빠진 예측)이 정답 처리됐다 | 거짓 정답 의심 |
| `gold_empty_correct` | correct | 정답 결과가 비어 있어서, 결과가 비기만 하면 정답이 된다 | 거짓 정답 의심 |
| `matches_tied_alternative_only` | incorrect | 동점 대체 정답과만 일치한다 | 거짓 오답 의심 |
| `gold_rows_with_extra_columns` | incorrect | 예측 컬럼이 더 많고, 그중 일부 컬럼만 고르면 정답 행이 그대로 나온다 | 거짓 오답 의심 |
| `gold_columns_concatenated` | incorrect | 정답은 여러 컬럼, 예측은 한 컬럼인데, 정답 각 행의 값을 같은 구분자(공백, `", "`, 없음)로 이어 붙이면 예측과 같다 | 거짓 오답 의심 |
| `tied_alternative_exists` | 모두 | BIRD가 동점 대체 정답(`--tied`)을 준 문제다 | 정보 |

예:

- **#300** `gold_rows_with_extra_columns`: 원자 id를 묻는 질문에 id와 원소를 함께 냈다.
- **#1445** `gold_columns_concatenated`: 정답은 `first_name, last_name` 두 컬럼, 예측은 `first_name || ' ' || last_name` 한 컬럼이다.
- **#736** `matches_tied_alternative_only`: "가장 지능이 낮은 영웅"이 여러 명으로 동점이고, 정답 SQL은 그중 하나만 고른다.

동점 대체 정답은 BIRD dev에 함께 들어 있는 `dev_tied_append.json`이다. 정답 SQL이 `ORDER BY ... LIMIT 1`로 동점 중 하나만 고르는 문제에 대해, 동점인 행을 모두 내는 SQL을 준다. 공식 평가 코드는 이 파일을 쓰지 않는다. 이 도구도 `--tied`로 받으면 플래그에만 쓰고 판정에는 쓰지 않는다([ADR 0024](../decisions/0024-tied-alternative-flag.md)).

저장소 예제(evidence 있음)에서는 오답 161개 중 38개(24%)에 거짓 오답 의심 플래그가 붙는다. EX를 볼 때 이 정도는 판정 규칙 때문에 틀린 것일 수 있다는 뜻이다.

## 4. HTML 리포트

`report --html`로 만든 파일을 브라우저로 연다. 인터넷 연결이 필요 없다.

- **맨 위:** 실행 정보(모델, 프롬프트 등 `--meta` 값), EX, 난이도별·DB별 EX, 출력 차이·구조 차이·플래그의 개수
- **필터:** 판정, DB, 난이도, 출력 차이, 구조 차이, 플래그. 처음에는 판정이 "오답·오류"로 골라져 있다. 플래그 필터의 "거짓 오답 의심 (모두)"는 거짓 오답 의심 플래그 3종을 한꺼번에 고른다.
- **케이스를 펼치면:** 질문과 evidence, 정답·예측 SQL(절마다 줄을 나눠 나란히), 플래그, 출력 차이와 숫자, 구조 차이와 근거, 양쪽 결과 표가 나온다. 정렬 전 SQL은 "원래 SQL"을 눌러 본다.

### 색칠 규칙

다른 곳을 빨리 찾도록 색칠한다. 색칠은 표시일 뿐이고 판정이나 차이를 바꾸지 않는다. 차이와 같은 범위(정답이 아니고 정답 SQL이 실행된 케이스)에만 칠한다([ADR 0039](../decisions/0039-html-report-scope.md)).

**SQL 절**

- 바깥 쿼리를 절 단위(WITH, SELECT, FROM+JOIN, WHERE, GROUP BY, HAVING, ORDER BY, LIMIT+OFFSET)로 나누고, 정규화한 뒤 같은 절끼리 비교한다.
- 다르거나 한쪽에만 있는 절을 양쪽에서 칠한다.
- SQLite가 무시하는 쓰는 순서는 다르다고 보지 않는다. AND로 이은 조건의 순서, `=` 양쪽의 순서, 내부 조인의 테이블 순서, `INNER JOIN`과 `JOIN`이 그렇다.
- 서브쿼리는 그것이 들어 있는 절에 속한다.
- 한쪽을 파싱하지 못했거나 바깥이 SELECT가 아니면(UNION 등) 칠하지 않는다.

**결과 행**

- 상대 결과에 없는 행을 칠한다.
- 실행 파일에는 결과의 앞 20행만 있다. 상대 결과가 20행을 넘으면, 보이지 않는 행 중에 같은 행이 있을 수 있다. 그래서 상대 결과가 모두 저장된 경우(20행 이하)에만 칠한다.
- 컬럼 수가 다르면 칠하지 않는다.

## 5. CSV로 손 분류하기

`report --csv`의 CSV는 엑셀에서 바로 열린다. 케이스마다 한 줄이고, 판정·차이·플래그가 이미 채워져 있다. 열 목록은 [CLI 레퍼런스](../reference/cli.md#report)에 있다.

마지막의 빈 `my_category`·`notes` 열은 사용자의 몫이다. 연구마다 오답 분류 체계가 다르므로, 도구는 "무엇이 다른가"만 채우고 "왜 틀렸나"는 사람이 정한다([ADR 0005](../decisions/0005-feature-priorities.md)). 예를 들어 `status`가 `incorrect`이고 `sql_structure_differences`에 `where_value`가 있는 줄을 거르면, 값을 잘못 쓴 오답부터 볼 수 있다.

분류 규칙을 파일로 정해 자동으로 붙이는 기능은 로드맵에 있다([ADR 0042](../decisions/0042-category-mapping-roadmap.md)).
