# 실측 결과: gpt-4o-mini 단일 프롬프트 baseline

`examples/bird-mini`(BIRD dev, 432문제)에서 같은 모델과 같은 프롬프트로 두 번 예측한 결과다. 두 실행의 차이는 BIRD의 `evidence`를 프롬프트에 넣었는지 하나뿐이다([ADR 0028](../../docs/decisions/0028-baseline-evidence-ablation.md)).

## 결과

| 설정 | EX | simple | moderate | challenging | correct | incorrect | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| evidence 있음 | **61.81%** | 68.22% | 54.62% | 47.27% | 267 | 161 | 4 |
| evidence 없음 | **37.50%** | 43.80% | 27.73% | 29.09% | 162 | 261 | 9 |

판정 신뢰도 플래그는 판정을 바꾸지 않고, 공식 규칙이 놓칠 수 있는 경우를 표시한다([ADR 0034](../../docs/decisions/0034-reliability-flags.md)).

| 플래그 | 의미 | evidence 있음 | evidence 없음 |
| --- | --- | --- | --- |
| `gold_rows_with_extra_columns` | 정답 행을 그대로 포함하고 컬럼만 더 있음 (거짓 오답 의심) | 25 | 20 |
| `gold_columns_concatenated` | 정답의 여러 컬럼을 한 문자열로 이어 붙임 (거짓 오답 의심) | 8 | 2 |
| `matches_tied_alternative_only` | 동점 대체 정답과만 일치 (거짓 오답 의심) | 5 (736, 802, 810, 832, 1365) | 1 (810) |
| `empty_prediction_correct` | 빈 예측이 정답 처리됨 (거짓 정답 의심) | 0 | 0 |
| `gold_empty_correct` | 정답 결과가 비어, 결과가 비기만 하면 정답 처리됨 (거짓 정답 의심) | 0 | 0 |
| `tied_alternative_exists` | 동점 대체 정답이 있는 문제 (정보) | 13 | 13 |

evidence 있음 설정의 오답 161개 중 38개(24%)에 거짓 오답 의심 플래그가 붙는다. 공식 규칙으로는 오답이지만, 사람이 보면 맞다고 할 수 있는 답이다. 예: #300은 원자 id에 원소 컬럼을 덧붙였고, #1445는 이름과 성을 한 컬럼으로 이어 붙였다.

## 오답 분석 (ADR 0031, 0033)

오답에는 출력 차이(실행 결과 비교)와 SQL 구조 차이(정답·예측 SQL 비교)가 붙는다. 둘 다 한 오답에 여러 개 붙을 수 있어서, 합계가 오답 수보다 크다. 정답 케이스와 정답 SQL 자체가 실패한 케이스에는 붙지 않는다. 숫자는 `text2sql-eval eval`의 요약 출력이다.

| 출력 차이 (Output difference) | evidence 있음 | evidence 없음 |
| --- | --- | --- |
| `column_mismatch` (컬럼 수가 다름) | 62 | 78 |
| `row_set_differs` (행 내용이 다름) | 58 | 46 |
| `single_value_differs` (값 하나가 다름) | 44 | 94 |
| `empty_result` (빈 결과) | 34 | 100 |
| `row_count_differs` (행 수가 다름) | 31 | 26 |
| `execution_failed` (실행 실패) | 4 | 9 |

| SQL 구조 차이 (SQL structure difference) | evidence 있음 | evidence 없음 |
| --- | --- | --- |
| `columns` (사용한 컬럼이 다름) | 79 | 155 |
| `tables_joins` (테이블·JOIN 구성이 다름) | 72 | 130 |
| `aggregation` (집계 함수가 다름) | 66 | 121 |
| `where_value` (WHERE 조건의 값이 다름) | 25 | 132 |
| `order_limit` (ORDER BY/LIMIT이 다름) | 23 | 40 |

- evidence 있음 오답 165건 중 61건(37%)이 출력 차이를 2개 이상 가진다. 가장 흔한 조합은 `row_count_differs + row_set_differs`(23건)와 `column_mismatch + row_set_differs`(20건)다.
- evidence를 빼면 `empty_result`가 34건에서 100건으로, `where_value`가 25건에서 132건으로 늘어난다. evidence는 주로 WHERE에 들어갈 값(철자, 대소문자, 코드값)을 알려 주므로, 없으면 모델이 값을 틀리고 결과가 비는 경우가 늘어난다.
- 오답 수(165, 270)가 incorrect 판정 수(161, 261)보다 큰 이유는 예측 SQL이 실패한 `error` 판정(4, 9)도 오답 분석 대상이기 때문이다.

## 두 실행 비교 (`compare`)

evidence 없음을 기준(base)으로, evidence 있음(head)과 케이스 단위로 비교한 결과다.

```text
$ text2sql-eval compare examples/results/gpt-4o-mini-no-evidence.run.json \
    examples/results/gpt-4o-mini-evidence.run.json
Comparing examples/results/gpt-4o-mini-no-evidence.run.json -> examples/results/gpt-4o-mini-evidence.run.json (432 common cases)
EX: 37.5% -> 61.8% (+24.3 pp)
Both correct 144 | Fixed 123 | Regressed 18 | Both wrong 147
By difficulty: challenging 29.1% -> 47.3%, moderate 27.7% -> 54.6%, simple 43.8% -> 68.2%
By database: student_club 43.0% -> 57.0%, superhero 57.4% -> 79.8%, toxicology 13.8% -> 51.0%
Output difference: empty_result 100 -> 34, single_value_differs 94 -> 44, column_mismatch 78 -> 62, row_set_differs 46 -> 58, row_count_differs 26 -> 31, execution_failed 9 -> 4
SQL structure difference: columns 155 -> 79, where_value 132 -> 25, tables_joins 130 -> 72, aggregation 121 -> 66, order_limit 40 -> 23
```

- evidence를 넣자 123건이 맞게 바뀌었고(Fixed), 18건은 오히려 틀리게 바뀌었다(Regressed).
- `--csv`를 주면 케이스마다 한 줄씩(변화, 양쪽 판정, 출력 차이, 질문, 정답·예측 SQL) 엑셀용 CSV로 쓴다. 뒤집힌 케이스만 골라 보기 쉽다.

## BIRD 공식 스크립트와의 일치 (2026-11-09)

같은 예측을 BIRD 공식 평가 스크립트로도 채점했다. 스크립트는 AlibabaResearch/DAMO-ConvAI의 `bird/llm/src/evaluation.py`이고, 수정하지 않고 그대로 실행했다(`--meta_time_out 30`, `--num_cpus 8`). 공식 스크립트는 DB를 쓰기 가능하게 열기 때문에 DB 복사본에서 돌렸다.

| 설정 | 공식 스크립트 (simple / moderate / challenging / total) | text2sql-eval |
| --- | --- | --- |
| evidence 있음 | 68.22 / 54.62 / 47.27 / 61.81 | 68.22 / 54.62 / 47.27 / 61.81 |
| evidence 없음 | 43.80 / 27.73 / 29.09 / 37.50 | 43.80 / 27.73 / 29.09 / 37.50 |

8개 숫자가 모두 소수점 둘째 자리까지 같다.

## 시간 제한에 민감한 케이스

판정이 기계 속도에 따라 달라질 수 있는 사례를 숨기지 않고 적는다([ADR 0021](../../docs/decisions/0021-execution-defaults.md)).

- **evidence 있음 211번:** 예측 쿼리가 180초에도 끝나지 않는다(중첩 서브쿼리 조인). 30초 제한에서 시간 초과로 판정된다. 경계에서 먼 사례라 판정이 흔들리지 않는다.
- **evidence 없음 247번:** 예측 쿼리가 약 18초 걸려 끝나고, 오답으로 판정된다. 기계가 약 1.6배 느리면 30초를 넘어 시간 초과로 바뀔 수 있다. 이 경우에도 점수(0점)는 같다.
- **evidence 없음 281번:** 약 5초 걸린다.

실제로 PR #8의 CI에서 GitHub Actions 서버가 247번을 30초 안에 끝내지 못해 시간 초과로 판정했다. 그래서 재현성 테스트(`tests/test_results.py`)는 이 세 케이스를 다시 실행하지 않는다. 나머지 429개 케이스의 판정과 플래그가 커밋된 실행 파일과 똑같은지만 검사한다. 세 케이스의 기록된 판정은 별도 테스트로 고정한다.

## 생성 정보

| 항목 | 값 |
| --- | --- |
| 모델 | `gpt-4o-mini` (응답 스냅샷 `gpt-4o-mini-2024-07-18`, 2027-01-14 종료 예정, [ADR 0030](../../docs/decisions/0030-baseline-model-gpt-4o-mini.md)) |
| 파라미터 | `temperature=0`, `seed=0`, `max_tokens=512` |
| 생성일 | 2026-11-09 |
| 토큰과 비용 | evidence 있음: 입력 206,926 / 출력 20,584 (약 $0.043). evidence 없음: 입력 195,792 / 출력 21,823 (약 $0.043). 2026-11-09 가격 기준 |
| API 실패 | 0건 |

`temperature=0`과 `seed`를 줘도 OpenAI 응답은 완전히 같다고 보장되지 않는다. 그래서 예측 파일을 커밋해 두었고, 판정은 이 파일에서 언제든 같게 재현된다.

## 파일

| 파일 | 내용 |
| --- | --- |
| `gpt-4o-mini-evidence.jsonl` | 예측 (evidence 있음). `meta`에 스냅샷, 토큰 수, 지연 시간 |
| `gpt-4o-mini-no-evidence.jsonl` | 예측 (evidence 없음) |
| `gpt-4o-mini-evidence.run.json` | `text2sql-eval eval` 실행 파일 (`schema_version` 3, 오답 분석 포함) |
| `gpt-4o-mini-no-evidence.run.json` | 같은 형식 |

## 다시 만들기

API 키 없이 판정만 다시 하려면 아래 명령을 쓴다.

```sh
uv run text2sql-eval eval \
  --dataset examples/bird-mini/dev.json \
  --db-dir examples/bird-mini/dev_databases \
  --pred examples/results/gpt-4o-mini-evidence.jsonl \
  --tied examples/bird-mini/dev_tied_append.json \
  --meta model=gpt-4o-mini-2024-07-18 --meta prompt=single-prompt-v1 \
  --meta evidence=yes --meta generated=2026-11-09 \
  --out examples/results/gpt-4o-mini-evidence.run.json
```

예측까지 다시 만드는 방법은 [examples/baseline/README.md](../baseline/README.md)에 있다.
