# Civilization Vault v0.5

Downloads the allowlist in `sources.json` onto several disks, by tier, with verified copies. The plan this implements, including tier sizes, copy policy and the 6-month review, is in [`../VAULT_PLAN.md`](../VAULT_PLAN.md).

Python 3.11+, standard library only. `discover` also calls `pip` (any recent version) to resolve the Python package sets.

## Commands (PowerShell; use your real drive letters)

```powershell
$V = 'py -3 vault.py --disk E:/CIVILIZATION_VAULT --disk F:/CIVILIZATION_VAULT'

iex "$V discover"                              # resolve every source; needs internet; ~15-30 min
iex "$V plan --list"                           # size per tier and per source vs. free space
iex "$V run --hours 48 --workers 4 --quiet"    # download P0..P2, one copy each, resumable
iex "$V sync"                                  # make the extra copies each tier requires (P0/P1: 2)
iex "$V verify"                                # re-hash everything; marks bad files for repair
iex "$V export --dest G:/VAULT_P0 --max-tier 0" # P0 seed onto a USB drive (repeat for the 2nd drive)
iex "$V status"                                # completeness, copies, errors, manual items
```

- **Order during a fast-network window:** `discover` → `run` (downloads only) → `sync` later. Copying between local disks needs no internet.
- **Many small files** (Debian, crates, DEM tiles): use `--workers 8`.
- **Testing:** `--only REGEX` downloads matching items only, and `--allow-same-device` permits two roots on one disk.
- **Tokens (optional):** `GITHUB_TOKEN` raises GitHub's limit of 60 API requests/hour. `HF_TOKEN` is only needed for gated models. Neither token is ever sent to a redirect target.

## What is downloaded

| Type | What it covers | Integrity |
|---|---|---|
| `kiwix` | ZIMs chosen by exact catalog name + flavour, newest date | SHA-256 from the Kiwix metalink |
| `hf` | Model files from Hugging Face, pinned to the commit at discover time; all shards required | SHA-256 (LFS) |
| `debian` | A working apt mirror: signed Release files, indices, every listed `.deb` and source file | Indices checked against Release; every file SHA-256 |
| `pypi` | pip resolves the full dependency set for each target platform; wheels + sdists + a `--require-hashes` lockfile | SHA-256 from PyPI |
| `rust_toolchain` | Rust installers per target, std source, compiler source | SHA-256 from the channel manifest |
| `crates` | Feature-aware dependency closure of the seed crates, written as an offline cargo `local-registry` | SHA-256 from the crates.io index |
| `github_release` / `github_source` | Release assets and source tarballs pinned to a tag or commit | Asset digest where GitHub publishes one; otherwise hashed at download |
| `http_index`, `url`, `s3` | Directory listings (optionally the newest matching version), direct links, public S3 buckets | Published SHA256SUMS / S3 MD5 where available |
| `manual` | Items that need a human: purchases, permission requests, tools with no stable link | Listed in `status` and MANIFEST.md |

Files without a published hash are still SHA-256-hashed at download, and every later `verify` and copy is checked against that hash.

## Using the software archive offline

These files are written next to the downloads by `discover`:

- **Debian** (`06_COMPUTING/debian/README-*.txt`): an apt `sources.list` line for the mirror. It needs the `debian-archive-keyring` package, which is on the DVD.
- **Python** (`06_COMPUTING/python_wheelhouse/requirements-*.txt`):
  `pip install --no-index --find-links wheels --require-hashes -r requirements-python_llm_linux.txt`.
  Source-only packages (llama-cpp-python, deepspeed, flash-attn) are built from `sdists/` with the toolchains in the vault.
- **Rust** (`06_COMPUTING/rust_crates/cargo-config.toml`): copy it into `~/.cargo/config.toml` and fix the path. If a project's `Cargo.lock` pins versions that are not in the vault, run `cargo generate-lockfile --offline`.
- **llama.cpp:**
  - Windows: use the prebuilt zips, or build from source with w64devkit + CMake.
  - Linux: build with `apt install build-essential cmake` from the mirror. For CUDA builds, use the CUDA runfile or Debian's `nvidia-cuda-toolkit`.

## Disk layout

```
<disk>/
  _metadata/queue.json, vault5.sqlite3   queue and this disk's verified-file records
  _tools/                                this program, sources.json, README, VAULT_PLAN.md
  MANIFEST.md / MANIFEST.tsv             printable index; full file list with SHA-256 and origin
  00_BOOTSTRAP/ ... 13_REGIONAL/         content: <category>/<source>/<files>
```

v5 uses its own database file and does not adopt v4 downloads. Most v4 Kiwix "ZIMs" were 1.8 MB metalink files, so start v5 on a fresh root.
