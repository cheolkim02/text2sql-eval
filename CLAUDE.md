@AGENTS.md

## Claude Code 전용

- 프로젝트 스킬은 `.claude/skills/`에 있다.
  - `decide`: 설계 결정이 생기면 스스로 불러 쓴다.
  - `review`: 구현을 마치면 스스로 불러 자가 검토한다.
  - `explain`, `devlog`: 사용자가 `/explain <경로>`, `/devlog`로 부를 때만 실행한다.
- 클라우드 세션에서 종료 검사가 커밋·push를 요구하면, 작업 브랜치에만 커밋·push하고 무엇을 왜 올렸는지 사용자에게 알린다. `main`에는 PR을 거쳐서만 반영한다.
- 도구 버전이나 Claude Code 기능(스킬, 훅, 설정)을 쓰기 전에는 공식 문서를 확인한다. 예: https://code.claude.com/docs/en/skills.md, https://code.claude.com/docs/en/hooks.md
