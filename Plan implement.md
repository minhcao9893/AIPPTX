🗺️ Plan implement — theo thứ tự ưu tiên
🔴 ƯU TIÊN 1 — app.py patch (unblock toàn bộ UI)
Việc cần làm:
1. Xóa biến HTML = """...""" (inline HTML cũ)
2. Thêm route GET / → đọc app_shell.html bằng open().read()
   (hoặc dùng send_from_directory nếu đặt trong static/)
3. Thêm route GET /static/ui_modules/<path:filename>
   → send_from_directory(APP_DIR / "ui_modules", filename)
4. Import bp_input, bp_design từ modules/
5. app.register_blueprint(bp_input)
6. app.register_blueprint(bp_design)
7. Giữ nguyên các route cũ (/api/files, /api/design, /api/generate legacy)
Gotcha: bp_input và bp_design đang có route /api/generate trùng với route cũ → cần đổi prefix hoặc xoá route legacy sau khi blueprint hoạt động.

🟠 ƯU TIÊN 2 — routes_input.py (Step I backend)
4 endpoints cần implement thật:
pythonPOST /api/parse-docx-text
  ├── nhận: multipart file hoặc { filename: str } (từ input/ folder)
  ├── gọi: extract_text_from_docx(path) — từ input_mask.py
  ├── trả: { text: str, slide_count: int, mode_hint: "trigger"|"raw" }
  └── mode_hint: nếu text có {Slide N} → "trigger", ngược lại → "raw"

POST /api/save-edited-text
  ├── nhận: { session_id: str, text: str }
  ├── ghi vào: _SESSION_TEXT[session_id] = { text, mode }
  └── trả: { ok: True }

POST /api/ai-split-docx
  ├── nhận: multipart file
  ├── gọi: split_docx_with_ai(path) — từ input_ai_splitter.py
  │         (bên trong: extract_text → mask → call_ai → unmask)
  └── trả: { trigger_text: str, slide_count: int }

POST /api/parse-slides
  ├── nhận: { text: str } hoặc { session_id: str }
  ├── gọi: parse_docx(text_or_path) — cần thêm adapter parse_from_text()
  └── trả: { slides: [ { index, title, has_chart, content_blocks } ] }
Gotcha: docx_parser_core.parse_docx() hiện nhận file_path, chưa có parse_from_text(text_str) → cần thêm adapter hoặc viết tempfile wrapper.

🟠 ƯU TIÊN 3 — input_mask.py (dependency của routes_input)
Các hàm cần implement:
pythonextract_text_from_docx(path: str) -> str
  # Dùng python-docx: doc = Document(path)
  # Gộp paragraphs + tables thành plain text
  # Giữ nguyên dấu xuống dòng, bỏ header/footer

mask_text(text: str) -> Tuple[str, dict]
  # Load blacklist từ list_store.py
  # Regex scan → tìm match → thay bằng alias (Công-ty-1, Người-2...)
  # Trả (masked_text, mapping: { alias: original })
  # Mapping cần lưu để unmask sau

unmask_text(structured: str, mapping: dict) -> str
  # Duyệt mapping, str.replace(alias, original)
  # Thứ tự: longer alias trước (tránh partial replace)
Gotcha: Alias phải unique trong 1 session — dùng counter, không dùng hash.

🟠 ƯU TIÊN 4 — input_ai_splitter.py (dependency của routes_input)
Hàm chính:
pythonsplit_docx_with_ai(path: str) -> str
  # 1. text = extract_text_from_docx(path)         ← dùng input_mask.py
  # 2. masked, mapping = mask_text(text)
  # 3. prompt = build_split_prompt(masked)
  #    prompt yêu cầu AI: thêm {Slide N} marker vào đầu mỗi phần
  #    giữ nguyên nội dung, không thêm/bớt thông tin
  # 4. result = call_groq(prompt)                  ← dùng ai_planner_core._call_groq
  # 5. structured = unmask_text(result, mapping)
  # 6. return structured

build_split_prompt(masked_text: str) -> str
  # System: "Bạn là công cụ chia văn bản. Chỉ thêm marker {Slide N}..."
  # User: masked_text
Gotcha: AI có thể thêm nội dung → cần validate: số từ output phải ≈ input ± 10%. Nếu lệch nhiều → retry 1 lần.

🟡 ƯU TIÊN 5 — design_theme.py
Hàm cần implement:
pythonTHEMES = {
  "corporate":  { primary: "#1E2761", secondary: "#4A90D9", ... },
  "minimal":    { ... },
  "vibrant":    { ... },
  "dark":       { ... },
  "earth":      { ... },
}

apply_theme_to_design(theme: str, custom_colors: dict) -> dict
  # 1. Load design_template.json
  # 2. base_colors = THEMES[theme]
  # 3. Merge custom_colors lên (override nếu user đã chọn)
  # 4. Ghi vào design dict: design["colors"] = merged_colors
  # 5. return design dict

save_design(design: dict) -> None
  # json.dump vào design_template.json (indent=2)
Gotcha: custom_colors từ frontend có thể thiếu key → cần .get() với fallback về theme defaults, không raise KeyError.

🟡 ƯU TIÊN 6 — layout_engine.py
Hàm cần implement:
python@dataclass
class BlockRect:
  left: float    # inches
  top: float
  width: float
  height: float

SLIDE_W = 13.33  # inches (widescreen 16:9)
SLIDE_H = 7.5

compute_layout(config: dict) -> List[BlockRect]
  # config = { layout_type: "vertical"|"horizontal"|"table2"|"table3",
  #            pct: [40, 60],   ← % chia ô (last ô = 100 - sum)
  #            margin: 0.3 }    ← inches
  # 
  # vertical:    chia theo chiều dọc (top/bottom)
  # horizontal:  chia theo chiều ngang (left/right)
  # table2:      2 cột đều
  # table3:      3 cột đều
  #
  # Trả List[BlockRect] — mỗi phần tử = 1 ô nội dung

_split_vertical(pct, margin) -> List[BlockRect]
_split_horizontal(pct, margin) -> List[BlockRect]
_split_table(n_cols, margin) -> List[BlockRect]
Gotcha: Đơn vị % → inches phải trừ margin đôi ở mỗi bên giữa ô. Công thức: width = (SLIDE_W - margin*(n+1)) * pct/100.

🟡 ƯU TIÊN 7 — routes_design.py (Step II backend)
4 endpoints cần implement thật:
pythonPOST /api/apply-theme
  ├── nhận: { theme: str, colors: { primary, secondary, accent, bg, text } }
  ├── gọi: apply_theme_to_design(theme, colors) → save_design()
  └── trả: { ok: True }

POST /api/generate
  ├── nhận: { session_id, slides_config, layout_config }
  │         slides_config = [ { index, tableMode, show_chart, show_insight } ]
  │         layout_config = { layout_type, pct, margin }
  ├── async thread:
  │   a. parse-slides (lấy từ _SESSION_TEXT[session_id])
  │   b. sanitize (sanitizer_core)
  │   c. compute_layout(layout_config) → gắn vào plan
  │   d. plan_layout (ai_planner_core)
  │   e. build (builder_core) → output/xxx.pptx
  │   f. copy to Desktop/output/ nếu có
  │   g. _progress = { status:"done", filename: xxx.pptx }
  └── trả ngay: { ok: True, message: "Đang generate..." }

GET /api/progress
  └── trả: _progress dict hiện tại

GET /api/download/<filename>
  └── send_file(OUTPUT_DIR / filename, as_attachment=True)
Gotcha: Thread generate cần bắt exception và set _progress["status"] = "error" — nếu không, frontend poll mãi không biết fail.

📋 Tóm tắt thứ tự implement
1. app.py patch          ← unblock UI ngay
2. routes_input.py       ← Step I chạy được
3. input_mask.py         ← dependency của routes_input
4. input_ai_splitter.py  ← mode 2
5. design_theme.py       ← Step II theme
6. layout_engine.py      ← Step II layout
7. routes_design.py      ← Step II generate
Làm theo thứ tự này thì sau bước 2+3 đã có thể test Step I end-to-end.