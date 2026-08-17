# 57-bit Retained State

Updated: 2026-08-17 CST

## Current deployed checkpoint override (authoritative, 2026-08-17)

- Model: TrustMark-Q 57-bit 900K parent plus decoder-only real-ceramic adaptation
- Step: 113100 (parent step 112500 + 600 local adaptation steps)
- SHA-256: `834d33d4666921f1ae6416d5c3a9d08a7ac60dc9dc21f4ce907caa5923e1d6ef`
- Step 113100 is the current best and only operational checkpoint. The 900K
  parent is historical only and is no longer considered for selection or
  rollback.
- Local package: `comparison_exports/real_ceramic_18_local_adapt_20260815`
- ECS path:
  `/opt/ceramic-watermark/models/checkpoint_decoder_57bit_real18_legacy_pilot3_step600.pt`
- Active 249 API SHA-256:
  `3392cdf4175c3c43cc41b3f587d9c235acc838a91277aa44a933ad016aabb55b`
- Active 249 policy: first try the unchanged three detector-relative variants
  (`0.84 colour`, `0.88 grayscale`, `0.92 colour`). Only after all three fail,
  use the central white square to estimate a homography and try 12 bounded
  perspective candidates. If those fail, try all 12 at `90/180/270` degrees.
  Both fallback stages require at least two BCH-5- and CRC-4-valid candidates
  to agree; the maximum is 51 attempts.
- ECS deployment verification: physical crops 01-18 = 18/18; old real-photo
  controls = 2/2; negative controls = 2/2. Evidence and rollback:
  `/opt/ceramic-watermark/deployments/real18_candidate_20260815-150105`.
- No training is currently running. Historical artifacts remain unchanged.
- Server 249 GPU5 production port `127.0.0.1:28765` runs from
  `/data0/liyanlei/ceramic_watermark/services/decoder_gpu5_real18_locator5_rotation_20260817`.
  The immediate rollback is GPU7 locator5 with the same step-113100 checkpoint
  and API; GPU7 locator4 is the secondary rollback.
- GPU5 shadow and production passed physical crops 18/18, perspective
  cases 54/54, rotation cases 180/180, combined perspective-rotation cases
  36/36, board photos 2/2, and two negative controls. Direct cases remain
  three attempts; a full 51-attempt negative completed in about 121 ms.
- Canonical 249 GPU5 tunnel script SHA-256:
  `24a998c3314b1d1ec543d89f66c443aabe6f281ab3940b09fbbc74d3a1948b9b`.
- The 2026-08-16 failure-sample work remains offline on GPU6. Both decoder
  fine-tuning candidates were rejected and must not replace step 113100. A
  six-candidate issued-ID catalog fallback passed the six supplied inputs and
  the two retained negatives in isolation, but is not part of the active API
  and has not completed the full regression gate. Evidence is recorded in
  `comparison_exports/failure_samples_20260816/RESULTS.md`.
- A later user-authorized actual-photo adaptation also remains offline. Its
  BN-frozen round5 candidate recovered the targeted old failure but scored
  rotation 178/180 and perspective-rotation 35/36, so it must not replace the
  formal step113100 checkpoint. On a ten-image untouched blind set, a fixed
  parent-first cascade improved detections only from 4/10 to 5/10 and was not
  deployed. See `comparison_exports/failure_samples_20260816/blind_test10/README.md`.
- Corrected payload-generalization testing on 2026-08-16 used genuine 57-bit
  P01-P20 K3/K5 files and scored 40/40 with step 113100. Twenty entirely new
  identifiers were also embedded at K3/K5 and decoded through locator5 for
  40/40, with zero wrong valid identifiers. Step 113100 is not limited to the
  18 physical adaptation IDs. The audit found that the adaptation script's
  replay and old P19/P20 holdout pointed at a 40-bit image set while assigning
  57-bit labels; that comparison was invalid and the replay provenance is
  defective. No retraining, checkpoint replacement, or deployment occurred.
  Evidence: `comparison_exports/payload_generalization_audit_20260816/README.md`.
- After explicit user authorization, the obsolete local and remote 40-bit
  replay PNG/CSV/preview data were deleted and replaced by a hash-verified
  60-pair 57-bit P01-P20 K1/K3/K5 replay set. Corrective GPU6 retraining from
  900K and from step113100, plus whole/layerwise interpolation, found no single
  checkpoint that preserved the complete historical gate while improving
  failure06. The strongest improving branch recovered failure06 but regressed
  rotation to 178/180, so it and all other candidates were rejected. Step
  113100 remains active and unchanged. See
  `comparison_exports/correct57_replay_retrain_20260816/README.md`.

## Previous deployed 900K parent checkpoint (archival history only)

- Model: TrustMark-Q 57-bit 900K
- Step: 112500
- SHA-256: `86cab6a87981c72c225a180201c85cd87773e2daa373ce95f0205545c2aee4b8`
- 249 path: `/data0/liyanlei/ceramic_watermark/experiments/trustmark_q_production4096_20260720/experiments_57bit_lowk_plateau_20260805/round_06/seed_2708057603/training/checkpoint_final.pt`
- ECS path: `/opt/ceramic-watermark/models/checkpoint_decoder_57bit_900k_step112500.pt`
- Historical deployment: it entered the ECS decoder service on 2026-08-06;
  the bounded three-stage fallback followed on 2026-08-13.
- Active protocol: 57-bit payload + CRC-4 + BCH-5, mode `0001`
- Active API source SHA-256:
  `3030cac60475d1d2c909f591b258200efb3ce5a9d3f14efd629cd4bc1511638e`

## Previous ECS decoding fallback policy (not active on 249)

- Stage one is unchanged: five centered scales `1.0/0.9/0.8/0.7/0.6`.
- Stage two runs only after stage-one failure and adds 14 candidates covering
  scale `0.96` with centered or one-percent cardinal shifts and centered scales
  `0.94/0.98`, under bilinear and bicubic resampling.
- Stage-two acceptance requires at least two candidates to return the same
  BCH-5- and CRC-4-valid identifier.
- Stage three runs only after both earlier stages fail. It applies bounded
  contrast factors `1.25` and `1.5` to the same five coarse and 14 fine
  geometries, for 38 additional candidates. Acceptance again requires at
  least two candidates to recover the same valid identifier.
- Existing successful inputs do not enter stage three. Post-deployment checks
  retained 5 attempts for the coarse positive and 19 attempts for both
  real-photo inputs. The unwatermarked negative entered stage three, remained
  undetected after 57 attempts, and completed in about 8.43 seconds.
- Contrast-stage deployment evidence:
  `/opt/ceramic-watermark/deployments/contrast_fallback_20260813-112316`.
- Immediate contrast-stage API rollback:
  `/opt/ceramic-watermark/services/decoder_api/app.py.pre-contrast-20260813-112316`.
- A photographed screenshot crop with SHA-256
  `029d9e78abb6186d77eb60600a78f0c54873029f77cbd513383693aebf3138d9`
  now recovers `08022061102620554` using scale `0.96`, vertical shift `+0.01`,
  with agreement `2/14`.
- Post-deployment ECS timings: 628.1 ms for a stage-one positive; 2350.0 ms
  for a negative after fallback; 2469.5 ms for the real-photo recovery.
- Deployment evidence:
  `/opt/ceramic-watermark/deployments/alignment_fallback_20260807-151624`.
- Immediate API-code rollback:
  `/opt/ceramic-watermark/services/decoder_api/app.py.pre-alignment-20260807-151624`.
- The model file and checkpoint SHA-256 did not change.

## Temporary Mini Program tunnel operation

- Default topology: Mini Program -> Cloudflare -> operator PC -> SSH local
  forward -> server 249 GPU5 loopback decoder.
- Canonical command:
  `powershell -ExecutionPolicy Bypass -File .\deployment_artifacts\start-local-249-gpu5-decoder-tunnel.ps1`
- Use `-ForceNewTunnel` only when a new temporary hostname is requested or the
  current hostname is invalid.
- The script handles the short Cloudflare authoritative-DNS/local-NXDOMAIN
  propagation gap using `curl --resolve`; its current SHA-256 is
  `24a998c3314b1d1ec543d89f66c443aabe6f281ab3940b09fbbc74d3a1948b9b`.
- The script must verify the step-113100 checkpoint SHA-256, locator5 model,
  outer-contour direct stage, inner-square perspective fallback, rotation
  fallback, and exact `3/12/36` candidate counts before returning an address.
- ECS-direct Cloudflare and third-party tunnel providers are non-default
  fallbacks. Do not use them without an explicit request or a confirmed failure
  of the local relay procedure.
- The script does not edit Mini Program or cloud-function configuration. That
  address is changed only when the user explicitly asks.
- The operator PC must remain awake and online while the temporary address is
  in use.

## Previous Stage 5 checkpoint

- Model: TrustMark-Q Stage 5
- Step: 69750
- Training branch: `lr=1e-7`, seed `3708045001`
- SHA-256: `40aef1d2ef4f1de639074b29e43c5209a5dd4aaedd7a11de01f3698e1b9d474a`
- Remote path: `/data0/liyanlei/ceramic_watermark/experiments/trustmark_q_production4096_20260720/experiments_57bit_20260803/retained_stage5_step69750/checkpoint_stage5_step69750.pt`
- Deployment: retained on ECS as the immediate rollback checkpoint
- ECS path: `/opt/ceramic-watermark/models/checkpoint_decoder_57bit_stage5_step69750.pt`
- Previous 40-bit checkpoint remains unchanged on ECS at
  `/opt/ceramic-watermark/models/checkpoint_decoder_master512_weakfocus_step45000.pt`
  with SHA-256
  `26d03a66ba641cec5a3e9a50c9e20e8463ae324923b62b00a507397d02a91970`.

This is the only retained checkpoint produced by the previous 57-bit work.

## Protocol

- Business identifier: 17 decimal digits (`5-digit enterprise + YYMMDD + 6-digit serial`)
- Payload: 57 bits
- Integrity: CRC-4
- ECC: BCH-5
- Network packet: 100 bits, including mode bits `0001`
- Success metric: exact 57-bit recovery after ECC and CRC validation

## Retained evidence

The paired evaluation used 100,000 identifiers per attack condition:

| Attack | Exact 57-bit recovery | False CRC-valid payloads |
|---|---:|---:|
| Clean | 100.000% | 0 |
| Medium-T | 99.421% | 0 |
| Strong-T | 80.026% | 0 |

These numbers used the historical augmentation configuration with
`print_p=0.45` and `screen_moire_p=0.70`. They must not be presented as results
for the new ceramic configuration.

## Current experiment contract

- Physical scene: print and fire the target image on ceramic, photograph it
  with a phone, crop the target, and recover the 57-bit payload.
- The 57-bit task is independent from the 40-bit service.
- Every formal training arm and formal evaluation uses 100,000 samples.
- Server 249 may use only GPUs 4, 5, and 6 (operator update: 2026-08-12).
- New Strong-T configuration: `print_p=0.90`, `screen_moire_p=0.40`.
- Alpha is only a parameter-exploration variable. Do not run an alpha sweep or
  use alpha to select a model unless the user explicitly requests that test.
- `1.5 cm x 1.5 cm` is a nominal physical-size reference, not a hard printing,
  filtering, or acceptance requirement. Record the measured size of each
  physical sample and preserve the square aspect ratio.
- No training is authorized or running.

## Retained remote package

`retained_stage5_step69750` contains:

- the canonical checkpoint and SHA-256 manifest;
- training contract, metrics, log, and step-69750 preview;
- the paired 100,000-sample result and previews;
- codec, training, evaluation, and phone-pilot source files;
- the historical augmentation configuration required to interpret the result.

All other previous 57-bit checkpoints, sweep outputs, smoke tests, Stage 1-4
branches, Stage 6 branches, DPI/resizer/retention experiments, and 500-step
alpha pilot outputs were deleted from server 249.
