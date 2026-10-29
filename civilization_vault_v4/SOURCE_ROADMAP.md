# AI-first source roadmap — v0.4

## Priority 0: Offline AI, needed before the high-speed connection ends

- Qwen3 8B Q4_K_M GGUF (small, locally runnable assistant)
- Qwen3 32B Q4_K_M GGUF (higher-capacity reasoning/coding)
- Retain model source repository name, revision, README, license, tokenizer and runtime instructions. GGUF typically embeds tokenizer data, but additional artifacts may be required.
- Preserve independent inference runtime: llama.cpp release binary for your operating system, plus source code, build toolchain/installers and SHA-256 manifest. **Runtime acquisition is not yet automated in this version.**

## Priority 1: Model diversity

- Gemma 3 27B Q4_K_M GGUF; review Gemma terms, vision support files, compatibility and hardware requirements.
- Later add specialized coding, multilingual translation, speech recognition/OCR and vision models only after verifying representative offline tests.

## Priority 2: Irreplaceable technical sources

- Medical standards/clinical guidance, verified material property tables, machining and repair manuals, industrial controls, agriculture, chemistry and water treatment, plus core reference texts.
- Preserve locally relevant equipment manuals and compatible drivers and firmware under applicable licensing/authorization.

## Lower priority

- Extra quantizations, duplicate fine-tunes, benchmark-only models, giant models that cannot run on foreseeable offline hardware, large training corpora, raw media, and broad historical mirrors.

## Important limitations

The discoverer currently downloads *model weights*, not a complete plug-and-play offline AI workstation. Store the runtime and installer dependencies separately, along with a pre-tested small model. The general educational source list is still incomplete; treat this as an incremental working acquisition system rather than a finished 16 TB catalog.

---

# Content-acquisition roadmap (not yet automated)

The **queue is currently much smaller than 10 TB**. The goal is quality, not filling the disks indiscriminately. The live program downloads only URLs included by the static catalog and its bounded Kiwix selection. Below are official **discovery pages** to use when adding explicitly permitted downloadable files to `sources.json`.

| Priority | Recovery domain | Official discovery entry | Notes |
|---|---|---|---|
| P0 | Offline general knowledge | https://library.kiwix.org/ | Choose English ZIM packs; confirm sizes |
| P0 | Open textbooks | https://openstax.org/subjects | Add authorized direct PDF links |
| P0 | First aid, medicine, public health | https://www.who.int/publications | Review publication license |
| P0 | Agriculture and food security | https://www.fao.org/publications | Review download conditions |
| P1 | Engineering and machinery | https://ntrs.nasa.gov/ | Public NASA reports, selectively |
| P1 | Energy and electricity | https://www.energy.gov/ | Public technical manuals and reports |
| P1 | US geological resources | https://www.usgs.gov/products/data | Selected useful geography |
| P1 | Medical research | https://pmc.ncbi.nlm.nih.gov/tools/openftlist/ | Respect article licenses and bulk access rules |
| P2 | Open source and compilers | https://www.softwareheritage.org/ | Curate code; do not mirror full multi-PB archive |
| P2 | Offline AI | https://huggingface.co/models | Select compatible models and their licenses; use official download tool |
| P2 | Global maps | https://download.geofabrik.de/ | Regional OSM extract downloads |
| P3 | Books and literature | https://www.gutenberg.org/policy/robot_access.html | Use approved mirrors / harvesting, do not scrape ordinary pages |

Add a JSON object in `sources.json` with `id`, `priority` (0–4), `category`, `filename`, `title`, `url` (direct HTTPS link), `origin`; optionally include an authoritative `sha256`. Rerun `discover` to refresh the queue. Ensure that filenames and categories are safe and unique.
