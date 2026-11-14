"""Small SVG library for the figures of this site; standard library only."""
from .chart import Labeler, axis_x, axis_y, band_labels, beeswarm, end_labels, flow, label_point, labels_width, legend, spread
from .html import list_html, table_html
from .scale import Band, Linear, nice_ticks, tick_labels
from .svg import El, Group, Svg, num, pts
from .text import measure, text_box, text_width, wrap

__all__ = [
    "Band", "El", "Group", "Labeler", "Linear", "Svg", "axis_x", "axis_y", "band_labels", "beeswarm",
    "end_labels", "flow", "label_point", "labels_width", "legend", "list_html", "measure", "nice_ticks",
    "num", "pts", "spread", "table_html", "text_box", "text_width", "tick_labels", "wrap",
]
