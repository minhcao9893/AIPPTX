# AIPPTX v2 — AI PowerPoint Generator

Tạo PowerPoint chuyên nghiệp từ file Word (.docx) bằng AI. Dữ liệu thật **không bao giờ rời khỏi máy**.

---

## 📁 Cấu trúc dự án

```
AIPPTX/
│
├── app/
│   ├── app.py                    # Flask server — hiện dùng HTML inline, cần patch sang app_shell.html
│   ├── main.py                   # CLI entry point
│   │
│   ├── docx_parser.py            # (71 dòng) Thin wrapper → modules/docx_parser_core.py
│   ├── sanitizer.py              # (70 dòng) Thin wrapper → modules/sanitizer_core.py
│   ├── ai_planner.py             # (26 dòng) Thin wrapper → modules/ai_planner_core.py
│   ├── builder.py                # (22 dòng) Thin wrapper → modules/builder_core.py
│   │
│   ├── key_pool.py               # Quản lý nhiều API keys, auto-rotate khi 429
│   ├── list_store.py             # Load whitelist/blacklist từ GitHub hoặc local
│   ├── github_repo.py            # GitHub Contents API
│   ├── stage1_list_updater.py    # Auto-cập nhật keyword lists
│   ├── design_editor.py          # GET/POST /api/design — thin wrapper
│   ├── config.json               # Cấu hình model, github keys
│   ├── design_template.json      # Theme + layout design
│   │
│   ├── ui_modules/               # ★ NEW v2 — Full UI rebuild
│   │   ├── app_shell.html        # Layout 2 cột full-screen (Step I + II), dark theme
│   │   ├── app_shell_styles.css  # CSS tự động refactor và tách riêng
│   │   ├── step1_input.js        # Mode toggle, file picker, goNext()
│   │   ├── step1_trigger.js      # Popup hướng dẫn cấu trúc {Slide N} + {Chart}
│   │   ├── step1_ai_processor.js # Helper gọi API /api/ai-split-docx (mode 2)
│   │   ├── step1_preview.js      # Preview + editable textarea (cột RIGHT)
│   │   ├── step1_input_styles.css
│   │   ├── step1_preview_styles.css
│   │   ├── step2_design.js       # 5 theme cards + 5 màu tuỳ chỉnh
│   │   ├── step2_slides.js       # Slide cards: title, toggle, dropdown tableMode
│   │   ├── step2_layout.js       # Chips thành phần + layout 4 kiểu + % ô
│   │   ├── step2_canvas.js       # Colored blocks preview (blue/green/orange...)
│   │   ├── step2_export.js       # Poll progress + download banner
│   │   ├── step2_init.js         # Step2 orchestrator + global toast()
│   │   └── step2_design_styles.css
│   │
│   └── modules/                  # Core logic + NEW pseudocode modules
│       ├── docx_parser_core.py   # (~200 dòng) parse_docx(), infer_chart_type()
│       ├── sanitizer_core.py     # (~400 dòng) NameMasker, mask_tree()
│       ├── ai_planner_core.py    # (~280 dòng) plan_layout(), enrich_skeleton()
│       ├── builder_core.py       # (<400 dòng) Entry point build(), Layout globals
│       ├── builder_components.py # (~400 dòng) Hàm dựng hình đồ họa (chart, split)
│       ├── builder_utils.py      # (~70 dòng) PPTX utils (_fmt, _inches)
│       ├── design_editor_core.py # load/save design_template.json, flatten_for_ui()
│       │
│       ├── input_mask.py         # ★ PSEUDOCODE — mask/unmask text thô mode 2
│       ├── input_ai_splitter.py  # ★ PSEUDOCODE — Word dài → AI → trigger structured
│       ├── design_theme.py       # ★ PSEUDOCODE — 5 màu + theme → design_template.json
│       ├── layout_engine.py      # ★ PSEUDOCODE — % config → BlockRect (inches)
│       ├── routes_input.py       # ★ PSEUDOCODE — Blueprint bp_input (Step I routes)
│       └── routes_design.py      # ★ PSEUDOCODE — Blueprint bp_design (Step II routes)
│
├── input/                        # Đặt file .docx vào đây
├── output/                       # File .pptx output
├── template/                     # Template PowerPoint (.pptx)
├── run/                          # Run scripts
│
├── requirements.txt
├── RUN.bat                       # Double-click để chạy
└── session-log.md                # Dev session log
```

---

## 🔄 Workflow v2

```
┌──────────────────────────────────────────────────────┐
│  STEP I — Input                                       │
│                                                      │
│  Mode 1 (trigger sẵn):                               │
│    .docx → parse text → preview editor               │
│                                                      │
│  Mode 2 (Word dài):                                  │
│    .docx → mask text → AI split → trigger structured │
│    (input_mask.py + input_ai_splitter.py)            │
└──────────────────────┬───────────────────────────────┘
                       │ trigger text (có {Slide N}, {Chart})
                       ▼
┌──────────────────────────────────────────────────────┐
│  STEP II — Design + Generate                          │
│                                                      │
│  1. Chọn theme / màu  → design_theme.py              │
│  2. Cấu hình từng slide (chart/content/insight)      │
│  3. Cấu hình layout % → layout_engine.py             │
│  4. Generate:                                        │
│     parse-slides → sanitize → ai_planner → builder   │
│  5. Download .pptx                                   │
└──────────────────────────────────────────────────────┘
```

---

## 🗂️ API Endpoints

### Step I (Blueprint `bp_input`)
| Method | Route | Chức năng |
|--------|-------|----------|
| POST | `/api/parse-docx-text` | Extract text từ .docx → preview |
| POST | `/api/save-edited-text` | Lưu text đã chỉnh vào session |
| POST | `/api/ai-split-docx` | Mode 2: Word dài → AI → trigger |
| POST | `/api/parse-slides` | Trigger text → danh sách slide objects |

### Step II (Blueprint `bp_design`)
| Method | Route | Chức năng |
|--------|-------|----------|
| POST | `/api/apply-theme` | Theme + colors → design_template.json |
| POST | `/api/generate` | Full config → tạo PPTX (async) |
| GET | `/api/progress` | Poll tiến trình generate |
| GET | `/api/download/<fn>` | Tải file PPTX |

### Legacy (app.py)
| Method | Route | Chức năng |
|--------|-------|----------|
| GET | `/api/design` | Load design editor |
| POST | `/api/design` | Save design patch |
| GET | `/api/files` | List input files |
| POST | `/api/generate` | Generate (old route — sẽ chuyển sang bp_design) |

---

## 🚀 Cách chạy

```bash
# Double-click RUN.bat hoặc:
cd AIPPTX
python -m app.main
```

Mở trình duyệt: `http://localhost:5000`

---

## 🔒 Bảo mật dữ liệu

| Thông tin | Gửi lên AI? |
|----------|------------|
| Số liệu thật (doanh thu, KPI) | ❌ Không (masked) |
| Tên công ty, người, địa danh | ❌ Không (masked) |
| Cấu trúc slide (loại biểu đồ) | ✅ Có |
| Magnitude (HIGH/MID/LOW) | ✅ Có |

---

## 📦 Cài đặt

```bash
pip install -r requirements.txt
```

Yêu cầu: Python 3.10+

---

## ⚠️ Trạng thái hiện tại (v2 — in-progress)

| Phần | Status |
|------|--------|
| UI modules (JS + HTML) | ✅ Viết xong (pseudocode/spec) |
| Python modules (pseudocode) | ✅ Spec xong, chưa implement |
| app.py patch (serve shell + Blueprint) | 🔄 **ĐANG LÀM** |
| input_mask.py | ⏳ Chờ implement |
| input_ai_splitter.py | ⏳ Chờ implement |
| design_theme.py | ⏳ Chờ implement |
| layout_engine.py | ⏳ Chờ implement |
| routes_input.py | ⏳ Chờ implement |
| routes_design.py | ⏳ Chờ implement |

---

End of README
