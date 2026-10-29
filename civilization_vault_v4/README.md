# Civilization Vault v0.4 — AI-first, 2 × 10 TB, six-month capacity plan

**Critical change:** LLMs are Priority 0. `discover` now queries the Hugging Face repository API for a selected quantized GGUF from each entry in `llm_models.json`, records reported size and available upstream SHA-256, and adds the model to the regular resumable/verified download queue. This does not download full model repositories or every quantization.

**Selected model set** (subject to repository availability): Qwen3 8B Q4_K_M (small offline assistant), Qwen3 32B Q4_K_M (higher capability; approximately 19.8 GB model), and Gemma 3 27B Q4_K_M (optional independent multimodal model; ~16.5 GB weights). The program selects filenames dynamically from model repositories. Model support and licenses should be reviewed before use. The 27B vision model may need additional supporting components; this downloader does not guarantee complete multimodal runtime setup. Qwen GGUF weights and model metadata are not replacements for archiving llama.cpp executables/source and offline Python packages.

**AI-first acquisition order:** Priority 0 LLMs plus foundational Kiwix sources first, then Priority 1 additional models and deeper technical collections. The rest of the catalog still needs curation; *this release will not fill two 10 TB disks*.

**Practical hardware:** You can preserve model weights today without being able to run them today. Store a small model suitable for typical desktop hardware and larger models for later workstations. RAM/VRAM and compute requirements depend on context length and acceleration method; disk size alone does not determine usability.

## Commands — PowerShell

```powershell
py -3 vault.py --root "E:/CIVILIZATION_VAULT" discover
py -3 vault.py --root "E:/CIVILIZATION_VAULT" plan --max-priority 1
py -3 vault.py --root "E:/CIVILIZATION_VAULT" --secondary "F:/CIVILIZATION_VAULT" --mode capacity run --hours 48 --workers 2 --reserve-gb 750 --max-file-gb 350 --max-priority 2
py -3 vault.py --root "E:/CIVILIZATION_VAULT" --secondary "F:/CIVILIZATION_VAULT" --mode capacity verify
```

Models require online model discovery during `discover`; re-run it before the fast network period. Use `--no-llms` only to deliberately exclude AI downloads. `--no-kiwix` excludes Kiwix discovery. If repositories are unreachable, failures are printed and the other downloads remain available.

**Six-month policy:** capacity-first, two independent 10 TB disks, no RAID and no redundancy until planned review. Maintain an extra copy of the highest-priority bootstrapping documents and the small model where feasible. Archive only files whose licenses permit your intended use. Large model checksums are verified after download; schedule periodic rechecks outside your fastest transfer window.

---

# Civilization Vault v0.3.1 — six-month capacity-first plan

**Temporary policy (October 2026–April 2027):** Two *separate* 10 TB disks, `--mode capacity`, approximately 16–18 TB combined target, no RAID and no full redundant copy. Revisit redundancy in six months. The risk of losing data on drive failure is accepted temporarily; keep a separate copy of the 50–100 GB essential bootstrap collection if possible.

## Quick launch: Windows PowerShell

```powershell
py -3 vault.py --root "E:/CIVILIZATION_VAULT" discover
py -3 vault.py --root "E:/CIVILIZATION_VAULT" plan
py -3 vault.py --root "E:/CIVILIZATION_VAULT" --secondary "F:/CIVILIZATION_VAULT" --mode capacity run --hours 48 --workers 2 --reserve-gb 750 --max-file-gb 350
py -3 vault.py --root "E:/CIVILIZATION_VAULT" --secondary "F:/CIVILIZATION_VAULT" --mode capacity verify
```

**Important:** `--mode capacity` balances by queue position, **not bytes**, and may fill one disk before the other. The source catalog is a starter; it does **not** presently contain 16 TB of verified downloadable sources. The download window cannot be fully utilized until the catalog is expanded. Do not switch the existing archive from capacity mode to copies mode without a verified migration.

## Review in April 2027

1. Inventory actual archived bytes and verify checksums on both drives.
2. Purchase independent destination storage; create verified backup copies **before** reformatting or migrating original drives.
3. Decide whether to convert to a mirrored NAS or keep independently stored archive copies.

---

# Civilization Vault v0.3 — two 10 TB disks

Python 3.10+; standard library; no dependencies. Revised from v0.2 to separate **two-copy preservation** from **two-disk capacity**. This is a starter downloader, **not a comprehensive automated mirror of all civilization-recovery sources**.

## First: choose the mode

- **`copies` (default, recommended):** Download files to Disk A, then run `sync` to copy/verify them on Disk B. **~10 TB logical maximum** with two independent copies, but plan for **8–9 TB**, leaving a free-space margin. Copying takes extra time; do not assume the second disk is backed up until `sync` succeeds.
- **`capacity` (explicit):** Split the queue across A and B. **~20 TB raw**, aim for **16–18 TB** combined. **Zero redundancy**: a disk failure loses its assigned files. The backup/sync command will refuse to run in this mode. Selection is deterministic by queue index and is NOT capacity-balanced: inspect free space on both disks.
- **No RAID 10:** Two disks cannot provide RAID 10. RAID 1 mirroring gives one disk's capacity and redundancy; two standalone USB disks with a verified file copy are simpler for the 48-hour window.

## Quick start — Windows PowerShell

Replace `E:` and `F:` with **different actual physical disk drives**. Both disks should be NTFS or another filesystem supporting files larger than 4 GB; do not use FAT32.

```powershell
py -3 vault.py --root "E:/CIVILIZATION_VAULT" discover
py -3 vault.py --root "E:/CIVILIZATION_VAULT" plan --max-priority 2
py -3 vault.py --root "E:/CIVILIZATION_VAULT" --secondary "F:/CIVILIZATION_VAULT" --mode copies run --hours 48 --workers 2 --reserve-gb 750 --max-file-gb 350
py -3 vault.py --root "E:/CIVILIZATION_VAULT" --secondary "F:/CIVILIZATION_VAULT" --mode copies sync --reserve-gb 750
py -3 vault.py --root "E:/CIVILIZATION_VAULT" --secondary "F:/CIVILIZATION_VAULT" verify
```

`sync` runs separately and **may not finish within the 48-hour window**. You can run it once early, and again as downloads progress or after the fast network window. It only copies completed, checksummed files; partial transfers are resumed during later `run` commands. Do not delete the primary until the full backup has been verified.

### Capacity-first mode (higher risk)

```powershell
py -3 vault.py --root "E:/CIVILIZATION_VAULT" discover
py -3 vault.py --root "E:/CIVILIZATION_VAULT" --secondary "F:/CIVILIZATION_VAULT" --mode capacity run --hours 48 --workers 2 --reserve-gb 750 --max-file-gb 350
py -3 vault.py --root "E:/CIVILIZATION_VAULT" --secondary "F:/CIVILIZATION_VAULT" --mode capacity verify
```

The queue lives on Disk A under `_metadata/queue.json`. Each drive has its own `_metadata/files.sqlite3`. Do **not switch modes in the middle of acquisition** without rebuilding and manually checking the archive layout. The software does not automatically redistribute files to balance disks, and will stop writing a disk as its safety margin approaches.

## What is automated

- Direct, approved HTTPS file URLs specified in `sources.json`.
- Selected Kiwix ZIM discovery from the public OPDS catalog (bounded catalog listing, selection is incomplete).
- Resume where servers support HTTP Range; retries; partial file retention.
- Basic free-space reserve, 350 GB default per-file cap, HTTPS redirect checks.
- SHA-256 checksums recorded after downloads, explicit `verify`, verified copy `sync`.

**What is NOT automated:** a complete WHO/FAO/manuals/science mirror, selecting offline AI weights, acquiring private factory manuals, catalog pagination beyond the requested window, or restoring the whole archive automatically after disk failure. These require verified source URLs, permission checks, and curation. The previous v0.2 catalog only had two static direct URLs plus Kiwix discovery, and v0.3 preserves that limitation. See `SOURCE_ROADMAP.md`.

## 48-hour bandwidth math

1 Gbps = **125 MB/s theoretical**, equivalent to 21.6 TB in 48 hours. Sustained 70–100 MB/s delivers **12.1–17.3 TB** if download sources keep up and the disks are capable. With two 10 TB drives in `copies` mode, only 8–9 TB unique data comfortably fits, and replication adds separate disk-write time. In `capacity` mode you could fit 16–18 TB unique data but risk losing half with one drive failure.

Keep no more than ~2 concurrent large downloads per HDD initially, avoid simultaneous heavy checksum verification during the fastest download period, cool/ventilate the drives, and connect them to independent USB 3.x ports. USB drives may throttle thermally. Avoid a power interruption and use a UPS if possible.

## Check before the high-speed window

1. Run discovery and review `_metadata/queue.json` to verify file URLs and sizes.
2. Confirm both disks have their expected free space and are genuinely separate devices.
3. Do a short download trial; test resume by stopping and restarting.
4. Test copying and verifying 1–2 files with `sync`.
5. Preserve the most critical initial 50–100 GB on one more device if possible.

Note: source servers can fail or change. Public catalog metadata is not necessarily an approved bulk redistribution license. Respect rate limits, content permissions and local laws.
