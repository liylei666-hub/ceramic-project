# Synthesized Constraints

## Active decoder deployment identity

source: `deployment_artifacts/README.md`

type: protocol

content:

The active decoder is the 57-bit real-ceramic adaptation at step 113100 with checkpoint SHA-256 `834d33d4666921f1ae6416d5c3a9d08a7ac60dc9dc21f4ce907caa5923e1d6ef`. Its checkpoint path is `/opt/ceramic-watermark/models/checkpoint_decoder_57bit_real18_legacy_pilot3_step600.pt`; the step-112500 900K parent remains the immediate rollback. The active API source SHA-256 is `21531782ffe62dbe183f35452bdbc62c540c43f5f958831c59874b1daa3626cd`.

## 57-bit payload schema

source: `deployment_artifacts/README.md`

type: schema

content:

The request declares `payload_bits=57`. The decoded business identifier is 17 decimal digits composed as `5-digit enterprise + YYMMDD + 6-digit serial`, carried as 57 bits plus CRC-4 and BCH-5 in network mode `0001`. A valid response exposes `business_id`, `enterprise_code`, `date_code`, and `serial_number` only after BCH and CRC validation. A legacy 40-bit image is a negative control and must yield `detected: false`.

## Decoder HTTP contract

source: `deployment_artifacts/README.md`

type: api-contract

content:

The service exposes `GET /healthz` and multipart `POST /decode`. The decode image field is `image`; protected calls carry the configured API token and the exact image SHA-256. Diagnostic responses may expose `decode_stage`, `alignment_fallback_used`, candidate alignment metadata, and the actual attempt count. The protected token must remain outside Mini Program source.

## Bounded fallback and acceptance

source: `deployment_artifacts/README.md`

type: protocol

content:

The current policy preserves the previous 57 candidates and adds seven grayscale centered scales `1.0/0.92/0.9/0.84/0.8/0.7/0.6` only after all prior candidates fail. At least two candidates must recover the same BCH-5- and CRC-4-valid identifier. The total search is capped at 64 attempts; earlier successful stages return immediately.

## Latency and negative-control behavior

source: `deployment_artifacts/README.md`

type: nfr

content:

Typical coarse positives complete in about 0.52-0.60 seconds. Sample 07 and full negatives may take about 9.1 seconds through the grayscale fallback and must remain inside the cloud-function 20-second timeout. Unwatermarked and legacy 40-bit negative controls must remain rejected.

## Temporary Mini Program relay

source: `deployment_artifacts/README.md`

source: `NEW_CHAT_HANDOFF.md` (authoritative current override corroboration)

source: `57BIT_RETAINED_STATE.md` (older tunnel-subsection value retained for provenance)

type: protocol

content:

Temporary access uses `Mini Program -> Cloudflare -> operator PC -> SSH -> ECS decoder`. Start or reuse it with `deployment_artifacts/start-local-decoder-tunnel.ps1`; use `-ForceNewTunnel` only to deliberately replace an invalid or unwanted temporary hostname. The script must verify `/healthz` before returning a decode URL, the operator PC must remain awake and online, and endpoint configuration must not be edited without an explicit request. The explicit authoritative 2026-08-15 current overrides set the synthesized script SHA-256 to `48a081d0d744b35adade59f149fda900a18d603214b2ec4ce7c11329da953847`; `48894767e9985d0a6dbcf24b8871f1489cae5f5603e46ab9fb8dfc87a124a938` is retained only as the older value recorded in the retained-state tunnel subsection.

## Network exposure and production HTTPS

source: `deployment_artifacts/README.md`

type: nfr

content:

The decoder binds to `127.0.0.1:8765`; port 8765 stays closed publicly. Production activation requires a compliant domain and DNS, ICP filing where applicable, public TCP 80/443 only, and Caddy or Nginx reverse proxying HTTPS `/decode` to the loopback service. The HTTPS origin must be added to the Mini Program legal domains before configuring `decodeApiUrl` and verifying on a real phone.

## Rollback and operational evidence

source: `deployment_artifacts/README.md`

type: protocol

content:

Do not delete the 900K parent checkpoint or deployment rollback evidence. Preserve the previous Stage 5 and 40-bit checkpoints, API rollback copies, service configuration, and evidence beneath `/opt/ceramic-watermark/deployments/real18_candidate_20260815-150105`. Operational changes must retain a direct health check and regression path.
