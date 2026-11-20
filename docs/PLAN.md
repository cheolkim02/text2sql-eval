# text-to-SQL 오답 분석 CLI 프로젝트 계획서

Nov 3, 2026 작성 · Nov 4, 2026 전면 개정

## 개요

text-to-SQL 연구에서 직접 겪은 **오답 분석의 병목**을 푸는 **Python 라이브러리 + CLI 저장소**를 만든다. 이름은 `text2sql-eval`이다(D1).

**한 줄 정의**

> text-to-SQL 실험 결과에서 **무엇이 틀렸는지를 AI 없이 근거와 함께 보여주고**, 판정을 믿기 어려운 케이스를 숨기지 않고, **두 실험의 차이가 진짜인지** 알려주는 분석 도구

**구조**

```text
[내 파이프라인: 언어·구조 무관]  →  predictions.jsonl  →  [text2sql-eval]  →  run.json  →  HTML 리포트 · CSV · 비교 결과
```

도구는 LLM을 부르지 않는다(D3). 파이프라인이 무엇이든(단일 프롬프트, MCTS, agentic loop, 후보 여러 개 + 선택) 최종 SQL만 예측 파일로 받는다. BIRD 공식 평가 스크립트와 같은 방식이다.

**이번 개정에서 바뀐 것 (11/3 판 대비)**

| 항목 | 11/3 판 | 11/4 판 |
| --- | --- | --- |
| 언어 | TypeScript | **Python** (D2) |
| 도구의 역할 | LLM 호출부터 채점까지 (Provider, 프롬프트, 캐시) | **예측 파일을 받아 판정·분석만** (D3) |
| 대표 기능 | 평가 파이프라인 전체, CI 게이트 | **결정적 오답 사실 추출** + 실행 비교 (D4) |
| 시연 데이터 | 합성 데이터 30\~40개 | **BIRD dev 3개 DB, 432문제** (D5) |
| 결과 화면 | 터미널 표, Markdown | **정적 HTML 리포트 + CSV** (D6) |
| 패키지 | `core`·`cli`·`llm-spec` 3개 | 패키지 1개 (`text2sql_eval`, CLI 포함) |
| 뺀 것 | — | `llm-spec`, SQL 파서 가드, LLM 어댑터·캐시·mock, `init`·`schema`·`guard`·`cases lint` (D7) |

**완료 기준 (11/14 밤)**

- [x] 깨끗한 환경에서 설치·린트·타입 검사·테스트가 성공하고, GitHub Actions CI가 녹색 → [CI](../.github/workflows/ci.yml)가 PR마다 wheel을 새 환경에 설치해 CLI까지 돌린다([ADR 0044](decisions/0044-ci-dogfooding.md)). 깨끗한 clone에서 README대로 53초([개발 기록](dev-log/2026-11-13.md))
- [x] `examples/bird-mini`에서 baseline 예측 2개(같은 모델, 설정 2종)로 `text2sql-eval eval`이 실행 파일을 만든다 → [examples/results](../examples/results/README.md)
- [x] 공식 호환 모드의 EX가 같은 예측에 대한 BIRD 공식 평가 스크립트의 EX와 일치한다(확인 결과를 문서에 기록) → 8개 숫자 일치([기록](../examples/results/README.md#bird-공식-스크립트와의-일치-2026-11-09))
- [x] 모든 오답 케이스에 "무엇이 다른가" 사실 목록과 근거가 붙는다. 사용자 분류는 CSV의 `my_category` 열로 이어 간다 (매핑 파일은 로드맵, ADR 0042) → 출력 차이 6종, SQL 구조 차이 5종([결과 읽기](guides/reading-results.md#2-차이-무엇이-다른가))
- [x] 판정 신뢰도 플래그 6개(ADR 0034)가 근거와 함께 표시된다 → [결과 읽기](guides/reading-results.md#3-판정-신뢰도-플래그)
- [x] `report`가 오프라인에서 열리는 HTML 한 파일과 엑셀에서 한글이 깨지지 않는 CSV를 만든다 → [CLI 레퍼런스](reference/cli.md#report), [예제 리포트](../examples/results/report.html)
- [x] `compare`가 분할표, 뒤집힌 케이스, 차이 분포 변화를 내고, 설정한 기준보다 나빠지면 종료 코드 1을 낸다 → [실행 비교하기](guides/comparing-runs.md), 기준은 `--max-drop`([ADR 0036](decisions/0036-compare-gate-opt-in.md))
- [x] README에 문제 정의, 설치, 3분 사용법, 실측 결과 표, AI 협업 방식이 있다 → [README](../README.md), [AI와 함께 개발한 방식](ai-workflow.md)
- [x] 결정 기록 10개 이상, 모두 결정자가 "사용자" → 48개([색인](decisions/README.md))
- [ ] 모든 모듈에 대해 설명 노트와 질문 답변을 마쳤다 → 사용자가 `/explain`으로 진행 중(`.study/`, 비공개)

## 내가 겪은 문제 (README "왜 필요한가"의 원재료)

1. **판단에 가장 오래 걸렸다.** 실행보다 오답 분석, 그리고 어디가 병목이고 무엇을 고쳐야 하는지 판단하는 데 시간이 많이 들었다. 주로 여러 설정을 계속 돌려 보며 경험적으로 찾았다.
2. **비교를 손으로 했다.** EX 점수와 틀린 문제 번호를 보고, 둘 다 틀린 문제와 각자 틀린 문제를 스크립트로 텍스트 파일에 뽑아 눈으로 보고 엑셀에 정리했다.
3. **오답 분류를 전부 수작업으로 했다.** 케이스마다 틀린 곳을 찾아 엑셀에 적고 카테고리를 붙였다. NL이나 SQL이 길면 읽기조차 힘들었다.
4. **분류를 AI에게 맡길 수 없었다.** 평가의 무결성(integrity) 때문이다. SQL 생성과 오답 분석은 다른 태스크지만, LLM 분류에도 오류가 생긴다. 물론 사람도 100% 정확하지 않다.
5. **카테고리가 연구마다 다르다.** 합의된 오답 분류 체계가 없다.
6. **EX 판정 자체가 틀린다.** 학계에서도 계속 논문이 나오는 문제다.
   - 거짓 정답: 정답 SQL의 결과가 빈 집합이면 빈 결과를 내는 모든 SQL이 정답이 된다. 정답이 집계 숫자 하나면, 우연히 그 숫자를 내는 잘못된 SQL도 정답이 된다.
   - 거짓 오답: "사람 이름을 출력하라"는 질문에 정답 SQL과 다른 형식(컬럼 구성)으로 이름을 내면, 내용상 맞아도 틀린 것으로 처리된다.
7. **재현이 어려웠다.** 스크립트 옵션으로 프롬프트 버전을 표시하고, Weights & Biases의 실행 명령을 보며 어떤 설정이 가장 좋았는지 찾았다.

겪지 않은 것: 위험한 SQL(DELETE, DROP 등) 생성, rate limit, 실행 중 중단. 그래서 이번 범위에서 SQL 가드, 응답 캐시, 이어서 돌리기는 뺀다.

## 핵심 기능

### ① 결정적 오답 사실 추출 (대표 기능)

정답 SQL과 예측 SQL을 파싱·정규화한 뒤 비교해, **"무엇이 다른가"를 사실로만** 보고한다. AI를 쓰지 않으므로 같은 입력에는 항상 같은 결과가 나오고, 모든 사실에 근거(어느 절의 무엇이 어떻게 다른가)가 붙는다.

- **실행 수준 사실:** 문법 오류, 없는 테이블·컬럼, 시간 초과, 빈 결과, 행 수 다름, 컬럼 수 다름, 값 다름
- **구조 수준 사실 (초안):** 사용한 테이블 집합, JOIN 구성, WHERE 조건(컬럼·연산자·값), 집계 함수, GROUP BY, ORDER BY·LIMIT, SELECT 컬럼, DISTINCT, 서브쿼리·집합 연산
- **해석은 사용자 몫:** "왜 틀렸나" 카테고리는 매핑 파일로 사용자가 정한다(예: `where.value_mismatch → 값 연결 오류`). 합의된 체계가 없다는 문제를 도구가 카테고리를 강요하지 않는 방식으로 피한다.
- **가장 어려운 부분:** 구조가 달라도 결과가 같은 올바른 SQL이 많다(별칭, 조인 순서, 서브쿼리 ↔ 조인, `IN` ↔ `EXISTS` 등). 정규화로 가짜 차이를 줄이고, 정답 판정된 케이스에서는 구조 차이를 오답 사실로 보고하지 않는다. 규칙은 실제 오답 케이스를 보면서 11/7 설계 세션에서 정한다(D18).

### ② 판정 신뢰도 플래그

판정을 바꾸지 않고, **믿기 어려운 판정을 근거와 함께 표시**한다.

- 거짓 정답 의심: 정답 결과가 빈 집합, 정답 결과가 값 하나(1×1)인데 예측 SQL 구조가 크게 다름
- 거짓 오답 의심: 예측 결과가 정답 컬럼을 모두 포함하고 컬럼만 더 있음, 값은 같은데 컬럼 순서·형식만 다름
- 최종 목록은 ADR 0034의 6개다(0012의 필수 2개를 대체).

### ③ 실행 비교 (부대표 기능)

엑셀 작업을 대체한다.

- 분할표: 둘 다 맞음 / A만 맞음 / B만 맞음 / 둘 다 틀림, 칸마다 케이스 목록
- 사실 분포 변화 (예: "WHERE 값 오류는 줄고 JOIN 누락은 늘었다")
- DB별·난이도별 분해 (BIRD의 `difficulty` 필드)
- 실행 조건(데이터셋 해시, 판정 모드)이 다르면 경고
- 기준보다 나빠지면 종료 코드 1 (CI에서도 쓸 수 있음. 주 용도는 로컬 실험 비교)

### ④ 결과 화면: HTML 리포트와 CSV

NL과 SQL이 길면 읽기 힘들다는 불편을 직접 겨냥한다.

- **정적 HTML 리포트 (파일 하나, 서버 없음, 오프라인):** 오답 목록 필터(DB, 난이도, 사실, 플래그), 케이스마다 질문·evidence, 자동 정렬된 정답·예측 SQL을 나란히 놓고 다른 절을 강조, 결과 표 차이를 행 단위로 표시
- **CSV:** 기존 엑셀 분석 흐름을 그대로 쓰되 사실·플래그 열이 미리 채워져 있고, 빈 `my_category`·`notes` 열을 둔다. 엑셀에서 한글이 깨지지 않게 UTF-8 BOM으로 저장한다.

## 기능 범위

SQLite 실행만 지원하고(BIRD·Spider의 DB가 SQLite), 위 핵심 기능을 제품 수준으로 만드는 것이 1순위다. 파서는 방언을 인식하게 두되 실행 백엔드는 SQLite 하나만 구현한다.

**필수 (11/14까지)**

- 데이터셋 로더: BIRD 형식(`question_id`, `db_id`, `question`, `evidence`, `SQL`, `difficulty`)과 자체 JSONL 형식, 오류에 위치 표시
- 예측 파일 로더: 한 줄 한 SQL 텍스트와 자체 JSONL(ADR 0018), 개수·누락·중복 `id` 검사
- 실행기: 읽기 전용 연결, 시간 제한, 병렬 실행
- EX 판정: BIRD 공식과 똑같은 집합 비교(ADR 0022), 빈 예측·동점 대체 정답은 플래그(ADR 0023, 0024)
- 사실 추출 ①, 신뢰도 플래그 ② (카테고리 매핑 파일은 로드맵, ADR 0042)
- 실행 파일(JSON): 스키마 버전, 도구 버전, 데이터셋 해시, 판정 모드, 사용자 메타데이터, 케이스별 결과
- 비교 ③, HTML 리포트·CSV ④
- CLI: `eval`, `report`, `compare`
- `examples/bird-mini`: BIRD dev 3개 DB와 문제 432개, 별도 라이선스 파일
- `examples/baseline`: OpenAI 단일 프롬프트 baseline(Python), 예측 파일 2개와 실행 파일을 `examples/results/`에 커밋
- CI, README, 가이드, `AGENTS.md`, 결정 기록

**권장 (시간이 남으면 이 순서로)**

1. 신뢰도 플래그 나머지 (거짓 오답 의심 등)
2. ~~CI 도그푸딩 단계~~ 완료 (ADR 0044)
3. Stop 훅과 `scripts/check_decisions.py` (ADR 0012로 필수에서 내림)
4. `compare`의 HTML 출력
5. BIRD 공식 예측 형식(`{"0": "SQL\t----- bird -----\tdb_id"}`) 입력 지원
6. 패키지 검사 도구 CI 단계, PyPI 배포, CHANGELOG
7. 공개 API 레퍼런스 자동 생성

**로드맵 (README에만 적고 이번에 하지 않음)**

- PostgreSQL·MySQL 실행 백엔드 (BIRD Mini-Dev는 같은 질문을 SQLite·MySQL·PostgreSQL로 제공)
- 엄격 판정 모드: 행 순서, 중복 행, 실수 오차까지 따지는 판정 (ADR 0022)
- 실행 비교의 통계 검정, 예: McNemar (ADR 0035)
- 파이프라인 단계별 추적 (예: 스키마 선택 단계의 테이블 재현율)
- 사람 라벨과 자동 사실의 일치도 측정
- 후보 coverage와 선택 손실 지표
- **beta: 결과 파일을 LLM이 읽고 분석을 제안하는 기능** (사실 추출은 결정적으로 유지하고, LLM은 그 위에서 요약만)
- 합성 예제 데이터셋
- Weights & Biases 등 실험 추적 도구 연동
- 사용자 카테고리 매핑 파일 `--categories` (ADR 0042)

**이번에 하지 않음**

- LLM 호출, 프롬프트 관리, 응답 캐시 (D3)
- SQL 파서 기반 가드 (읽기 전용 연결과 시간 제한으로 대신함)
- `llm-spec`, 웹 서버, 대시보드

**범위 축소 규칙**

11/7에 3일 지연을 반영해 일정과 범위를 한 번 조정했다(ADR 0012). 아래는 그 뒤의 점검 규칙이다.

- 11/9 밤에 `eval`이 실행 파일을 만들지 못하거나 사실 추출 1차가 돌지 않으면: HTML의 결과 표 차이 표시를 빼고, 구조 수준 사실을 테이블·JOIN·WHERE·집계·SELECT 다섯 종류로 줄인다.
- 11/11 밤에 `compare`가 끝나지 않으면: 사실 분포 변화와 DB별 분해를 빼고 분할표·뒤집힌 케이스만 남긴다.
- 11/12 밤에 HTML 리포트가 끝나지 않으면: SQL 나란히 보기와 필터만 남기고 결과 표 차이를 뺀다. CSV는 줄이지 않는다.
- 줄이지 않는 것: 테스트, CI, README, 결정 기록, 학습 노트, 사실의 근거 표시.

## 데이터

### 시연 데이터: `examples/bird-mini` (D5)

BIRD dev(2024-06-27 판)에서 작은 DB 3개의 문제를 **전부** 쓴다. dev 전체 1,534문제, DB 11개 중에서 저장소에 넣을 수 있는 크기만 골랐다. 큰 DB(`card_games` 261.8MB, `european_football_2` 597.8MB 등)는 넣지 않고, 전체 dev가 필요한 사용자를 위해 다운로드 스크립트를 둔다.

| DB | 크기 | 문제 수 | simple / moderate / challenging |
| --- | --- | --- | --- |
| `superhero` | 0.2MB | 129 | 81 / 33 / 15 |
| `student_club` | 2.6MB | 158 | 101 / 48 / 9 |
| `toxicology` | 2.7MB | 145 | 76 / 38 / 31 |
| 합계 | 약 5.5MB | **432** | 258 / 119 / 55 |

**라이선스:** BIRD 팀은 데이터 라이선스를 CC BY-SA 4.0으로 공지했고, 원 논문은 원본 DB들이 퍼블릭 도메인·CC-BY·CC-BY-SA 중 하나라고 밝힌다. 코드는 MIT로 두고, `examples/bird-mini/LICENSE`에 CC BY-SA 4.0 전문, `SOURCE.md`에 출처(논문, 사이트, 다운로드 URL, 판 날짜, 고른 DB와 이유)를 적는다. 데이터를 바꾸면 그 사실도 `SOURCE.md`에 남긴다.

### 데이터셋 형식 (자체 JSONL, 한 줄에 케이스 하나)

BIRD 형식을 그대로 읽을 수 있고, 다른 데이터셋은 아래 형식으로 맞춘다.

```json
{"id":"superhero-718","db_id":"superhero","question":"...","evidence":"...","gold_sql":"SELECT ...","difficulty":"simple","tags":[]}
```

### 예측 파일 형식 (D27, ADR 0018)

두 형식을 받는다.

**한 줄 한 SQL 텍스트 파일.** N번째 줄이 데이터셋 N번째 케이스의 예측이다. 줄 수가 케이스 수와 다르면 오류이고, 빈 줄은 빈 예측으로 센다.

```text
SELECT T2.power_name FROM hero_power AS T1 INNER JOIN superpower AS T2 ON ...
SELECT COUNT(*) FROM superhero WHERE ...
```

**자체 JSONL.** 한 줄에 JSON 객체 하나다. `id`·`sql`은 필수이고 `meta`는 선택이다. `id`가 데이터셋에 없거나 중복되면 줄 번호와 함께 오류를 낸다.

```json
{"id":718,"sql":"SELECT ...","meta":{"latency_ms":1830}}
```

실행 전체의 메타데이터(모델, 프롬프트 버전, 커밋 등)는 `eval --meta key=value` 또는 `--meta-file`로 넣고 실행 파일에 그대로 남긴다. 연구 때 스크립트 옵션과 W&B로 하던 기록을 결과 파일 안에 함께 두기 위함이다.

### baseline (`examples/baseline`, D24)

OpenAI API로 단일 프롬프트 baseline을 만든다. 도구 본체와 분리된 예제 코드이고, 도구가 어떤 파이프라인이든 받는다는 것을 보여 준다. 비교 구성 추천은 **같은 모델로 evidence를 줄 때 vs 안 줄 때**다(비용이 적고 결과 차이가 의미 있다). 실행 전 호출 수(432 × 구성 수)와 예상 비용을 확인하고, 결과는 `examples/results/`에 커밋해 누구나 API 키 없이 리포트를 재생성할 수 있게 한다.

## 명령어 설계

CLI는 라이브러리를 얇게 감싼 것이다. 모든 로직은 라이브러리에 있고, CLI는 옵션 해석과 출력만 한다.

### 평가 흐름

1. 데이터셋과 예측 파일을 읽고 `id`를 맞춘다(누락·중복은 오류).
2. 정답 SQL과 예측 SQL을 읽기 전용 연결에서 시간 제한을 두고 실행한다.
3. 결과를 판정 모드에 따라 비교해 `correct` / `incorrect` / `error`를 정한다.
4. 오답·오류 케이스에서 사실을 추출하고, 모든 케이스에 신뢰도 플래그 규칙을 적용한다.
5. (로드맵, ADR 0042) 카테고리 매핑 파일이 있으면 사실에 사용자 카테고리를 붙인다.
6. 실행 파일(JSON)로 저장한다. `report`가 읽고, `compare`가 두 실행 파일을 비교한다.

### CLI 명령어 (초안)

```text
text2sql-eval eval                       예측 파일을 판정하고 실행 파일을 만든다
  --dataset <path>                  BIRD JSON 또는 자체 JSONL
  --db-dir <dir>                    <db_id>/<db_id>.sqlite 구조
  --pred <predictions.jsonl>
  --out <run.json>
  --categories <map.toml>           사실 → 내 카테고리 매핑 (로드맵, ADR 0042)
  --timeout <sec> --workers <n>
  --meta key=value ... | --meta-file <path>
  --json                            요약을 stdout에 JSON으로

text2sql-eval report <run.json>
  --html <out.html>                 오프라인 HTML 리포트
  --csv <out.csv>                   엑셀용 CSV (UTF-8 BOM)
  --by <db|difficulty|fact|flag>    터미널 요약의 그룹 기준
  --json

text2sql-eval compare <base.json> <head.json>
  --max-drop <pp>                   허용하는 EX 하락폭(%p), 넘으면 종료 코드 1
  --csv <out.csv>                   뒤집힌 케이스 목록
  --html <out.html>                 (권장)
  --json
```

### 종료 코드

| 코드 | 의미 | 예 |
| --- | --- | --- |
| 0 | 성공 | 판정 완료, 비교 기준 통과 |
| 1 | 판정 실패 | `compare`에서 기준보다 나빠짐 |
| 2 | 사용법·입력 오류 | 잘못된 옵션, 파일 없음, 형식 검증 실패, `id` 누락·중복 |
| 3 | 실행 환경 오류 | DB 파일 열기 실패, 권한 |
| 130 | 사용자 중단 | Ctrl-C |

오류 메시지는 무엇이 잘못됐는지, 어떻게 고치는지 두 줄로 쓴다. 예: `예측 파일에 없는 케이스가 12개 있습니다 (superhero-718 외 11개). --allow-missing으로 빈 예측을 오답 처리할 수 있습니다.`

### 라이브러리 공개 API (초안)

```python
def load_dataset(path: Path) -> Dataset: ...
def load_predictions(path: Path) -> Predictions: ...
def evaluate(
    dataset: Dataset, predictions: Predictions, *, db_dir: Path, options: EvalOptions
) -> RunResult: ...
def extract_facts(
    gold_sql: str, pred_sql: str, *, dialect: str = "sqlite"
) -> list[Fact]: ...
def compare_runs(base: RunResult, head: RunResult) -> Comparison: ...
def write_html_report(run: RunResult, path: Path) -> None: ...
def write_csv(run: RunResult, path: Path) -> None: ...


@dataclass(frozen=True)
class Correct:
    status: Literal["correct"]
    case_id: str
    flags: tuple[Flag, ...]


@dataclass(frozen=True)
class Incorrect:
    status: Literal["incorrect"]
    case_id: str
    facts: tuple[Fact, ...]
    flags: tuple[Flag, ...]


@dataclass(frozen=True)
class ExecError:
    status: Literal["error"]
    case_id: str
    kind: Literal["syntax", "unknown_identifier", "timeout", "runtime"]
    message: str


CaseResult = Correct | Incorrect | ExecError


@dataclass(frozen=True)
class Fact:
    kind: str  # 예: "where.value_mismatch"
    clause: str  # 예: "WHERE"
    gold: str  # 근거: 정답 쪽 조각
    pred: str  # 근거: 예측 쪽 조각
```

데이터 모델 방식(dataclass 또는 다른 것)은 D13에서 정한다. 실행 파일에는 `schema_version`을 넣고, 형식이 바뀌면 올린다.

## 폴더 구조

패키지 하나, `src` 레이아웃이다. 의존 방향은 `cli → report·compare → judge·facts → execution·datasets` 한 방향이다.

```text
text2sql-eval/
├─ AGENTS.md                  에이전트 규칙 (사람도 읽는 협업 규약)
├─ CLAUDE.md                  @AGENTS.md 를 불러오고 Claude Code 전용 규칙만 추가
├─ README.md
├─ CONTRIBUTING.md            개발 환경, 명령어, 커밋 규칙
├─ LICENSE                    MIT (코드)
├─ CHANGELOG.md               (선택)
├─ pyproject.toml             메타데이터, 의존성, 린트·타입 검사·테스트 설정
├─ <잠금 파일>                 D9에서 정한 도구의 잠금 파일
├─ .github/workflows/ci.yml   린트 → 포맷 검사 → 타입 검사 → 테스트(버전 매트릭스) → 빌드 → (권장) 도그푸딩
├─ .claude/
│  ├─ settings.json           훅 설정 (결정 기록 누락 검사)
│  └─ skills/
│     ├─ decide/SKILL.md      설계 결정 제시 → 사용자 선택 → ADR 기록
│     ├─ explain/SKILL.md     코드 설명 + 확인 질문
│     ├─ review/SKILL.md      AI가 쓴 코드 자가 검토 체크리스트
│     └─ devlog/SKILL.md      하루 마무리 기록
├─ scripts/
│  └─ check_decisions.py      훅이 호출: 의존성·설정·공개 API·형식 변경에 ADR이 있는지 검사
├─ src/text2sql_eval/
│  ├─ __init__.py             공개 API만 내보냄 (여기에 없으면 비공개)
│  ├─ py.typed
│  ├─ datasets/               BIRD·JSONL 데이터셋 로더, 예측 파일 로더
│  ├─ execution/              읽기 전용 실행, 시간 제한, 병렬 실행
│  ├─ judge/                  EX 판정(모드별), 신뢰도 플래그
│  ├─ facts/                  SQL 파싱·정규화, 구조 비교, 사실 생성 (대표 기능)
│  ├─ categories/             사실 → 사용자 카테고리 매핑 (로드맵, ADR 0042)
│  ├─ compare/                실행 비교
│  ├─ report/                 HTML(단일 파일), CSV, 터미널 요약
│  ├─ runfile.py              실행 파일 스키마와 버전
│  ├─ errors.py               오류 타입 정의
│  └─ cli/                    진입점, eval·report·compare 명령, 종료 코드
├─ tests/
│  ├─ unit/                   모듈별 단위 테스트
│  ├─ property/               속성 기반 테스트 (정규화, 판정 규칙)
│  ├─ integration/            실제 SQLite로 eval → report → compare
│  ├─ cli/                    실제 프로세스로 실행하는 e2e 테스트
│  └─ fixtures/               작은 DB, 케이스, 예측, 스냅샷
├─ examples/
│  ├─ bird-mini/              data(문제 JSON, sqlite 3개), LICENSE(CC BY-SA 4.0), SOURCE.md, download_full_dev.py
│  ├─ baseline/               OpenAI 단일 프롬프트 baseline, README
│  ├─ categories.example.toml 카테고리 매핑 예시 (로드맵, ADR 0042)
│  └─ results/                예측 파일 2개, 실행 파일, report.html (공개 실측)
├─ docs/
│  ├─ PLAN.md                 이 문서
│  ├─ ai-workflow.md          AI와 어떻게 개발했는지
│  ├─ architecture.md         모듈 경계와 데이터 흐름
│  ├─ decisions/              0000-template.md, README.md(색인), 0001-… 
│  ├─ dev-log/                날짜별 개발 기록
│  ├─ images/                 README·가이드용 스크린샷 (ADR 0045)
│  ├─ guides/                 (ADR 0012로 6개에서 4개로 줄임)
│  │  ├─ getting-started.md   3분 시작
│  │  ├─ prediction-format.md 내 파이프라인 결과를 예측 파일로 만들기
│  │  ├─ reading-results.md   사실·근거·정규화 규칙, 신뢰도 플래그, CSV로 손 분류하기
│  │  └─ comparing-runs.md    비교 결과 읽는 법
│  └─ reference/
│     ├─ cli.md
│     ├─ api.md
│     └─ run-file.md          실행 파일 형식
└─ .study/                    gitignore: 학습 노트와 질문 답변 (공개하지 않음)
```

## 내가 내릴 결정

모두 내가 정한다. Claude는 선택지와 장단점을 제시하고, 내가 고르면 ADR로 기록한다. "추천"은 출발점일 뿐이고, 도구 버전·유지보수 상태는 결정 직전에 공식 문서로 다시 확인한다. D1\~D7은 11/3\~4 대화에서 이미 정했으므로 첫 세션에서 묻지 않고 ADR만 쓴다.

**이미 정한 것**

| ID | 결정 | 내용 | 날짜 |
| --- | --- | --- | --- |
| D1 | 이름 | `text2sql-eval` (PyPI 이름 비어 있음 11/4 확인, import 이름 `text2sql_eval`, CLI 명령어도 `text2sql-eval`) | 11/3 |
| D2 | 언어 | Python. 이유: 대표 기능의 핵심인 SQL 파싱·정규화 생태계, 익숙한 언어여야 깊이와 설명 가능성 확보, 사용자(text-to-SQL 연구자)가 Python을 씀 | 11/4 |
| D3 | 구조 | 예측 파일을 입력으로 받고 도구는 LLM을 부르지 않는다 | 11/4 |
| D4 | 기능 우선순위 | 대표: 결정적 사실 추출, 부대표: 실행 비교. 후보 coverage는 제외(구현이 쉽고, multi-candidate가 필수 요소가 아님) | 11/4 |
| D5 | 시연 데이터 | BIRD dev `superhero`·`student_club`·`toxicology` 432문제를 저장소에 포함, CC BY-SA 4.0 별도 표기 | 11/4 |
| D6 | 결과 화면 | 정적 HTML 리포트 + CSV (터미널은 요약만) | 11/4 |
| D7 | 범위 밖 | 합성 예제 데이터, LLM 분석 beta는 로드맵. `llm-spec`, SQL 가드, LLM 호출은 뺀다 | 11/4 |

**앞으로 정할 것**

| ID | 결정 | 선택지 | 추천 (출발점) | 시점 |
| --- | --- | --- | --- | --- |
| D8 | 지원 Python 버전 | 3.10+ / 3.11+ / 3.12+ | **결정됨: 3.11+ (ADR 0009)** | 11/7 |
| D9 | 프로젝트 관리·빌드 백엔드 | uv / Poetry / pip + hatch | **결정됨: uv + uv_build (ADR 0010)** | 11/7 |
| D10 | 린트·포맷 | Ruff / flake8 + black + isort | **결정됨: Ruff 하나 (ADR 0011)** | 11/7 |
| D11 | 타입 검사 | pyright strict / mypy strict / 둘 다 | **결정됨: pyright strict + 규칙 1개 (ADR 0013)** | 11/7 |
| D12 | 테스트 | pytest / unittest, 속성 기반(Hypothesis), 스냅샷 방식 | **결정됨: pytest + Hypothesis + syrupy (ADR 0014)** | 11/7 |
| D13 | 데이터 모델·입력 검증 | dataclass + 직접 검증 / pydantic / msgspec | **결정됨: dataclass + 직접 검증 (ADR 0019)** | 11/8 |
| D14 | CLI 프레임워크 | argparse / click / typer | **결정됨: argparse (ADR 0025)** | 11/8 |
| D15 | SQL 파서 | sqlglot / sqlparse / 직접 | **결정됨: sqlglot (ADR 0032)** | 11/9 |
| D16 | EX 판정 규칙 | BIRD 공식 호환(행 집합 비교로 알려짐) / 엄격(순서·중복·컬럼 이름) / 둘 다 | **결정됨: 공식과 똑같은 집합 비교 하나만 (ADR 0022)** | 11/8 |
| D17 | 시간 제한 구현 | `sqlite3` 진행 콜백 / 별도 프로세스 | **결정됨: 진행 콜백 + 스레드 병렬 (ADR 0020)** | 11/8 |
| D18 | 사실 목록과 정규화 규칙 | 실제 오답 케이스를 보며 정함 | **결정됨: 다중 라벨 출력 차이 6개 + SQL 구조 차이 5종 (ADR 0031, 0033)** | 11/9 |
| D19 | 신뢰도 플래그 목록 | 빈 결과, 값 하나, 컬럼 상위집합, 형식 차이 등 | **결정됨: 6개 (거짓 정답 의심 2, 거짓 오답 의심 3, 정보 1) (ADR 0034)** | 11/9 |
| D20 | 카테고리 매핑 파일 형식 | TOML / YAML / JSON | **결정됨: 로드맵으로 미룸, 손 분류는 CSV `my_category` (ADR 0042)** | 11/8 |
| D21 | HTML 리포트 구현 | Jinja2 / 표준 라이브러리 템플릿, CSS·JS 인라인 | **결정됨: Jinja2, 자동 이스케이프 (ADR 0038)** | 11/11 |
| D22 | 통계 검정 | McNemar 정확 검정 직접 구현 / scipy | **결정됨: 넣지 않음 (ADR 0035, Claude 추천 기각)** | 11/10 |
| D23 | 문서 도구 | Markdown만 / MkDocs + API 자동 생성 | **결정됨: Markdown만, `api.md`는 테스트로 코드와 맞춤 (ADR 0041)** | 11/13 |
| D24 | baseline 구성 | 모델, evidence 있음/없음 vs 프롬프트 2종 | **결정됨: 같은 모델 × evidence 있음/없음 (ADR 0028)** | 11/9 |
| D25 | 문서 언어 | 한국어 / 영어 / 한국어 + 영어 요약 | **결정됨: README 한국어 + 영어 요약, 코드·커밋·docstring 영어 (ADR 0016)** | 11/7 |
| D26 | 커밋 규칙과 AI 표시 | Conventional Commits 여부, `Co-Authored-By` 여부 | **결정됨: 둘 다 사용 (ADR 0017)** | 11/7 |
| D27 | 예측 파일 형식 | 자체 JSONL / BIRD 공식 형식 / 둘 다 | **결정됨: 한 줄 한 SQL 텍스트 + 자체 JSONL (ADR 0018)** | 11/8 |
| D28 | Ruff 규칙 세트 | 기본 / 넓게 고른 세트 / 전부 켜고 일부 끄기 | **결정됨: 기본 규칙, 88자 (ADR 0015, Claude 추천 기각)** | 11/7 |
| D29 | 빈 예측 처리 | 공식과 동일 / 항상 오답 / 공식과 동일 + 플래그 | **결정됨: 공식과 동일 + 플래그 (ADR 0023)** | 11/8 |
| D30 | 동점 대체 정답 처리 | 무시 / 둘 중 하나와 맞으면 정답 / 원래 정답 + 플래그 | **결정됨: 원래 정답으로 판정 + 플래그 (ADR 0024)** | 11/8 |
| D31 | 실행 파일 형식 | JSON 하나 / JSONL / 파일 두 개 | **결정됨: JSON 하나 (ADR 0026)** | 11/9 |
| D32 | 예측 파일 형식 판별 | 확장자 + 덮어쓰기 / 옵션 필수 / 내용 추측 | **결정됨: 확장자 + `--pred-format` (ADR 0027)** | 11/9 |
| D33 | baseline 모델 | gpt-6.1-sol / gpt-5.4-mini / gpt-5-mini / 기타 | **결정됨: gpt-4o-mini, 2027-01-14 종료 예정 (ADR 0030, Claude 추천 기각)** | 11/9 |
| D34 | baseline API 호출 방식 | 공식 SDK(examples 그룹) / urllib | **결정됨: 공식 SDK, examples 그룹 (ADR 0029)** | 11/9 |
| D35 | compare 실패 기준 | 기본 실패 없음 + `--max-drop` / 기본 0 | **결정됨: 기본 실패 없음, `--max-drop`으로 켬 (ADR 0036)** | 11/11 |
| D36 | 데이터셋이 다른 두 실행 비교 | 경고 + 공통 케이스 / 오류 | **결정됨: 경고 + 공통 케이스 (ADR 0037)** | 11/11 |
| D37 | HTML 리포트 범위 | 기본 / 기본 + 강조 / 기본 + `compare` HTML | **결정됨: 기본 + 다른 절·행 강조 (ADR 0039, Claude 추천 기각)** | 11/11 |
| D38 | CSV 수식 주입 대응 | 그대로 두고 문서에 경고 / 위험한 첫 글자 앞에 `'` / 위험한 첫 글자 앞에 탭 | **결정됨: 위험한 첫 글자 앞에 `'` (ADR 0040)** | 11/11 |
| D39 | 공개 API 범위 (`__init__.py`에서 내보낼 것) | CLI 흐름의 함수와 결과 타입 / CLI와 실행 파일 형식만 / 모듈 전부 | **결정됨: CLI 흐름의 함수와 결과 타입 (ADR 0043)** | 11/12 |
| D40 | CI 도그푸딩 | 넣음 / 넣지 않음 | **결정됨: wheel을 새 환경에 설치해 `eval → report` 실행 (ADR 0044)** | 11/12 |
| D41 | 문서용 이미지 위치 | `docs/images/` / `examples/results/` / 외부 URL | **결정됨: `docs/images/` (ADR 0045)** | 11/14 |
| D42 | PyPI 배포 | 배포하지 않음 / 태그 push 시 GitHub Actions + Trusted Publishing / 로컬에서 토큰으로 수동 | **결정됨: 태그 push 시 GitHub Actions + Trusted Publishing, 저장소 공개 후 첫 배포 (ADR 0046)** | 11/14 |
| D43 | 공개 전 개인 정보 | 그대로 / 현재 파일에서 지움 / 기록까지 지움 | **결정됨: 현재 파일에서 프로젝트와 무관한 것 모두 지움 (ADR 0047)** | 11/15 |
| D44 | ADR 이유 작성 방식 | 평서문으로 쓰고 규칙도 바꿈 / 규칙 유지(인용) / 평서문 + 사용자 확인 | **결정됨: 대화를 인용하지 않고 평서문으로 씀 (ADR 0048)** | 11/16 |
| D45 | ponytail 도입 방식 | skill 파일 복사 / 규칙을 AGENTS.md에 녹임 / 플러그인으로만 설치 | **결정됨: skill 파일 3개를 `.claude/skills/`에 복사 (ADR 0049)** | 11/20 |
| D46 | ponytail과 우리 규칙의 관계 | 항상 적용 + AGENTS.md 우선 / 부를 때만 적용 / 원본 그대로 | **결정됨: 항상 적용, AGENTS.md 우선, 보고는 한국어 (ADR 0050)** | 11/20 |
| D47 | 행 수 제한 기본값 | 1,000,000행 / 100,000행 / 제한 없음 유지 | **결정됨: 기본 1,000,000행 (ADR 0051)** | 11/20 |
| D48 | syrupy | 뺌 / 실제로 씀 / 문서만 고침 | **결정됨: 개발 의존성과 문서에서 뺌 (ADR 0052)** | 11/20 |

라이선스는 코드 MIT, 예제 데이터 CC BY-SA 4.0으로 정하고 0001번 ADR에 함께 적는다. 이 목록에 없는 결정이 나오면 Claude가 D44부터 새 번호를 붙여 물어본다.

## AI 협업 규칙

나는 설계·결정·리뷰를 하고, Claude는 선택지 제시·구현·테스트·문서 초안·기록을 한다. 결정 기록은 세 겹으로 자동화한다. 규칙만으로는 빠뜨릴 수 있어서, 훅으로 누락을 한 번 더 잡는다.

### 결정 기록 자동화

1. **규칙 (`AGENTS.md`, `CLAUDE.md`):** Claude Code는 세션을 시작할 때 프로젝트의 `CLAUDE.md`를 읽고, `CLAUDE.md` 안의 `@AGENTS.md` 줄은 그 파일을 함께 불러온다([공식 문서](https://code.claude.com/docs/en/memory.md)). 여기에 "결정이 필요한 순간 멈추고 물어본 뒤, 답을 받으면 즉시 ADR을 쓴다"는 규칙을 둔다.
2. **스킬 (`.claude/skills/decide/SKILL.md`):** 설계 결정이 생기면 Claude가 스스로 불러 쓰고, 내가 `/decide <주제>`로 직접 부를 수도 있다. 스킬의 `description`이 자동 호출 여부를 정한다([공식 문서](https://code.claude.com/docs/en/skills.md)).
   - 순서: 결정 주제와 맥락 한 단락 → 선택지 2\~4개를 장단점 표로 → Claude의 추천과 이유 → 내 답을 기다림 → 답을 받으면 `docs/decisions/NNNN-<slug>.md` 작성 → `docs/decisions/README.md` 색인 갱신 → 파일 경로를 한 줄로 알림
3. **훅 (`.claude/settings.json` → `scripts/check_decisions.py`, ADR 0012로 권장 범위):** Claude가 응답을 끝낼 때마다 도는 `Stop` 훅이다. 작업 트리에 아래 변경이 있는데 `docs/decisions/`에 새 파일이나 수정이 없으면, 종료 코드 2와 안내 문구를 내서 Claude가 멈추지 않고 결정을 물어보게 한다([공식 훅 가이드](https://code.claude.com/docs/en/hooks-guide.md)).
   - 감시 대상: `pyproject.toml`(의존성과 도구 설정), 잠금 파일, `src/text2sql_eval/__init__.py`(공개 API), `.github/workflows/*`, 데이터셋·예측·실행 파일 형식 정의, 카테고리 매핑 형식
   - 무한 반복 방지: 훅 입력의 `stop_hook_active` 값을 확인해 이미 한 번 막았으면 통과시킨다. 필드 이름과 동작은 설정 전에 공식 훅 레퍼런스에서 다시 확인한다.
   - 예외: docstring만 고친 경우처럼 내가 "ADR 불필요"라고 답한 변경은 Claude가 `docs/decisions/skipped.md`에 날짜·파일·이유를 한 줄 남긴다. 이것도 `docs/decisions/` 아래 변경이라 훅을 통과하고, 생략한 기록까지 남는다.

### ADR 템플릿 (`docs/decisions/0000-template.md`)

```markdown
# NNNN. <결정 제목>

- 날짜: YYYY-MM-DD
- 상태: 채택 | 대체됨(NNNN) | 폐기
- 결정자: 사용자
- AI 관여: 선택지 조사·추천 (Claude 추천: <안>, 채택 여부: 예/아니오)
- 관련 결정 ID: D<n>

## 맥락
무엇을 왜 정해야 했는지 2~3문장.

## 선택지
| 안 | 장점 | 단점 |
| --- | --- | --- |

## 결정
고른 안 한 문장.

## 이유
사용자가 밝힌 이유를 평서문으로 쓰고(대화를 인용하지 않음), 필요하면 보충. 이유 없이 추천을 따랐으면 "추천안(<안>)을 채택했다".

## 결과
이 결정으로 생기는 제약, 후속 작업, 다시 볼 조건.
```

### Claude가 혼자 정해도 되는 것

내부 함수 이름, 파일 안 코드 배치, 테스트 케이스 구성처럼 밖에서 보이지 않는 것만 정한다. 대신 커밋 메시지 본문에 남긴다. 공개 API, 의존성, 설정, 데이터·실행 파일 형식, 판정·사실 규칙, 폴더 구조를 바꾸는 것은 전부 내 결정이다.

### 작업 단위와 커밋

1. Claude가 기능 하나의 계획을 3\~5줄로 제시하고 내가 승인한다.
2. 테스트를 먼저 또는 함께 쓴다. 오류 경로 테스트를 빠뜨리지 않는다.
3. 구현 후 `check`(린트 + 포맷 검사 + 타입 검사 + 테스트, 실행 방법은 D9)를 통과시킨다.
4. Claude가 `review` 스킬의 체크리스트로 자가 검토하고 고친 점을 보고한다.
5. 내가 diff를 읽고, `/explain`으로 모르는 부분을 풀고, 승인한다.
6. Claude가 Conventional Commits 형식으로 커밋한다. 내 승인 없이 커밋·푸시하지 않는다. AI 표시 방식은 D26을 따른다.

**자가 검토 체크리스트 (`review` 스킬)**

- [ ] 공개 API에 `Any`가 없고, 근거 없는 `cast`·`# type: ignore`가 없다
- [ ] 판별 유니언을 다루는 분기에 `assert_never` 전수 검사가 있다
- [ ] 공개 함수에 docstring과 사용 예시가 있다
- [ ] 실패 경로에 테스트가 있다
- [ ] 새 의존성에는 ADR이 있다
- [ ] 쓰이지 않는 추상화·옵션·코드가 없다
- [ ] 주석은 "무엇"이 아니라 "왜"를 설명한다
- [ ] 오류 메시지가 고칠 방법을 말해 준다
- [ ] 사실 추출·판정에 비결정적 요소(무작위, 시간, 순서 없는 집합 순회 결과 노출)가 없다

### 모든 줄을 설명하기 위한 학습 체계

- **`/explain <파일 또는 모듈>`:** Claude가 구조와 선택 이유, 버린 대안을 설명하고 확인 질문 5개를 낸다. 내가 답하면 채점하고 부족한 부분을 보충한다. 문답은 `.study/<모듈>.md`에 저장(공개하지 않음).
- **`/devlog`:** 하루 끝에 `docs/dev-log/YYYY-MM-DD.md`를 쓴다. 한 일, 내린 결정(ADR 링크), **AI가 틀린 것과 내가 고친 것**, 내일 할 일.
- "AI가 틀린 것" 기록은 "AI를 어떻게 통제했나"를 설명하는 가장 구체적인 자료가 된다. 이 프로젝트의 주제(평가를 AI에 맡길 때의 무결성)와도 이어진다.
- 마지막 날 `docs/ai-workflow.md`에 정리한다: 작업 방식, ADR 수, Claude 추천을 기각한 결정 수, AI 코드를 고친 대표 사례 3개.

## 일별 일정

11/7에 일정을 다시 짰다(ADR 0012). 11/7부터 하루 약 5시간(11/15는 4시간)으로 총 약 44시간이다.

| 날짜 | 시간 | 할 일 | 결정 | 완료 기준 |
| --- | --- | --- | --- | --- |
| 11/3 (화) 밤 | 1h | GitHub 저장소 생성, 초판 `docs/PLAN.md` 커밋 | — | 완료 |
| 11/4 (수) | — | 계획 개정(이 문서), D1–D7 결정 | D1–D7 | 완료 |
| 11/7 (토) | 5h | **기반:** ADR 0001–0008, `pyproject.toml`, 린트·포맷·타입 검사·테스트 설정, 빈 패키지와 `py.typed`, `ci.yml`, `.gitignore`. **AI 협업 체계(가볍게):** AGENTS.md·CLAUDE.md, 스킬 4개. **데이터:** `examples/bird-mini` 반입(LICENSE, SOURCE.md, 다운로드 스크립트) | D8–D12, D25, D26, D28 | 빈 패키지로 CI 녹색, 432문제와 DB 3개가 저장소에 있음 |
| 11/8 (일) | 5h | **로더·판정:** 데이터셋·예측 파일 로더(오류에 위치 표시), 읽기 전용 실행기(시간 제한, 병렬), EX 판정(공식 코드 확인 후 구현), 실행 파일 스키마, CLI 뼈대와 `eval`. | D13, D14, D16, D17, D27 | `eval`이 실행 파일 생성, 432문제 로드·판정 테스트 통과 |
| 11/9 (월) | 5h | **baseline:** `examples/baseline`으로 예측 2개 생성(비용 확인 후), 공식 스크립트와 EX 일치 확인. **사실 설계 세션:** 실제 오답 케이스를 함께 읽으며 정규화 규칙과 사실 목록을 정함, 1차 구현. 범위 점검 1 | D15, **D18**, D24 | 오답 케이스 20개 이상에서 사실이 근거와 함께 나옴, 정답 케이스에서 가짜 차이 0 |
| 11/10 (화) | 5h | **사실 완성:** 실행 수준 사실, 구조 수준 사실 전체, 속성 기반 테스트, 카테고리 매핑 | D20 | 432문제 전체에서 사실 추출이 예외 없이 끝남 |
| 11/11 (수) | 5h | **신뢰도 플래그(ADR 0034)와 비교:** 분할표, 뒤집힌 케이스, 사실 분포 변화, DB별·난이도별 분해, 조건 불일치 경고, 종료 코드, `compare --csv`. 범위 점검 2 | D19, D22 | 플래그마다 테스트와 실제 사례 1개 이상, 비교 결과가 손으로 계산한 값과 일치 |
| 11/12 (목) | 5h | **리포트:** HTML(단일 파일, SQL 자동 정렬과 나란히 보기, 다른 절 강조, 결과 표 차이, 필터), CSV(UTF-8 BOM). 범위 점검 3 | D21 | 오프라인에서 HTML 열림, 엑셀에서 CSV 한글 정상 |
| 11/13 (금) | 5h | **CLI 마무리와 문서:** 오류 메시지, `--help` 예시, e2e 테스트, README, 가이드 4개, `architecture.md`, `reference/` 3개, CONTRIBUTING | D23 | 새 환경에서 설치 → `eval` → `report`가 3분 안에 됨, 처음 보는 사람이 README만 보고 실행 가능 |
| 11/14 (토) | 5h | **품질·결과:** README 실측 결과 표와 HTML 스크린샷, 타입 검사·`Any`·`ignore` 전수 점검, 리팩터, `ai-workflow.md`, 전 모듈 `/explain` 복습 | — | 개요의 완료 기준 전부 체크 |
| 11/15 (일) | 4h | **공개와 릴리스:** 깨끗한 clone에서 재현 확인, 저장소 공개 전환, README 첫 화면 점검, `v0.1.0` 태그와 PyPI 배포 | — | v0.1.0 공개 |

## 주의사항

- **데이터 라이선스:** `examples/bird-mini`는 CC BY-SA 4.0이다. 출처 표기를 빠뜨리지 않고, 코드 라이선스(MIT)와 섞이지 않게 README와 폴더 `LICENSE`에서 분명히 구분한다.
- **판정 결과의 정직성:** 공식 스크립트와 EX가 다르게 나오면 숨기지 말고 원인을 문서에 적는다. 신뢰도 플래그가 판정을 뒤집는 것처럼 보이지 않게, 플래그는 "의심"이라는 표현만 쓴다.
- **API 비용과 키:** baseline 실행 전에 호출 수(432 × 구성 수)와 예상 비용을 확인한다. 키는 `.env`에만 두고 커밋하지 않는다. 키가 커밋되면 기록을 지우는 것보다 키를 바로 폐기하는 것이 먼저다.
- **공개 전환 전 점검 (11/15):** git 기록 전체의 비밀값 검사, `.env`·`.study/`가 빠졌는지, 공개해도 되는 예제 결과만 있는지 확인한다.
- **커밋 기록은 있는 그대로:** 날짜를 고치거나 AI 표시를 지우지 않는다. "AI를 어떻게 통제했나"는 기록의 일관성으로 보여 준다.

## 출처

- [BIRD-bench 공식 사이트 (CC BY-SA 4.0 공지, dev set)](https://bird-bench.github.io/)
- [BIRD 논문 (arXiv 2305.03111)](https://arxiv.org/abs/2305.03111)
- [BIRD Mini-Dev (SQLite·MySQL·PostgreSQL)](https://huggingface.co/datasets/birdsql/bird_mini_dev)
- [sqlglot (PyPI)](https://pypi.org/project/sqlglot/)
- [Claude Code: CLAUDE.md와 AGENTS.md, @ 가져오기](https://code.claude.com/docs/en/memory.md)
- [Claude Code: 스킬](https://code.claude.com/docs/en/skills.md)
- [Claude Code: 훅 가이드](https://code.claude.com/docs/en/hooks-guide.md)
- [Claude Code: 훅 레퍼런스](https://code.claude.com/docs/en/hooks.md)
