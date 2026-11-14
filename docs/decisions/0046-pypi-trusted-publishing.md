# 0046. PyPI에는 태그를 push할 때 GitHub Actions가 Trusted Publishing으로 배포한다

- 날짜: 2026-11-14
- 상태: 채택
- 결정자: 사용자
- AI 관여: 선택지 조사·추천 (Claude 추천: 태그 push 시 Trusted Publishing, 저장소 공개 후 첫 배포, 채택 여부: 예)
- 관련 결정 ID: D42

## 맥락
지금은 저장소를 받아 `pip install .`로 설치해야 한다. PyPI에 올리면 `pip install text2sql-eval` 한 줄로 설치된다.

배포에는 되돌릴 수 없는 면이 있다.
- PyPI는 한 번 올린 버전을 지워도 같은 번호로 다시 올릴 수 없다.
- 배포 파일에는 소스가 들어가므로, 저장소를 공개하기 전에 올리면 코드가 먼저 공개된다.

이름 `text2sql-eval`은 2026-11-14에 PyPI와 TestPyPI에서 비어 있었다.

## 선택지
| 안 | 장점 | 단점 |
| --- | --- | --- |
| 배포하지 않음 | 작업과 위험이 없음 | 한 줄 설치가 안 되고, 그 사이 이름을 남이 가져갈 수 있음 |
| 태그를 push하면 GitHub Actions가 Trusted Publishing으로 배포 | API 토큰을 저장하지 않음, 배포가 기록되고 재현됨 | 워크플로 추가, PyPI에 pending publisher를 사용자가 직접 등록 |
| 로컬에서 API 토큰으로 `uv publish` | 가장 빠름 | 토큰 관리 부담, 배포 기록이 남지 않음 |

## 결정
`v*` 태그를 push하면 `.github/workflows/release.yml`이 패키지를 빌드하고 검사한 뒤, GitHub environment `pypi`에서 Trusted Publishing(OIDC)으로 PyPI에 올린다. 첫 배포(`v0.1.0`)는 저장소를 공개한 뒤에 한다.

## 이유
> "D42 추천대로 태그 자동 배포로 하자."

## 결과
- PyPI pending publisher 값은 다음과 같다. 워크플로와 정확히 맞아야 한다.
  - 프로젝트 이름 `text2sql-eval`
  - 소유자 `cheolkim02`
  - 저장소 `text2sql-eval`
  - 워크플로 `release.yml`
  - environment `pypi`
- pending publisher는 이름을 미리 확보하지 않는다. 첫 배포 전에 다른 사람이 이름을 쓰면 무효가 된다.
- GitHub Free 플랜에서는 environment를 공개 저장소에서만 설정할 수 있다. 그래서 environment를 쓰는 배포 작업은 저장소를 공개한 뒤에만 돌릴 수 있다. 첫 배포를 공개 후로 정한 이유이기도 하다.
- API 토큰을 저장소나 GitHub Secrets에 두지 않는다(AGENTS.md 절대 규칙 5).
- 구현에서 검사와 배포를 작업 두 개로 나눴다(Claude가 자가 검토에서 정함).
  - 깨끗한 환경 검사는 PyPI에서 의존성을 받아 실행한다. 그래서 PyPI 권한(`id-token`)이 없는 검사 작업에서 돈다.
  - 배포 작업은 같은 커밋을 다시 빌드하고, 파일 해시가 검사 작업의 것과 같을 때만 올린다. uv_build는 같은 소스에서 바이트 단위로 같은 파일을 만든다(2026-11-14 확인).
- 출처 (2026-11-14 확인):
  - [PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/)
  - [PyPI: pending publisher로 프로젝트 만들기](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
  - [uv: 패키지 배포](https://docs.astral.sh/uv/guides/package/)
  - [GitHub: 배포 environment 관리](https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment)
