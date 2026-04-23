/**
 * step2_export.js — Step II: Tạo PPTX + download + progress
 * ============================================================
 * Quản lý:
 *   - Nút [Tạo pptx] → gọi API /api/generate
 *   - Progress overlay (prog-overlay, prog-bar, prog-msg)
 *   - Sau khi xong: toast + link tải + thông báo file ở Desktop/output
 *
 * Luồng:
 *   1. Thu thập layout config từ tất cả slides (Layout.getLayoutConfig())
 *   2. Thu thập design config (Step2Design.getDesign())
 *   3. POST /api/generate → server: mask → AI → unmask → build pptx
 *   4. Poll /api/progress để update bar
 *   5. Khi xong: show download link + toast
 *
 * Phụ thuộc:
 *   - app_shell.html → #progress-overlay, #prog-bar, #prog-msg, #prog-detail
 *   - step2_layout.js  → Layout.getLayoutConfig()
 *   - step2_design.js  → Step2Design.getDesign()
 *   - step2_slides.js  → Step2Slides.getAllConfigs(), getSlides()
 */

const Step2Export = (() => {

  let _polling = false;

  /* ── Entry point ─────────────────────────────────────────── */
  async function generatePPTX() {
    const slides  = Step2Slides.getSlides();
    const configs = Step2Slides.getAllConfigs();
    const design  = Step2Design.getDesign();

    // Lưu layout config của slide đang chọn trước khi submit
    const currentLayout = Layout.getLayoutConfig();
    const currentIdx    = Step2Slides.getSelectedIdx();
    Step2Slides.setLayoutConfig(currentIdx, currentLayout);

    // Xây dựng layouts per-slide (fallback về vertical nếu chưa set)
    const defaultLayout = { layout_type: 'vertical', pct: [], margin: 0.25 };
    const layouts = configs.map((c, i) => {
      const cfg = c.layoutConfig;
      if (cfg) {
        return {
          layout_type: cfg.layout_type || cfg.layout || 'vertical',
          pct:         cfg.pct || [],
          tableDist:   cfg.tableDist || null,
          margin:      cfg.margin || 0.25,
          components:  cfg.components || [],
          imageUrls:   c.imageUrls || []
        };
      } else {
        // Nếu vẫn null (do init chưa kịp chạy Layout.buildDefaultConfig), tự build nhanh ở đây
        const s = slides[i];
        const nTbl = s.table_count || 0;
        const hasContent = s.has_content || false;
        const imageCount = s.image_count || 0;
        const nComp = nTbl + (hasContent ? 1 : 0) + imageCount;
        return {
          layout_type: 'vertical',
          pct: Array(nComp).fill(0), // backend will split equally if total is 0 or all are 0
          margin: 0.25,
          components: [], // backend will fallback to slide content
          imageUrls: c.imageUrls || []
        };
      }
    });

    if (!slides || slides.length === 0) {
      toast('Không có slide nào để tạo PPTX', 'error');
      return;
    }

    // Build payload
    const payload = {
      slides:  slides,
      configs: configs,
      design:  design,
      template_name: design.template || null,  // filename trong folder template/
      layout:  currentLayout,   // global fallback (bảo tương thích)
      layouts: layouts,          // per-slide layout config
      adv_values: (typeof Step2DesignPanel !== 'undefined' && Step2DesignPanel.getAdvValues)
                  ? (Step2DesignPanel.getAdvValues() || {})
                  : {},           // Advanced design values (transparency, v.v.)
      input_text: (window.APP_STATE || {}).inputText || '',
      input_mode: (window.APP_STATE || {}).inputMode || 1
    };

    showProgress(0, 'Chuẩn bị...');

    try {
      const res  = await fetch('/api/generate', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(payload)
      });

      if (!res.ok) {
        const err = await res.text();
        throw new Error(err);
      }

      // Start polling
      _polling = true;
      pollProgress();

    } catch (e) {
      hideProgress();
      toast('Lỗi: ' + e.message, 'error');
    }
  }

  /* ── Progress polling ────────────────────────────────────── */
  async function pollProgress() {
    while (_polling) {
      await _sleep(800);
      try {
        const res  = await fetch('/api/progress');
        const data = await res.json();

        showProgress(data.pct || 0, data.message || '');
        document.getElementById('prog-detail').textContent = data.detail || '';

        if (data.status === 'done') {
          _polling = false;
          hideProgress();
          onSuccess(data.filename, data.output_path);
          break;
        }
        if (data.status === 'error') {
          _polling = false;
          hideProgress();
          toast('Lỗi tạo PPTX: ' + (data.message || ''), 'error');
          break;
        }
      } catch {
        // silent retry
      }
    }
  }

  /* ── Success handler ─────────────────────────────────────── */
  function onSuccess(filename, outputPath) {
    // Toast thông báo
    toast(`✓ Đã tạo xong: ${filename}`, 'success');

    // Show download + info banner
    _showDownloadBanner(filename, outputPath);
  }

  function _showDownloadBanner(filename, outputPath) {
    // Tạo banner tạm thời ở bottom của page-step2
    const existing = document.getElementById('export-banner');
    if (existing) existing.remove();

    const banner = document.createElement('div');
    banner.id = 'export-banner';
    banner.style.cssText = `
      position: fixed; bottom: 0; left: 0; right: 0;
      background: linear-gradient(90deg, #0d1f12, #0f2a1a);
      border-top: 1px solid rgba(52,211,153,0.3);
      padding: 14px 28px; display: flex; align-items: center;
      gap: 16px; z-index: 8500; animation: slideUp 0.3s ease;
    `;
    banner.innerHTML = `
      <span style="font-size:20px;">🎉</span>
      <div style="flex:1;">
        <div style="font-size:13px; font-weight:700; color:#34d399;">${filename} đã sẵn sàng</div>
        <div style="font-size:11px; color:#64748b; margin-top:2px;">${outputPath || 'Desktop/output/'}</div>
      </div>
      <a href="/api/download/${encodeURIComponent(filename)}"
         style="padding:9px 20px; background:#34d399; color:#000; border-radius:8px;
                font-size:12px; font-weight:700; text-decoration:none; font-family:'Syne',sans-serif;">
        ⬇ Tải xuống
      </a>
      <button onclick="document.getElementById('export-banner').remove()"
              style="background:none; border:none; color:#64748b; font-size:18px; cursor:pointer;">✕</button>
    `;
    document.body.appendChild(banner);
  }

  /* ── Progress UI ─────────────────────────────────────────── */
  function showProgress(pct, msg) {
    document.getElementById('progress-overlay').classList.add('show');
    document.getElementById('prog-bar').style.width = `${pct}%`;
    document.getElementById('prog-msg').textContent = msg;
  }

  function hideProgress() {
    document.getElementById('progress-overlay').classList.remove('show');
  }

  /* ── Utils ───────────────────────────────────────────────── */
  function _sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

  return { generatePPTX };
})();
