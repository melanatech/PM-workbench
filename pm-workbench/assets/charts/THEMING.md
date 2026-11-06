# Chart theming notes

Short note on how common chart systems pick colors, and the approach this folder uses.

## What other systems do

Apache ECharts publishes a theme builder. It writes a script that calls `echarts.registerTheme` with a theme object: a categorical `color` list, `backgroundColor`, text, axis, legend, tooltip, and `visualMap`. This folder generates that shape.

Vega-Lite defaults to the `category10` scheme and a spare frame: one color encoding, axis titles, and a view with little extra chrome. Observable Plot is similar. Both assume one series color unless you pass a scheme. Neither is a token file you can share with a second library.

Datawrapper defaults use one accent, gray for the other series, direct labels, and a description under the chart. Its guidance tells authors to skip pie charts and dual axes.

The Financial Times visual vocabulary maps a question to a chart type and keeps one message on the chart. Economist graphics use one highlight color and gray for the rest, with the source named on the figure. Both traditions avoid dual axes.

IBM Carbon charts take categorical and sequential palettes from Carbon theme tokens, including light, dark, and high contrast. Material expresses color as roles on a surface (primary, surface, on-surface, error) and checks contrast, rather than shipping one chart palette. Atlassian design tokens name chart colors by job (categorical, sequential, success, danger) so product code does not hardcode hex values.

## Palettes considered

Okabe-Ito (Okabe and Ito, Color Universal Design) is eight published colors chosen so common color-vision deficiencies can still tell them apart. The neutral preset uses those hexes for its categorical list.

Tableau 10 is a widely used ten-color categorical set. It is not the default here. Several neighbors in that set are closer under color-vision deficiency than Okabe-Ito.

ColorBrewer (Cynthia Brewer) publishes qualitative, sequential, and diverging schemes with fixed hexes. Sequential arrays in the light presets use ColorBrewer Blues. Diverging arrays use ColorBrewer RdBu. The print preset uses ColorBrewer Greys and RdGy.

## Chosen approach

Each preset is a token JSON file. Semantic roles are `primary`, `comparison`, `baseline`, `highlight`, `muted`, `positive`, `negative`, and `annotation`. Chrome tokens are `font`, `text`, `muted`, `gridline`, `axis`, `background`, and `surface`. Categorical, sequential, and diverging arrays sit beside the roles.

`scripts/make_chart_theme.py` reads one JSON file. It checks text on background with the WCAG relative luminance formula and a 4.5 ratio for small text. It checks that the first four categorical colors are pairwise at least 80 apart in 8-bit Euclidean RGB. On failure it exits 2 and writes nothing. On success it writes an ECharts theme register script and an Altair theme register function.

This folder is for internal and teammate HTML. User-facing prototypes stay on the company component system and do not load these files.
