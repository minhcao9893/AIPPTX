"""
input_ai_splitter.py — Word dài (chưa trigger) → AI → Structured trigger text
===============================================================================
Xử lý Mode 2 trong Step I.

Luồng đầy đủ:
  1. Nhận .docx path từ Flask route /api/ai-split-docx
  2. extract_text (input_mask.py)
  3. mask_text → masked, mapping (input_mask.py)
  4. Gọi AI với prompt "Phân chia nội dung sau thành N slides, format {Slide N}..."
  5. unmask_text(ai_output, mapping) → structured text
  6. Return structured text + slide_count
"""

from typing import Optional
import re


# SplitResult dùng dict thường — TypedDict không dùng được như constructor
# { ok, text, slide_count, error }


# ── AI prompt template ─────────────────────────────────────────────────────────
SPLIT_PROMPT_TEMPLATE = """
Bạn là trợ lý tổ chức nội dung thuyết trình.
Nhiệm vụ: Đọc nội dung sau và phân chia thành tối đa {max_slides} slide.

YÊU CẦU FORMAT OUTPUT:
- Mỗi slide bắt đầu bằng: {{Slide N}} Tiêu đề ngắn gọn
- Giữ nguyên các bảng (table data) sau trigger {{Chart}} nếu phù hợp
- Tinh gọn nội dung, loại bỏ thông tin không cần thiết
- Ngôn ngữ: {lang}
- Chỉ trả về nội dung đã format, không thêm giải thích

NỘI DUNG:
{masked_text}
"""


def split_docx_with_ai(
    docx_path: str,
    max_slides: int = 10,
    lang: str = 'vi'
) -> dict:
    """
    Word dài → mask → AI split → unmask → structured trigger text.
    Returns dict: { ok, text, slide_count, error }
    """
    try:
        from .input_mask import extract_text_from_docx, mask_text, unmask_text

        # 1. Extract text
        text = extract_text_from_docx(docx_path)

        # 2. Mask dữ liệu nhạy cảm
        masked, mapping = mask_text(text)

        # 3. Build prompt
        prompt = SPLIT_PROMPT_TEMPLATE.format(
            max_slides=max_slides,
            lang=lang,
            masked_text=masked
        )

        # 4. Gọi AI
        ai_response = _call_ai(prompt)

        # Validate: output không được quá ngắn (< 40% input) hoặc quá dài (> 150%)
        # AI được phép tóm tắt — không dùng 90-110% vì quá chặt
        words_in  = len(masked.split())
        words_out = len(ai_response.split())
        if words_in > 0 and not (0.4 <= words_out / words_in <= 1.5):
            # Retry 1 lần nếu output lệch quá nhiều
            ai_response = _call_ai(prompt)

        # 6. Unmask
        structured = unmask_text(ai_response, mapping)

        # 7. Đếm slides
        slide_count = len(re.findall(r'\{Slide\s+\d+\}', structured, re.IGNORECASE))

        return {'ok': True, 'text': structured,
                'slide_count': slide_count, 'error': None}

    except Exception as e:
        return {'ok': False, 'text': '', 'slide_count': 0, 'error': str(e)}


def _call_ai(prompt: str) -> str:
    """
    Gọi Groq API với key pool + rotation.
    Model lấy từ config.json. Max 3 retries.
    """
    import json
    from pathlib import Path

    # Load config
    cfg_path = Path(__file__).resolve().parents[1] / 'config.json'
    cfg = json.loads(cfg_path.read_text(encoding='utf-8')) if cfg_path.exists() else {}
    model = cfg.get('model', 'llama-3.3-70b-versatile')

    from ..key_pool import get_key_pool
    pool = get_key_pool()
    if not pool or len(pool) == 0:
        raise RuntimeError('Không có API key trong pool')

    last_err = None
    for _ in range(3):
        # Dùng .next_key() — KeyPool không support indexing []
        key = pool.next_key()
        if not key:
            raise RuntimeError('Key pool rỗng')
        try:
            from groq import Groq
            client = Groq(api_key=key)
            resp = client.chat.completions.create(
                model=model,
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.3,
                max_tokens=4096
            )
            return resp.choices[0].message.content
        except Exception as e:
            last_err = e
            err_str = str(e)
            if '429' in err_str or 'rate' in err_str.lower():
                # pool.next_key() đã tự rotate sang key tiếp theo — chứ không cần gọi thêm
                continue
            else:
                raise

    raise RuntimeError(f'AI thất bại sau 3 lần retry: {last_err}')


def _parse_slide_count(text: str) -> int:
    """Count {Slide N} markers."""
    return len(re.findall(r'\{Slide\s+\d+\}', text, re.IGNORECASE))
