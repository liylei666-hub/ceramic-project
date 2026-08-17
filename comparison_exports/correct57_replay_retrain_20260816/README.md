# Correct 57-bit replay cleanup and retraining

Date: 2026-08-16 CST

## Outcome

The obsolete replay images that carried 40-bit payloads were deleted locally
and on server 249. A verified 57-bit replay set was rebuilt, and three bounded
GPU6 adaptation strategies were evaluated. None produced a single checkpoint
that strictly exceeded the active step 113100 across the complete historical
gate. Therefore no candidate was deployed and GPU7 production remains exactly
unchanged.

Active checkpoint SHA-256:
`834d33d4666921f1ae6416d5c3a9d08a7ac60dc9dc21f4ce907caa5923e1d6ef`

Active API SHA-256:
`3392cdf4175c3c43cc41b3f587d9c235acc838a91277aa44a933ad016aabb55b`

## Deleted data

From both the local comparison export and the matching 249 evaluation root:

- `k_1/` through `k_5/` (100 replay PNGs per copy);
- `image_metrics.csv`;
- five contact sheets and the P01 strength preview.

Historical checkpoints, the unwatermarked master, README, and summary evidence
were retained. The deleted PNGs are reproducible from the frozen encoder, but
the deletions themselves are not recoverable from these locations.

## Correct replay contract

Server root:
`/data0/liyanlei/ceramic_watermark/experiments/real_ceramic_correct57_replay_20260816`

The replacement replay contains P01-P20 at K1/K3/K5, 60 image/label pairs.
Before training, the script now fails closed unless all of the following match:

- 57-bit protocol declaration;
- 17-digit identifier;
- packed 57-bit payload;
- expected P01-P20 coverage at all three strengths;
- file SHA-256.

All 60 saved images passed clean exact57 verification with the unchanged 900K
parent. The K3/K5 decoded pixels are identical to the previously authoritative
57-bit files. Replay manifest SHA-256:
`80c94df1dd0285cbe4a2cc793cd8f6bf5ae4f3a060aeaebe2125ce4a3c45414f`.

## Candidate results

| Candidate | Real | Perspective | Rotation | Perspective+rotation | Boards | Negatives | failure06 | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Active step 113100 | 18/18 | 54/54 | 180/180 | 36/36 | 2/2 | 2/2 | 0/1 | Retain |
| Clean-from-900K seed 2608154072 step600 | 18/18 | 53/54 | 179/180 | 35/36 | 2/2 | 2/2 | 0/1 | Reject |
| Clean-from-900K seed 2608154073 step600 | 17/18 | 54/54 | 177/180 | 36/36 | 2/2 | 2/2 | 0/1 | Reject |
| Step113100 + correct replay + failure photos, BN-frozen step150 | 18/18 | 54/54 | 178/180 | 36/36 | 2/2 | 2/2 | 1/1 | Reject |

The conservative step150 branch recovered failure06 directly in three attempts,
but lost `01_r030.png` and `07_r060.png`. Whole-model interpolation had no
feasible interval: failure06 first recovered at alpha 0.82, while `01_r030.png`
already failed from alpha 0.60. A 64-arm layer-restricted search also found no
candidate that passed the original 18, failure06, and both rotation boundaries.

The ten-image blind set was not used for training, selection, interpolation, or
this evaluation.

## Evidence hashes on server 249

- Clean seed 4072 summary:
  `1fc771f19f0cf49a887669dcb8b3168687a2f3948346b5bd3d1ccc47a52e6ad6`
- Clean seed 4072 full gate:
  `2a6e6050dbd2e2bca6c3ce9e95031e3effbaca826c3105eae516e49cd91c5e92`
- Clean seed 4073 summary:
  `b6841518bfa80675db3e16e6e57cc202aaf1144150b4bfb4e2a4eac38af8c780`
- Clean seed 4073 full gate:
  `29e7611e25dc1f8427f61fbd0943ffb754d7a499e1724b459e9333f024d99d68`
- Correct-replay failure-photo summary:
  `a61884342e07f91793bc8de8e5f6b62fe4541b82829e3f80ebd6bab2514461b6`
- Correct-replay failure-photo full gate:
  `a402de08c19c48b37fcd2becc03caf725b7939e7d448a663b9e5b181540adb05`
- Whole-model interpolation search:
  `1d56a2aa2bc39bbfc7befda56410fe8277123ffd36bf67a69debe43dcc4837b5`
- Layerwise interpolation search:
  `3c163f1bc7c6e5b41b9425fe12dbe474554457af62fe5a7e2806c39bc96a7c54`

## Interpretation

The mislabeled replay unquestionably changed the optimization gradients and
invalidated the old digital holdout evidence. It does not follow that the
deployed checkpoint is empirically weaker: corrected new-payload tests pass,
and every clean replacement tested here regressed at least one retained case.
For the currently available data, step 113100 remains the strongest verified
single checkpoint.
