# 0049. ponytail은 skill 파일 3개를 저장소에 복사해 쓴다

- 날짜: 2026-11-20
- 상태: 채택
- 결정자: 사용자
- AI 관여: 원본 프롬프트·명령·라이선스 확인과 선택지 조사·추천 (Claude 추천: skill 파일을 저장소에 복사, 채택 여부: 예)
- 관련 결정 ID: D45

## 맥락
사용자가 [ponytail](https://github.com/DietrichGebert/ponytail)을 저장소에 넣고, 이를 적용해 코드를 정리하고 싶어 했다. ponytail은 "필요한 만큼만, 가장 작은 변경으로" 코드를 쓰게 하는 Claude Code skill이다(MIT). 저장소 전체를 점검하는 `/ponytail-audit`, 변경을 리뷰하는 `/ponytail-review`가 있다. 넣는 방식에 따라 무엇이 저장소에 남는지, 다른 사람과 클라우드 세션에도 적용되는지가 달라진다.

## 선택지
| 안 | 장점 | 단점 |
| --- | --- | --- |
| skill 파일 3개(`ponytail`, `ponytail-review`, `ponytail-audit`)를 `.claude/skills/`에 복사하고 출처·라이선스 표기 | 저장소를 받은 누구나, 클라우드 세션에서도 같은 규칙으로 동작함. 플러그인 훅과 외부 전송이 없음. 버전이 고정됨 | 원본 업데이트를 손으로 따라가야 함. 외부 글이 저장소에 들어옴 |
| 규칙은 `AGENTS.md`에 한국어로 녹이고, `audit`·`review` skill만 복사 | 규칙이 한 곳에 모이고 다른 에이전트도 따름 | 원본과 문장이 달라져 업데이트 반영이 어려움 |
| 저장소에는 넣지 않고 사용자의 Claude Code에 플러그인으로 설치 | 원본 그대로, 자동 업데이트, 비용 표시 띠 등 전체 기능 | 저장소에 남지 않음. 플러그인 훅이 매 턴 돌고 `~/.config/ponytail/`에 기록함 |

## 결정
ponytail v5.3.3(커밋 `7801d06`)의 `skills/ponytail`, `skills/ponytail-review`, `skills/ponytail-audit`의 `SKILL.md`를 고치지 않고 `.claude/skills/` 아래 같은 이름의 폴더로 복사한다. 원본 `LICENSE`와 출처·업데이트 방법(`SOURCE.md`)을 `.claude/skills/ponytail/`에 둔다.

## 이유
추천안(skill 파일을 저장소에 복사)을 채택했다. 저장소에 넣는다는 목적에 맞고, 이 저장소의 클라우드 세션에서도 바로 쓸 수 있다. 훅 없이 프롬프트만 들어오므로 무엇이 동작하는지 설명하기 쉽다.

## 결과
- 복사 전에 세 `SKILL.md`와 `LICENSE`를 모두 읽었다. 다른 파일을 참조하지 않고, `main`과 v5.3.3의 내용이 같았다(2026-11-20 확인).
- 플러그인의 훅(비용 표시 띠, 작업 기록, 웹훅)과 `ponytail-debt`, `ponytail-gain`, `ponytail-help`는 가져오지 않았다.
- 원본은 고치지 않는다. 이 저장소의 규칙과 다른 점은 `AGENTS.md`에서 정한다(0050).
- 업데이트는 손으로 한다. 새 태그에서 다시 받아 읽고, `SOURCE.md`의 버전과 커밋을 고친다.
- 다음 작업: `/ponytail-audit` 방식으로 저장소 전체를 점검하고, 사용자가 고른 항목만 작은 PR로 고친다.
