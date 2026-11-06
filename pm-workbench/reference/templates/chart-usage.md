# Chart usage

For internal HTML and teammate HTML. User-facing prototypes stay on the company component system and do not load `assets/charts/`.

One message per chart. No dual axes. No pie charts. Do not mix two source systems on one chart. The caption names the population, the window, and the denominator. Those three fields are free text on every helper.

Bars start at zero. A line does too, unless the question is about a rate that has no meaningful zero, in which case say so in the caption and do not add a second axis.

## Which helper

| Question | Helper | Data |
|---|---|---|
| How do categories compare, or how does one series compare with another? | `barCompare` | `categories`, `series[{ name, role, values }]` |
| How does a measure move across an ordered window? | `lineSeries` | `x`, `series[{ name, role, values }]`, optional `bands[{ from, to, label }]` |
| Where does a staged count drop? | `funnel` | `stages[{ name, value }]`, order kept as given |
| How do two categories cross? | `heatmap` | `x`, `y`, `values` as a matrix (row is y). Set `scale` to `diverging` only when the midpoint is meaningful. |
| What is the spread, not only the center? | `distribution` | `categories`, `series[{ name, role, values }]`. Each value is `[min, q1, median, q3, max]`. |
| How does a count flow from one set of labels to another? | `sankey` | `nodes[{ name }]`, `links[{ source, target, value }]` |

`role` is one of `primary`, `comparison`, `baseline`, `highlight`, `muted`, `positive`, `negative`, `annotation`. Omit it to take the next categorical color.

Load order: `echarts.min.js`, then `generated/<theme>.theme.js`, then `wb-charts.js`. Pass the theme name as the third argument. The fourth argument is `{ population, window, denominator }`.
