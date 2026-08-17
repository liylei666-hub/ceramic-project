---
status: resolved
trigger: "旧40-bit回放数据删掉，而且是不是会影响权重能力，重新微调一下权重得到更好的"
created: 2026-08-16
updated: 2026-08-16
---

## Symptoms

- Expected behavior: real-ceramic decoder adaptation preserves arbitrary 57-bit
  payload capability while improving physical-photo robustness.
- Actual behavior: the step-113100 adaptation replay path points to images that
  carry old 40-bit payloads, but the script supervises them with unrelated
  57-bit P01-P18 labels and evaluates P19/P20 the same invalid way.
- Error messages: no runtime exception; the defect is a silent dataset/label
  mismatch.
- Timeline: introduced in the 600-step real-ceramic adaptation on 2026-08-15;
  discovered during the corrected payload-generalization audit on 2026-08-16.
- Reproduction: inspect `image_metrics.csv` in the replay directory and compare
  its `payload_bits_40` values with the 57-bit labels constructed by
  `finetune_real_ceramic_local.py`.

## Current Focus

- hypothesis: the old replay was a real label-provenance defect, but the active
  step 113100 remains the strongest empirically verified single checkpoint.
- test: completed two clean-from-900K seeds, a conservative corrected-replay
  failure-photo adaptation, whole interpolation, and layerwise interpolation.
- expecting: any replacement must equal all retained gates and add a recovery.
- next_action: retain step 113100; collect independent new printed/fired data
  before another weight-selection cycle.

## Evidence

- timestamp: 2026-08-16
  finding: the old replay manifest explicitly declares 40-bit payloads, while
  the adaptation script constructs 57-bit BCH-5 targets for the same images.
- timestamp: 2026-08-16
  finding: corrected genuine 57-bit and fresh random payload tests both passed
  40/40 with step 113100, so the decoder is not limited to 18 identifiers.
- timestamp: 2026-08-16
  finding: obsolete local and remote K1-K5 replay images, CSV, and previews were
  deleted; historical weights, master image, and summary were retained.
- timestamp: 2026-08-16
  finding: a new frozen-encoder replay set contains 60 verified P01-P20
  K1/K3/K5 pairs; K3/K5 pixels match the previously authoritative files.
- timestamp: 2026-08-16
  finding: corrected seed 2608154072 step600 scored physical 18/18,
  perspective 53/54, rotation 179/180, perspective-rotation 35/36, boards 2/2,
  negatives 2/2, and failure06 0/1, so it was rejected.

## Eliminated

- hypothesis: step 113100 memorized only the 18 adaptation identifiers.
  reason: 20 newly generated identifiers at K3/K5 decoded 40/40 through locator5.
- hypothesis: the first clean replay retrain is an immediate replacement.
  reason: it regressed three mandatory historical geometry cases and did not
  recover failure06.
- hypothesis: conservative or layerwise interpolation can retain both hard
  rotations while recovering failure06.
  reason: whole interpolation had disjoint thresholds and 64 layerwise arms
  produced no boundary-passing candidate.

## Resolution

- root_cause: the adaptation replay path referenced old 40-bit encoded images
  while the script constructed unrelated 57-bit labels; the manifest was not
  validated before training.
- fix: deleted obsolete replay image data, rebuilt 60 verified 57-bit pairs,
  and made training fail closed on protocol, identifier, payload, coverage, and
  SHA-256 mismatches.
- verification: corrected replay 60/60 clean; all replacement candidates ran
  through the retained locator5 gate. No candidate strictly exceeded active
  step 113100, whose model/API hashes and health check remain unchanged.
- files_changed: training validation scripts, handoff/deployment state, and
  `comparison_exports/correct57_replay_retrain_20260816/README.md`.
