# baseline: OpenAI 단일 프롬프트

`text2sql-eval`에 넣을 예측 파일을 만드는 예제다. 도구 자체는 모델을 부르지 않는다([ADR 0004](../../docs/decisions/0004-prediction-file-input.md)). 이 스크립트는 "어떤 파이프라인이든 예측 파일만 만들면 된다"는 것을 보여 주는 가장 단순한 파이프라인이다.

## 프롬프트

질문마다 한 번 호출한다. evidence 줄만 설정에 따라 들어가거나 빠진다.

```text
[system] You are a SQLite expert. Answer with one SQLite query and nothing else.
[user]   Database schema:
         <해당 DB의 CREATE TABLE 문>

         Hint: <BIRD evidence>      (--evidence일 때만)

         Question: <질문>
```

응답에서 코드 블록 표시(```sql)를 걷어내고, 줄바꿈을 공백으로 바꿔 한 줄로 만든다.

## 실행

`openai` 패키지는 `examples` 의존성 그룹에만 있다([ADR 0029](../../docs/decisions/0029-openai-sdk-for-examples.md)).

```sh
export OPENAI_API_KEY=sk-...
uv run --group examples python examples/baseline/predict.py \
  --dataset examples/bird-mini/dev.json \
  --db-dir examples/bird-mini/dev_databases \
  --evidence --limit 10 --out /tmp/trial.jsonl
```

- 먼저 `--limit 10`으로 비용을 확인한다. 실행이 끝나면 토큰 수와 예상 비용을 출력한다.
- `--no-evidence`로 evidence를 뺀 설정을 만든다.
- API 호출이 끝내 실패한 질문은 빈 예측으로 쓰고, 그 오류를 `meta.error`에 남긴다.

결과와 공식 스크립트 대조는 [examples/results/README.md](../results/README.md)에 있다.
