# Synthesized Context

## Current ceramic-watermark operations

source: `NEW_CHAT_HANDOFF.md`

The following current override is retained verbatim:

> The ECS decoder now runs the 57-bit real-ceramic decoder adaptation at checkpoint step 113100, SHA-256 `834d33d4666921f1ae6416d5c3a9d08a7ac60dc9dc21f4ce907caa5923e1d6ef`.
>
> It is decoder-only adaptation from the retained 900K step-112500 parent; the parent checkpoint remains the immediate rollback and was not modified.
>
> Active API source SHA-256: `21531782ffe62dbe183f35452bdbc62c540c43f5f958831c59874b1daa3626cd`.
>
> The previous 57 candidates are unchanged. Only after all fail, seven grayscale centered scales `1.0/0.92/0.9/0.84/0.8/0.7/0.6` run and require agreement from at least two candidates. Maximum attempts are 64.
>
> ECS verification passed all supplied physical crops 01-18, both old real-photo controls, the unwatermarked negative, and the legacy 40-bit negative. Evidence and immediate rollback are under `/opt/ceramic-watermark/deployments/real18_candidate_20260815-150105`.
>
> Typical coarse positives take about 0.52-0.60 seconds on the ECS. Sample 07 takes about 9.1 seconds through grayscale fallback; full negatives take about 9.1 seconds, within the cloud-function 20-second timeout.
>
> Canonical temporary tunnel script SHA-256: `48a081d0d744b35adade59f149fda900a18d603214b2ec4ce7c11329da953847`.
>
> Temporary access still uses `Mini Program -> Cloudflare -> local PC -> SSH -> ECS decoder`.

The handoff explicitly says all later material is historical wherever it conflicts with that current override, `57BIT_RETAINED_STATE.md`, or `deployment_artifacts/README.md`. Its older 40-bit API/model descriptions and 4096 experiment are therefore retained only as history, not active state.

## Mini Program, validation, and HTTPS handoff

source: `NEW_CHAT_HANDOFF.md`

The following operational notes are retained verbatim:

> The capture page now maps the visible guide box to camera-image coordinates, crops only the guide-box content, and exports a 512x512 PNG. Preview, persistence, and upload all use the cropped file. Album images use a centered square crop.
>
> Upload is already implemented with `wx.uploadFile`. The endpoint is configured in `app.js` through `globalData.decodeApiUrl`, which is currently empty.

> 1. Keep synthetic training stopped until the 57-bit specification is approved.
> 2. Build a labeled real-world validation set from printed and fired ceramic pieces photographed through the production phone/miniprogram crop flow, recording the actual printed dimensions rather than enforcing exactly `1.5 cm x 1.5 cm`.
> 3. Define the 57-bit acceptance threshold before testing to avoid selecting on the validation set.
> 4. Treat 57-bit as an independent business scene; do not require 40-bit compatibility in its training or acceptance criteria.
> 5. Any approved formal experiment uses 100,000 training samples, an independent 100,000-sample evaluation, and only server 249 GPUs 4, 5, and 6 (operator update: 2026-08-12).
> 6. Do not schedule or run alpha experiments unless the user explicitly asks.

> 1. Prepare a compliant domain and point it to `8.138.42.34`.
> 2. Complete ICP filing when required for the mainland China ECS.
> 3. Open only TCP 80/443 in the ECS security group; keep 8765 closed.
> 4. Install Caddy or Nginx and proxy HTTPS `/decode` to `http://127.0.0.1:8765/decode`.
> 5. Add the HTTPS origin to the mini program's `uploadFile` legal domains.
> 6. Set `decodeApiUrl` to `https://the-domain.example/decode`.
> 7. Verify the crop and upload flow on a real phone.

No domain or public HTTPS endpoint is configured in the handoff, and Caddy is not installed on the ECS.

## Natural-image 512-bit watermark proof of concept

source: `README.md`

The following PoC notes are retained verbatim:

> 独立实验项目，部署在 249 服务器：`/data0/liyanlei/natural_image_512bit_watermark_poc`。旧的陶瓷水印项目未修改。

> ChunkySeal：官方 VideoSeal 仓库中的 1024-bit 图像水印模型。
>
> SyncSeal：官方 WMAR 仓库中的几何同步模型，用于旋转和裁剪后的反变换。
>
> 本轮把 512-bit 有效载荷简单重复一次，形成 1024-bit 物理消息；这只是基线，不是正式 BCH/LDPC 编码。
>
> 实验固定使用 249 的物理 GPU 7（RTX 3090）。

> 组合输出满足当前的 `PSNR > 40 dB`、`SSIM > 0.98` 要求。

> 说明：旋转的“直接解码”不具备几何不变性，SyncSeal 反变换后恢复；裁剪和 JPEG 是当前基线的主要误码来源。`physical_bit_accuracy` 是 1024-bit 物理消息指标，`payload_bit_accuracy` 是重复合并后的 512-bit 有效载荷指标。

> 1. 用 BCH/LDPC 或交织 + CRC 替换简单重复码，并在多张自然图像、多随机 payload 上统计误码率和整包成功率。
> 2. 对 JPEG QF70 增强训练/微调，目标是纠正本轮 1 bit 残余错误。
> 3. 明确中心裁剪的评价口径：本实验为“保留中心区域后 resize 回 1024”，不是任意位置裁剪。

This PoC is a separate scope from the 57-bit ceramic deployment, so its 512-bit payload and GPU 7 statements do not conflict with the ceramic protocol or GPU contract.

## Real-ceramic 01-18 local adaptation evidence

source: `comparison_exports/real_ceramic_18_local_adapt_20260815/README.md`

The following evidence and limitation notes are retained verbatim:

> 本候选使用笔记本 RTX 4070 Laptop GPU 完成，并于 2026-08-15 在 ECS 隔离预检通过后部署；正式 900K 父权重仍作为即时回滚保留。

> 用户提供的两张真实陶瓷板照片共 18 个图案，全部按真实编号 01–18 裁出并与原始清单中的业务 ID 交叉核对。
>
> 正式 900K 权重配合当前线上 57 个候选时，仅正确恢复 3/18。
>
> 候选适配权重配合“现有 57 候选 + 最后 7 个灰度尺度候选”后，原始 18 张为 18/18。
>
> 连续重复解码 3 次，每张结果均一致，即 54/54 正确；没有错误的 BCH+CRC 合法 ID。
>
> 01–06、08–18 在第一级粗搜索恢复；07 在最后的灰度共识阶段恢复。
>
> 旧彩色实拍和旧灰度实拍均正确恢复 `08022061102620554`。
>
> 未嵌入负样本和旧 40-bit 图片均保持拒绝。

> 原始 18 张就是本轮适配数据，因此 18/18 只证明对用户提供的这两张真实照片稳定，不能直接外推为任意新陶瓷、手机、距离和光照下均为 100%。

> 选择权重之后额外定义的 144 张组合扰动审计中：有界候选策略正确 101/144（70.14%）；更大的通用光照搜索正确 112/144（77.78%）；两者均没有错误的 CRC 合法 ID；主要失败来自人为叠加的偏暗高对比和偏暗模糊条件。

> 因此该候选满足“稳定解出当前提供的 18 张”这一目标，但部署前仍建议新增独立手机实拍作为真正盲测，尤其覆盖暗光、虚焦和反光。

The evidence directory, training metrics, 144-sample audits, source-photo hashes, crop manifests, isolated API source, and rollback bundle remain under `comparison_exports/real_ceramic_18_local_adapt_20260815/` and `/opt/ceramic-watermark/deployments/real18_candidate_20260815-150105`.
