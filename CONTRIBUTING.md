# 기여 안내

이 저장소에서 코드를 고치는 방법이다. 사람과 AI 코딩 에이전트가 함께 일하는 규칙은 [AGENTS.md](AGENTS.md)에 있고, 이 문서와 같은 내용을 따른다.

## 개발 환경

[uv](https://docs.astral.sh/uv/)를 쓴다([ADR 0010](docs/decisions/0010-uv-and-uv-build.md)). 개발은 지원하는 가장 낮은 버전인 Python 3.11에서 한다(`.python-version`).

```sh
git clone https://github.com/cheolkim02/text2sql-eval.git
cd text2sql-eval
uv sync
```

`uv sync`는 `uv.lock`에 고정된 버전으로 가상환경(`.venv`)을 만들고, 패키지와 개발 도구를 설치한다.

## 검사

```sh
sh scripts/check.sh
```

CI와 같은 순서로 네 가지를 돈다. 모두 통과해야 merge한다.

| 단계 | 명령 | 결정 |
| --- | --- | --- |
| 린트 | `uv run ruff check .` | [ADR 0011](docs/decisions/0011-ruff.md), [0015](docs/decisions/0015-ruff-default-rules.md) |
| 포맷 | `uv run ruff format --check .` (Markdown 안의 Python 코드 블록 포함) | 같음 |
| 타입 | `uv run --group examples pyright` (strict) | [ADR 0013](docs/decisions/0013-pyright-strict.md) |
| 테스트 | `uv run pytest` | [ADR 0014](docs/decisions/0014-pytest-hypothesis-syrupy.md) |

포맷은 `uv run ruff format .`으로 고친다. 테스트 일부만 돌리려면 `uv run pytest tests/test_judge.py -k empty`처럼 쓴다. 테스트는 네트워크 없이 돈다.

CI(`.github/workflows/ci.yml`)는 여기에 더해 Python 3.11~3.15에서 테스트하고, wheel을 빌드해 새 환경에 설치한 뒤 CLI를 돌려 본다.

## 코드 규칙

- **Python 3.11 문법만 쓴다.** `type` 문이나 `def f[T]()` 같은 3.12 이상 문법은 쓰지 않는다. 제네릭은 `TypeVar`로 쓴다([ADR 0009](docs/decisions/0009-python-version.md)).
- **타입:** 공개 API에 `Any`를 쓰지 않는다. 근거 없는 `cast`나 `# type: ignore`를 쓰지 않는다. 꼭 필요하면 이유를 주석으로 남긴다.
- **결정성:** 판정과 차이 계산에 LLM, 무작위, 시간에 따라 달라지는 값을 쓰지 않는다.
- **오류:** 사용자 입력 문제는 `InputError(path, problem, location=..., hint=...)`로 낸다. 무엇이 잘못됐고 어떻게 고치는지를 영어로 쓴다.
- **공개 API:** `src/text2sql_eval/__init__.py`의 `__all__`에 있는 것만 공개다. 바꾸면 `tests/test_public_api.py`와 [API 레퍼런스](docs/reference/api.md)를 함께 고친다.
- **테스트:** 기능과 함께, 실패하는 경로까지 쓴다. syrupy 스냅샷은 바뀐 내용을 사람이 확인한 뒤에만 갱신한다.

## 문서

- 언어: README 본문, `docs/` 아래 문서, ADR은 한국어로 쓴다. 코드 식별자, 주석, docstring, 커밋 메시지, CLI 출력은 영어로 쓴다([ADR 0016](docs/decisions/0016-documentation-language.md)).
- Markdown으로만 쓴다([ADR 0041](docs/decisions/0041-markdown-docs.md)). `tests/test_docs.py`가 레퍼런스와 코드가 맞는지, 링크가 살아 있는지 검사한다. 옵션이나 실행 파일 필드를 더하면 레퍼런스도 함께 고친다.
- 숫자와 출력 예시는 실제로 돌린 결과를 붙인다.

## 설계 결정

공개 API, 의존성, 설정 파일, 데이터·예측·실행 파일 형식, 판정·차이·플래그 규칙, 폴더 구조, 도구 선택은 결정 대상이다.

1. 결정할 것이 생기면 선택지를 장단점과 함께 표로 정리한다.
2. 결정하면 [`docs/decisions/0000-template.md`](docs/decisions/0000-template.md) 형식으로 ADR을 쓴다.
3. [색인](docs/decisions/README.md)에 한 줄을 더한다.

ADR에는 결정한 사람의 말을 그대로 인용한다.

## 커밋과 PR

- 제목은 [Conventional Commits](https://www.conventionalcommits.org/) 형식이다. `feat`, `fix`, `docs`, `test`, `refactor`, `build`, `ci`, `chore`를 쓰고, 범위는 쓰지 않아도 된다. 예: `fix(cli): say "1 error", not "1 errors"`.
- 본문에는 무엇을 왜 바꿨는지와 관련 ADR 번호를 쓴다.
- AI가 함께 쓴 커밋은 본문 끝에 `Co-Authored-By` 줄을 붙인다([ADR 0017](docs/decisions/0017-commit-conventions.md)).
- 이미 push한 커밋은 고치지 않는다.
- `main`에는 PR로만 반영하고, CI가 모두 통과해야 merge한다.
