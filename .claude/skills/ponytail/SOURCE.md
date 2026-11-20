# ponytail 출처

`ponytail`, `ponytail-review`, `ponytail-audit` 세 skill은 외부 저장소의 파일을 고치지 않고 그대로 복사한 것이다([ADR 0049](../../../docs/decisions/0049-ponytail-vendored-skills.md)).

- 원본: [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail)
- 버전: v5.3.3 (커밋 `7801d061243d7b753bad0e0b3c057cd250b11755`)
- 복사한 날: 2026-11-20
- 라이선스: MIT. 전문은 이 폴더의 [LICENSE](LICENSE)이고, 세 폴더 모두에 적용된다.

| 이 저장소 | 원본 경로 |
| --- | --- |
| `.claude/skills/ponytail/SKILL.md` | `skills/ponytail/SKILL.md` |
| `.claude/skills/ponytail-review/SKILL.md` | `skills/ponytail-review/SKILL.md` |
| `.claude/skills/ponytail-audit/SKILL.md` | `skills/ponytail-audit/SKILL.md` |
| `.claude/skills/ponytail/LICENSE` | `LICENSE` |

플러그인의 훅(비용 표시 띠, 기록, 웹훅)과 나머지 명령(`ponytail-debt`, `ponytail-gain`, `ponytail-help`)은 가져오지 않았다.

이 저장소의 규칙과 다를 때는 `AGENTS.md`의 "ponytail" 절이 우선한다([ADR 0050](../../../docs/decisions/0050-ponytail-precedence.md)).

## 업데이트하는 법

1. 원본의 새 릴리스 태그에서 위 네 파일을 다시 받는다.
2. 바뀐 내용을 읽고, `AGENTS.md`와 부딪히는 곳이 없는지 확인한다.
3. 이 파일의 버전, 커밋, 날짜를 고친다.
