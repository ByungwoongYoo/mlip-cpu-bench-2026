# Third-party licences

No model weights and no raw reference files are redistributed in this repository. The MIT licence of this
repository covers our code, results and charts only. Before using model weights or model-generated outputs
commercially, check the checkpoint-specific licences.
Licences were read on 2026-11-01/02 from model cards, model repositories and installed package metadata.
This is a summary, not legal advice; check upstream before you rely on it.

| Model | Checkpoint used | Code licence | Weights licence |
|---|---|---|---|
| CHGNet-r2SCAN-2026.9 | `CHGNet-PES-MatPES-r2SCAN-1M-2026.9` via matgl 4.1.3; HF `materialyze/CHGNet-PES-MatPES-r2SCAN-1M-2026.9` @ `ec1d760b9ec1e04f616af05f9a5df0f87dcb0bb7` | matgl: BSD-3-Clause | **UNKNOWN.** The model card states no licence. We do not infer one from the matgl library licence, and we do not claim that commercial use is forbidden either |
| PET-MAD-s | `pet-mad-s-v1.6.0.ckpt` (UPET `version="latest"` resolved to v1.6.0), HF `lab-cosmo/upet` @ `06774bd774562c6f801024f380c5af3026c66b60` | upet: BSD-3-Clause | BSD-3-Clause, as stated by the weight host at that revision. The file we ran is the file at that revision (hash below) |
| Prophet-OAME-MBD | `prophet-oame-mbd.pt` via KairosCalculator | MIT | CC-BY-4.0 |
| MACE-MP-0 medium | `2023-12-03-mace-128-L1_epoch-199.model` (MACE-MP-0 "medium"), float64 | mace-torch: MIT | MIT for this MACE-MP-0 medium checkpoint. Other MACE checkpoints carry their own, different licences; this entry does not cover them |
| FlashCart-MAD | FlashCart MAD checkpoint, seed 0, cutoff 5 Å (`i3c3f96l2_lr2.5e-3_wd1.2e-2_fw0.1_r5.0_s0/best`) | Apache-2.0 | Apache-2.0 (Zenodo 10.5281/zenodo.23159584) |

## Checkpoint hashes (SHA-256 of the files that were loaded)

| Model | File | SHA-256 |
|---|---|---|
| CHGNet-r2SCAN | `model.pt` | `188206edd447bc56ecf9388acb6a019ef1e386285e4ffa30cc44138c0af3c21c` |
| CHGNet-r2SCAN | `state.pt` | `c057cdeb744e1dfbb40b06b286da2b6c519786fb71c26a19c8fa220ec1ff4380` |
| PET-MAD-s | `pet-mad-s-v1.6.0.ckpt` | `3f52e97c459b2a28a94fc49b8a2f9a92551231a0ea4f5b5db2396f12d8ffa1e9` |
| MACE-MP-0 medium | `2023-12-03-mace-128-L1_epoch-199.model` | `01bfe22100139f424713cf921144e5509cbe353d67aa9fa1be9c6e1e0ed35845` |
| Prophet-OAME-MBD | `prophet-oame-mbd.pt` | `28b21122f4c6c1a7c5fe9bac8a0182edf9d24a7a65a72a9ca80b8d12d4620514` |
| FlashCart-MAD | `best/model.pt` | `cb37c7395029fa2610b4df3b16d067fd95e6aafc793de0beeb427f92c9ae5a8e` |

## Reference data

`refs/solids.json` is a derived table (numbers plus citations) built by `build_refs.py` from:

- F. Tran, J. Stelzl, P. Blaha, J. Chem. Phys. 144, 204120 (2016), doi:10.1063/1.4948636, via the CMR `uafd` CSV files.
- K. Lejaeghere, V. Van Speybroeck, G. Van Oost, S. Cottenier, Crit. Rev. Solid State Mater. Sci. 39, 1 (2014),
  doi:10.1080/10408436.2013.772503, arXiv:1204.2733v5 (supplementary tables and ancillary CIFs).

The raw CSVs, the arXiv source and the paper PDFs are not included. `fetch_refs.sh` downloads them and checks their sha256.
