"""Output formatting for FUTBIN CLI — JSON and table modes."""

import json
import sys


def output_json(data):
    """Output data as formatted JSON."""
    if hasattr(data, "to_dict"):
        data = data.to_dict()
    elif isinstance(data, list):
        data = [item.to_dict() if hasattr(item, "to_dict") else item for item in data]
    print(json.dumps(data, indent=2, ensure_ascii=False))


def output_table(headers: list[str], rows: list[list[str]], max_col_width: int = 40):
    """Output data as a formatted table."""
    if not headers or not rows:
        print("No data to display.")
        return

    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = min(max(col_widths[i], len(str(cell))), max_col_width)

    # Print header
    header_line = " | ".join(str(h).ljust(col_widths[i]) for i, h in enumerate(headers))
    print(header_line)
    print("-+-".join("-" * w for w in col_widths))

    # Print rows
    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            if i < len(col_widths):
                text = str(cell)[:col_widths[i]]
                cells.append(text.ljust(col_widths[i]))
        print(" | ".join(cells))


def output_players_table(players: list, skin=None):
    """Format players as a table."""
    headers = ["ID", "Name", "RAT", "POS", "Price", "PAC", "SHO", "PAS", "DRI", "DEF", "PHY"]
    rows = []
    for p in players:
        d = p.to_dict() if hasattr(p, "to_dict") else p
        price = d.get("price_ps")
        price_str = f"{price:,}" if price else "---"
        rows.append([
            str(d.get("id", "")),
            d.get("name", "")[:25],
            str(d.get("rating", "")),
            d.get("position", ""),
            price_str,
            str(d.get("pac", "") or ""),
            str(d.get("sho", "") or ""),
            str(d.get("pas", "") or ""),
            str(d.get("dri", "") or ""),
            str(d.get("defense", "") or ""),
            str(d.get("phy", "") or ""),
        ])

    if skin:
        skin.table(headers, rows)
    else:
        output_table(headers, rows)


def output_sbcs_table(sbcs: list, skin=None):
    """Format SBCs as a table."""
    headers = ["Name", "Category", "Cost", "Expires"]
    rows = []
    for s in sbcs:
        d = s.to_dict() if hasattr(s, "to_dict") else s
        rows.append([
            d.get("name", "")[:40],
            d.get("category", ""),
            d.get("cost", ""),
            d.get("expires", "")[:20],
        ])
    if skin:
        skin.table(headers, rows)
    else:
        output_table(headers, rows)


def output_market_table(indices: list, skin=None):
    """Format market indices as a table."""
    headers = ["Name", "PS Value", "PS Change", "PC Value", "PC Change"]
    rows = []
    for idx in indices:
        d = idx.to_dict() if hasattr(idx, "to_dict") else idx
        ps_change = d.get("change_pct_ps")
        pc_change = d.get("change_pct_pc")
        rows.append([
            d.get("name", ""),
            str(d.get("value_ps", "---")),
            f"{ps_change:+.2f}%" if ps_change is not None else "---",
            str(d.get("value_pc", "---")),
            f"{pc_change:+.2f}%" if pc_change is not None else "---",
        ])
    if skin:
        skin.table(headers, rows)
    else:
        output_table(headers, rows)
