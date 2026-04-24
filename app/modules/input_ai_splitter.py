"""
input_ai_splitter.py — Word dài (chưa trigger) → 2-lượt AI → Structured trigger text
=====================================================================================
Xử lý Mode 2 trong Step I. Luồng 2-lượt:

  Lượt 1 — Stage 1 (Extract Blacklist/Whitelist):
    1. extract_text từ .docx
    2. strip_numbers(text) → text_no_numbers (giữ nguyên từ, bỏ số)
    3. Gọi AI với text_no_numbers + current whitelist/blacklist
    4. AI trả về { add_whitelist, add_blacklist } → merge → new lists
    5. Tạo mapping: build alias cho từng term trong blacklist mới

  Lượt 2 — Stage 2 (Structure to Slides):
    6. mask_text(text_gốc_có_số, blacklist=new_blacklist) → masked_text (số giữ nguyên)
    7. Gọi AI với masked_text → AI soạn cấu trúc {Slide N}, {Chart}, bảng số liệu
    8. unmask_text(ai_output, mapping) → trigger text với số thật
    9. Return trigger text + slide_count
"""

from typing import Optional, List, Tuple
import re
import json


# { ok, text, slide_count, error, stage1_blacklist_added, stage1_whitelist_added }


# ── Prompt templates ─────────────────────────────────────────────────────────

# Lượt 1: Stage 1 — extract whitelist/blacklist từ text không có số
STAGE1_PROMPT = """
Bạn là trợ lý bảo mật dữ liệu thuyết trình.
Nhiệm vụ: Đọc nội dung (đã loại bỏ số) và cập nhật danh sách từ nhạy cảm.

QUY TẮC:
- Blacklist: tên công ty, tên người, tên địa danh cụ thể, thương hiệu, sản phẩm riêng
- Whitelist: từ thông thường cần GIỮ NGUYÊN, không được mask (ví dụ: tên ngành, khái niệm phổ biến)
- CHỈ thêm term CHƯA CÓ trong danh sách hiện tại
- Giới hạn: tối đa 30 term mỗi loại mỗi lần

DANH SÁCH HIỆN TẠI:
{current_lists_json}

NỘI DUNG (đã bỏ số):
{text_no_numbers}

TRẢ VỀ JSON DUY NHẤT (không thêm giải thích, không markdown):
{{"add_whitelist": [...], "add_blacklist": [...]}}
"""

# Lượt 2: Stage 2 — soạn cấu trúc slide từ masked text
STAGE2_PROMPT = """
Bạn là chuyên gia soạn nội dung thuyết trình.
Nhiệm vụ: Đọc nội dung và tổ chức thành tối đa {max_slides} slide có cấu trúc.

YÊU CẦU FORMAT BẮT BUỘC:
- Mỗi slide BẮT BUỘC bắt đầu bằng dòng: {{Slide N}} Tiêu đề slide
  Ví dụ: {{Slide 1}} Tổng quan thị trường
         {{Slide 2}} Kết quả kinh doanh
- Dấu ngoặc nhọn {{ và }} là BẮT BUỘC, KHÔNG được dùng ## hay ** hay dạng khác
- Nếu có bảng số liệu: đặt {{Chart}} trên dòng riêng, sau đó là các dòng tab-separated
- Giữ NGUYÊN các alias dạng Cty-1, Ng-2, Vung-3 (đây là dữ liệu đã mask, KHÔNG dịch)
- Giữ NGUYÊN tất cả số liệu (%, triệu, tỷ...)
- Tinh gọn nội dung, loại bỏ thông tin lặp
- Ngôn ngữ output: {lang}
- Chỉ trả về nội dung đã format, KHÔNG thêm giải thích hay preamble

VÍ DỤ OUTPUT ĐÚNG:
{{Slide 1}} Giới thiệu
Nội dung slide 1 ở đây.

{{Slide 2}} Kết quả
- Doanh thu tăng 20%
- Lợi nhuận: 50 tỷ

NỘI DUNG CẦN XỬ LÝ:
{masked_text}
"""


# ── Number stripping (cho Lượt 1) ──────────────────────────────────────────
_RE_NUMBERS = re.compile(
    r'\b[\d]+(?:[.,][\d]+)*\s*(?:%|triệu|tỷ|nghìn|k|m|b|usd|vnd|đ)?\b',
    re.IGNORECASE
)

def _strip_numbers(text: str) -> str:
    """Xóa số và đơn vị đi kèm, giữ lại text. Dùng cho Lượt 1."""
    return _RE_NUMBERS.sub(' ', text)


# ── Lượt 1: Stage 1 — Extract Blacklist/Whitelist ───────────────────────────
def _run_stage1(
    text_no_numbers: str,
    current_whitelist: List[str],
    current_blacklist: List[str]
) -> Tuple[List[str], List[str]]:
    """
    Gọi AI lượt 1: text (không số) + lists hiện tại → trả về (new_whitelist, new_blacklist).
    Nếu AI lỗi → trả về lists cũ (graceful degradation).
    """
    try:
        # Giới hạn text gửi AI (tránh vượt context)
        text_truncated = text_no_numbers[:6000]

        current_lists_json = json.dumps({
            'whitelist': current_whitelist[:100],
            'blacklist': current_blacklist[:100]
        }, ensure_ascii=False)

        prompt = STAGE1_PROMPT.format(
            current_lists_json=current_lists_json,
            text_no_numbers=text_truncated
        )

        raw = _call_ai(prompt)

        # Parse JSON từ response
        # Tìm block JSON đầu tiên trong response
        # Strip markdown code fences nếu có
        clean_raw = re.sub(r'```(?:json)?\s*', '', raw).strip()
        clean_raw = clean_raw.rstrip('`').strip()
        # Tìm JSON object đầu tiên (hỗ trợ nested arrays)
        json_match = re.search(r'\{[\s\S]*?"add_whitelist"[\s\S]*?\}', clean_raw)
        if json_match:
            # Lấy từ vị trí { đầu tiên đến hết
            start = clean_raw.index('{')
            parsed = json.loads(clean_raw[start:])
        else:
            parsed = json.loads(clean_raw)

        add_w = [str(x).strip() for x in parsed.get('add_whitelist', []) if str(x).strip()]
        add_b = [str(x).strip() for x in parsed.get('add_blacklist', []) if str(x).strip()]

        # Merge: không trùng lặp
        def _merge(base: List[str], add: List[str]) -> List[str]:
            seen = set(b.lower() for b in base)
            merged = list(base)
            for x in add:
                if x.lower() not in seen:
                    seen.add(x.lower())
                    merged.append(x)
            return merged

        new_w = _merge(current_whitelist, add_w)
        new_b = _merge(current_blacklist, add_b)
        return new_w, new_b

    except Exception as e:
        # Graceful degradation: Stage 1 lỗi không chặn luồng
        import sys
        print(f'⚠️ [input_ai_splitter] Stage 1 lỗi (dùng lists cũ): {e}', file=sys.stderr)
        return current_whitelist, current_blacklist


# ── Main entrypoint ──────────────────────────────────────────────────────────
def split_docx_with_ai(
    docx_path: str,
    max_slides: int = 10,
    lang: str = 'vi'
) -> dict:
    """
    Word dài → 2-lượt AI → structured trigger text.
    Lượt 1: extract blacklist/whitelist → build mapping
    Lượt 2: mask text gốc → AI soạn slide → unmask
    Returns dict: { ok, text, slide_count, error, stage1_added_w, stage1_added_b }
    """
    try:
        from .input_mask import extract_text_from_docx, mask_text, unmask_text

        # ── Step 1: Extract text gốc ─────────────────────────────────────────
        raw_text = extract_text_from_docx(docx_path)

        # ── Step 2: Load lists hiện tại ──────────────────────────────────────
        try:
            from .list_store import load_lists
            current_whitelist, current_blacklist = load_lists()
        except Exception:
            current_whitelist, current_blacklist = [], []

        # ── Step 3: Strip numbers → Lượt 1 ──────────────────────────────────
        text_no_numbers = _strip_numbers(raw_text)
        new_whitelist, new_blacklist = _run_stage1(
            text_no_numbers, current_whitelist, current_blacklist
        )
        n_added_w = len(new_whitelist) - len(current_whitelist)
        n_added_b = len(new_blacklist) - len(current_blacklist)

        # Save lists mới async (không block)
        if n_added_w or n_added_b:
            import threading
            try:
                from .list_store import save_lists
                _nw, _nb = list(new_whitelist), list(new_blacklist)
                threading.Thread(
                    target=lambda: save_lists(_nw, _nb, message=f'Mode2 Stage1 +{n_added_w}W/+{n_added_b}B'),
                    daemon=True
                ).start()
            except Exception:
                pass

        # ── Step 4: Mask text GỐC (có số) với blacklist mới ─────────────────
        # Lọc whitelist ra khỏi blacklist trước khi mask
        whitelist_set = set(w.lower() for w in new_whitelist)
        effective_blacklist = [t for t in new_blacklist if t.lower() not in whitelist_set]

        masked_text, mapping = mask_text(raw_text, blacklist=effective_blacklist)

        # ── Step 5: Lượt 2 — AI soạn cấu trúc slide ─────────────────────────
        prompt2 = STAGE2_PROMPT.format(
            max_slides=max_slides,
            lang=lang,
            masked_text=masked_text
        )

        ai_response = _call_ai(prompt2)

        # Validate: phải có ít nhất 1 {Slide N}
        if not re.search(r'\{Slide\s+\d+\}', ai_response, re.IGNORECASE):
            # Retry 1 lần với reminder mạnh hơn
            retry_prompt = prompt2 + '\n\nNHẮC LẠI: Output PHẢI bắt đầu mỗi slide bằng {Slide N}, dùng dấu ngoặc nhọn thật sự { và }.'
            ai_response = _call_ai(retry_prompt)
            # Nếu vẫn không có {Slide N} → tự thêm wrapper
            if not re.search(r'\{Slide\s+\d+\}', ai_response, re.IGNORECASE):
                ai_response = '{Slide 1} Nội dung\n' + ai_response

        # ── Step 6: Unmask ───────────────────────────────────────────────────
        structured = unmask_text(ai_response, mapping)

        # ── Step 7: Đếm slides ───────────────────────────────────────────────
        slide_count = len(re.findall(r'\{Slide\s+\d+\}', structured, re.IGNORECASE))

        return {
            'ok': True,
            'text': structured,
            'slide_count': slide_count,
            'error': None,
            'stage1_added_w': n_added_w,
            'stage1_added_b': n_added_b,
        }

    except Exception as e:
        return {'ok': False, 'text': '', 'slide_count': 0, 'error': str(e),
                'stage1_added_w': 0, 'stage1_added_b': 0}


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
    for _ in range(min(3, max(len(pool), 1))):
        # Dùng .next_key() — KeyPool không support indexing []
        key = pool.next_key()
        if not key:
            raise RuntimeError('Key pool rỗng hoặc tất cả key đã bị loại')
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
                # Rate limit: rotate key, thử lại
                continue
            elif '400' in err_str and ('restricted' in err_str.lower() or 'organization' in err_str.lower()):
                # Key bị restrict vĩnh viễn → đánh dấu xấu, dùng key khác
                pool.mark_bad(key)
                continue
            else:
                raise

    raise RuntimeError(f'AI thất bại sau 3 lần retry: {last_err}')


def _parse_slide_count(text: str) -> int:
    """Count {Slide N} markers."""
    return len(re.findall(r'\{Slide\s+\d+\}', text, re.IGNORECASE))
