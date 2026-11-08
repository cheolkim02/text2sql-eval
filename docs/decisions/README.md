# 결정 기록 (ADR)

이 저장소의 설계 결정 목록이다. 결정자는 모두 사용자이고, AI가 관여한 방식은 각 문서의 "AI 관여"에 적는다. 형식은 [0000-template.md](0000-template.md)를 따른다.

| 번호 | 결정 | 관련 ID | 날짜 | 상태 |
| --- | --- | --- | --- | --- |
| [0001](0001-record-architecture-decisions.md) | 설계 결정을 ADR로 기록, 코드 MIT·예제 데이터 CC BY-SA 4.0 | — | 2026-11-03 | 채택 |
| [0002](0002-project-name.md) | 프로젝트 이름 `text2sql-eval` | D1 | 2026-11-03 | 채택 |
| [0003](0003-language-python.md) | 구현 언어 Python | D2 | 2026-11-04 | 채택 |
| [0004](0004-prediction-file-input.md) | 예측 파일 입력, LLM 호출 없음 | D3 | 2026-11-04 | 채택 |
| [0005](0005-feature-priorities.md) | 대표: 결정적 사실 추출, 부대표: 실행 비교 | D4 | 2026-11-04 | 채택 |
| [0006](0006-demo-dataset-bird-subset.md) | 시연 데이터 BIRD dev 3개 DB, 432문제 | D5 | 2026-11-04 | 채택 |
| [0007](0007-report-outputs-html-csv.md) | 결과 화면 HTML 리포트 + CSV | D6 | 2026-11-04 | 채택 |
| [0008](0008-out-of-scope-and-roadmap.md) | 범위에서 뺄 것과 로드맵 | D7 | 2026-11-04 | 채택 |
| [0009](0009-python-version.md) | 지원 Python 3.11+ | D8 | 2026-11-07 | 채택 |
| [0010](0010-uv-and-uv-build.md) | 프로젝트 관리 uv, 빌드 백엔드 uv_build | D9 | 2026-11-07 | 채택 |
| [0011](0011-ruff.md) | 린트·포맷 Ruff | D10 | 2026-11-07 | 채택 |
| [0012](0012-schedule-adjustment-1107.md) | 일정 지연에 따른 일정·범위 조정 | — | 2026-11-07 | 채택 |
| [0013](0013-pyright-strict.md) | 타입 검사 pyright strict + 규칙 1개 | D11 | 2026-11-07 | 채택 |
| [0014](0014-pytest-hypothesis-syrupy.md) | 테스트 pytest + Hypothesis + syrupy | D12 | 2026-11-07 | 채택 |
| [0015](0015-ruff-default-rules.md) | Ruff 기본 규칙, 줄 길이 88자 | D28 | 2026-11-07 | 채택 |
| [0016](0016-documentation-language.md) | 문서 언어: README 한국어 + 영어 요약, 코드·커밋 영어 | D25 | 2026-11-07 | 채택 |
| [0017](0017-commit-conventions.md) | Conventional Commits + AI 참여 표시 | D26 | 2026-11-07 | 채택 |
| [0018](0018-prediction-file-formats.md) | 예측 파일: 한 줄 한 SQL 텍스트 + 자체 JSONL | D27 | 2026-11-08 | 채택 |
| [0019](0019-dataclasses-and-manual-validation.md) | 데이터 모델 dataclass, 입력 검증 직접 구현 | D13 | 2026-11-08 | 채택 |
| [0020](0020-progress-handler-timeout-and-threads.md) | 시간 제한 진행 콜백, 병렬 실행 스레드 | D17 | 2026-11-08 | 채택 |
| [0021](0021-execution-defaults.md) | 실행 기본값: 쿼리당 30초, 행 수 제한 없음, 읽기 전용 | D17 후속 | 2026-11-08 | 채택 |
| [0022](0022-ex-set-comparison.md) | EX 판정: 공식과 똑같은 집합 비교 하나만 | D16 | 2026-11-08 | 채택 |
| [0023](0023-empty-prediction-flag.md) | 빈 예측: 공식과 똑같이 판정 + 플래그 | D29 | 2026-11-08 | 채택 |
| [0024](0024-tied-alternative-flag.md) | 동점 대체 정답: 판정에 쓰지 않고 플래그 | D30 | 2026-11-08 | 채택 |
