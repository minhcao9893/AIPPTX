/**
 * step2_design.js — Step II: Theme + 5 màu cơ bản
 * ==================================================
 * Render phần Design ở LEFT panel (30%).
 * Cho phép:
 *   - Chọn theme (Corporate / Minimal / Bold / Dark / Pastel)
 *   - Tuỳ chỉnh 5 màu cơ bản: primary, secondary, accent, bg, text
 *
 * Phụ thuộc:
 *   - app_shell.html → #s2-design-body
 *   - step2_canvas.js → Canvas.redraw() khi theme đổi
 */

const Step2Design = (() => {

  /* ── Theme definitions ──────────────────────────────────── */
  const THEMES = [
    {
      id: 'template_default',
      name: 'Giữ theme template',
      preview: 'linear-gradient(135deg, #1e293b 50%, #334155 100%)',
      colors: null  // null = không override, giữ nguyên template
    },
    {
      id: 'corporate',
      name: 'Corporate',
      preview: 'linear-gradient(135deg, #003366 50%, #0055aa 100%)',
      colors: { primary:'#003366', secondary:'#0055aa', accent:'#f4a020', bg:'#ffffff', text:'#1a1a2e' }
    },
    {
      id: 'minimal',
      name: 'Minimal',
      preview: 'linear-gradient(135deg, #f5f5f5 50%, #e0e0e0 100%)',
      colors: { primary:'#1a1a1a', secondary:'#555555', accent:'#ff6b35', bg:'#fafafa', text:'#1a1a1a' }
    },
    {
      id: 'bold',
      name: 'Bold',
      preview: 'linear-gradient(135deg, #1a0533 50%, #6c1bb5 100%)',
      colors: { primary:'#6c1bb5', secondary:'#e040fb', accent:'#00e5ff', bg:'#0d0021', text:'#ffffff' }
    },
    {
      id: 'dark',
      name: 'Dark',
      preview: 'linear-gradient(135deg, #0b1120 50%, #1e293b 100%)',
      colors: { primary:'#38bdf8', secondary:'#818cf8', accent:'#34d399', bg:'#0b1120', text:'#e2e8f0' }
    },
    {
      id: 'pastel',
      name: 'Pastel',
      preview: 'linear-gradient(135deg, #fce4ec 50%, #e3f2fd 100%)',
      colors: { primary:'#e91e8c', secondary:'#3f51b5', accent:'#4caf50', bg:'#fff9fb', text:'#37474f' }
    },
    // ── 5 theme nóng / ấm mới ──
    {
      id: 'sunrise',
      name: 'Sunrise',
      preview: 'linear-gradient(135deg, #ff6b35 0%, #f7c59f 100%)',
      colors: { primary:'#d4380d', secondary:'#fa8c16', accent:'#fadb14', bg:'#fffbe6', text:'#3b1f00' }
    },
    {
      id: 'autumn',
      name: 'Autumn',
      preview: 'linear-gradient(135deg, #8b2500 0%, #d46b08 50%, #faad14 100%)',
      colors: { primary:'#8b2500', secondary:'#d46b08', accent:'#ffc53d', bg:'#fdf3e0', text:'#3e1a00' }
    },
    {
      id: 'terracotta',
      name: 'Terracotta',
      preview: 'linear-gradient(135deg, #c0392b 0%, #e67e22 50%, #f39c12 100%)',
      colors: { primary:'#c0392b', secondary:'#e67e22', accent:'#f1c40f', bg:'#fef9f0', text:'#2c1810' }
    },
    {
      id: 'tropical',
      name: 'Tropical',
      preview: 'linear-gradient(135deg, #ff4757 0%, #ff6b81 50%, #ffa502 100%)',
      colors: { primary:'#c7003b', secondary:'#ff4757', accent:'#ffa502', bg:'#fff5f7', text:'#2c0015' }
    },
    {
      id: 'desert',
      name: 'Desert',
      preview: 'linear-gradient(135deg, #b7791f 0%, #d69e2e 50%, #ecc94b 100%)',
      colors: { primary:'#7b5000', secondary:'#b7791f', accent:'#d69e2e', bg:'#fffdf7', text:'#2d1a00' }
    },
  ];

  const COLOR_LABELS = {
    primary:   'Màu chính',
    secondary: 'Màu phụ',
    accent:    'Accent',
    bg:        'Nền',
    text:      'Chữ'
  };

  /* ── State ──────────────────────────────────────────────── */
  let _selectedTheme = 'template_default';
  let _colors = null;  // null khi dùng theme template
  let _selectedTemplate = null;  // filename template được chọn
  let _selectedImageCompId = null;

  /* ── Render ─────────────────────────────────────────────── */
  function render() {
    const body = document.getElementById('s2-design-body');
    body.innerHTML = `
      <div class="section-label">Template PPTX</div>
      <div style="margin-bottom:12px;">
        <select id="s2-template-select" style="width:100%;background:var(--bg-card);border:1px solid var(--border);border-radius:6px;color:var(--txt);font-size:11px;padding:6px 8px;" onchange="Step2Design.onTemplateChange(this.value)">
          <option value="__none__">⚡ Không dùng template</option>
        </select>
        <div style="font-size:9px;color:var(--txt-dim);margin-top:4px;">File .pptx trong folder template/ sẽ được áp slide master</div>
      </div>

      <div class="section-label">Theme</div>
      <div class="theme-grid" id="s2-theme-grid" style="grid-template-columns:1fr 1fr; max-height:260px; overflow-y:auto;">
        ${THEMES.map(t => `
          <div class="theme-card ${t.id === _selectedTheme ? 'selected' : ''}"
               style="background:${t.id === 'minimal' ? '#2a2a3a' : 'var(--bg-card)'};"
               onclick="Step2Design.selectTheme('${t.id}')">
            <div class="theme-preview" style="background:${t.preview};"></div>
            <div class="theme-name">${t.name}</div>
          </div>
        `).join('')}
      </div>

      <div class="section-label" style="margin-top:20px;">5 Màu cơ bản</div>
      <div id="s2-color-rows">
        ${_selectedTheme === 'template_default' ? '<div style="font-size:10px;color:var(--txt-dim);padding:8px 0;text-align:center;">&#128204; Dùng màu gốc của template — không override</div>' : Object.keys(COLOR_LABELS).map(key => `
          <div class="color-row">
            <span class="color-label">${COLOR_LABELS[key]}</span>
            <div class="color-swatch"
                 style="background:${_colors[key]};"
                 onclick="Step2Design.openColorPicker('${key}', this)"
                 title="${_colors[key]}">
            </div>
            <input type="color" id="cp-${key}" value="${_colors[key]}"
                   oninput="Step2Design.onColorInput('${key}', this.value)">
            <span style="font-size:10px; color:var(--txt-dim); font-family:'JetBrains Mono',monospace;">${_colors[key]}</span>
          </div>
        `).join('')}
      </div>

      ${_selectedTheme !== 'template_default' ? `
      <div style="margin-top:20px;">
        <button class="btn btn-ghost" style="width:100%; font-size:11px;" onclick="Step2Design.resetColors()">
          ↺ Reset về theme gốc
        </button>
      </div>` : ''}
    `;

    // Load template list async sau khi render
    _loadTemplateList();
  }

  /* ── Handlers ────────────────────────────────────────────── */
  function selectTheme(id) {
    _selectedTheme = id;
    if (id === 'template_default') {
      _colors = null;
    } else {
      const t = THEMES.find(t => t.id === id);
      _colors = { ...t.colors };
    }
    render();
    _notifyChange();
  }

  async function _loadTemplateList() {
    try {
      const res  = await fetch('/api/templates');
      const data = await res.json();
      const sel  = document.getElementById('s2-template-select');
      if (!sel) return;
      // giữ option __none__, thêm các file
      sel.innerHTML = '<option value="__none__">⚡ Không dùng template</option>';
      (data.templates || []).forEach(function(f) {
        const opt = document.createElement('option');
        opt.value = f;
        opt.textContent = '📊 ' + f;
        if (f === _selectedTemplate) opt.selected = true;
        sel.appendChild(opt);
      });
      // Nếu chưa chọn template nào, auto chọn file đầu tiên nếu có
      if (!_selectedTemplate && data.templates && data.templates.length > 0) {
        _selectedTemplate = data.templates[0];
        sel.value = _selectedTemplate;
      } else if (_selectedTemplate) {
        sel.value = _selectedTemplate;
      }
    } catch(e) { console.warn('load templates:', e); }
  }

  function onTemplateChange(val) {
    _selectedTemplate = (val === '__none__') ? null : val;
  }

  function openColorPicker(key, swatchEl) {
    const input = document.getElementById(`cp-${key}`);
    input.style.left  = swatchEl.getBoundingClientRect().left + 'px';
    input.style.top   = swatchEl.getBoundingClientRect().bottom + 'px';
    input.style.pointerEvents = 'auto';
    input.click();
    input.style.pointerEvents = 'none';
  }

  function onColorInput(key, value) {
    _colors[key] = value;
    // Update swatch UI tanpa full re-render
    const swatch = document.querySelector(`[onclick*="openColorPicker('${key}'"]`);
    if (swatch) swatch.style.background = value;
    const spans = document.querySelectorAll('.color-row');
    spans.forEach(row => {
      const s = row.querySelector('.color-swatch');
      const k = row.querySelector('[onclick]')?.getAttribute('onclick')?.match(/'(\w+)'/)?.[1];
      if (k === key) {
        row.querySelectorAll('span')[1].textContent = value;
      }
    });
    _notifyChange();
  }

  function resetColors() {
    const t = THEMES.find(t => t.id === _selectedTheme);
    _colors = { ...t.colors };
    render();
    _notifyChange();
  }

  function _notifyChange() {
    // Notify canvas to redraw với màu mới
    if (typeof Canvas !== 'undefined') Canvas.setColors(_colors);
    // Notify Preview pane (realtime)
    if (typeof Preview !== 'undefined') {
      try {
        var adv = (typeof Step2DesignPanel !== 'undefined') ? Step2DesignPanel.getAdvValues() : null;
        Preview.onDesignChange(adv, _colors);
      } catch(e) {}
    }
  }

  function onSelectImageBlock(compId) {
     _selectedImageCompId = compId;
     const aiGenPanel = document.getElementById('s2-ai-gen');
     if (aiGenPanel) {
         aiGenPanel.classList.remove('disabled');
         aiGenPanel.style.opacity = '1';
         aiGenPanel.style.pointerEvents = 'auto';
         const promptInput = document.getElementById('s2-ai-prompt');
         if (promptInput) {
            promptInput.focus();
            promptInput.onkeydown = (e) => {
               if (e.key === 'Enter') generateAIImage();
            };
         }
     }
  }

  function generateAIImage() {
     if (!_selectedImageCompId) return;
     const promptInput = document.getElementById('s2-ai-prompt');
     const prompt = promptInput.value.trim();
     if (!prompt) return;

     const btn = document.getElementById('s2-ai-btn');
     btn.disabled = true;
     btn.textContent = 'Đang tạo...';

     const imageUrl = `https://image.pollinations.ai/prompt/${encodeURIComponent(prompt)}?width=1024&height=768&nologo=true&seed=${Math.floor(Math.random()*10000)}`;
     
     const slideIdx = Step2Slides.getSelectedIdx();
     const configs = Step2Slides.getAllConfigs();
     if (!configs[slideIdx].imageUrls) configs[slideIdx].imageUrls = [];
     
     const k = parseInt(_selectedImageCompId.replace('img', ''));
     configs[slideIdx].imageUrls[k] = imageUrl;

     const img = new Image();
     img.onload = () => {
         btn.disabled = false;
         btn.textContent = 'Tạo ảnh';
         Layout.onSlideSelected(slideIdx, Step2Slides.getSlides()[slideIdx], configs[slideIdx]);
     };
     img.onerror = () => {
         btn.disabled = false;
         btn.textContent = 'Tạo ảnh';
         Layout.onSlideSelected(slideIdx, Step2Slides.getSlides()[slideIdx], configs[slideIdx]);
     };
     img.src = imageUrl;
  }

  /* ── Public ─────────────────────────────────────────────── */
  function init() { render(); }
  function getDesign() { return { theme: _selectedTheme, colors: _colors, template: _selectedTemplate }; }

  return { init, render, selectTheme, openColorPicker, onColorInput, resetColors, getDesign, onSelectImageBlock, generateAIImage, onTemplateChange };
})();
