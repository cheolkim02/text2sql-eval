# 0043. 공개 API는 CLI 흐름의 함수와 결과 타입으로 한다

- 날짜: 2026-11-12
- 상태: 채택
- 결정자: 사용자
- AI 관여: 선택지 조사·추천 (Claude 추천: CLI 흐름의 함수와 결과 타입, 채택 여부: 예)
- 관련 결정 ID: D39

## 맥락
지금 `text2sql_eval`은 `__version__`만 내보낸다. 라이브러리로 쓰이려면 무엇을 공개할지 정해야 한다. 공개한 이름은 `docs/reference/api.md`에 문서화하고, 함부로 바꾸지 않겠다는 약속이 된다.

## 선택지
| 안 | 장점 | 단점 |
| --- | --- | --- |
| CLI 흐름의 함수와 결과 타입 (약 20개) | Python에서도 CLI와 같은 일을 함, 타입 품질을 보여 줄 대상이 생김 | 지켜야 할 이름이 늘어남, 겹치는 이름 정리 필요 |
| CLI와 실행 파일 형식만 | 약속할 것이 가장 적음 | 라이브러리로 보여 줄 것이 없음 |
| 모듈 전부 | 제한 없음 | 내부 함수까지 약속해 고치기 어려움 |

## 결정
불러오기 → 판정 → 실행 파일 읽기·쓰기 → 비교 → 리포트 쓰기의 함수와, 그 입력·결과 타입을 `text2sql_eval/__init__.py`의 `__all__`로 내보낸다. `__all__`에 없는 것은 비공개다.

## 이유
추천안(CLI 흐름의 함수와 결과 타입)을 채택했다.

## 결과
- 공개 이름 36개 (구현 계획 승인, 2026-11-12):
  - 함수 8개: `evaluate_files`, `read_run`, `write_run`, `compare_runs`, `write_html_report`, `write_report_csv`, `write_comparison_csv`, `status_of`
  - 실행 파일: `Run`, `CaseRecord`, `Summary`, `FileRef`, `RunSettings`, `ResultSample`, `QueryFailure`, `SqlValue`, `PredictionState`
  - 판정: `Verdict`, `Correct`, `Incorrect`, `ExecError`, `Flag`, `FlagKind`
  - 차이: `CaseDiff`, `OutputDiff`, `OutputDifference`, `Relation`, `StructureReport`, `Fact`, `FactKind`
  - 비교: `Comparison`, `CaseChange`, `Change`, `GroupEx`
  - 기타: `InputError`, `__version__`
- 추가 (2026-11-12, 사용자 승인): 공개 타입의 필드에 쓰이는데 빠져 있던 타입 별칭 `PredictionFormat`(`Run.prediction_format`)과 `QuerySummary`(`CaseRecord.gold`, `CaseRecord.pred`)를 더해 38개가 됐다. API 문서를 쓰다가 발견했다.
- 공개 함수의 결과에 나오는 타입은 모두 내보낸다. 사용자가 내부 모듈을 import하지 않고 타입을 적고 `match`로 나눌 수 있게 하려는 것이다.
- 데이터셋·예측 로더와 낮은 수준의 `evaluate`는 공개하지 않는다. CLI의 `eval`과 같은 일은 `evaluate_files`가 한다.
- 이름 정리: `write_html` → `write_html_report`, 리포트 `write_csv` → `write_report_csv`, 비교 `write_csv` → `write_comparison_csv`
- `tests/test_public_api.py`가 지키는 것: `__all__`이 위 목록과 같다, 함수에는 예시가 있다, 클래스에는 docstring이 있다, 시그니처와 필드에 `Any`가 없다.
- 공개 API에는 `Any`를 쓰지 않는다(AGENTS.md 절대 규칙 6).
- `api.md`와 `__all__`이 같은지 테스트로 검사한다(0041).
