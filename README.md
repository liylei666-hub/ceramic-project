# 1024x1024 Natural-Image 512-bit Watermark PoC

独立实验项目，部署在 249 服务器：

`/data0/liyanlei/natural_image_512bit_watermark_poc`

旧的陶瓷水印项目未修改。

## 初步方案

- ChunkySeal：官方 VideoSeal 仓库中的 1024-bit 图像水印模型。
- SyncSeal：官方 WMAR 仓库中的几何同步模型，用于旋转和裁剪后的反变换。
- 本轮把 512-bit 有效载荷简单重复一次，形成 1024-bit 物理消息；这只是基线，不是正式 BCH/LDPC 编码。
- 实验固定使用 249 的物理 GPU 7（RTX 3090）。

## 输入和质量

输入：`videoseal/assets/imgs/1.jpg` 调整为 1024x1024 RGB 图像 `assets/natural_1024.png`。

嵌入输出：

| 方法 | PSNR (dB) | SSIM |
|---|---:|---:|
| ChunkySeal | 47.063 | 0.99446 |
| ChunkySeal + SyncSeal | 44.841 | 0.99115 |

组合输出满足当前的 `PSNR > 40 dB`、`SSIM > 0.98` 要求。

## 初测恢复结果

结果文件：`outputs/chunkyseal_syncseal_initial/result.json`。

| 攻击 | 直接解码 512-bit | SyncSeal 反变换后 512-bit | 整包 |
|---|---:|---:|---|
| Identity | 100.0% | 100.0% | 通过 |
| 中心裁剪 50% | 99.805% | 99.219% | 未通过（4 bit） |
| 中心裁剪 70% | 100.0% | 100.0% | 通过 |
| 中心裁剪 90% | 100.0% | 100.0% | 通过 |
| 旋转 10° | 99.805% | 100.0% | 通过 |
| 旋转 30° | 48.828% | 100.0% | 通过 |
| 旋转 45° | 48.828% | 100.0% | 通过 |
| 旋转 90° | 100.0% | 100.0% | 通过 |
| 旋转 180° | 48.828% | 100.0% | 通过 |
| JPEG QF70 | 99.805% | 99.805% | 未通过（1 bit） |

说明：旋转的“直接解码”不具备几何不变性，SyncSeal 反变换后恢复；裁剪和 JPEG 是当前基线的主要误码来源。`physical_bit_accuracy` 是 1024-bit 物理消息指标，`payload_bit_accuracy` 是重复合并后的 512-bit 有效载荷指标。

## 运行

```bash
cd /data0/liyanlei/natural_image_512bit_watermark_poc
CUDA_VISIBLE_DEVICES=7 env/bin/python src/chunky_combo_eval.py
```

脚本使用 mmap 权重加载，避免官方 13GB checkpoint 在 CPU 上完整解包导致 OOM。

## 下一步

1. 用 BCH/LDPC 或交织 + CRC 替换简单重复码，并在多张自然图像、多随机 payload 上统计误码率和整包成功率。
2. 对 JPEG QF70 增强训练/微调，目标是纠正本轮 1 bit 残余错误。
3. 明确中心裁剪的评价口径：本实验为“保留中心区域后 resize 回 1024”，不是任意位置裁剪。
