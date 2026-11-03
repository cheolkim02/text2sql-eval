# text-to-SQL 평가 CLI 프로젝트 계획서 (토스 인턴 지원용)

Nov 3, 2026 · @철

## 개요

토스 Platform Engineer 인턴 서류 마감(11/15 일 23:59) 전에, MES text-to-SQL 연구를 **TypeScript 라이브러리 + CLI 저장소**로 만든다. 이름은 `text2sql-eval`이다(결정 D1, 11/3). 토스 서류에 GitHub 링크로 내고, 이후 SK하이닉스 경험기술서 1번(AI 활용)의 포트폴리오로도 쓴다.

**산출물 세 가지**

1. **평가 엔진 + CLI:** 자연어 질문을 LLM이 SQL로 바꾸면, 안전 검사 → 실행 → 정답 결과와 비교 → 오류 유형 분류 → 리포트와 실행 간 회귀 비교까지 한다. 토스 프로젝트 "LLM 스킬 성능 평가 시스템"에 대응한다.
2. **LLM용 스펙 도구 (`llm-spec`):** 공개 API 타입에서 LLM이 읽기 좋은 스펙(`llms.txt`)을 만들고, 문서와 코드가 어긋나면 CI를 실패시킨다. 이 저장소 자체에 적용한다. 토스 프로젝트 "LLM이 읽는 스펙과 개발환경"에 대응한다.
3. **AI 협업 개발의 증거:** AGENTS.md, 결정 기록(ADR), CI 게이트, AI 코드를 고친 리뷰 커밋.

**완료 기준 (11/14 밤)**

- [ ] `pnpm install && pnpm build && pnpm test`가 깨끗한 환경에서 성공하고, GitHub Actions CI가 녹색
- [ ] 합성 MES 샘플 데이터셋으로 `text2sql-eval run`이 mock 모델과 실제 모델 1개 이상으로 리포트를 만든다
- [ ] `text2sql-eval compare`가 정확도 하락 시 종료 코드 1을 낸다
- [ ] `llm-spec check`가 CI에서 돌고, 스펙이 낡으면 실패한다
- [ ] README에 문제 정의, 설치, 3분 사용법, 실측 결과 표, AI 협업 방식이 있다
- [ ] 결정 기록 10개 이상, 모두 결정자가 "사용자"
- [ ] 모든 모듈에 대해 설명 노트와 면접식 질문 답변을 마쳤다

## 토스에 보여줄 카테고리

공고 우대사항 7개에 8개를 더해 15개를 보여준다. 각 카테고리는 저장소에서 바로 확인할 수 있는 파일이나 CI 결과로 증명한다. 공고 원문은 [토스 Platform Engineer 인턴십](https://toss.im/career/job-detail?gh_jid=8096691003).

| # | 카테고리 | 출처 | 저장소의 증거 | 우선순위 |
| --- | --- | --- | --- | --- |
| 1 | 라이브러리·CLI 형태 | 공고 | `packages/core`(라이브러리), `packages/cli`(실행 파일), `packages/llm-spec` | 필수 |
| 2 | 문제를 설명하는 README | 공고 | 한 줄 정의, 왜 필요한가, 60초 빠른 시작, 실측 결과 표, 데모 GIF | 필수 |
| 3 | 빌드·린트·의존성 설정 | 공고 | pnpm workspace, 빌드 도구 설정, 타입 기반 린트, `exports` 맵, `engines`, 최소 의존성 | 필수 |
| 4 | CI와 테스트 | 공고 | GitHub Actions(린트, 타입 검사, 테스트, 빌드, 스펙 검사), 단위·통합(실제 SQLite)·스냅샷 테스트 | 필수 |
| 5 | 레퍼런스와 가이드 | 공고 | `docs/guides/*`, `docs/reference/cli.md`, 자동 생성되는 `docs/reference/api.md` | 필수 |
| 6 | 디렉터리 구조와 코드 품질 | 공고 | 모듈 경계 문서, 한 방향 의존, 오류를 타입으로 표현 | 필수 |
| 7 | TypeScript를 정확하게 | 공고 | strict 계열 옵션 전부, `any` 0개, 판별 유니언 결과 타입, zod 스키마에서 타입 추론, 타입 테스트 | 필수 |
| 8 | 패키지 배포 정합성 | 추가 | `publint`, `@arethetypeswrong/cli` CI 통과, 타입 선언 파일 포함 | 권장 |
| 9 | 재현성 | 추가 | mock 모델, LLM 응답 캐시와 replay, 네트워크 없이 도는 테스트 | 필수 |
| 10 | 안전성 | 추가 | 읽기 전용 SQL 검사, 실행 시간·행 수 제한, API 키는 환경변수로만, 로그에서 키 가리기 | 필수 |
| 11 | CLI 사용성 | 추가 | `--help` 예시, 고칠 방법을 말해 주는 오류 메시지, `--json` 출력, 종료 코드 규약 | 필수 |
| 12 | 실측 결과 | 추가 | 모델 2개 × 샘플 데이터셋 결과 표와 오류 유형 분포(README) | 권장 |
| 13 | 릴리스 관리 | 추가 | changesets, CHANGELOG, 시맨틱 버전, 선택으로 npm 배포 | 선택 |
| 14 | AI 협업 개발의 증거 | 추가 | `AGENTS.md`, `docs/decisions/`, `docs/ai-workflow.md`, AI 코드를 고친 리뷰 커밋 | 필수 |
| 15 | 도그푸딩 | 추가 | `llm-spec`이 이 저장소의 `llms.txt`를 만들고 검사, `text2sql-eval compare`가 CI에서 프롬프트 회귀를 검사 | 필수 |

두 가지를 더 하면 토스 프로젝트 4번(LLM 저장소를 안전하게 관리)과도 이어진다: CI의 비밀값 노출 검사(gitleaks 등), 의존성 자동 업데이트 설정. 둘 다 선택이다.

## 기능 범위

SQLite 하나만 지원하고, 평가 파이프라인을 끝까지 완성하는 것이 1순위다. 기능을 넓히는 것보다 적은 기능을 제품 수준으로 만드는 쪽이 토스 기준에 맞다.

**필수 (11/14까지)**

- `core` 라이브러리
  - 데이터셋 로더: JSONL 케이스 파일을 zod로 검증
  - 스키마 추출: SQLite에서 테이블·컨럼·외래키를 읽고 LLM 프롬프트용 텍스트로 렌더
  - SQL 가드: 파서 기반으로 단일 `SELECT`/`WITH`만 허용, `PRAGMA`·`ATTACH`·쓰기 문장 차단
  - 실행기: 읽기 전용 연결, 실행 시간 제한, 행 수 제한
  - 결과 비교기: 정답 SQL과 예측 SQL의 결과 집합 비교(순서, 컨럼 이름, 실수 오차 규칙은 결정 D9)
  - 오류 유형 분류: 문법 오류, 없는 테이블·컨럼(스키마 환각), 가드 차단, 실행 오류, 시간 초과, 결과 불일치(행 수, 컨럼, 값), 모델 호출 실패
  - 모델 어댑터: 공통 인터페이스 + mock + 응답 캐시·replay + 실제 모델 1개
  - 실행기(runner): 동시 실행 수 제한, 취소(`AbortSignal`), 진행 이벤트
  - 리포트: JSON(기계용), Markdown, 터미널 표
  - 실행 비교: 두 실행의 정확도 차이, 나빠진 케이스 목록, 임계값 판정
- `cli`: `init`, `schema`, `guard`, `cases lint`, `run`, `report`, `compare`
- `llm-spec`: `generate`(공개 API → `llms.txt`, `api.md`), `check`(낡은 스펙이면 실패)
- `examples/mes-sample`: 합성 MES 스키마(테이블 6\~8개), 시드 스크립트, 케이스 30\~40개(난이도·유형 태그)
- CI, README, 가이드 4개, `AGENTS.md`, 결정 기록

**권장 (시간이 남으면 이 순서로)**

1. `llm-spec examples`: 문서 속 TypeScript 코드 블록을 타입 검사
2. `publint`·`@arethetypeswrong/cli` CI 단계
3. 두 번째 실제 모델 어댑터와 모델 비교 결과 표
4. PR에 비교 결과를 다는 GitHub Actions 예제 워크플로
5. 데모 GIF, changesets, npm 배포
6. HTML 리포트

**이번에 하지 않음**

- PostgreSQL·MySQL 지원: 방언(dialect) 인터페이스만 열어 두고 구현은 SQLite만
- 웹 UI, 서버, 대시보드
- 자기 수정 루프 같은 다단계 에이전트 전략(로드맵에만 적음)
- 산학 과제의 실제 데이터·스키마·프롬프트

**범위 축소 규칙**

- 11/9 밤에 `run`과 `compare`가 mock으로 끝까지 돌지 않으면: 권장 항목을 모두 버리고 `llm-spec`은 `generate`와 `check`만 만든다.
- 11/12 밤에 `llm-spec check`가 CI에서 돌지 않으면: `llm-spec`을 `generate`만 남기고 문서·품질에 시간을 쓴다.
- 줄이지 않는 것: 테스트, CI, README, 결정 기록, 학습 노트.

## 명령어 설계

CLI는 얇게 `core` 라이브러리를 감싼 것이다. 모든 로직은 `core`에 있고, CLI는 옵션 해석과 출력만 한다. 이름 `text2sql-eval`은 npm에서 비어 있는 것을 11/3에 확인했다. CLI 명령어도 같은 이름을 쓴다.

### 평가 흐름

1. 데이터셋의 케이스 하나(질문 + 정답 SQL)를 읽는다.
2. DB 스키마와 질문을 프롬프트로 만들어 모델에 보낸다(캐시에 있으면 캐시 사용).
3. 예측 SQL을 가드에 통과시킨다. 차단되면 `blocked`로 기록하고 끝.
4. 예측 SQL과 정답 SQL을 읽기 전용 연결에서 각각 실행한다.
5. 두 결과 집합을 비교해 `correct` / `incorrect` / `error`로 분류한다.
6. 모든 케이스를 모아 실행 파일(JSON)로 저장한다. `report`가 읽고, `compare`가 두 실행 파일을 비교한다.

### CLI 명령어

```text
text2sql-eval init [dir]                 설정 파일과 예제 데이터셋 생성
  --template <mes-sample|empty>     기본 mes-sample
  --force                           기존 파일 덮어쓰기

text2sql-eval schema --db <path>         LLM 프롬프트용 스키마 출력
  --format <text|ddl|json>          기본 text
  --tables <a,b>                    일부 테이블만

text2sql-eval guard <sql|-> --db <path>  SQL 안전 검사만 수행 (- 는 stdin)
  --json

text2sql-eval cases lint [--dataset <path>]
  확인: 스키마 검증, id 중복, 정답 SQL의 가드 통과와 실행 성공
  경고: 빈 결과, ORDER BY 없는 LIMIT(정답이 매번 달라질 수 있음)

text2sql-eval run                        평가 실행
  --config <path>                   기본 text2sql-eval.config.ts
  --dataset <path> --db <path>      설정 파일 값을 덮어씁
  --provider <id> --model <name>
  --concurrency <n>                 기본 4
  --cache <read-write|read-only|off>  read-only = 캐시만 사용(replay)
  --filter <tag:join,difficulty:hard>
  --limit <n>
  --out <path>                      기본 .text2sql-eval/runs/<시각>-<모델>.json
  --min-accuracy <0..1>             미달 시 종료 코드 1
  --json                            요약을 stdout에 JSON으로

text2sql-eval report <run.json>
  --format <table|md|json>          기본 table
  --by <tag|difficulty|error>       그룹별 집계
  --failures                        틀린 케이스만: 질문, 예측 SQL, 정답 SQL, 오류 유형

text2sql-eval compare <base.json> <head.json>
  --max-drop <pp>                   허용하는 정확도 하락폭(%p), 기본 0
  --fail-on-flip                    base에서 맞던 케이스가 하나라도 틀리면 실패
  --format <table|md|json>          md = PR 코멘트용

llm-spec generate --entry <file> --out <llms.txt> [--api-md <path>]
llm-spec check    --entry <file> --out <llms.txt>   다르면 diff 출력 후 실패
llm-spec examples <glob...>         (권장) 문서 속 ts 코드 블록 타입 검사
```

### 종료 코드

| 코드 | 의미 | 예 |
| --- | --- | --- |
| 0 | 성공 | 평가 완료, 가드 통과, 스펙 최신 |
| 1 | 판정 실패 | 정확도 미달, 회귀, 가드 차단, 스펙 불일치, lint 오류 |
| 2 | 사용법·설정 오류 | 잘못된 옵션, 설정 검증 실패, 파일 없음 |
| 3 | 실행 환경 오류 | API 키 없음·인증 실패, 네트워크, DB 열기 실패 |
| 130 | 사용자 중단 | Ctrl-C (진행분은 부분 실행 파일로 저장) |

오류 메시지는 무엇이 잘못됐는지, 어떻게 고치는지 두 줄로 쓴다. 예: `OPENAI_API_KEY가 설정되지 않았습니다. --provider mock으로 먼저 실행해 볼 수 있습니다.`

### 설정 파일

```ts
// text2sql-eval.config.ts
import { defineConfig } from '@text2sql-eval/core';

export default defineConfig({
  dataset: './cases.jsonl',
  db: './mes.sqlite',
  provider: { id: 'openai-compatible', model: 'your-model-name', apiKeyEnv: 'OPENAI_API_KEY' },
  prompt: { template: './prompt.md' },
  guard: { timeoutMs: 5_000, maxRows: 1_000 },
  compare: { order: 'auto', floatTolerance: 1e-6 },
  concurrency: 4,
});
```

모델 이름은 예시다. 실제 모델과 제공자는 결정 D10에서 정한다.

### 데이터셋 형식 (JSONL, 한 줄에 케이스 하나)

```json
{"id":"wo-007","question":"지난주 라인별 완료된 작업지시 수는?","gold":"SELECT line_id, COUNT(*) AS n FROM work_orders WHERE status = 'DONE' AND finished_at >= date('2026-10-26') AND finished_at < date('2026-11-02') GROUP BY line_id","tags":["aggregation","time-window"],"difficulty":"easy","evidence":"'지난주'는 2026-10-26~2026-11-01"}
```

`evidence`는 선택 필드로, 질문만으로는 알 수 없는 도메인 힌트다. `order`를 케이스별로 덮어쓸 수 있다.

### 라이브러리 공개 API (초안)

```ts
export function defineConfig(config: Text2SqlEvalConfig): Text2SqlEvalConfig;
export function loadDataset(path: string): Promise<Dataset>;
export function introspectSchema(db: ReadonlyDatabase): SchemaInfo;
export function renderSchema(schema: SchemaInfo, format: 'text' | 'ddl'): string;
export function createGuard(options?: GuardOptions): (sql: string) => GuardResult;
export function evaluate(options: EvaluateOptions): Promise<RunResult>;
export function compareRuns(base: RunResult, head: RunResult, options?: CompareOptions): Comparison;
export function createMockProvider(answers: ReadonlyMap<string, string>): Provider;
export function withCache(provider: Provider, options: CacheOptions): Provider;

export interface Provider {
  readonly id: string;
  generateSql(request: GenerateRequest, context: { signal: AbortSignal }): Promise<GenerateResponse>;
}

export type GuardResult =
  | { ok: true; sql: string }
  | { ok: false; violation: GuardViolation; message: string };

export type CaseResult =
  | { status: 'correct'; caseId: string; predictedSql: string; latencyMs: number }
  | { status: 'incorrect'; caseId: string; predictedSql: string; mismatch: Mismatch; latencyMs: number }
  | { status: 'error'; caseId: string; predictedSql?: string; error: EvalError };

export type EvalError = {
  kind: 'syntax' | 'unknown_identifier' | 'blocked' | 'runtime' | 'timeout' | 'provider';
  message: string;
};
```

실행 파일(JSON)에는 `schemaVersion`, 도구 버전, 모델, 프롬프트 해시, 데이터셋 해시를 넣는다. 그래야 `compare`가 조건이 다른 두 실행을 경고할 수 있다.

## 폴더 구조

pnpm workspace 모노레포로 패키지 3개를 둔다(결정 D2). 의존 방향은 `cli → core` 한 방향이고, `llm-spec`은 다른 패키지에 의존하지 않는다.

```text
text2sql-eval/
├─ AGENTS.md                  에이전트 규칙 (사람도 읽는 협업 규약)
├─ CLAUDE.md                  @AGENTS.md 를 불러오고 Claude Code 전용 규칙만 추가
├─ README.md
├─ CONTRIBUTING.md            개발 환경, 명령어, 커밋 규칙
├─ LICENSE
├─ llms.txt                   llm-spec이 생성 (직접 수정 금지)
├─ package.json               루트 스크립트: build, test, lint, typecheck, check
├─ pnpm-workspace.yaml
├─ tsconfig.base.json         strict 계열 옵션 공통 설정
├─ eslint.config.js
├─ vitest.config.ts
├─ .changeset/                (권장) 릴리스 기록
├─ .github/
│  └─ workflows/
│     ├─ ci.yml               lint → typecheck → test → build → llm-spec check
│     └─ eval-regression.yml  (권장) replay 캐시로 run → compare → PR 코멘트
├─ .claude/
│  ├─ settings.json            훅 설정 (결정 기록 누락 검사)
│  └─ skills/
│     ├─ decide/SKILL.md       설계 결정 제시 → 사용자 선택 → ADR 기록
│     ├─ explain/SKILL.md      코드 설명 + 면접식 질문
│     ├─ review/SKILL.md       AI가 쓴 코드 자가 검토 체크리스트
│     └─ devlog/SKILL.md       하루 마무리 기록
├─ scripts/
│  └─ check-decisions.mjs      훅이 호출: 의존성·설정·공개 API 변경에 ADR이 있는지 검사
├─ docs/
│  ├─ PLAN.md                  이 문서
│  ├─ ai-workflow.md           AI와 어떻게 개발했는지 (토스에 보여줄 문서)
│  ├─ architecture.md          모듈 경계와 데이터 흐름
│  ├─ decisions/
│  │  ├─ 0000-template.md
│  │  └─ 0001-record-decisions.md …
│  ├─ dev-log/                 날짜별 개발 기록 (2026-11-04.md …)
│  ├─ guides/
│  │  ├─ getting-started.md
│  │  ├─ dataset-format.md
│  │  ├─ providers.md
│  │  ├─ safety.md
│  │  └─ ci-regression.md
│  └─ reference/
│     ├─ cli.md
│     └─ api.md               llm-spec이 생성
├─ examples/
│  └─ mes-sample/
│     ├─ schema.sql           합성 MES 스키마
│     ├─ seed.ts              결정적 시드 데이터 생성
│     ├─ cases.jsonl          평가 케이스 30~40개
│     ├─ prompt.md            프롬프트 템플릿
│     ├─ text2sql-eval.config.ts
│     └─ results/             공개할 실측 실행 파일
├─ packages/
│  ├─ core/
│  │  ├─ src/
│  │  │  ├─ index.ts           공개 API만 내보냄 (여기에 없으면 비공개)
│  │  │  ├─ config/            defineConfig, 설정 스키마, 로더
│  │  │  ├─ dataset/           케이스 스키마, JSONL 로더, lint
│  │  │  ├─ schema/            스키마 추출, 렌더러
│  │  │  ├─ guard/             SQL 파싱, 안전 규칙
│  │  │  ├─ executor/          읽기 전용 실행, 시간·행 제한
│  │  │  ├─ compare/           결과 집합 비교, 오류 분류
│  │  │  ├─ providers/         Provider 인터페이스, mock, cache, 실제 어댑터
│  │  │  ├─ runner/            evaluate, 동시성, 진행 이벤트
│  │  │  ├─ report/            집계, Markdown·표 렌더, compareRuns
│  │  │  └─ errors.ts          오류 타입 정의
│  │  ├─ test/                  단위·통합·타입 테스트, fixtures/
│  │  ├─ package.json
│  │  └─ tsconfig.json
│  ├─ cli/
│  │  ├─ src/
│  │  │  ├─ bin.ts             실행 진입점 (#!/usr/bin/env node)
│  │  │  ├─ commands/          init, schema, guard, cases, run, report, compare
│  │  │  ├─ output/            표, 색, JSON 출력
│  │  │  └─ exit-codes.ts
│  │  └─ test/                  실제 프로세스로 실행하는 e2e 테스트
│  └─ llm-spec/
│     ├─ src/
│     │  ├─ extract/           TypeScript 컴파일러 API로 공개 심볼·JSDoc 추출
│     │  ├─ render/            llms.txt, api.md 렌더
│     │  ├─ check/             생성물과 파일 비교, diff
│     │  └─ bin.ts
│     └─ test/
└─ .study/                    gitignore: 학습 노트와 면접 답변 (공개하지 않음)
```

합성 MES 스키마 초안: `lines`(생산 라인), `equipment`(설비), `products`(품목), `work_orders`(작업지시), `lots`(로트), `process_steps`(공정 단계), `inspections`(검사 결과), `downtime_events`(비가동). 산학 과제의 실제 스키마를 복사하지 않고, 일반적인 MES 개념으로 새로 설계한다.

## 내가 내릴 결정

아래 20개는 모두 내가 정한다. Claude는 선택지와 장단점을 제시하고, 내가 고르면 ADR로 기록한다. "추천"은 출발점일 뿐이고, 도구 버전·유지보수 상태는 결정 직전에 공식 문서로 다시 확인한다.

| ID | 결정 | 선택지 | 추천 (출발점) | 시점 |
| --- | --- | --- | --- | --- |
| D1 | 프로젝트·패키지 이름 | `text2sql-eval` / `nl2sql-eval` / 다른 이름 | **결정됨: `text2sql-eval`**, npm 스코프 `@text2sql-eval/*` (첫 세션에서 ADR만 기록) | 11/4 |
| D2 | 저장소 구조 | pnpm 모노레포 3패키지 / 단일 패키지 | 모노레포 (빌드·의존성 설정을 보여주기 좋음) | 11/4 |
| D3 | Node 버전·모듈 형식 | Node 22+ ESM 전용 / ESM+CJS | Node 22 이상, ESM 전용 | 11/4 |
| D4 | 빌드 도구 | tsdown / tsup / tsc | 공식 문서의 유지보수 상태를 보고 결정 | 11/4 |
| D5 | 린트·포맷 | ESLint(typescript-eslint 타입 기반 strict) + Prettier / Biome | ESLint 타입 기반 (TypeScript 정확성을 더 잘 보여줌) | 11/4 |
| D6 | 테스트 | Vitest / node:test | Vitest + `expectTypeOf` 타입 테스트 | 11/4 |
| D7 | 오류 모델 | 예외 / 결과 값(판별 유니언) / 혼합 | 예상되는 실패는 결과 값, 프로그래밍 오류만 예외 | 11/5 |
| D8 | 설정 파일 로딩 | `.ts` 직접 import / jiti / JSON만 | jiti (Node 버전에 덜 민감) | 11/5 |
| D9 | 결과 비교 규칙 | 순서, 컨럼 이름, 중복 행, 실수 오차, NULL | 정답에 ORDER BY가 있을 때만 순서 비교, 컨럼은 이름 대신 위치, 중복 포함 다중집합, 오차 1e-6 | 11/7 |
| D10 | 첫 실제 모델 제공자 | OpenAI 호환 API / Anthropic SDK / 둘 다 | OpenAI 호환 하나 먼저 (여러 제공자가 같은 형식), 두 번째는 권장 범위 | 11/7 |
| D11 | SQLite 드라이버 | better-sqlite3 / node:sqlite / sql.js(wasm) | better-sqlite3 (읽기 전용 연결 지원, 안정적) | 11/5 |
| D12 | 쿼리 시간 제한 구현 | worker thread 종료 / SQLite 진행 콜백 | worker thread (동기 드라이버는 같은 스레드에서 멈출 수 없음) | 11/6 |
| D13 | SQL 가드 방식 | 파서(node-sql-parser 등) / 토크나이저 직접 / DB 기능만 | 2중 방어: 파서 검사 + DB 수준 읽기 전용(`readonly` 연결, `PRAGMA query_only`) | 11/6 |
| D14 | CLI 프레임워크 | commander / cac / citty / `node:util` parseArgs | 의존성 수와 타입 지원을 비교해 결정 | 11/6 |
| D15 | 캐시 키와 저장 | 해시 입력 항목, 저장 위치, 커밋 여부 | 해시(제공자, 모델, 렌더된 프롬프트, 파라미터) → `.text2sql-eval/cache/`; 예제 캐시는 커밋해 CI에서 replay | 11/7 |
| D16 | 프롬프트 템플릿 | Markdown + `{{schema}}` 같은 자리표시자 / 코드 함수 | Markdown 템플릿 (비개발자도 수정 가능) | 11/7 |
| D17 | llm-spec 추출 방식 | TypeScript 컴파일러 API 직접 / ts-morph / api-extractor | 컴파일러 API 직접 (의존성 적고 면접에서 설명하기 좋음) | 11/11 |
| D18 | llms.txt 형식 | llmstxt.org 제안 형식 / 자체 형식 | 제안 형식 + API 상세 섹션 | 11/11 |
| D19 | 문서 언어 | 한국어 / 영어 / 한국어+영어 요약 | README는 한국어 + 영어 한 단락, 코드·커밋·JSDoc은 영어 | 11/4 |
| D20 | 커밋 규칙과 AI 표시 | Conventional Commits 여부, AI 참여 표시(`Co-Authored-By`) 여부 | 둘 다 사용 (AI 활용을 투명하게 드러내는 것이 어필 포인트) | 11/4 |

라이선스는 MIT로 정하고 0001번 ADR에 함께 적는다. 이 목록에 없는 결정이 나오면 Claude가 새 ID를 붙여 물어본다.

## AI 협업 규칙

나는 설계·결정·리뷰를 하고, Claude는 선택지 제시·구현·테스트·문서 초안·기록을 한다. 결정 기록은 세 겹으로 자동화한다. 규칙만으로는 빠뜨릴 수 있어서, 훅으로 누락을 한 번 더 잡는다.

### 결정 기록 자동화

1. **규칙 (`AGENTS.md`, `CLAUDE.md`):** Claude Code는 세션을 시작할 때 프로젝트의 `CLAUDE.md`를 읽고, `CLAUDE.md` 안의 `@AGENTS.md` 줄은 그 파일을 함께 불러온다([공식 문서](https://code.claude.com/docs/en/memory.md)). 여기에 "결정이 필요한 순간 멈추고 물어본 뒤, 답을 받으면 즉시 ADR을 쓴다"는 규칙을 둔다.
2. **스킬 (`.claude/skills/decide/SKILL.md`):** 설계 결정이 생기면 Claude가 스스로 불러 쓰고, 내가 `/decide <주제>`로 직접 부를 수도 있다. 스킬의 `description`이 자동 호출 여부를 정한다([공식 문서](https://code.claude.com/docs/en/skills.md)).
   - 순서: 결정 주제와 맥락 한 단락 → 선택지 2\~4개를 장단점 표로 → Claude의 추천과 이유 → 내 답을 기다림 → 답을 받으면 `docs/decisions/NNNN-<slug>.md` 작성 → `docs/decisions/README.md` 색인 갱신 → 파일 경로를 한 줄로 알림
3. **훅 (`.claude/settings.json` → `scripts/check-decisions.mjs`):** Claude가 응답을 끝낼 때마다 도는 `Stop` 훅이다. 작업 트리에 아래 변경이 있는데 `docs/decisions/`에 새 파일이나 수정이 없으면, 종료 코드 2와 안내 문구를 내서 Claude가 멈추지 않고 결정을 물어보게 한다([공식 훅 가이드](https://code.claude.com/docs/en/hooks-guide.md)).
   - 감시 대상: `package.json`의 의존성, `tsconfig*.json`, `eslint.config.*`, `packages/*/src/index.ts`(공개 API), `.github/workflows/*`, 데이터셋·실행 파일 스키마
   - 무한 반복 방지: 훅 입력의 `stop_hook_active` 값을 확인해 이미 한 번 막았으면 통과시킨다. 필드 이름과 동작은 설정 전에 공식 훅 레퍼런스에서 다시 확인한다.
   - 예외: JSDoc만 고친 경우처럼 내가 "ADR 불필요"라고 답한 변경은 Claude가 `docs/decisions/skipped.md`에 날짜·파일·이유를 한 줄 남긴다. 이것도 `docs/decisions/` 아래 변경이라 훅을 통과하고, 생략한 기록까지 남는다.

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

내부 함수 이름, 파일 안 코드 배치, 테스트 케이스 구성처럼 밖에서 보이지 않는 것만 정한다. 대신 커밋 메시지 본문에 남긴다. 공개 API, 의존성, 설정, 데이터 형식, 평가 규칙, 폴더 구조를 바꾸는 것은 전부 내 결정이다.

### 작업 단위와 커밋

1. Claude가 기능 하나의 계획을 3\~5줄로 제시하고 내가 승인한다.
2. 테스트를 먼저 또는 함께 쓴다. 오류 경로 테스트를 빠뜨리지 않는다.
3. 구현 후 `pnpm check`(린트 + 타입 검사 + 테스트)를 통과시킨다.
4. Claude가 `review` 스킬의 체크리스트로 자가 검토하고 고친 점을 보고한다.
5. 내가 diff를 읽고, `/explain`으로 모르는 부분을 풀고, 승인한다.
6. Claude가 Conventional Commits 형식으로 커밋한다. 내 승인 없이 커밋·푸시하지 않는다. AI 표시 방식은 결정 D20을 따른다.

**자가 검토 체크리스트 (`review` 스킬)**

- [ ] `any`, 근거 없는 `as` 단언, non-null `!`가 없다
- [ ] 공개 함수에 JSDoc과 `@example`이 있다
- [ ] 실패 경로에 테스트가 있다
- [ ] 새 의존성에는 ADR이 있다
- [ ] 쓰이지 않는 추상화·옵션·코드가 없다
- [ ] 주석은 "무엇"이 아니라 "왜"를 설명한다
- [ ] 오류 메시지가 고칠 방법을 말해 준다

### 모든 줄을 설명하기 위한 학습 체계

- **`/explain <파일 또는 모듈>`:** Claude가 구조와 선택 이유, 버린 대안을 설명하고 면접식 질문 5개를 낸다. 내가 답하면 채점하고 부족한 부분을 보충한다. 문답은 `.study/<모듈>.md`에 저장(공개하지 않음).
- **`/devlog`:** 하루 끝에 `docs/dev-log/YYYY-MM-DD.md`를 쓴다. 한 일, 내린 결정(ADR 링크), **AI가 틀린 것과 내가 고친 것**, 내일 할 일.
- "AI가 틀린 것" 기록은 면접에서 "AI를 어떻게 통제했나"에 답하는 가장 구체적인 자료가 된다.
- 마지막 날 `docs/ai-workflow.md`에 정리한다: 작업 방식, ADR 수, Claude 추천을 기각한 결정 수, AI 코드를 고친 대표 사례 3개.

## 일별 일정

11/4(수)부터 12일, 총 약 57시간이다. 평일 3\~4시간, 주말 7\~8시간으로 잡았고, 토스 제출은 마감 당일 18시까지 끝낸다. 이 기간에도 코딩테스트 하루 1문제(30분)는 따로 유지한다.

| 날짜 | 시간 | 할 일 | 결정 | 완료 기준 |
| --- | --- | --- | --- | --- |
| 11/3 (화) 밤 | 1h | GitHub 빈 저장소(비공개) 생성, 이 문서를 Markdown으로 내보내 `docs/PLAN.md`로 저장, Node 22+·pnpm·Claude Code 확인 | — | 로컬에 clone, PLAN.md 커밋 |
| 11/4 (수) | 4h | **기반:** 시작 프롬프트로 세션 시작. workspace, tsconfig, 린트, Vitest, 빌드, `ci.yml`, AGENTS.md·CLAUDE.md, ADR 템플릿, 스킬 4개, Stop 훅과 `check-decisions.mjs` | D1–D6, D19, D20 | 빈 패키지 3개로 CI 녹색, 훅이 ADR 없는 의존성 추가를 실제로 막음, ADR 8개 |
| 11/5 (목) | 4h | **데이터:** 설정 스키마·`defineConfig`·로더, 케이스 스키마·JSONL 로더(오류에 줄 번호), 합성 MES `schema.sql`·`seed.ts`, 스키마 추출·렌더러 | D7, D8, D11 | 시드 DB가 매번 같게 생성, `introspectSchema` 테스트 통과 |
| 11/6 (금) | 4h | **안전:** SQL 가드(차단 테스트 20개 이상: 다중 문장, 쓰기 문장, `PRAGMA`, `ATTACH`, 주석 속 세미콜론 등), worker 기반 실행기(시간·행 제한), CLI 뼈대와 `text2sql-eval guard` | D12, D13, D14 | 악성 SQL 전부 차단, 무한 재귀 CTE가 시간 제한으로 끊김 |
| 11/7 (토) | 8h | **평가 핵심:** 결과 비교기, 오류 분류, Provider 인터페이스, mock, 캐시·replay, OpenAI 호환 어댑터, 프롬프트 렌더, `cases lint`, 케이스 작성 시작 | D9, D10, D15, D16 | mock으로 케이스 1개가 끝까지 평가됨 |
| 11/8 (일) | 7h | **실행:** runner(동시성, 취소, 진행 이벤트), 실행 파일 스키마, `text2sql-eval run`, 케이스 30\~40개 완성. **SKT FLY AI 지원서 마감(2h 별도)** | — | mock 전체 실행 + 실제 모델 1회 실행 성공, 비용 기록 |
| 11/9 (월) | 3h | **리포트:** `report`(표·md·json, `--by`, `--failures`), `compareRuns`와 `compare`. **17시 토스 채용설명회** (질문 하나 준비). 범위 점검 1 | — | 프롬프트를 일부러 나쁘게 바꾸면 `compare`가 종료 코드 1 |
| 11/10 (화) | 3h | **CLI 마무리:** `init`, `schema`, 오류 메시지 정리, `--help` 예시, 실제 프로세스 e2e 테스트, `docs/reference/cli.md` | — | 새 폴더에서 `init → run --provider mock → report`가 3분 안에 됨 |
| 11/11 (수) | 4h | **llm-spec 1:** 공개 심볼·타입·JSDoc 추출, `llms.txt`·`api.md` 렌더 | D17, D18 | `core`의 `llms.txt`가 생성됨 |
| 11/12 (목) | 4h | **llm-spec 2:** `check`(diff, 종료 코드 1), CI 연결, 이 저장소에 적용. (권장) `examples`. 범위 점검 2 | — | JSDoc을 바꾸고 재생성하지 않으면 CI 실패 |
| 11/13 (금) | 4h | **문서:** README, 가이드 5개, `architecture.md`, CONTRIBUTING. (권장) publint·attw, `eval-regression.yml` | — | 처음 보는 사람이 README만 보고 실행 가능 |
| 11/14 (토) | 8h | **품질·결과:** 실제 모델 2개(또는 모델 1개 × 프롬프트 2종) 실측과 README 표, `any`·단언 전수 검사, 리팩터, `ai-workflow.md`, 전 모듈 `/explain` 복습. (권장) 데모 GIF | — | 개요의 완료 기준 전부 체크 |
| 11/15 (일) | 4h | **제출:** 깨끗한 clone에서 재현 확인, 저장소 공개 전환, README 첫 화면 점검, 지원서 작성, **18시까지 제출**, 코드 동결 | — | 제출 완료 (마감 23:59) |

**그 뒤 일정:** 11/16(월) 10시 IBK 인턴 마감 · 11/18(수) 11시 토스 과제 대상자 발표 · 11/20(금)\~26(목) 토스 과제 기간 · 11/21(토) FLY AI 면접·코딩역량평가(서류 통과 시). 과제 기간에는 저장소를 고치지 않고 `.study/` 복습에 집중한다.

## Claude Code 시작 프롬프트

이 문서를 Markdown으로 내보내 저장소의 `docs/PLAN.md`로 저장한 뒤, 저장소 폴더에서 Claude Code를 열고 아래 블록 전체를 첫 메시지로 붙여 넣는다. 두 번째 세션부터는 이 프롬프트가 필요 없다. 첫 세션에서 만든 `CLAUDE.md`와 `AGENTS.md`가 매 세션 자동으로 읽힌다.

```text
너는 이 저장소에서 나와 함께 TypeScript 라이브러리와 CLI를 만드는 페어 프로그래머다.
프로젝트 계획은 docs/PLAN.md에 있다. 무엇이든 하기 전에 그 파일을 끝까지 읽어라.
이 프롬프트와 PLAN.md가 충돌하면 이 프롬프트를 따르고, 충돌한 점을 나에게 알려라.

## 배경
- 나: 성균관대 소프트웨어학과 4학년. 제조업 MES에 agentic AI text-to-SQL을 적용하는 산학연구를 했다.
- 목표: 2026-11-15(일) 23:59 마감인 토스 Platform Engineer 인턴 서류에 이 저장소를 GitHub 링크로 낸다.
  내 제출 목표는 11/15 18:00이다.
- 토스 우대사항: 서비스가 아닌 라이브러리·CLI, 문제를 설명하는 README, 올바른 빌드·린트·의존성 설정,
  CI와 테스트, 레퍼런스·가이드, 디렉터리 구조와 코드 품질, TypeScript를 정확하게 쓰기.
- 만들 것: (1) text2sql-eval: text-to-SQL 평가 엔진(core)과 CLI(cli)
  (2) llm-spec: 공개 API에서 llms.txt를 생성·검사하는 도구
  (3) AI와 협업한 개발 과정의 기록(ADR, dev-log, ai-workflow.md)
- 나는 면접에서 이 저장소의 모든 줄을 설명해야 한다. 빨리 많이 쓰는 것보다,
  내가 이해할 수 있게 작게 나눠 쓰는 것을 우선한다.

## 절대 규칙
1. 설계 결정은 내가 한다. 공개 API, 의존성 추가·변경, 설정 파일, 데이터·실행 파일 형식, 평가 규칙,
   폴더 구조, 도구 선택은 모두 결정 대상이다. 결정이 필요하면 구현을 멈추고 decide 절차를 따른다.
   내 답 없이 추천안으로 진행하지 않는다.
2. 내가 결정하면 그 자리에서 ADR을 쓴다. "기록할까요?"라고 묻지 않는다.
3. 내 승인 없이 커밋, 푸시, 패키지 배포, 저장소 공개 전환을 하지 않는다.
4. 산학 과제의 실제 데이터·스키마·프롬프트를 쓰지 않는다. 예제는 일반적인 MES 개념으로 새로 만든 합성 데이터다.
5. API 키는 환경변수로만 읽는다. 키를 파일·로그·테스트 스냅샷에 남기지 않는다.
6. TypeScript: strict 계열 옵션 전부, any 금지, 근거 없는 as 단언·non-null ! 금지.
   불가피하면 이유를 주석으로 남기고 나에게 알린다.
7. 모르는 것(라이브러리 API, 도구의 현재 권장 사항, Claude Code 기능)은 추측하지 말고 공식 문서를 확인한다.
   확인할 수 없으면 그렇다고 말하고 확인 방법을 제안한다.

## decide 절차
결정이 필요하면 이 형식으로 묻는다.
- 결정 ID(PLAN.md의 D1~D20, 목록에 없으면 D21부터 새 번호)와 제목
- 맥락 2~3문장
- 선택지 2~4개를 표로: 안 | 장점 | 단점 | 이 프로젝트에 미치는 영향
- 너의 추천과 이유 한 문장 (도구 선택이면 확인한 공식 문서 링크)
- "어느 것으로 할까요?"로 끝낸다
독립적인 결정은 한 번에 최대 3개까지 묶어 물어도 된다.
내 답을 받으면:
- docs/decisions/NNNN-<slug>.md를 템플릿(docs/decisions/0000-template.md)대로 쓴다
- docs/decisions/README.md 색인에 한 줄을 추가한다
- "ADR 0007 기록: docs/decisions/0007-sqlite-driver.md"처럼 한 줄로 보고한다
- "이유"에는 내가 한 말을 그대로 인용한다. 내가 너의 추천을 고르지 않았으면 "AI 관여"에 그 사실을 적는다

## 작업 단위
기능 하나마다: 계획 3~5줄 제시 → 내 승인 → 테스트와 구현 → pnpm check 통과
→ review 체크리스트로 자가 검토하고 고친 점 보고 → 내가 diff 검토 → 내 승인 후 커밋.
- 커밋은 Conventional Commits 형식으로 작게. AI 참여 표시는 D20 결정을 따른다.
- 한 번에 바꾸는 파일은 되도록 5개 이하. 커지면 나눈다.
- 구현을 마치면 "이 변경에서 면접에 나올 만한 질문" 2개를 덧붙인다.

## 첫 세션에서 할 일 (순서대로)
1. docs/PLAN.md를 읽고 목표·범위·일정을 10줄 이내로 요약한다. 모호하거나 모순된 부분은 질문한다.
2. D1(이름)은 text2sql-eval로 이미 정했다(npm 스코프 @text2sql-eval/*, CLI 명령어도 text2sql-eval).
   묻지 말고 ADR만 쓴다. 결정 D2–D6, D19, D20을 decide 절차로 묻는다. 도구 선택(D4 빌드 도구 등)은
   묻기 전에 공식 문서로 현재 유지보수 상태를 확인하고 출처를 붙인다.
3. 결정을 받는 대로 기반 파일을 만든다.
   - pnpm workspace, packages/core·cli·llm-spec 빈 패키지, tsconfig.base.json,
     린트·테스트·빌드 설정, 루트 스크립트(build, test, lint, typecheck, check)
   - .github/workflows/ci.yml: lint → typecheck → test → build. llm-spec check 단계는 자리만 만든다
   - AGENTS.md: 이 프롬프트의 절대 규칙, decide 절차, 작업 단위, 명령어, 폴더 구조 요약.
     사람이 읽어도 자연스러운 협업 규약으로 쓴다. 200줄 이내
   - CLAUDE.md: 첫 줄에 @AGENTS.md, 그 아래에는 Claude Code 전용 사항만
   - docs/decisions/0000-template.md(PLAN.md의 템플릿), README.md(색인),
     0001-record-architecture-decisions.md(결정을 ADR로 기록한다는 결정 + MIT 라이선스)
   - .claude/skills/ 아래 decide, explain, review, devlog 네 스킬. 각 SKILL.md에 name과 description을 쓴다.
     decide는 네가 설계 결정을 만났을 때 스스로 불러 쓸 수 있게 description을 구체적으로 쓴다.
     explain과 devlog는 내가 부를 때만 실행되게 한다.
     필드 이름은 https://code.claude.com/docs/en/skills.md 에서 확인한다
   - scripts/check-decisions.mjs와 .claude/settings.json의 Stop 훅.
     감시 대상(package.json 의존성, tsconfig*.json, eslint.config.*, packages/*/src/index.ts,
     .github/workflows/*, 데이터셋·실행 파일 스키마)이 바뀌었는데 docs/decisions/에 변경이 없으면
     stderr에 "어떤 파일 때문에 어떤 결정을 물어야 하는지"를 쓰고 종료 코드 2로 끝낸다.
     같은 경고로 끊임없이 막지 않도록, Stop 훅 입력 필드를
     https://code.claude.com/docs/en/hooks.md 에서 확인해 처리한다.
     내가 "ADR 불필요"라고 답한 변경은 docs/decisions/skipped.md에 날짜·파일·이유를 한 줄 남긴다
     (docs/decisions/ 아래 변경이라 훅을 통과한다). git 커밋이 하나도 없는 상태도 처리한다.
     훅을 일부러 한 번 발동시켜 동작하는 것을 보여 준다
   - .gitignore에 .study/, .text2sql-eval/cache/의 비예제 캐시, .env
   - docs/dev-log/<오늘 날짜>.md
4. CI가 녹색인지 확인하고, 오늘 만든 것과 남은 것을 보고한다.

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
나에게는 한국어로 짧게. 코드·커밋·JSDoc 언어는 D19 결정을 따른다.

지금 첫 세션을 시작한다. 1번부터 진행해라.
```

## 주의사항

- **기밀:** 산학 과제의 데이터·스키마·프롬프트, 삼성SDS ERP 과제 내용은 저장소에 넣지 않는다. README의 연구 배경은 "제조 MES에 text-to-SQL을 적용한 경험에서 출발"한 정도로만 쓴다. 미게재 논문의 내용을 옮길 때는 공동 연구자와 지도교수에게 먼저 확인한다.
- **토스 과제의 AI 사용 규정:** 11/20\~26 과제에서 AI 도구를 써도 되는지 과제 안내를 먼저 확인한다. 금지라면 직접 짠다. 이 저장소의 규칙과는 별개다.
- **API 비용과 키:** 실제 모델 실행은 캐시를 켜고 돌려 재실행 비용을 없앤다. 실행 전에 케이스 수 × 모델 수로 호출 횟수를 확인한다. 키가 커밋되면 기록을 지우는 것보다 키를 바로 폐기하는 것이 먼저다.
- **공개 전환 전 점검 (11/15):** git 기록 전체의 비밀값 검사, `.env`·`.study/`가 빠졌는지, 공개해도 되는 예제 캐시만 있는지 확인한다.
- **제출본 고정:** 제출 직전 커밋에 `v0.1.0` 태그를 달고 README에 "서류 제출 시점: v0.1.0"을 적는다. 마감 뒤 커밋이 있어도 제출 시점을 구분할 수 있다.
- **커밋 기록은 있는 그대로:** 날짜를 고치거나 AI 표시를 지우지 않는다. "AI를 어떻게 통제했나"라는 어필이 기록의 일관성에 달려 있다.
- **학업과의 충돌:** 이번 학기 12학점의 과제·시험 일정을 일정표에 겹쳐 보고, 겹치는 날은 미리 범위 축소 규칙을 적용한다.
- **다음 쓰임:** 토스 결과와 관계없이 이 저장소는 SK하이닉스 경험기술서 1번(AI 활용 경험)의 핵심 소재다. "연구 → 평가 도구화 → AI 협업 개발 체계"의 흐름으로 쓴다.

## 출처

- [토스: Platform Engineer 인턴십 공고](https://toss.im/career/job-detail?gh_jid=8096691003)
- [Claude Code: CLAUDE.md와 AGENTS.md, @ 가져오기](https://code.claude.com/docs/en/memory.md)
- [Claude Code: 스킬](https://code.claude.com/docs/en/skills.md)
- [Claude Code: 훅 가이드](https://code.claude.com/docs/en/hooks-guide.md)
- [Claude Code: 훅 레퍼런스](https://code.claude.com/docs/en/hooks.md)
