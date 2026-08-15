# Requirements: 陶瓷水印（Ceramic Watermark）

> **基线边界**：所有 v1 要求均以当前 step 113100 checkpoint（SHA-256 `834d33d4666921f1ae6416d5c3a9d08a7ac60dc9dc21f4ce907caa5923e1d6ef`）为对象，不授权训练、替换权重或续跑历史实验。适配集 18/18 不是独立盲测，也不是普遍 100% 的依据。

**Defined:** 2026-08-15  
**Core Value:** 在真实陶瓷/生产手机裁切流程中精确恢复经 BCH-5 + CRC-4 校验的 57-bit 业务标识，同时保留负样本拒绝，并只以独立新实拍盲测衡量泛化。

## v1 Requirements

### Current Operational Baseline

- [ ] **BASE-01**: 操作者可无写入地确认活动服务使用 `/opt/ceramic-watermark/models/checkpoint_decoder_57bit_real18_legacy_pilot3_step600.pt` 的 step 113100 checkpoint（SHA-256 `834d33d4666921f1ae6416d5c3a9d08a7ac60dc9dc21f4ce907caa5923e1d6ef`）和 API 源码 SHA-256 `21531782ffe62dbe183f35452bdbc62c540c43f5f958831c59874b1daa3626cd`，且服务健康检查通过。
- [ ] **BASE-02**: step 112500 父权重（SHA-256 `86cab6a87981c72c225a180201c85cd87773e2daa373ce95f0205545c2aee4b8`）保持未修改并可立即回滚；Stage 5、40-bit、API 回滚副本、服务配置和 `/opt/ceramic-watermark/deployments/real18_candidate_20260815-150105` 下的部署证据均被保留。
- [ ] **DECODE-01**: 对声明 `payload_bits=57` 的正样本，系统只在完整 57 bits 经 BCH-5 和 CRC-4 校验后接受，并返回由 `5 位企业码 + YYMMDD + 6 位流水号` 组成的 17 位 `business_id` 及其拆分字段，网络模式为 `0001`。
- [ ] **DECODE-02**: 系统保持原 57 个候选不变，仅在其全部失败后依次尝试 7 个居中灰度尺度 `1.0/0.92/0.9/0.84/0.8/0.7/0.6`；灰度阶段至少两个候选恢复同一有效标识才接受，总尝试数不超过 64，早期成功立即返回。
- [ ] **API-01**: 服务提供 `GET /healthz` 和 multipart `POST /decode`（图像字段 `image`）；受保护调用携带配置的 API token 与准确图像 SHA-256，且 token 不出现在小程序源码中。
- [ ] **NEG-01**: 无水印图像和旧 40-bit 图像均返回 `detected: false`，不得暴露已接受的业务标识。
- [ ] **NFR-01**: 生产裁切的正样本和完整负样本均在云函数 20 秒超时预算内返回，并可记录实际 `decode_stage`、fallback 使用情况和尝试次数以供复核。
- [ ] **OPS-01**: 本路线图执行期间不启动训练、不替换权重、不续跑历史实验；任何此类动作均需新的用户明确授权和独立计划。
- [ ] **OPS-02**: 当前解码器保持绑定 `127.0.0.1:8765` 且 8765 不公开；临时访问仅复用指定 Cloudflare/PC/SSH 链路及权威脚本 SHA-256 `48a081d0d744b35adade59f149fda900a18d603214b2ec4ce7c11329da953847`，脚本在返回 decode URL 前通过 `/healthz` 且运行期间 operator PC 保持在线；未获明确授权不修改小程序端点，也不使用 `-ForceNewTunnel` 主动更换 hostname。

### Independent Blind Validation

- [ ] **VAL-01**: 盲测集来自未参与当前适配和权重选择的新印制/烧制陶瓷及新实拍，使用生产手机/小程序裁切流程，记录真实印刷尺寸、设备、距离、光照和失败相关条件，而不强制 `1.5 cm × 1.5 cm`。
- [ ] **VAL-02**: 在查看盲测结果前冻结样本纳入规则、正样本“完整 57-bit + BCH-5 + CRC-4 精确恢复”规则、负样本拒绝规则和汇总指标，防止在盲测集上选择阈值。
- [ ] **VAL-03**: 全部盲测样本在 checkpoint SHA-256 前后核对一致的前提下，通过真实小程序 capture page 的裁切与上传链路执行；正样本按期望业务 ID 逐样本比对，负样本至少覆盖无水印、旧 40-bit，并覆盖暗光、虚焦、反光等真实困难条件。
- [ ] **VAL-04**: 盲测报告公开样本级期望值/实际值、条件、耗时和失败原因，并分别给出精确恢复率、拒绝率与假接受数的分子/分母；报告明确将 01–18 的 18/18 标为适配集证据，不外推为任意新陶瓷、手机、距离或光照下 100%。

### Compliant Production Access

- [ ] **PROD-01**: 生产入口使用指向 ECS `8.138.42.34` 的受控域名与 DNS，并在适用时完成中国大陆 ICP 备案，证书和域名状态可被外部检查。
- [ ] **PROD-02**: ECS 公网只开放 TCP 80/443，由 Caddy 或 Nginx 将 HTTPS `/decode` 反向代理到 `http://127.0.0.1:8765/decode`；公网无法直连 8765。
- [ ] **PROD-03**: 生产请求路径保护 `/decode`，且无需把受保护 API token 嵌入小程序源码；HTTPS origin 已加入小程序 `uploadFile` 合法域名。
- [ ] **PROD-04**: 只有在用户明确授权端点变更后才将 `decodeApiUrl` 设置为合规 HTTPS URL；随后真机完成引导框裁切、512×512 PNG 上传、精确业务 ID 显示与负控拒绝的端到端验证。

## v2 Requirements

None defined. Any model training or weight change requires a separately authorized milestone and is not implicitly deferred work.

## Out of Scope

| Feature | Reason |
|---------|--------|
| 训练、微调、alpha sweep、权重替换、历史实验续跑 | 用户明确禁止；本里程碑验证并部署当前接受权重 |
| 自然图像 512-bit watermark PoC | 与陶瓷 57-bit 业务协议和运行环境相互独立 |
| 40-bit 正向兼容 | 旧 40-bit 仅作为拒绝负控 |
| 公开 TCP 8765 | 解码器必须保持 loopback，公网只允许 80/443 |
| 未授权的小程序端点或临时 hostname 变更 | 属于外部运行状态变更，必须由用户明确批准 |
| 以适配集 18/18 宣称普遍 100% | 数据参与适配，不能证明独立泛化 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| BASE-01 | Phase 1 | Pending |
| BASE-02 | Phase 1 | Pending |
| DECODE-01 | Phase 1 | Pending |
| DECODE-02 | Phase 1 | Pending |
| API-01 | Phase 1 | Pending |
| NEG-01 | Phase 1 | Pending |
| NFR-01 | Phase 1 | Pending |
| OPS-01 | Phase 1 | Pending |
| OPS-02 | Phase 1 | Pending |
| VAL-01 | Phase 2 | Pending |
| VAL-02 | Phase 2 | Pending |
| VAL-03 | Phase 2 | Pending |
| VAL-04 | Phase 2 | Pending |
| PROD-01 | Phase 3 | Pending |
| PROD-02 | Phase 3 | Pending |
| PROD-03 | Phase 3 | Pending |
| PROD-04 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0
- Duplicate mappings: 0

---
*Requirements defined: 2026-08-15*  
*Last updated: 2026-08-15 after roadmap creation from ingested operational intel*
