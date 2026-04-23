"""
routes_input.py — Flask routes cho Step I (Input)
===================================================
API endpoints:
  POST /api/parse-docx-text   → Extract text từ Word (mode 1 preview)
  POST /api/save-edited-text  → Lưu text đã chỉnh sửa vào session
  POST /api/ai-split-docx     → Mode 2: Word dài → AI → trigger text
  POST /api/parse-slides      → Parse trigger text → danh sách slide objects
"""

from flask import Blueprint, request, jsonify
from pathlib import Path
import tempfile, os, re

from .input_mask import extract_text_from_docx, mask_text, unmask_text

bp_input = Blueprint('input', __name__)

# Lưu session text trong memory
_SESSION_TEXT = {}   # { 'current': { text, mode } }


def _mode_hint(text: str) -> str:
    """Nếu text có {Slide N} → 'trigger', ngược lại → 'raw'."""
    return 'trigger' if re.search(r'\{Slide\s+\d+\}', text, re.IGNORECASE) else 'raw'


def _count_tables(body: str) -> int:
    """
    Đếm số bảng thực sự trong 1 slide body.
    Bảng = khối các dòng liên tiếp có chứa ký tự tab,
    ngăn cách nhau bởi dòng trống hoặc dòng không có tab.
    """
    count = 0
    in_table = False
    for line in body.split('\n'):
        has_tab = '\t' in line
        if has_tab and not in_table:
            count += 1
            in_table = True
        elif not has_tab:
            in_table = False
    return count


@bp_input.route('/api/parse-docx-text', methods=['POST'])
def parse_docx_text():
    """
    Nhận: multipart file upload
    Trả: { ok, text, slide_count, mode_hint }
    """
    try:
        if 'file' not in request.files:
            return jsonify({'ok': False, 'error': 'Không có file trong request'}), 400

        f = request.files['file']
        suffix = Path(f.filename).suffix or '.docx'

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            f.save(tmp.name)
            tmp_path = tmp.name

        try:
            text = extract_text_from_docx(tmp_path)
        finally:
            os.unlink(tmp_path)

        slide_count = len(re.findall(r'\{Slide\s+\d+\}', text, re.IGNORECASE))
        hint = _mode_hint(text)

        return jsonify({
            'ok': True,
            'text': text,
            'slide_count': slide_count,
            'mode_hint': hint
        })

    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


@bp_input.route('/api/save-edited-text', methods=['POST'])
def save_edited_text():
    """
    Nhận: { text: str, mode?: str }
    Trả: { ok: True }
    """
    try:
        data = request.get_json() or {}
        text = data.get('text', '')
        mode = data.get('mode', 'trigger')
        _SESSION_TEXT['current'] = {'text': text, 'mode': mode}
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


@bp_input.route('/api/ai-split-docx', methods=['POST'])
def ai_split_docx():
    """
    Mode 2: Upload Word dài → AI chia thành trigger text có {Slide N}.
    Nhận: multipart file
    Trả: { ok, trigger_text, slide_count }
    """
    try:
        if 'file' not in request.files:
            return jsonify({'ok': False, 'error': 'Không có file'}), 400

        f = request.files['file']
        suffix = Path(f.filename).suffix or '.docx'

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            f.save(tmp.name)
            tmp_path = tmp.name

        try:
            from .input_ai_splitter import split_docx_with_ai
            result = split_docx_with_ai(tmp_path)
        finally:
            os.unlink(tmp_path)

        trigger_text = result.get('text', '')
        slide_count  = len(re.findall(r'\{Slide\s+\d+\}', trigger_text, re.IGNORECASE))

        _SESSION_TEXT['current'] = {'text': trigger_text, 'mode': 'ai'}

        return jsonify({
            'ok': True,
            'trigger_text': trigger_text,
            'slide_count': slide_count
        })

    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


@bp_input.route('/api/parse-slides', methods=['POST'])
def parse_slides():
    """
    Nhận: { text?: str } hoặc dùng session text
    Trả: { ok, slides: [ { title, index, has_chart, table_count, has_content } ] }
    """
    try:
        data = request.get_json() or {}
        text = data.get('text') or _SESSION_TEXT.get('current', {}).get('text', '')

        if not text:
            return jsonify({'ok': False, 'error': 'Không có text'}), 400

        # Parse slides từ trigger text bằng regex đơn giản
        # Mỗi khối bắt đầu bằng {Slide N}
        blocks = re.split(r'(\{Slide\s+\d+\})', text, flags=re.IGNORECASE)

        slides = []
        i = 1
        while i < len(blocks):
            marker = blocks[i].strip()   # e.g. "{Slide 1}"
            body   = blocks[i + 1].strip() if i + 1 < len(blocks) else ''
            i += 2

            # Tích title = dòng đầu tiên không rỗng
            lines = [l for l in body.split('\n') if l.strip()]
            title = lines[0] if lines else marker

            idx_match = re.search(r'\d+', marker)
            idx = int(idx_match.group()) if idx_match else len(slides) + 1

            has_chart   = bool(re.search(r'\{Chart\}', body, re.IGNORECASE))
            table_count = _count_tables(body)
            
            # Find images
            images = re.findall(r'\[IMAGE:\s*([^\]]+)\]', body, re.IGNORECASE)
            image_count = len(images)

            # Determine has_content by filtering out non-text elements
            content_lines = lines[1:] if len(lines) > 1 else []
            content_lines = [l for l in content_lines if not re.match(r'\[IMAGE:\s*[^\]]+\]', l, re.IGNORECASE)]
            content_lines = [l for l in content_lines if '\t' not in l]
            content_lines = [l for l in content_lines if not re.search(r'\{Chart\}', l, re.IGNORECASE)]
            has_content = len(content_lines) > 0

            slides.append({
                'index':       idx,
                'title':       title,
                'has_chart':   has_chart,
                'table_count': table_count,
                'has_content': has_content,
                'image_count': image_count,
                'images':      images,
            })

        return jsonify({'ok': True, 'slides': slides})

    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

