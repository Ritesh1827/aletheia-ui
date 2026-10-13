# TrustTrace Web — Milestone 1 (Oxide Observatory · Verify-first)

Python-first Web layer for the Physical-to-Digital Anti-Counterfeit Trust Fabric.
Spec source of truth: `TrustTrace_Web_UI_UX_Spec.md` (read-only, do not edit).

## Run (M1)

```bash
uv sync
uv run uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/verify` and try:

- `TT-DEMO-0001` — VERIFIED path
- `TT-DEMO-0002` — CLONE_DETECTED with conflicting observations
- `TT-DEMO-UNKNOWN` — unknown-serial state
- `TT-DEMO-ERR` — backend error state (retry; never an all-clear)

## Checks

```bash
uv run ruff check .
uv run mypy app
uv run pytest -q
```

## Notes

- 100% mock data in M1, labelled `DEMO DATA` throughout. No real backend wired.
- `VERIFIED` means available history checks are consistent — not physical authenticity.
- Deferred: Control Tower, Incidents, Explorer, Red-Team, Lots & Recall, Audit, RBAC.
