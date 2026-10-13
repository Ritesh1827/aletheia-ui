# TrustTrace Web Application

## UI/UX, Design System, Component Architecture, RBAC, and Block Explorer Specification

**Project:** Physical-to-Digital Anti-Counterfeit Trust Fabric\
**Scope:** Web layer only

## 1. Scope

The solution pipeline is:

1.  Physical: NTAG 424 DNA SUN / seal-ID / QR
2.  Event: signed GS1 EPCIS 2.0 JSON-LD event
3.  Ledger: off-chain event log plus on-chain Merkle roots, freeze, and
    revocation
4.  AI/rules: velocity, duplicate identity, and custody checks producing
    an evidence-backed verdict
5.  Web: Verify page, Control Tower, and Red-Team console

This document specifies **only the Web layer**. The frontend consumes
backend APIs. It does not implement the physical tag, signer, anomaly
engine, blockchain contract, or IoT sensors. If APIs are not ready, use
replaceable mock services and label all simulated data clearly.

**Product principle:** Assume the QR can be cloned. Show why a product
history is or is not plausible, and make every verdict inspectable.

`VERIFIED` means the available history checks are consistent. It does
not guarantee that the physical item is genuine.

## 2. Information architecture

### Primary navigation

1.  Overview / Control Tower
2.  Verify Product
3.  Provenance
4.  Incidents
5.  Lots & Recall
6.  Block Explorer
7.  Red-Team Lab
8.  Access Control
9.  Audit & Integrity
10. Integrations, if supported

Use a persistent desktop sidebar and a compact top bar with global
search, environment status, notifications, and account/role menu. Show
only navigation permitted to the current role, but always enforce
permissions on the backend too.

### Suggested routes

  Route                             Purpose
  --------------------------------- -------------------------------
  `/overview`                       Control Tower
  `/verify`                         Serial/QR lookup
  `/verify/:serial`                 Verdict and proof
  `/provenance/:serial`             Timeline and custody history
  `/incidents`                      Incident queue
  `/incidents/:id`                  Investigation workspace
  `/lots`                           Lot inventory
  `/lots/:id`                       Lot commitment and status
  `/lots/:id/recall`                Recall blast-radius
  `/explorer`                       Provenance Block Explorer
  `/explorer/block/:heightOrHash`   Block details
  `/explorer/tx/:hash`              Transaction/anchor details
  `/explorer/address/:address`      Actor or contract address
  `/red-team`                       Scenario console
  `/access/users`                   User and role administration
  `/access/roles/:role`             Permission matrix
  `/access/actors`                  Actor registry and revocation
  `/audit`                          Integrity checks
  `/integrations`                   Partner status, if supported

## 3. Distinctive visual identity: "Oxide Observatory"

Avoid generic AI-SaaS visuals: purple-blue gradients, glowing blobs,
pervasive glassmorphism, and excessive rounded cards. Aim for a precise
forensic instrument: mineral-dark surfaces, oxidized copper, warm paper
text, and restrained status colors.

### Color tokens

  Token               Hex         Use
  ------------------- ----------- -------------------------
  `canvas`            `#111416`   Main background
  `surface-1`         `#191E20`   Sidebar and panels
  `surface-2`         `#22292B`   Raised surfaces
  `surface-3`         `#2C3536`   Hover/selected surfaces
  `line`              `#394344`   Borders and separators
  `text-primary`      `#F0E9DC`   Main text, warm ivory
  `text-secondary`    `#B6B7AD`   Secondary labels
  `text-muted`        `#858E89`   Metadata/disabled text
  `oxide`             `#D47752`   Primary accent
  `oxide-hover`       `#E28A63`   Hover state
  `oxide-pressed`     `#B95D3C`   Pressed state
  `copper-pale`       `#F0B08B`   Proof highlights/focus
  `signal-good`       `#8FBEA5`   Passed checks
  `signal-watch`      `#E2BB69`   Suspicious/review
  `signal-critical`   `#E4776C`   Critical/clone/tampered
  `signal-info`       `#8EB8C3`   Informational status

Use color semantically, not decoratively. Pair every status color with a
text label and icon. Suggested balance: 70% dark surfaces, 20% neutral
text/space, 8% oxide accents, 2% status colors.

### Typography

Use **IBM Plex Sans** for UI and reading, and **IBM Plex Mono** for
serials, hashes, event payloads, and numbers. Provide local
sans-serif/monospace fallbacks.

  -----------------------------------------------------------------------
  Token             Size /            Weight            Use
                    line-height                         
  ----------------- ----------------- ----------------- -----------------
  `display`         32 / 38 px        600               Main page title
                                                        only

  `h1`              26 / 32 px        600               Page title

  `h2`              20 / 26 px        600               Section heading

  `h3`              16 / 22 px        600               Panel heading

  `body`            14 / 21 px        400               Default content

  `body-strong`     14 / 21 px        600               Table emphasis

  `small`           12 / 17 px        400               Supporting labels

  `eyebrow`         10 / 14 px        600, uppercase,   Section category
                                      0.10em tracking   

  `metric`          28 / 32 px        600, tabular      Key metrics
                                      numerals          

  `code`            12 / 18 px        400, monospace    IDs, hashes, JSON

  `button`          13 / 18 px        600               Button text
  -----------------------------------------------------------------------

### Layout and motion

-   8 px spacing system: 4, 8, 12, 16, 24, 32, 40, 48, 64.
-   Sidebar: 232--248 px; top bar: 60--68 px.
-   Dashboard max width: 1600 px; verification reading width: around
    1120 px.
-   Panel radius 8 px; buttons/inputs 6 px. Use thin borders and minimal
    shadows.
-   Use motion only for meaningful feedback, typically 120--240 ms.
    Respect reduced-motion preferences. Avoid pulsing backgrounds and
    decorative chain animations.
-   Use one consistent line-icon family. Icons reinforce labels rather
    than replace them.

## 4. Component-based architecture

Every meaningful control must be reusable and independently styled, with
variants, states, accessibility behavior, and typed props.

``` text
src/
  app/                 # routes, layouts, providers
  components/
    primitives/        # Button, IconButton, Input, Select, Checkbox, Switch,
                       # Tabs, Tooltip, Dialog, Drawer, DropdownMenu,
                       # CopyButton, CodeBlock, Skeleton, EmptyState, ErrorState
    navigation/        # AppSidebar, TopBar, Breadcrumbs, RoleGate
    data-display/      # StatusBadge, VerdictBanner, MetricCard, DataTable,
                       # FilterBar, Timeline, EvidenceList, HashDisplay,
                       # JsonViewer, Pagination, KeyValueGrid
    provenance/        # ProductSearch, ProductIdentityCard, ProvenanceTimeline,
                       # CustodyStep, RouteMap, ProofBundlePanel, RecallTree
    explorer/          # ExplorerSearch, BlockSummary, BlockRow, TransactionRow,
                       # AnchorTransactionCard, MerkleProofViewer,
                       # ActorAddressCard, ContractEventLog, ChainHealthPanel
    incidents/         # IncidentQueue, SeverityBadge, EvidenceDrawer,
                       # FindingCard, NextActionPanel
    access/            # UserTable, RoleBadge, PermissionMatrix,
                       # RoleAssignmentDialog, ActorRegistryTable, RevokeActorDialog
    red-team/          # ScenarioCard, AttackActionButton, Confirmation,
                       # ScenarioResultPanel, LiveEventFeed
    feedback/          # Toast, InlineAlert, ConfirmDialog
  features/            # verification, incidents, lots, explorer, access, red-team, audit
  services/            # apiClient and feature-specific API services
  hooks/
  types/
  utils/
  styles/
```

### Component contract

Each component defines purpose, variants, typed props, relevant
loading/disabled/focus/success/error states, accessible name,
empty/error behavior, and tests for critical interactions. Prefer
composition over duplicated components.

### Button variants

  Variant       Use
  ------------- ------------------------------------------------------
  Primary       Main page action, e.g. Verify
  Secondary     Supporting workflow
  Outline       Less prominent bordered action
  Ghost         Table row and navigation actions
  Danger        Revoke, freeze, recall
  Icon button   Copy/open/refresh, with tooltip and accessible label
  Loading       Pending API action; prevent duplicate submission

Use an oxide primary button sparingly. Destructive actions need
target-specific confirmation.

### Shared primitives

-   `StatusBadge`: verified, suspicious, clone detected, tampered,
    recalled, pending, revoked, unknown.
-   `VerdictBanner`: status, explanation, risk score, confidence,
    uncertainty.
-   `MetricCard`: label, value, context, status, loading state.
-   `HashDisplay`: truncated hash, reveal/copy full value.
-   `EvidenceList`: rule ID, severity, reason, event references, next
    step.
-   `Timeline`: chronological events/findings; custody events visually
    differ from observations.
-   `DataTable`: sorting, filters, pagination, loading/empty states, row
    actions.
-   `JsonViewer`: syntax-aware JSON, copy/download, collapsible long
    values.
-   `Toast`, `InlineAlert`, `ConfirmDialog`, `EmptyState`, `ErrorState`,
    and `Skeleton`.

Keep API logic out of presentation components. Use typed services,
explicit loading/empty/error/stale/partial states, request
cancellation/deduplication where needed, and server-confirmed updates
for recall, freeze, revocation, and role changes. A mock service must
use the same response types as the real service.

## 5. Core page specifications

### A. Control Tower (`/overview`)

-   Header, environment badge, last-updated time.
-   Metrics: open critical incidents, contested serials, frozen lots,
    anchored batches, integrity status.
-   Incident queue: severity, serial, rule, conflict summary, time,
    status.
-   Secondary panels: lot status, anchor health, recent custody events,
    recent integrity checks.
-   Quick actions: verify serial, inspect incident, open Red-Team Lab.
-   Every metric links to a filtered view. No decorative charts without
    operational meaning. Show demo-data banner when applicable.

### B. Verify (`/verify`, `/verify/:serial`)

1.  Search by serial/QR payload; optional scanner only if implemented.
2.  Verdict banner: `VERIFIED`, `SUSPICIOUS`, `CLONE_DETECTED`,
    `TAMPERED`, `RECALLED`, or `UNKNOWN`.
3.  Caveat: "This verdict assesses available records and history. It
    does not independently prove the physical item is genuine."
4.  Identity: serial, lot, product, lifecycle status, permitted
    custodian.
5.  Check matrix: lot commitment, chain integrity, actor authorization,
    custody sequence, movement plausibility.
6.  Evidence findings with rule IDs, severity, reasons, references,
    uncertainty, and next steps.
7.  Provenance timeline; distinguish custody events from observation
    events.
8.  Map only when authorized location data exists; label simulated data.
9.  Proof panel: anchor ID, Merkle root, transaction hash,
    inclusion-proof status.
10. Copy serial, download proof bundle, open provenance; claim action
    only if supported.

Never display "100% genuine". `VERIFIED` means available history checks
are consistent.

### C. Incident Investigation (`/incidents/:id`)

Show severity, status, serial, time, plain-language reason, findings,
linked events, chronological evidence timeline, conflicting observations
side-by-side, risk score explanation, confidence/uncertainty, next
steps, and investigator action audit. Actions may include assign,
annotate, review, resolve, escalate, export. Resolution must not erase
original findings.

### D. Lots & Recall

Show lot ID, committed quantity, Merkle root, anchor status, freeze
state, permitted custodians/containers, and incidents. Recall view can
show lot-to-case-to-pallet hierarchy, affected/sold/claimed/unlocated
quantities, custodians, and pull-stock tasks only when supplied by the
backend. Confirm freeze/recall with the exact target and impact. Never
invent counts.

### E. Red-Team Lab (`/red-team`)

Scenario cards: - Clone QR / conflicting locations - Invented serial /
quantity overflow - Invalid or revoked actor - Fake handover - Database
tampering / integrity failure - Double claim - Post-sale scan

Each card states what it simulates, demo target, expected detector, and
action. Label simulation clearly. After execution show API result,
verdict/incident, triggered rule IDs, evidence references, timestamp,
and link to the affected serial. Protect red-team routes server-side and
do not expose them in production.

### F. Audit & Integrity (`/audit`)

Show latest run, checked records, valid/invalid signatures, broken chain
links, root mismatches, anchored-root status, and report download if
supported. Distinguish `PASS`, `FAIL`, `NOT CHECKED`, and `STALE`. Every
failure links to the relevant event, batch, or incident.

## 6. Custom Block Explorer: Provenance Anchor Explorer

This is **not** a generic cryptocurrency explorer. It focuses on
supply-chain event batches, lot commitments, contract events, and
verifiable product histories.

### Landing page

Title: **Provenance Explorer**\
Subtitle: "Inspect anchored supply-chain evidence, not token prices."

Search accepts block height/hash, transaction hash, Merkle root, lot ID,
serial, actor address, or contract address.

Status strip, based on actual API/RPC data: - Network name and chain
ID - RPC connection state - Latest block number - Latest successful
anchor - Pending/unanchored event count, if available - Contract
address - Data freshness

Main panels: 1. **Latest Provenance Anchors:** anchor ID, block, time,
root, event count, lot/batch, transaction. 2. **Recent Registry
Events:** actual emitted events such as lot registration, actor status
changes, lot freeze, and batch anchors. 3. **Lots with Recent Anchors:**
lot ID, committed quantity, freeze state, root. 4. **Anchor Health:**
successful anchors, pending batches, latest failure, audit result.

### Block detail

Show block height/hash, parent hash, timestamp, transaction count,
transactions, method/event summary, sender, contract, status, and
related lot/anchor. Show gas fields only if the connected chain provides
them. Do not show mining fields or mainnet-specific details unless
actually available.

### Transaction / anchor detail

Show transaction hash, success/failure/pending status, block and
timestamp, from/to contract, method/event type, gas/fee if available,
related lot/root/anchor, Merkle root, batch leaf count, contract event
log, related off-chain event IDs, proof status, and links to lot/product
history. If chain transaction exists but off-chain payload is missing,
display a partial-evidence warning. Never fabricate event details from a
root hash.

### Merkle proof viewer

-   Leaf event hash
-   Sibling hashes and left/right direction
-   Compact proof-path/tree diagram
-   Computed root and expected anchored root
-   `PROOF VALID`, `PROOF INVALID`, or `NOT VERIFIED`
-   One-sentence explanation
-   Copy/download proof bundle if supported

Only show valid/invalid after verification actually runs. Static
examples must be labelled.

### Cross-navigation and visual language

Connect lot commitment → lot → serial → batch anchor → transaction →
Merkle proof. Use oxide for selected paths, monospace for
hashes/addresses, readable row spacing, and clear status labels. No
token-price charts, coin logos, gas speculation, NFT galleries, or
generic crypto-market widgets.

## 7. RBAC UI

RBAC must be visible and understandable, but enforced by the backend.
Frontend role checks are a UX aid, not a security boundary.

### Proposed roles

  --------------------------------------------------------------------------
  Role                                Capabilities
  ----------------------------------- --------------------------------------
  Consumer / Public Verifier          Public serial status and permitted
                                      proof summary

  Manufacturer                        Register authorized lots/products and
                                      create manufacture events

  Logistics / Custodian               Offer/accept transfers and submit
                                      permitted observations

  Retailer                            Receive stock, mark sale where
                                      authorized, inspect assigned history

  Investigator / Auditor              Read
                                      incidents/evidence/provenance/audit;
                                      annotate if granted

  Recall Manager                      Freeze/recall authorized lots and
                                      manage response

  Registrar / Admin                   Manage actors, roles, and revocation
                                      within policy

  Demo Operator                       Run red-team simulations in a
                                      protected demo environment
  --------------------------------------------------------------------------

These are proposed UI roles; map them to actual backend permissions
before production.

### Access Control screen

Tabs: **Users**, **Roles & Permissions**, **Registered Actors**,
**Access Audit**.

Users table: identity, role, organization, status, MFA status/last
active only if supplied, permitted actions. Role detail: purpose,
grouped permission matrix, assigned users if available, read/write/admin
distinctions, save/cancel when editing is supported.

### Example permission matrix

  ------------------------------------------------------------------------------------------------------------
  Resource /      Public    Manufacturer   Logistics   Retailer     Investigator   Recall       Registrar
  action                                                                           Manager      
  --------------- --------- -------------- ----------- ------------ -------------- ------------ --------------
  Verify public   Yes       Yes            Yes         Yes          Yes            Yes          Yes
  status                                                                                        

  View internal   No        Own lots       Assigned    Assigned     Yes            Authorized   Yes
  evidence                                                                         lots         

  Register lot    No        Authorized     No          No           No             No           Policy-based

  Offer/accept    No        If custodian   Yes         If custodian No             No           No
  custody                                                                                       

  Mark sold       No        No             No          Authorized   No             No           No

  Freeze/recall   No        No             No          No           Recommend      Authorized   Emergency only
                                                                                                by policy

  Revoke actor    No        No             No          No           Recommend      No           Yes

  Run red-team    No        No             No          No           No             No           Demo-only
  scenario                                                                                      permission

  View integrity  Public    Own scope      Own scope   Own scope    Yes            Authorized   Yes
  audit           summary                                                          scope        
  ------------------------------------------------------------------------------------------------------------

This is a starting proposal, not a substitute for the backend's actual
policy.

### RBAC interaction rules

-   Show current role and organization in account menu.
-   Explain unavailable actions, e.g. "Requires Recall Manager
    permission."
-   Hide sensitive actions where their existence is sensitive; otherwise
    disabled-with-explanation may help users understand workflows.
-   Backend must independently authorize every privileged request.
-   Confirm actor revocation, freeze/recall, role changes, and
    credential rotation.
-   Confirmation shows target and consequences.
-   Log actor, action, target, timestamp, outcome, and request ID where
    supported.
-   Do not allow administrators to silently grant themselves higher
    privileges.
-   Prefer least privilege over a universal super-admin interface.

Example:

``` tsx
<RoleGate permission="lot:recall">
  <Button variant="danger" onClick={openRecallConfirmation}>
    Recall lot
  </Button>
</RoleGate>
```

`RoleGate` improves UX only; the server must reject unauthorized
requests independently.

## 8. Verdict language

  Backend verdict           UI label                          Tone
  ------------------------- --------------------------------- -----------------
  `VERIFIED`                History checks passed             Good / neutral
  `SUSPICIOUS`              History needs review              Warning
  `CLONE_DETECTED`          Conflicting histories detected    Critical
  `TAMPERED`                Integrity check failed            Critical
  `RECALLED` / frozen lot   Lot recalled / frozen             Critical
  `UNKNOWN`                 Product identity not recognized   Neutral warning

Normalize statuses in one typed mapping layer. For each verdict show
checks, pass/fail, evidence refs, severity, confidence if supplied,
uncertainty, next step, and data freshness. Do not describe a risk score
as a calibrated probability unless the backend defines it that way.

## 9. API integration

The supplied project spec lists these candidate backend endpoints: -
`POST /lots` - `GET /products/{serial}/verify` -
`GET /products/{serial}/bundle` - `POST /events/sign` -
`GET /anomaly/:epc` - `GET /audit/integrity` - `POST /anchor/run` -
`POST /products/{serial}/claim` - `POST /redteam/*` -
`GET /lots/{id}/blast-radius` - `POST /lots/{id}/recall`

Confirm actual route names, methods, response schemas, authentication,
and error formats before integration; the spec does not define every
response.

Define TypeScript types for `Verdict`, `CheckResult`, `EvidenceFinding`,
`ProvenanceEvent`, `AnchorProof`, `Lot`, `Incident`, `Actor`, and
`AuditReport`. Centralize base URL and API configuration. Handle errors
consistently. Never place private keys, signing secrets, admin
credentials, or privileged tokens in frontend code. Browser UI must not
be authoritative for signature validity, permissions, Merkle
verification, or verdict calculation.

Suggested service boundaries:

``` ts
interface VerificationService {
  verifySerial(serial: string): Promise<VerificationVerdict>;
  getProofBundle(serial: string): Promise<ProofBundle>;
}

interface ProvenanceService {
  getTimeline(serial: string): Promise<ProvenanceEvent[]>;
  getLot(lotId: string): Promise<LotDetails>;
  getBlastRadius(lotId: string): Promise<BlastRadius>;
}

interface ExplorerService {
  getNetworkStatus(): Promise<ExplorerNetworkStatus>;
  search(query: string): Promise<ExplorerSearchResult>;
  getBlock(id: string): Promise<BlockDetails>;
  getTransaction(hash: string): Promise<AnchorTransactionDetails>;
  verifyMerkleProof(proofId: string): Promise<MerkleProofResult>;
}

interface AccessService {
  getCurrentPermissions(): Promise<Permission[]>;
  listUsers(): Promise<UserSummary[]>;
  getRolePermissions(roleId: string): Promise<RolePermission[]>;
}
```

These are proposed frontend contracts, not claims that these endpoints
already exist. If explorer RPC/indexer data is unavailable, use a
clearly labelled demo dataset. Respect the project spec's
coarse-location/privacy assumptions.

## 10. Responsive design and accessibility

-   Desktop: persistent sidebar, multi-column operational layout.
-   Tablet: collapsible sidebar and stacked secondary panels.
-   Mobile: prioritize Verify, verdict, evidence, and timeline; use
    drawers for filters/navigation.
-   Use semantic headings, form labels, visible keyboard focus,
    accessible dialogs, and WCAG AA contrast targets.
-   Never rely only on red/green status.
-   Provide accessible copy confirmation, form errors, and status
    announcements.
-   Restore focus after dialogs close and respect browser zoom/reduced
    motion.

## 11. Required page states

Every data-driven page must define: - **Loading:** layout-matched
skeletons. - **Empty:** explain what belongs here and how to find/create
it. - **Error:** plain-language error, safe retry, correlation ID if
supplied. - **Partial:** identify missing sources, e.g. "Event details
unavailable; on-chain root found." - **Stale:** show retrieval time. -
**Demo:** persistent `DEMO DATA` indicator for simulated chain, GPS,
sensors, or scenarios. - **Unauthorized:** explain missing permission
without leaking restricted data. - **Not found:** distinguish unknown
serial from backend failure.

Never convert API failure into an empty "all clear" state.

## 12. Security and trust UX checklist

-   [ ] Verdicts assess available records, not absolute physical
    authenticity.
-   [ ] Backend enforces RBAC.
-   [ ] Private keys and signing secrets never reach the browser.
-   [ ] Destructive actions have target-specific confirmation.
-   [ ] Revoked actors/frozen lots show status and timestamps.
-   [ ] Red-team endpoints are protected server-side.
-   [ ] Consumer views hide internal notes and sensitive locations.
-   [ ] Proof validity is shown only after actual verification.
-   [ ] Disconnected chain, pending anchor, and stale data are honest
    states.
-   [ ] Findings link to evidence.
-   [ ] Mock data is visibly labelled.
-   [ ] Status colors are paired with text.
-   [ ] API failures never imply success.

## 13. Recommended build order

### Phase 1: Foundation

1.  Palette, typography, spacing, tokens, responsive breakpoints.
2.  App shell, navigation, buttons, inputs, badges, tables, dialogs,
    toasts, and empty/loading/error states.
3.  Typed API client and mock/real service switch.

### Phase 2: Core demo

4.  Verify search and verdict page.
5.  Provenance timeline and evidence list.
6.  Control Tower and incident details.
7.  Connect real backend response shapes.

### Phase 3: Differentiators

8.  Provenance Block Explorer and Merkle proof viewer.
9.  Red-Team Lab and scenario results.
10. Lot/recall view where APIs are ready.
11. Audit & Integrity.

### Phase 4: RBAC and polish

12. Role-aware navigation and permission-aware actions.
13. Users, Roles & Permissions, Registered Actors.
14. Test each role against backend enforcement.
15. Mobile, keyboard, empty/error states, and fresh-demo rehearsal.

If time is tight, prioritize: Verify → Control Tower/incidents →
timeline → explorer anchor/transaction detail → Red-Team Lab → RBAC UI →
recall/admin. Do not trade accurate verdict language or correct
integration for decorative animation.

## 14. Definition of done

-   [ ] Search a serial and render its backend verdict.
-   [ ] Findings show evidence refs and next steps where supplied.
-   [ ] Timeline distinguishes custody events from observations.
-   [ ] Product/lot links to anchor, transaction, and Merkle proof where
    supported.
-   [ ] Explorer honestly labels missing or demo data.
-   [ ] Demo roles change navigation/action visibility correctly.
-   [ ] Backend rejects unauthorized requests even when UI is bypassed.
-   [ ] Red-team scenarios display actual API results and rule IDs.
-   [ ] Freeze/recall reflects confirmed backend result.
-   [ ] Every page has loading, empty, error, and unauthorized states.
-   [ ] Desktop/tablet/mobile layouts remain usable.
-   [ ] No private frontend secrets.
-   [ ] README enables another developer to run the Web app.

## 15. Assumptions

1.  The supplied master spec defines backend, cryptographic, chain, and
    anomaly concepts; this document translates them into the Web
    experience only.
2.  Palette, routes, component tree, roles, and layouts are design
    recommendations.
3.  Verify endpoints and schemas against the actual implementation.
4.  Label local Hardhat/Anvil as a local demo network.
5.  Label HMAC-based NFC/SUN simulation as simulated.
6.  `VERIFIED` means history consistency, not absolute physical
    authenticity.
7.  Reusable feature components and typed services should make
    integration with the backend and convergence partners easier without
    rewriting the UI.
