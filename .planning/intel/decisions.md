# Synthesized Decisions

## 57-bit ceramic watermark retained state

source: `57BIT_RETAINED_STATE.md`

status: proposed (the classification marks this ADR as `locked: false`)

decision:

- Run the ECS ceramic decoder with the TrustMark-Q 57-bit 900K parent plus decoder-only real-ceramic adaptation at step 113100, checkpoint SHA-256 `834d33d4666921f1ae6416d5c3a9d08a7ac60dc9dc21f4ce907caa5923e1d6ef`.
- Preserve the step-112500 900K parent, SHA-256 `86cab6a87981c72c225a180201c85cd87773e2daa373ce95f0205545c2aee4b8`, as the immediate rollback without modifying it.
- Decode the 17-digit business identifier as a 57-bit payload protected by CRC-4 and BCH-5 in network mode `0001`; success means exact 57-bit recovery after ECC and CRC validation.
- Keep the existing 57 search candidates and, only after they all fail, run seven centered grayscale scales `1.0/0.92/0.9/0.84/0.8/0.7/0.6`; accept only agreement from at least two candidates, with at most 64 attempts.
- Use `Mini Program -> Cloudflare -> operator PC -> SSH local forward -> ECS loopback decoder` as the default temporary-access topology. The explicit authoritative 2026-08-15 current overrides establish canonical tunnel script SHA-256 `48a081d0d744b35adade59f149fda900a18d603214b2ec4ce7c11329da953847`. The retained-state tunnel subsection's `48894767e9985d0a6dbcf24b8871f1489cae5f5603e46ab9fb8dfc87a124a938` is preserved as an older value in `../INGEST-CONFLICTS.md`.
- Keep training stopped unless explicitly authorized. Any formal ceramic arm and evaluation uses 100,000 samples and server 249 GPUs 4, 5, and 6. Alpha sweeps require an explicit request, and `1.5 cm x 1.5 cm` remains a nominal reference rather than an acceptance constraint.
- Preserve the parent checkpoint, previous Stage 5 and 40-bit rollback checkpoints, API rollback copies, deployment evidence, and retained remote package.

scope:

- TrustMark-Q 57-bit checkpoint
- decoder service
- decoding fallback policy
- Mini Program tunnel
- 57-bit payload protocol
- ceramic experiment contract
- rollback artifacts
