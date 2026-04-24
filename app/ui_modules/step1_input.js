/**
 * step1_input.js — Step I: File picker + Mode toggle
 * ===================================================
 * Quản lý:
 *   - Toggle chế độ: Mode 1 (Trigger) / Mode 2 (AI)
 *   - File picker cho cả 2 mode (chọn file từ bất kỳ thư mục)
 *   - Điều phối sang preview (Step1Preview) và AI processor (Step1AI)
 *   - Nút "Tiếp theo →" → chuyển sang Step II
 *
 * Phụ thuộc:
 *   - step1_trigger.js   → Step1Trigger.show() / .close()
 *   - step1_preview.js   → Step1Preview.load(text, mode)
 *   - step1_ai_processor.js → Step1AI.run(file, opts)
 *   - app_shell.html     → DOM ids: s1-mode-*, s1-panel-*, s1-file-input, ...
 */

const Step1 = (() => {

  /* ── State ──────────────────────────────────────────────── */
  let _mode       = 1;      // 1 = trigger, 2 = AI
  let _file1      = null;   // File object mode 1
  let _file2      = null;   // File object mode 2
  let _parsedText = '';     // Nội dung preview hiện tại
  let _slideCount = 0;      // Số slide phát hiện được

  /* ── Mode toggle ──────────────────────────────────────────── */
  function setMode(m) {
    _mode = m;
    document.getElementById('s1-mode-trigger').classList.toggle('active', m === 1);
    document.getElementById('s1-mode-ai').classList.toggle('active', m === 2);
    document.getElementById('s1-panel-mode1').style.display = m === 1 ? 'block' : 'none';
    document.getElementById('s1-panel-mode2').style.display = m === 2 ? 'block' : 'none';
    Step1Preview.clear();
  }

  /* ── Mode 1: File picker ─────────────────────────────────── */
  function pickFile() {
    document.getElementById('s1-file-input').click();
  }

  function onFileSelected(input) {
    const file = input.files[0];
    if (!file) return;
    _file1 = file;

    // Cập nhật UI
    document.getElementById('s1-fp-label').textContent = file.name;
    const info = document.getElementById('s1-file-info');
    info.style.display = 'block';
    document.getElementById('s1-file-name').textContent = file.name;
    document.getElementById('s1-file-path').textContent = file.size
      ? `${(file.size / 1024).toFixed(1)} KB`
      : '—';

    // Auto preview
    previewFile();
  }

  /**
   * Gọi API /api/parse-docx để lấy text từ file Word
   * Sau đó đẩy sang Step1Preview.load()
   */
  async function previewFile() {
    if (!_file1) { toast('Vui lòng chọn file trước', 'error'); return; }
    const fd = new FormData();
    fd.append('file', _file1);

    try {
      const res  = await fetch('/api/parse-docx-text', { method: 'POST', body: fd });
      const data = await res.json();
      if (!data.ok) throw new Error(data.error || 'Parse lỗi');

      _parsedText = data.text;
      _slideCount = data.slide_count || 0;
      Step1Preview.load(data.text, 'trigger', {
        slideCount: _slideCount,
        fileName: _file1.name
      });
    } catch (e) {
      toast('Không đọc được file: ' + e.message, 'error');
    }
  }

  /* ── Mode 2: File picker ─────────────────────────────────── */
  function pickFile2() {
    document.getElementById('s1-file-input-2').click();
  }

  function onFile2Selected(input) {
    const file = input.files[0];
    if (!file) return;
    _file2 = file;
    document.getElementById('s1-fp2-label').textContent = `✓ ${file.name}`;
  }

  /**
   * Chạy AI analysis cho mode 2 — luồng 2-lượt:
   *   Lượt 1: Stage 1 extract blacklist/whitelist (AI 1)
   *   Lượt 2: Mask text gốc → AI soạn cấu trúc slide (AI 2)
   */
  async function runAIAnalysis() {
    if (!_file2) { toast('Vui lòng chọn file trước', 'error'); return; }

    const maxSlides = parseInt(document.getElementById('s1-ai-max-slides').value) || 10;
    const lang      = document.getElementById('s1-ai-lang').value;

    const statusEl = document.getElementById('s1-ai-status');
    const msgEl    = document.getElementById('s1-ai-msg');
    statusEl.classList.add('show');
    document.getElementById('s1-btn-analyze').disabled = true;

    const fd = new FormData();
    fd.append('file', _file2);
    fd.append('max_slides', maxSlides);
    fd.append('lang', lang);

    // Progress messages theo đúng 2 lượt thực tế
    const progressSteps = [
      'Đang đọc và phân tích văn bản...',
      'Lượt 1 — AI nhận diện từ nhạy cảm...',
      'Lượt 1 — Cập nhật blacklist / whitelist...',
      'Lượt 2 — Mask dữ liệu nhạy cảm...',
      'Lượt 2 — AI soạn cấu trúc slide...',
      'Hoàn tất — Unmask và xây trigger...',
    ];
    let si = 0;
    const ticker = setInterval(() => {
      msgEl.textContent = progressSteps[Math.min(si++, progressSteps.length - 1)];
    }, 2500);

    try {
      const res  = await fetch('/api/ai-split-docx', { method: 'POST', body: fd });
      const data = await res.json();
      clearInterval(ticker);
      if (!data.ok) throw new Error(data.error || 'AI error');

      _parsedText = data.trigger_text || data.text || '';
      _slideCount = data.slide_count || 0;

      // Thông báo Stage 1 kết quả nếu có
      const s1w = data.stage1_added_w || 0;
      const s1b = data.stage1_added_b || 0;
      const s1msg = (s1w || s1b)
        ? ` (+${s1b} blacklist, +${s1w} whitelist)`
        : '';

      Step1Preview.load(_parsedText, 'ai', {
        slideCount: _slideCount,
        fileName: _file2.name
      });
      toast(`✓ AI đã phân tích xong: ${_slideCount} slide${s1msg}`, 'success');
    } catch (e) {
      clearInterval(ticker);
      toast('AI lỗi: ' + e.message, 'error');
    } finally {
      statusEl.classList.remove('show');
      document.getElementById('s1-btn-analyze').disabled = false;
    }
  }

  /* ── Trigger Guide popup ──────────────────────────────────── */
  function showTriggerGuide() { Step1Trigger.show(); }
  function closeTriggerGuide(){ Step1Trigger.close(); }

  function saveEdited() { Step1Preview.saveEdited(); }
  function copyContent(){ Step1Preview.copyContent(); }

  /* ── Điều hướng ──────────────────────────────────────────── */
  function goNext() {
    const text = Step1Preview.getText();
    if (!text || text.trim().length < 10) {
      toast('Cần có nội dung trước khi tiếp tục', 'error');
      return;
    }
    // Lưu text vào state chung
    window.APP_STATE = window.APP_STATE || {};
    window.APP_STATE.inputText = text;
    window.APP_STATE.inputMode = _mode;

    // Chuyển sang step 2
    document.getElementById('page-step1').classList.remove('active');
    document.getElementById('page-step2').classList.add('active');
    Step2.init(text);
  }

  /* ── Public API ──────────────────────────────────────────── */
  return {
    setMode, pickFile, onFileSelected, previewFile,
    pickFile2, onFile2Selected, runAIAnalysis,
    showTriggerGuide, closeTriggerGuide, goNext,
    saveEdited, copyContent
  };
})();
