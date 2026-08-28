# Ceramic watermark project handoff

Updated: 2026-08-17 CST

## Current operational override (authoritative, 2026-08-17)

- Server-level GPU constraint: GPU6 is faulty and must not be allocated to any
  future experiment. Treat GPU6 as unavailable until a separate hardware/
  driver-recovery authorization is given. Do not infer availability from
  `nvidia-smi`; new CUDA initialization fails on GPU0-4 and GPU7 as well while
  GPU5 production remains healthy.
- The Mini Program decoder runs on server 249 GPU5 at `127.0.0.1:28765` from
  `/data0/liyanlei/ceramic_watermark/services/decoder_gpu5_real18_locator5_rotation_20260817`.
- Step 113100 is the current best and only checkpoint considered for operation.
  Checkpoint SHA-256:
  `834d33d4666921f1ae6416d5c3a9d08a7ac60dc9dc21f4ce907caa5923e1d6ef`.
  Step 112500/900K is historical only and is no longer a candidate or rollback.
- Active 249 API SHA-256:
  `3392cdf4175c3c43cc41b3f587d9c235acc838a91277aa44a933ad016aabb55b`.
- Canonical local source and GPU5 operational scripts are archived in
  `deployment_artifacts/locator5_rotation_gpu5/`.
- Stage one is unchanged: locate the complete outer contour and try three
  detector-relative crops (`0.84 colour`, `0.88 grayscale`, `0.92 colour`).
  Successful requests stop after three attempts.
- Only after all three direct candidates fail, the API locates the central
  white square, estimates a four-corner homography, and tries 12 bounded
  perspective-rectified candidates. If those also fail, it tries the same 12
  candidates at `90/180/270` degrees (36 rotation candidates). Both fallback
  stages require at least two BCH-5- and CRC-4-valid candidates to agree.
  Maximum attempts are 51.
- GPU5 shadow and production both passed physical crops 18/18,
  synthetic perspective cases 54/54 (26 perspective recoveries), arbitrary
  rotation cases 180/180 (132 rotation recoveries), combined perspective plus
  rotation cases 36/36 (all 36 rotation recoveries), two board photos 2/2,
  and both negative controls. No wrong valid identifier occurred.
- Warm direct cases remain about 35-48 ms. A full 51-attempt negative completed
  in about 119 ms. A blank image returns undetected with zero attempts.
- Immediate rollback is the previous GPU7 locator5 service at
  `/data0/liyanlei/ceramic_watermark/services/decoder_gpu7_real18_locator5_rotation_20260816`;
  it uses the same checkpoint and API. Locator4 on GPU7 remains the secondary
  rollback; neither rollback uses 900K.
- The ECS retains step 113100 with the older 64-candidate API as a separate
  historical deployment, but it is not the current Mini Program route.
- Canonical 249 GPU5 temporary tunnel script SHA-256:
  `eff181e4580800dcb128b487f62f31ebf8e9afdc1ee516930dfe3e8443248b37`.
- The launcher now starts an SSH-only watchdog from
  `deployment_artifacts/watch-local-249-gpu5-ssh-forward.ps1` (SHA-256
  `7f40b2d992edaefe8aa99107d30dddaf13f7ae5ceb12880e49d51dc3f7c34e99`).
  It restores the local `18766 -> 249:28765` forward after a transient Wi-Fi
  or transport reset without restarting cloudflared or changing the hostname.
- Temporary access uses
  `Mini Program -> Cloudflare -> local PC -> SSH -> 249 GPU5 decoder`.
- A 2026-08-16 independent GPU6 evaluation of six failed user samples did not
  alter the operational checkpoint or service. Two low-resolution adaptation
  branches were rejected because neither recovered failures 01-03 and the
  stronger branch regressed the original physical set. A bounded six-candidate
  issued-ID catalog fallback recovered all six inputs offline while rejecting
  the retained unwatermarked and blank controls. It has not been integrated,
  fully regressed, or deployed. See
  `comparison_exports/failure_samples_20260816/RESULTS.md`.
- The user later authorized training on the original failed photos and supplied
  ten new images as an untouched blind set. A BatchNorm-frozen auxiliary
  candidate recovered the targeted old failure but regressed three historical
  rotation cases, so it was rejected as a replacement. A fixed parent-first
  offline cascade preserved the old model and detected 5/10 blind inputs versus
  4/10 for the parent alone. This one-image gain is insufficient for deployment.
  The ten blind images must not be reused for selecting the completed round5
  candidate. Evidence: `comparison_exports/failure_samples_20260816/blind_test10/README.md`.
- A 2026-08-16 payload-generalization audit corrected an invalid earlier P19/P20
  comparison: the files used then were old 40-bit images mislabeled with 57-bit
  targets. With the correct 57-bit P01-P20 K3/K5 files, step 113100 scored
  40/40. A fresh set of 20 previously unseen identifiers was then encoded at
  K3/K5 and decoded through the locator5 API for another 40/40, with zero wrong
  valid identifiers. The decoder is therefore not restricted to the 18 adapted
  IDs. The audit also found that the 600-step adaptation used the old 40-bit
  P01-P18 files as mislabeled 57-bit replay, which weakens training provenance
  but did not remove clean arbitrary-payload capability. No weight or service
  was changed. See `comparison_exports/payload_generalization_audit_20260816/README.md`.
- The user then authorized deletion and corrective retraining. The obsolete
  local and 249 K1-K5 40-bit replay PNGs, CSV, and previews were deleted; old
  checkpoints and summary evidence were retained. A fail-closed 60-pair
  P01-P20 K1/K3/K5 57-bit replay set was rebuilt. Two clean-from-900K seeds,
  one conservative step113100 BN-frozen failure-photo adaptation, whole-model
  interpolation, and 64 layerwise interpolation arms were tested on GPU6.
  Every single-weight candidate regressed at least one retained geometry case;
  the best conservative branch recovered failure06 but scored rotation
  178/180. All candidates were rejected, the blind10 set remained unused, and
  GPU7 production stayed on the exact step 113100/API hashes above. Evidence:
  `comparison_exports/correct57_replay_retrain_20260816/README.md`.
- On 2026-08-17, a new company print batch was generated with the frozen
  official TrustMark-Q encoder on idle GPU4: 20 new 17-digit identifiers, each
  embedded once at K3 and once at K5 (40 PNGs total). The identifiers have no
  overlap with either the original P01-P20 identifiers or the previous fresh
  20-identifier audit set. All 40 saved 512x512 RGB PNGs passed the exact
  step-113100 locator5 decode path (40/40, zero wrong valid identifiers), and
  local transfer hashes and dimensions were rechecked. No training, model, API,
  or production-service change occurred. User-facing folder and ZIP:
  `C:\Users\liylei\Desktop\陶瓷水印_公司新样本20组_K3_K5_20260817` and the
  same path with `.zip`; ZIP SHA-256 is
  `b19b7b5ec37d204fb2d719cb79d42655b8079fd78bc91b414e528b208d5e5792`.

Everything below is historical where inconsistent with this override,
`57BIT_RETAINED_STATE.md`, or `deployment_artifacts/README.md`.

## Previous 2026-08-13 operational override (superseded where inconsistent)

- The online decoder is now the 57-bit 900K checkpoint at step 112500, SHA-256
  `86cab6a87981c72c225a180201c85cd87773e2daa373ce95f0205545c2aee4b8`.
- The active API uses the bounded three-stage fallback documented in
  `deployment_artifacts/README.md`. Its source SHA-256 is
  `3030cac60475d1d2c909f591b258200efb3ce5a9d3f14efd629cd4bc1511638e`.
  The original five-crop stage stays first; the 14-candidate fine stage runs
  only after failure and requires agreement from at least two candidates.
- Only after both existing stages fail, a final contrast stage tests factors
  `1.25/1.5` over the same 19 geometries (38 candidates) and also requires
  agreement from at least two candidates. Existing successful requests retain
  their original result, stage, attempt count, and latency class.
- Deployment regressions on the two-core ECS were about 0.63 seconds for the
  coarse positive, 2.38-2.39 seconds for both real-photo inputs through fine
  alignment, and 8.43 seconds for a full negative after all 57 attempts. The
  negative remained undetected. Evidence is at
  `/opt/ceramic-watermark/deployments/contrast_fallback_20260813-112316`.
- The 2026-08-07 real-photo regression recovers `08022061102620554` in about
  2.47 seconds through the fine stage. Deployment evidence is at
  `/opt/ceramic-watermark/deployments/alignment_fallback_20260807-151624`.
- Temporary Mini Program URLs must default to the operator-PC relay topology:
  `Mini Program -> Cloudflare -> local PC -> SSH -> ECS decoder`.
- Run
  `powershell -ExecutionPolicy Bypass -File .\deployment_artifacts\start-local-decoder-tunnel.ps1`
  from the project root. Use `-ForceNewTunnel` only when a new hostname is
  requested or the current hostname is invalid.
- The script verifies `/healthz` against the exact 900K model and SHA-256 before
  returning the complete `/decode` URL.
- The script includes an authoritative-DNS plus `curl --resolve` fallback for
  newly-created Quick Tunnel hostnames when the local resolver temporarily
  caches `NXDOMAIN`. Current local script SHA-256:
  `48894767e9985d0a6dbcf24b8871f1489cae5f5603e46ab9fb8dfc87a124a938`.
- Do not silently switch to ECS-direct Cloudflare or another tunnel provider.
  Those are explicit fallbacks only.
- Do not modify the Mini Program or cloud-function address unless the user
  explicitly asks. The operator PC must remain awake and online.
- `57BIT_RETAINED_STATE.md` and `deployment_artifacts/README.md` supersede older
  checkpoint and tunnel statements later in this historical handoff.

## Objective

Embed and recover business information from the single ceramic logo carrier.
Online production now uses the 57-bit protocol and the 900K checkpoint. It
packs a 17-digit `5-digit enterprise + YYMMDD + 6-digit serial` identifier into
57 payload bits. Users photograph the printed ceramic logo with a phone and
submit the cropped logo for decoding. The primary metric is exact payload
recovery after ECC and integrity validation, not average per-bit accuracy.

## Historical Stage 5 baseline (superseded by the 900K operational override)

- Packet: 57-bit business payload + CRC-4 in the 61 BCH-5 data positions,
  encoded to 96 protected bits plus mode bits `0001` for a 100-bit network
  codeword.
- Stage 5 step 69750 is the retained previous-work rollback checkpoint, not the
  current production checkpoint.
- Checkpoint SHA-256:
  `40aef1d2ef4f1de639074b29e43c5209a5dd4aaedd7a11de01f3698e1b9d474a`.
- Its paired 100,000-sample result is Clean 100.000%, Medium-T 99.421%, and
  Strong-T 80.026%, with zero wrong CRC-valid payloads.
- These metrics used the historical `print_p=0.45` and
  `screen_moire_p=0.70` augmentation and are not results for the new
  `0.90/0.40` configuration.
- The 57-bit task is a new business scene and does not need 40-bit
  compatibility.
- Alpha is only a parameter experiment and is out of scope until the user
  explicitly asks for an alpha test.
- `1.5 cm x 1.5 cm` is only an approximate target size. It is not a hard
  dataset, printing, or acceptance constraint; record actual sample sizes.
- All other previous 57-bit checkpoints, Stage 1-4/6 branches, smoke tests,
  DPI/resizer/retention sweeps, and 500-step alpha pilots were deleted.
- Canonical retained package:
  `/data0/liyanlei/ceramic_watermark/experiments/trustmark_q_production4096_20260720/experiments_57bit_20260803/retained_stage5_step69750`.
- Local retained-state record: `57BIT_RETAINED_STATE.md`.

## Selected model

- Method: TrustMark-Q master-512 target adaptation.
- Selected run: seed `512409603`, checkpoint step 8000.
- The official pretrained encoder is frozen; the decoder is target-adapted.
- The 40-bit payload is internally BCH-SUPER encoded into a 100-bit network
  codeword. The API returns the decoded original 40-bit payload.
- Clean exact40: 100%.
- Medium composite T exact40: 100%.
- Strong composite T including reduced print simulation: 95.51%, 92.19%, and
  94.34% over three independent 512-sample draws; pooled 94.01%.
- PSNR: 40.13 dB; SSIM: 0.99268.
- Deployed to the ECS decoder on 2026-07-20 after direct P01, photographed P10,
  and unwatermarked negative-control regression checks.
- Checkpoint SHA-256:
  `de852d24ea72486b1a8bec198d24c8962d557b8c6967318b799d20650bbfdf38`.

Local results:

- `comparison_exports/master512_print_finetune_20260720/summary.json`
- `comparison_exports/master512_print_finetune_20260720/result_seed512409603.json`
- `comparison_exports/master512_print_finetune_20260720/checkpoint_best_seed512409603.pt`

The mentor-provided PDF-compatible Illustrator source has been preserved and
exported as a vector-derived target-logo candidate under
`C:\Users\liylei\Documents\陶瓷水印\assets\target_logo\jingdezhen_standard_v1`.
The training derivative is `derived/jingdezhen_standard_logo_512.png`; it is a
512x512 RGB PNG and is the selected production carrier. The previous seed-4
checkpoint is retained only as a rollback baseline.

Do not select the old Hidden, 256-finetuned TrustMark, or rejected quality-first
experiments for deployment.

## Historical 4096 resolution-transfer experiment (superseded)

This experiment is retained only as resolution-transfer evidence. On
2026-07-20 the user rejected 4096 production embedding because the ceramic
printing/firing process does not preserve that many addressable dots. Do not
generate or send new 4096 watermarked production files.

The historical path was:

`4096 source -> 256 frozen encoder -> 4096 residual merge and 8-bit save ->`
`ceramic printing/firing -> high-resolution camera geometry -> 512 or 1024`
`phone export -> 245 decoder`.

The optional printing stage runs before camera geometry and phone resizing. It
is intentionally limited to the dominant effects: pigment blur/spread, dot gain
and firing colour/gamma drift. Camera lighting, sensor noise, motion blur and
JPEG effects remain later stages. Artificial downscale-then-upscale augmentation
and the duplicate post-resize `bleed` effect have been removed.

Implementation and tests:

- `trustmark_target_finetune_production.py`
- `C:\Users\liylei\Documents\陶瓷水印\src\ceramic_watermark\augment.py`
- `C:\Users\liylei\Documents\陶瓷水印\tests\test_training_components.py`
- Nine local training-component tests pass.

The isolated 249 staging root is
`/data0/liyanlei/ceramic_watermark/experiments/trustmark_q_production4096_20260720`.
A one-step 4096-to-512 print-pipeline preflight completed on GPU 0 under
`runs/preflight_print4096_capture512_seed40960002`; peak CUDA allocation was
19019 MiB. The single clean sample decoded exactly, while medium/strong samples
did not decode with the unadapted official decoder. This is only a pipeline
check, not a robustness result. No long training run has started.

The paired zero-shot resolution transfer test completed on 249 with three
independent 512-payload repeats (seeds `40962001`, `40962002`, and `40962003`).
Each repeat used the same payloads and identical T random draws across three
arms: old carrier embedded at 512, new carrier embedded at 512, and new carrier
embedded at 4096 then resized once to 512. Printing simulation was disabled so
that `new4096 - new512` isolated embedding resolution. The original T was
retained except for the explicitly removed downscale-then-upscale transform.

- Clean and Medium-T exact40: 100% for every arm in every repeat.
- Strong-T old-carrier 512: 92.38%, 94.34%, 96.09%; pooled 94.27%.
- Strong-T new-carrier 512: 89.84%, 90.63%, 93.16%; pooled 91.21%.
- Strong-T new-carrier 4096-to-512: 89.84%, 90.23%, 93.75%; pooled 91.28%.
- Pooled pure-resolution delta (`new4096 - new512`): +0.07 percentage points.
- Pooled carrier-change delta (`new512 - old512`): -3.06 percentage points.

The zero-shot resolution gate therefore passes: 4096 embedding does not require
resolution-specific decoder adaptation. No pilot or long decoder training was
started. The remaining Strong-T gap belongs to the new carrier. Any future
adaptation should be justified as new-carrier adaptation and gated by real
phone-photo results and the production acceptance threshold.

The production decision is now the simpler 512 path:

`official vector source -> render once at 512 -> frozen 256 encoder ->`
`residual merge and 8-bit save at 512 -> ceramic printing/firing ->`
`mini-program 512 crop/export -> 245 decoder`.

Formal local result:

- `comparison_exports/resolution_transfer_summary.json`
- `comparison_exports/resolution_transfer_seed40962001.json`
- `comparison_exports/resolution_transfer_seed40962002.json`
- `comparison_exports/resolution_transfer_seed40962003.json`

## Master-512 decoder adaptation and physical print trial

Three decoder-only adaptations completed on 249 GPUs 0-2 using the official
vector source rendered at 512. The official TrustMark-Q encoder remained
frozen. Training used 8,000 steps, batch 8, AdamW `lr=5e-6`, and the reduced
print simulation plus camera T. Each checkpoint was independently evaluated on
three shared 512-payload/T seeds, for 1,536 payloads per checkpoint.

- Seed `512409601`: Clean 100%, Medium-T 100%, Strong-T 93.82% pooled.
- Seed `512409602`: Clean 100%, Medium-T 100%, Strong-T 92.45% pooled.
- Seed `512409603`: Clean 100%, Medium-T 100%, Strong-T 94.01% pooled.
- Selected print-trial candidate: seed `512409603`, step 8000.
- Checkpoint SHA-256:
  `de852d24ea72486b1a8bec198d24c8962d557b8c6967318b799d20650bbfdf38`.

The Strong-T protocol here includes the reduced print simulation and therefore
must not be directly subtracted from the earlier no-print zero-shot resolution
result. The selected checkpoint replaced the online decoder on 2026-07-20
after direct P01, photographed P10, and unwatermarked negative-control
regression checks.

The initial 4096 manufacturer set was superseded and renamed locally to
`旧版_不要打印_4096嵌入_陶瓷水印20张_20260720`. It must not be sent for printing.

The replacement manufacturer set contains twenty unique 40-bit payloads
embedded directly at 512 and saved as 512x512 8-bit RGB PNGs. All 20 saved PNGs
passed official clean exact40 verification; their dimensions, uniqueness, and
SHA-256 hashes were rechecked locally. The authoritative user-facing artifacts
are:

- Folder:
  `C:\Users\liylei\Desktop\陶瓷水印_厂家打印20张_512嵌入_替换版_20260720`
- ZIP:
  `C:\Users\liylei\Desktop\陶瓷水印_厂家打印20张_512嵌入_替换版_20260720.zip`
- ZIP SHA-256:
  `01cdb302c1e8afcf277630becdc0c6a6a427c900fe13a843e817f473408c3ca2`

Formal fine-tuning results:

- `comparison_exports/master512_print_finetune_20260720/summary.json`
- `comparison_exports/master512_print_finetune_20260720/result_seed512409601.json`
- `comparison_exports/master512_print_finetune_20260720/result_seed512409602.json`
- `comparison_exports/master512_print_finetune_20260720/result_seed512409603.json`
- `comparison_exports/master512_print_finetune_20260720/checkpoint_best_seed512409603.pt`

## ECS deployment

- Instance: `i-7xv84dndpegwmn0mqdw6`
- Public IP: `8.138.42.34`
- OS: Ubuntu 22.04 LTS, 2 CPU cores, about 7.2 GB RAM.
- SSH user: `root`
- Local private key: `C:\Users\liylei\.ssh\aliyun_ceramic_temp_rsa`
- Service: `ceramic-decoder.service`, enabled and active.
- Service user: `ceramic-api`.
- API currently binds only to `127.0.0.1:8765`; port 8765 is not public.
- Model: `trustmark-q-master512-resume-seed512419603-step15750`.
- Model checkpoint SHA-256:
  `01abc4c2220c993b35f0ba82cb38dbfb9e2a559cd5d825bb5d1801f5de95c61e`.
- P01 and a photographed mini-program P01 return their exact expected 40-bit payloads; the
  unwatermarked master returns `detected=false` and `ecc_valid=false`.
- CPU processing time is about 0.51-0.57 seconds per image.

Server paths:

- Root: `/opt/ceramic-watermark`
- Checkpoint:
  `/opt/ceramic-watermark/models/checkpoint_decoder_master512_resume_seed512419603_step15750.pt`
- Previous step-8000 checkpoint retained for rollback:
  `/opt/ceramic-watermark/models/checkpoint_decoder_master512_seed512409603_step8000.pt`
- API: `/opt/ceramic-watermark/services/decoder_api`
- Environment: `/etc/ceramic-watermark/decoder.env`
- Unit: `/etc/systemd/system/ceramic-decoder.service`

Local deployment files are under `deployment_artifacts/`.

## API contract

- `GET /healthz`
- `POST /decode` as multipart form data.
- Image field: `image`.
- Form field: `payload_bits=40`.
- Authoritative response field: `payload_bits`, a 40-character binary string.
- `product_code` is only the same value rendered as 10 hexadecimal digits.
- `product_id` is only the same value rendered as a decimal integer.
- The internal 100-bit BCH codeword is not returned.

## WeChat mini program

Project path:

`C:\Users\liylei\Documents\陶瓷水印\apps\wechat-miniapp`

The capture page now maps the visible guide box to camera-image coordinates,
crops only the guide-box content, and exports a 512x512 PNG. Preview,
persistence, and upload all use the cropped file. Album images use a centered
square crop.

Upload is already implemented with `wx.uploadFile`. The endpoint is configured
in `app.js` through `globalData.decodeApiUrl`, which is currently empty.

The client now treats `payload_bits` as authoritative: it requires exactly 40
binary characters and derives the 10-digit hexadecimal `productCode` and
decimal `productId` locally instead of trusting the server's convenience
fields.

## Current next step

1. Keep synthetic training stopped until the 57-bit specification is approved.
2. Build a labeled real-world validation set from printed and fired ceramic
   pieces photographed through the production phone/miniprogram crop flow,
   recording the actual printed dimensions rather than enforcing exactly
   `1.5 cm x 1.5 cm`.
3. Define the 57-bit acceptance threshold before testing to avoid selecting on
   the validation set.
4. Treat 57-bit as an independent business scene; do not require 40-bit
   compatibility in its training or acceptance criteria.
5. Any approved formal experiment uses 100,000 training samples, an independent
   100,000-sample evaluation, and only server 249 GPUs 4, 5, and 6 (operator
   update: 2026-08-12).
6. Do not schedule or run alpha experiments unless the user explicitly asks.

## Pending HTTPS deployment

To connect a preview or production mini program:

1. Prepare a compliant domain and point it to `8.138.42.34`.
2. Complete ICP filing when required for the mainland China ECS.
3. Open only TCP 80/443 in the ECS security group; keep 8765 closed.
4. Install Caddy or Nginx and proxy HTTPS `/decode` to
   `http://127.0.0.1:8765/decode`.
5. Add the HTTPS origin to the mini program's `uploadFile` legal domains.
6. Set `decodeApiUrl` to `https://the-domain.example/decode`.
7. Verify the crop and upload flow on a real phone.

No domain or public HTTPS endpoint has been configured yet.

A restricted Caddy reverse-proxy template and activation instructions are
prepared under `deployment_artifacts/Caddyfile.example` and
`deployment_artifacts/README.md`. Caddy is not installed on the ECS yet.

The repository-level `C:\Users\liylei\Documents\陶瓷水印\AGENTS.md` has been
updated to match the selected TrustMark-Q deployment baseline, the external
40-bit payload contract, and the approved internal 100-bit BCH-SUPER codeword.
