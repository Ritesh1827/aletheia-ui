# Aletheia, Explained in Plain Words

**What this is:** a demo web app for catching fake products. Someone sticks a tag or QR code on a
physical item (a sensor housing, a medicine box, anything valuable). Every time that item moves —
factory → truck → warehouse → shop — somebody scans it and the system writes down *what happened,
where, when, and who saw it*. Later, anyone can type in the serial number and the app answers one
question: **"does this item's life story make sense?"**

The honest rule behind everything: **a QR code can be photocopied**. So the app never says "this is
100% genuine". It says "the available records are consistent" (VERIFIED) or "two records contradict
each other" (CLONE DETECTED) — and it always shows its work.

---

## 1. The big pipeline (5 steps)

Think of it like a passport control for products:

| Step | Real-world meaning | What this repo implements |
|------|--------------------|---------------------------|
| 1. Tag | A chip/QR/seal on the item | *Not in this repo* — the web app just reads typed or scanned serials |
| 2. Event | Each scan creates a signed note: "item X was in Oslo at 9:12, seen by Store 14" | Fixture events (`evt-0001`…) + a camera scanner that reads QR/barcodes on the Verify page |
| 3. Ledger | Notes are bundled; a fingerprint (Merkle root) of each bundle is anchored on a blockchain | Mock ledger + mock chain data, inspected in the Block Explorer |
| 4. Rules | Detectors check: is the custody order sane? Is the movement physically possible? Is the actor registered? | Deterministic demo rules (`R-VELOCITY-04`, `R-DUP-IDENTITY-02`, …) |
| 5. Web | Humans read verdicts, investigate cases, freeze bad lots | This whole repo — FastAPI + Jinja2 pages |

**This repo = step 5 only** (the web layer), running on replaceable mock data for steps 2–4.

---

## 2. The demo story (follow one serial)

Two serials carry the whole demo:

- **`AL-DEMO-0001` — the good citizen.** Made at the factory, quality-checked, shipped to
  Northwind Logistics, received at a depot, sent onward. Six events, all in order, plausible places
  and times. Verdict: **VERIFIED** (risk 8/100), with one gentle note: no post-sale scan exists yet.
- **`AL-DEMO-0002` — the cloned QR.** Scanned in **Oslo at 09:12** and in **Gdansk at 09:53** —
  1,140 km apart in 41 minutes. No truck drives that fast. On top of that, a second custody claim
  appears from an unknown party. Verdict: **CLONE_DETECTED** (risk 92/100) with two critical
  findings naming the exact rules and event IDs, plus what to do next ("quarantine the unit").

Two more fixtures round it out: `AL-DEMO-UNKNOWN` (serial nobody recognizes → honest "unknown"
state) and `AL-DEMO-ERR` (simulated backend failure → error page with retry, *never* a fake
all-clear).

---

## 3. Backend, piece by piece (`app/services/`)

All services are **mocks with typed interfaces** — same function signatures a real backend would
expose, so the real thing can be plugged in later without touching pages. The seam is
`app/services/deps.py` (one function per capability).

- **`mock_verify.py` — the verdict engine (mock).** `verify_serial()` returns a full
  `VerificationVerdict`: identity, 5 plausibility checks (lot commitment, chain integrity, actor
  authorization, custody sequence, movement plausibility), evidence findings with rule IDs and next
  steps, a custody-vs-observation timeline, and an anchor proof bundle. Unknown serials and backend
  failures raise typed errors instead of returning fake success.
- **`mock_explorer.py` — the fake blockchain index.** Anchors (`ANCH-DEMO-1/2`), blocks,
  transactions, a registry contract, network status (live / stale / disconnected), and **real
  SHA-256 Merkle math**: proof paths are genuinely derived leaf→root, and verification genuinely
  recomputes. A `tampered_proof_demo()` vector (one corrupted sibling) proves FAIL is reachable.
- **`mock_operations.py` — Control Tower + incidents.** Tower metrics, the incident queue
  (`INC-1042` velocity conflict, `INC-1041` duplicate claims, …), case detail with conflicting
  observations side by side, and investigator action logging.
- **`mock_lots.py` — Lots & Recall.** Two committed lots (`LOT-DEMO-A` 10,000 units anchored,
  `LOT-DEMO-B` 2,500 units pending anchor), freeze/recall with typed lot-ID confirmation,
  idempotent repeats, blast-radius traces (lot → units → custodians → cases), and per-lot audit.
- **`mock_redteam.py` — the attack simulator.** Six scenarios that run *real logic* on your
  inputs (velocity math with haversine distance, registry lookup, custody-transition checks, proof
  recomputation, claim comparison, lifecycle ordering). Outcomes follow inputs — nothing is
  pre-declared "detected".
- **`mock_access.py` — roles & permissions.** Four demo roles (Read-only Verifier, Operator,
  Investigator, Admin) over eight permissions, a full permission matrix, an access audit that records
  allowed *and denied* attempts, and `require()` — the single backend enforcement point.
- **`mock_audit.py` — the hash-chained audit log.** Every privileged action appends an event;
  each record embeds the SHA-256 of the previous one. `verify()` recomputes the whole chain:
  **PASS** (clean run), **FAIL** (names the altered record or broken link with expected-vs-stored
  evidence), **NOT VERIFIED** (empty log). Free-text notes and secrets are never stored — only IDs,
  actions, outcomes, and presence flags.
- **`scan_parse.py` — scan interpreter.** Turns raw camera output into a serial: plain `AL-…`
  serials pass through; `AL:`-prefixed payloads and `verify.aletheia.example` URLs yield a serial;
  anything else is AMBIGUOUS (shown to the user, never auto-verified).

---

## 4. Frontend, page by page (`templates/` + `static/`)

Server-rendered pages (FastAPI + Jinja2), sprinkled with HTMX and Alpine.js — no SPA framework.

- **Verify (`/verify`, `/verify/:serial`)** — the heart. Serial lookup with camera scanning,
  verdict banner (status + plain-language label + risk + confidence + the ever-present caveat),
  check matrix, evidence findings, filterable provenance timeline, proof bundle with copy buttons,
  and on mobile a sticky Copy/Timeline/Proof dock.
- **Control Tower (`/overview`)** — shift status: metrics, filterable incident queue, custody feed,
  anchor health, lot status, integrity summaries, demo-safe quick actions.
- **Incidents (`/incidents`, `/incidents/:id`)** — investigation workspace: severity, findings,
  conflicting observations side-by-side, next steps, action audit, note/accept actions.
- **Lots & Recall (`/lots`, `/lots/:id`, `/lots/:id/blast-radius`)** — inventory table, lot detail
  with observed units, freeze/recall behind typed confirmation, blast-radius tree, audit download.
- **Provenance Explorer (`/explorer`, `/explorer/block|tx|address/...`)** — a *supply-chain*
  explorer, not a coin explorer: anchors, registry events, lots, Merkle proof viewer with
  leaf/siblings/directions/computed-vs-expected root. Honest disconnected/stale/missing-payload
  states; `?mode=` previews them.
- **Red-Team Lab (`/red-team`)** — six scenario cards with detectors, run forms, result pages
  showing triggered rules and evidence links.
- **Access Control (`/access`)** — live permission matrix, session card, demo role switcher,
  role/user directory, access audit. Always labelled demo — switching roles is a convenience, not
  a login.
- **Audit & Integrity (`/audit`)** — verification banner (PASS/FAIL/NOT VERIFIED), filterable
  event log with record hashes, failure evidence table.
- **403 page** — denials name the missing permission and the current role, and note the attempt
  was recorded. No data leaks.

**Design language:** warm paper surfaces, ink borders, one red accent, status colors always paired
with text labels. System fonts (no webfont downloads). **Mobile** gets a bottom tab bar
(Verify·Tower·Lots·Cases·Explore·Lab), a slide-in drawer, tables that reflow into labeled cards, a
snap-scrolling check rail, and ≥44px touch targets (`static/css/mobile.css` + `static/js/mobile.js`).

---

## 5. Backend enforcement (why hiding buttons is not security)

Permissions live in **one matrix** and are enforced in **one function** (`require()`), called by
`session.guard()` at the top of every privileged route: lot freeze/recall, incident annotate,
red-team execution, viewing the audit log. The UI also disables buttons you can't use — but that's
courtesy; the server re-checks everything and answers 403 with an audit trail. Tests prove each
role's allows *and* denials, including spoofed role values (unknown roles collapse to the
read-only verifier).

---

## 6. Blockchain, honestly

There is **no real blockchain connected**. What exists:

- A mock chain index (chain ID `31337` — the well-known local-dev identifier) with blocks,
  transactions, a registry contract address, and anchor records.
- **Genuine Merkle mechanics** on fixture data: roots are derived, proofs recompute, tampering is
  detected for real — the cryptography is honest, only the network is pretend.
- The spec's production vision (local Hardhat/Anvil demo network, off-chain event log + on-chain
  Merkle roots/freeze/revocation) is documented in `Aletheia_Web_UI_UX_Spec.md` as the integration
  target, not as something already built.

Rule of thumb used everywhere: **records can be verified; physical items cannot be proven genuine
by software.** Every PASS/VERIFIED label carries that caveat.

---

## 7. Convergence: how the pieces (and future partners) plug together

"Convergence" here means two things, both designed in:

1. **Inside the app:** everything meets at typed seams. Pages never call mocks directly — routes
   call `deps.*`, which today forward to `mock_*` modules. The audit log is the cross-cutting
   thread: lots, incidents, red-team, and access all append to one hash-chained record.
2. **With outside systems:** each mock mirrors the intended real contract
   (`VerificationVerdict`, `AnchorProof`, `BlastRadius`, …). A convergence partner (real signer,
   real chain indexer, real anomaly engine) replaces a `mock_*` module behind the same `deps`
   functions; pages, tests, and RBAC keep working because they only ever see the typed shapes.
   Mock payloads are always labelled `DEMO DATA` so real and simulated evidence can never be
   confused during integration.

---

## 8. Glossary (jargon → plain English)

- **Serial** — the ID printed/encoded on one physical unit (`AL-DEMO-0001`).
- **Lot** — a manufacturing batch (e.g. 10,000 units committed under one Merkle root).
- **Custody event** — a signed handover (offer → accept → receive). **Observation** — a sighting
  (a scan ping) without ownership change.
- **Merkle root / anchor** — a fingerprint of a whole event bundle, stamped onto the chain so
  later tampering shows.
- **Verdict** — the app's reading of a serial's *records*: VERIFIED means consistent history.
- **RBAC** — role-based access control: who may do what, enforced by the server.
- **Blast radius** — if a lot is bad, which units, custodians, and cases are exposed.
- **Red-team** — friendly attacks you run against yourself to test the detectors.
- **Idempotent** — repeating an action (re-freezing a frozen lot) safely changes nothing.
