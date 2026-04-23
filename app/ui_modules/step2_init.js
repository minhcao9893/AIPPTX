/**
 * step2_init.js — Step II: Orchestrator / Global init
 */

const Step2 = (() => {

  async function init(text) {
    console.log('[Step2] init() bắt đầu, text.length=', text ? text.length : 0);

    // 1. Design panel
    try {
      if (typeof Step2DesignPanel !== 'undefined') {
        Step2DesignPanel.init();
        console.log('[Step2] DesignPanel OK');
      } else {
        console.error('[Step2] Step2DesignPanel chưa load — kiểm tra step2_design_panel.js');
      }
    } catch(e) {
      console.error('[Step2] DesignPanel.init() lỗi:', e);
    }

    // 2. Parse slides
    try {
      const res  = await fetch('/api/parse-slides', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ text })
      });
      const data = await res.json();
      console.log('[Step2] parse-slides kết quả:', data);

      if (!data.ok || !data.slides || data.slides.length === 0) {
        toast('Không parse được slide nào. Kiểm tra cấu trúc file.', 'error');
        const list = document.getElementById('s2-slides-list');
        if (list) list.innerHTML = '<div style="padding:16px;color:var(--txt-dim);font-size:12px;">Chưa có slide nào được phân tích.</div>';
        return;
      }

      try {
        Step2Slides.init(data.slides);
        console.log('[Step2] Slides.init() OK, số slides:', data.slides.length);
      } catch(e) {
        console.error('[Step2] Slides.init() lỗi:', e);
        toast('Lỗi khởi tạo slide: ' + e.message, 'error');
      }

    } catch(e) {
      console.error('[Step2] fetch parse-slides lỗi:', e);
      toast('Lỗi kết nối server: ' + e.message, 'error');
    }
  }

  function goBack() {
    document.getElementById('page-step2').classList.remove('active');
    document.getElementById('page-step1').classList.add('active');
  }

  function generatePPTX() {
    Step2Export.generatePPTX();
  }

  return { init, goBack, generatePPTX };
})();

/* ── Global toast helper ─────────────────────────────────────── */
function toast(msg, type = '') {
  const el   = document.getElementById('toast');
  const icon = document.getElementById('toast-icon');
  const txt  = document.getElementById('toast-msg');
  el.className = type ? `show ${type}` : 'show';
  icon.textContent = type === 'success' ? '✓' : type === 'error' ? '✕' : '●';
  txt.textContent  = msg;
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => el.classList.remove('show'), 3200);
}
