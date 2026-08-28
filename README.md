# 陶瓷 57-bit 水印项目

面向真实陶瓷生产和手机拍摄流程的 57-bit 业务标识水印系统。

## 当前运行基线

- 解码模型：`trustmark-q-57bit-real18-step113100-locator5-perspective-rotation`
- checkpoint：decoder-only 实陶适配，step 113100
- checkpoint SHA-256：`834d33d4666921f1ae6416d5c3a9d08a7ac60dc9dc21f4ce907caa5923e1d6ef`
- 输入：微信小程序裁切后的 512×512 PNG
- 业务载荷：57-bit，包含 BCH-5 纠错、CRC-4 校验和业务标识解析

## 目录

- `deployment_artifacts/`：解码 API、249 GPU5 部署、Cloudflare/SSH 隧道及 watchdog
- `cloudfunctions/`：CloudBase 解码、配置读取和配置更新云函数
- `57BIT_RETAINED_STATE.md`：当前模型、接口和验收状态
- `NEW_CHAT_HANDOFF.md`：运行交接信息
- `.planning/`：项目规划、约束和阶段状态
- `comparison_exports/`：已提交的实验摘要和验证报告

## 生产链路

微信小程序 → CloudBase → HTTPS 临时入口 → 249 GPU5 回环解码服务。

解码器只绑定回环地址，公网访问通过受保护的 HTTPS 入口转发。API token、SSH 私钥、模型权重、日志和临时运行文件均不纳入 Git。

## 重要约束

- 当前 step 113100 是唯一接受的运行基线，未经明确授权不得替换或重新训练。
- 57-bit 业务协议与旧 40-bit 项目保持隔离。
- 生产端点和小程序配置不得在未授权情况下变更。

部署与验证命令请参阅 [`deployment_artifacts/README.md`](deployment_artifacts/README.md)。
