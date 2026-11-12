# 예측 파일 만들기

`text2sql-eval`은 모델을 부르지 않는다. 내 파이프라인이 만든 SQL을 파일로 받아 판정한다([ADR 0004](../decisions/0004-prediction-file-input.md)). 이 문서는 그 파일을 만드는 법이다.

필요한 것은 세 가지다.

1. **문제 파일(`--dataset`):** BIRD 형식의 JSON
2. **DB 폴더(`--db-dir`):** `<db-dir>/<db_id>/<db_id>.sqlite` 구조의 SQLite 파일
3. **예측 파일(`--pred`):** 아래 두 형식 중 하나([ADR 0018](../decisions/0018-prediction-file-formats.md))

## 문제 파일과 DB

BIRD의 `dev.json`을 그대로 쓴다. 직접 만든 문제라면 같은 모양으로 쓴다.

```json
[
  {
    "question_id": 195,
    "db_id": "toxicology",
    "question": "What is the most common bond type?",
    "evidence": "most common bond type refers MAX(COUNT(bond_type))",
    "SQL": "SELECT T.bond_type FROM ( SELECT bond_type, COUNT(bond_id) FROM bond GROUP BY bond_type ORDER BY COUNT(bond_id) DESC LIMIT 1 ) AS T",
    "difficulty": "simple"
  }
]
```

- `question_id`(정수)는 겹치면 안 된다.
- `difficulty`는 없어도 된다. 있으면 난이도별 EX를 낸다.
- 나머지 필드는 무시한다.

BIRD dev 전체를 받으려면 [download_full_dev.py](../../examples/bird-mini/download_full_dev.py)를 쓴다.

## 형식 1: 텍스트 (한 줄에 SQL 하나)

```text
SELECT T.bond_type FROM bond AS T GROUP BY T.bond_type ORDER BY COUNT(*) DESC LIMIT 1
SELECT COUNT(*) FROM atom WHERE element = 'cl'

SELECT molecule_id FROM molecule WHERE label = '+'
```

- **N번째 줄이 문제 파일의 N번째 문제의 예측이다.** 줄 수가 문제 수와 다르면 입력 오류다.
- 모델이 SQL을 내지 못한 문제는 **빈 줄로 남긴다**(위의 세 번째 줄). 줄을 지우면 그 뒤의 예측이 모두 한 칸씩 밀린다.
- SQL은 한 줄이어야 한다. 줄바꿈이 있는 SQL은 공백으로 이어 붙인다(예: `" ".join(sql.split())`).
- 앞뒤 공백은 지운다. 파일 끝의 줄바꿈 하나와 Windows 줄바꿈(`\r\n`)은 괜찮다.
- 확장자는 `.txt`를 쓴다.

## 형식 2: JSONL (한 줄에 JSON 객체 하나)

```text
{"id": 195, "sql": "SELECT T.bond_type FROM bond AS T GROUP BY T.bond_type ORDER BY COUNT(*) DESC LIMIT 1", "meta": {"latency_ms": 821}}
{"id": 196, "sql": "SELECT COUNT(*) FROM atom WHERE element = 'cl'"}
{"id": 197, "sql": ""}
```

| 필드 | 필수 | 내용 |
| --- | --- | --- |
| `id` | 예 | 문제의 `question_id`. 정수나 문자열(`195`와 `"195"`는 같다) |
| `sql` | 예 | 예측 SQL. 빈 문자열이면 SQL을 내지 못한 것이다. 여러 줄이어도 된다 |
| `meta` | | 이 예측에 대한 정보(토큰 수, 지연 시간 등) 객체. 실행 파일의 케이스에 그대로 남는다 |

- **줄 순서는 상관없다.** `id`로 문제와 맞춘다.
- 같은 `id`가 두 번 나오거나, 문제 파일에 없는 `id`면 입력 오류다.
- 빠진 문제가 있으면 기본적으로 입력 오류다. 일부만 판정하려면 `--allow-missing`을 준다. 빠진 문제는 빈 예측으로 판정되고 `prediction_state`가 `missing`으로 기록된다.
- 빈 줄은 건너뛴다. 확장자는 `.jsonl`을 쓴다.

예측마다 메타 정보를 남기고 싶거나 일부만 판정하려면 JSONL이 낫다. 줄 순서가 상관없어서 병렬로 만든 결과를 모으기에도 편하다.

## 내 파이프라인에서 쓰기

모델 호출 결과를 JSONL로 쓰는 예:

```python
import json
from pathlib import Path


def write_predictions(predictions: dict[int, str], path: Path) -> None:
    """predictions: question_id -> SQL (empty string if the model gave none)."""
    with path.open("w", encoding="utf-8") as file:
        for question_id, sql in predictions.items():
            line = {"id": question_id, "sql": sql}
            file.write(json.dumps(line, ensure_ascii=False) + "\n")
```

저장소의 [baseline 예제](../../examples/baseline/README.md)가 OpenAI API로 예측을 만들어 이 형식으로 쓰는 실제 코드다.

실험 설정은 `--meta`로 실행 파일에 남긴다. 나중에 어떤 설정의 결과인지 바로 알 수 있다.

```sh
text2sql-eval eval --dataset dev.json --db-dir dev_databases \
  --pred runs/v3.jsonl --meta model=my-model --meta prompt=v3 --out runs/v3.json
```

## 빈 예측은 어떻게 판정되나

빈 SQL(빈 줄, `"sql": ""`, `--allow-missing`으로 빠진 문제)은 BIRD 공식 스크립트처럼 빈 쿼리로 실행해 판정한다([ADR 0023](../decisions/0023-empty-prediction-flag.md)). 빈 쿼리의 결과는 0행이다.

- 정답 결과도 0행이면 공식 규칙으로는 정답이다. 이때 `empty_prediction_correct` 플래그를 붙여 표시한다.
- 그 밖에는 오답이고, 출력 차이는 `empty_result`다.

`eval`의 요약에 `Predictions: 3 missing, 1 empty (judged as empty SQL)`처럼 그 수를 함께 보여 준다.

## 형식 고르기

확장자로 형식을 정한다. `.txt`는 텍스트, `.jsonl`은 JSONL이다. 다른 확장자를 쓰려면 `--pred-format text` 또는 `--pred-format jsonl`을 준다([ADR 0027](../decisions/0027-prediction-format-detection.md)).

BIRD 공식 예측 형식(`{"0": "SQL\t----- bird -----\tdb_id"}`)은 아직 읽지 않는다(PLAN의 권장 목록).
