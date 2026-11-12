# 실행 비교하기

프롬프트, 모델, few-shot, 모듈 구성을 바꿀 때마다 "EX가 몇 %p 올랐나"만으로는 부족하다. 어떤 문제가 새로 맞고 어떤 문제가 새로 틀렸는지, 틀리는 방식이 어떻게 바뀌었는지를 봐야 다음에 무엇을 고칠지 정할 수 있다. `compare`는 두 실행 파일을 케이스 단위로 비교해 이것을 보여 준다.

```sh
text2sql-eval compare BASE.json HEAD.json [--csv flips.csv] [--max-drop 1.0]
```

`BASE`는 기준(바꾸기 전), `HEAD`는 비교 대상(바꾼 뒤)이다. 아래 예는 저장소의 두 실행으로, 같은 모델과 같은 프롬프트에서 `evidence`를 뺀 실행(base)과 넣은 실행(head)이다.

```text
Comparing examples/results/gpt-4o-mini-no-evidence.run.json -> examples/results/gpt-4o-mini-evidence.run.json (432 common cases)
EX: 37.5% -> 61.8% (+24.3 pp)
Both correct 144 | Fixed 123 | Regressed 18 | Both wrong 147
By difficulty: challenging 29.1% -> 47.3%, moderate 27.7% -> 54.6%, simple 43.8% -> 68.2%
By database: student_club 43.0% -> 57.0%, superhero 57.4% -> 79.8%, toxicology 13.8% -> 51.0%
Output difference: empty_result 100 -> 34, single_value_differs 94 -> 44, column_mismatch 78 -> 62, row_set_differs 46 -> 58, row_count_differs 26 -> 31, execution_failed 9 -> 4
SQL structure difference: columns 155 -> 79, where_value 132 -> 25, tables_joins 130 -> 72, aggregation 121 -> 66, order_limit 40 -> 23
```

## 한 줄씩 읽기

**공통 케이스.** 두 실행에 모두 있는 케이스 `id`만 비교한다. 아래의 모든 숫자는 공통 케이스 기준이므로, 실행 파일 하나의 EX와 다를 수 있다.

**EX와 변화.** `+24.3 pp`는 퍼센트포인트다. 37.5%에서 61.8%가 됐다는 뜻이다(24.3% 증가가 아니다).

**분할표.** 케이스를 네 칸으로 나눈다. `error`도 맞지 않은 것으로 센다.

| | head 정답 | head 오답 |
| --- | --- | --- |
| **base 정답** | Both correct 144 | **Regressed 18** (나빠짐) |
| **base 오답** | **Fixed 123** (고쳐짐) | Both wrong 147 |

EX 변화는 `(Fixed - Regressed) / 공통 케이스 수`와 같다. (123 - 18) / 432 = 24.3%p. 같은 +2%p라도 "10개 고치고 1개 망침"과 "40개 고치고 31개 망침"은 다른 변화다. 후자는 바꾼 것이 문제마다 다르게 작용했다는 뜻이고, 망가진 31개를 읽어 봐야 한다.

**난이도별·DB별.** 공통 케이스를 난이도와 DB로 나눠 EX를 낸다. 이 예에서는 `toxicology`가 13.8%에서 51.0%로 가장 크게 올랐다. 이 DB는 값이 코드로 저장되어 있어서(`'+'`는 발암성, `'='`는 이중 결합) evidence 없이는 모델이 알 수 없다.

**차이 분포의 변화.** 출력 차이와 SQL 구조 차이의 종류별 개수가 어떻게 바뀌었는지 보여 준다. 이 예에서는 `where_value`가 132에서 25로, `empty_result`가 100에서 34로 줄었다. evidence는 주로 WHERE에 들어갈 값(철자, 대소문자, 코드값)을 알려 주므로, 없으면 값을 틀리고 결과가 빈다. 반대로 `row_set_differs`는 46에서 58로 늘었다. 결과가 비지는 않게 됐지만 내용이 틀린 경우가 늘었다는 뜻이다. 차이가 무슨 뜻인지는 [결과 읽기](reading-results.md)에 있다.

통계 검정(예: McNemar)은 하지 않는다([ADR 0035](../decisions/0035-no-significance-test.md)). 차이가 작을 때는 `Fixed`와 `Regressed`의 크기와, 뒤집힌 케이스를 직접 읽어 보고 판단한다.

## 뒤집힌 케이스 보기

`--csv`를 주면 공통 케이스마다 한 줄인 CSV를 쓴다. 엑셀에서 `change` 열로 거르면 된다.

```sh
text2sql-eval compare base.json head.json --csv flips.csv
```

- `change`가 `regressed`인 줄: 바꾼 뒤에 틀린 케이스. 먼저 읽을 것이다.
- `base_output_differences`와 `head_output_differences`: 같은 케이스가 어떻게 다르게 틀렸는지 보여 준다.
- `base_pred_sql`와 `head_pred_sql`: 두 예측 SQL을 나란히 보여 준다.

`--json`은 뒤집힌 케이스의 `id` 목록(`fixed_ids`, `regressed_ids`)을 함께 낸다. 스크립트로 이어서 처리할 때 쓴다.

## 비교가 의미 있으려면

- **같은 데이터셋.** 데이터셋 파일의 SHA-256이 다르면 맨 앞에 `WARNING: the runs used different dataset files`가 나온다. 한쪽에만 있는 케이스가 있으면 그 수도 경고한다. 공통 케이스가 하나도 없으면 오류로 멈춘다([ADR 0037](../decisions/0037-compare-dataset-mismatch.md)).
- **같은 판정 조건.** 시간 제한(`settings.timeout_seconds`)이나 `--tied` 여부가 다르면 판정이나 플래그가 달라질 수 있다. 두 실행 파일의 `settings`와 `inputs`를 확인한다.
- **설정 기록.** `eval --meta model=... --meta prompt=...`로 남긴 값이 실행 파일에 있으므로, 무엇과 무엇을 비교하는지 나중에도 알 수 있다.

## CI에서 쓰기: `--max-drop`

기본적으로 `compare`는 EX가 떨어져도 종료 코드 0으로 끝난다. 비교는 보고하는 일이지 막는 일이 아니기 때문이다. `--max-drop PP`를 주면 EX가 `PP` %p보다 많이 떨어질 때 종료 코드 1로 끝난다([ADR 0036](../decisions/0036-compare-gate-opt-in.md)).

```sh
text2sql-eval compare runs/main.json runs/branch.json --max-drop 1.0
```

기준을 넘으면 요약 뒤에 표준 오류로 이런 줄이 나온다(숫자는 예).

```text
FAILED: EX dropped by 1.6 pp, more than --max-drop 1
```

예를 들어 파이프라인 저장소의 CI에서, 기준 실행 파일을 저장소에 두고 PR마다 새로 `eval`한 결과와 비교하면 EX가 크게 떨어지는 변경을 merge 전에 알 수 있다. 다만 LLM 응답은 `temperature=0`이어도 완전히 같게 재현되지 않을 수 있다. 그래서 기준(`PP`)을 0보다 조금 크게 두는 편이 낫다.
