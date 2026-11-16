# AGENTS.md

이 저장소에서 사람과 AI 코딩 에이전트가 함께 일하는 규약이다. 사람이 읽어도 그대로 통하도록 쓴다. 전체 계획은 [docs/PLAN.md](docs/PLAN.md), 결정 기록은 [docs/decisions/](docs/decisions/README.md)에 있다.

## 프로젝트

`text2sql-eval`은 text-to-SQL 실험의 예측 파일을 받아 다음을 하는 Python 라이브러리이자 CLI다.

- EX(실행 정확도)를 판정한다.
- 오답에서 "무엇이 다른가"를 **AI 없이** 근거와 함께 추출한다.
- 판정을 믿기 어려운 케이스에 플래그를 붙인다.
- 두 실행을 케이스 단위로 비교한다.
- HTML 리포트와 CSV를 만든다.

도구는 LLM을 부르지 않는다([0004](docs/decisions/0004-prediction-file-input.md)).

- **사용자(사람):** 설계, 결정, 리뷰
- **에이전트:** 선택지 제시, 구현, 테스트, 문서 초안, 기록
- 사용자는 이 저장소의 모든 줄을 설명할 수 있어야 한다. 빨리 많이 쓰는 것보다, 사용자가 이해할 수 있게 작게 나눠 쓰는 것을 우선한다.

## 절대 규칙

1. **설계 결정은 사용자가 한다.** 공개 API, 의존성 추가·변경, 설정 파일, 데이터·예측·실행 파일 형식, 판정·사실·플래그 규칙, 폴더 구조, 도구 선택은 모두 결정 대상이다. 결정이 필요하면 구현을 멈추고 아래 "결정 절차"를 따른다. 답 없이 추천안으로 진행하지 않는다.
2. **사용자가 결정하면 그 자리에서 ADR을 쓴다.** "기록할까요?"라고 묻지 않는다.
3. **사용자 승인 없이** 커밋, 푸시, 패키지 배포, 저장소 공개 전환을 하지 않는다. `main`에는 사용자가 PR을 merge해서만 반영된다.
4. **예제 데이터는 공개 데이터만 쓴다.** 지금은 `examples/bird-mini`(BIRD dev, CC BY-SA 4.0)다.
5. **API 키는 환경변수로만 읽는다.** 키를 파일·로그·테스트 스냅샷에 남기지 않는다. 도구 본체는 API 키를 쓰지 않는다.
6. **타입:** pyright strict 0 오류. 공개 API에 `Any`를 쓰지 않는다. 근거 없는 `cast`·`# type: ignore`를 쓰지 않는다. 불가피하면 이유를 주석으로 남기고 사용자에게 알린다.
7. **사실 추출과 판정은 결정적이어야 한다.** LLM, 무작위성, 시간에 따라 달라지는 값을 쓰지 않는다.
8. **모르는 것은 추측하지 않는다.** 라이브러리 API, 도구의 현재 권장 사항, BIRD 공식 평가 규칙, 에이전트 기능은 공식 문서나 원본 코드로 확인한다. 확인할 수 없으면 그렇다고 말하고 확인 방법을 제안한다.

## 결정 절차

결정이 필요하면 이 형식으로 묻는다(`decide` 스킬).

- 결정 ID와 제목: PLAN.md의 D 번호를 쓰고, 목록에 없으면 다음 빈 번호를 붙인다.
- 맥락 2~3문장
- 선택지 2~4개를 표로: 안 | 장점 | 단점 | 이 프로젝트에 미치는 영향
- 에이전트의 추천과 이유 한 문장. 도구 선택이면 확인한 공식 문서 링크를 붙인다.
- "어느 것으로 할까요?"로 끝낸다.

서로 독립적인 결정은 한 번에 최대 3개까지 묶어 물을 수 있다.

답을 받으면 다음을 한다.

1. `docs/decisions/0000-template.md` 형식으로 `docs/decisions/NNNN-<slug>.md`를 쓴다.
   - "이유"에는 사용자가 밝힌 이유를 평서문으로 쓴다. 대화를 인용하지 않는다. 이유 없이 추천을 따랐으면 "추천안(…)을 채택했다"고 쓴다([0048](docs/decisions/0048-adr-reasons-without-quotes.md)).
   - 사용자가 추천을 고르지 않았으면 "AI 관여"에 그 사실을 적는다.
   - 사용자가 잘 모른다고 하고 추천을 따랐다면, 그 사실과 학습할 거리를 적는다.
2. `docs/decisions/README.md` 색인에 한 줄을 추가하고, PLAN.md의 결정 표에 "결정됨"을 표시한다.
3. "ADR 0018 기록: docs/decisions/0018-....md"처럼 한 줄로 보고한다.

사용자가 "ADR 불필요"라고 답한 변경은 `docs/decisions/skipped.md`에 날짜·파일·이유를 한 줄로 남긴다.

**에이전트가 혼자 정해도 되는 것:** 밖에서 보이지 않는 것만이다. 내부 함수 이름, 파일 안 코드 배치, 테스트 케이스 구성 등이 해당한다. 이런 것은 커밋 메시지 본문에 남긴다.

## 작업 단위

기능 하나마다 아래 순서로 진행한다.

1. 에이전트가 계획을 3~5줄로 제시하고, 사용자가 승인한다.
2. 테스트를 먼저 또는 함께 쓴다. 실패 경로 테스트를 빠뜨리지 않는다.
3. 구현한 뒤 `sh scripts/check.sh`를 통과시킨다.
4. `review` 스킬의 체크리스트로 자가 검토하고, 고친 것과 남은 것을 보고한다.
5. 사용자가 diff를 읽고, 모르는 부분은 `/explain`으로 푼 뒤 승인한다.
6. 승인을 받으면 커밋한다. 형식은 아래 "커밋"을 따른다.

덧붙일 것:

- 한 번에 바꾸는 파일은 되도록 5개 이하로 한다. 커지면 나눈다.
- 구현을 마치면 "이 변경을 설명할 때 받을 만한 질문" 2개를 덧붙인다.

## 명령어

```sh
uv sync                     # 가상환경 생성과 의존성 설치 (uv.lock 기준)
sh scripts/check.sh         # CI와 같은 검사: ruff check → ruff format --check → pyright → pytest
uv run pytest               # 테스트만
uv run pytest tests/test_bird_mini.py -k checksum   # 일부만
uv run ruff format .        # 포맷 적용
uv run pyright              # 타입 검사만
uv build                    # wheel과 sdist 빌드 (dist/)
```

- 개발 환경은 가장 낮은 지원 버전(Python 3.11, `.python-version`)에서 돈다. 3.12 이상 전용 문법은 쓰지 않는다([0009](docs/decisions/0009-python-version.md)).
- CI(`.github/workflows/ci.yml`)는 3.11~3.15에서 테스트한다.

## 도구 설정 요약

| 도구 | 설정 | 결정 |
| --- | --- | --- |
| uv, uv_build | `pyproject.toml`, `uv.lock` 커밋 | [0010](docs/decisions/0010-uv-and-uv-build.md) |
| Ruff | 기본 규칙, 줄 길이 88자. Markdown 안의 Python 코드 블록도 포맷한다 | [0011](docs/decisions/0011-ruff.md), [0015](docs/decisions/0015-ruff-default-rules.md) |
| pyright | strict + `reportUnnecessaryTypeIgnoreComment`, 대상 `src`·`tests`·`examples` | [0013](docs/decisions/0013-pyright-strict.md) |
| pytest, Hypothesis, syrupy | 단위·속성 기반·스냅샷 테스트. 스냅샷은 사용자가 diff를 승인한 뒤에만 갱신한다 | [0014](docs/decisions/0014-pytest-hypothesis-syrupy.md) |

규칙을 바꾸려면 새 ADR이 필요하다.

## 폴더 구조

```text
src/text2sql_eval/   라이브러리와 CLI (공개 API는 __init__.py에서만 내보낸다)
tests/               테스트 (네트워크 없이 돈다)
examples/bird-mini/  BIRD dev 일부 (CC BY-SA 4.0, 출처는 SOURCE.md)
scripts/             개발용 스크립트 (check.sh)
docs/PLAN.md         계획서
docs/decisions/      ADR과 색인
docs/dev-log/        날짜별 개발 기록
.study/              사용자의 학습 노트 (gitignore, 공개하지 않음)
```

앞으로 생길 모듈과 의존 방향은 PLAN.md의 "폴더 구조"를 따른다. 의존 방향: `cli → report·compare → judge·facts → execution·datasets`

## 언어와 커밋

- **한국어:** README 본문(맨 위에 영어 요약 한 단락), `docs/` 아래 문서, ADR, 개발 기록([0016](docs/decisions/0016-documentation-language.md))
- **영어:** 코드 식별자, 주석, docstring, 커밋 메시지, CLI 출력과 오류 메시지
- **커밋:** 제목은 Conventional Commits 형식이다(`feat`, `fix`, `docs`, `test`, `refactor`, `build`, `ci`, `chore`, 범위는 선택). 본문에는 무엇을 왜 바꿨는지와 관련 ADR 번호를 쓴다. AI가 함께 쓴 커밋은 본문 끝에 `Co-Authored-By` 줄을 붙인다([0017](docs/decisions/0017-commit-conventions.md)).
- 이미 push한 커밋은 고치지 않는다. 날짜를 바꾸거나 AI 표시를 지우지 않는다.

## 매일 세션을 시작할 때

1. PLAN.md "일별 일정"에서 오늘 날짜의 행을 읽는다.
2. 가장 최근 `docs/dev-log/`를 읽는다.
3. 오늘 할 일과 필요한 결정을 5줄로 제시한다.
4. 일정보다 늦었으면 PLAN.md의 "범위 축소 규칙"을 근거로 무엇을 줄일지 제안하고 사용자의 결정을 받는다.

## 말투

- 사용자에게는 한국어로 짧게 쓴다.
- 모르는 개념은 이 프로젝트의 실제 예시로 설명한다.
