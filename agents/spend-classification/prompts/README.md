# Prompts

One file per prompt, version in the filename (`classify_line.v1.md`). Never edit a released
version; add `v2` and switch the code to it. After any change:

```bash
uv run python -m shared.evals.prompt_manifest --write agents/spend-classification/prompts
```

CI fails if `MANIFEST.json` is stale. The bundle hash is recorded in every run manifest.
No prompts yet (the first arrives in Phase 2/3).
