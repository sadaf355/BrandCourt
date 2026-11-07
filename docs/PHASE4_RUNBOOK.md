# BrandCourt model and evaluation runbook

## Provider
Use Ollama as the selected local provider. Configure the API and evaluator with the same values:
- `MODEL_MODE=ollama`
- `OLLAMA_BASE_URL=http://localhost:11434`
- `OLLAMA_MODEL=llama3.2:3b`
- `OLLAMA_EMBEDDING_MODEL=nomic-embed-text`

Pull the models before evaluation:
```bash
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```
The evaluator checks `/api/tags` before starting model-dependent variants. If either model is
missing or Ollama is offline, the variant is marked blocked and no prediction file is written.

## Seed and run
Run the existing GlowSerum seed command documented in the README, then run:
```bash
python scripts/evaluate_api.py --variant code_rules_only --token <admin-token>
python scripts/evaluate_api.py --variant retrieval_and_nli --token <admin-token>
python scripts/evaluate_api.py --variant full_pipeline --token <admin-token>
python scripts/score_eval.py --code-only ../data/sample/glowserum_code_rules_only_predictions.jsonl --retrieval-nli ../data/sample/glowserum_retrieval_and_nli_predictions.jsonl --full ../data/sample/glowserum_full_pipeline_predictions.jsonl --evaluation-doc ../docs/EVALUATION.md
```
All three files must contain all 52 IDs and share the same dataset SHA-256. The scorer refuses
mixed datasets or partial predictions.

## Round 3 proof cases
See `EVALUATION.md` for the three acceptance scenarios. Record screenshots/job IDs and reviewer
decisions in the run evidence before treating them as passed. The proof-case unit tests validate
forced-quote source integrity; they do not replace the API-level Guideline Health, precedent, and
fix-verification walkthroughs.
