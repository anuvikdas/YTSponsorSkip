# Bounded local acquisition trial

The trial ledger is `results/trial-budget.sqlite3` by default (Git-ignored). Its cap is
`YTSS_TRIAL_ATTEMPT_LIMIT=50` at most; lower values from 2 to 50 are allowed. The ledger
idempotently seeds the two observed 2026-10-19 Supadata acquisition attempts, one for
`dQw4w9WgXcQ` and one for `Vw1Qrko8oTs`. The separately authorized follow-up for the latter
reserved a third attempt. The current local ledger therefore reads **3/50**, not 1/50. It is a
count of local upstream acquisition attempts across providers, not Supadata's billing counter.

`TrialBudget.reserve_attempt` uses a SQLite `BEGIN IMMEDIATE` transaction to check and reserve
before the upstream transcript call. A timeout consumes its reservation. Any future retry needs a
new reservation; no automatic acquisition retry is enabled. `TranscriptService` invokes a
provider only on a cache miss and coalesces concurrent identical requests, so a cache hit spends
zero attempts and coalesced callers share one upstream attempt. The Supadata adapter makes only
one transcript acquisition request per attempt. A 202 job uses that same attempt, and
`reserve_poll` separately counts each job-status request with a configurable cap of at most five
(`YTSS_TRIAL_POLL_LIMIT=5`). Exhaustion or an unreadable ledger fails closed with a stable 503
error code and no-skip/unavailable response; it never sends an acquisition request.

The ledger survives backend process restarts **on the same persistent filesystem**. Do not delete,
replace or point `YTSS_TRIAL_BUDGET_PATH` at a new file to evade the cap: that would lose the
third reservation and undermine the trial. There is deliberately no reset endpoint. A future
reset would require an explicit new budget decision and preservation of the previous ledger.
SQLite serializes processes sharing the same file, but separate machines, containers or Render
instances have separate files. Render Free's local filesystem should not be treated as durable
across deployments/restarts; the in-process cache is also not durable. This is a local experiment
guard, **not** an account-level hard spend limit. Keep live Supadata selection local-only and use
the provider's account credit counter and Free-plan preflight as separate checks. Auto Recharge
and generated transcription remain out of scope.

To select Supadata for local FastAPI testing, keep the key only in `.env` and add:

```dotenv
YTSS_TRANSCRIPT_PROVIDER=supadata
YTSS_REQUEST_TIMEOUT_SECONDS=30
```

The default remains `youtube`. Start locally with
`.venv/bin/uvicorn ytsponsorskip.main:app --app-dir backend/src --host 127.0.0.1 --port 8000`.
The FastAPI Supadata wiring was verified with mocked HTTP responses, not another live transcript
request. Do not issue a live API request solely to repeat that test.
