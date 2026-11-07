---
name: review
description: Self-review the current diff against this repository's checklist (types, tests, dependencies, determinism, error messages) and report what was fixed and what remains. Use after implementing a feature and before asking the user to review the diff, or when the user runs /review.
---

# 자가 검토

현재 변경(`git diff`와 새 파일)을 아래 체크리스트로 검사한다. 고칠 수 있는 것은 고치고, 결정이 필요한 것은 `decide` 절차로 넘긴다.

## 1. 자동 검사

`sh scripts/check.sh`를 실행해 통과시킨다. 이 스크립트는 ruff check, ruff format --check, pyright, pytest를 돈다.

## 2. 체크리스트

- [ ] 공개 API에 `Any`가 없고, 근거 없는 `cast`·`# type: ignore`가 없다
- [ ] 판별 유니언을 다루는 분기에 `assert_never` 전수 검사가 있다
- [ ] 공개 함수에 docstring(영어)과 사용 예시가 있다
- [ ] 실패 경로에 테스트가 있다
- [ ] 새 의존성, 설정 변경, 형식 변경에는 ADR이 있다
- [ ] 쓰이지 않는 추상화·옵션·코드가 없다
- [ ] 주석은 "무엇"이 아니라 "왜"를 설명한다
- [ ] 오류 메시지가 무엇이 잘못됐는지와 고칠 방법을 말해 준다(영어)
- [ ] 사실 추출·판정에 비결정적 요소가 없다
  - 무작위, 현재 시각, 순서 없는 집합의 순회 결과를 그대로 출력하는 것 등
- [ ] API 키나 비밀값이 코드·로그·스냅샷에 없다
- [ ] Python 3.11에서 동작하는 문법만 쓴다(`type` 문, PEP 695 제네릭 문법 금지)
- [ ] 한 번에 바꾼 파일이 5개를 넘으면, 나눌 수 있는지 검토했다

## 3. 보고

표 하나로 보고한다. 열: 항목 | 결과(통과 / 고침 / 남음) | 내용

- "고침"은 무엇을 어떻게 고쳤는지 적는다.
- "남음"은 왜 남겼고 무엇이 필요한지 적는다.
