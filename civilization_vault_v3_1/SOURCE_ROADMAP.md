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
