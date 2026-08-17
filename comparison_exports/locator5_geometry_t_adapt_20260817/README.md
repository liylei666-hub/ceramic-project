# Locator5 Geometry-T Adaptation

Date: 2026-08-17 CST

## Status

Rejected. The operational checkpoint remains step 113100 with SHA-256
`834d33d4666921f1ae6416d5c3a9d08a7ac60dc9dc21f4ce907caa5923e1d6ef`.
GPU7 service files and weights were not modified.

## Candidate contract

- Parent: operational step 113100.
- Device: server 249 GPU6 only.
- Training data: existing labeled physical crops 01-18 and verified 57-bit
  P01-P20 K1/K3/K5 replay. No failure samples and no blind_test10 image were
  used for training or selection.
- BatchNorm statistics: frozen.
- Non-geometric image degradations were unchanged.
- Geometry T: 60% exact active locator5 crops (`0.84` colour, `0.88`
  grayscale, `0.92` colour); 40% bounded residuals with scale `0.84-0.96`,
  shift `+/-1.2%`, and rotation `+/-0.75 degrees`.
- Training: seed `2608171131`, 300 steps, batch size 4, three physical items
  per batch, AdamW learning rate `1e-7`.

## Full locator5 regression

The parent passed all retained checks: real 18/18, perspective 54/54,
rotation 180/180, combined perspective-rotation 36/36, boards 2/2,
negatives 2/2, and failure06 remained 0/1.

| Candidate step | Regression result | Rejection reason |
|---:|---|---|
| 50 | Combined 35/36 | `07_p24_r090` failed |
| 100 | Rotation 178/180; combined 35/36 | `07_r060`, `07_r270`, `07_p24_r090` failed |
| 150 | Combined 35/36 | `07_p24_r090` failed |
| 200 | Rotation 179/180; combined 35/36 | `07_r270`, `07_p24_r090` failed |
| 250 | Rotation 179/180 | `07_r270` failed |
| 300 | Rotation 178/180 | `07_r060`, `07_r270` failed |

All six candidates also left failure06 at 0/1. None is stronger than the
parent under the no-regression deployment gate, so none is a deployment or
rollback candidate.

## Artifacts

- Remote experiment root:
  `/data0/liyanlei/ceramic_watermark/experiments/locator5_geometry_t_adapt_20260817`
- Candidate script SHA-256:
  `cfa4267444ecca9dae18c0418489058aec16a1771f1446638543ce4f5acecef3`
- Full regression output:
  `full_regression_gpu6.jsonl`
