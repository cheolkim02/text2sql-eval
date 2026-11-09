# 실측 결과: gpt-4o-mini 단일 프롬프트 baseline

`examples/bird-mini`(BIRD dev, 432문제)에서 같은 모델과 같은 프롬프트로 두 번 예측한 결과다. 두 실행의 차이는 BIRD의 `evidence`를 프롬프트에 넣었는지 하나뿐이다([ADR 0028](../../docs/decisions/0028-baseline-evidence-ablation.md)).

## 결과

| 설정 | EX | simple | moderate | challenging | correct | incorrect | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| evidence 있음 | **61.81%** | 68.22% | 54.62% | 47.27% | 267 | 161 | 4 |
| evidence 없음 | **37.50%** | 43.80% | 27.73% | 29.09% | 162 | 261 | 9 |

| 플래그 | evidence 있음 | evidence 없음 |
| --- | --- | --- |
| `tied_alternative_exists` (동점 대체 정답이 있는 문제) | 13 | 13 |
| `matches_tied_alternative_only` (대체 정답과만 일치, 거짓 오답 의심) | 5 (736, 802, 810, 832, 1365) | 1 (810) |
| `empty_prediction_correct` | 0 | 0 |

evidence 있음 설정의 오답 161개 중 5개는 동점 대체 정답과 일치한다. 공식 규칙으로는 오답이지만 올바른 답일 수 있다.

## BIRD 공식 스크립트와의 일치 (2026-11-09)

같은 예측을 BIRD 공식 평가 스크립트로도 채점했다. 스크립트는 AlibabaResearch/DAMO-ConvAI의 `bird/llm/src/evaluation.py`이고, 수정하지 않고 그대로 실행했다(`--meta_time_out 30`, `--num_cpus 8`). 공식 스크립트는 DB를 쓰기 가능하게 열기 때문에 DB 복사본에서 돌렸다.

| 설정 | 공식 스크립트 (simple / moderate / challenging / total) | text2sql-eval |
| --- | --- | --- |
| evidence 있음 | 68.22 / 54.62 / 47.27 / 61.81 | 68.22 / 54.62 / 47.27 / 61.81 |
| evidence 없음 | 43.80 / 27.73 / 29.09 / 37.50 | 43.80 / 27.73 / 29.09 / 37.50 |

8개 숫자가 모두 소수점 둘째 자리까지 같다.

## 시간 제한에 민감한 케이스

판정이 기계 속도에 따라 달라질 수 있는 사례를 숨기지 않고 적는다([ADR 0021](../../docs/decisions/0021-execution-defaults.md)).

- **evidence 있음 211번:** 예측 쿼리가 180초에도 끝나지 않는다(중첩 서브쿼리 조인). 30초 제한에서 시간 초과로 판정된다. 경계에서 먼 사례라 판정이 흔들리지 않는다.
- **evidence 없음 247번:** 예측 쿼리가 약 18초 걸려 끝나고, 오답으로 판정된다. 기계가 약 1.6배 느리면 30초를 넘어 시간 초과로 바뀔 수 있다. 이 경우에도 점수(0점)는 같다.
- **evidence 없음 281번:** 약 5초 걸린다.

재현성 테스트(`tests/test_results.py`)는 기본 30초 제한으로 커밋된 판정을 다시 만들어 낸다. 5초로 낮추면 247번과 281번이 시간 초과로 바뀐다.

## 생성 정보

| 항목 | 값 |
| --- | --- |
| 모델 | `gpt-4o-mini` (응답 스냅샷 `gpt-4o-mini-2024-07-18`, 2027-01-14 종료 예정, [ADR 0030](../../docs/decisions/0030-baseline-model-gpt-4o-mini.md)) |
| 파라미터 | `temperature=0`, `seed=0`, `max_tokens=512` |
| 생성일 | 2026-11-09 |
| 토큰과 비용 | evidence 있음: 입력 206,926 / 출력 20,584 (약 $0.043). evidence 없음: 입력 195,792 / 출력 21,823 (약 $0.043). 2026-11-09 가격 기준 |
| API 실패 | 0건 |

`temperature=0`과 `seed`를 줘도 OpenAI 응답은 완전히 같다고 보장되지 않는다. 그래서 예측 파일을 커밋해 두었고, 판정은 이 파일에서 언제든 같게 재현된다.

## 파일

| 파일 | 내용 |
| --- | --- |
| `gpt-4o-mini-evidence.jsonl` | 예측 (evidence 있음). `meta`에 스냅샷, 토큰 수, 지연 시간 |
| `gpt-4o-mini-no-evidence.jsonl` | 예측 (evidence 없음) |
| `gpt-4o-mini-evidence.run.json` | `text2sql-eval eval` 실행 파일 |
| `gpt-4o-mini-no-evidence.run.json` | 같은 형식 |

## 다시 만들기

API 키 없이 판정만 다시 하려면 아래 명령을 쓴다.

```sh
uv run text2sql-eval eval \
  --dataset examples/bird-mini/dev.json \
  --db-dir examples/bird-mini/dev_databases \
  --pred examples/results/gpt-4o-mini-evidence.jsonl \
  --tied examples/bird-mini/dev_tied_append.json \
  --meta model=gpt-4o-mini-2024-07-18 --meta prompt=single-prompt-v1 \
  --meta evidence=yes --meta generated=2026-11-09 \
  --out examples/results/gpt-4o-mini-evidence.run.json
```

예측까지 다시 만드는 방법은 [examples/baseline/README.md](../baseline/README.md)에 있다.
