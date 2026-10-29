# Civilization Vault — Master Plan

**Plan version:** 2026-10 (cycle 1) · **Next review:** 2027-04 · **Then:** every 6 months (April / October)
**Implemented by:** [`civilization_vault_v5/`](civilization_vault_v5/README.md). The allowlist is `sources.json`.

This file is the fixed reference for the project. Each review revalidates it and updates the numbers in place. Record what changed in the change log at the bottom.

---

## 1. Constraints and decisions

| Item | Decision |
|---|---|
| Budget | Low now; revisited at every 6-month review |
| Storage ceiling | **30 TB raw** acceptable over the life of the plan |
| Current hardware | 2 × 10 TB disks; cycle 1 needs **4.6 TB** of them (§5) |
| GPUs | Not owned. Borrowed from other projects/companies for batch jobs (§4) |
| Scope | Industrial-civilization recovery across the 3 scenarios (near-zero tech, 90–99% population loss, systems collapse) |
| Advanced tech | Semiconductors, pharma, aerospace: **a defined minimum is mandatory** (§3); depth beyond that is optional |
| Software | Full Linux distribution **with source**, plus the Python and Rust libraries needed to run, convert and fine-tune the selected models. The vault must be able to rebuild its own tools |
| AI role | Teaches, searches, translates and explains. It never replaces exact data: doses, specs, tolerances, firmware or standards |

## 2. Tiers (measured 2026-10-29 by `vault.py discover`)

All sizes are measured from the live sources: catalogs, APIs, indices and HEAD checks. Only 20 small files (mostly GitHub source tarballs) have no size before download.

| Tier | Files | Logical size | Copies | Raw | What it is |
|---|---|---|---|---|---|
| **P0 Bootstrap seed** | 74 | **132.5 GB** | 2 disks + 2 USB drives | 265 GB | Usable on a weak laptop with no GPU and no internet |
| **P1 Recovery library** | 214,809 | **1.26 TB** | 2 | 2.51 TB | Main working library, software stack and advanced-tech minimum |
| **P2 Deep technical** | 61,901 | **1.84 TB** | 1 | 1.84 TB | Large models, fine elevation data, big databases |
| **P3 Extension** | — | up to the 30 TB ceiling | 1 | — | Chosen at each review |
| **Total** | 276,784 | **3.23 TB** | | **4.62 TB** | |

### P0 — Bootstrap seed (132.5 GB)

| Group | Size |
|---|---|
| Wikipedia EN without images (52.7), MDWiki, WikiMed, Wikibooks, Wikiversity, Wiktionary | 75 |
| LibreTexts (10 subjects); iFixit, Appropedia, energypedia, CD3WD, post-disaster, water, food, knots, medicine ZIMs, MedlinePlus, NHS medicines, CDC, PhET | 19 |
| 17 technical StackExchange sites (electronics, physics, chemistry, DIY, mechanics, aviation…) | 12.5 |
| AI Level A: Gemma 4 12B Q4 + vision projector (CPU-capable) | 7.3 |
| AI Level B: Qwen3.8 27B UD-Q4_K_M + vision projector | 17.4 |
| llama.cpp CPU/Vulkan builds (Windows, Linux, macOS) + source; Kiwix readers and server | 0.8 |
| FAA handbooks: PHAK, AMT General/Airframe/Powerplant, Weight & Balance, AC 43.13-1B | 0.5 |

### P1 — Recovery library (1.26 TB)

| Group | Size |
|---|---|
| Wikipedia with images 127.4, Gutenberg 221.3, Khan Academy 180.0 (**dated 2023-03**), CrashCourse 23.0, Stack Overflow + 6 SE sites 136.6, Wikisource, Wikivoyage | 697 |
| Wikipedia raw XML dump (re-indexing, AI retrieval) | 27.2 |
| OpenStreetMap planet 95.5; Copernicus DEM GLO-90 elevation 71.1 | 167 |
| **Software stack** (see §2a) | 270 |
| AI Level B extras: Qwen3.6 35B-A3B MoE 23.0, Qwen3.8 27B Q8 29.1, Gemma 4 31B 19.5, Qwen3 embedding 1.2 | 73 |
| Advanced-tech minimum (§3) | ~32 |

### §2a Software stack: rebuild-your-own-tools (P1)

| Component | Size | Notes |
|---|---|---|
| **Debian 13 "trixie" full mirror, amd64 + all source**: main, contrib, non-free, non-free-firmware | 243.5 GB, 186,870 files | Working apt repository: Linux kernel source, GCC, Python, Rust, CMake, CUDA toolkit packages (non-free), drivers, firmware. Every file SHA-256-verified against the signed Release file |
| Debian amd64 DVD-1 | 4.0 GB | Bootable installer for a blank machine; the mirror then provides everything else |
| **Python 3.13 wheelhouse, Linux x86_64** (CUDA torch, vLLM): 6 groups `vllm`, `core`, `sci`, `apps`, `onnx`, `build` | 4.0 GB, 554 files | Wheels + source packages + hash-locked requirements file per group. vLLM pins torch 2.13; the rest uses torch 2.15, so they are separate environments |
| Python 3.13 wheelhouse, Windows x64 (CPU torch): 5 groups | +0.56 GB | Shares the wheel folder with Linux |
| Source-only Python packages: llama-cpp-python, deepspeed, flash-attn | included | Built with the toolchains below |
| CPython 3.13 source + Windows installer + embeddable | 0.06 GB | |
| PyTorch full source (with submodules) | 0.8 GB | Not published on PyPI |
| **Rust** stable toolchains (Linux x64/arm64, Windows GNU + .msi), std source, compiler source | 1.35 GB | SHA-256 from Rust's signed channel manifest |
| **Rust crates**: offline cargo registry, 702 crate versions | 0.11 GB | Feature-aware closure of 46 seeds: tokenizers, safetensors, candle, hf-hub, pyo3, numpy, tokio, serde, clap, reqwest, axum, rusqlite, image… |
| **CUDA 12.8.1** toolkit + driver: Linux runfile 5.38, Windows 3.37 | 8.75 GB | NVIDIA EULA |
| llama.cpp CUDA builds (Windows + Linux, with CUDA runtime) | 1.45 GB | |
| Windows build tools: w64devkit (GCC/make), CMake (+ Linux + source), Ninja, portable Git | 0.26 GB | Builds llama.cpp and Python extensions on Windows without Visual Studio |

Together these cover:
- **Running the models:** llama.cpp (CPU, Vulkan, CUDA), Python transformers, and vLLM for Level C on borrowed GPUs.
- **Converting them:** `convert_hf_to_gguf.py` with gguf, torch, safetensors and sentencepiece.
- **Fine-tuning them:** peft, trl, accelerate, bitsandbytes and deepspeed.
- **Rebuilding everything from source:** every Debian package, plus PyTorch, CPython, Rust, and the source packages for each wheel.

### P2 — Deep technical (1.84 TB)

| Item | Size |
|---|---|
| Level C original weights: DeepSeek-V4.1-Flash 510.3 (MIT), GLM-5.3-Flash 328.4 (MIT), Qwen3.8 27B 55.6, Gemma 4 31B 62.6 | 957 |
| Copernicus DEM GLO-30 (30 m elevation, DEM tiles only) | 589 |
| PubChem Compound SDF | 116.8 |
| TED all talks | 91.2 |
| Debian arm64 binaries (shares the mirror; architecture-independent packages already counted in P1) + arm64 DVD | 55.3 |
| DailyMed OTC labels | 35.6 |
| **Regional reserve** (manual): local equipment manuals, facility inventory, maps, firmware/config backups. **Give it 2+ copies.** | 1,000 reserved |
| Manual: arXiv selected categories (requester-pays S3, roughly $90/TB), PubMed Central OA (bulk path moved) | e |

### P3 — Extension to the 30 TB ceiling

Candidates, ranked at each review:
- full arXiv (~5–8 TB e)
- DeepSeek-V4-Pro (865 m)
- Sentinel-2 cloudless mosaic
- a Python aarch64 wheelhouse
- MIT OCW video
- deeper regional coverage

## 3. Advanced-technology minimum (mandatory)

The goal is to keep the *path* back to each capability, not the capability itself. For semiconductors, the realistic first target is a 1–10 µm process (1970s–80s level).

| Domain | Automated in v5 (measured) | Manual (listed by `status` / MANIFEST.md) |
|---|---|---|
| **Semiconductors** | OSS CAD Suite (Yosys, nextpnr, Verilator, iverilog) 1.35 GB; OpenROAD + flow scripts; KLayout; Magic; Netgen; ngspice; Xyce; IHP SG13G2 and GF180MCU PDKs; open_pdks; ciel; KiCad 0.97 GB | Built sky130 PDK (via ciel); IIC-OSIC-TOOLS container; NIST/SEMATECH e-Handbook (its PDF index moved); **buy 3–5 fabrication / device-physics / thin-film textbooks** |
| **Pharmaceuticals** | ChEMBL 5.8 GB; DailyMed Rx 18.0 GB (+OTC 35.6 in P2); PubChem 116.8 GB (P2); NHS medicines ZIM (P0) | WHO Essential Medicines Lists; WHO International Pharmacopoeia (check bulk-download terms); WHO GMP TRS annexes; FDA Orange Book (TLS check failed from this network); Organic Syntheses (permission); WHO manufacturing manuals |
| **Aerospace** | 6 FAA handbooks (P0); OpenVSP; SU2; OpenRocket; JSBSim; OpenFOAM; FreeCAD 1.34 GB; XFOIL | NACA reports via NTRS API (planned v6 source type); MIL-HDBK-5J (free cancelled edition; MMPDS is a paid budget item) |

## 4. AI strategy with borrowed GPUs

| Level | Hardware needed | Models (all in the vault) | Role |
|---|---|---|---|
| A | Any laptop, CPU only | Gemma 4 12B Q4 | Always-available assistant; ships with P0 |
| B | One 24–32 GB GPU or 64 GB RAM | Qwen3.8 27B (Q4/Q8), Qwen3.6 35B-A3B, Gemma 4 31B | Main working assistant |
| C | Borrowed multi-GPU (≥ 8 × 80 GB) | DeepSeek-V4.1-Flash, GLM-5.3-Flash (original weights; served with the vLLM environment) | Best reasoning, used only when borrowed hardware is available |

**Batch jobs for borrowed GPU time**, ranked by value:
1. Build the **semantic search index** over the vault with the Qwen3 embedding model; store the index.
2. Run **OCR** on scanned PDFs (NACA, FAA, older manuals).
3. **Translate** P0 into the regional survivor languages.
4. Generate **study curricula** and diagnostic decision trees. Store them in `_generated/`, keep provenance, and never mix them with authoritative sources.

**Model refresh rule:** at each review, a new model replaces an old one only if it scores better on a fixed offline test set (`eval/recovery_questions.jsonl`, ~100 questions with verified answers; **to be written before 2027-04**). Keep the previous Level A model for one more cycle.

## 5. Storage layout (cycle 1, current 2 × 10 TB)

| Tier | Logical | Copies | Raw used |
|---|---|---|---|
| P0 | 132.5 GB | 2 disks + 2 × 256 GB USB/SSD via `export` (one kept off-site) | 265 GB on disks |
| P1 | 1.26 TB | 2 | 2.51 TB |
| P2 | 1.84 TB | 1 (+ a 2nd copy for the regional reserve) | 1.84 TB |
| Manifest, lockfiles, cargo index, tools | < 1 GB | Every disk and drive, plus a printed MANIFEST.md | — |
| **Total** | **3.23 TB** | | **4.62 TB of 20 TB (23%)** |

Cycle 1 needs no new disks, only two 256 GB drives for P0. That leaves about 13 TB (after a 15% free-space margin) for P3, so the April 2027 review decides between:
- **(a)** adding a second copy of P2 (+1.84 TB), or
- **(b)** filling P3,

and when the 3rd disk (toward 30 TB) is needed.

**Download time at 1 Gbps** (~100 MB/s sustained): about 9 hours for P0+P1, about 5 more for P2. Debian, the crates and the elevation tiles are ~270k small files, so use `--workers 8`.

## 6. Six-month review procedure

Run every April and October, and record the results in the change log.

1. **Integrity:** `vault.py verify` on every disk and drive; record SMART data, power-on hours and reallocated sectors. Replace any disk that shows errors; `sync` restores the copies.
2. **Restore test:** on a clean offline machine, using P0 media only: open Kiwix, search Wikipedia, run the Level A model with llama.cpp, and open one FAA handbook. Then, using P1:
   - install one package from the Debian mirror
   - install the `core` Python group with `--require-hashes`
   - build one crate offline against the vault registry

   Record the time taken and any failures.
3. **Source refresh:** `discover` (all sources), then `plan --list`; diff against the previous queue (new versions, dead links, size changes). Fix any `FAIL` line in `sources.json`.
4. **Model refresh:** benchmark candidates against the eval set and apply the refresh rule (§4). Check licenses.
5. **Software refresh:** decide whether to move to the next Debian stable / Python minor / CUDA release (a new release means a new, full download of that component).
6. **Advanced-tech minimum:** confirm each row in §3 is present and readable; work through the manual items.
7. **License/legal check** for any new source.
8. **Budget decision:** disks, second copy of P2, and which P3 candidates to add.
9. **Borrowed-GPU log:** what was run, outputs stored, and what comes next.
10. Bump the plan version, add a change-log entry and set the next review date.

## 7. Issues found in civilization_vault_v4 — status in v5

| v4 defect | v5 |
|---|---|
| Kiwix downloads were 1.8 MB `.meta4` XML files saved as `.zim` | **Fixed:** real ZIM URL; SHA-256 taken from the metalink |
| Language filter on `<title>` dropped English Wikipedia, Wikibooks, Gutenberg, Stack Overflow; queued French/Portuguese packs and ~100 TED packs | **Fixed:** explicit allowlist by catalog name + flavour |
| Only 1,200 of 3,656 catalog entries read | **Fixed:** full catalog |
| LLM discovery picked the smallest shard; no vision projector; no original weights | **Fixed:** shard completeness check; projector files and full repositories supported; pinned to commit |
| Models a generation old | **Fixed:** Qwen3.8 / Qwen3.6 / Gemma 4 / DeepSeek-V4.1 / GLM-5.3 |
| No per-tier copies; capacity mode checked only the primary disk; SQLite connection leak | **Fixed:** tier copy policy, `sync` / `export`, per-disk free-space checks, one connection per disk |
| `sources.json` had 2 entries | **Fixed:** 142 sources (127 automated, 15 manual) |

v5 also checks resumed downloads with `If-Range`, so a changed upstream file restarts instead of corrupting. It verifies every file against the publisher's hash where one exists, and `verify` marks bad copies so `sync` repairs them.

## Change log

- **2026-10 (cycle 1):** Plan created. Sizes measured from the Kiwix OPDS catalog (3,656 entries), Hugging Face API, AWS S3 listings (Copernicus), NCBI, the GitHub API, and HEAD checks. v4 defects documented.
- **2026-10 (cycle 1, rev. 2):** v5 implemented and tested end to end on 2,137 real files (download, hash verification, sync, corruption repair, export). Added the full software stack (§2a): Debian 13 mirror with source, Python 3.13 wheelhouses (Linux CUDA + Windows) with source packages, Rust toolchains + crate registry, CUDA 12.8.1, Windows build tools, PyTorch source. Every tier re-measured: 3.23 TB logical / 4.62 TB raw (was ~8 TB estimated). Debian came out far smaller than estimated (243 GB vs ~1 TB) and moved from P2 to P1; Copernicus DEM tiles only (GLO-90 71 GB, GLO-30 589 GB).
