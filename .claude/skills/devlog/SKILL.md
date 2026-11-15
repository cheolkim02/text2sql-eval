---
name: devlog
description: Write today's development log to docs/dev-log/YYYY-MM-DD.md - what was done, decisions made (with ADR links), what the AI got wrong and how the user corrected it, and tomorrow's plan. Only when the user runs /devlog.
disable-model-invocation: true
---

# 개발 기록

오늘 날짜로 `docs/dev-log/YYYY-MM-DD.md`를 쓴다. 이미 있으면 내용을 합친다.

## 근거로 쓸 자료

- 오늘의 `git log`와 커밋 본문
- 오늘 추가·수정된 `docs/decisions/` 파일
- 이 세션의 대화
- `docs/PLAN.md`의 오늘 일정 행

## 형식

```markdown
# YYYY-MM-DD

## 한 일
- 일정 대비: 계획(PLAN.md 오늘 행)과 실제의 차이

## 내린 결정
- [NNNN 제목](../decisions/NNNN-slug.md): 한 줄 요약 (Claude 추천 채택 / 기각)

## AI가 틀린 것과 내가 고친 것
- 파일과 내용을 구체적으로: 무엇이 틀렸고, 어떻게 알아챘고, 어떻게 고쳤는지

## 배운 것

## 내일 할 일
- PLAN.md 내일 행 기준, 밀린 것 포함
```

## 원칙

"AI가 틀린 것"은 "AI를 어떻게 통제했나"를 설명하는 핵심 자료다.

- 부풀리거나 지어내지 않는다.
- 없었으면 "없음"이라고 쓴다.
- 사용자가 Claude의 추천을 기각한 결정도 여기에 함께 적는다.

다 쓰면 사용자에게 보여주고, 고칠 곳을 묻는다.
