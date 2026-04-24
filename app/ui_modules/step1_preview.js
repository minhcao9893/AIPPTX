/**
 * step1_preview.js — Step I: Word Preview + Editable textarea
 * =============================================================
 * Hiển thị nội dung file Word đã parse ra bên RIGHT panel.
 * Render slide cards: title + content (bullets/text) + bảng + ảnh.
 *
 * Phụ thuộc:
 *   - app_shell.html → #s1-preview-area, #s1-editor, #s1-empty-state, ...
 */

const Step1Preview = (() => {

  let _mode  = 'trigger';  // 'trigger' | 'ai'
  let _dirty = false;
  let _rawText = '';        // giữ raw text để getText() vẫn hoạt động

  // ── Helpers render ────────────────────────────────────────────

  function _esc(s) {
    return String(s)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  /** Render một bảng {columns, rows} thành HTML table */
  function _renderTable(tbl) {
    if (!tbl || !tbl.columns || !tbl.columns.length) return '';
    const cols = tbl.columns;
    const rows = tbl.rows || [];
    let h = `<div class="s1-tbl-wrap"><table class="s1-tbl">`;
    h += `<thead><tr>${cols.map(c=>`<th>${_esc(c)}</th>`).join('')}</tr></thead>`;
    if (rows.length) {
      h += `<tbody>`;
      rows.forEach(row => {
        const cells = Array.isArray(row) ? row : cols.map(c => row[c] ?? '');
        h += `<tr>${cells.map(v=>`<td>${_esc(v)}</td>`).join('')}</tr>`;
      });
      h += `</tbody>`;
    }
    h += `</table></div>`;
    return h;
  }

  /** Render content của 1 slide: bullets/text/table */
  function _renderContent(slide) {
    let html = '';

    // --- Images ---
    (slide.images || []).forEach(img => {
      html += `<img src="/api/media/${img}" data-tag="[IMAGE: ${img}]"
        style="max-height:140px;border-radius:4px;margin:6px 0;display:block;border:1px solid var(--accent)">`;
    });

    const content = slide.content;

    // --- Table ---
    if (content && typeof content === 'object' && content.columns) {
      html += _renderTable(content);
      // extra_tables nếu có
      (slide.extra_tables || []).forEach(t => { html += _renderTable(t); });
      return html;
    }

    // --- Bullets array ---
    if (Array.isArray(content) && content.length) {
      html += `<ul class="s1-bullets">`;
      content.forEach(b => { html += `<li>${_esc(b)}</li>`; });
      html += `</ul>`;
      return html;
    }

    // --- Plain text ---
    const txt = typeof content === 'string' ? content : (slide.raw_text || '');
    if (txt.trim()) {
      // loại bỏ dòng đầu (đã là title)
      const lines = txt.split('\n').slice(1).filter(l=>l.trim());
      if (lines.length) {
        html += `<p class="s1-body">${lines.map(_esc).join('<br>')}</p>`;
      }
    }
    return html;
  }

  /** Render full list slide cards từ mảng slides */
  function _renderSlideCards(slides) {
    if (!slides || !slides.length) return '<p style="color:var(--text-muted);padding:1rem">Không có slide nào.</p>';
    return slides.map(slide => {
      const typeLabel = { table:'TABLE', bullet:'BULLETS', text:'TEXT', chart:'CHART' }[slide.type] || slide.type || '';
      const badge = slide.chart_hint
        ? `<span class="s1-type-badge chart">CHART</span>`
        : typeLabel ? `<span class="s1-type-badge ${slide.type}">${typeLabel}</span>` : '';
      const body = _renderContent(slide);
      return `
        <div class="s1-slide-card" data-idx="${slide.index}">
          <div class="s1-slide-header">
            <span class="s1-slide-num">${slide.index}</span>
            <span class="s1-slide-title">${_esc(slide.title)}</span>
            ${badge}
          </div>
          ${body ? `<div class="s1-slide-body">${body}</div>` : ''}
        </div>`;
    }).join('');
  }

  // ── Public API ─────────────────────────────────────────────────

  /**
   * Load nội dung text vào preview editor
   * @param {string} text       - Nội dung file (raw text hoặc structured trigger text)
   * @param {string} mode       - 'trigger' | 'ai'
   * @param {object} meta       - { slideCount, fileName }
   */
  async function load(text, mode, meta = {}) {
    _mode = mode;
    _dirty = false;
    _rawText = text;

    document.getElementById('s1-empty-state').style.display = 'none';
    document.getElementById('s1-preview-area').style.display = 'flex';

    const editor = document.getElementById('s1-editor');

    // Badge
    const badge = document.getElementById('s1-preview-mode-badge');
    badge.textContent = mode === 'ai' ? 'AI STRUCTURED' : 'TRIGGER MODE';
    badge.style.background = mode === 'ai'
      ? 'rgba(167,139,250,0.15)' : 'rgba(79,156,249,0.12)';
    badge.style.color = mode === 'ai' ? 'var(--accent3)' : 'var(--accent)';

    // Info
    const slideStr = meta.slideCount ? `${meta.slideCount} slides` : '';
    const fileStr  = meta.fileName || '';
    document.getElementById('s1-preview-info').textContent =
      [fileStr, slideStr].filter(Boolean).join(' · ');

    // Nếu có {Slide N} → gọi API parse-slides-full để lấy structured data
    const hasTriggers = /\{Slide\s+\d+\}/i.test(text);
    if (hasTriggers) {
      editor.innerHTML = '<p style="color:var(--text-muted);padding:1rem;font-size:0.85rem">⏳ Đang parse slides…</p>';
      try {
        const res   = await fetch('/api/parse-slides-full', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text }),
        });
        const data  = await res.json();
        if (data.ok && data.slides && data.slides.length) {
          editor.innerHTML = _renderSlideCards(data.slides);
          editor.oninput = () => { _dirty = true; };
          return;
        }
      } catch(e) {
        console.warn('parse-slides-full failed, fallback to raw', e);
      }
    }

    // Fallback: render raw text + images (cũ)
    let html = text.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
    html = html.replace(/\[IMAGE:\s*([^\]]+)\]/gi, (match, p1) =>
      `<img src="/api/media/${p1}" data-tag="${match}" style="max-height:150px;border-radius:4px;margin:8px 0;display:block;border:1px solid #4f9cf9;">`);
    editor.innerHTML = html;
    editor.oninput = () => { _dirty = true; };
  }

  function clear() {
    document.getElementById('s1-empty-state').style.display = 'flex';
    document.getElementById('s1-preview-area').style.display = 'none';
    document.getElementById('s1-editor').innerHTML = '';
    _dirty = false;
  }

  function getText() {
    // Nếu đang hiển thị dưới dạng slide cards → trả raw text gốc
    if (_rawText) return _rawText;
    // Fallback: dùng DOM như cũ
    const editor = document.getElementById('s1-editor');
    const clone = editor.cloneNode(true);
    clone.querySelectorAll('img[data-tag]').forEach(img => {
      const txt = document.createTextNode(img.getAttribute('data-tag'));
      img.parentNode.replaceChild(txt, img);
    });
    const offscreen = document.createElement('div');
    offscreen.style.cssText = 'position:absolute;left:-9999px;top:-9999px;white-space:pre-wrap;';
    offscreen.appendChild(clone);
    document.body.appendChild(offscreen);
    let text = clone.innerText;
    document.body.removeChild(offscreen);
    return text;
  }

  /** Gọi API lưu file đã chỉnh sửa (optional — lưu temp session) */
  async function saveEdited() {
    const text = getText();
    try {
      const res  = await fetch('/api/save-edited-text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, mode: _mode })
      });
      const data = await res.json();
      if (data.ok) toast('✓ Đã lưu chỉnh sửa', 'success');
      else         toast('Lưu thất bại', 'error');
    } catch {
      toast('Không kết nối được server', 'error');
    }
    _dirty = false;
  }

  function copyContent() {
    const text = getText();
    navigator.clipboard.writeText(text)
      .then(() => toast('✓ Đã copy nội dung', 'success'))
      .catch(() => toast('Copy thất bại', 'error'));
  }

  return { load, clear, getText, saveEdited, copyContent };
})();
