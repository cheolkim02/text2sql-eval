---
name: decide
description: Ask the user to make a design decision and record it as an ADR. Use this whenever work reaches a choice that belongs to the user in this repository - a new or changed dependency, public API, configuration file, data/prediction/run file format, judging/fact/flag rule, folder structure, or tool choice - before writing the code that depends on it. Also use when the user types /decide <topic>.
argument-hint: "[topic]"
---

# 설계 결정 절차

주제: $ARGUMENTS (비어 있으면 지금 작업 중에 생긴 결정)

구현을 멈추고 아래 순서를 따른다. 답을 받기 전에는 추천안으로 진행하지 않는다.

## 1. 묻기

다음 형식으로 사용자에게 묻는다.

1. **결정 ID와 제목:** `docs/PLAN.md` "내가 내릴 결정" 표의 D 번호. 표에 없으면 다음 빈 번호를 붙이고, 표에 행을 추가한다.
2. **맥락:** 2~3문장. 무엇을 왜 지금 정해야 하는지.
3. **선택지:** 2~4개를 표로 쓴다. 열: 안 | 장점 | 단점 | 이 프로젝트에 미치는 영향
4. **추천:** 추천안과 이유 한 문장.
   - 도구나 라이브러리를 고르는 결정이면, 묻기 전에 공식 문서와 PyPI로 현재 버전과 유지보수 상태를 확인하고 출처 링크를 붙인다.
5. 마지막 문장은 "어느 것으로 할까요?"로 끝낸다.

추가 규칙:

- 서로 독립적인 결정은 한 번에 최대 3개까지 묶어 물을 수 있다.
- 사용자가 개념을 모를 수 있으니, 낯선 용어는 이 프로젝트의 예시로 한 줄씩 풀어 쓴다.

## 2. 기록하기 (답을 받은 즉시, 묻지 않고)

1. **ADR 작성:** `docs/decisions/0000-template.md` 형식으로 `docs/decisions/NNNN-<slug>.md`를 쓴다. NNNN은 마지막 번호 + 1이다.
   - 결정자: 항상 "사용자"
   - 이유: 사용자가 밝힌 이유를 평서문으로 쓴다. 사용자의 말을 `>` 인용으로 옮기지 않는다. 이유 없이 추천을 따랐으면 "추천안(<안>)을 채택했다"고 쓴다. 필요하면 "보충:"을 덧붙인다.
   - AI 관여: "Claude 추천: <안>, 채택 여부: 예/아니오"
     - 사용자가 추천을 고르지 않았으면 "아니오"로 적는다.
     - 사용자가 잘 모른다고 하고 추천을 따랐다면, 그 사실과 `/explain`으로 학습할 거리를 적는다.
2. **색인 갱신:** `docs/decisions/README.md` 표에 한 줄을 추가한다.
3. **계획서 갱신:** `docs/PLAN.md` 결정 표의 해당 행 "추천" 칸에 `**결정됨: <요약> (ADR NNNN)**`을 쓴다.
4. **보고:** "ADR NNNN 기록: docs/decisions/NNNN-<slug>.md"처럼 한 줄로 알린다.

사용자가 "ADR 불필요"라고 답하면, ADR 대신 `docs/decisions/skipped.md`에 `- YYYY-MM-DD, <파일>, <이유>` 한 줄을 남긴다. 파일이 없으면 만든다.
