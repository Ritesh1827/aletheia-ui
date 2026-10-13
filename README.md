# Aletheia Web — Physical-to-Digital Anti-Counterfeit Trust Fabric (Web Layer)

Python-first web layer for a supply-chain trust fabric: verify product serials against their
history, investigate clone/tamper incidents, manage lots and recalls, inspect anchored
supply-chain evidence, run red-team scenarios, and enforce role-based access — all backed by a
hash-chained audit log. **100% mock data (`DEMO DATA`), no production backend wired.**

> New here? Read [`PROJECT_EXPLAINED.md`](PROJECT_EXPLAINED.md) first — same system in plain
> words. Normative UI/UX source of truth: [`Aletheia_Web_UI_UX_Spec.md`](Aletheia_Web_UI_UX_Spec.md).

## Stack

- **Runtime:** Python ≥ 3.11 · FastAPI · Uvicorn
- **Rendering:** Jinja2 templates + HTMX + Alpine.js (server-rendered, no SPA build)
- **Data/validation:** Pydantic v2 models everywhere (API shapes double as fixtures)
- **Tooling:** `uv` · `ruff` (lint) · `mypy --strict` (types) · `pytest` (tests)
- **Crypto:** stdlib `hashlib.sha256` only (Merkle derivation/recomputation, audit hash chain)

## Quickstart

```bash
uv sync
uv run uvicorn app.main:app --reload   # http://127.0.0.1:8000/verify
```

Try: `AL-DEMO-0001` (VERIFIED) · `AL-DEMO-0002` (CLONE_DETECTED) · `AL-DEMO-UNKNOWN`
(unknown) · `AL-DEMO-ERR` (backend error — retry, never an all-clear).

```bash
uv run ruff check .     # lint
uv run mypy app         # strict type-check (30 files)
uv run pytest -q        # 123 tests
```

## Configuration

| Variable | Default | Effect |
|---|---|---|
| `ALETHEIA_API_MODE` | `mock` | Non-`mock` disables demo gates (red-team becomes 403) |
| `ALETHEIA_CHAIN_LABEL` | `local demo network` | Chain label in UI |

## Architecture

```
Browser ──▶ FastAPI routers (app/routes/) ──▶ deps seam (app/services/deps.py)
      │                │                               │         ╲
      │                │ session guard (?as=/cookie)   │          ╲ mock_* services
      │                ▼                               ▼           ╱ (verify, explorer,
 templates/ ◀── Pydantic models (app/models/) ◀── mock_* ───────╱   operations, lots,
 Jinja2 + HTMX + Alpine.js                                   redteam, access, audit)
 static/css (tokens/base/components/mobile) · static/js (app/mobile/scanner/verify_scan)
```

- **Routes never touch mocks directly** — everything goes through `deps.*`, so a real backend
  plugs in behind identical signatures.
- **AuthZ centralization:** `app/routes/session.py::guard()` → `mock_access.require()`.
  UI gating (`can()`) is courtesy only.
- **Audit fan-in:** lots, incidents, red-team, access denials, role switches all append to
  `mock_audit` (hash-chained, verified on every `/audit` load).

## Routes

| Method | Route | Permission | Notes |
|---|---|---|---|
| GET | `/`, `/verify`, `/verify/:serial`, `/verify/:serial/bundle` | public | 303 redirect on known `?q=`; 404 unknown; 502 backend error |
| GET | `/overview`, `/incidents`, `/incidents/:id`, `/incidents/:id/export` | public reads | annotate via POST below |
| POST | `/incidents/:id/actions?action=note\|accept` | `incident:annotate` | 403 + audit on denial |
| GET | `/lots`, `/lots/:id`, `/lots/:id/blast-radius`, `/lots/:id/audit` | public reads | |
| POST | `/lots/:id/freeze` | `lot:freeze` | typed ID confirmation, idempotent |
| POST | `/lots/:id/recall` | `lot:recall` | admin-only; also freezes |
| GET | `/explorer`, `/explorer/search`, `/explorer/block/:id`, `/explorer/tx/:hash`, `/explorer/tx/:hash/proof`, `/explorer/address/:addr` | public reads | `?mode=live\|stale\|down\|error` |
| GET/POST | `/red-team`, `/red-team/:id`, `/red-team/:id/run`, `/red-team/:id/result` | run paths: `redteam:run` | demo-mode gate + permission |
| GET/POST | `/access`, `/access/role` | public | matrix + demo role switch (`al_role` cookie, `?as=` override) |
| GET | `/audit` | `integrity:view` | filters + live integrity report |

Demo roles: `?as=verifier|operator|investigator|admin` (unknown → verifier; cookie persists).

## Permission matrix

| Permission | verifier | operator | investigator | admin |
|---|---|---|---|---|
| `verify:public` | ✅ | ✅ | ✅ | ✅ |
| `evidence:internal` | — | — | ✅ | ✅ |
| `incident:annotate` | — | — | ✅ | ✅ |
| `lot:freeze` | — | — | ✅ | ✅ |
| `lot:recall` | — | — | — | ✅ |
| `actor:revoke` | — | — | — | ✅ |
| `redteam:run` | — | ✅ | ✅ | ✅ |
| `integrity:view` | — | — | ✅ | ✅ |

(`actor:revoke` is policy-reserved; no revocation UI exists yet.)

## Audit & integrity design

- Event: `seq, event_id (EVT-####), at, actor, action, target, outcome, context, prev_hash, record_hash`.
- `record_hash = sha256(seq|event_id|at|actor|action|target|outcome|context-json|prev_hash)`;
  genesis `prev_hash = "GENESIS"`. Deterministic demo clock, 2 seeded entries.
- `verify()` recomputes all hashes + links → `PASS` / `FAIL` (per-record expected-vs-stored
  evidence) / `NOT VERIFIED` (empty log). PASS is emitted only after a clean run.
- Stored context is identifiers + outcomes + presence flags only — note/reason free text and
  secrets never enter the unified log (lot-scoped logs keep their own demo records).
- `mock_audit.tamper_demo()` is test-only (mutate-without-rehash); routes/templates never call it.

## Frontend & mobile

- `templates/layouts/base.html`: sidebar, topbar (global serial search, session chip → `/access`),
  mobile drawer + 6-tab bar (Verify·Tower·Lots·Cases·Explore·Lab), toasts, `?v=5` asset cache-busting
  (bump the number whenever CSS/JS changes so browsers never run stale bundles).
- `static/css/`: `tokens` (palette/type) → `base` (shell) → `components` → `mobile.css`
  (≤900px: drawer, table→card reflow via JS-injected `data-label`, snap-rail checks, 44px targets).
- `static/js/`: `app.js` (copy/toast), `mobile.js` (drawer/search/tabs/cards/share, Alpine-aware),
  `scanner.js` + `verify_scan.js` (on-device camera QR/barcode → serial, `html5-qrcode` vendored).
- Hamburger is mobile-only (sidebar pinned on desktop); the show/hide rules share one
  selector across breakpoints so visibility is decided by width alone.

## Project structure

```
app/
  main.py            # factory, router registration, static mount
  config.py          # env + title
  models/            # verify, explorer, operations, lots, redteam, access, audit
  routes/            # verify, operations, explorer, redteam, lots, access, audit, session
  services/          # deps.py seam + mock_* (verify/explorer/operations/lots/redteam/access/audit) + scan_parse.py
templates/{layouts,pages,components}/   # 19 templates
static/{css,js}/     # tokens/base/components/mobile.css; app/mobile/scanner/verify_scan.js (+vendor)
tests/               # test_{verify,operations,explorer,redteam,lots,scan,regression,access,audit}.py
```

## Conventions

- Typed errors, never `None` verdicts; API failures are 4xx/5xx pages, never all-clear states.
- `VERIFIED` = consistent history, not physical authenticity (caveat rendered on every verdict).
- Idempotent repeats (`already-frozen`) recorded, not errored. `ruff`/`mypy --strict` clean required.
- Test isolation: module stores reset via autouse fixtures (`reset_demo_state()`).

## Integrating a real backend (convergence)

Replace a `mock_*` module behind the same `deps.*` signatures with the real client; keep the
Pydantic models as the contract. Pages, RBAC, audit fan-in, and tests keep working. Keep `DEMO DATA`
labels on anything still simulated. Secrets stay server-side; the browser never verifies
signatures, enforces permissions, or computes verdicts authoritatively.

## Limitations (demo)

In-memory stores (restart wipes state); demo role cookie instead of identity; no user admin (directory
is fixed); chain data is fixtures with real Merkle math; camera needs localhost/HTTPS secure context.
