"""
ai_planner_core.py — AI Planner Core Functions
========================================
Core functions for AI layout planning.
"""

from typing import Dict, List, Optional, Set, Tuple
import json
import re
import os
import time
import concurrent.futures
from groq import Groq


def _load_config() -> dict:
    cfg_path = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(cfg_path):
        with open(cfg_path, encoding="utf-8") as f:
            return json.load(f)
    return {}


CONFIG = _load_config()
MODEL = CONFIG.get("model", "llama-3.3-70b-versatile")


SYSTEM_PROMPT = """
You are a professional PowerPoint Strategist and Business Analyst AI.
You receive a presentation SKELETON with REAL structure and context.

LANGUAGE RULE: ALL output text (insight_text, design_notes, any string values) MUST be in English only.
No Vietnamese, no mixed language. Translate slide titles or content references to English naturally.

DATA FORMAT:
- Text, dates, column headers: REAL values (use them to understand context)
- Numbers: REAL values (use them directly for chart decisions and insights)
- Company/org names: anonymized as Company-A, Company-B… (keep as-is in output)
- Region/location names: anonymized as Region-1, Region-2… (keep as-is in output)
- Person names: anonymized as Person-A, Person-B… (keep as-is in output)

YOUR CORE TASK:
1. Choose the RIGHT chart type based on actual data structure (columns, row count, trends)
2. Write SPECIFIC insight_text IN ENGLISH using REAL numbers and anonymized names:
   - Compare values: "Company-A led with 45,200 units, 2× ahead of Company-B's 22,100"
   - Trends: "Region-1 grew 23% QoQ while Region-2 declined 8%"
   - Rankings: "Company-C dominated Region-2 with 67% market share"
   - Keep alias names EXACTLY as given — they will be swapped for real names automatically

INSIGHT RULES:
- ALL insight_text must be in English
- Use actual column names, real numbers, and alias names freely
- 1–3 sentences max. No filler like "as shown above"
- If data is text-only → describe the strategic message of the slide in English
""".strip()


def enrich_skeleton(skeleton: dict) -> dict:
    """Build content_summary per slide."""
    enriched = json.loads(json.dumps(skeleton))

    for slide in enriched.get("slides", []):
        raw = slide.pop("raw_text", "")
        chart_hint = slide.get("chart_hint", False)
        chart_hint_type = slide.get("chart_type_hint", "none")
        content = slide.get("content", {})

        parts = []
        if chart_hint:
            parts.append(f"[CHART REQUIRED — suggested: {chart_hint_type}]")
        if slide.get("type"):
            parts.append(f"[slide type: {slide['type']}]")

        if isinstance(content, dict) and "columns" in content:
            cols = content["columns"]
            rows = content.get("rows", [])
            n_rows = len(rows)
            parts.append(f"[table: {len(cols)} cols × {n_rows} rows]")
            parts.append(f"[columns: {', '.join(str(c) for c in cols)}]")
            if rows:
                parts.append(f"[data_preview: {rows[:3]}]")
        elif isinstance(content, list):
            parts.append(f"[{len(content)} bullet points]")
            if content:
                parts.append(f"[bullets_preview: {[str(b)[:80] for b in content[:3]]}]")
        elif isinstance(content, str) and content.strip():
            n_lines = len([l for l in content.strip().split("\n") if l.strip()])
            preview = content.strip()[:200]
            parts.append(f"[text: {n_lines} lines | preview: {preview}]")

        lines = [l for l in raw.split("\n") if l.strip()]
        if lines:
            parts.append(f"[title: {lines[0]}]")

        slide["content_summary"] = " | ".join(parts)
        slide.pop("_relative", None)
        slide.pop("_cat_map_size", None)

    return enriched


def layout_prompt(skeleton: dict, design_hints: dict = None) -> str:
    """Build layout prompt for AI."""
    design_block = ""
    if design_hints:
        colors = design_hints.get("colors", {})
        fonts = design_hints.get("fonts", {})
        design_block = (
            f"\nDesign constraints: primary={colors.get('bg_dark','#1E2761')} "
            f"accent={colors.get('bullet_dot','#028090')} "
            f"font={fonts.get('main','Calibri')}\n"
        )

    enriched = enrich_skeleton(skeleton)

    return f"""
Analyze this presentation skeleton and return layout_plan JSON.
Each slide has content_summary (structure).
{design_block}

IMPORTANT: All insight_text and design_notes MUST be written in English.

CHART TYPE GUIDE (when chart_hint=true):
  pie         → ≤8 rows, 2 cols, share/proportion
  line        → time-series, trends over periods
  bar         → single numeric series, ranking/comparison
  grouped_bar → multiple numeric series, side-by-side

LAYOUT GUIDE:
  title_only  → cover slide
  split_left  → left 60%: chart+table | right 40%: insight (DEFAULT for data slides)
  image_split → left 60%: 3 image placeholders | right 40%: insight (no table data)
  one_col     → bullet/text only (use sparingly)

Skeleton:
{json.dumps(enriched, ensure_ascii=False, indent=2)}

Return ONLY valid JSON (no markdown fences):
{{
  "slides": [
    {{
      "index": <int>,
      "layout": "<title_only|split_left|image_split|one_col>",
      "chart_type": "<bar|grouped_bar|line|pie|none>",
      "color_scheme": "<corporate_blue|warm|neutral>",
      "insight_text": "<specific 1-3 sentences IN ENGLISH>",
      "design_notes": "<brief in English: why this layout>",
      "elements": [
        {{ "type": "<title|chart|table|text|bullet_list>",
           "position": "<top|left|right|center|bottom|full>",
           "font_size": <int> }}
      ]
    }}
  ]
}}

RULES:
1. chart_hint=true → chart_type MUST be bar/grouped_bar/line/pie (never none)
2. ALL insight_text MUST be in English — no exceptions
3. Use trends, ranking, numbers in insight_text when available
4. color_scheme: corporate_blue=data/ops, warm=achievement, neutral=process/text
5. Slides with table data → layout=split_left; slides without data → layout=image_split
""".strip()


def is_rate_limited(err: Exception) -> bool:
    status = getattr(err, "status_code", None) or getattr(err, "status", None)
    if status == 429:
        return True
    msg = str(err).lower()
    return "429" in msg or "rate limit" in msg or "ratelimit" in msg or "too many requests" in msg


def is_org_restricted(err: Exception) -> bool:
    """Phát hiện lỗi key bị Groq ban tổ chức (400 Organization has been restricted)."""
    msg = str(err).lower()
    return "organization has been restricted" in msg


def _recover_truncated_json(json_str: str) -> dict:
    """
    Attempt to recover a truncated JSON response from the AI.
    Extracts all fully-completed slide objects using regex,
    ignoring any partial/broken slide at the end.
    """
    import re

    # Find all complete slide objects: match from opening { to closing }
    # Strategy: find each '{' at the slide level and try to parse
    slides = []
    depth = 0
    start = None
    i = 0
    in_string = False
    escape_next = False

    while i < len(json_str):
        ch = json_str[i]
        if escape_next:
            escape_next = False
            i += 1
            continue
        if ch == '\\' and in_string:
            escape_next = True
            i += 1
            continue
        if ch == '"':
            in_string = not in_string
        if not in_string:
            if ch == '{':
                if depth == 1:   # start of a slide object (depth 0=root, 1=slides array)
                    start = i
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 1 and start is not None:  # completed a slide object
                    candidate = json_str[start:i+1]
                    try:
                        slide_obj = json.loads(candidate)
                        slides.append(slide_obj)
                    except json.JSONDecodeError:
                        pass
                    start = None
        i += 1

    if not slides:
        raise ValueError("No complete slide objects found in truncated JSON")

    return {"slides": slides}


# ── Chunk helpers ────────────────────────────────────────────────────────────

CHUNK_SIZE = 5   # số slide mỗi chunk (mỗi API key xử lý)


def _split_skeleton(skeleton: dict, chunk_size: int) -> List[dict]:
    """Chia skeleton thành nhiều mini-skeleton, mỗi cái ≤ chunk_size slides."""
    slides = skeleton.get("slides", [])
    chunks = []
    for i in range(0, len(slides), chunk_size):
        batch = slides[i : i + chunk_size]
        mini = dict(skeleton)   # copy metadata (title, v.v.)
        mini["slides"] = batch
        chunks.append(mini)
    return chunks


# Prompt rút gọn dùng cho mỗi chunk (tiết kiệm token input)
CHUNK_SYSTEM_PROMPT = """You are a PowerPoint layout AI. Return ONLY valid JSON, no markdown.
ALL text values (insight_text, design_notes) MUST be in English.
Layout: split_left=data slides (chart+table left, insight right), image_split=no-data slides, title_only=cover.
Chart: bar=ranking, grouped_bar=multi-series, line=trend, pie=share(≤8 rows), none=text-only.""".strip()


def is_daily_limit(err: Exception) -> bool:
    """Phát hiện lỗi hết TPD (Tokens Per Day) — khác với TPM rate limit."""
    msg = str(err).lower()
    return "tokens per day" in msg or "tpd" in msg or "per day" in msg


def _call_groq_single(api_key: str, mini_skeleton: dict,
                      design_hints: dict, key_pool=None) -> dict:
    """
    Gọi Groq với 1 api_key cho 1 mini_skeleton.
    Trả về layout_plan chỉ chứa các slide của chunk đó.
    Nếu 429, tự động xoay sang key tiếp theo trong pool.
    """
    prompt = layout_prompt(mini_skeleton, design_hints or {})
    client = Groq(api_key=api_key)

    max_retries = 3
    current_key = api_key
    for attempt in range(max_retries):
        try:
            from groq import Groq as _Groq
            client = _Groq(api_key=current_key)
            response = client.chat.completions.create(
                model=MODEL,
                max_tokens=4096,
                messages=[
                    {"role": "system", "content": CHUNK_SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
            )
            raw = response.choices[0].message.content
            print(f"[Groq] ✅ chunk OK key={current_key[-8:]}")
            break
        except Exception as e:
            print(f"[Groq] ❌ Error (attempt {attempt+1}): {type(e).__name__}: {str(e)[:120]}")
            if is_daily_limit(e):
                raise
            if is_org_restricted(e):
                # Key bị Groq ban tổ chức — rotate ngay, không retry với key này
                print(f"[Groq] 🚫 Key={current_key[-8:]} bị Organization Restricted. Rotating...")
                if key_pool is not None:
                    next_k = key_pool.next_key()
                    if next_k and next_k != current_key:
                        current_key = next_k
                        print(f"[Groq] 🔄 Switched to key={current_key[-8:]}")
                        continue
                raise RuntimeError("Tất cả Groq keys bị restricted. Vui lòng thêm key mới từ org khác vào keys.txt.")
            if is_rate_limited(e) and attempt < max_retries - 1:
                # Rotate sang key khác trong pool nếu có
                if key_pool is not None:
                    next_k = key_pool.next_key()
                    if next_k and next_k != current_key:
                        current_key = next_k
                        print(f"[Groq] 🔄 Rotating to key={current_key[-8:]}")
                time.sleep(1.5 + attempt * 0.75)
                continue
            raise
    else:
        # This part is reached if the loop finishes without 'break'
        raise RuntimeError(f"Failed to get response from Groq after {max_retries} attempts.")

    # Parse JSON
    clean = re.sub(r"```(?:json)?|```", "", raw).strip()
    clean = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', clean)

    try:
        plan = json.loads(clean)
    except json.JSONDecodeError as e1:
        start = clean.find('{')
        if start < 0:
            raise ValueError(f"No JSON: {e1}")
        plan = None
        for end_pos in [clean.rfind('}'), len(clean)]:
            if end_pos <= start:
                continue
            try:
                plan = json.loads(clean[start:end_pos + 1])
                break
            except json.JSONDecodeError:
                pass
        if plan is None:
            plan = _recover_truncated_json(clean[start:])

    if "slides" not in plan:
        raise ValueError("layout_plan missing 'slides' key")
    return plan


def _plan_parallel(skeleton: dict, design_hints: dict,
                   keys: List[str]) -> dict:
    """
    Chia skeleton thành chunks, mỗi chunk giao 1 API key.
    Chạy song song. Nếu key bị TPD (hết quota ngày), tự động
    thử key tiếp theo trong pool thay vì crash ngay.
    """
    chunks  = _split_skeleton(skeleton, CHUNK_SIZE)
    n_chunks = len(chunks)
    n_keys   = len(keys)

    results: List[Optional[dict]] = [None] * n_chunks
    failed_chunks: List[int]   = []   # chunk chưa có kết quả
    exhausted_keys: Set[str]   = set()  # key đã hết TPD

    def _worker(idx: int, mini: dict, key: str):
        try:
            return idx, _call_groq_single(key, mini, design_hints, key_pool=_pool_ref), None
        except Exception as e:
            return idx, None, e

    # Ref pool để truyền vào worker
    from ..key_pool import get_key_pool as _gkp
    _pool_ref = _gkp()

    # Vòng lặp: thử từng key, nếu TPD thì đánh dấu và thử key khác
    key_cursor = 0
    pending = list(range(n_chunks))  # index chunk chưa xong

    while pending:
        # Lấy danh sách key còn dùng được
        available_keys = [k for k in keys if k not in exhausted_keys]
        if not available_keys:
            raise RuntimeError(
                f"Tất cả {n_keys} API key đã hết quota ngày (TPD).\n"
                f"Vui lòng thử lại sau hoặc thêm key từ org khác vào keys.txt."
            )

        # Gán key round-robin cho các chunk đang pending
        assignments = [
            (i, chunks[i], available_keys[j % len(available_keys)])
            for j, i in enumerate(pending)
        ]

        next_pending = []
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(len(assignments), len(available_keys))
        ) as ex:
            futures = {ex.submit(_worker, idx, mini, key): (idx, key)
                       for idx, mini, key in assignments}
            for future in concurrent.futures.as_completed(futures):
                idx, result, err = future.result()
                if err is None:
                    results[idx] = result
                elif is_daily_limit(err):
                    # Key này hết TPD — đánh dấu, chunk sẽ retry với key khác
                    _, bad_key = futures[future]
                    exhausted_keys.add(bad_key)
                    next_pending.append(idx)
                else:
                    # Lỗi thật (network, parse, v.v.) — raise ngay
                    raise RuntimeError(f"Chunk {idx} lỗi: {err}")

        pending = next_pending  # retry với key mới nếu còn chunk bị TPD

    # Merge theo thứ tự
    merged_slides = []
    for plan in results:
        if plan:
            merged_slides.extend(plan.get("slides", []))

    return {"slides": merged_slides}


# ── API Functions ───────────────────────────────────────────────────────────

def plan_layout(skeleton: dict, design_hints: dict = None) -> dict:
    """Send skeleton to Groq → layout_plan.
    
    Tự động chọn chế độ:
      - parallel : nhiều key + nhiều slide → mỗi key xử lý CHUNK_SIZE slide song song
      - sequential: 1 key hoặc ít slide → gọi tuần tự như cũ
    """
    from ..key_pool import get_key_pool

    chart_overrides = {}
    for slide in skeleton.get("slides", []):
        if slide.get("chart_hint") and slide.get("chart_type_hint", "none") != "none":
            idx = slide["index"]
            hint = slide["chart_type_hint"]
            chart_overrides[idx] = hint
            chart_overrides[idx + 1] = hint
            if idx > 0:
                chart_overrides[idx - 1] = hint

    pool = get_key_pool()
    keys = pool.keys  # danh sách đầy đủ, không rotate
    n_slides = len(skeleton.get("slides", []))
    n_keys   = len(keys)

    # ── Chọn chế độ ────────────────────────────────────────────────────────
    use_parallel = n_keys >= 2 and n_slides > CHUNK_SIZE

    _debug_log_path = os.path.join(os.path.dirname(__file__), "ai_debug.log")

    if use_parallel:
        # ── PARALLEL MODE ───────────────────────────────────────────────────
        n_chunks = (n_slides + CHUNK_SIZE - 1) // CHUNK_SIZE
        with open(_debug_log_path, "w", encoding="utf-8") as _f:
            _f.write(f"MODE: PARALLEL — {n_slides} slides → {n_chunks} chunks × {CHUNK_SIZE} | keys available: {n_keys}\n")

        layout_plan = _plan_parallel(skeleton, design_hints or {}, keys)

    else:
        # ── SEQUENTIAL MODE (cũ) ────────────────────────────────────────────
        prompt = layout_prompt(skeleton, design_hints or {})

        with open(_debug_log_path, "w", encoding="utf-8") as _f:
            _f.write(f"MODE: SEQUENTIAL — {n_slides} slides | keys available: {n_keys}\n")
            _f.write(f"{'='*70}\n")
            _f.write("SYSTEM PROMPT\n")
            _f.write(f"{'='*70}\n")
            _f.write(SYSTEM_PROMPT + "\n\n")
            _f.write(f"{'='*70}\n")
            _f.write("USER PROMPT (enriched skeleton)\n")
            _f.write(f"{'='*70}\n")
            _f.write(prompt + "\n")

        last_err = None
        max_retries = 3
        raw_response = ""

        for attempt in range(max_retries):
            key = pool.next_key() if n_keys else None
            if not key:
                raise ValueError(
                    "Không có Groq API key nào.\n"
                    "→ Tạo file keys.txt ở thư mục gốc AIPPTX/ và điền key Groq vào (1 key mỗi dòng).\n"
                    "→ Lấy key miễn phí tại: https://console.groq.com"
                )
            client = Groq(api_key=key)
            try:
                response = client.chat.completions.create(
                    model=MODEL,
                    max_tokens=4096,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user",   "content": prompt},
                    ],
                )
                raw_response = response.choices[0].message.content
                break
            except Exception as e:
                print(f"[Groq] ❌ SEQUENTIAL Error (attempt {attempt+1}): {type(e).__name__}: {str(e)[:120]}")
                last_err = e
                if is_org_restricted(e):
                    # Key bị Groq ban tổ chức — thử key tiếp theo
                    print(f"[Groq] 🚫 Key={key[-8:] if key else '?'} bị Organization Restricted. Trying next key...")
                    if n_keys > 1 and attempt < max_retries - 1:
                        time.sleep(0.5)
                        continue
                    raise RuntimeError("Tất cả Groq keys bị restricted. Vui lòng thêm key mới từ org khác vào keys.txt.")
                if is_rate_limited(e) and n_keys:
                    time.sleep(1.5 + attempt * 0.75)
                    continue
                raise

        with open(_debug_log_path, "a", encoding="utf-8") as _f:
            _f.write(f"\n{'='*70}\nAI RAW RESPONSE\n{'='*70}\n")
            _f.write(raw_response + "\n")

        clean = re.sub(r"```(?:json)?|```", "", raw_response).strip()
        clean = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', clean)

        try:
            layout_plan = json.loads(clean)
        except json.JSONDecodeError as e1:
            start = clean.find('{')
            if start < 0:
                raise ValueError(f"No JSON object found. Raw error: {e1}")
            layout_plan = None
            for end_pos in [clean.rfind('}'), len(clean)]:
                if end_pos <= start:
                    continue
                try:
                    layout_plan = json.loads(clean[start:end_pos + 1])
                    break
                except json.JSONDecodeError:
                    pass
            if layout_plan is None:
                try:
                    layout_plan = _recover_truncated_json(clean[start:])
                except Exception as recover_err:
                    raise ValueError(
                        f"JSON parse failed (likely truncated by token limit). "
                        f"Original error: {e1}. Recovery error: {recover_err}"
                    )

        if "slides" not in layout_plan:
            raise ValueError("layout_plan missing 'slides' key")

    # ── Apply chart_overrides (cả 2 mode) ──────────────────────────────────
    for slide_plan in layout_plan.get("slides", []):
        idx = slide_plan.get("index", -1)
        if idx in chart_overrides and slide_plan.get("chart_type", "none") == "none":
            forced = chart_overrides[idx]
            slide_plan["chart_type"] = forced
            if slide_plan.get("layout", "") not in ("split_left", "full_chart"):
                slide_plan["layout"] = "split_left"

    return layout_plan
