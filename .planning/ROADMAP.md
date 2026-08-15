# Roadmap: 陶瓷水印（Ceramic Watermark）

> **路线图边界**：当前 step 113100 是已接受、必须保留的运行基线，不是待训练候选。路线图只做基线防漂移与复核、独立新实拍盲测，以及盲测之后的合规 HTTPS 生产接入；不包含训练、替换权重、续跑历史实验或未经授权的小程序端点变更。

## Overview

项目先把现有 57-bit 解码服务、回滚能力、协议行为和临时访问边界固化为可复核的运行基线；再以同一 checkpoint 通过真实小程序裁切/上传链路执行预先冻结口径的独立新实拍盲测，诚实测量精确恢复和负样本拒绝；最后才在用户明确授权端点变更后建立合规 HTTPS 入口并做真机端到端验证。由于未提供 granularity 配置，本路线图采用默认 Standard，但遵循“最小、结果导向”要求压缩为 3 个自然交付阶段。

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): planned milestone work
- Decimal phases: reserved for urgent insertions

- [ ] **Phase 1: Preserve the Accepted Operational Baseline** - 当前解码器身份、协议、负控、回滚与临时访问边界可复核且不漂移。
- [ ] **Phase 2: Independent Real-Ceramic Blind Validation** - 用不参与适配的新制品和新实拍，在真实手机裁切链路上衡量泛化。
- [ ] **Phase 3: Compliant HTTPS Production Access** - 在盲测后且获端点变更授权时，以合规 HTTPS 完成生产真机接入。

## Phase Details

### Phase 1: Preserve the Accepted Operational Baseline
**Goal**: 操作者可以确认当前服务仍是获接受的 step 113100 部署，并在不训练、不换权重、不暴露 8765、不改小程序端点的前提下安全运行和即时回滚。  
**Depends on**: Nothing (first phase)  
**Requirements**: BASE-01, BASE-02, DECODE-01, DECODE-02, API-01, NEG-01, NFR-01, OPS-01, OPS-02  
**Success Criteria** (what must be TRUE):
  1. 操作者可从健康检查和部署证据核对活动 checkpoint、API 源码、step 112500 回滚及保留工件的指定 SHA-256，且核对过程不写入或替换任何权重。
  2. 使用生产裁切正样本调用受保护的 `/decode` 时，只有 BCH-5 与 CRC-4 均有效的完整 57-bit 结果会被接受，并返回精确 17 位业务 ID 及企业码、日期码和流水号拆分。
  3. 困难正样本可观察到原 57 候选先运行、七个灰度尺度仅在其全部失败后运行、灰度结果至少双候选一致且总尝试不超过 64；诊断字段与实际路径一致。
  4. 无水印和旧 40-bit 负控均保持 `detected: false`，正负样本均在 20 秒预算内返回，不产生错误的 CRC 合法业务 ID。
  5. 临时链路只通过权威脚本到达 ECS loopback，返回 decode URL 前 `/healthz` 已通过且 operator PC 在线，公网 8765 保持关闭；检查可证明未启动训练、未续跑历史实验、未更换权重，且未擅自修改小程序端点或用 `-ForceNewTunnel` 更换 hostname。
**Plans**: TBD

### Phase 2: Independent Real-Ceramic Blind Validation
**Goal**: 用户获得一份可审计的独立新实拍盲测结果，能判断当前固定解码器在真实生产手机裁切流程中的精确恢复、拒绝和已知失败边界。  
**Depends on**: Phase 1  
**Requirements**: VAL-01, VAL-02, VAL-03, VAL-04  
**Success Criteria** (what must be TRUE):
  1. 在解码结果揭盲前，用户可审阅已冻结的样本纳入规则、精确 57-bit 成功规则、负样本拒绝规则和汇总指标；新样本具有未参与适配的来源证明并记录真实尺寸、设备与拍摄条件。
  2. 每个盲测正样本均通过真实手机上的小程序 capture page 引导框裁切和上传，以期望 17 位业务 ID 做逐样本精确比对；checkpoint 在测试前后保持指定 SHA-256 不变。
  3. 无水印、旧 40-bit 以及暗光、虚焦、反光等困难负控/场景均有样本级结果，用户可看到准确拒绝、假接受、耗时和失败原因，而非只看到汇总百分比。
  4. 最终报告展示精确恢复率、拒绝率和假接受数的分子/分母及适用条件，并明确区分独立盲测与适配集 18/18，不声称任意新陶瓷、手机、距离和光照下普遍 100%。
**Plans**: TBD  
**UI hint**: yes

### Phase 3: Compliant HTTPS Production Access
**Goal**: 经授权后，小程序用户可通过合规 HTTPS origin 安全上传生产裁切并获得解码结果，而 ECS 解码器继续保持 loopback 隔离和既有验收行为。  
**Depends on**: Phase 2  
**Requirements**: PROD-01, PROD-02, PROD-03, PROD-04  
**Success Criteria** (what must be TRUE):
  1. 外部检查可确认受控域名、DNS、有效 HTTPS 证书及适用的 ICP 状态，公网只开放 80/443，且无法直接访问 8765。
  2. 通过 HTTPS `/decode` 的受保护请求可到达 `127.0.0.1:8765` 并返回健康的解码响应，而受保护 API token 不存在于小程序源码中。
  3. 在用户明确授权前 `decodeApiUrl` 保持不变；授权后 HTTPS origin 出现在 `uploadFile` 合法域名中，端点指向该 origin 而非临时 relay 或公开 8765。
  4. 用户可在真实手机上完成引导框裁切、512×512 PNG 上传和正确业务 ID 获取；无水印与旧 40-bit 仍被拒绝，端到端请求保持在 20 秒预算内。
**Plans**: TBD

## Coverage Validation

| Phase | Requirement Count | Coverage |
|-------|-------------------|----------|
| Phase 1 | 9 | BASE-01 through OPS-02, each mapped once |
| Phase 2 | 4 | VAL-01 through VAL-04, each mapped once |
| Phase 3 | 4 | PROD-01 through PROD-04, each mapped once |
| **Total** | **17** | **17/17 mapped; 0 orphaned; 0 duplicated** |

## Progress

**Execution Order:** Phase 1 -> Phase 2 -> Phase 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Preserve the Accepted Operational Baseline | 0/TBD | Not started | - |
| 2. Independent Real-Ceramic Blind Validation | 0/TBD | Not started | - |
| 3. Compliant HTTPS Production Access | 0/TBD | Not started | - |
