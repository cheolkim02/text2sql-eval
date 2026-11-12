# 실행 파일 형식

`text2sql-eval eval`은 실행 하나를 JSON 파일 하나로 쓴다([ADR 0026](../decisions/0026-run-file-json.md)). `report`와 `compare`가 이 파일을 읽고, 사람이 직접 열어 봐도 되도록 들여쓰기한 UTF-8 JSON이다. Python에서는 [`read_run`·`write_run`](api.md#read_run)으로 읽고 쓴다.

지금 형식은 `schema_version` **3**이다. 이 도구는 자기와 같은 버전만 읽는다. 다른 버전이면 입력 오류가 난다. 파일이 더 새 버전이면 도구를 업그레이드하라고, 더 오래된 버전이면 `eval`을 다시 돌리라고 안내한다.

## 전체 구조

```json
{
  "schema_version": 3,
  "tool": {"name": "text2sql-eval", "version": "0.1.0"},
  "created_at": "2026-11-11T09:03:51Z",
  "inputs": {
    "dataset": {"path": "examples/bird-mini/dev.json", "sha256": "3218e995…"},
    "predictions": {"path": "examples/results/gpt-4o-mini-evidence.jsonl", "sha256": "a349007a…", "format": "jsonl"},
    "tied": {"path": "examples/bird-mini/dev_tied_append.json", "sha256": "606cd1e9…"},
    "db_dir": "examples/bird-mini/dev_databases"
  },
  "settings": {"timeout_seconds": 30.0, "max_rows": null, "allow_missing": false},
  "meta": {"model": "gpt-4o-mini-2024-07-18", "prompt": "single-prompt-v1"},
  "summary": {"total": 432, "correct": 267, "incorrect": 161, "error": 4, "ex": 0.6180555555555556},
  "cases": [ … ]
}
```

(해시는 줄였다. 실제 파일은 [examples/results](../../examples/results/)에 있다.)

| 필드 | 타입 | 내용 |
| --- | --- | --- |
| `schema_version` | 정수 | 형식 버전. 지금은 3 |
| `tool` | 객체 | 이 파일을 쓴 도구의 `name`과 `version` |
| `created_at` | 문자열 | 만든 시각, UTC, 초 단위(`2026-11-11T09:03:51Z`) |
| `inputs` | 객체 | 입력 파일. 아래 참고 |
| `settings` | 객체 | 실행 설정. 아래 참고 |
| `meta` | 객체 | `--meta KEY=VALUE`로 준 값. 문자열에서 문자열로 |
| `summary` | 객체 | `total`, `correct`, `incorrect`, `error`(케이스 수)와 `ex`(EX, 0~1). `cases`에서 다시 계산할 수 있는 값이고, 읽을 때는 쓰지 않는다 |
| `cases` | 배열 | 케이스마다 하나, 데이터셋 순서 |

### `inputs`

| 필드 | 내용 |
| --- | --- |
| `dataset` | 데이터셋 파일의 `path`(실행할 때 준 그대로)와 `sha256`(파일 내용의 SHA-256, 16진수) |
| `predictions` | 예측 파일의 `path`, `sha256`, `format`(`text` 또는 `jsonl`) |
| `tied` | 동점 대체 정답 파일의 `path`와 `sha256`. 주지 않았으면 `null` |
| `db_dir` | DB 폴더 경로 |

`compare`는 두 실행의 `dataset.sha256`이 다르면 경고한다. 해시가 같으면 같은 문제 파일로 돌렸다는 뜻이다.

### `settings`

| 필드 | 내용 |
| --- | --- |
| `timeout_seconds` | 쿼리당 시간 제한(초) |
| `max_rows` | 행 수 제한. 없으면 `null` |
| `allow_missing` | `--allow-missing`을 줬는지 |

## 케이스

실제 파일의 #300(결과 행은 두 줄만 남겼다):

```json
{
  "id": "300",
  "db_id": "toxicology",
  "difficulty": "simple",
  "question": "What atoms comprise TR186?",
  "evidence": "TR186 is a molecule id",
  "gold_sql": "SELECT T.atom_id FROM atom AS T WHERE T.molecule_id = 'TR186'",
  "pred_sql": "SELECT atom_id, element FROM atom WHERE molecule_id = 'TR186';",
  "prediction_state": "given",
  "pred_meta": {"model": "gpt-4o-mini-2024-07-18", "input_tokens": 321, "output_tokens": 19, "latency_ms": 821},
  "status": "incorrect",
  "error": null,
  "flags": [
    {
      "kind": "gold_rows_with_extra_columns",
      "detail": "the prediction returns every gold row plus extra columns; it may be a correct answer judged wrong"
    }
  ],
  "gold": {"columns": ["atom_id"], "rows": [["TR186_1"], ["TR186_10"]], "row_count": 41},
  "pred": {"columns": ["atom_id", "element"], "rows": [["TR186_1", "c"], ["TR186_10", "c"]], "row_count": 41},
  "diff": {
    "output": {
      "differences": ["column_mismatch"],
      "gold_columns": 1,
      "pred_columns": 2,
      "gold_distinct_rows": 41,
      "pred_distinct_rows": 41,
      "gold_contained": true,
      "relation": null
    },
    "sql_structure": {
      "differences": [{"kind": "columns", "gold": "(none)", "pred": "element"}],
      "parse_failed": null
    }
  }
}
```

| 필드 | 타입 | 내용 |
| --- | --- | --- |
| `id` | 문자열 | 데이터셋의 `question_id`를 문자열로 |
| `db_id` | 문자열 | DB 이름 |
| `difficulty` | 문자열 또는 `null` | 데이터셋에 있으면 그대로(`simple`, `moderate`, `challenging`) |
| `question`, `evidence`, `gold_sql` | 문자열 | 데이터셋 원문 |
| `pred_sql` | 문자열 | 예측 SQL. 예측이 없으면 빈 문자열 |
| `prediction_state` | 문자열 | `given`(예측 있음), `empty`(빈 SQL), `missing`(예측 파일에 없음, `--allow-missing`일 때만) |
| `pred_meta` | 객체 | JSONL 예측 줄의 `meta`를 그대로. 없으면 `{}` |
| `status` | 문자열 | 판정: `correct`, `incorrect`, `error` |
| `error` | 객체 또는 `null` | `status`가 `error`일 때만: 어느 쪽(`side`: `pred` 또는 `gold`)이, 어떻게(`kind`: `error`, `timeout`, `row_limit`) 실패했는지와 `message`. 둘 다 실패하면 공식 스크립트처럼 예측 쪽을 적는다 |
| `flags` | 배열 | 판정 신뢰도 플래그. 각각 `kind`(코드)와 `detail`(설명). 판정을 바꾸지 않는다 |
| `gold`, `pred` | 객체 | 실행 결과. 아래 참고 |
| `diff` | 객체 또는 `null` | 정답이 아닌 케이스의 차이. 아래 참고 |

`status`, 플래그와 차이의 코드별 뜻은 [결과 읽기 가이드](../guides/reading-results.md)에 있다.

### 실행 결과 (`gold`, `pred`)

성공하면:

| 필드 | 내용 |
| --- | --- |
| `columns` | 컬럼 이름 목록 |
| `rows` | 결과의 **앞 20행**. 각 행은 값의 배열이다 |
| `row_count` | 전체 행 수. `rows`보다 많으면 일부만 저장된 것이다 |

실패하면 `{"failure": {"kind": "timeout", "message": "did not finish within 30 s"}}`처럼 `failure`만 있다. `kind`는 `error`(SQLite 오류), `timeout`, `row_limit` 중 하나다.

행은 앞 20행만 저장한다. 판정은 실행할 때 전체 행으로 이미 끝났으므로, 저장된 행은 사람이 보기 위한 표본이다. HTML 리포트의 행 강조도 이 표본에 맞춰 조심스럽게 한다([ADR 0039](../decisions/0039-html-report-scope.md)).

### 값의 표기

SQLite 값은 JSON으로 이렇게 적는다.

| SQLite 값 | JSON |
| --- | --- |
| `NULL` | `null` |
| 정수, 유한한 실수 | 숫자 |
| 문자열 | 문자열 |
| BLOB | `{"$bytes": "00ff"}` (16진수) |
| 무한대, NaN | `{"$float": "inf"}`, `{"$float": "-inf"}`, `{"$float": "nan"}` |

JSON에는 BLOB, 무한대, NaN이 없어서 `$`로 시작하는 키 하나짜리 객체로 표시한다. `read_run`은 이것을 원래 값으로 되돌린다.

### 차이 (`diff`)

정답이 아닌 케이스(`incorrect`, 예측 쪽 `error`)에만 있다. 정답 케이스와, 정답 SQL 자체가 실패한 케이스에는 `null`이다([ADR 0031](../decisions/0031-error-facts-v1.md)). 두 객체를 가진다.

| 필드 | 내용 |
| --- | --- |
| `output` | 실행 결과를 비교한 출력 차이 |
| `sql_structure` | 정답·예측 SQL을 파싱해 비교한 SQL 구조 차이 |

`diff.output`은 실행 결과의 차이다([ADR 0033](../decisions/0033-multi-label-differences.md)).

| 필드 | 내용 |
| --- | --- |
| `differences` | 출력 차이 코드 목록. 여러 개일 수 있다 |
| `gold_columns`, `pred_columns` | 컬럼 수 |
| `gold_distinct_rows`, `pred_distinct_rows` | 중복을 뺀 행 수 |
| `gold_contained` | 정답 행이 예측 행 안에 그대로 있는지. 컬럼 수가 다르면 예측 컬럼의 순서·부분을 바꿔 가며 찾는다. 판단할 수 없으면 `null` |
| `relation` | 컬럼 수가 같을 때 예측 행 집합과 정답 행 집합의 관계: `subset`, `superset`, `overlap`, `disjoint`. 그 밖에는 `null` |

`diff.sql_structure`는 정답·예측 SQL을 파싱해 비교한 차이다([ADR 0031](../decisions/0031-error-facts-v1.md), [0032](../decisions/0032-sqlglot.md)).

| 필드 | 내용 |
| --- | --- |
| `differences` | 각각 `kind`(구조 차이 코드), `gold`, `pred`(그 근거가 되는 SQL 조각) |
| `parse_failed` | 파싱에 실패한 쪽(`gold`, `pred`). 실패하면 `differences`는 비어 있다. 성공하면 `null` |

## 버전 정책

- 필드를 바꾸거나 없애면 `schema_version`을 올린다.
- 이 문서는 지금 버전(3)만 설명한다.
- 지난 버전의 실행 파일은 지금 도구로 `eval`을 다시 돌려 새 버전으로 만든다. 예측 파일을 함께 남겨 두면 언제든 다시 만들 수 있다.
