# 0029. baseline 예제는 공식 openai SDK를 쓰고, examples 의존성 그룹에만 둔다

- 날짜: 2026-11-09
- 상태: 채택
- 결정자: 사용자
- AI 관여: 선택지 조사·추천 (Claude 추천: 공식 SDK를 examples 그룹에만, 채택 여부: 예)
- 관련 결정 ID: D34

## 맥락
`examples/baseline` 스크립트가 OpenAI API를 부르는 방식을 정해야 했다. 도구 본체는 LLM을 부르지 않으므로(0004) 사용자 설치에는 영향이 없지만, 새 의존성이다.

## 선택지
| 안 | 장점 | 단점 |
| --- | --- | --- |
| 공식 `openai` SDK (examples 그룹에만) | 재시도·오류 타입·응답 파싱이 갖춰짐, 실제로 쓰는 방식 | 예제용 의존성 1개와 그 하위 의존성 |
| 표준 라이브러리 `urllib`로 직접 호출 | 의존성 0개 | 재시도와 오류 처리를 직접 써야 해 예제가 길어짐 |

## 결정
`pyproject.toml`의 `[dependency-groups]`에 `examples` 그룹을 만들고 `openai`를 넣는다. 패키지의 런타임 의존성(`[project] dependencies`)에는 넣지 않는다.

## 이유
추천안(공식 SDK를 `examples` 그룹에만)을 채택했다.

## 결과
- 예제 실행은 `uv run --group examples python examples/baseline/predict.py ...` 형태가 된다.
- CI는 `examples` 그룹을 설치하지 않으므로, baseline 스크립트는 타입 검사에서 openai 패키지를 찾지 못할 수 있다. 설정 방법은 구현 계획에서 함께 제안한다.
- API 키는 환경변수(`OPENAI_API_KEY`)로만 읽는다.
