# 결정 기록 (ADR)

이 저장소의 설계 결정 목록이다. 결정자는 모두 사용자이고, AI가 관여한 방식은 각 문서의 "AI 관여"에 적는다. 형식은 [0000-template.md](0000-template.md)를 따른다.

| 번호 | 결정 | 관련 ID | 날짜 | 상태 |
| --- | --- | --- | --- | --- |
| [0001](0001-record-architecture-decisions.md) | 설계 결정을 ADR로 기록, 코드 MIT·예제 데이터 CC BY-SA 4.0 | — | 2026-11-03 | 채택 |
| [0002](0002-project-name.md) | 프로젝트 이름 `text2sql-eval` | D1 | 2026-11-03 | 채택 |
| [0003](0003-language-python.md) | 구현 언어 Python | D2 | 2026-11-04 | 채택 |
| [0004](0004-prediction-file-input.md) | 예측 파일 입력, LLM 호출 없음 | D3 | 2026-11-04 | 채택 |
| [0005](0005-feature-priorities.md) | 대표: 결정적 사실 추출, 부대표: 실행 비교 | D4 | 2026-11-04 | 일부 대체됨(0042) |
| [0006](0006-demo-dataset-bird-subset.md) | 시연 데이터 BIRD dev 3개 DB, 432문제 | D5 | 2026-11-04 | 채택 |
| [0007](0007-report-outputs-html-csv.md) | 결과 화면 HTML 리포트 + CSV | D6 | 2026-11-04 | 채택 |
| [0008](0008-out-of-scope-and-roadmap.md) | 범위에서 뺄 것과 로드맵 | D7 | 2026-11-04 | 채택 |
| [0009](0009-python-version.md) | 지원 Python 3.11+ | D8 | 2026-11-07 | 채택 |
| [0010](0010-uv-and-uv-build.md) | 프로젝트 관리 uv, 빌드 백엔드 uv_build | D9 | 2026-11-07 | 채택 |
| [0011](0011-ruff.md) | 린트·포맷 Ruff | D10 | 2026-11-07 | 채택 |
| [0012](0012-schedule-adjustment-1107.md) | 11/7 일정·범위 조정 | — | 2026-11-07 | 일부 대체됨(0034) |
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
| [0025](0025-argparse.md) | CLI는 argparse | D14 | 2026-11-09 | 채택 |
| [0026](0026-run-file-json.md) | 실행 파일은 JSON 하나 | D31 | 2026-11-09 | 채택 |
| [0027](0027-prediction-format-detection.md) | 예측 파일 형식: 확장자 판별 + 덮어쓰기 옵션 | D32 | 2026-11-09 | 채택 |
| [0028](0028-baseline-evidence-ablation.md) | baseline: 같은 모델 × evidence 있음/없음 | D24 | 2026-11-09 | 채택 |
| [0029](0029-openai-sdk-for-examples.md) | baseline 예제는 openai SDK, examples 그룹에만 | D34 | 2026-11-09 | 채택 |
| [0030](0030-baseline-model-gpt-4o-mini.md) | baseline 모델 gpt-4o-mini (지원 중단 예정) | D33 | 2026-11-09 | 채택 |
| [0031](0031-error-facts-v1.md) | 오답 사실 1차: 결과 카테고리 5개 + 구조 사실 4종 | D18 | 2026-11-10 | 일부 대체됨(0033) |
| [0032](0032-sqlglot.md) | SQL 파서 sqlglot | D15 | 2026-11-10 | 채택 |
| [0033](0033-multi-label-differences.md) | 다중 라벨 출력 차이, `columns` 구조 차이, 명칭 변경 | D18 후속 | 2026-11-11 | 채택 |
| [0034](0034-reliability-flags.md) | 판정 신뢰도 플래그 6개 | D19 | 2026-11-11 | 채택 |
| [0035](0035-no-significance-test.md) | 실행 비교에 통계 검정(McNemar)을 넣지 않음 | D22 | 2026-11-11 | 채택 |
| [0036](0036-compare-gate-opt-in.md) | compare는 `--max-drop`을 줄 때만 실패 | D35 | 2026-11-11 | 채택 |
| [0037](0037-compare-dataset-mismatch.md) | 데이터셋이 다르면 경고하고 공통 케이스만 비교 | D36 | 2026-11-11 | 채택 |
| [0038](0038-jinja2-html-report.md) | HTML 리포트는 Jinja2 템플릿 (자동 이스케이프) | D21 | 2026-11-11 | 채택 |
| [0039](0039-html-report-scope.md) | HTML 리포트 범위: 기본 화면 + 다른 절·행 강조 | D37 | 2026-11-11 | 채택 |
| [0040](0040-csv-formula-escaping.md) | CSV 셀이 수식 문자로 시작하면 앞에 `'` | D38 | 2026-11-11 | 채택 |
| [0041](0041-markdown-docs.md) | 문서는 Markdown으로만, `api.md`는 테스트로 코드와 맞춤 | D23 | 2026-11-12 | 채택 |
| [0042](0042-category-mapping-roadmap.md) | 사용자 카테고리 매핑 파일은 로드맵 | D20 | 2026-11-12 | 채택 |
| [0043](0043-public-api-scope.md) | 공개 API: CLI 흐름의 함수와 결과 타입 | D39 | 2026-11-12 | 채택 |
| [0044](0044-ci-dogfooding.md) | CI에서 빌드한 wheel을 새 환경에 설치해 CLI를 돌림 | D40 | 2026-11-12 | 채택 |
| [0045](0045-docs-images-folder.md) | 문서용 이미지는 `docs/images/` | D41 | 2026-11-14 | 채택 |
| [0046](0046-pypi-trusted-publishing.md) | PyPI는 태그 push 시 GitHub Actions + Trusted Publishing | D42 | 2026-11-14 | 채택 |
| [0047](0047-remove-unrelated-personal-content.md) | 공개 전 프로젝트와 무관한 개인 정보를 현재 파일에서 지움 | D43 | 2026-11-15 | 채택 |
