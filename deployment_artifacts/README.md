# Ceramic watermark decoder deployment

## Current deployment override (authoritative, 2026-08-17)

- The active Mini Program decoder runs on server 249 GPU5 at
  `127.0.0.1:28765` from
  `/data0/liyanlei/ceramic_watermark/services/decoder_gpu5_real18_locator5_rotation_20260817`.
- Active model: 57-bit real-ceramic decoder adaptation
- Checkpoint step: 113100
- Checkpoint SHA-256:
  `834d33d4666921f1ae6416d5c3a9d08a7ac60dc9dc21f4ce907caa5923e1d6ef`
- Step 113100 is the only operational checkpoint considered. Step 112500/900K
  is retained only as history and is not a candidate or rollback.
- Active 249 API SHA-256:
  `3392cdf4175c3c43cc41b3f587d9c235acc838a91277aa44a933ad016aabb55b`
- Canonical local source and operational scripts are archived under
  `deployment_artifacts/locator5_rotation_gpu5/`; its `decoder_api/app.py` is an
  exact copy of the active 249 API.
- Active policy: first run the unchanged three outer-contour-relative variants.
  If all fail, locate the central white square, estimate a four-corner
  homography, and try 12 bounded perspective candidates. If those fail, try
  the same candidates at `90/180/270` degrees (36 rotation candidates).
  Both fallback stages require agreement from at least two BCH-5- and
  CRC-4-valid candidates. The maximum is 51 attempts.
- GPU5 shadow and production verification both passed physical crops
  18/18, perspective cases 54/54, arbitrary rotation cases 180/180, combined
  perspective-rotation cases 36/36, two board photos 2/2, an unwatermarked
  negative, and a blank-image negative.
- A corrected GPU6 payload-generalization audit additionally passed genuine
  57-bit P01-P20 K3/K5 images 40/40 and 20 freshly encoded, previously unseen
  identifiers at K3/K5 another 40/40 through the locator5 API, with zero wrong
  valid identifiers. This changed neither the checkpoint nor the service. See
  `comparison_exports/payload_generalization_audit_20260816/README.md`.
- Subsequent user-authorized cleanup removed the mislabeled 40-bit replay image
  data and rebuilt a verified 57-bit replay set. Multiple corrective GPU6
  retraining and interpolation candidates were fully gated; none strictly
  exceeded step 113100, so no checkpoint or service change was deployed. See
  `comparison_exports/correct57_replay_retrain_20260816/README.md`.
- Direct cases remain three attempts at about 35-48 ms after warm-up. A full
  51-attempt negative completed in about 119 ms.
- Immediate rollback is GPU7 locator5 under
  `/data0/liyanlei/ceramic_watermark/services/decoder_gpu7_real18_locator5_rotation_20260816`;
  GPU7 locator4 remains the secondary rollback.
- Temporary access remains
  `Mini Program -> Cloudflare -> local PC -> SSH -> 249 GPU5 decoder`.
- Canonical 249 GPU5 tunnel script SHA-256:
  `eff181e4580800dcb128b487f62f31ebf8e9afdc1ee516930dfe3e8443248b37`.
- SSH watchdog SHA-256:
  `7f40b2d992edaefe8aa99107d30dddaf13f7ae5ceb12880e49d51dc3f7c34e99`.
  It recovers the local forward after a transient client-network reset without
  restarting cloudflared or changing the Quick Tunnel hostname.

The older sections below document the parent deployment and prior fallback
history; this override is authoritative where they differ.

## Previous 900K parent deployment (archival history only)

- Host: `8.138.42.34`
- Service: `ceramic-decoder.service`
- API bind address: `127.0.0.1:8765`
- Model: TrustMark-Q 57-bit 900K checkpoint step 112500
- Payload: 57-bit business ID plus CRC-4, encoded as a BCH-5 100-bit codeword
  with mode bits `0001`
- Checkpoint SHA-256:
  `86cab6a87981c72c225a180201c85cd87773e2daa373ce95f0205545c2aee4b8`
- Active API source SHA-256:
  `3030cac60475d1d2c909f591b258200efb3ce5a9d3f14efd629cd4bc1511638e`
- Temporary Mini Program access uses the operator PC as the relay:
  `Mini Program -> Cloudflare -> local PC -> SSH -> ECS decoder`.
- The current ephemeral URL is produced and verified by
  `start-local-decoder-tunnel.ps1`; do not record a temporary hostname here.

The API remains bound to loopback. For the temporary manufacturer demo, the
operator PC first creates an SSH local forward from `127.0.0.1:18765` to the
ECS `127.0.0.1:8765`, then starts a local Cloudflare Quick Tunnel. This is the
default and required temporary-address procedure. `/decode` requires an API
token and an exact image SHA-256; port 8765 stays closed publicly.

## Previous ECS three-stage fallback (not active on 249)

Since 2026-08-07, `/decode` uses a bounded two-stage policy. Stage one keeps
the original five centered crop scales (`1.0`, `0.9`, `0.8`, `0.7`, `0.6`).
If any stage-one candidate passes BCH-5 and CRC-4, the API returns immediately
and does not pay the fallback cost.

Only when stage one finds nothing, stage two tests 14 fine-alignment
candidates: scale `0.96` with centered or one-percent horizontal/vertical
shifts, plus centered scales `0.94` and `0.98`, each with bilinear and bicubic
resampling. A fallback result is accepted only when at least two candidates
recover the same 17-digit identifier. This consensus rule limits the extra
false-accept risk from the CRC-4 search.

The deployment regression measurements on the two-core ECS were:

| Input | Result | Attempts | Processing time |
|---|---|---:|---:|
| Existing positive control | Correct, coarse stage | 5 | 628.1 ms |
| Unwatermarked negative control | Not detected | 19 | 2350.0 ms |
| Real-photo screenshot crop | `08022061102620554`, fine stage | 19 | 2469.5 ms |

The real-photo input SHA-256 was
`029d9e78abb6186d77eb60600a78f0c54873029f77cbd513383693aebf3138d9`.
Its successful alignment was scale `0.96`, horizontal shift `0`, vertical
shift `+0.01`, with agreement from both resampling variants. The 900K model and
checkpoint were not changed. ECS evidence is retained under
`/opt/ceramic-watermark/deployments/alignment_fallback_20260807-151624`;
the immediate code rollback is
`/opt/ceramic-watermark/services/decoder_api/app.py.pre-alignment-20260807-151624`.

`Caddyfile.example` is the deployment-ready reverse-proxy template. Replace
`decode.example.com` with the project's real domain only after its DNS A record
points to `8.138.42.34` and TCP 80/443 are open in the ECS security group.

Since 2026-08-13, a third stage runs only if both stages above fail. It applies
contrast factors `1.25` and `1.5` and reuses the same five coarse crops and 14
fine-alignment candidates, for 38 additional attempts. The result is accepted
only when at least two candidates recover the same BCH-5- and CRC-4-valid
identifier. Existing successful requests therefore keep their original path.

Post-deployment checks retained the existing behavior: the positive completed
in 5 attempts (629.8 ms), and two real-photo inputs completed in 19 attempts
(2382.4 ms and 2392.5 ms). An unwatermarked negative exhausted all 57 attempts
in 8433.2 ms and remained undetected. The cloud-function decoder request
timeout is 20 seconds. Evidence and rollback metadata are under
`/opt/ceramic-watermark/deployments/contrast_fallback_20260813-112316`; the
immediate rollback is
`/opt/ceramic-watermark/services/decoder_api/app.py.pre-contrast-20260813-112316`.

## Server paths

- Application root: `/opt/ceramic-watermark`
- Active decoder checkpoint:
  `/opt/ceramic-watermark/models/checkpoint_decoder_57bit_900k_step112500.pt`
- Previous 57-bit step-69750 rollback checkpoint:
  `/opt/ceramic-watermark/models/checkpoint_decoder_57bit_stage5_step69750.pt`
- Preserved 40-bit checkpoint:
  `/opt/ceramic-watermark/models/checkpoint_decoder_master512_weakfocus_step45000.pt`
  (SHA-256
  `26d03a66ba641cec5a3e9a50c9e20e8463ae324923b62b00a507397d02a91970`)
- Environment: `/etc/ceramic-watermark/decoder.env`
- Systemd unit: `/etc/systemd/system/ceramic-decoder.service`
- Protected token: `/etc/ceramic-watermark/decoder.token`
- The ECS-side `ceramic-cloudflared-quick.service` is retained only as an
  explicitly requested fallback. It is not the default address generator.

## Operations

```bash
systemctl status ceramic-decoder.service
systemctl restart ceramic-decoder.service
journalctl -u ceramic-decoder.service -n 100 --no-pager
curl -fsS http://127.0.0.1:8765/healthz
```

Local decode smoke test on the server:

```bash
TOKEN="$(cat /etc/ceramic-watermark/decoder.token)"
IMAGE=/opt/ceramic-watermark/samples/step69750_57bit_photo_test.jpg
IMAGE_SHA256="$(sha256sum "$IMAGE" | awk '{print $1}')"
curl -fsS \
  -H "X-Ceramic-Token: ${TOKEN}" \
  -H "X-Image-SHA256: ${IMAGE_SHA256}" \
  -F image=@"$IMAGE" \
  -F payload_bits=57 \
  http://127.0.0.1:8765/decode
```

The active service returns `business_id`, `enterprise_code`, `date_code`, and
`serial_number` only after BCH mode `0001` and CRC-4 both validate. The previous
40-bit image is now a negative control and must return `detected: false`.
Responses expose `decode_stage`, `localization_found`, `localization_bbox`,
the selected localization padding/mode, and the actual `attempts` count.

## Temporary demo tunnel

The standard operation is run from the project root on the operator PC:

```powershell
powershell -ExecutionPolicy Bypass -File .\deployment_artifacts\start-local-249-gpu5-decoder-tunnel.ps1
```

The script performs all of the following before returning an address:

1. creates or reuses the local SSH forward to the 249 GPU5 loopback decoder;
2. creates or reuses the local Cloudflare Quick Tunnel;
3. verifies `/healthz` reports step 113100, the exact checkpoint SHA-256, and
   the `3/12/36` locator5 perspective-plus-rotation policy;
4. starts one hidden SSH-only watchdog that checks the exact local health
   contract every 10 seconds and recreates the SSH forward after failure;
5. prints both `base_url` and the complete `decode_url`.

The watchdog is `watch-local-249-gpu5-ssh-forward.ps1`. It may stop only an
`ssh.exe` process that owns local port 18766. It does not stop or restart
cloudflared, so a short Wi-Fi interruption can recover on the same public
hostname. Recovery attempts use the existing SSH key and exponential backoff;
runtime evidence is appended to `tmp/ssh-249-gpu5-watchdog.log`.

For a newly created Quick Tunnel, the operator PC's upstream DNS can briefly
cache `NXDOMAIN` even after Cloudflare's authoritative DNS has published the
hostname. The script handles this narrow case by resolving against the zone's
authoritative name servers and verifying `/healthz` with TLS SNI via
`curl --resolve`; it still refuses to return an address unless the exact
locator5 model, checkpoint, and localization policy match.

To deliberately replace the current temporary hostname, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\deployment_artifacts\start-local-249-gpu5-decoder-tunnel.ps1 -ForceNewTunnel
```

Copy the returned `decode_url` into the cloud function's `DECODER_URL`. The
protected token must remain in `DECODER_TOKEN`; never place it in Mini Program
source. Do not change the Mini Program or cloud-function address automatically
unless the user explicitly asks for that change.

For automatic Quick Tunnel rotation, the launcher also publishes the verified
state atomically to `tmp/current-gpu5-decode-url.json`. A cloud function can
read the same JSON contract through a **fixed HTTPS configuration URL** and
then forward to its current `decode_url`; see
`cloud-function-endpoint-adapter.example.js` and
`current-gpu5-decode-url.schema.json`. The fixed configuration URL must be
hosted outside the Quick Tunnel, for example in CloudBase, on the company's
HTTPS domain, or behind a Cloudflare Named Tunnel. Hosting the JSON on the
rotating Quick Tunnel does not solve endpoint discovery. Configure the cloud
function's `DECODER_CONFIG_URL` with that stable URL and keep `DECODER_TOKEN`
server-side.

The operator PC must stay powered on, awake, and connected to the network. If
the PC sleeps, shuts down, changes networks, or either local process exits, the
temporary address stops working and the script must be run again.

Do not switch to another tunnel provider merely because a temporary URL is
requested. That requires an explicit request or a confirmed failure of the
standard local relay.

## Production HTTPS activation

After the domain and ICP requirements are ready:

```bash
# First install the current stable Caddy package from its official Debian/
# Ubuntu repository: https://caddyserver.com/docs/install#debian-ubuntu-raspbian
install -o root -g root -m 0644 Caddyfile.example /etc/caddy/Caddyfile
caddy validate --config /etc/caddy/Caddyfile
systemctl reload caddy
```

Then verify both routes from outside the ECS:

```bash
curl -fsS https://decode.example.com/healthz
curl -fsS \
  -F image=@master512_p01.png \
  -F payload_bits=40 \
  https://decode.example.com/decode
```

Keep port 8765 closed publicly. A future production setup may replace the quick
tunnel with a stable domain and reverse proxy; the CloudBase proxy pattern can
remain unchanged.
