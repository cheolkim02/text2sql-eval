# text2sql-eval

[![CI](https://github.com/cheolkim02/text2sql-eval/actions/workflows/ci.yml/badge.svg)](https://github.com/cheolkim02/text2sql-eval/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/text2sql-eval)](https://pypi.org/project/text2sql-eval/)
[![Python](https://img.shields.io/pypi/pyversions/text2sql-eval)](https://pypi.org/project/text2sql-eval/)

**English summary.** Documentation is in Korean. `text2sql-eval` is a Python library and CLI for the error analysis of text-to-SQL experiments. It judges execution accuracy (EX) with the same rule as BIRD's official script, explains every wrong case without an LLM (how the results differ and where the SQL differs), flags verdicts the official rule may get wrong, compares two runs case by case, and writes an offline HTML report and a CSV. The same inputs always give the same output.

```sh
pip install text2sql-eval
text2sql-eval eval --dataset dev.json --db-dir dev_databases --pred predictions.jsonl --out run.json
```

text-to-SQL 실험의 예측 파일을 받아 **EX(실행 정확도)를 판정하고, 오답이 정답과 무엇이 다른지를 AI 없이 근거와 함께 보여 주는** Python 라이브러리이자 CLI다.

## 무엇을 하나

- **EX 판정:** BIRD 공식 스크립트와 같은 규칙(행 집합 비교)으로 판정한다. 같은 예측을 공식 스크립트로도 채점해 숫자가 같음을 확인했다.
- **오답의 차이:** 오답마다 두 가지를 근거와 함께 붙인다. 한 오답에 여러 개가 붙을 수 있다.
  - 출력 차이 6종: 빈 결과(`empty_result`), 컬럼 수(`column_mismatch`), 행 수(`row_count_differs`), 값 하나(`single_value_differs`), 행 내용(`row_set_differs`), 실행 실패(`execution_failed`)
  - SQL 구조 차이 5종: WHERE 값(`where_value`), 테이블·JOIN(`tables_joins`), 컬럼(`columns`), 집계(`aggregation`), ORDER BY/LIMIT(`order_limit`)
- **판정 신뢰도 플래그:** 공식 규칙이 놓쳤을 수 있는 판정 6가지를 표시한다(거짓 정답 의심, 거짓 오답 의심). 판정 자체는 바꾸지 않는다.
- **두 실험 비교:** 케이스 단위 분할표(고쳐짐, 나빠짐), 난이도별·DB별 EX, 차이 분포의 변화를 보여 준다. 기준보다 나빠지면 실패하게 해서 CI에서도 쓸 수 있다.
- **리포트:** 인터넷 없이 열리는 HTML 한 파일과, 엑셀에서 한글이 깨지지 않는 CSV를 만든다. HTML은 정답·예측 SQL을 절마다 줄을 나눠 나란히 보여 주고, 다른 절과 다른 행을 색칠한다.

판정과 분석에 LLM, 무작위, 시간에 따라 달라지는 값을 쓰지 않는다. 같은 입력이면 같은 결과가 나온다.

![HTML 리포트에서 #247 케이스를 펼친 화면. 정답·예측 SQL이 절마다 줄을 나눠 나란히 보이고, 서로 다른 WHERE 절과 정답에 없는 예측 결과 행 cl, h가 노랗게 칠해져 있다](https://raw.githubusercontent.com/cheolkim02/text2sql-eval/main/docs/images/report-case.png)

HTML 리포트에서 오답 하나(#247)를 펼친 화면이다. 정답과 예측 SQL에서 다른 절(WHERE)과, 정답에 없는 예측 결과 행(`cl`, `h`)을 칠한다. 출력 차이(`row_count_differs`, `row_set_differs`)와 SQL 구조 차이(`tables_joins`)를 근거와 함께 보여 준다. 리포트 전체는 [examples/results/report.html](https://github.com/cheolkim02/text2sql-eval/blob/main/examples/results/report.html)이다. GitHub 화면에서는 HTML 소스로 보이니, 파일을 내려받아 브라우저로 연다.

## 설치

Python 3.11 이상이 필요하다.

```sh
pip install text2sql-eval
```

## 3분 사용법

예제 데이터는 패키지가 아니라 저장소에 들어 있다. BIRD dev의 DB 3개와 문제 432개, gpt-4o-mini의 예측 두 벌이다. 위에서 설치했다면 저장소는 데이터만 받으면 된다.

```sh
git clone https://github.com/cheolkim02/text2sql-eval.git
cd text2sql-eval
```

설치하지 않았거나 저장소의 코드로 설치하려면 여기서 `pip install .`을 한다. uv를 쓰면 `uv sync`를 하고 아래 명령 앞에 `uv run`을 붙인다. 자세한 안내는 [시작하기](https://github.com/cheolkim02/text2sql-eval/blob/main/docs/guides/getting-started.md)에 있다.

판정하기(30초쯤 걸린다):

```sh
text2sql-eval eval \
  --dataset examples/bird-mini/dev.json \
  --db-dir examples/bird-mini/dev_databases \
  --pred examples/results/gpt-4o-mini-evidence.jsonl \
  --tied examples/bird-mini/dev_tied_append.json \
  --out runs/evidence.json
```

`--tied`는 BIRD가 함께 주는 동점 대체 정답 파일이다. 정답 SQL이 동점 중 하나만 고르는 문제에 다른 정답을 알려 준다. 판정에는 쓰지 않고 플래그에만 쓰며, 빼도 된다.

```text
Evaluated 432 cases: EX 61.8% (267 correct, 161 incorrect, 4 errors)
Output difference: 62 column_mismatch, 58 row_set_differs, 44 single_value_differs, 34 empty_result, 31 row_count_differs, 4 execution_failed
SQL structure difference: 79 columns, 72 tables_joins, 66 aggregation, 23 order_limit, 22 where_value
Flags: 8 gold_columns_concatenated, 25 gold_rows_with_extra_columns, 5 matches_tied_alternative_only, 13 tied_alternative_exists
Run file: runs/evidence.json
```

리포트 만들기(`runs/evidence.html`을 브라우저로 연다):

```sh
text2sql-eval report runs/evidence.json --html runs/evidence.html --csv runs/evidence.csv
```

evidence를 뺀 실험과 비교하기:

```sh
text2sql-eval compare examples/results/gpt-4o-mini-no-evidence.run.json runs/evidence.json
```

```text
Comparing examples/results/gpt-4o-mini-no-evidence.run.json -> runs/evidence.json (432 common cases)
EX: 37.5% -> 61.8% (+24.3 pp)
Both correct 144 | Fixed 123 | Regressed 18 | Both wrong 147
By difficulty: challenging 29.1% -> 47.3%, moderate 27.7% -> 54.6%, simple 43.8% -> 68.2%
By database: student_club 43.0% -> 57.0%, superhero 57.4% -> 79.8%, toxicology 13.8% -> 51.0%
Output difference: empty_result 100 -> 34, single_value_differs 94 -> 44, column_mismatch 78 -> 62, row_set_differs 46 -> 58, row_count_differs 26 -> 31, execution_failed 9 -> 4
SQL structure difference: columns 155 -> 79, tables_joins 130 -> 72, where_value 129 -> 22, aggregation 121 -> 66, order_limit 40 -> 23
```

## 내 실험에 쓰기

가장 널리 쓰이는 BIRD 형식을 기준으로, 파일 세 개가 필요하다.

1. **문제 파일(`--dataset`):** BIRD의 `dev.json`과 같은 JSON 배열이다. 문제마다 `question_id`(정수), `db_id`, `question`, `evidence`, `SQL`(정답 SQL)이 있다. `difficulty`가 있으면 난이도별 EX도 낸다.
2. **DB 폴더(`--db-dir`):** `<db-dir>/<db_id>/<db_id>.sqlite` 구조의 SQLite 파일이다. BIRD의 `dev_databases` 폴더가 이 구조다.
3. **예측 파일(`--pred`):** 모델이 만든 SQL이다. 두 형식 중 하나로 쓴다.
   - `.txt`: 한 줄에 SQL 하나. N번째 줄이 문제 파일의 N번째 문제의 예측이다.
   - `.jsonl`: 한 줄에 `{"id": question_id, "sql": "..."}` 하나. 줄 순서는 상관없다.

```text
{"id": 195, "sql": "SELECT T.bond_type FROM bond AS T GROUP BY T.bond_type ORDER BY COUNT(*) DESC LIMIT 1"}
{"id": 196, "sql": "SELECT COUNT(*) FROM atom WHERE element = 'cl'"}
```

```sh
text2sql-eval eval --dataset dev.json --db-dir dev_databases \
  --pred my_predictions.jsonl --meta model=my-model --out runs/my-run.json
text2sql-eval report runs/my-run.json --html runs/my-run.html
```

`--meta`로 모델 이름이나 프롬프트 버전 같은 실험 설정을 판정 결과 파일에 함께 남긴다. 예측 파일을 만드는 법은 [예측 파일 만들기](https://github.com/cheolkim02/text2sql-eval/blob/main/docs/guides/prediction-format.md)에 있다.

Python에서는 같은 일을 이렇게 한다([API 레퍼런스](https://github.com/cheolkim02/text2sql-eval/blob/main/docs/reference/api.md)).

```python
from pathlib import Path

from text2sql_eval import evaluate_files, write_html_report, write_run

run = evaluate_files(
    Path("dev.json"),
    Path("my_predictions.jsonl"),
    db_dir=Path("dev_databases"),
)
print(f"EX {run.summary.ex:.1%}")
write_run(run, Path("runs/my-run.json"))
write_html_report(run, Path("runs/my-run.html"), run_name="my-run")
```

## 실측 결과

저장소에 커밋된 baseline이다. `examples/bird-mini`(BIRD dev, 432문제)에서 gpt-4o-mini로 같은 프롬프트를 두 번 돌렸고, 다른 점은 BIRD의 `evidence`(힌트)를 넣었는지 하나다.

| 설정 | EX | simple | moderate | challenging | BIRD 공식 스크립트 |
| --- | --- | --- | --- | --- | --- |
| evidence 있음 | **61.81%** | 68.22% | 54.62% | 47.27% | 61.81% (일치) |
| evidence 없음 | **37.50%** | 43.80% | 27.73% | 29.09% | 37.50% (일치) |

- **공식 스크립트와 일치:** 공식 평가 스크립트를 수정하지 않고 같은 예측을 채점했다. 난이도별 숫자까지 8개가 모두 소수점 둘째 자리까지 같다.
- **거짓 오답 의심:** evidence 있음 실험의 오답 161개 중 38개(24%)에 플래그가 붙었다. 공식 규칙으로는 오답이지만 사람이 보면 맞다고 할 만한 답이다. 예를 들어 #1445는 이름과 성을 한 컬럼으로 이어 붙였고, #300은 원자 id에 원소 컬럼을 덧붙였다.
- **두 실험 비교:** evidence를 넣자 123개가 맞게 바뀌고 18개가 틀리게 바뀌었다(+24.3%p). `where_value` 차이가 129개에서 22개로 가장 많이 줄었다. evidence가 주로 WHERE에 들어갈 값(철자, 대소문자, 코드값)을 알려 주기 때문이다.

생성 조건, 비용, 시간 제한에 민감한 케이스는 [examples/results](https://github.com/cheolkim02/text2sql-eval/tree/main/examples/results)에 있다.

## 문서

| 문서 | 내용 |
| --- | --- |
| [시작하기](https://github.com/cheolkim02/text2sql-eval/blob/main/docs/guides/getting-started.md) | 설치부터 예제로 `eval → report → compare`까지 |
| [예측 파일 만들기](https://github.com/cheolkim02/text2sql-eval/blob/main/docs/guides/prediction-format.md) | 내 파이프라인의 결과를 넣는 법 |
| [결과 읽기](https://github.com/cheolkim02/text2sql-eval/blob/main/docs/guides/reading-results.md) | 판정 규칙, 차이와 플래그의 뜻, HTML 리포트, CSV로 손 분류하기 |
| [실험 비교하기](https://github.com/cheolkim02/text2sql-eval/blob/main/docs/guides/comparing-runs.md) | 비교 결과 해석, CI에서 쓰기 |
| [CLI 레퍼런스](https://github.com/cheolkim02/text2sql-eval/blob/main/docs/reference/cli.md) | 명령과 옵션, 종료 코드, 출력 형식 |
| [API 레퍼런스](https://github.com/cheolkim02/text2sql-eval/blob/main/docs/reference/api.md) | 공개 Python API 38개 |
| [판정 결과 파일 형식](https://github.com/cheolkim02/text2sql-eval/blob/main/docs/reference/run-file.md) | `eval`이 쓰는 JSON |
| [아키텍처](https://github.com/cheolkim02/text2sql-eval/blob/main/docs/architecture.md) | 모듈 경계, 의존 방향, 설계 원칙 |
| [기여 안내](https://github.com/cheolkim02/text2sql-eval/blob/main/CONTRIBUTING.md) | 개발 환경, 검사, 커밋 규칙 |

## 한계와 로드맵

- **지원 형식:** 가장 널리 쓰이는 BIRD 형식(문제 파일, DB 폴더)을 먼저 지원한다. 예측은 텍스트(`.txt`)와 JSONL(`.jsonl`)로 받는다. 다른 벤치마크 형식은 추가할 예정이다.
- **실행 엔진:** SQLite만 실행한다. PostgreSQL·MySQL은 로드맵이다.
- **판정:** BIRD 공식 규칙 하나로만 판정한다. 행 순서와 중복까지 따지는 엄격 모드는 로드맵이다.
- **정규화:** SQL 구조 차이의 정규화는 최소한이다. 조건 순서, `IN`과 `EXISTS`, 서브쿼리와 JOIN처럼 뜻은 같고 모양이 다른 SQL은 다르게 본다.
- **카테고리 매핑:** 사용자가 정한 카테고리를 파일로 자동으로 붙이는 기능은 로드맵이다. 지금은 CSV의 `my_category` 열에 손으로 적는다.
- **버전:** 아직 0.x 버전이라 공개 API와 판정 결과 파일 형식이 바뀔 수 있다. 판정 결과 파일에는 형식 버전(`schema_version`)이 들어 있다.

## 해결하려는 문제

text-to-SQL 실험에서는 실험을 돌리는 것보다 결과를 판단하는 데 시간이 더 오래 걸린다.

- **오답 분석이 수작업이다.** 틀린 케이스마다 정답과 예측 SQL을 읽고, 다른 곳을 찾아 엑셀에 적고, 카테고리를 붙인다. 질문이나 SQL이 길면 읽기조차 힘들다.
- **분류를 AI에게 맡길 수 없다.** 평가 결과를 LLM이 분류하면 그 분류에도 오류가 섞여, 평가를 믿을 수 없게 된다.
- **EX 판정 자체가 틀린다.** 정답 결과가 비어 있으면 빈 결과를 내는 아무 SQL이나 정답이 된다. 사람 이름을 물었을 때 이름과 성을 한 컬럼으로 이어 붙여 내면, 내용이 맞아도 오답이 된다.
- **실험 비교도 수작업이다.** 두 설정에서 둘 다 틀린 문제, 한쪽만 틀린 문제를 스크립트로 뽑아 눈으로 본다.

그래서 이 도구는 "무엇이 다른가"를 규칙으로 보고하고, "왜 틀렸나"는 사람이 판단하게 둔다.

## 품질

- **타입:** pyright strict에서 오류가 0개다. 공개 API에 `Any`가 없고, 타입 정보(`py.typed`)를 함께 배포한다.
- **CI:** GitHub Actions에서 다음을 돌린다.
  - Ruff 린트와 포맷 검사, pyright
  - Python 3.11~3.15 테스트
  - 빌드한 wheel을 개발 도구 없는 새 환경에 설치해 CLI를 실제로 돌려 보기
- **테스트:** 단위 테스트, Hypothesis 속성 기반 테스트, 실제 프로세스로 돌리는 e2e 테스트가 있다. 그 밖에 이런 것을 지킨다.
  - 커밋된 baseline이 예측 파일에서 그대로 다시 나오는지
  - 문서가 코드와 어긋나지 않는지

## AI와 함께 만든 방식

이 저장소는 Claude Code와 함께 만들었다. 설계 결정은 모두 사람이 하고 이유와 함께 [결정 기록](https://github.com/cheolkim02/text2sql-eval/blob/main/docs/decisions/README.md)으로 남겼으며, 에이전트는 선택지 제시와 구현·테스트·문서 초안을 맡았다. 역할 규칙은 [AGENTS.md](https://github.com/cheolkim02/text2sql-eval/blob/main/AGENTS.md)에, 사람이 기각한 추천과 AI가 틀린 사례는 [AI와 함께 개발한 방식](https://github.com/cheolkim02/text2sql-eval/blob/main/docs/ai-workflow.md)에 있다.

## 라이선스

- 코드: [MIT](https://github.com/cheolkim02/text2sql-eval/blob/main/LICENSE)
- 예제 데이터 `examples/bird-mini`: [BIRD](https://bird-bench.github.io/) dev의 일부, [CC BY-SA 4.0](https://github.com/cheolkim02/text2sql-eval/blob/main/examples/bird-mini/LICENSE)(출처와 바꾼 점은 [SOURCE.md](https://github.com/cheolkim02/text2sql-eval/blob/main/examples/bird-mini/SOURCE.md))
