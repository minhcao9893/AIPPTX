"""
layout_engine.py — Tính BlockRect (inches) từ layout config
=============================================================
Nhận config { layout_type, pct, margin } → List[BlockRect] cho builder.

Slide size: 13.33 x 7.5 inches (widescreen 16:9)
Title bar:  ~1.2 inches từ trên → content area = 6.3 inches chiều cao
"""

from dataclasses import dataclass
from typing import List


# ── Slide dimensions ──────────────────────────────────────────────────────────
SLIDE_W = 13.33   # inches
SLIDE_H = 7.50    # inches
TITLE_H = 1.20    # inches (title bar)
CONTENT_TOP = TITLE_H + 0.1   # content area bắt đầu từ đây
CONTENT_H   = SLIDE_H - CONTENT_TOP - 0.15  # trừ bottom margin


@dataclass
class BlockRect:
    left:   float   # inches từ trái
    top:    float   # inches từ trên
    width:  float   # inches
    height: float   # inches


def compute_layout(config: dict) -> List[BlockRect]:
    """
    Tính List[BlockRect] từ layout config.

    config = {
        layout_type: "vertical" | "horizontal" | "table2" | "table3",
        pct: [40, 60],    # % chia ô (optional, dùng cho vertical/horizontal hoặc flat list cho table)
        tableDist: [2, 1], # Số lượng ô trên mỗi dòng (cho layout table)
        margin: 0.3       # inches gap giữa các ô
    }

    Returns: List[BlockRect] — 1 rect per content block.
    """
    layout_type = config.get('layout_type', 'horizontal')
    pct         = config.get('pct', [])
    table_dist  = config.get('tableDist')
    if isinstance(pct, (int, float)):
        pct = [pct]
    margin      = float(config.get('margin', 0.25))

    if layout_type == 'vertical':
        return _split_vertical(pct, margin)
    elif layout_type == 'horizontal':
        return _split_horizontal(pct, margin)
    elif layout_type in ('table2', 'table3'):
        if table_dist:
            return _split_grid(table_dist, pct, margin)
        else:
            # Fallback nếu không có table_dist: chia theo cột như cũ hoặc chia đều
            n_cols = 2 if layout_type == 'table2' else 3
            return _split_table(n_cols, margin)
    else:
        # fallback: 1 ô toàn màn hình
        return [BlockRect(
            left=margin, top=CONTENT_TOP,
            width=SLIDE_W - 2 * margin,
            height=CONTENT_H
        )]


def _normalize_pct(pct: list, n: int) -> List[float]:
    """Helper to normalize percentages and handle 0 as auto."""
    if not pct:
        pct = [0] * n
    if len(pct) < n:
        pct = list(pct) + [0] * (n - len(pct))
    
    # Treat 0 as "auto" for the last slot(s)
    fixed = [p for p in pct if p and p > 0]
    auto_count = n - len(fixed)
    fixed_total = sum(fixed)
    
    if auto_count > 0 and fixed_total < 100:
        auto_pct = (100 - fixed_total) / auto_count
        return [float(p) if p and p > 0 else auto_pct for p in pct]
    else:
        # Normalize: đảm bảo tổng = 100
        total_pct = sum(pct) or 100
        return [float(p) / total_pct * 100 for p in pct]


def _split_vertical(pct: list, margin: float) -> List[BlockRect]:
    """
    Chia theo chiều dọc (top / bottom).
    pct = [40, 60] → ô trên 40%, ô dưới 60% chiều cao content.
    """
    n = len(pct) or 1
    pct_norm = _normalize_pct(pct, n)

    total_gap = margin * (n + 1)
    usable_h  = CONTENT_H - total_gap

    rects = []
    y = CONTENT_TOP + margin
    for p in pct_norm:
        h = usable_h * (p / 100)
        rects.append(BlockRect(
            left=margin, top=y,
            width=SLIDE_W - 2 * margin,
            height=h
        ))
        y += h + margin

    return rects


def _split_horizontal(pct: list, margin: float) -> List[BlockRect]:
    """
    Chia theo chiều ngang (left / right).
    pct = [40, 60] → ô trái 40%, ô phải 60% chiều rộng.
    """
    n = len(pct) or 1
    pct_norm = _normalize_pct(pct, n)

    total_gap = margin * (n + 1)
    usable_w  = SLIDE_W - total_gap

    rects = []
    x = margin
    for p in pct_norm:
        w = usable_w * (p / 100)
        rects.append(BlockRect(
            left=x, top=CONTENT_TOP,
            width=w,
            height=CONTENT_H - margin
        ))
        x += w + margin

    return rects


def _split_grid(table_dist: list, pct: list, margin: float) -> List[BlockRect]:
    """
    Chia lưới theo dòng và cột (table2/table3).
    table_dist = [2, 1] → dòng 1 có 2 ô, dòng 2 có 1 ô.
    pct = flat list percentages của tất cả ô.
    """
    n_rows = len(table_dist)
    total_v_gap = margin * (n_rows + 1)
    usable_h = CONTENT_H - total_v_gap
    row_h = usable_h / n_rows

    rects = []
    y = CONTENT_TOP + margin
    pct_idx = 0

    for row_count in table_dist:
        total_h_gap = margin * (row_count + 1)
        usable_w = SLIDE_W - total_h_gap
        
        # Lấy pct cho dòng này
        row_pcts = pct[pct_idx : pct_idx + row_count]
        pct_idx += row_count
        
        row_pct_norm = _normalize_pct(row_pcts, row_count)
        
        x = margin
        for p in row_pct_norm:
            w = usable_w * (p / 100)
            rects.append(BlockRect(
                left=x, top=y,
                width=w, height=row_h
            ))
            x += w + margin
        
        y += row_h + margin

    return rects


def _split_table(n_cols: int, margin: float) -> List[BlockRect]:
    """
    Chia đều thành n_cols cột (fallback cũ).
    """
    total_gap = margin * (n_cols + 1)
    col_w     = (SLIDE_W - total_gap) / n_cols

    rects = []
    for i in range(n_cols):
        x = margin + i * (col_w + margin)
        rects.append(BlockRect(
            left=x, top=CONTENT_TOP,
            width=col_w,
            height=CONTENT_H - margin
        ))

    return rects
