# bird-mini: 출처와 변경 내역

이 폴더는 BIRD 벤치마크 dev set의 일부다. 저장소의 코드(MIT)와 달리, 이 폴더의 데이터는 **CC BY-SA 4.0**으로 배포된다([LICENSE](LICENSE)).

## Attribution

- **Work:** BIRD (BIg Bench for LaRge-scale Database Grounded Text-to-SQL Evaluation), dev set, release `dev_20240627`
- **Authors:** Jinyang Li et al., the BIRD team
- **Paper:** "Can LLM Already Serve as A Database Interface? A BIg Bench for Large-Scale Database Grounded Text-to-SQLs", NeurIPS 2023 Datasets and Benchmarks, [arXiv:2305.03111](https://arxiv.org/abs/2305.03111)
- **Source:** <https://bird-bench.github.io/>, downloaded from <https://bird-bench.oss-cn-beijing.aliyuncs.com/dev.zip> on 2026-11-07
- **License:** [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)
- **Changes:** subset of 3 of 11 databases, JSON files re-serialized; details below

## 라이선스 근거

- BIRD 공식 사이트는 데이터 라이선스를 CC BY-SA 4.0으로 바꿨다고 공지했다.
- 원 논문은 BIRD의 원본 DB가 퍼블릭 도메인, CC-BY, CC-BY-SA 중 하나를 따른다고 밝힌다.
- 그래서 출처를 표시하고 같은 라이선스(CC BY-SA 4.0)로 재배포한다. ShareAlike 조건은 이 폴더의 데이터와 그 변형물에만 적용되고, 이 데이터를 읽는 저장소의 코드에는 적용되지 않는다.

## 받은 원본

| 항목 | 값 |
| --- | --- |
| 파일 | `dev.zip` (346,207,293 bytes) |
| SHA-256 | `cdd6d19faeb45a23970b98d3ef6c40a87987c95459c2cf12076897a60cf5a630` |
| 내부 폴더 | `dev_20240627/` |
| 원본 규모 | 문제 1,534개, DB 11개 |

## 고른 DB와 이유

저장소에 넣을 수 있는 크기의 DB만 골랐고, 고른 DB의 문제는 **전부** 넣었다(결정 기록 [0006](../../docs/decisions/0006-demo-dataset-bird-subset.md)).

| DB | `.sqlite` 크기 | 문제 수 | simple / moderate / challenging | SHA-256 (`.sqlite`) |
| --- | --- | --- | --- | --- |
| `superhero` | 237,568 B | 129 | 81 / 33 / 15 | `75e94a2c3236ee3bb2c01fb97a1c4b4c1c269bcefd4eab1d04be323d2d0825b1` |
| `student_club` | 2,641,920 B | 158 | 101 / 48 / 9 | `eb89bcfe97eefa386a27904ec5aa15159811a7eac894ec659a36e48fa9f76b77` |
| `toxicology` | 2,678,784 B | 145 | 76 / 38 / 31 | `f5fa7f21af1ad878ff8fef1b0582b8cb2d7ed63dbac65ff16d2ba05667650c5b` |
| 합계 | 약 5.5MB | **432** | 258 / 119 / 55 | |

넣지 않은 큰 DB: `european_football_2`(597.8MB), `codebase_community`(481.4MB), `card_games`(261.8MB), `financial`(71.3MB), `debit_card_specializing`(34.6MB), `formula_1`(22.4MB), `california_schools`(11.1MB), `thrombosis_prediction`(7.3MB). 전체 dev가 필요하면 [download_full_dev.py](download_full_dev.py)를 쓴다.

## 폴더 구성

원본의 폴더 구조를 그대로 따른다. 그래서 전체 dev를 받으면 같은 경로 규칙으로 바꿔 쓸 수 있다.

| 경로 | 내용 |
| --- | --- |
| `dev.json` | 고른 DB의 문제 432개. 필드: `question_id`, `db_id`, `question`, `evidence`, `SQL`, `difficulty` |
| `dev_tied_append.json` | 고른 DB의 동점 대체 정답 13개 (아래 참고) |
| `dev_tables.json` | 고른 DB 3개의 스키마 정보 (Spider 형식) |
| `dev_databases/<db_id>/<db_id>.sqlite` | SQLite DB 파일 |
| `dev_databases/<db_id>/database_description/*.csv` | 테이블별 컬럼 설명 (원본 그대로) |

## 원본에서 바꾼 것

1. DB 11개 중 3개(`superhero`, `student_club`, `toxicology`)와 그 문제만 남겼다.
2. `dev.json`, `dev_tied_append.json`, `dev_tables.json`을 같은 내용으로 다시 직렬화했다(UTF-8, 들여쓰기 4칸, 항목 순서와 값은 원본 그대로).
3. macOS 메타데이터 파일 `.DS_Store`를 뺐다.
4. 원본의 `dev.sql`(정답 SQL과 `db_id`를 탭으로 묶은 파일)은 `dev.json`과 내용이 겹쳐 넣지 않았다.

`.sqlite` 파일과 `database_description/*.csv`는 바이트 단위로 원본과 같다.

## `dev_tied_append.json`에 대해

원본 릴리스에 함께 들어 있는 파일로, 문서화된 설명은 찾지 못했다. 2026-11-07에 내용을 비교한 결과는 다음과 같다.

- 42개 항목 모두 `dev.json`에 같은 `question_id`가 있다. 질문은 39개가 같고, 정답 SQL은 41개가 다르다.
- 원래 정답이 `ORDER BY ... LIMIT 1`로 하나만 고르는 곳을, 최댓값·최솟값과 같은 **동점 행을 모두 돌려주도록** 바꾼 대체 정답이다. 예: `question_id` 244(`toxicology`).
- 고른 DB 3개에 해당하는 것은 13개다(`superhero` 7, `student_club` 4, `toxicology` 2).

이 파일을 판정에 어떻게 쓸지(예: 대체 정답과 일치해도 정답으로 볼지)는 EX 판정 규칙 결정(D16)에서 정한다.

## 확인한 것 (2026-11-07)

- `dev.json`의 정답 SQL 432개와 `dev_tied_append.json`의 13개가 모두 읽기 전용 연결에서 오류 없이 실행되고, 각각 1초 안에 끝난다.
- 정답 결과의 모양: 값 하나(1행 1열)인 문제 247개, 그 밖의 문제 185개, 빈 결과인 문제 0개.
