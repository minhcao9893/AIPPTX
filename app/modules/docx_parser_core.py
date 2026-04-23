"""
docx_parser_core.py — DOCX Parser Core Functions
=============================================
Core functions for parsing Word documents.
"""

import re
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph


def para_text(para: Paragraph) -> str:
    return para.text.strip()


def table_to_matrix(table: Table) -> dict:
    """Convert docx Table → {columns, rows} dict."""
    rows = []
    for row in table.rows:
        cells = [cell.text.strip() for cell in row.cells]
        rows.append(cells)

    if not rows:
        return {"columns": [], "rows": []}

    header = rows[0]
    data_rows = []
    for row in rows[1:]:
        converted = []
        for cell in row:
            try:
                clean = cell.replace(",", "").replace(" ", "").replace("%", "")
                if "." in clean:
                    converted.append(float(clean))
                else:
                    converted.append(int(clean))
            except ValueError:
                converted.append(cell)
        data_rows.append(converted)

    return {"columns": header, "rows": data_rows}


def infer_chart_type(table_data: dict) -> str:
    """Heuristic to pick best chart type from table structure."""
    columns = table_data.get("columns", [])
    rows = table_data.get("rows", [])

    if not columns or not rows:
        return "grouped_bar"

    n_cols = len(columns)
    n_rows = len(rows)

    period_re = re.compile(
        r"^(Q[1-4]|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|"
        r"\d{4}|Tháng\s*\d+|Quý\s*[1-4]|T\d+)", re.IGNORECASE)
    col0_header_is_period = bool(period_re.match(str(columns[0]))) if columns else False
    col0_values_are_period = any(
        period_re.match(str(r[0])) for r in rows if isinstance(r, list) and r
    )
    col0_is_period = col0_header_is_period or col0_values_are_period

    RANK_KEYWORDS = {"giai đoạn", "stage", "hạng mục", "category", "loại", "type",
                    "kênh", "channel", "phân khúc", "segment"}
    col0_is_rank = str(columns[0]).lower().strip() in RANK_KEYWORDS if columns else False

    numeric_series = 0
    for ci in range(1, n_cols):
        if any(isinstance(r[ci], (int, float)) for r in rows
               if isinstance(r, list) and ci < len(r)):
            numeric_series += 1

    if col0_is_period:
        return "line"
    if col0_is_rank:
        return "bar"
    if n_cols == 2 and n_rows <= 8:
        return "pie"
    if numeric_series >= 2:
        return "grouped_bar"
    return "bar"


def detect_slide_type(raw_text: str, tables: list, bullets: list,
                     has_chart_trigger: bool) -> str:
    """Heuristic: guess slide type."""
    if has_chart_trigger and tables:
        return "chart"
    if not raw_text and not tables and not bullets:
        return "title"
    if tables:
        return "table"
    if bullets:
        return "bullet"
    return "text"


def collect_blocks(doc: Document) -> list:
    """Walk document body in order, collecting paragraphs and tables."""
    blocks = []
    for block in doc.element.body:
        tag = block.tag.split("}")[-1]
        if tag == "p":
            para = Paragraph(block, doc)
            full_text = para.text
            style = para.style.name if para.style else "Normal"
            lines = full_text.split("\n")
            for line in lines:
                line = line.strip()
                if line:
                    blocks.append({
                        "type": "para",
                        "content": line,
                        "style": style
                    })
        elif tag == "tbl":
            table = Table(block, doc)
            blocks.append({"type": "table", "content": table})
    return blocks


def parse_docx(docx_path: str, SLIDE_TRIGGER, CHART_TRIGGER) -> list:
    """Parse Word file → list of slide dicts."""
    doc = Document(docx_path)
    blocks = collect_blocks(doc)

    slide_groups = []
    current_num = None
    current_blocks = []

    for block in blocks:
        if block["type"] == "para":
            m = SLIDE_TRIGGER.search(block["content"])
            if m:
                if current_num is not None:
                    slide_groups.append((current_num, current_blocks))
                current_num = int(m.group(1))
                current_blocks = []
                continue
        if current_num is not None:
            current_blocks.append(block)

    if current_num is not None:
        slide_groups.append((current_num, current_blocks))

    slides = []
    for slide_num, group in slide_groups:
        has_chart_trigger = any(
            CHART_TRIGGER.search(b["content"])
            for b in group if b["type"] == "para"
        )

        display_blocks = [
            b for b in group
            if not (b["type"] == "para" and CHART_TRIGGER.search(b["content"]))
        ]

        para_texts = [b["content"] for b in display_blocks if b["type"] == "para"]
        tables_raw = [b["content"] for b in display_blocks if b["type"] == "table"]

        bullets = [
            b["content"] for b in display_blocks
            if b["type"] == "para"
            and ("List" in (b.get("style") or "")
                 or "Bullet" in (b.get("style") or "")
                 or b["content"].startswith(("-", "•", "*", "·", "●", "+")))
        ]

        if not bullets and not tables_raw and len(para_texts) > 2:
            bullets = para_texts[1:]

        tables = [table_to_matrix(t) for t in tables_raw]

        title = para_texts[0] if para_texts else f"Slide {slide_num}"
        body_text = "\n".join(para_texts[1:]) if len(para_texts) > 1 else ""
        raw_text = "\n".join(para_texts)

        slide_type = detect_slide_type(body_text, tables, bullets, has_chart_trigger)

        chart_type_hint = "none"
        if has_chart_trigger and tables:
            chart_type_hint = infer_chart_type(tables[0])

        slide = {
            "index": slide_num,
            "title": title,
            "type": slide_type,
            "chart_hint": has_chart_trigger,
            "chart_type_hint": chart_type_hint,
            "raw_text": raw_text,
            "content": {},
        }

        if tables:
            slide["content"] = tables[0]
            if len(tables) > 1:
                slide["extra_tables"] = tables[1:]
        elif bullets:
            slide["content"] = bullets
        else:
            slide["content"] = body_text

        slides.append(slide)

    slides.sort(key=lambda s: s["index"])
    return slides


# ── Default triggers (dùng trong parse_docx_from_text và docx_parser.py) ──────
import re as _re
DEFAULT_SLIDE_TRIGGER = _re.compile(r'\{Slide\s+(\d+)\}', _re.IGNORECASE)
DEFAULT_CHART_TRIGGER = _re.compile(r'\{Chart\}', _re.IGNORECASE)


def parse_docx_from_text(text: str) -> dict:
    """
    Adapter: parse trigger text (string) thạy vì file path.
    Parse trực tiếp từ text — không dùng tempfile docx để giữ table structure.
    """
    slides = []
    # Split theo {Slide N} markers
    blocks = re.split(r'(\{Slide\s+\d+\})', text, flags=re.IGNORECASE)

    i = 1
    while i < len(blocks):
        marker = blocks[i].strip()
        body   = blocks[i + 1].strip() if i + 1 < len(blocks) else ''
        i += 2

        idx_match = re.search(r'\d+', marker)
        slide_num = int(idx_match.group()) if idx_match else len(slides) + 1

        has_chart_trigger = bool(DEFAULT_CHART_TRIGGER.search(body))

        # Loại bỏ dòng {Chart}
        lines = [l for l in body.split('\n') if not DEFAULT_CHART_TRIGGER.search(l)]

        # Extract images
        images = []
        clean_lines = []
        for l in lines:
            m = re.match(r'\[IMAGE:\s*(.+)\]', l.strip(), re.IGNORECASE)
            if m:
                images.append(m.group(1))
            else:
                clean_lines.append(l)

        para_texts = [l.strip() for l in clean_lines if l.strip() and '\t' not in l]
        table_lines = [l for l in clean_lines if '\t' in l]

        title = para_texts[0] if para_texts else f'Slide {slide_num}'
        body_text = '\n'.join(para_texts[1:]) if len(para_texts) > 1 else ''

        # Parse bảng từ các dòng tab-separated — hỗ trợ nhiều bảng trong 1 slide
        all_tables = []
        if table_lines:
            rows_raw = [l.split('\t') for l in table_lines]

            def _is_header_row(row):
                """Trả True nếu tất cả cells đều là string (không parse được số)."""
                for cell in row:
                    clean = cell.strip().replace(',', '').replace(' ', '').replace('%', '')
                    try:
                        float(clean)
                        return False  # có ít nhất 1 số → không phải header
                    except ValueError:
                        pass
                return True

            def _parse_table_block(block_rows):
                header = [c.strip() for c in block_rows[0]]
                data_rows = []
                for row in block_rows[1:]:
                    converted = []
                    for cell in row:
                        cell = cell.strip()
                        try:
                            clean = cell.replace(',', '').replace(' ', '').replace('%', '')
                            if '.' in clean:
                                converted.append(float(clean))
                            else:
                                converted.append(int(clean))
                        except ValueError:
                            converted.append(cell)
                    data_rows.append(converted)
                return {'columns': header, 'rows': data_rows}

            # Phân tách thành nhiều bảng: bắt đầu block mới khi gặp header row (sau block đầu)
            current_block = []
            for i_row, row in enumerate(rows_raw):
                is_hdr = _is_header_row(row)
                if is_hdr and current_block:
                    # Lưu block cũ, bắt đầu block mới
                    if len(current_block) >= 2:  # ít nhất header + 1 data row
                        all_tables.append(_parse_table_block(current_block))
                    current_block = [row]
                else:
                    current_block.append(row)
            # Xử lý block cuối
            if len(current_block) >= 2:
                all_tables.append(_parse_table_block(current_block))
            elif len(current_block) == 1 and not all_tables:
                # Chỉ có header, không có data — tạo bảng rỗng
                all_tables.append({'columns': [c.strip() for c in current_block[0]], 'rows': []})

        table_data = all_tables[0] if all_tables else {}

        bullets = []
        if not table_data:
            bullets = [
                l for l in para_texts[1:]
                if l.startswith(('-', '•', '*', '·', '●', '+'))
            ]
            if not bullets and len(para_texts) > 2:
                bullets = para_texts[1:]

        if all_tables:
            slide_type = 'chart' if has_chart_trigger else 'table'
            chart_hint_type = infer_chart_type(all_tables[0]) if has_chart_trigger else 'none'
            content = all_tables[0]
        elif bullets:
            slide_type = 'bullet'
            chart_hint_type = 'none'
            content = bullets
        else:
            slide_type = 'text'
            chart_hint_type = 'none'
            content = body_text

        slide_entry = {
            'index':           slide_num,
            'title':           title,
            'type':            slide_type,
            'chart_hint':      has_chart_trigger,
            'chart_type_hint': chart_hint_type,
            'raw_text':        '\n'.join(para_texts),
            'content':         content,
            'images':          images,
            'image_count':     len(images),
        }
        # Lưu các bảng phụ (nếu có > 1 bảng trong slide)
        if len(all_tables) > 1:
            slide_entry['extra_tables'] = all_tables[1:]
        slides.append(slide_entry)

    slides.sort(key=lambda s: s['index'])
    return {'slides': slides}