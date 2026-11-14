# Figures

Every figure of a post is an SVG that is inlined into the page, so it takes its colours and fonts from the
page and follows the light and dark theme.

## Files

| path | what |
|---|---|
| `data/fig/<id>.json` | the numbers a figure draws (`comment-example.json` holds the example comment instead); the other data are `data/facts.json` and `data/facts_allow.txt` |
| `figures/gen/<id>.py` | generator: reads `data/fig/<id>.json`, writes the files below |
| `figures/gen/<id>.py` without `data/fig/<id>.json` | diagram: a generator without a data file, called with `{}` |
| `figures/svgkit/` | small SVG library, standard library only |
| `figures/build.py` | runs every generator; `figures/gen/_*.py` are shared helpers |
| `content/posts/<post>/fig/<id>.svg` | wide variant, `viewBox` width 720 |
| `content/posts/<post>/fig/<id>.narrow.svg` | narrow variant, `viewBox` width 360 |
| `content/posts/<post>/fig/<id>.table.html` | the same numbers as a table, or an ordered list for a diagram |

The page shows the wide variant in a container of 610 px or more and the narrow one, at most 460 px wide,
below that. Both are drawn close to their real size (the wide one at 85 to 110%, the narrow one at 100 to
128%), so 13 px text stays readable everywhere. A figure whose wide layout already reads at 360 px writes no
narrow file.

## Rules for an SVG

- Root: `<svg viewBox="0 0 W H" role="img" aria-labelledby="<id>-t <id>-d">` with a `<title id="<id>-t">`
  (what it is) and a `<desc id="<id>-d">` (the one sentence the figure says). No `width`, `height`, `style`.
- Classes only. No `fill`, `stroke`, `font-*` or `style` attributes with colours or fonts, no `<style>`, no
  `<script>`, no link to another host. Every `id` starts with the figure id.
- The classes are those of `assets/css/fig.css`; a new one is added there first.
- Coordinates with at most two decimals; the same input gives the same bytes.

## Colour

- `c-product`, `c-test`, `c-infra` mean the three failure classes and nothing else, in every figure.
- A figure that does not show classes by colour uses `c-focus` for what the text is about and `c-ctl` or
  `c-ctl-soft` for what it is compared with. Focus and class colours never share a figure.
- Text is `t`, `t-strong`, `t-muted`, `t-big`, `t-mono`, or `t-on` inside a filled mark. Text never takes a
  series colour.
- Grid and axes are solid hairlines (`grid`, `axis`). A dashed line (`arrow-off`) means "not connected".

## Marks

- Bars at most 24 px thick, the data end rounded by 4 px, square at the baseline.
- Lines 2 px, markers of radius 4 or more with a `ring` in the surface colour.
- Touching fills are separated by a 2 px gap, never by a stroke.
- Two or more series get a legend; up to four are also labelled at the mark. One series gets none.
- Labels are measured before they are placed; a label that does not fit inside a mark goes outside it or
  into the hover text. No number on every point.

## Hover and toggles

- A mark with details carries `data-tip="..."`, `tabindex="0"` and a child `<title>` with the same text, so
  it works without the script. Small marks get a transparent `hit` shape of at least 24 px.
- A figure with two views draws both as `<g data-layer="name">`; the default one also has `class="is-on"`.
- Every value shown on hover is also in the table file.
