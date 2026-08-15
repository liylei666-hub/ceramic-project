# Project State

> **Operational guardrail**: step 113100 checkpoint SHA-256 `834d33d4666921f1ae6416d5c3a9d08a7ac60dc9dc21f4ce907caa5923e1d6ef` is the accepted active baseline; do not train, replace weights, continue historical experiments, expose 8765, or change the Mini Program endpoint without explicit user authorization.

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-08-15)

**Core value:** 在真实陶瓷/生产手机裁切流程中精确恢复经 BCH-5 + CRC-4 校验的 57-bit 业务标识，同时保留负样本拒绝，并只以独立新实拍盲测衡量泛化。  
**Current focus:** Phase 1 — Preserve the Accepted Operational Baseline

## Current Position

Phase: 1 of 3 (Preserve the Accepted Operational Baseline)  
Plan: 0 of TBD in current phase  
Status: Ready to plan  
Last activity: 2026-08-15 — Ingested operational intel converted into project context, 17 requirements, and a 3-phase roadmap

Progress: [----------] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: none
- Trend: not enough data

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in `PROJECT.md` Key Decisions.

- Current baseline is decoder-only step 113100; step 112500 remains unmodified immediate rollback.
- Canonical temporary tunnel script SHA-256 is `48a081d0d744b35adade59f149fda900a18d603214b2ec4ce7c11329da953847`; the `488947…` value is historical only.
- Generalization must be measured on independent new real-phone captures; 18/18 is adaptation-set evidence only.
- Compliant HTTPS and Mini Program endpoint activation occur only after blind validation and explicit endpoint-change authorization.

### Pending Todos

None yet.

### Blockers/Concerns

- No independent new printed/fired blind set is recorded yet; Phase 2 needs samples that did not participate in adaptation or model selection.
- No compliant production domain/HTTPS origin is configured, Caddy is not installed, and ICP may be required; these belong only to Phase 3.
- The Mini Program `decodeApiUrl` is currently empty and must not be changed without explicit user authorization.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Model development | Training, fine-tuning, alpha sweeps, weight replacement, historical experiment continuation | Out of scope pending explicit authorization | Project initialization |
| Separate project | Natural-image 512-bit watermark PoC | Out of scope | Project initialization |

## Session Continuity

Last session: 2026-08-15  
Stopped at: Roadmap initialized; Phase 1 is ready for planning  
Resume file: None
