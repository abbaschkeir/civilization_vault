# Civilization Vault — Master Plan

**Plan version:** 2026-10 (cycle 1) · **Next review:** 2027-04 · **Then:** every 6 months (April / October)

This file is the fixed reference for the project. Each review revalidates it and updates the numbers in place. Record what changed in the change log at the bottom.

---

## 1. Constraints and decisions

| Item | Decision |
|---|---|
| Budget | Low now; revisited at every 6-month review |
| Storage ceiling | **30 TB raw** acceptable over the life of the plan |
| Current hardware | 2 × 10 TB disks (from v4); enough for cycle 1 (see §5) |
| GPUs | Not owned. Borrowed from other projects/companies for batch jobs (§4) |
| Scope | Industrial-civilization recovery across the 3 scenarios (near-zero tech, 90–99% population loss, systems collapse) |
| Advanced tech | Semiconductors, pharma, aerospace: **a defined minimum is mandatory** (§3); depth beyond that is optional |
| AI role | Teaches, searches, translates and explains. It never replaces exact data: doses, specs, tolerances, firmware or standards |

## 2. Tiers (measured sizes, October 2026)

Sizes are decimal GB/TB. **m** = measured from the source catalog or API on 2026-10-29. **e** = estimate that must be measured at the next review.

### P0 — Bootstrap seed · ≈ 140 GB · copies: 3 disks + 2 small offline drives

Must be usable on a weak laptop with no GPU and no internet.

| Item | Size |
|---|---|
| Kiwix: Wikipedia EN nopic (52.7), MDWiki (2.3), WikiMed (1.9), Wikibooks (6.2), Wikiversity (2.5), Wiktionary nopic (9.2) | 74.8 m |
| Kiwix: LibreTexts bio/chem/med/geo/eng/phys/math/stats/workforce/K-12 | 10.0 m |
| Kiwix: iFixit EN, Appropedia, energypedia, CD3WD, Post-Disaster, LowTech, water, food, knots, military medicine, MedlinePlus, NHS medicines, CDC travel, PhET | 9.4 m |
| Kiwix: StackExchange: electronics, physics, chemistry, biology, engineering, DIY, mechanics, gardening, ham, woodworking, aviation, space, medical sciences, earth science, cooking, 3D printing, Arduino | 12.5 m |
| AI: Gemma 4 12B Q4_K_M + mmproj (Apache-2.0); runs on CPU | 7.3 m |
| AI: Qwen3.8-27B UD-Q4_K_M + mmproj (Apache-2.0); 24 GB GPU or 32 GB+ RAM | 17.4 m |
| Runtimes: llama.cpp source + Windows/Linux binaries, Kiwix readers (desktop, kiwix-serve), installers | ~2 e |
| Advanced-tech core handbooks (the P0 rows of §3) | ~5 e |

### P1 — Recovery library · ≈ 1.4 TB · copies: 2

| Item | Size |
|---|---|
| Kiwix: Wikipedia EN maxi (with images) | 127.4 m |
| Kiwix: Project Gutenberg EN | 221.3 m |
| Kiwix: Khan Academy EN (**dated 2023-03; check for refresh**) | 180.0 m |
| Kiwix: CrashCourse | 23.0 m |
| Kiwix: Stack Overflow (114.9), Math, TeX, SuperUser, AskUbuntu, ServerFault, Unix SE | 136.6 m |
| Kiwix: Wikisource maxi, Wikivoyage nopic | 8.9 m |
| Wikipedia EN raw XML dump (re-indexing / AI retrieval source) | 26.9 m |
| OpenStreetMap planet PBF | 95.5 m |
| Copernicus DEM GLO-90 (global elevation, 90 m) | 185 m |
| AI: Qwen3.6-35B-A3B UD-Q4_K_M + mmproj (MoE; fast on CPU+RAM) | 23.0 m |
| AI: Qwen3.8-27B Q8_0 (higher-fidelity copy of P0 model) | 29.0 m |
| AI: Gemma 4 31B Q4 GGUF (independent model family) | ~19 e |
| Advanced-tech minimum (P1 rows of §3) | ~150 e |
| Debian stable install ISO/BD set (amd64 + arm64) | ~150 e |

### P2 — Deep technical · ≈ 6.5 TB · copies: 1 (until budget allows a 2nd)

These sources can still be downloaded again while the internet exists, so for now a single copy is an acceptable risk.

| Item | Size |
|---|---|
| Frontier weights for borrowed GPUs: DeepSeek-V4.1-Flash (MIT) 510, GLM-5.3-Flash (MIT) 328, Qwen3.8-27B original 56, Gemma 4 31B original 63 | 957 m |
| Copernicus DEM GLO-30 (global elevation, 30 m) | 1,384 m |
| Debian full mirror amd64 + source (every package and its source) | ~1,050 m (debian.org mirror-size page) |
| PubChem Compound SDF | 111 m |
| arXiv selected categories (physics.app-ph, cond-mat, eess, cs.AR, q-bio, etc.); **requester-pays S3 at roughly $0.09/GB** | ~1,000 e |
| PubMed Central Open Access XML (PDF bulk discontinued Aug 2026) | ~400 e |
| NASA NTRS: broader NASA reports beyond the P1 NACA set | ~500 e |
| TED all talks | 91 m |
| **Regional reserve**: local equipment manuals, facility inventory, maps, firmware/config backups | 1,000 (reserved) |

### P3 — Extension to the 30 TB ceiling · filled only after review

Candidates, ranked at each review:
- full arXiv (~5–8 TB e)
- DeepSeek-V4-Pro (865 m)
- Sentinel-2 cloudless mosaic
- curated PyPI / crates / npm
- MIT OCW video
- Debian arm64 full
- deeper regional coverage

**Cumulative logical size:** P0 0.14 TB → P1 ~1.5 TB → P2 ~8 TB → P3 up to ~20 TB.

## 3. Advanced-technology minimum (mandatory)

The goal is to keep the *path* back to each capability, not the capability itself. For semiconductors, the realistic first target is a 1–10 µm process (1970s–80s level), not a modern node.

| Domain | P0 (core, ~5 GB in total) | P1 minimum | Notes |
|---|---|---|---|
| **Semiconductors** (~60 GB e) | Device-physics and process overview pages; NIST/SEMATECH e-Handbook of Statistical Methods (process control) | Open PDKs: IHP SG13G2 (0.5 m), GF180MCU, SkyWater sky130 (built via `ciel`, size e). EDA source + binaries: Yosys, OpenROAD (1.0 m), OpenROAD-flow-scripts (0.9 m), Magic, KLayout (0.4 m), ngspice, Xyce, Netgen, Verilator, KiCad (4.5 m). IIC-OSIC-TOOLS container image. MIT OCW microfabrication course packs | The process-recipe and fab-equipment knowledge is mostly copyrighted textbooks: **buy** 3–5 core texts (fab processing, device physics, vacuum/thin-film) in print + ebook. Budget item, not a download |
| **Pharmaceuticals** (~40 GB e, +111 GB PubChem in P2) | WHO Model List of Essential Medicines (adult + children); WHO International Pharmacopoeia; WHO GMP (TRS series); NHS medicines A–Z (already P0) | DailyMed SPL Rx+OTC (~16 e); FDA Orange Book data; ChEMBL SQLite (~5 e); Organic Syntheses procedures (**bulk permission needed**); WHO manuals on sterile production, fermentation and vaccine cold chain; open reaction datasets (USPTO extract, ORD) | The International Pharmacopoeia is free to read online, but the terms for bulk download must be confirmed |
| **Aerospace** (~60 GB e) | FAA handbooks: Pilot's Handbook of Aeronautical Knowledge, AMT General/Airframe/Powerplant, AC 43.13-1B, Weight & Balance (public domain, ~1 GB) | NACA Technical Reports 1915–1958 via NTRS API (e); MIL-HDBK-5J (metallic material properties); NASA SP series (selected); tools: OpenVSP (0.5 m), SU2 (1.0 m), OpenRocket (0.5 m), JSBSim, OpenFOAM, FreeCAD (3.0 m), XFOIL | MMPDS (the successor to MIL-HDBK-5) is paid; MIL-HDBK-5J is the free baseline |

## 4. AI strategy with borrowed GPUs

Storing a model is not the same as being able to run it, so models are stored at three levels:

| Level | Hardware needed | Models | Role |
|---|---|---|---|
| A | Any laptop, CPU only | Gemma 4 12B Q4 | Always-available assistant; ships with P0 |
| B | One 24–32 GB GPU or 64 GB RAM | Qwen3.8-27B, Qwen3.6-35B-A3B, Gemma 4 31B | Main working assistant |
| C | Borrowed multi-GPU (≥ 8 × 80 GB) | DeepSeek-V4.1-Flash, GLM-5.3-Flash (original weights) | Best reasoning, used only when borrowed hardware is available |

**Batch jobs for borrowed GPU time**, ranked by value. These are worth more than chat time:
1. Build a **semantic search index** (embeddings) over the whole vault. Store the index and the embedding model with it (P1).
2. Run **OCR** on scanned PDFs (NACA, FAA, older manuals) to produce searchable text.
3. **Translate** P0 into the 5–10 most likely survivor languages for your region.
4. Generate **study curricula** and diagnostic decision trees from P0/P1 sources. Store them in `_generated/`, keep provenance, and **never** mix them with authoritative sources.

**Model refresh rule:** at each review, a new model replaces an old one only if it scores better on the fixed offline test set (`eval/recovery_questions.jsonl`, ~100 questions with verified answers). Keep the previous Level A model for one more cycle.

## 5. Storage layout (cycle 1, current 2 × 10 TB)

| Tier | Logical | Copies | Raw used |
|---|---|---|---|
| P0 | 0.14 TB | 2 disks + 2 × 256 GB USB/SSD (one kept off-site) | 0.28 TB on disks |
| P1 | 1.4 TB | 2 (one per disk) | 2.8 TB |
| P2 | 6.5 TB | 1 (spread across both disks by free space) | 6.5 TB |
| Manifest (URL, size, SHA-256, license, date) | < 1 GB | Every disk, every USB drive, plus a printed index | — |
| **Total** | | | **≈ 9.6 TB of 20 TB (48%)** |

Cycle 1 needs no new disks, only two cheap 256 GB drives for P0. The next purchase (a 3rd disk of 10–12 TB, total ≈ 30 TB raw) is decided in 2027-04 and enables a second copy of P2.

## 6. Six-month review procedure

Run every April and October, and record the results in the change log.

1. **Integrity:** run `verify` on every disk and drive; record SMART data, power-on hours and reallocated sectors. Replace any disk that shows errors.
2. **Restore test:** on a clean offline machine, using P0 media only: open Kiwix, search Wikipedia, run the Level A model, and open one handbook PDF. Record the time taken and any failures.
3. **Source refresh:** run `discover`, then diff the queue against the last manifest for new versions, dead URLs and size changes. Update every **e** in §2 to **m**.
4. **Model refresh:** benchmark candidates against the eval set and apply the refresh rule (§4). Check licenses.
5. **Advanced-tech minimum:** confirm each row in §3 is present and readable; add whatever was deferred.
6. **License/legal check** for any new source.
7. **Budget decision:** additional disks, redundancy level for P2, and which P3 candidates to add.
8. **Borrowed-GPU log:** what was run, outputs stored, and what comes next.
9. Bump the plan version, add a change-log entry and set the next review date.

## 7. Known issues in civilization_vault_v4 (fix before the next download run)

Verified 2026-10-29 by running v4's own `kiwix_discover` against the live Kiwix catalog:

1. **Every Kiwix URL points to a `.zim.meta4` file.** The code downloads a ~1.8 MB metalink XML file and saves it as `.zim`. Fix: strip `.meta4` from the URL, read the SHA-256 from the metalink, and set `expected_bytes` from the OPDS `length`.
2. **The language filter checks `<title>`, but the title is just "Wikipedia".** As a result, English Wikipedia, Wikibooks, Gutenberg and Stack Overflow are **never queued**, while French Khan Academy, French/Portuguese iFixit and hundreds of TED topic packs are. Fix: replace keyword matching with an explicit allowlist of `<name>` + `<flavour>` taken from §2.
3. **`count=1200` reads only the first 1,200 of 3,656 catalog entries.**
4. **LLM discovery picks the *smallest* matching GGUF file.** For split models this is one shard, which gives an unusable model. It also skips `mmproj` (needed for vision) and cannot fetch original safetensors weights (needed for Level C).
5. **Model list is a generation old:** Qwen3 / Gemma 3. Replace with the models in §4.
6. **Neither mode can do per-tier copies.** `copies` mode puts everything on both disks, and `capacity` mode puts everything on one. A tier-aware placement is needed (P0/P1 on both disks, P2 by free space). In `capacity` mode the loop also checks free space only on the primary disk, and opens a new SQLite connection for every secondary-disk file.
7. **No sources yet for §3**, the Debian/OSM/DEM bulk sets, or the Wikipedia XML dump; `sources.json` has 2 entries.

## Change log

- **2026-10 (cycle 1):** Plan created. Sizes measured from the Kiwix OPDS catalog (3,656 entries), Hugging Face API, AWS S3 listings (Copernicus), the NCBI PubChem FTP listing, the GitHub API, and HEAD requests (OSM, Wikimedia dumps). v4 discovery defects documented (§7).
