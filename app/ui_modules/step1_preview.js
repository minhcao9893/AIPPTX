/**
 * step1_preview.js — Step I: Word Preview + Editable textarea
 * =============================================================
 * Hiển thị nội dung file Word đã parse ra bên RIGHT panel.
 * Cho phép edit trực tiếp trong textarea.
 *
 * Phụ thuộc:
 *   - app_shell.html → #s1-preview-area, #s1-editor, #s1-empty-state, ...
 */

const Step1Preview = (() => {

  let _mode = 'trigger';   // 'trigger' | 'ai'
  let _dirty = false;       // đã edit chưa

  /**
   * Load nội dung text vào preview editor
   * @param {string} text       - Nội dung file (raw text hoặc structured trigger text)
   * @param {string} mode       - 'trigger' | 'ai'
   * @param {object} meta       - { slideCount, fileName }
   */
  function load(text, mode, meta = {}) {
    _mode = mode;
    _dirty = false;

    document.getElementById('s1-empty-state').style.display = 'none';
    document.getElementById('s1-preview-area').style.display = 'flex';

    const editor = document.getElementById('s1-editor');
    
    // Encode text to HTML entities
    let html = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    // Render images
    html = html.replace(/\[IMAGE:\s*([^\]]+)\]/gi, (match, p1) => {
        return `<img src="/api/media/${p1}" data-tag="${match}" style="max-height:150px; border-radius:4px; margin:8px 0; display:block; border:1px solid #4f9cf9;">`;
    });
    editor.innerHTML = html;

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

    // Listen for edits
    editor.oninput = () => { _dirty = true; };
  }

  function clear() {
    document.getElementById('s1-empty-state').style.display = 'flex';
    document.getElementById('s1-preview-area').style.display = 'none';
    document.getElementById('s1-editor').innerHTML = '';
    _dirty = false;
  }

  function getText() {
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
    
    // In contenteditable div, modern browsers preserve newlines in innerText
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
