# University workspace migration

Historical migration checkpoint. The blank-key and blocked-API observations below were true at migration time. A later verified live API run is documented in `../event_extraction_review.md`; do not interpret the historical key state as current.

Canonical root: `C:\dev\university\dads5250-bluebikes-planner`.
Ignored credential file: `C:\dev\university\dads5250-bluebikes-planner\.env`.

495 task artifact files (1,150,106,917 bytes) were copied and SHA256-verified before source cleanup. The raw archives and local caches were preserved. The old zero-commit task Git directory, old virtual environment, temporary build outputs and Python bytecode were not imported. A fresh independent Git root uses the original private origin. No world-group history, hooks, configuration or unrelated files were copied.

The old `.env.example` contained a credential-like value. Its entire file was preserved privately under the ignored `data/cache/migration/` directory, without logging or manually transcribing the value. Both new `.env.example` and `.env` have a blank `OPENAI_API_KEY`. The private backup and `.env` are ignored by the target repository and the ancestor `C:\dev` repository. The new task directory itself is untracked by the ancestor; no ancestor Git history or configuration is modified.

Read-only history checks found zero commits, reflogs or Git objects in the old task repository, no tracked example in its index, no parent world-group history for the old task example path, and an empty private GitHub remote with zero branches before any new-root push. These checks find no evidence that the old example was committed or pushed; deleted historical remote objects cannot be ruled out by current-state inspection.

The new environment passes `pip check` and 37 tests. The submission Notebook was rerun at the new root: all 10 code cells executed, outputs present and zero cell errors. Data pipeline, crew planner, event schema/fixtures and recorded-output validation remain usable. Actual OpenAI extraction still needs the intentionally blank local key; no private backup key is used automatically. Human review, TA confirmation, demo recording/upload and Canvas submission remain outstanding.

See `verification.json`, `preservation-manifest.json`, `source-before.json` and `parent-before.json` for audit evidence. Historical source paths in migration records are intentional. Source cleanup occurs only after these verification checks; its result is recorded separately.

Source cleanup is complete. The verified old task folder and its now-empty container were removed. Exact parent status comparison, excluding that task folder, is unchanged; existing `.task-ragtag/` and Dataform verification files remain untouched. No parent history, index, tracked files or Git configuration were changed.
