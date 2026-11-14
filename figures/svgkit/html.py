"""HTML twins of figures: a table for a chart, an ordered list for a diagram."""
from html import escape


def table_html(headers, rows, caption):
    """An accessible table; the first cell of each row is its row header."""
    out = ["<table>", f"<caption>{escape(caption)}</caption>", "<thead><tr>"]
    out += [f'<th scope="col">{escape(str(h))}</th>' for h in headers]
    out += ["</tr></thead>", "<tbody>"]
    for row in rows:
        cells = [f'<th scope="row">{escape(str(row[0]))}</th>']
        cells += [f"<td>{escape(str(c))}</td>" for c in row[1:]]
        out.append("<tr>" + "".join(cells) + "</tr>")
    out += ["</tbody>", "</table>"]
    return "\n".join(out) + "\n"


def list_html(items):
    """An ordered list; an item is text or (text, [sub-items])."""
    def ol(items):
        parts = ["<ol>"]
        for it in items:
            if isinstance(it, str):
                parts.append(f"<li>{escape(it)}</li>")
            else:
                text, sub = it
                parts.append(f"<li>{escape(text)}\n{ol(sub)}</li>")
        parts.append("</ol>")
        return "\n".join(parts)

    return ol(items) + "\n"
