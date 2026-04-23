"""
app.py — Web UI (Flask localhost)
===================================
Non-tech user interface:
  1. Mở http://localhost:5000
  2. Chọn file Word từ folder input/
  3. Bấm Generate → AI tạo PPTX tự động
  4. Download PPTX — hoặc lấy từ folder output/

Key management:
  - Đọc keys.txt từ GitHub private repo (cấu hình trong config.json)
  - Tự động rotate key khi hit rate limit (HTTP 429)
  - Không cần user nhập key
"""

import os
import json
import threading
import webbrowser
from pathlib import Path
from dotenv import load_dotenv

# Load .env.local từ thư mục gốc project (nếu có) — chỉ có tác dụng khi chạy local
_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env.local")
from datetime import datetime

from flask import Flask, render_template_string, jsonify, request, send_file
from flask import send_from_directory
from .design_editor import get_design_json, save_design_json
from .modules.routes_input import bp_input
from .modules.routes_design import bp_design

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT_DIR      = Path(__file__).resolve().parents[1]
APP_DIR       = Path(__file__).resolve().parent

# If running on Render with persistent disk, use it. Otherwise use local dirs.
if os.environ.get("RENDER"):
    PERSISTENT_DIR = Path("/app/persistent")
    INPUT_DIR      = PERSISTENT_DIR / "input"
    OUTPUT_DIR     = PERSISTENT_DIR / "output"
    TEMPLATE_DIR   = PERSISTENT_DIR / "template"
else:
    INPUT_DIR      = ROOT_DIR / "input"
    OUTPUT_DIR     = ROOT_DIR / "output"
    TEMPLATE_DIR   = ROOT_DIR / "template"
DESIGN_FILE   = APP_DIR / "design_template.json"
CONFIG_FILE   = APP_DIR / "config.json"

# Default template (auto-used if user doesn't pick one)
DEFAULT_TEMPLATE = TEMPLATE_DIR / "template.pptx"

INPUT_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
TEMPLATE_DIR.mkdir(exist_ok=True)

app = Flask(__name__, static_folder=None)
_progress = {"status": "idle", "message": "", "file": ""}

# ── Register Blueprints ───────────────────────────────────────────────────────
app.register_blueprint(bp_input)
app.register_blueprint(bp_design)


# ── HTML Template ─────────────────────────────────────────────────────────────
HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI-PPTX Generator</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', Arial, sans-serif; background: #f0f2f8;
         min-height: 100vh; display: flex; align-items: center; justify-content: center; }
  .card { background: white; border-radius: 16px; padding: 40px 48px;
          width: 560px; box-shadow: 0 8px 32px rgba(30,39,97,0.12); }
  .logo { font-size: 28px; font-weight: 800; color: #1E2761; letter-spacing: 1px; }
  .logo span { color: #028090; }
  .subtitle { color: #666; margin-top: 6px; font-size: 14px; }
  h2 { color: #1E2761; margin: 28px 0 16px; font-size: 16px; font-weight: 600; }
  .file-list { border: 1px solid #dde; border-radius: 8px; overflow: hidden; }
  .file-item { padding: 12px 16px; cursor: pointer; display: flex;
               align-items: center; gap: 10px; transition: background 0.15s;
               border-bottom: 1px solid #eef; font-size: 14px; }
  .file-item:last-child { border-bottom: none; }
  .file-item:hover { background: #f0f4ff; }
  .file-item.selected { background: #e8edff; font-weight: 600; color: #1E2761; }
  .file-icon { font-size: 18px; }
  .empty { padding: 24px; color: #999; text-align: center; font-size: 13px; }
  .template-select { width: 100%; padding: 9px 12px; border: 1px solid #dde;
                     border-radius: 6px; font-size: 14px; color: #333;
                     background: white; margin-top: 4px; }
  .template-select:focus { outline: none; border-color: #028090; }
  .design-btn { padding: 10px 20px; background: #028090; color: white;
         border: none; border-radius: 8px; font-size: 14px; font-weight: 600;
         cursor: pointer; margin-top: 20px; transition: background 0.2s; }
  .design-btn:hover { background: #026f7a; }
  /* ── Design Panel ── */
  .design-panel { display: none; margin-top: 20px; border: 1px solid #dde;
                  border-radius: 12px; overflow: hidden; }
  .design-panel.show { display: block; }
  .design-panel-header { background: #1E2761; color: white; padding: 14px 20px;
                         display: flex; justify-content: space-between; align-items: center; }
  .design-panel-header span { font-weight: 700; font-size: 15px; }
  .design-close { background: none; border: none; color: white; font-size: 18px;
                  cursor: pointer; line-height: 1; }
  .design-tabs { display: flex; border-bottom: 1px solid #dde; background: #f8f9ff; }
  .design-tab { padding: 10px 16px; font-size: 13px; cursor: pointer; border: none;
                background: none; color: #555; font-weight: 500; border-bottom: 2px solid transparent;
                transition: all 0.15s; }
  .design-tab.active { color: #1E2761; border-bottom-color: #028090; font-weight: 700; }
  .design-tab:hover { background: #eef0ff; }
  .design-body { padding: 20px 24px; max-height: 420px; overflow-y: auto; }
  .design-field { display: flex; align-items: center; justify-content: space-between;
                  padding: 7px 0; border-bottom: 1px solid #f0f0f0; gap: 12px; }
  .design-field:last-child { border-bottom: none; }
  .design-label { font-size: 13px; color: #444; flex: 1; }
  .design-input { border: 1px solid #dde; border-radius: 5px; padding: 4px 8px;
                  font-size: 13px; color: #333; width: 160px; }
  .design-input:focus { outline: none; border-color: #028090; }
  input[type=color].design-input { padding: 2px 4px; height: 32px; width: 60px; cursor: pointer; }
  .palette-row { display: flex; gap: 6px; }
  .palette-row input[type=color] { width: 36px; height: 30px; padding: 1px 2px;
                                   border: 1px solid #dde; border-radius: 4px; cursor: pointer; }
  .design-footer { padding: 14px 24px; border-top: 1px solid #dde; background: #f8f9ff;
                   display: flex; gap: 10px; }
  .design-save-btn { padding: 9px 20px; background: #1E2761; color: white; border: none;
                     border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer; }
  .design-save-btn:hover { background: #2a3580; }
  .design-reset-btn { padding: 9px 16px; background: white; color: #666; border: 1px solid #dde;
                      border-radius: 6px; font-size: 14px; cursor: pointer; }
  .design-reset-btn:hover { background: #f5f5f5; }
  .design-msg { font-size: 13px; color: #028090; align-self: center; margin-left: auto; display: none; }
  .btn { width: 100%; padding: 14px; background: #1E2761; color: white;
         border: none; border-radius: 8px; font-size: 16px; font-weight: 600;
         cursor: pointer; margin-top: 24px; transition: background 0.2s; }
  .btn:hover:not(:disabled) { background: #2a3580; }
  .btn:disabled { background: #aab; cursor: not-allowed; }
  .progress-box { margin-top: 20px; padding: 16px; border-radius: 8px;
                  background: #f8f9ff; border: 1px solid #dde; display: none; }
  .progress-box.show { display: block; }
  .progress-msg { font-size: 14px; color: #444; }
  .spinner { display: inline-block; width: 14px; height: 14px;
             border: 2px solid #1E2761; border-top-color: transparent;
             border-radius: 50%; animation: spin 0.7s linear infinite;
             margin-right: 8px; vertical-align: middle; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .result-box { display: none; margin-top: 16px; padding: 16px;
                border-radius: 8px; background: #e8f8f5; border: 1px solid #b2dfdb; }
  .result-box.show { display: block; }
  .dl-btn { display: inline-block; margin-top: 10px; padding: 10px 20px;
            background: #028090; color: white; border-radius: 6px;
            text-decoration: none; font-size: 14px; font-weight: 600; }
  .dl-btn:hover { background: #026f7a; }
  .error-box { display: none; margin-top: 16px; padding: 14px; border-radius: 8px;
               background: #fff0f0; border: 1px solid #ffcdd2; color: #b71c1c; font-size: 13px; }
  .error-box.show { display: block; }
  .refresh-btn { background: none; border: none; color: #028090; cursor: pointer;
                 font-size: 13px; text-decoration: underline; margin-top: 6px; }
  .template-hint { font-size: 11px; color: #999; margin-top: 4px; }
</style>
</head>
<body>
<div class="card">
  <div class="logo">AI<span>-PPTX</span></div>
  <div class="subtitle">Tạo PowerPoint từ file Word — dữ liệu không rời máy bạn</div>

  <h2>📁 Chọn file Word trong folder input/</h2>
  <div class="file-list" id="fileList"><div class="empty">Đang tải...</div></div>
  <button class="refresh-btn" onclick="loadFiles()">🔄 Tải lại danh sách</button>

  <button class="design-btn" onclick="toggleDesign()">🎨 Design</button>

  <!-- Design Panel -->
  <div class="design-panel" id="designPanel">
    <div class="design-panel-header">
      <span>🎨 Design Settings</span>
      <button class="design-close" onclick="toggleDesign()">✕</button>
    </div>
    <div class="design-tabs" id="designTabs"></div>
    <div class="design-body" id="designBody">Đang tải...</div>
    <div class="design-footer">
      <button class="design-save-btn" onclick="saveDesign()">💾 Lưu</button>
      <button class="design-reset-btn" onclick="resetDesign()">↩ Reset</button>
      <span class="design-msg" id="designMsg"></span>
    </div>
  </div>

  <h2>🎨 Chọn template PowerPoint</h2>
  <select class="template-select" id="templateSelect">
    <option value="__default__">📊 template.pptx (mặc định)</option>
  </select>
  <div class="template-hint">
    Đặt file .pptx mẫu vào folder <code>template/</code> rồi bấm
    <button class="refresh-btn" style="margin-left:4px" onclick="loadTemplates()">🔄 Tải lại</button>
  </div>

  <button class="btn" id="genBtn" disabled onclick="generate()">
    ⚡ Tạo PPTX
  </button>

  <div class="progress-box" id="progressBox">
    <span class="spinner"></span>
    <span class="progress-msg" id="progressMsg">Đang xử lý...</span>
  </div>

  <div class="result-box" id="resultBox">
    ✅ <strong>Tạo thành công!</strong><br>
    File đã lưu vào folder <code>output/</code><br>
    <a class="dl-btn" id="dlLink" href="#">⬇ Download PPTX</a>
  </div>

  <div class="error-box" id="errorBox"></div>
</div>

<script>
let selectedFile = null;

async function loadFiles() {
  try {
    const res = await fetch('/api/files');
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    const list = document.getElementById('fileList');
    if (!data.files || data.files.length === 0) {
      list.innerHTML = '<div class="empty">Chưa có file .docx nào trong folder input/<br>Hãy copy file Word vào đó rồi bấm 🔄</div>';
      return;
    }
    list.innerHTML = data.files.map(f => {
      const safeId = f.replace(/[^a-zA-Z0-9]/g, '_');
      return `<div class="file-item" onclick="selectFile('${f}')" id="fi_${safeId}">
                <span class="file-icon">📝</span> ${f}
              </div>`;
    }).join('');
  } catch (err) {
    document.getElementById('fileList').innerHTML =
      `<div class="empty" style="color:#b71c1c">❌ Lỗi tải danh sách file: ${err.message}</div>`;
  }
}

async function loadTemplates() {
  try {
    const res = await fetch('/api/templates');
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    const sel = document.getElementById('templateSelect');
    const cur = sel.value;
    // Keep default option, add rest
    sel.innerHTML = '<option value="__default__">📊 template.pptx (mặc định)</option>';
    (data.templates || []).forEach(t => {
      if (t === 'template.pptx') return; // already in default
      const opt = document.createElement('option');
      opt.value = t;
      opt.textContent = '📊 ' + t;
      sel.appendChild(opt);
    });
    if (cur && cur !== '__default__') sel.value = cur;
  } catch (err) {
    console.error('Lỗi tải template:', err);
  }
}

function selectFile(name) {
  selectedFile = name;
  document.querySelectorAll('.file-item').forEach(el => el.classList.remove('selected'));
  const safeId = name.replace(/[^a-zA-Z0-9]/g, '_');
  document.getElementById('fi_' + safeId)?.classList.add('selected');
  document.getElementById('genBtn').disabled = false;
}

async function generate() {
  if (!selectedFile) return;
  document.getElementById('genBtn').disabled = true;
  document.getElementById('progressBox').classList.add('show');
  document.getElementById('resultBox').classList.remove('show');
  document.getElementById('errorBox').classList.remove('show');
  document.getElementById('progressMsg').textContent = 'Đang khởi động...';

  const templateVal = document.getElementById('templateSelect').value;

  const res = await fetch('/api/generate-legacy', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      filename: selectedFile,
      template: templateVal  // '__default__' or specific filename
    })
  });
  const data = await res.json();

  if (data.error) {
    document.getElementById('progressBox').classList.remove('show');
    document.getElementById('errorBox').innerHTML =
      '❌ Lỗi: ' + data.error.replace(/\\n/g, '<br>');
    document.getElementById('errorBox').classList.add('show');
    document.getElementById('genBtn').disabled = false;
    return;
  }

  pollProgress(data.job_id);
}

async function pollProgress(jobId) {
  const res = await fetch('/api/progress/' + jobId);
  const data = await res.json();
  document.getElementById('progressMsg').textContent = data.message;

  if (data.status === 'done') {
    document.getElementById('progressBox').classList.remove('show');
    document.getElementById('resultBox').classList.add('show');
    document.getElementById('dlLink').href = '/api/download/' + data.file;
    document.getElementById('genBtn').disabled = false;
  } else if (data.status === 'error') {
    document.getElementById('progressBox').classList.remove('show');
    document.getElementById('errorBox').innerHTML =
      '❌ ' + data.message.replace(/\\n/g, '<br>');
    document.getElementById('errorBox').classList.add('show');
    document.getElementById('genBtn').disabled = false;
  } else {
    setTimeout(() => pollProgress(jobId), 1500);
  }
}

// ── Design Panel ─────────────────────────────────────────────────────────────
let _designSchema = null;
let _designValues = null;
let _designOriginal = null;
let _activeTab = null;

async function toggleDesign() {
  const panel = document.getElementById('designPanel');
  if (panel.classList.contains('show')) {
    panel.classList.remove('show');
    return;
  }
  if (!_designSchema) await loadDesign();
  panel.classList.add('show');
}

async function loadDesign() {
  const res = await fetch('/api/design');
  const data = await res.json();
  _designSchema = data.schema;
  _designValues = Object.assign({}, data.values);
  _designOriginal = Object.assign({}, data.values);
  renderDesignTabs();
}

function renderDesignTabs() {
  const tabsEl = document.getElementById('designTabs');
  const tabs = Object.keys(_designSchema);
  _activeTab = tabs[0];
  tabsEl.innerHTML = tabs.map(t =>
    `<button class="design-tab${t === _activeTab ? ' active' : ''}" onclick="switchTab('${t}')">${t}</button>`
  ).join('');
  renderDesignBody(_activeTab);
}

function switchTab(tabName) {
  _activeTab = tabName;
  document.querySelectorAll('.design-tab').forEach(b =>
    b.classList.toggle('active', b.textContent === tabName)
  );
  renderDesignBody(tabName);
}

function renderDesignBody(tabName) {
  const tab = _designSchema[tabName];
  const body = document.getElementById('designBody');
  body.innerHTML = tab.fields.map(field => {
    const val = _designValues[field.key];
    let input = '';
    if (field.type === 'color') {
      const hex = (val || '#000000').toString();
      const display = hex.startsWith('#') ? hex : '#000000';
      input = `<input type="color" class="design-input" data-key="${field.key}" value="${display}" oninput="patchVal('${field.key}', this.value)">`;
    } else if (field.type === 'colors') {
      const arr = Array.isArray(val) ? val : ['#000000','#000000','#000000','#000000','#000000'];
      const pickers = arr.map((c, i) =>
        `<input type="color" data-key="${field.key}" data-idx="${i}" value="${c}" oninput="patchPalette('${field.key}', ${i}, this.value)">`
      ).join('');
      input = `<div class="palette-row">${pickers}</div>`;
    } else if (field.type === 'bool') {
      input = `<select class="design-input" data-key="${field.key}" onchange="patchVal('${field.key}', this.value === 'true')">
        <option value="true"${val === true ? ' selected' : ''}>✅ Bật</option>
        <option value="false"${val === false ? ' selected' : ''}>❌ Tắt</option>
      </select>`;
    } else if (field.type === 'number') {
      input = `<input type="number" class="design-input" step="any" data-key="${field.key}" value="${val ?? ''}" oninput="patchVal('${field.key}', parseFloat(this.value))">`;
    } else {
      input = `<input type="text" class="design-input" data-key="${field.key}" value="${val ?? ''}" oninput="patchVal('${field.key}', this.value)">`;
    }
    return `<div class="design-field"><span class="design-label">${field.label}</span>${input}</div>`;
  }).join('');
}

function patchVal(key, value) {
  _designValues[key] = value;
}

function patchPalette(key, idx, value) {
  if (!Array.isArray(_designValues[key])) _designValues[key] = [];
  _designValues[key][idx] = value;
}

async function saveDesign() {
  const res = await fetch('/api/design', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(_designValues)
  });
  const data = await res.json();
  const msg = document.getElementById('designMsg');
  msg.style.display = 'inline';
  msg.textContent = data.ok ? `✅ Đã lưu ${data.saved} thay đổi` : '❌ Lỗi lưu';
  setTimeout(() => { msg.style.display = 'none'; }, 3000);
}

function resetDesign() {
  if (!_designOriginal) return;
  _designValues = Object.assign({}, _designOriginal);
  renderDesignBody(_activeTab);
  const msg = document.getElementById('designMsg');
  msg.style.display = 'inline';
  msg.textContent = '↩ Đã reset về giá trị gốc';
  setTimeout(() => { msg.style.display = 'none'; }, 2500);
}

window.onload = () => { loadFiles(); loadTemplates(); };
</script>
</body>
</html>
"""


# ── Flask Routes ──────────────────────────────────────────────────────────────

_jobs = {}


@app.route("/")
def index():
    from flask import redirect
    return redirect("/v2")


@app.route("/v2")
def index_v2():
    """Serve new UI shell — JS modules inlined directly to avoid static route conflicts."""
    shell_path = APP_DIR / "ui_modules" / "app_shell.html"
    if not shell_path.exists():
        return "app_shell.html not found", 404
    html = shell_path.read_text(encoding="utf-8")
    js_modules = [
        "step1_input.js", "step1_trigger.js", "step1_ai_processor.js", "step1_preview.js",
        "step2_design.js", "step2_design_panel.js", "step2_slides.js", "step2_layout.js",
        "step2_canvas.js", "step2_preview.js", "step2_export.js", "step2_init.js"
    ]
    inline_scripts = []
    ui_dir = APP_DIR / "ui_modules"
    for m in js_modules:
        js_path = ui_dir / m
        if js_path.exists():
            js_content = js_path.read_text(encoding="utf-8")
            inline_scripts.append(f'<script>/* {m} */\n{js_content}\n</script>')
        else:
            inline_scripts.append(f'<script>console.error("MISSING: {m}");</script>')
    scripts = "\n".join(inline_scripts)
    html = html.replace("</body>", f"{scripts}\n</body>")
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/static/ui_modules/<path:filename>")
def serve_ui_module(filename):
    """Serve JS/CSS files from ui_modules/."""
    return send_from_directory(str(APP_DIR / "ui_modules"), filename)


@app.route("/api/files")
def list_files():
    files = sorted([f.name for f in INPUT_DIR.glob("*.docx")])
    return jsonify({"files": files})


@app.route("/api/design", methods=["GET"])
def design_get():
    return jsonify(get_design_json(DESIGN_FILE))


@app.route("/api/design", methods=["POST"])
def design_post():
    patch = request.json or {}
    return jsonify(save_design_json(DESIGN_FILE, patch))


@app.route("/api/templates")
def list_templates():
    templates = sorted([f.name for f in TEMPLATE_DIR.glob("*.pptx")])
    return jsonify({"templates": templates})


@app.route("/api/generate-legacy", methods=["POST"])
def generate_legacy():
    filename      = request.json.get("filename", "")
    template_name = request.json.get("template", "__default__")
    docx_path     = INPUT_DIR / filename

    if not docx_path.exists():
        return jsonify({"error": f"File không tồn tại: {filename}"})

    # Resolve template path: use default if '__default__' or empty
    if not template_name or template_name == "__default__":
        template_path = str(DEFAULT_TEMPLATE) if DEFAULT_TEMPLATE.exists() else None
    else:
        tp = TEMPLATE_DIR / template_name
        if not tp.exists():
            return jsonify({"error": f"Template không tồn tại: {template_name}"})
        template_path = str(tp)

    # ── Initialize key pool ────────────────────────────────────────────────
    try:
        from .key_pool import get_key_pool
        from . import key_pool as _kp
        pool = get_key_pool(force_reload=True)
        if len(pool) == 0:
            # Đọc _LAST_GITHUB_ERROR sau khi get_key_pool chạy xong
            gh_err = _kp._LAST_GITHUB_ERROR
            detail = f"\n\n🔍 Lỗi GitHub: {gh_err}" if gh_err else ""
            return jsonify({
                "error": (
                    "❌ Không tìm thấy API keys!\n"
                    f"Repo: {pool.__class__.__module__} | Kiểm tra PAT token còn hạn không.{detail}\n\n"
                    "Cấu hình GitHub private repo trong config.json:\n"
                    "- github_keys.owner\n- github_keys.repo\n"
                    "- github_keys.path (keys.txt)\n- github_keys.pat (GitHub token)"
                )
            })
    except Exception as e:
        return jsonify({"error": f"❌ Lỗi khi tải key pool: {str(e)}"})
    job_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    _jobs[job_id] = {"status": "running", "message": "Bắt đầu xử lý...", "file": ""}

    t = threading.Thread(
        target=_run_pipeline,
        args=(job_id, str(docx_path), filename, template_path),
        daemon=True
    )
    t.start()

    return jsonify({"job_id": job_id})


@app.route("/api/progress/<job_id>")
def progress(job_id):
    return jsonify(_jobs.get(job_id, {"status": "error", "message": "Job không tồn tại"}))


@app.route("/api/download/<path:filename>")
def download(filename):
    path = OUTPUT_DIR / filename
    if not path.exists():
        return "File không tồn tại", 404
    return send_file(str(path), as_attachment=True)


# ── Pipeline runner (runs in background thread) ───────────────────────────────

def _update(job_id: str, message: str, status: str = "running"):
    _jobs[job_id]["message"] = message
    _jobs[job_id]["status"]  = status


def _run_pipeline(job_id: str, docx_path: str, source_filename: str,
                  template_path: str = None):
    try:
        # Step 1: Parse Word
        _update(job_id, "📝 Đang đọc file Word...")
        from .docx_parser import docx_to_input_json
        raw_data  = docx_to_input_json(docx_path)
        n_slides  = len(raw_data.get("slides", []))
        _update(job_id, f"✅ Đọc xong — {n_slides} slides")

        # Stage 1: Auto-update whitelist/blacklist
        # Chạy ngay sau parse, trước sanitize. Nếu fail thì skip, không crash pipeline.
        _update(job_id, "🧠 Stage 1: Cập nhật whitelist/blacklist...")
        try:
            from .stage1_list_updater import run_stage1_update
            n_w, n_b = run_stage1_update(raw_data, dry_run=False, verbose=False)
            _update(job_id, f"✅ Stage 1: +{n_w} whitelist, +{n_b} blacklist")
        except Exception as _s1_err:
            import sys as _sys
            print(f"⚠️ Stage 1 failed (continuing): {_s1_err}", file=_sys.stderr)
            _update(job_id, "⚠️ Stage 1 skipped (tiếp tục pipeline...)")

        # Step 2: Sanitize
        _update(job_id, "🔒 Đang mã hóa dữ liệu nhạy cảm...")
        from .sanitizer import sanitize, build_skeleton_metadata
        skeleton, name_map = sanitize(raw_data)
        skeleton = build_skeleton_metadata(skeleton)
        _update(job_id, f"✅ Đã mask {len(name_map)} tên (Company/Region/Person)")

        # Step 3: Load design
        design = {}
        if DESIGN_FILE.exists():
            design = json.loads(DESIGN_FILE.read_text(encoding="utf-8"))

        # Step 4: AI layout planning
        _update(job_id, "📡 AI đang thiết kế layout (tiếng Anh)...")
        from .ai_planner import plan_layout
        layout_plan = plan_layout(skeleton, design_hints=design)
        _update(job_id, "✅ AI đã hoàn thành layout")

        # Step 5: Build PPTX
        stem     = Path(source_filename).stem
        ts       = datetime.now().strftime("%Y%m%d_%H%M")
        out_name = f"{stem}_{ts}.pptx"
        out_path = str(OUTPUT_DIR / out_name)

        tpl_label = Path(template_path).name if template_path else "no template"
        _update(job_id, f"🎨 Đang tạo PPTX (template: {tpl_label})...")

        from .builder import build
        build(layout_plan, name_map, raw_data,
              output_path=out_path,
              template_path=template_path,
              design=design)

        _jobs[job_id] = {
            "status":  "done",
            "message": f"✅ Hoàn thành! → output/{out_name}",
            "file":    out_name
        }

    except Exception as e:
        import traceback
        _jobs[job_id] = {
            "status":  "error",
            "message": str(e) + "\n" + traceback.format_exc(),
            "file":    ""
        }


# ── Startup ───────────────────────────────────────────────────────────────────

def _open_browser():
    import time
    time.sleep(1.2)
    webbrowser.open("http://localhost:5000/v2")


def _run_stage1_if_enabled():
    try:
        if not CONFIG_FILE.exists():
            return
        cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        if not cfg.get("enable_stage1", False):
            return
        from .stage1_list_updater import run_stage1_update
        print("🧠 Stage 1: đang cập nhật whitelist/blacklist (chạy ngầm)...")
        n_w, n_b = run_stage1_update(dry_run=False)
        print(f"🧠 Stage 1: xong ({n_w} whitelist, {n_b} blacklist added)")
    except Exception as e:
        print(f"⚠️ Stage 1 lỗi (bỏ qua): {e}")


if __name__ == "__main__":
    print(">> AI-PPTX đang khởi động...")
    print(f"   Input folder  : {INPUT_DIR}")
    print(f"   Output folder : {OUTPUT_DIR}")
    print(f"   Template      : {DEFAULT_TEMPLATE}")
    print("   Mở trình duyệt: http://localhost:5000")

    # Stage 1 now runs inside _run_pipeline (after file pick), not at startup
    # threading.Thread(target=_run_stage1_if_enabled, daemon=True).start()

    # Only open browser if not in production (Render sets RENDER env var)
    if not os.environ.get("RENDER"):
        threading.Thread(target=_open_browser, daemon=True).start()
    
    port = int(os.environ.get("PORT", 5000))
    host = "0.0.0.0"  # Render needs this
    app.run(host=host, port=port, debug=False)
