# text-to-SQL 오답 분석 CLI 프로젝트 계획서 (토스 인턴 지원용)

Nov 3, 2026 작성 · Nov 4, 2026 전면 개정 · @철

## 개요

토스 Platform Engineer 인턴 서류 마감(11/15 일 23:59) 전에, text-to-SQL 연구에서 직접 겪은 **오답 분석의 병목**을 푸는 **Python 라이브러리 + CLI 저장소**를 만든다. 이름은 `text2sql-eval`이다(D1). 토스 서류에 저장소 링크로 내고, 이후 SK하이닉스 경험기술서 1번(AI 활용)의 포트폴리오로도 쓴다.

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
| 출발점 | 토스 공고의 카테고리 15개 | 연구에서 겪은 불편 ∩ 서류 지원 가이드 |
| 언어 | TypeScript | **Python** (D2) |
| 도구의 역할 | LLM 호출부터 채점까지 (Provider, 프롬프트, 캐시) | **예측 파일을 받아 판정·분석만** (D3) |
| 대표 기능 | 평가 파이프라인 전체, CI 게이트 | **결정적 오답 사실 추출** + 실행 비교 (D4) |
| 시연 데이터 | 합성 MES 30\~40개 | **BIRD dev 3개 DB, 432문제** (D5) |
| 결과 화면 | 터미널 표, Markdown | **정적 HTML 리포트 + CSV** (D6) |
| 패키지 | `core`·`cli`·`llm-spec` 3개 | 패키지 1개 (`text2sql_eval`, CLI 포함) |
| 뺀 것 | — | `llm-spec`, SQL 파서 가드, LLM 어댑터·캐시·mock, `init`·`schema`·`guard`·`cases lint` (D7) |

**완료 기준 (11/14 밤)**

- [ ] 깨끗한 환경에서 설치·린트·타입 검사·테스트가 성공하고, GitHub Actions CI가 녹색
- [ ] `examples/bird-mini`에서 baseline 예측 2개(같은 모델, 설정 2종)로 `text2sql-eval eval`이 실행 파일을 만든다
- [ ] 공식 호환 모드의 EX가 같은 예측에 대한 BIRD 공식 평가 스크립트의 EX와 일치한다(확인 결과를 문서에 기록)
- [ ] 모든 오답 케이스에 "무엇이 다른가" 사실 목록과 근거가 붙는다. 사용자 분류는 CSV의 `my_category` 열로 이어 간다 (매핑 파일은 로드맵, ADR 0042)
- [ ] 판정 신뢰도 플래그 6개(ADR 0034)가 근거와 함께 표시된다
- [ ] `report`가 오프라인에서 열리는 HTML 한 파일과 엑셀에서 한글이 깨지지 않는 CSV를 만든다
- [ ] `compare`가 분할표, 뒤집힌 케이스, 차이 분포 변화를 내고, 설정한 기준보다 나빠지면 종료 코드 1을 낸다
- [ ] README에 문제 정의, 설치, 3분 사용법, 실측 결과 표, AI 협업 방식이 있다
- [ ] 결정 기록 10개 이상, 모두 결정자가 "사용자"
- [ ] 모든 모듈에 대해 설명 노트와 면접식 질문 답변을 마쳤다

## 내가 겪은 문제 (README "왜 필요한가"의 원재료)

연구 배경: 산학연구로 제조 MES에 text-to-SQL을 적용했고(NL-SQL 쌍 생성, 데이터 coverage 지표, 여러 후보 SQL 병렬 생성과 최종 선택), 개인 연구로 자연어의 모호성·중의성을 DB 스키마 probing으로 해소하는 방법을 연구했다. 파이프라인은 Python과 bash 스크립트로 만들었고, 단일 프롬프트부터 키워드 추출, 스키마 선택, 스키마 메타 정보 순회, 테이블·컬럼 선택, 조인 경로 탐색, MCTS, agentic loop, 실행 기반 수정까지 여러 모듈을 조합했다. 바꿔 본 것은 프롬프트 문구, 모델, few-shot 예시와 추출 방식, 모듈 구성이다. 평가는 BIRD·Spider로, 주 지표는 EX(execution accuracy)였다.

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

## 서류 지원 가이드와 저장소의 증거

토스 서류 지원 가이드의 항목과, 저장소에서 바로 확인할 수 있는 증거다. 공고 원문은 [토스 Platform Engineer 인턴십](https://toss.im/career/job-detail?job_id=8096691003).

**지원서 문항: "자동화, 툴링, 테스팅 등으로 개발 환경을 개선한 경험"** → "연구 개발 루프에서 가장 큰 병목이던 오답 분석과 실험 비교를, 결정적이고 근거를 보여주는 도구로 바꿨다."

| # | 가이드 항목 | 저장소의 증거 | 우선순위 |
| --- | --- | --- | --- |
| 1 | 서비스가 아닌 라이브러리 또는 CLI | `src/text2sql_eval/` 공개 API + `text2sql-eval` 명령어, PyPI 형식 패키지 | 필수 |
| 2 | 어떤 문제를 푸는지 알 수 있는 README | 한 줄 정의, "내가 겪은 문제", 3분 빠른 시작, 실측 결과 표, HTML 리포트 스크린샷 | 필수 |
| 3 | 빌드·린트·의존성 설정 | `pyproject.toml` 하나로 메타데이터·도구 설정, 잠금 파일, 최소 의존성(추가마다 ADR), 지원 Python 버전 명시 | 필수 |
| 4 | 버그를 막는 CI 체크와 테스트 | GitHub Actions(린트, 포맷 검사, 타입 검사, Python 버전 매트릭스 테스트, 빌드, 패키지 검사), 단위·통합(실제 SQLite)·속성 기반·스냅샷 테스트 | 필수 |
| 5 | 레퍼런스와 가이드 | `docs/guides/*`, `docs/reference/cli.md`, 공개 API 레퍼런스, 실행 파일 형식 문서 | 필수 |
| 6 | 수정하기 쉬운 디렉터리 구조와 코드 품질 | 모듈 경계 문서(`architecture.md`), 한 방향 의존, 오류를 타입으로 표현 | 필수 |
| 7 | 타입을 정확하게 쓰려는 고민 | 타입 검사기 strict 모드 0 오류, 공개 API에 `Any` 없음, `Literal` 기반 판별 유니언과 `assert_never` 전수 검사, `py.typed` 배포. (가이드 원문은 TypeScript. 언어를 Python으로 정한 이유는 D2 ADR에 쓴다) | 필수 |
| 8 | 재현성 (추가) | 실행 파일에 도구 버전·데이터셋 해시·판정 모드·사용자 메타데이터 기록, 네트워크 없이 도는 테스트, 커밋된 예제 예측으로 리포트 재생성 | 필수 |
| 9 | 판정의 정직성 (추가) | 공식 스크립트와 EX 일치 확인, 신뢰도 플래그, 사실과 해석의 분리 | 필수 |
| 10 | CLI 사용성 (추가) | `--help` 예시, 고칠 방법을 말해 주는 오류 메시지, `--json` 출력, 종료 코드 규약 | 필수 |
| 11 | AI 협업 개발의 증거 (추가) | `AGENTS.md`, `docs/decisions/`, `docs/dev-log/`, `docs/ai-workflow.md`, AI 코드를 고친 리뷰 커밋 | 필수 |
| 12 | 도그푸딩 (추가) | CI가 커밋된 예제 예측으로 `eval → report → compare`를 실제로 돌리고 결과를 스냅샷과 비교 | 권장 |
| 13 | 릴리스 관리 (추가) | CHANGELOG, 시맨틱 버전, `v0.1.0` 태그, 선택으로 PyPI 배포 | 선택 |

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
2. CI 도그푸딩 단계 (가이드 #12)
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
- 합성 MES 예제 데이터셋
- Weights & Biases 등 실험 추적 도구 연동
- 사용자 카테고리 매핑 파일 `--categories` (ADR 0042)

**이번에 하지 않음**

- LLM 호출, 프롬프트 관리, 응답 캐시 (D3)
- SQL 파서 기반 가드 (읽기 전용 연결과 시간 제한으로 대신함)
- `llm-spec`, 웹 서버, 대시보드
- 산학 과제의 실제 데이터·스키마·프롬프트

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
│     ├─ explain/SKILL.md     코드 설명 + 면접식 질문
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
│  ├─ guides/                 (ADR 0012로 6개에서 4개로 줄임)
│  │  ├─ getting-started.md   3분 시작
│  │  ├─ prediction-format.md 내 파이프라인 결과를 예측 파일로 만들기
│  │  ├─ reading-results.md   사실·근거·정규화 규칙, 신뢰도 플래그, CSV로 손 분류하기
│  │  └─ comparing-runs.md    비교 결과 읽는 법
│  └─ reference/
│     ├─ cli.md
│     ├─ api.md
│     └─ run-file.md          실행 파일 형식
└─ .study/                    gitignore: 학습 노트와 면접 답변 (공개하지 않음)
```

## 내가 내릴 결정

모두 내가 정한다. Claude는 선택지와 장단점을 제시하고, 내가 고르면 ADR로 기록한다. "추천"은 출발점일 뿐이고, 도구 버전·유지보수 상태는 결정 직전에 공식 문서로 다시 확인한다. D1\~D7은 11/3\~4 대화에서 이미 정했으므로 첫 세션에서 묻지 않고 ADR만 쓴다.

**이미 정한 것**

| ID | 결정 | 내용 | 날짜 |
| --- | --- | --- | --- |
| D1 | 이름 | `text2sql-eval` (PyPI 이름 비어 있음 11/4 확인, import 이름 `text2sql_eval`, CLI 명령어도 `text2sql-eval`) | 11/3 |
| D2 | 언어 | Python. 이유: 대표 기능의 핵심인 SQL 파싱·정규화 생태계, 익숙한 언어여야 깊이와 설명 가능성 확보, 사용자(text-to-SQL 연구자)가 Python을 씀, 가이드의 TypeScript 항목은 한 번만 나오는 "좋아요" 항목 | 11/4 |
| D3 | 구조 | 예측 파일을 입력으로 받고 도구는 LLM을 부르지 않는다 | 11/4 |
| D4 | 기능 우선순위 | 대표: 결정적 사실 추출, 부대표: 실행 비교. 후보 coverage는 제외(구현이 쉽고, multi-candidate가 필수 요소가 아님) | 11/4 |
| D5 | 시연 데이터 | BIRD dev `superhero`·`student_club`·`toxicology` 432문제를 저장소에 포함, CC BY-SA 4.0 별도 표기 | 11/4 |
| D6 | 결과 화면 | 정적 HTML 리포트 + CSV (터미널은 요약만) | 11/4 |
| D7 | 범위 밖 | 합성 MES 데이터, LLM 분석 beta는 로드맵. `llm-spec`, SQL 가드, LLM 호출은 뺀다 | 11/4 |

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

라이선스는 코드 MIT, 예제 데이터 CC BY-SA 4.0으로 정하고 0001번 ADR에 함께 적는다. 이 목록에 없는 결정이 나오면 Claude가 D40부터 새 번호를 붙여 물어본다.

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
사용자가 말한 이유를 그대로 인용하고, 필요하면 보충.

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

- **`/explain <파일 또는 모듈>`:** Claude가 구조와 선택 이유, 버린 대안을 설명하고 면접식 질문 5개를 낸다. 내가 답하면 채점하고 부족한 부분을 보충한다. 문답은 `.study/<모듈>.md`에 저장(공개하지 않음).
- **`/devlog`:** 하루 끝에 `docs/dev-log/YYYY-MM-DD.md`를 쓴다. 한 일, 내린 결정(ADR 링크), **AI가 틀린 것과 내가 고친 것**, 내일 할 일.
- "AI가 틀린 것" 기록은 면접에서 "AI를 어떻게 통제했나"에 답하는 가장 구체적인 자료가 된다. 이 프로젝트의 주제(평가를 AI에 맡길 때의 무결성)와도 이어진다.
- 마지막 날 `docs/ai-workflow.md`에 정리한다: 작업 방식, ADR 수, Claude 추천을 기각한 결정 수, AI 코드를 고친 대표 사례 3개.

## 일별 일정

처음 계획은 11/4부터 하루 약 5시간이었으나, 11/4~11/6을 쓰지 못해 11/7에 일정을 다시 짰다(ADR 0012). 11/7부터 하루 약 5시간(11/15는 4시간)으로 총 약 44시간이다. 토스 제출은 마감 당일 18시까지 끝낸다. 이 기간에도 코딩테스트 하루 1문제(30분)는 따로 유지한다.

| 날짜 | 시간 | 할 일 | 결정 | 완료 기준 |
| --- | --- | --- | --- | --- |
| 11/3 (화) 밤 | 1h | GitHub 저장소 생성, 초판 `docs/PLAN.md` 커밋 | — | 완료 |
| 11/4 (수) | — | 계획 개정(이 문서), D1–D7 결정 | D1–D7 | 완료 |
| 11/7 (토) | 5h | **기반:** ADR 0001–0008, `pyproject.toml`, 린트·포맷·타입 검사·테스트 설정, 빈 패키지와 `py.typed`, `ci.yml`, `.gitignore`. **AI 협업 체계(가볍게):** AGENTS.md·CLAUDE.md, 스킬 4개. **데이터:** `examples/bird-mini` 반입(LICENSE, SOURCE.md, 다운로드 스크립트) | D8–D12, D25, D26, D28 | 빈 패키지로 CI 녹색, 432문제와 DB 3개가 저장소에 있음 |
| 11/8 (일) | 5h | **로더·판정:** 데이터셋·예측 파일 로더(오류에 위치 표시), 읽기 전용 실행기(시간 제한, 병렬), EX 판정(공식 코드 확인 후 구현), 실행 파일 스키마, CLI 뼈대와 `eval`. **SKT FLY AI 지원서 마감(2h 별도)** | D13, D14, D16, D17, D27 | `eval`이 실행 파일 생성, 432문제 로드·판정 테스트 통과 |
| 11/9 (월) | 5h | **baseline:** `examples/baseline`으로 예측 2개 생성(비용 확인 후), 공식 스크립트와 EX 일치 확인. **사실 설계 세션:** 실제 오답 케이스를 함께 읽으며 정규화 규칙과 사실 목록을 정함, 1차 구현. **17시 토스 채용설명회** (질문 하나 준비). 범위 점검 1 | D15, **D18**, D24 | 오답 케이스 20개 이상에서 사실이 근거와 함께 나옴, 정답 케이스에서 가짜 차이 0 |
| 11/10 (화) | 5h | **사실 완성:** 실행 수준 사실, 구조 수준 사실 전체, 속성 기반 테스트, 카테고리 매핑 | D20 | 432문제 전체에서 사실 추출이 예외 없이 끝남 |
| 11/11 (수) | 5h | **신뢰도 플래그(ADR 0034)와 비교:** 분할표, 뒤집힌 케이스, 사실 분포 변화, DB별·난이도별 분해, 조건 불일치 경고, 종료 코드, `compare --csv`. 범위 점검 2 | D19, D22 | 플래그마다 테스트와 실제 사례 1개 이상, 비교 결과가 손으로 계산한 값과 일치 |
| 11/12 (목) | 5h | **리포트:** HTML(단일 파일, SQL 자동 정렬과 나란히 보기, 다른 절 강조, 결과 표 차이, 필터), CSV(UTF-8 BOM). 범위 점검 3 | D21 | 오프라인에서 HTML 열림, 엑셀에서 CSV 한글 정상 |
| 11/13 (금) | 5h | **CLI 마무리와 문서:** 오류 메시지, `--help` 예시, e2e 테스트, README, 가이드 4개, `architecture.md`, `reference/` 3개, CONTRIBUTING | D23 | 새 환경에서 설치 → `eval` → `report`가 3분 안에 됨, 처음 보는 사람이 README만 보고 실행 가능 |
| 11/14 (토) | 5h | **품질·결과:** README 실측 결과 표와 HTML 스크린샷, 타입 검사·`Any`·`ignore` 전수 점검, 리팩터, `ai-workflow.md`, 전 모듈 `/explain` 복습 | — | 개요의 완료 기준 전부 체크 |
| 11/15 (일) | 4h | **제출:** 깨끗한 clone에서 재현 확인, 저장소 공개 전환, README 첫 화면 점검, 지원서 작성, **18시까지 제출**, 코드 동결 | — | 제출 완료 (마감 23:59) |

**그 뒤 일정:** 11/16(월) 10시 IBK 인턴 마감 · 11/16\~19 (권장) TypeScript 기초 학습 (과제가 TypeScript일 경우 대비) · 11/18(수) 11시 토스 과제 대상자 발표 · 11/20(금)\~26(목) 토스 과제 기간 · 11/21(토) FLY AI 면접·코딩역량평가(서류 통과 시). 과제 기간에는 저장소를 고치지 않고 `.study/` 복습에 집중한다.

## Claude Code 시작 프롬프트

저장소 폴더에서 Claude Code를 열고 아래 블록 전체를 첫 메시지로 붙여 넣는다. 두 번째 세션부터는 이 프롬프트가 필요 없다. 첫 세션에서 만든 `CLAUDE.md`와 `AGENTS.md`가 매 세션 자동으로 읽힌다.

```text
너는 이 저장소에서 나와 함께 Python 라이브러리와 CLI를 만드는 페어 프로그래머다.
프로젝트 계획은 docs/PLAN.md에 있다. 무엇이든 하기 전에 그 파일을 끝까지 읽어라.
이 프롬프트와 PLAN.md가 충돌하면 이 프롬프트를 따르고, 충돌한 점을 나에게 알려라.

## 배경
- 나: 성균관대 소프트웨어학과 4학년. 제조 MES text-to-SQL 산학연구와, 자연어 모호성을
  스키마 probing으로 해소하는 개인 연구를 했다. 평가는 BIRD·Spider, 주 지표는 EX였다.
- 목표: 2026-11-15(일) 23:59 마감인 토스 Platform Engineer 인턴 서류에 이 저장소 링크를 낸다.
  내 제출 목표는 11/15 18:00이다.
- 서류 지원 가이드: 서비스가 아닌 라이브러리·CLI, 문제를 설명하는 README, 올바른 빌드·린트·의존성 설정,
  CI와 테스트, 레퍼런스·가이드, 디렉터리 구조와 코드 품질, 타입을 정확하게 쓰기(원문은 TypeScript).
- 만들 것: text2sql-eval. 예측 파일을 받아 EX를 판정하고, 오답에서 "무엇이 다른가"를 AI 없이
  근거와 함께 추출하고, 판정 신뢰도 플래그를 붙이고, 두 실행을 케이스 단위로 비교하고,
  HTML 리포트와 CSV를 만든다. 도구는 LLM을 부르지 않는다.
- 나는 면접에서 이 저장소의 모든 줄을 설명해야 한다. 빨리 많이 쓰는 것보다,
  내가 이해할 수 있게 작게 나눠 쓰는 것을 우선한다.

## 절대 규칙
1. 설계 결정은 내가 한다. 공개 API, 의존성 추가·변경, 설정 파일, 데이터·예측·실행 파일 형식,
   판정·사실·플래그 규칙, 폴더 구조, 도구 선택은 모두 결정 대상이다. 결정이 필요하면 구현을 멈추고
   decide 절차를 따른다. 내 답 없이 추천안으로 진행하지 않는다.
2. 내가 결정하면 그 자리에서 ADR을 쓴다. "기록할까요?"라고 묻지 않는다.
3. 내 승인 없이 커밋, 푸시, 패키지 배포, 저장소 공개 전환을 하지 않는다.
4. 산학 과제의 실제 데이터·스키마·프롬프트를 쓰지 않는다. 예제 데이터는 examples/bird-mini(BIRD dev, CC BY-SA 4.0)다.
5. API 키는 환경변수로만 읽는다. 키를 파일·로그·테스트 스냅샷에 남기지 않는다. 도구 본체는 API 키를 쓰지 않는다.
6. 타입: 타입 검사기 strict 모드 0 오류, 공개 API에 Any 금지, 근거 없는 cast·# type: ignore 금지.
   불가피하면 이유를 주석으로 남기고 나에게 알린다.
7. 사실 추출과 판정은 결정적이어야 한다. LLM이나 무작위성을 쓰지 않는다.
8. 모르는 것(라이브러리 API, 도구의 현재 권장 사항, BIRD 공식 평가 규칙, Claude Code 기능)은
   추측하지 말고 공식 문서나 원본 코드를 확인한다. 확인할 수 없으면 그렇다고 말하고 확인 방법을 제안한다.

## decide 절차
결정이 필요하면 이 형식으로 묻는다.
- 결정 ID(PLAN.md의 D8~D27, 목록에 없으면 D28부터 새 번호)와 제목
- 맥락 2~3문장
- 선택지 2~4개를 표로: 안 | 장점 | 단점 | 이 프로젝트에 미치는 영향
- 너의 추천과 이유 한 문장 (도구 선택이면 확인한 공식 문서 링크)
- "어느 것으로 할까요?"로 끝낸다
독립적인 결정은 한 번에 최대 3개까지 묶어 물어도 된다.
내 답을 받으면:
- docs/decisions/NNNN-<slug>.md를 템플릿(docs/decisions/0000-template.md)대로 쓴다
- docs/decisions/README.md 색인에 한 줄을 추가한다
- "ADR 0009 기록: docs/decisions/0009-type-checker.md"처럼 한 줄로 보고한다
- "이유"에는 내가 한 말을 그대로 인용한다. 내가 너의 추천을 고르지 않았으면 "AI 관여"에 그 사실을 적는다

## 작업 단위
기능 하나마다: 계획 3~5줄 제시 → 내 승인 → 테스트와 구현 → check 통과
→ review 체크리스트로 자가 검토하고 고친 점 보고 → 내가 diff 검토 → 내 승인 후 커밋.
- 커밋은 Conventional Commits 형식으로 작게. AI 참여 표시는 D26 결정을 따른다.
- 한 번에 바꾸는 파일은 되도록 5개 이하. 커지면 나눈다.
- 구현을 마치면 "이 변경에서 면접에 나올 만한 질문" 2개를 덧붙인다.

## 첫 세션에서 할 일 (순서대로)
1. docs/PLAN.md를 읽고 목표·범위·일정을 10줄 이내로 요약한다. 모호하거나 모순된 부분은 질문한다.
2. D1~D7은 이미 정했다. 묻지 말고 PLAN.md의 내용과 이유로 ADR만 쓴다(0001은 ADR을 쓴다는 결정과
   라이선스: 코드 MIT, 예제 데이터 CC BY-SA 4.0). D8~D12, D25, D26을 decide 절차로 묻는다.
   도구 선택은 묻기 전에 공식 문서로 현재 유지보수 상태와 권장 사항을 확인하고 출처를 붙인다.
3. 결정을 받는 대로 기반 파일을 만든다.
   - pyproject.toml, src/text2sql_eval/(__init__.py, py.typed), tests/, 린트·포맷·타입 검사·테스트 설정,
     check를 한 번에 실행하는 방법
   - .github/workflows/ci.yml: 린트 → 포맷 검사 → 타입 검사 → 테스트(지원 버전 매트릭스) → 빌드
   - .gitignore에 .study/, .env, 실행 산출물(examples/results 제외)
   - docs/dev-log/<오늘 날짜>.md
4. CI가 녹색인지 확인하고, 오늘 만든 것과 남은 것을 보고한다.
   AI 협업 체계(AGENTS.md, CLAUDE.md, ADR 템플릿·색인, 스킬 4개, Stop 훅)는 다음 날(11/5) 일정이다.

## 11/5에 만들 AI 협업 체계
- AGENTS.md: 이 프롬프트의 절대 규칙, decide 절차, 작업 단위, 명령어, 폴더 구조 요약.
  사람이 읽어도 자연스러운 협업 규약으로 쓴다. 200줄 이내
- CLAUDE.md: 첫 줄에 @AGENTS.md, 그 아래에는 Claude Code 전용 사항만
- docs/decisions/0000-template.md(PLAN.md의 템플릿), README.md(색인)
- .claude/skills/ 아래 decide, explain, review, devlog 네 스킬. 각 SKILL.md에 name과 description을 쓴다.
  decide는 네가 설계 결정을 만났을 때 스스로 불러 쓸 수 있게 description을 구체적으로 쓴다.
  explain과 devlog는 내가 부를 때만 실행되게 한다.
  필드 이름은 https://code.claude.com/docs/en/skills.md 에서 확인한다
- scripts/check_decisions.py와 .claude/settings.json의 Stop 훅.
  감시 대상(PLAN.md의 "결정 기록 자동화" 목록)이 바뀌었는데 docs/decisions/에 변경이 없으면
  stderr에 "어떤 파일 때문에 어떤 결정을 물어야 하는지"를 쓰고 종료 코드 2로 끝낸다.
  같은 경고로 끊임없이 막지 않도록, Stop 훅 입력 필드를
  https://code.claude.com/docs/en/hooks.md 에서 확인해 처리한다.
  내가 "ADR 불필요"라고 답한 변경은 docs/decisions/skipped.md에 날짜·파일·이유를 한 줄 남긴다.
  훅을 일부러 한 번 발동시켜 동작하는 것을 보여 준다

## 스킬 내용
- decide: 위 decide 절차 그대로.
- explain <경로>: 그 코드의 역할, 데이터 흐름, 선택 이유와 버린 대안을 설명하고 면접식 질문 5개를 낸다.
  내가 답하면 채점하고 보충한 뒤, 문답을 .study/<모듈>.md에 저장한다.
- review: PLAN.md의 자가 검토 체크리스트로 현재 diff를 검사하고, 고친 것과 남은 것을 표로 보고한다.
- devlog: 오늘의 docs/dev-log/YYYY-MM-DD.md를 쓴다. 한 일, 내린 결정(ADR 링크),
  AI가 틀린 것과 내가 고친 것(파일과 내용까지 구체적으로), 내일 할 일.

## 매일 세션을 시작할 때
PLAN.md 일별 일정에서 오늘 날짜의 행과 가장 최근 dev-log를 읽고, 오늘 할 일과 필요한 결정을 5줄로 제시한다.
일정보다 늦으면 PLAN.md의 범위 축소 규칙을 근거로 무엇을 줄일지 제안하고 내 결정을 받는다.
(이 항목은 AGENTS.md에도 넣어 다음 세션부터 자동으로 적용되게 한다.)

## 말투
나에게는 한국어로 짧게. 코드·커밋·docstring 언어는 D25 결정을 따른다.

지금 첫 세션을 시작한다. 1번부터 진행해라.
```

## 주의사항

- **기밀:** 산학 과제의 데이터·스키마·프롬프트, 삼성SDS ERP 과제 내용은 저장소에 넣지 않는다. README의 연구 배경은 이 문서의 "내가 겪은 문제" 수준(방법론 일반론과 겪은 불편)까지만 쓴다. 미게재 논문의 내용을 옮길 때는 공동 연구자와 지도교수에게 먼저 확인한다.
- **데이터 라이선스:** `examples/bird-mini`는 CC BY-SA 4.0이다. 출처 표기를 빠뜨리지 않고, 코드 라이선스(MIT)와 섞이지 않게 README와 폴더 `LICENSE`에서 분명히 구분한다.
- **판정 결과의 정직성:** 공식 스크립트와 EX가 다르게 나오면 숨기지 말고 원인을 문서에 적는다. 신뢰도 플래그가 판정을 뒤집는 것처럼 보이지 않게, 플래그는 "의심"이라는 표현만 쓴다.
- **토스 과제의 AI 사용 규정:** 11/20\~26 과제에서 AI 도구를 써도 되는지 과제 안내를 먼저 확인한다. 금지라면 직접 짠다. 이 저장소의 규칙과는 별개다.
- **API 비용과 키:** baseline 실행 전에 호출 수(432 × 구성 수)와 예상 비용을 확인한다. 키는 `.env`에만 두고 커밋하지 않는다. 키가 커밋되면 기록을 지우는 것보다 키를 바로 폐기하는 것이 먼저다.
- **공개 전환 전 점검 (11/15):** git 기록 전체의 비밀값 검사, `.env`·`.study/`가 빠졌는지, 공개해도 되는 예제 결과만 있는지 확인한다.
- **제출본 고정:** 제출 직전 커밋에 `v0.1.0` 태그를 달고 README에 "서류 제출 시점: v0.1.0"을 적는다. 마감 뒤 커밋이 있어도 제출 시점을 구분할 수 있다.
- **커밋 기록은 있는 그대로:** 날짜를 고치거나 AI 표시를 지우지 않는다. "AI를 어떻게 통제했나"라는 어필이 기록의 일관성에 달려 있다.
- **학업과의 충돌:** 이번 학기 12학점의 과제·시험 일정을 일정표에 겹쳐 보고, 겹치는 날은 미리 범위 축소 규칙을 적용한다.
- **다음 쓰임:** 토스 결과와 관계없이 이 저장소는 SK하이닉스 경험기술서 1번(AI 활용 경험)의 핵심 소재다. "연구에서 겪은 분석 병목 → 결정적 분석 도구화 → AI 협업 개발 체계"의 흐름으로 쓴다.

## 출처

- [토스: Platform Engineer 인턴십 공고](https://toss.im/career/job-detail?job_id=8096691003)
- [BIRD-bench 공식 사이트 (CC BY-SA 4.0 공지, dev set)](https://bird-bench.github.io/)
- [BIRD 논문 (arXiv 2305.03111)](https://arxiv.org/abs/2305.03111)
- [BIRD Mini-Dev (SQLite·MySQL·PostgreSQL)](https://huggingface.co/datasets/birdsql/bird_mini_dev)
- [sqlglot (PyPI)](https://pypi.org/project/sqlglot/)
- [Claude Code: CLAUDE.md와 AGENTS.md, @ 가져오기](https://code.claude.com/docs/en/memory.md)
- [Claude Code: 스킬](https://code.claude.com/docs/en/skills.md)
- [Claude Code: 훅 가이드](https://code.claude.com/docs/en/hooks-guide.md)
- [Claude Code: 훅 레퍼런스](https://code.claude.com/docs/en/hooks.md)
