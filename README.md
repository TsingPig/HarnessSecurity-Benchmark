# HarnessSecurity-Bench project page

A minimal, illustrated page for the manuscript. It introduces the study,
benchmark, and results with short text and four prominent paper visuals.
Figures and tables flow directly through the page. A collapsed resource list
provides every Figure 1–6 and Table 4–8 without a selector or catalog interface.
Scientific terms, numbers, and figure captions come from the manuscript.

## Languages

The header's **EN / 中文** buttons switch page text, figure captions, image alt
text, resource links, and accessibility labels without reloading the page.
The initial language is English; a visitor's selection is remembered locally
when browser storage is available. Original paper figures and PDFs retain their
English text. English copy is maintained in `index.html` and the manuscript
manifest; Chinese copy is maintained in `data/translations.zh.json`.

Translation glossary:

| Manuscript term | Chinese wording |
|---|---|
| Coding agent | 编程智能体 |
| Harness | harness (retained in English) |
| Security mechanism | 安全机制 |
| Attack surface | 攻击面 |
| Task utility | 任务效用 |
| Attack effect | 攻击效果 |
| Deterministic oracle | 确定性判定器 |
| Command allowlisting / denylisting | 命令允许列表 / 命令拒绝列表 |

Translation scope:

- The 400 entries are harness–mechanism combinations, rather than 400 harnesses;
  confirmed absence and unresolved evidence remain distinct.
- Task utility and attack effects use separate deterministic oracles. Neither
  outcome is presented as a substitute for the other.
- The mechanism comparisons preserve both security effects and utility losses
  or gains. Release preparation is not described as a completed data release.

## Assets

From the study repository root, run `python scripts/site/sync_paper_pdfs.py`
after compiling the paper into `.build/arxiv/`. The script requires `pypdf`. SVG export also requires `pdftocairo`;
use `--pdftocairo <path>` if it is not on PATH or in the standard local MiKTeX
installation. The script copies the full paper and five original
figure PDFs byte for byte, and extracts Figure 6 and Tables 4–8 without
rasterization. `data/paper-assets.json` records source paths, manuscript and
asset hashes, captions, extraction regions, and SVG preview hashes. Crops follow
invisible shipout anchors in the manuscript, so they remain aligned after
two-column reflow. Review the extracted regions after manuscript layout changes. Existing raster icons in original figures
remain unchanged; text, table rules, and plotted paths remain vector content.

The page displays SVG illustrations exported directly from the PDFs using
Poppler. They scale with the page and have no viewer controls, frames, or internal
scrollbars. Vector paths and glyphs remain vector content, and existing raster
icons are preserved. Every visual retains a direct link to its original PDF.

After exporting, run `npm ci --prefix scripts/site` and
`npm run optimize --prefix scripts/site` from the study repository root.
The optimizer removes redundant vector markup and shares identical embedded
images without resizing or re-encoding their pixels. It retains the original
viewBox and uses five-decimal precision for path operations. The current four
page illustrations total 3.82 MB, reduced from 5.90 MB (35.2%). Their SVG URLs
include content hashes to refresh changed previews. The hero image is preloaded
with high fetch priority; lower images use lazy loading and asynchronous decoding.
Original PDFs retain their source quality.


## Dataset release

The dataset remains in preparation. `data/catalog.json` retains four empty
collections for the future verified release. The page shows one concise release
statement. No raw benchmark data, traces, credentials, or private run files are
bundled with the site.

## Local preview

Run `python -m http.server 8765 --bind 127.0.0.1 --directory docs` from the study
repository root, then open <http://127.0.0.1:8765/>. The static page requires no
build process or external web dependencies.

## GitHub Pages

The publishing repository is <https://github.com/TsingPig/HarnessSecurity-Benchmark>.
Its Pages address is <https://tsingpig.github.io/HarnessSecurity-Benchmark/>.
The `main` branch contains only `tasks/` and the concise English README. The
independent `gh-pages` branch contains the static website at its root. Pages
publishes from `gh-pages` automatically after a push.

The study repository keeps the preparation source and sync script. To update the
live page, regenerate the assets here, copy the contents of `docs/` to the root of
the publishing repository's `gh-pages` branch, and push that branch. Verify the
public page before citing a release.

Official Pages documentation:
<https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site>.
