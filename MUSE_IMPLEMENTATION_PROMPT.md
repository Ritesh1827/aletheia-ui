# Muse Implementation Prompt: TrustTrace Web Application

## Project context

You are implementing the **Web layer only** for a hackathon project
called **Physical-to-Digital Anti-Counterfeit Trust Fabric**.

Before editing code, read `TrustTrace_Web_UI_UX_Spec.md` in full. Treat
it as the source of truth for UI/UX, color tokens, typography, component
architecture, pages, RBAC, the custom provenance Block Explorer, API
boundaries, trust language, and implementation priorities.

Pipeline context: Physical tag/QR → signed EPCIS event → off-chain event
log + on-chain anchor → rules/AI evidence verdict → Web Verify page +
Control Tower + Red-Team console.

Do not claim to implement physical NFC security, backend cryptography,
blockchain contracts, IoT sensors, or anomaly detection as part of the
frontend. Integrate existing APIs when available. If APIs are
unavailable, use a replaceable mock service with the same typed
interface as the intended API, and label mock data clearly.

## Primary objective

Build a polished, cohesive, distinctive, component-based frontend that
feels like a supply-chain forensic operations tool, not a generic AI
dashboard.

Required pages: - Control Tower - Product Verify - Provenance timeline -
Incident investigation - Lots and Recall - Domain-specific Provenance
Block Explorer - Red-Team Lab - RBAC / Access Control - Audit &
Integrity

## Non-negotiable design rules

1.  Follow the **Oxide Observatory** design system in
    `TrustTrace_Web_UI_UX_Spec.md`.
2.  Preserve the exact palette tokens and HEX values. Do not substitute
    generic purple/blue gradients, glowing blobs, excessive
    glassmorphism, or a default AI-dashboard style.
3.  Use IBM Plex Sans for UI and IBM Plex Mono for identifiers, hashes,
    JSON, and technical data where practical, with fallbacks.
4.  Apply the specified typography scale, spacing, surface colors,
    borders, and status colors consistently.
5.  Make the UI information-dense but readable, aligned, responsive, and
    restrained in its use of motion.
6.  Every meaningful button must use a reusable component or shared
    variant, have a clear action, and support loading/disabled states
    and feedback.
7.  Provide loading, empty, error, unauthorized, and demo states
    wherever relevant.
8.  Never rely on color alone for status. Include visible labels and
    suitable icons.
9.  `VERIFIED` means available history checks are consistent. It does
    not guarantee physical authenticity.

## Component architecture

Inspect the existing repo and adapt to its current stack rather than
needlessly replacing it. Create reusable, typed components for: - Button
variants: primary, secondary, outline, ghost, danger, loading -
IconButton with accessible label/tooltip - Inputs, search, select,
checkbox, switch - Dialog, confirmation dialog, drawer, dropdown, tabs,
tooltip - StatusBadge and VerdictBanner - MetricCard, DataTable,
FilterBar - Timeline / ProvenanceTimeline - EvidenceList / FindingCard -
HashDisplay with copy action - JSON viewer - Toast, inline alert,
skeleton, empty state, error state - AppSidebar, TopBar, Breadcrumbs,
RoleGate - Explorer-specific block, transaction, anchor, contract-event,
and Merkle-proof components - Red-Team scenario cards and result panels

Avoid duplicate components and giant single-file pages. Componentize
reusable behavior and domain concepts, not every trivial text span.

## Custom Block Explorer

Build a **Provenance Anchor Explorer**, not a generic cryptocurrency
explorer. Focus on: - Supply-chain anchor batches, lot commitments,
Merkle roots - Transaction and contract-event details - Links from
anchors to lots, serials, event IDs, and proof bundles - Merkle proof
viewer with leaf hash, sibling hashes/directions, computed root,
expected root, and verification status when real proof data exists -
Actual network/RPC state and latest anchor where available - Honest
pending, disconnected, stale, and missing-payload states

Do not add token prices, coin logos, NFT galleries, or generic crypto
market widgets. Do not fabricate chain data. Label mock data
`DEMO DATA`.

## RBAC

Implement the RBAC experience described in the spec: Users, Roles &
Permissions, Registered Actors, Access Audit, role-aware navigation,
permission matrix, and confirmation flows for privileged actions.

Frontend role checks are a UX aid only. Backend authorization must
enforce every privileged action. Never expose private keys, signing
secrets, or admin credentials in client code. If auth/permission APIs
are missing, use a clearly labelled demo role selector/mock session and
state that server-side enforcement is still required.

## API integration

-   Inspect existing routes, response types, environment variables,
    scripts, and components before changes.
-   Preserve working code and dependencies; do not change frameworks
    without a concrete reason.
-   Confirm real endpoint names and schemas before wiring them.
    Candidate endpoints in the spec do not prove that every endpoint
    exists.
-   Centralize API calls in typed service modules, not visual
    components.
-   Keep mock adapters replaceable by real services.
-   Never turn an API failure into an empty or successful verification
    result.
-   Do not claim that browser code authoritatively verifies signatures,
    enforces permissions, validates Merkle proofs, or computes the
    trusted verdict.
-   Keep private keys and privileged secrets server-side.

## Work in stages

### Stage 1: Inspect and plan

Read the spec and inspect the repository. Report the existing stack,
what is already implemented, what is missing, and a short plan. Do not
make destructive changes during inspection.

### Stage 2: Foundation

Set up design tokens, typography, app shell, sidebar, top bar,
responsive layout, and shared components. Build a representative screen
to validate the visual system. Run available build/lint/type-check
commands and fix errors.

### Stage 3: Core screens

Implement in this order: 1. Product Verify: search, verdict, checks,
evidence, timeline, proof summary. 2. Control Tower: operational
metrics, incident queue, anchor/lot status. 3. Incident detail:
evidence-led investigation. 4. Provenance Block Explorer: search,
anchors, block/transaction detail, Merkle proof viewer. 5. Red-Team Lab:
controlled scenarios and result feed. 6. Lots & Recall. 7. Audit &
Integrity. 8. RBAC / Access Control.

If time is tight, prioritize the first five, but keep the app navigable
and retain the RBAC plan.

### Stage 4: Verification

Run available build, lint, and type-check commands. Test navigation,
every visible button, loading/empty/error/unauthorized/demo states, and
desktop/mobile layouts. Confirm no secrets are shipped in the frontend.
Report which features use real APIs and which are mocked.

## Coding standards

-   Use TypeScript types for API and domain objects if supported by the
    existing stack.
-   Centralize design tokens.
-   Keep components small and understandable.
-   Avoid unnecessary dependencies, services, databases, or a new
    backend just to make the UI look functional.
-   Do not remove existing features without explaining why.
-   Avoid dead buttons, fake spinners, unhandled promise failures, and
    console errors.
-   Use realistic, internally consistent fixtures for mocks, labelled as
    demo.
-   Never claim a service is connected unless verified.

## Completion report

At the end of each stage, report: 1. Files created or changed. 2.
Screens/components completed. 3. Real API integrations versus mock data.
4. Build/type-check/lint results. 5. Known gaps and the next smallest
useful step.

**Begin with Stage 1: inspect the existing repository and read
`TrustTrace_Web_UI_UX_Spec.md`. Do not immediately overwrite or
regenerate the entire project.**
