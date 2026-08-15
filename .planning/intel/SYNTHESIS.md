# Document Synthesis Summary

## Documents

- Total synthesized: 5
- ADR: 1
- SPEC: 1
- PRD: 0
- DOC: 3
- UNKNOWN: 0

All five classification records were consumed. Cross-reference traversal covered five classified nodes, did not exceed depth 50, and found no cycles.

## Decisions

- Locked decisions: 0
- Proposed decisions: 1
- Source: `57BIT_RETAINED_STATE.md`

See `decisions.md`.

## Requirements

- Extracted requirements: 0
- Requirement IDs: none
- Competing acceptance variants: 0

No PRD was present. See `requirements.md`.

## Constraints

- Total constraints: 8
- api-contract: 1
- schema: 1
- nfr: 2
- protocol: 4

See `constraints.md`.

## Context

- Context topics: 4
- Current ceramic-watermark operations
- Mini Program, validation, and HTTPS handoff
- Natural-image 512-bit watermark proof of concept
- Real-ceramic 01-18 local adaptation evidence

See `context.md`.

## Conflicts

- Blockers: 0
- Competing variants: 0
- Auto-resolved: 1

The auto-resolution follows the explicit authoritative 2026-08-15 current overrides for the temporary tunnel script SHA-256, which take priority over default document-type precedence. The current value is `48a081d0d744b35adade59f149fda900a18d603214b2ec4ce7c11329da953847`; `48894767e9985d0a6dbcf24b8871f1489cae5f5603e46ab9fb8dfc87a124a938` is retained as an older value. See `../INGEST-CONFLICTS.md` for source-attributed detail.

## Intel entry points

- `decisions.md`
- `requirements.md`
- `constraints.md`
- `context.md`
- `SYNTHESIS.md`
