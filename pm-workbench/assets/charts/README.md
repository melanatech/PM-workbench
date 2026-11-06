# Charts

Shared chart themes and helpers for internal HTML and teammate HTML. User-facing prototypes stay on the company component system and do not load this folder.

## Vendored library

| | |
|---|---|
| File | `echarts.min.js` |
| Package | `echarts` |
| Version | 6.1.0 |
| License | Apache-2.0 |
| Upstream | https://echarts.apache.org |
| Source tarball | https://registry.npmjs.org/echarts/-/echarts-6.1.0.tgz |
| Path in tarball | `package/dist/echarts.min.js` |

The minified file is the full build (funnel, heatmap, boxplot, and sankey included). License text from that package is in `LICENSE-echarts.txt`.

## Themes

Token files live in `themes/`. Presets: `neutral`, `high-contrast`, `print`, `dark`. See `THEMING.md` for the palette choice.

Regenerate from the kit root:

```bash
python3 scripts/make_chart_theme.py neutral
python3 scripts/make_chart_theme.py assets/charts/themes/high-contrast.json
```

The script checks two things, then writes `generated/<name>.theme.js` and `generated/<name>.altair.py`:

- Text on background, WCAG relative luminance, ratio at least 4.5.
- First four categorical colors pairwise at least 80 apart in 8-bit Euclidean RGB.

Exit 2 means a failed check or a bad file. Nothing is written for that theme.

A theme JSON that lives outside this kit writes its generated files to `generated/` next to that theme's `themes/` folder, so a local brand file does not land in this folder. `--out` overrides the directory.

## Helpers

`wb-charts.js` draws into a container with the local ECharts build. Load `echarts.min.js`, then the theme script, then `wb-charts.js`.

Each helper takes a container (element or id), a data object, a theme name, and a caption object with `population`, `window`, and `denominator`. The caption is rendered under the chart. Helpers: `barCompare`, `lineSeries` (optional `bands`), `funnel`, `heatmap`, `distribution` (boxplot), `sankey`.

`gallery.html` loads the local build only. Open it from this folder. Sample categories are the letters A to D.

Which helper to use, and the rules (one message, no dual axes, no pie charts), are in `reference/templates/chart-usage.md`.
