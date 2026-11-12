# Python API 레퍼런스

`text2sql_eval` 패키지가 `__all__`로 내보내는 이름만 공개 API다([ADR 0043](../decisions/0043-public-api-scope.md)). 하위 모듈(`text2sql_eval.judge.ex` 등)은 예고 없이 바뀔 수 있으니 패키지에서 바로 가져온다. 패키지는 타입 정보(`py.typed`)를 함께 배포하므로 pyright·mypy로 사용 코드를 검사할 수 있다. 공개 API에는 `Any`가 없다(테스트로 검사한다).

CLI의 `eval → report → compare`와 같은 흐름:

```python
from pathlib import Path

import text2sql_eval as t2s

run = t2s.evaluate_files(
    Path("examples/bird-mini/dev.json"),
    Path("examples/results/gpt-4o-mini-evidence.jsonl"),
    db_dir=Path("examples/bird-mini/dev_databases"),
    tied=Path("examples/bird-mini/dev_tied_append.json"),
    meta={"model": "gpt-4o-mini"},
)
t2s.write_run(run, Path("runs/evidence.json"))
t2s.write_html_report(run, Path("runs/evidence.html"), run_name="evidence")

base = t2s.read_run(Path("examples/results/gpt-4o-mini-no-evidence.run.json"))
comparison = t2s.compare_runs(base, run)
print(comparison.counts()["fixed"], round(comparison.delta_pp, 1))  # 123 24.3
```

모든 결과 타입은 고정된(frozen) dataclass다. 값을 바꿀 수 없고, 같은 내용이면 `==`로 같다.

## 함수

### `evaluate_files`

```text
evaluate_files(dataset: Path, predictions: Path, *, db_dir: Path,
               prediction_format: "text" | "jsonl" | None = None,
               allow_missing: bool = False, tied: Path | None = None,
               timeout: float = 30.0, max_rows: int | None = None,
               workers: int | None = None,
               meta: Mapping[str, str] | None = None) -> Run
```

`text2sql-eval eval`이 하는 일을 한다. 파일을 읽고, 모든 케이스를 실행·판정하고, 입력 파일의 SHA-256과 설정, `meta`를 기록한 [`Run`](#run)을 돌려준다. 파일로 남기려면 [`write_run`](#write_run)을 쓴다. 인자의 뜻은 [CLI의 `eval` 옵션](cli.md#eval)과 같다.

- `prediction_format`이 `None`이면 확장자(`.txt`, `.jsonl`)로 정한다.
- 입력 파일이 잘못됐거나 데이터셋과 맞지 않거나 DB 파일이 없으면 [`InputError`](#inputerror)를 낸다.

### `read_run`

`read_run(path: Path) -> Run`

[실행 파일](run-file.md)을 읽는다. 형식이 맞지 않거나 `schema_version`이 다르면 [`InputError`](#inputerror)를 낸다.

### `write_run`

`write_run(run: Run, path: Path) -> None`

실행을 UTF-8 JSON으로 쓴다. 상위 폴더가 없으면 만든다. `read_run(path) == run`이 성립한다.

### `compare_runs`

`compare_runs(base: Run, head: Run) -> Comparison`

두 실행에 모두 있는 케이스를 짝지어 [`Comparison`](#comparison)을 돌려준다. 데이터셋 해시가 다르거나 한쪽에만 있는 케이스는 오류가 아니라 `Comparison`의 필드로 알려 준다.

### `write_html_report`

`write_html_report(run: Run, path: Path, *, run_name: str) -> None`

오프라인에서 열리는 HTML 리포트 파일 하나를 쓴다. `run_name`은 페이지 제목에 들어간다(보통 실행 파일 이름).

### `write_report_csv`

`write_report_csv(run: Run, path: Path) -> None`

케이스마다 한 줄인 CSV를 쓴다. 열은 [CLI의 `report`](cli.md#report)와 같다.

### `write_comparison_csv`

`write_comparison_csv(comparison: Comparison, path: Path) -> None`

공통 케이스마다 한 줄인 비교 CSV를 쓴다. 열은 [CLI의 `compare`](cli.md#compare)와 같다.

### `status_of`

`status_of(verdict: Verdict) -> "correct" | "incorrect" | "error"`

판정의 상태 이름. 실행 파일의 `status`, CSV의 `status`와 같은 값이다.

## 실행 파일

### `Run`

실행 하나. [실행 파일 형식](run-file.md)과 필드가 대응한다.

| 필드 | 타입 |
| --- | --- |
| `tool_version`, `created_at`, `db_dir` | `str` |
| `dataset`, `predictions` | [`FileRef`](#fileref) |
| `prediction_format` | `"text"` 또는 `"jsonl"` |
| `tied` | [`FileRef`](#fileref) `\| None` |
| `settings` | [`RunSettings`](#runsettings) |
| `meta` | `dict[str, str]` |
| `cases` | `tuple[`[`CaseRecord`](#caserecord)`, ...]` |

`run.summary`는 `cases`에서 계산한 [`Summary`](#summary)다.

### `Summary`

`total`, `correct`, `incorrect`, `error` (모두 `int`). `ex`는 `correct / total`이다(케이스가 없으면 0.0).

### `FileRef`

입력 파일의 `path`(`str`)와 `sha256`(`str`, 16진수).

### `RunSettings`

`timeout_seconds: float`, `max_rows: int | None`, `allow_missing: bool`.

### `CaseRecord`

케이스 하나의 판정과 근거.

| 필드 | 타입 |
| --- | --- |
| `id`, `db_id`, `question`, `evidence`, `gold_sql`, `pred_sql` | `str` |
| `difficulty` | `str \| None` |
| `prediction_state` | [`PredictionState`](#predictionstate) |
| `verdict` | [`Verdict`](#verdict) |
| `gold`, `pred` | [`ResultSample`](#resultsample) `\|` [`QueryFailure`](#queryfailure) |
| `pred_meta` | `dict[str, object]` |
| `diff` | [`CaseDiff`](#casediff) `\| None` (정답이거나 정답 SQL이 실패하면 `None`) |

### `ResultSample`

성공한 쿼리 결과의 표본. `columns: tuple[str, ...]`, `rows`(앞 20행, `tuple[tuple[SqlValue, ...], ...]`), `row_count: int`(전체 행 수).

### `QueryFailure`

실패한 쿼리. `kind`는 `"error"`, `"timeout"`, `"row_limit"` 중 하나이고, `message: str`이 있다.

### `SqlValue`

SQLite가 돌려주는 값의 타입: `int | float | str | bytes | None`.

### `PredictionState`

`"given"`(예측 있음), `"empty"`(빈 SQL), `"missing"`(예측 파일에 없음).

## 판정

### `Verdict`

`Correct | Incorrect | ExecError`. 판별 유니언이므로 `match`로 나누고, 빠뜨린 경우가 없는지 타입 검사기가 확인하게 할 수 있다.

```python
from typing import assert_never

from text2sql_eval import Correct, ExecError, Incorrect, Verdict


def describe(verdict: Verdict) -> str:
    match verdict:
        case Correct():
            return "correct"
        case Incorrect():
            return "wrong rows"
        case ExecError(side=side, kind=kind):
            return f"{side} query failed: {kind}"
        case _:
            assert_never(verdict)
```

### `Correct`

예측 행과 정답 행이 집합으로 같다(BIRD 공식 규칙). `flags: tuple[Flag, ...]`.

### `Incorrect`

두 쿼리 모두 실행됐고 행이 다르다. `flags: tuple[Flag, ...]`.

### `ExecError`

쿼리가 실패해 0점이다. `side`(`"pred"` 또는 `"gold"`), `kind`(`"error"`, `"timeout"`, `"row_limit"`), `message: str`, `flags`.

### `Flag`

판정을 의심하거나 다시 볼 이유. 판정은 바꾸지 않는다. `kind:` [`FlagKind`](#flagkind), `detail: str`.

### `FlagKind`

`"empty_prediction_correct"`, `"gold_empty_correct"`, `"matches_tied_alternative_only"`, `"gold_rows_with_extra_columns"`, `"gold_columns_concatenated"`, `"tied_alternative_exists"`. 뜻은 [결과 읽기 가이드](../guides/reading-results.md)에 있다.

## 차이

### `CaseDiff`

오답 하나의 차이. `output:` [`OutputDiff`](#outputdiff), `structure:` [`StructureReport`](#structurereport).

### `OutputDiff`

실행 결과의 차이. `differences: tuple[OutputDifference, ...]`, `gold_columns`, `pred_columns`, `gold_distinct_rows`, `pred_distinct_rows`(`int`), `gold_contained: bool | None`, `relation: Relation | None`. 각 필드의 뜻은 [실행 파일 형식](run-file.md#차이-diff)에 있다.

### `OutputDifference`

`"execution_failed"`, `"empty_result"`, `"column_mismatch"`, `"row_count_differs"`, `"single_value_differs"`, `"row_set_differs"`.

### `Relation`

컬럼 수가 같을 때 예측 행 집합이 정답 행 집합의 무엇인지: `"subset"`, `"superset"`, `"overlap"`, `"disjoint"`.

### `StructureReport`

SQL 구조의 차이. `facts: tuple[Fact, ...]`, `parse_failed`(`"gold"`, `"pred"` 또는 `None`).

### `Fact`

구조 차이 하나와 그 근거. `kind:` [`FactKind`](#factkind), `gold: str`, `pred: str`(양쪽 SQL 조각).

### `FactKind`

`"where_value"`, `"tables_joins"`, `"columns"`, `"aggregation"`, `"order_limit"`.

## 비교

### `Comparison`

두 실행을 공통 케이스로 비교한 결과. 케이스는 `base`의 순서다.

| 필드·메서드 | 타입 | 내용 |
| --- | --- | --- |
| `cases` | `tuple[CaseChange, ...]` | 공통 케이스 |
| `dataset_mismatch` | `bool` | 데이터셋 SHA-256이 다른지 |
| `only_in_base`, `only_in_head` | `tuple[str, ...]` | 한쪽에만 있는 케이스 `id` |
| `counts()` | `Counter[Change]` | 분할표 |
| `base_ex`, `head_ex` | `float` | 공통 케이스 기준 EX |
| `delta_pp` | `float` | EX 변화(%p, `head - base`) |
| `by("difficulty" \| "db_id")` | `list[GroupEx]` | 난이도별 또는 DB별 EX, 이름 순 |
| `output_differences()` | `tuple[Counter[str], Counter[str]]` | `base`, `head`의 출력 차이 개수 |
| `structure_differences()` | `tuple[Counter[str], Counter[str]]` | `base`, `head`의 SQL 구조 차이 개수 |

### `CaseChange`

공통 케이스 하나. `base`, `head`(둘 다 [`CaseRecord`](#caserecord))와 `change`([`Change`](#change)).

### `Change`

`"both_correct"`, `"fixed"`(head만 맞음), `"regressed"`(base만 맞음), `"both_wrong"`.

### `GroupEx`

그룹 하나의 EX. `name: str`, `cases: int`, `base_ex: float`, `head_ex: float`.

## 오류와 버전

### `InputError`

입력 파일을 쓸 수 없을 때 나는 예외. `path`, `problem`, `location`(`str | None`, 예: `"line 3"`), `hint`(`str | None`)를 가진다. `str(error)`는 CLI가 보여 주는 메시지와 같다.

### `__version__`

설치된 패키지의 버전 문자열.
