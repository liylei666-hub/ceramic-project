# 真实陶瓷 01–18 本机适配候选

日期：2026-08-15

## 结论

本候选使用笔记本 RTX 4070 Laptop GPU 完成，并于 2026-08-15 在 ECS
隔离预检通过后部署；正式 900K 父权重仍作为即时回滚保留。

- 用户提供的两张真实陶瓷板照片共 18 个图案，全部按真实编号 01–18 裁出并与原始清单中的业务 ID 交叉核对。
- 正式 900K 权重配合当前线上 57 个候选时，仅正确恢复 3/18。
- 候选适配权重配合“现有 57 候选 + 最后 7 个灰度尺度候选”后，原始 18 张为 18/18。
- 连续重复解码 3 次，每张结果均一致，即 54/54 正确；没有错误的 BCH+CRC 合法 ID。
- 01–06、08–18 在第一级粗搜索恢复；07 在最后的灰度共识阶段恢复。
- 旧彩色实拍和旧灰度实拍均正确恢复 `08022061102620554`。
- 未嵌入负样本和旧 40-bit 图片均保持拒绝。
- 正式 900K 父权重文件未修改。ECS 当前运行本候选，部署与回滚证据位于
  `/opt/ceramic-watermark/deployments/real18_candidate_20260815-150105`。

## 权重与代码身份

- 正式父权重 SHA-256：
  `86cab6a87981c72c225a180201c85cd87773e2daa373ce95f0205545c2aee4b8`
- 隔离候选权重：
  `checkpoint_decoder_57bit_real18_legacy_pilot3_step600.pt`
- 候选权重 SHA-256：
  `834d33d4666921f1ae6416d5c3a9d08a7ac60dc9dc21f4ce907caa5923e1d6ef`
- 候选 API SHA-256：
  `21531782ffe62dbe183f35452bdbc62c540c43f5f958831c59874b1daa3626cd`
- 候选 API 只在现有三个阶段全部失败后增加 7 个灰度尺度：
  `1.0/0.92/0.9/0.84/0.8/0.7/0.6`，至少两个候选恢复同一 ID 才接受。

## 证据文件

- `evidence/formal900k_baseline_original18.json`：正式 900K 的 3/18 基线。
- `evidence/candidate_original18_repeat3.json`：候选对 18 张连续三次的 54/54 结果。
- `evidence/candidate_regressions.json`：旧实拍、负样本及对照样本回归。
- `evidence/training_summary.json`：第三轮训练合同、选择步数和评估摘要。
- `evidence/training_metrics.jsonl`：训练过程中每 100 步的固定评估结果。
- `evidence/audit_144_bounded_candidate.json`：选择权重之后定义的 144 张组合扰动审计。
- `evidence/audit_144_photometric_ceiling.json`：更大光照搜索在同一 144 张上的覆盖上限。

## 限制

原始 18 张就是本轮适配数据，因此 18/18 只证明对用户提供的这两张真实照片稳定，不能直接外推为任意新陶瓷、手机、距离和光照下均为 100%。

选择权重之后额外定义的 144 张组合扰动审计中：

- 有界候选策略正确 101/144（70.14%）；
- 更大的通用光照搜索正确 112/144（77.78%）；
- 两者均没有错误的 CRC 合法 ID；
- 主要失败来自人为叠加的偏暗高对比和偏暗模糊条件。

因此该候选满足“稳定解出当前提供的 18 张”这一目标，但部署前仍建议新增独立手机实拍作为真正盲测，尤其覆盖暗光、虚焦和反光。

## 数据身份

- 冷色光照 01–09 原图 SHA-256：
  `9efacfebd0ba0a1e0fd2240fcc63deac8f421bf4922d9f9457b32cbc723b2835`
- 暖色光照 10–18 原图 SHA-256：
  `31e49d6c77480f1a99672e453bb1056792e6446b2a30091480191fd9a32c7775`
- 真实 ID 对照：`manifests/expected_ids_01_18.json`
- 裁切坐标与裁片哈希：`manifests/crop_manifest_01_09.json`、`manifests/crop_manifest_10_18.json`

## 目录

- `decoder_api/`：隔离候选 API 源码。
- `samples/real_crops/`：01–18 的独立真实裁片。
- `samples/source_photos/`：两张完整陶瓷板原图。
- `scripts/`：裁切、训练、候选评估和回归脚本。
- `evidence/`：全部结果文件。

ECS 已通过隔离服务预检和正式端口复测后切换到本候选；不要删除正式
900K 父权重或部署目录中的回滚文件。新增真实照片仍应继续作为独立盲测。
