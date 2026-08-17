# 2026-08-16 失败样本独立评估

## 结论

- 正式权重 step 113100、GPU7 locator5 服务及公网路由均未修改。
- 6 个文件中 `failure_04.png` 与 `failure_05.png` 内容相同，实际为 5 张不同图片。
- 正式服务已能解出 04/05；原权重加自动灰度拉伸也能稳定解出 06。
- 01/02/03 在 3150 组定位、尺度、插值和光度前处理下均无合法 BCH-5/CRC-4 结果。
- 两轮从 step 113100 隔离分支的低分辨率/暗光/模糊/JPEG 微调均未救回 01/02/03，且第二轮损害旧样本，因此两个候选都淘汰，禁止部署。
- 使用正式权重和 18 个已发行编号的码字目录，在现有 51 次解码全部失败后追加 6 个候选，可正确恢复全部失败样本，同时不接受现有无水印负样本和空白图。

## 第二轮微调候选（淘汰）

- 远端目录：`/data0/liyanlei/ceramic_watermark/experiments/lowres_candidate_from113100_20260816/round2_strong`
- 最佳分支步数：50（对应总步数 113150）
- SHA-256：`6926834d213c347ddb0f92d14de14a393cac1c44d4cbea3281232e954b6ef518`
- 原 18 张直接命中：9/18
- 01/02/03 合法候选：0/0/0
- 01/02/03 到目标码字的最低硬错误位：13/17/12

## 六候选已发行编号目录回退

仅在正式的直接、透视、旋转三级共 51 次均失败后运行。使用正式 step 113100 权重，约束如下：

- 最近目录码字距离不超过 16 位；
- 与目录第二名的距离差至少 10 位；
- 至少 2 个独立候选返回同一编号；
- 目录必须覆盖所有已发行编号；目录外编号不允许走此回退。

六个候选为：

1. inner `0.46`、padding `0.96`、gray-auto-unsharp1、bilinear
2. inner `0.46`、padding `0.96`、gray-auto-unsharp1、bicubic
3. inner `0.42`、padding `0.80`、gray-auto-unsharp1、lanczos4
4. inner `0.44`、padding `0.84`、gray-auto-unsharp1、lanczos4
5. inner `0.46`、padding `0.96`、gray-contrast125、bicubic
6. inner `0.46`、padding `0.96`、gray-contrast125、lanczos4

独立评估结果：

| 输入 | 正确编号 | 通过严格门槛的同意候选数 |
|---|---|---:|
| failure_01 | `91321270129575785` | 2 |
| failure_02 | `91321270129575785` | 2 |
| failure_03 | `09366360614692060` | 2 |
| failure_04 | `91321270129575785` | 6 |
| failure_05 | `91321270129575785` | 6 |
| failure_06 | `21359300828395828` | 4 |
| unwatermarked_negative | 不接受 | 0 |
| blank | 不定位 | 0 |

这只是 GPU6 离线候选验证，尚未加入 API，尚未做完整旧回归，也未部署到 GPU7。

## 实际失败照片定向训练与十张盲测

- 用户随后允许原失败照片进入训练，并另提供十张独立盲测图。
- 冻结 BatchNorm 统计量的 round5 step300 能让旧 failure_06 以三次直接候选恢复，同时保持原18张18/18。
- round5 step300 SHA-256：`30f7bf8f2bfff55514ad9cd6e45351a05cf096f47aa75da33fcb3d28d1562795`。
- 直接替换仍被完整回归否决：透视54/54、旋转178/180、透视旋转35/36，低于正式权重180/180和36/36。
- 为严格保留旧效果，固定了“正式 step113100 全部失败后才调用 round5”的离线级联策略；正式旧回归由原模型完成，两个负样本在辅助模型上也保持不接受。
- 十张盲测中，正式模型检测4/10，固定级联检测5/10，仅净新增编号05一张；泛化提升不足，级联未部署。
- 完整盲测记录：`comparison_exports/failure_samples_20260816/blind_test10/README.md`。

## 本地实验脚本

- `tmp/search_failure_preprocessing_gpu.py`
- `tmp/measure_failure_bit_errors_gpu.py`
- `tmp/finetune_lowres_capture_candidate.py`
- `tmp/finetune_lowres_capture_candidate_round2.py`
- `tmp/test_soft_aggregation_gpu.py`
- `tmp/evaluate_catalog_fallback_gpu.py`
- `tmp/evaluate_catalog_minimal_gpu.py`
