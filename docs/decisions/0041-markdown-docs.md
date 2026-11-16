# 0041. 문서는 Markdown으로만 쓴다

- 날짜: 2026-11-12
- 상태: 채택
- 결정자: 사용자
- AI 관여: 선택지 조사·추천 (Claude 추천: Markdown만, 채택 여부: 예)
- 관련 결정 ID: D23
- 편집: 2026-11-15, 공개 전에 프로젝트와 무관한 개인 정보를 지움([0047](0047-remove-unrelated-personal-content.md))

## 맥락
가이드 4개, `architecture.md`, `reference/`(CLI, API, 실행 파일 형식)를 어떤 형태로 낼지 정해야 했다. 독자는 대부분 GitHub에서 저장소를 열어 본다.

## 선택지
| 안 | 장점 | 단점 |
| --- | --- | --- |
| Markdown만 | GitHub에서 바로 읽힘, 의존성·배포 없음 | API 문서를 손으로 써서 코드와 어긋날 수 있음 |
| pdoc 16.0.0 (Stable, MIT-0) | docstring에서 API 문서 HTML 자동 생성 | 개발 의존성 1개, 남이 보려면 GitHub Pages 배포 필요 |
| MkDocs 1.6.1 + Material 9.8.1 + mkdocstrings 1.0.8 | 검색되는 문서 사이트 | MkDocs 마지막 릴리스 2024-08, Material은 PyPI에 "Inactive" 표시, 일정 위험 |

## 결정
`docs/` 아래 Markdown 파일로만 쓴다. 문서 사이트 생성기와 배포는 쓰지 않는다.

## 이유
추천안(Markdown만)을 채택했다.

## 결과
- `docs/reference/api.md`는 손으로 쓴다. 문서와 코드가 어긋나지 않도록, `api.md`에 적힌 이름과 `text2sql_eval.__all__`이 같은지 테스트로 검사한다.
- 문서 안의 Python 코드 블록은 Ruff가 포맷을 검사한다(0011).
- API 문서 자동 생성은 PLAN의 권장 목록에 남긴다.
- 출처: PyPI (2026-11-12 확인)
