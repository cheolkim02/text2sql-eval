# 0013. 타입 검사는 pyright strict 모드에 규칙 1개를 더해 한다

- 날짜: 2026-11-07
- 상태: 채택
- 결정자: 사용자
- AI 관여: 선택지 조사·추천 (Claude 추천: pyright strict + `reportUnnecessaryTypeIgnoreComment`, 채택 여부: 예). 사용자가 도구를 잘 모른다고 밝혀 추천을 따른 결정이다.
- 관련 결정 ID: D11
- 편집: 2026-11-15, 공개 전에 프로젝트와 무관한 개인 정보를 지움([0047](0047-remove-unrelated-personal-content.md))

## 맥락
"타입을 정확하게 쓰려는 고민"(0003)을 보여줄 타입 검사기를 정해야 했다. 판정 결과를 `Correct | Incorrect | ExecError` 같은 판별 유니언으로 표현할 계획이라, 빠진 경우를 잡아 주는 검사가 중요하다.

## 선택지
| 안 | 장점 | 단점 |
| --- | --- | --- |
| pyright strict | 타입을 모르는 값(`Unknown`)과 `match`의 빠진 경우까지 오류로 잡음, Production/Stable(1.1.414) | Node.js 기반이라 PyPI 래퍼로 설치, 외부 라이브러리 타입이 부실하면 경고가 많을 수 있음 |
| mypy `--strict` | 표준 타입 검사기, Stable(2.4.1) | 라이브러리에서 온 모르는 타입을 덜 엄격하게 다룸 |
| 둘 다 | 이중 검사 | 두 도구의 판단 차이를 맞추는 시간 |
| ty | 매우 빠름 | Beta(0.0.99) |

## 결정
pyright를 `typeCheckingMode = "strict"`로 쓰고, strict에서도 꺼져 있는 `reportUnnecessaryTypeIgnoreComment`를 `"error"`로 켠다.

## 이유
> "추천대로 pyright strict + 규칙 1개 추가. 다 뭔지 몰라."

보충: 사용자는 타입 검사가 무엇인지 모른다고 밝혔다. 이 결정은 Claude의 추천을 따른 것이고, 타입 검사의 역할과 이 프로젝트에서 잡아 주는 실수를 `/explain`으로 학습해야 한다. 추가 규칙은 "근거 없는 `# type: ignore` 금지" 규칙을 사람이 아니라 도구가 강제하게 하려는 것이다.

## 결과
- `src/`, `tests/`, `examples/`를 모두 검사한다.
- 외부 라이브러리(예: sqlglot) 때문에 `Unknown` 오류가 많으면, 그 경계에서만 타입을 좁히는 함수를 두고 이유를 주석으로 남긴다. 규칙을 끄려면 새 ADR이 필요하다.
