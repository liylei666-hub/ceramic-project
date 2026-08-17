# Step 113100 payload-generalization audit

Date: 2026-08-16 CST

## Conclusion

Step 113100 is not restricted to the 18 identifiers used by the real-ceramic
adaptation. The frozen encoder and the deployed decoder successfully completed
two clean digital 57-bit tests on server 249 GPU6 without training or changing
the production service.

- Correct historical 57-bit set: P01-P20 at K3 and K5, 40/40 exact, zero wrong
  BCH-5/CRC-4-valid identifiers. P19 and P20 were not among the 18 physical
  adaptation identifiers and both passed at both strengths.
- Fresh closed loop: 20 newly generated identifiers, disjoint from the earlier
  P01-P20 set, embedded at K3 and K5 and decoded through the locator5 API,
  40/40 exact with zero wrong valid identifiers.
- Checkpoint SHA-256:
  `834d33d4666921f1ae6416d5c3a9d08a7ac60dc9dc21f4ce907caa5923e1d6ef`.
- No model weights, production code, or GPU7 service were changed.

This establishes payload generalization for saved digital images. It does not
claim that every newly printed and photographed ceramic image will decode:
physical printing, firing, lighting, focus, crop, and resolution remain a
separate robustness problem.

## Corrected invalid comparison

The earlier P19/P20 comparison against
`evaluations/kmix100300_best_step29500_k1to5_20_seed2026072520` was invalid.
Those files carry old 40-bit payloads, while the evaluation assigned them the
new 57-bit P19/P20 identifiers. Therefore the reported 0/6 and raw Hamming
distances did not measure 57-bit payload generalization.

The same old 40-bit directory was also used as P01-P18 replay during the
600-step real-ceramic adaptation, paired with 57-bit labels. This is an
incorrect-label replay-data defect. It invalidates the adaptation run's
digital-unseen evaluation and weakens its training provenance, although the
two corrected tests above show that step 113100 still retains clean arbitrary
payload capability. Do not retrain or replace the deployed checkpoint without
explicit authorization and the complete regression gate.

## Evidence on server 249

Root:
`/data0/liyanlei/ceramic_watermark/tmp/correct57_unseen_20260816`

- Correct P01-P20 K3/K5 result:
  `step113100_correct57_K3K5.jsonl`
  (SHA-256 `58384d140ab09095e63ab9502501cedcdb344c2b6e77e776fa4e2c01b5df5e0c`)
- Fresh random embedding manifest:
  `new_random_seed2608165701/manifest.json`
  (SHA-256 `4f66af79c117ea0553ff1681ab9677985bb6e17607136095147dad26ec8b511d`)
- Fresh locator5 API result:
  `new_random_api_step113100.jsonl`
  (SHA-256 `37bc66461d1e35171ce7fc2c752c31a14f15d209b228c7612a0f9d2c025af8d8`)

The fresh manifest contains 20 unique identifiers and has zero overlap with
the earlier P01-P20 identifiers.
