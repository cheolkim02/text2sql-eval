# CLI 레퍼런스

`text2sql-eval`은 명령 세 개로 이루어진다.

| 명령 | 하는 일 | 입력 | 출력 |
| --- | --- | --- | --- |
| [`eval`](#eval) | 정답·예측 SQL을 실행해 EX를 판정하고, 오답의 차이와 판정 신뢰도 플래그를 기록한다 | 데이터셋, DB 폴더, 예측 파일 | [실행 파일](run-file.md)(JSON) |
| [`report`](#report) | 실행 파일 하나를 HTML 리포트와 CSV로 만든다 | 실행 파일 | HTML, CSV |
| [`compare`](#compare) | 두 실행 파일을 케이스 단위로 비교한다 | 실행 파일 2개 | 터미널 요약, CSV |

`text2sql-eval --version`은 버전을, `text2sql-eval <명령> --help`는 옵션과 예시를 출력한다. 같은 일을 Python에서 하려면 [API 레퍼런스](api.md)를 본다.

## 종료 코드

| 코드 | 뜻 | 예 |
| --- | --- | --- |
| 0 | 성공 | 판정 완료, 리포트 작성, 비교 완료 |
| 1 | 검사 실패 | `compare --max-drop`의 기준보다 EX가 더 떨어짐 |
| 2 | 사용법·입력 오류 | 잘못된 옵션, 파일 없음, 형식 오류, 데이터셋과 맞지 않는 `id` |
| 3 | 실행 환경 오류 | 출력 파일을 쓸 수 없음(권한, 경로가 폴더임) |
| 130 | 사용자 중단 | Ctrl-C |

오류는 표준 오류(stderr)에 두 줄로 나온다. 첫 줄은 어느 파일의 어디가 무엇이 잘못됐는지, 둘째 줄(`hint:`)은 고치는 방법이다.

```text
error: p.jsonl, line 2: missing field 'sql'
  hint: each line should look like {"id": 718, "sql": "SELECT ..."}
```

결과를 `| head`처럼 중간에 끊어 읽어도 오류를 내지 않는다. 이때도 `compare --max-drop` 실패의 종료 코드 1은 유지된다.

## eval

```text
text2sql-eval eval --dataset DATASET --db-dir DB_DIR --pred PRED --out OUT
                   [--pred-format {text,jsonl}] [--allow-missing] [--tied TIED]
                   [--timeout TIMEOUT] [--max-rows MAX_ROWS] [--workers WORKERS]
                   [--meta KEY=VALUE] [--json]
```

| 옵션 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `--dataset DATASET` | 예 | | BIRD 형식 문제 파일. 객체의 JSON 배열이고, 각 객체에 `question_id`(정수), `db_id`, `question`, `evidence`, `SQL`이 있어야 한다. `difficulty`는 있으면 쓴다 |
| `--db-dir DB_DIR` | 예 | | DB 폴더. 각 DB는 `<db-dir>/<db_id>/<db_id>.sqlite`에 있어야 한다(BIRD 구조) |
| `--pred PRED` | 예 | | 예측 파일. 형식은 [예측 파일 가이드](../guides/prediction-format.md) |
| `--out OUT` | 예 | | 쓸 실행 파일. 상위 폴더가 없으면 만든다 |
| `--pred-format {text,jsonl}` | | 확장자로 판별 | `.txt`는 `text`, `.jsonl`은 `jsonl`로 읽는다. 다른 확장자면 이 옵션으로 정한다 |
| `--allow-missing` | | 끔 | JSONL 전용. 줄이 없는 케이스를 빈 예측으로 판정한다. 없으면 빠진 케이스가 하나라도 있을 때 입력 오류로 멈춘다 |
| `--tied TIED` | | 없음 | BIRD의 동점 대체 정답 파일(`dev_tied_append.json`). 판정에는 쓰지 않고 플래그에만 쓴다 |
| `--timeout TIMEOUT` | | `30` | 쿼리 하나에 허용하는 초. 넘으면 `timeout` 실패로 기록한다 |
| `--max-rows MAX_ROWS` | | 1,000,000 | 결과 행이 이보다 많으면 `row_limit` 실패로 기록한다([ADR 0051](../decisions/0051-default-row-limit.md)) |
| `--workers WORKERS` | | `min(8, CPU 수)` | 동시에 실행할 쿼리 수 |
| `--meta KEY=VALUE` | | 없음 | 실행에 대한 사실(모델, 프롬프트 버전 등)을 실행 파일에 기록한다. 여러 번 줄 수 있다. 첫 `=`에서 나누므로 `note=a=b`의 값은 `a=b`다 |
| `--json` | | 끔 | 요약을 사람이 읽는 글 대신 JSON 한 줄로 출력한다 |

DB는 읽기 전용으로 열기 때문에 예측 SQL이 DB를 바꿀 수 없다. 판정 규칙은 [결과 읽기 가이드](../guides/reading-results.md)에 있다.

출력 예(저장소의 예제 데이터, `--tied`와 `--meta`를 준 경우):

```text
$ text2sql-eval eval --dataset examples/bird-mini/dev.json \
    --db-dir examples/bird-mini/dev_databases \
    --pred examples/results/gpt-4o-mini-evidence.jsonl \
    --tied examples/bird-mini/dev_tied_append.json \
    --meta model=gpt-4o-mini-2024-07-18 --out runs/evidence.json
Evaluated 432 cases: EX 61.8% (267 correct, 161 incorrect, 4 errors)
Output difference: 62 column_mismatch, 58 row_set_differs, 44 single_value_differs, 34 empty_result, 31 row_count_differs, 4 execution_failed
SQL structure difference: 79 columns, 72 tables_joins, 66 aggregation, 23 order_limit, 22 where_value
Flags: 8 gold_columns_concatenated, 25 gold_rows_with_extra_columns, 5 matches_tied_alternative_only, 13 tied_alternative_exists
Run file: runs/evidence.json
```

- 차이와 플래그는 종류별 개수다. 한 오답에 여러 개가 붙을 수 있어 합계가 오답 수보다 클 수 있다.
- 빠진 예측이나 빈 예측이 있으면 `Predictions: 3 missing, 1 empty (judged as empty SQL)` 같은 줄이 더 나온다.
- 이 예에서 30초 넘게 걸리는 이유는 끝나지 않는 예측 하나(211번)가 시간 제한까지 기다리기 때문이다.

`--json`을 주면 다음 키를 가진 JSON을 출력한다.

| 키 | 값 |
| --- | --- |
| `run_file` | 쓴 실행 파일 경로 |
| `total`, `correct`, `incorrect`, `error` | 케이스 수 |
| `ex` | EX (0~1) |
| `missing_predictions`, `empty_predictions` | 빠진 예측, 빈 예측의 수 |
| `flags`, `output_differences`, `sql_structure_differences` | 종류별 개수. 0인 종류는 없다 |

## report

```text
text2sql-eval report RUN [--html HTML] [--csv CSV]
```

| 옵션 | 설명 |
| --- | --- |
| `RUN` | `eval`이 쓴 실행 파일 |
| `--html HTML` | HTML 리포트를 이 파일에 쓴다 |
| `--csv CSV` | 케이스마다 한 줄인 CSV를 이 파일에 쓴다 |

`--html`과 `--csv` 중 하나는 꼭 줘야 한다. 둘 다 없으면 사용법 오류(종료 코드 2)다.

```text
$ text2sql-eval report runs/evidence.json --html runs/evidence.html --csv runs/evidence.csv
Report of runs/evidence.json: 432 cases, EX 61.8%
HTML: runs/evidence.html
CSV: runs/evidence.csv
```

- **HTML:** 파일 하나로, 인터넷 없이 브라우저에서 열린다. 요약, 필터가 있는 케이스 목록, 케이스별 정답·예측 SQL과 결과 비교가 있다. 읽는 법은 [결과 읽기 가이드](../guides/reading-results.md)에 있다.
- **CSV:** 엑셀에서 한글이 깨지지 않도록 UTF-8 BOM으로 쓴다. 셀이 `=`, `+`, `-`, `@` 등으로 시작하면 엑셀이 수식으로 실행하지 않도록 앞에 `'`를 붙인다([ADR 0040](../decisions/0040-csv-formula-escaping.md)). 열은 다음과 같다.

| 열 | 내용 |
| --- | --- |
| `id`, `db_id`, `difficulty` | 케이스 정보 |
| `status` | `correct`, `incorrect`, `error` |
| `prediction` | `given`(예측 있음), `empty`(빈 SQL), `missing`(예측 없음) |
| `output_differences` | 출력 차이 코드, `;`로 구분 |
| `sql_structure_differences` | SQL 구조 차이 코드, `;`로 구분 |
| `flags` | 판정 신뢰도 플래그 코드, `;`로 구분 |
| `question`, `evidence`, `gold_sql`, `pred_sql` | 원문 |
| `error` | 실행 실패의 내용. 예: `pred timeout: did not finish within 30 s` |
| `my_category`, `notes` | 빈 열. 사용자가 손으로 분류하고 메모한다 |

## compare

```text
text2sql-eval compare BASE HEAD [--max-drop PP] [--csv CSV] [--json]
```

| 옵션 | 설명 |
| --- | --- |
| `BASE` | 기준 실행 파일(예: 바꾸기 전) |
| `HEAD` | 비교할 실행 파일(예: 바꾼 뒤) |
| `--max-drop PP` | EX가 `PP` %p보다 많이 떨어지면 종료 코드 1로 끝난다. 주지 않으면 떨어져도 실패하지 않는다([ADR 0036](../decisions/0036-compare-gate-opt-in.md)) |
| `--csv CSV` | 두 실행에 모두 있는 케이스마다 한 줄인 CSV를 쓴다 |
| `--json` | 요약을 JSON 한 줄로 출력한다 |

두 실행 모두에 있는 케이스 `id`만 비교한다. 데이터셋 파일의 SHA-256이 다르거나 한쪽에만 있는 케이스가 있으면 요약 맨 앞에 `WARNING:` 줄이 나온다. 공통 케이스가 하나도 없으면 입력 오류다([ADR 0037](../decisions/0037-compare-dataset-mismatch.md)).

```text
$ text2sql-eval compare examples/results/gpt-4o-mini-no-evidence.run.json \
    examples/results/gpt-4o-mini-evidence.run.json
Comparing examples/results/gpt-4o-mini-no-evidence.run.json -> examples/results/gpt-4o-mini-evidence.run.json (432 common cases)
EX: 37.5% -> 61.8% (+24.3 pp)
Both correct 144 | Fixed 123 | Regressed 18 | Both wrong 147
By difficulty: challenging 29.1% -> 47.3%, moderate 27.7% -> 54.6%, simple 43.8% -> 68.2%
By database: student_club 43.0% -> 57.0%, superhero 57.4% -> 79.8%, toxicology 13.8% -> 51.0%
Output difference: empty_result 100 -> 34, single_value_differs 94 -> 44, column_mismatch 78 -> 62, row_set_differs 46 -> 58, row_count_differs 26 -> 31, execution_failed 9 -> 4
SQL structure difference: columns 155 -> 79, tables_joins 130 -> 72, where_value 129 -> 22, aggregation 121 -> 66, order_limit 40 -> 23
```

`--max-drop`을 넘으면 표준 오류에 `FAILED: EX dropped by 24.3 pp, more than --max-drop 5`처럼 나온다. 읽는 법은 [실행 비교 가이드](../guides/comparing-runs.md)에 있다.

`--json`의 키:

| 키 | 값 |
| --- | --- |
| `common_cases` | 공통 케이스 수 |
| `dataset_mismatch` | 데이터셋 SHA-256이 다른지 |
| `only_in_base`, `only_in_head` | 한쪽에만 있는 케이스 `id` 목록 |
| `base_ex`, `head_ex`, `delta_pp` | 공통 케이스 기준 EX(0~1)와 변화(%p) |
| `both_correct`, `fixed`, `regressed`, `both_wrong` | 분할표의 네 칸 |
| `fixed_ids`, `regressed_ids` | 뒤집힌 케이스 `id` 목록 |
| `output_differences`, `sql_structure_differences` | `base`와 `head`의 종류별 개수 |
| `failed_max_drop` | `--max-drop` 기준을 넘었는지 |

CSV 열은 `id`, `db_id`, `difficulty`, `change`(`both_correct`, `fixed`, `regressed`, `both_wrong`), `base_status`, `head_status`, `base_output_differences`, `head_output_differences`, `question`, `gold_sql`, `base_pred_sql`, `head_pred_sql`이다.
