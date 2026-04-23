"""
input_mask.py — Mask/Unmask cho Mode 2 (Word dài → AI)
=======================================================
Tương tự sanitizer_core.py nhưng dùng cho luồng mới:
  - Input: raw text từ Word (toàn bộ nội dung, chưa có trigger)
  - Output: masked_text (thay thế blacklist bằng alias) + mapping

Luồng sử dụng (gọi bởi input_ai_splitter.py):
  1. text = extract_text_from_docx(path)
  2. masked, mapping = mask_text(text)
  3. structured = call_ai(masked)  ← input_ai_splitter.py
  4. result = unmask_text(structured, mapping)
"""

from typing import Tuple
import re
from pathlib import Path

try:
    from docx import Document
except ImportError:
    Document = None


# ── Alias templates ───────────────────────────────────────────────────────────
ALIAS_TEMPLATES = {
    "company":  "Cty-{n}",
    "person":   "Ng-{n}",
    "location": "Vung-{n}",
    "number":   "So-{n}",
}

# ── Category detection ────────────────────────────────────────────────────────
# FIX BUG-9: category detection trước đó là vòng for bỏ trống, mọi term đều → company
_PERSON_RE = re.compile(
    r'^(Nguyễn|Trần|Lê|Phạm|Hoàng|Huỳnh|Phan|Vũ|Võ|'
    r'Đặng|Bùi|Đỗ|Hồ|Ngô|Dương|Lý|Đinh|Đoàn)\s+\S',
    re.UNICODE
)
_NUMBER_RE = re.compile(r'^[\d\s\.,\+\-\%]+$')
_LOCATION_KW = {
    'hà nội', 'hồ chí minh', 'tp.hcm', 'tp hcm', 'đà nẵng', 'hải phòng',
    'miền bắc', 'miền nam', 'miền trung', 'tây nguyên', 'việt nam'
}


def _detect_term_category(term: str) -> str:
    """Phân loại term — person / location / number / company."""
    t = term.strip()
    if _NUMBER_RE.fullmatch(t):
        return 'number'
    if t.lower() in _LOCATION_KW:
        return 'location'
    if _PERSON_RE.match(t):
        return 'person'
    return 'company'


def mask_text(raw_text: str, blacklist: list = None) -> Tuple[str, dict]:
    """
    Mask các từ nhạy cảm trong raw_text bằng alias.

    Args:
        raw_text:  text thô từ Word
        blacklist: danh sách (term, category) hoặc chỉ [term, ...]
                   Nếu None → tự load từ list_store.py

    Returns:
        (masked_text, mapping)  — mapping: { alias: original }
    """
    if blacklist is None:
        try:
            from .list_store import get_blacklist
            blacklist = get_blacklist()  # returns list of str
        except Exception:
            blacklist = []

    # Normalize thành list of str
    terms = []
    for item in blacklist:
        if isinstance(item, (list, tuple)):
            terms.append(str(item[0]))
        else:
            terms.append(str(item))

    # Sort by length DESC — match cụm dài trước, tránh partial
    terms = sorted(set(terms), key=len, reverse=True)

    masked = raw_text
    mapping = {}        # { alias: original }
    counters = {k: 0 for k in ALIAS_TEMPLATES}
    used: dict = {}     # { term_lower: alias } — tái dùng alias cho cùng term

    for term in terms:
        if not term.strip():
            continue
        key = term.lower()
        if key in used:
            alias = used[key]
        else:
            # FIX BUG-9: dùng _detect_term_category thay vì vòng for bỏ trống
            cat = _detect_term_category(term)
            counters[cat] += 1
            alias = ALIAS_TEMPLATES[cat].format(n=counters[cat])
            used[key] = alias
            mapping[alias] = term

        # Replace case-insensitive, giữ word boundary
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        masked = pattern.sub(alias, masked)

    return masked, mapping


def unmask_text(structured_text: str, mapping: dict) -> str:
    """
    Khôi phục alias → giá trị thật.
    Sort alias by length DESC để tránh partial replace.
    """
    if not mapping:
        return structured_text

    result = structured_text
    # Sort alias dài trước
    for alias in sorted(mapping.keys(), key=len, reverse=True):
        result = result.replace(alias, mapping[alias])
    return result


def extract_text_from_docx(docx_path: str) -> str:
    """
    Extract toàn bộ text từ .docx (paragraphs + tables) thành plain text.
    Table: mỗi row = 1 dòng, cells cách nhau bằng '\\t'.
    """
    if Document is None:
        raise ImportError("python-docx chưa cài. Chạy: pip install python-docx")

    doc = Document(docx_path)
    lines = []
    
    media_dir = Path(__file__).resolve().parents[1] / "input" / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    # Duyệt theo thứ tự body (paragraphs xen kẽ tables)
    for block in doc.element.body:
        tag = block.tag.split('}')[-1] if '}' in block.tag else block.tag

        if tag == 'p':  # paragraph
            from docx.text.paragraph import Paragraph
            from docx.oxml.ns import qn
            import uuid

            para = Paragraph(block, doc)
            text = para.text.strip()
            if text:
                lines.append(text)

            # Tìm hình ảnh trong paragraph
            for drawing in block.iter(qn('w:drawing')):
                for blip in drawing.iter(qn('a:blip')):
                    rId = blip.get(qn('r:embed'))
                    if rId and rId in doc.part.related_parts:
                        image_part = doc.part.related_parts[rId]
                        # Lưu ảnh
                        ext = image_part.content_type.split('/')[-1]
                        if ext == "jpeg": ext = "jpg"
                        filename = f"img_{uuid.uuid4().hex[:8]}.{ext}"
                        with open(media_dir / filename, "wb") as f:
                            f.write(image_part.blob)
                        lines.append(f"[IMAGE: {filename}]")

        elif tag == 'tbl':  # table
            from docx.table import Table
            tbl = Table(block, doc)
            for row in tbl.rows:
                cells = [c.text.strip() for c in row.cells]
                row_text = '\t'.join(cells)
                if row_text.strip():
                    lines.append(row_text)

    return '\n'.join(lines)
