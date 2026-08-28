---
status: resolved
trigger: "SSH tunnel exited unexpectedly although the operator did not change networks; determine root cause and prevent recurrence."
created: 2026-08-17T13:10:00+08:00
updated: 2026-08-17T13:27:00+08:00
---

# SSH tunnel reset

## Symptoms

- Expected: the temporary Mini Program route remains available while the PC is awake and online.
- Actual: cloudflared remained alive, but the SSH forward stopped listening on `127.0.0.1:18766`.
- Observed error: `client_loop: send disconnect: Connection reset` at 2026-08-17 12:07:28 CST.
- Timeline: tunnel started at 11:20:49 CST and failed about 47 minutes later.
- Reproduction: not deterministic; no intentional network change was made.

## Current Focus

- hypothesis: confirmed.
- test: forced termination of the active SSH forward while leaving cloudflared running.
- expecting: watchdog creates a new SSH process, exact local health recovers, and the same public hostname remains valid.
- next_action: none.

## Evidence

- timestamp: 2026-08-17T12:07:03+08:00
  observation: Windows WLAN AutoConfig event 8003 recorded that the Intel AX201 driver disconnected from `SYSU-SECURE`.
- timestamp: 2026-08-17T12:07:14+08:00
  observation: the first reassociation attempt failed because the driver disconnected during association.
- timestamp: 2026-08-17T12:07:17+08:00
  observation: WLAN association and WPA2-Enterprise connection succeeded.
- timestamp: 2026-08-17T12:07:28+08:00
  observation: SSH stderr recorded `Connection reset`; cloudflared recorded its control stream cancellation at the same second and reconnected nine seconds later.
- timestamp: 2026-08-17T13:05:57+08:00
  observation: canonical script restored SSH forwarding and reused the existing Cloudflare hostname; public health passed.
- timestamp: 2026-08-17T13:26:00+08:00
  observation: controlled SSH termination recovered automatically to a new PID, remained stable for an additional 15 seconds, and passed exact local and authoritative-DNS public health verification.

## Eliminated

- hypothesis: step 113100 decoder or GPU5 service failed.
  reason: direct SSH health check to `127.0.0.1:28765` returned the exact expected model and hashes.
- hypothesis: the Cloudflare hostname expired first.
  reason: cloudflared remained alive, reconnected to the edge, and logged origin connection refusal only after local port 18766 disappeared.
- hypothesis: the user intentionally changed networks.
  reason: WLAN events identify a driver-triggered disconnect and automatic reassociation on the same SSID.

## Resolution

- root_cause: Intel AX201/WLAN driver disconnected the active Wi-Fi association for about 14 seconds. Both long-lived transports dropped; cloudflared automatically reconnected, but OpenSSH exited and the one-shot launcher had no supervisor.
- fix: added an SSH-only watchdog, launched idempotently by the canonical GPU5 tunnel script. It verifies exact health every 10 seconds and recreates only the local SSH forward with bounded backoff.
- verification: forced SSH failure changed the SSH PID, recovered exact step-113100 health automatically, stayed stable, and preserved the existing Cloudflare hostname.
- files_changed: deployment_artifacts/watch-local-249-gpu5-ssh-forward.ps1; deployment_artifacts/start-local-249-gpu5-decoder-tunnel.ps1; deployment_artifacts/README.md; 57BIT_RETAINED_STATE.md; NEW_CHAT_HANDOFF.md.
