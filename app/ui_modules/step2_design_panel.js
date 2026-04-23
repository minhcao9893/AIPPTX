/**
 * step2_design_panel.js — Design left panel: Tab Theme + Tab Advanced
 * =====================================================================
 * Tab "Theme"    → step2_design.js (Theme picker + 5 màu cơ bản)
 * Tab "Advanced" → /api/design GET/POST
 *
 * ADVANCED: Layout gom theo COMPONENT (không theo property type)
 * Mỗi component = 1 accordion section chứa TẤT CẢ properties của nó:
 *   màu, font, size, bật/tắt, padding, v.v.
 */

const Step2DesignPanel = (() => {

  let _activeTab   = 'theme';
  let _advValues   = null;
  let _advOriginal = null;

  /* ════════════════════════════════════════════════════════════════
   * COMPONENT MAP — định nghĩa từng component với fields của nó
   * Mỗi field: { key, label, type }
   * type: 'color' | 'bool' | 'number' | 'text' | 'select'
   * ════════════════════════════════════════════════════════════════ */
  const COMPONENTS = [
    {
      id: 'header_band',
      icon: '▬',
      label: 'Header Banner',
      desc: 'Dải tiêu đề đầu mỗi slide nội dung',
      fields: [
        { key: 'header_band.enabled',             label: 'Hiển/Tắt',        type: 'bool'   },
        { key: 'header_band.color',               label: 'Màu nền',         type: 'color',  ref: 'colors.bg_dark'        },
        { key: 'transparency.header_band_alpha',  label: 'Độ trong suốt (%)', type: 'transparency' },
        { key: 'colors.heading',                  label: 'Màu chữ tiêu đề', type: 'color'  },
        { key: 'header_band.height_inches',       label: 'Chiều cao (in)',   type: 'number' },
        { key: 'fonts.header_band_size',          label: 'Cỡ chữ',          type: 'number' },
        { key: 'header_band.title_x_inches',      label: 'Offset X (in)',    type: 'number' },
        { key: 'header_band.title_y_inches',      label: 'Offset Y (in)',    type: 'number' },
        { key: 'header_band.title_width_inches',  label: 'Chiều rộng (in)', type: 'number' },
        { key: 'header_band.title_height_inches', label: 'Chiều cao text (in)', type: 'number' },
      ]
    },
    {
      id: 'title_slide',
      icon: '🎯',
      label: 'Cover Slide',
      desc: 'Slide bìa đầu tiên',
      fields: [
        { key: 'title_slide.enabled',             label: 'Hiện/Tắt',          type: 'bool'   },
        { key: 'title_slide.bg.enabled',          label: 'Vẽ nền bg',         type: 'bool'   },
        { key: 'colors.bg_dark',                  label: 'Màu nền',           type: 'color'  },
        { key: 'title_slide.title.color',         label: 'Màu tiêu đề',       type: 'color'  },
        { key: 'title_slide.title.font_size',     label: 'Cỡ chữ tiêu đề',   type: 'number' },
        { key: 'title_slide.title.align',         label: 'Căn chỉnh',         type: 'select', options: ['left','center','right'] },
        { key: 'title_slide.title.y_inches',      label: 'Vị trí Y (in)',     type: 'number' },
        { key: 'title_slide.subtitle.enabled',    label: 'Hiện subtitle',     type: 'bool'   },
        { key: 'title_slide.subtitle.font_size',  label: 'Cỡ chữ subtitle',   type: 'number' },
        { key: 'title_slide.accent_bar.enabled',  label: 'Hiện accent bar',   type: 'bool'   },
        { key: 'title_slide.accent_bar.width_inches', label: 'Rộng accent bar (in)', type: 'number' },
      ]
    },
    {
      id: 'fonts',
      icon: 'Aa',
      label: 'Fonts',
      desc: 'Kiểu chữ & cỡ chữ toàn bộ deck',
      fields: [
        { key: 'fonts.main',              label: 'Font chính',        type: 'text'   },
        { key: 'fonts.heading',           label: 'Font heading',      type: 'text'   },
        { key: 'fonts.title_font',        label: 'Font title slide',  type: 'text'   },
        { key: 'fonts.body_font',         label: 'Font body',         type: 'text'   },
        { key: 'fonts.title_size',        label: 'Size title',        type: 'number' },
        { key: 'fonts.title_slide_size',  label: 'Size title slide',  type: 'number' },
        { key: 'fonts.subtitle_size',     label: 'Size subtitle',     type: 'number' },
        { key: 'fonts.bullet_size',       label: 'Size bullet',       type: 'number' },
        { key: 'fonts.insight_label_size',label: 'Size insight label',type: 'number' },
        { key: 'fonts.insight_body_size', label: 'Size insight body', type: 'number' },
        { key: 'fonts.table_header_size', label: 'Size table header', type: 'number' },
        { key: 'fonts.table_body_size',   label: 'Size table body',   type: 'number' },
      ]
    },
    {
      id: 'colors_global',
      icon: '🎨',
      label: 'Màu tổng quát',
      desc: 'Palette màu dùng chung toàn deck',
      fields: [
        { key: 'colors.bg_dark',         label: 'BG Dark',         type: 'color' },
        { key: 'colors.bg_light',        label: 'BG Light',        type: 'color' },
        { key: 'colors.accent',          label: 'Accent',          type: 'color' },
        { key: 'colors.heading',         label: 'Heading',         type: 'color' },
        { key: 'colors.body',            label: 'Body text',       type: 'color' },
        { key: 'colors.bullet_dot',      label: 'Bullet dot',      type: 'color' },
        { key: 'colors.divider_line',    label: 'Divider line',    type: 'color' },
        { key: 'colors.slide_background',label: 'Slide bg',        type: 'color' },
        { key: 'colors.panel_bg',        label: 'Panel bg',        type: 'color' },
        { key: 'colors.body_text',       label: 'Body text alt',   type: 'color' },
        { key: 'colors.highlight',       label: 'Highlight',       type: 'color' },
        { key: 'colors.chart_accent',    label: 'Chart accent',    type: 'color' },
      ]
    },
    {
      id: 'right_panel',
      icon: '💡',
      label: 'AI Insight Panel',
      desc: 'Panel AI Insight bên phải slide',
      fields: [
        { key: 'right_panel.enabled',            label: 'Hiện/Tắt',         type: 'bool'   },
        { key: 'colors.insight_bg',              label: 'Màu nền',          type: 'color'  },
        { key: 'colors.insight_border',          label: 'Màu viền',         type: 'color'  },
        { key: 'right_panel.padding_inches',     label: 'Padding (in)',     type: 'number' },
        { key: 'right_panel.label.enabled',      label: 'Hiện label',       type: 'bool'   },
        { key: 'right_panel.label.text',         label: 'Text label',       type: 'text'   },
        { key: 'right_panel.label.font_size',    label: 'Cỡ label',         type: 'number' },
        { key: 'colors.insight_label',           label: 'Màu label',        type: 'color'  },
        { key: 'colors.insight_body',            label: 'Màu body text',    type: 'color'  },
        { key: 'right_panel.body.font_size',     label: 'Cỡ body',          type: 'number' },
        { key: 'right_panel.label_divider.enabled', label: 'Hiện divider', type: 'bool'   },
        { key: 'split_layout.split_ratio',       label: 'Tỉ lệ left/right', type: 'number' },
      ]
    },
    {
      id: 'divider',
      icon: '┃',
      label: 'Divider',
      desc: 'Đường kẻ dọc giữa left và right panel',
      fields: [
        { key: 'divider.enabled',       label: 'Hiện/Tắt',     type: 'bool'   },
        { key: 'colors.divider_line',   label: 'Màu',          type: 'color'  },
        { key: 'divider.width_inches',  label: 'Độ dày (in)',  type: 'number' },
      ]
    },
    {
      id: 'bullet_slide',
      icon: '●',
      label: 'Bullet Slide',
      desc: 'Slide dạng danh sách gạch đầu dòng',
      fields: [
        { key: 'bullet_slide.bullet_dot_char',           label: 'Ký tự bullet',      type: 'text'   },
        { key: 'bullet_slide.bullet_size',               label: 'Cỡ chữ bullet',     type: 'number' },
        { key: 'colors.bullet_dot',                      label: 'Màu bullet dot',    type: 'color'  },
        { key: 'colors.body',                            label: 'Màu body text',     type: 'color'  },
        { key: 'bullet_slide.line_spacing_pt',           label: 'Line spacing (pt×100)', type: 'number' },
        { key: 'bullet_slide.footer_insight.enabled',    label: 'Hiện footer insight', type: 'bool' },
        { key: 'bullet_slide.footer_insight.font_size',  label: 'Cỡ footer insight', type: 'number' },
        { key: 'bullet_slide.footer_insight.color',      label: 'Màu footer insight', type: 'color' },
      ]
    },
    {
      id: 'table',
      icon: '⊞',
      label: 'Table',
      desc: 'Bảng dữ liệu trong slide',
      fields: [
        { key: 'colors.table_header',         label: 'Màu nền header',   type: 'color'  },
        { key: 'table.header.color',          label: 'Màu chữ header',   type: 'color'  },
        { key: 'table.header.font_size',      label: 'Cỡ chữ header',    type: 'number' },
        { key: 'colors.table_row_alt',        label: 'Màu row alt',      type: 'color'  },
        { key: 'table.body.font_size',        label: 'Cỡ chữ body',      type: 'number' },
        { key: 'colors.table_text',           label: 'Màu chữ bảng',     type: 'color'  },
      ]
    },
    {
      id: 'chart',
      icon: '📊',
      label: 'Chart',
      desc: 'Biểu đồ trong slide',
      fields: [
        { key: 'chart.has_legend',       label: 'Hiện legend',      type: 'bool'   },
        { key: 'chart.show_data_labels', label: 'Hiện data labels', type: 'bool'   },
        { key: 'colors.chart_palette',   label: 'Palette màu',      type: 'colors' },
        { key: 'colors.chart_accent',    label: 'Màu accent',       type: 'color'  },
      ]
    },
    {
      id: 'image_placeholder',
      icon: '🖼',
      label: 'Image Placeholder',
      desc: 'Ô placeholder cho ảnh',
      fields: [
        { key: 'image_placeholder.count',          label: 'Số ô',         type: 'number' },
        { key: 'colors.img_placeholder_fill',      label: 'Màu nền',      type: 'color'  },
        { key: 'colors.img_placeholder_border',    label: 'Màu viền',     type: 'color'  },
        { key: 'image_placeholder.label_font_size',label: 'Cỡ chữ label', type: 'number' },
        { key: 'image_placeholder.label_color',    label: 'Màu chữ label',type: 'color'  },
      ]
    },
    {
      id: 'slide_transparency',
      icon: '🔲',
      label: 'Nền & Độ trong suốt',
      desc: 'Mức transparency nền slide (0 = đặc, 100 = trong suốt)',
      fields: [
        { key: 'slide.bg_transparency',   label: 'Transparency nền (%)', type: 'transparency' },
        { key: 'colors.slide_background', label: 'Màu nền slide',        type: 'color'  },
        { key: 'colors.panel_bg',         label: 'Màu panel bg',          type: 'color'  },
      ]
    },
    {
      id: 'slide_size',
      icon: '📐',
      label: 'Kích thước Slide',
      desc: 'Kích thước & margin slide',
      fields: [
        { key: 'slide.width_inches',              label: 'Rộng (in)',         type: 'number' },
        { key: 'slide.height_inches',             label: 'Cao (in)',          type: 'number' },
        { key: 'slide.margin_left_inches',        label: 'Margin trái (in)', type: 'number' },
        { key: 'slide.margin_right_inches',       label: 'Margin phải (in)', type: 'number' },
        { key: 'content_slide.content_top_inches',label: 'Content top (in)', type: 'number' },
        { key: 'content_slide.content_bottom_margin_inches', label: 'Content bottom margin (in)', type: 'number' },
      ]
    },
    {
      id: 'brand',
      icon: '🏢',
      label: 'Thương hiệu',
      desc: 'Tên công ty & logo',
      fields: [
        { key: 'brand.company_name', label: 'Tên công ty', type: 'text' },
        { key: 'brand.logo_path',    label: 'Đường dẫn logo', type: 'text' },
      ]
    },
  ];

  /* ══ Accordion state ══════════════════════════════════════════════ */
  const _openSections = new Set(['header_band']); // mở mặc định

  /* ── Init ────────────────────────────────────────────────────────── */
  function init() {
    try { Step2Design.init(); } catch(e) { console.error('Step2Design.init:', e); }
    switchTab('theme');
  }

  /* ── Tab switching ───────────────────────────────────────────────── */
  function switchTab(tab) {
    _activeTab = tab;
    const themeEl  = document.getElementById('s2-design-body');
    const advEl    = document.getElementById('s2-advanced-design');
    const btnTheme = document.getElementById('s2-design-tab-theme');
    const btnAdv   = document.getElementById('s2-design-tab-advanced');

    if (tab === 'theme') {
      if (themeEl) themeEl.style.display = 'flex';
      if (advEl)   advEl.style.display   = 'none';
      if (btnTheme) { btnTheme.style.color = 'var(--accent)'; btnTheme.style.borderBottomColor = 'var(--accent)'; }
      if (btnAdv)   { btnAdv.style.color   = ''; btnAdv.style.borderBottomColor = 'transparent'; }
    } else {
      if (themeEl) themeEl.style.display = 'none';
      if (advEl)   advEl.style.display   = 'flex';
      if (btnTheme) { btnTheme.style.color = ''; btnTheme.style.borderBottomColor = 'transparent'; }
      if (btnAdv)   { btnAdv.style.color   = 'var(--accent)'; btnAdv.style.borderBottomColor = 'var(--accent)'; }
      if (!_advValues) loadAdvanced();
    }
  }

  /* ── Advanced: Load từ API ───────────────────────────────────────── */
  async function loadAdvanced() {
    const body = document.getElementById('s2-adv-body');
    if (body) body.innerHTML = '<div style="color:var(--txt-muted);font-size:12px;padding:16px 0;text-align:center;">⏳ Đang tải...</div>';

    try {
      const res  = await fetch('/api/design');
      const data = await res.json();

      // Flatten nested object → flat map { 'header_band.enabled': true, ... }
      _advValues   = _flattenObj(data.values);
      _advOriginal = Object.assign({}, _advValues);

      renderAdvanced();
    } catch (e) {
      if (body) body.innerHTML = '<div style="color:#ef4444;font-size:12px;padding:16px;">❌ Lỗi tải design: ' + e.message + '</div>';
    }
  }

  /* ── Flatten/Unflatten helpers ───────────────────────────────────── */
  function _flattenObj(obj, prefix) {
    prefix = prefix || '';
    const result = {};
    for (const k in obj) {
      const fullKey = prefix ? prefix + '.' + k : k;
      const val = obj[k];
      if (val !== null && typeof val === 'object' && !Array.isArray(val)) {
        Object.assign(result, _flattenObj(val, fullKey));
      } else {
        result[fullKey] = val;
      }
    }
    return result;
  }

  function _unflattenObj(flat) {
    const result = {};
    for (const key in flat) {
      const parts = key.split('.');
      let cur = result;
      for (let i = 0; i < parts.length - 1; i++) {
        if (!cur[parts[i]] || typeof cur[parts[i]] !== 'object') cur[parts[i]] = {};
        cur = cur[parts[i]];
      }
      cur[parts[parts.length - 1]] = flat[key];
    }
    return result;
  }

  /* ── Render component-grouped accordion ─────────────────────────── */
  function renderAdvanced() {
    const body = document.getElementById('s2-adv-body');
    if (!body || !_advValues) return;

    body.innerHTML = '';

    COMPONENTS.forEach(function(comp) {
      const section = document.createElement('div');
      section.className = 'adv-section';
      section.style.cssText = 'border-bottom:1px solid var(--border);';

      const isOpen = _openSections.has(comp.id);

      // ── Header (click to toggle) ──
      const header = document.createElement('div');
      header.style.cssText = [
        'display:flex;align-items:center;gap:8px;',
        'padding:10px 16px;cursor:pointer;',
        'transition:background 0.15s;',
        'user-select:none;',
        isOpen ? 'background:rgba(56,189,248,0.06);' : '',
      ].join('');
      header.onmouseenter = function() { if (!_openSections.has(comp.id)) header.style.background = 'rgba(255,255,255,0.03)'; };
      header.onmouseleave = function() { if (!_openSections.has(comp.id)) header.style.background = 'none'; };

      const iconEl = document.createElement('span');
      iconEl.style.cssText = 'font-size:14px;width:20px;text-align:center;flex-shrink:0;';
      iconEl.textContent = comp.icon;

      const labelWrap = document.createElement('div');
      labelWrap.style.cssText = 'flex:1;min-width:0;';
      labelWrap.innerHTML = `
        <div style="font-size:11px;font-weight:700;color:var(--txt);letter-spacing:0.5px;">${comp.label}</div>
        <div style="font-size:9px;color:var(--txt-dim);margin-top:1px;">${comp.desc}</div>
      `;

      // Quick preview: show inline color swatches for color fields
      const previewEl = document.createElement('div');
      previewEl.style.cssText = 'display:flex;gap:3px;flex-shrink:0;margin-right:6px;';
      comp.fields.filter(f => f.type === 'color').slice(0, 3).forEach(function(f) {
        const val = _advValues[f.key];
        if (val && typeof val === 'string' && val.startsWith('#')) {
          const dot = document.createElement('div');
          dot.style.cssText = `width:8px;height:8px;border-radius:50%;background:${val};flex-shrink:0;`;
          previewEl.appendChild(dot);
        }
      });

      const chevron = document.createElement('span');
      chevron.id = 'chev-' + comp.id;
      chevron.style.cssText = 'font-size:10px;color:var(--txt-muted);transition:transform 0.2s;flex-shrink:0;';
      chevron.textContent = '▶';
      if (isOpen) chevron.style.transform = 'rotate(90deg)';

      header.appendChild(iconEl);
      header.appendChild(labelWrap);
      header.appendChild(previewEl);
      header.appendChild(chevron);

      header.onclick = function() { toggleSection(comp.id, section, chevron, header); };

      // ── Body (fields) ──
      const fieldsEl = document.createElement('div');
      fieldsEl.id = 'adv-fields-' + comp.id;
      fieldsEl.style.cssText = [
        'overflow:hidden;',
        'transition:max-height 0.25s ease;',
        isOpen ? 'max-height:2000px;' : 'max-height:0;',
      ].join('');

      const fieldsInner = document.createElement('div');
      fieldsInner.style.cssText = 'padding:4px 16px 12px 44px;display:flex;flex-direction:column;gap:0;';

      comp.fields.forEach(function(field) {
        const row = _makeFieldRow(field);
        if (row) fieldsInner.appendChild(row);
      });

      fieldsEl.appendChild(fieldsInner);
      section.appendChild(header);
      section.appendChild(fieldsEl);
      body.appendChild(section);
    });
  }

  function toggleSection(id, sectionEl, chevron, header) {
    const fieldsEl = document.getElementById('adv-fields-' + id);
    if (!fieldsEl) return;

    if (_openSections.has(id)) {
      _openSections.delete(id);
      fieldsEl.style.maxHeight = '0';
      chevron.style.transform = 'rotate(0deg)';
      header.style.background = 'none';
    } else {
      _openSections.add(id);
      fieldsEl.style.maxHeight = '2000px';
      chevron.style.transform = 'rotate(90deg)';
      header.style.background = 'rgba(56,189,248,0.06)';
    }
  }

  /* ── Build một field row ─────────────────────────────────────────── */
  function _makeFieldRow(field) {
    const key = field.key;
    const val = (_advValues && key in _advValues) ? _advValues[key] : null;

    const row = document.createElement('div');
    row.style.cssText = [
      'display:flex;align-items:center;justify-content:space-between;',
      'padding:5px 0;border-bottom:1px solid rgba(255,255,255,0.04);',
      'gap:10px;',
    ].join('');

    const lbl = document.createElement('span');
    lbl.style.cssText = 'font-size:11px;color:var(--txt-muted);flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;';
    lbl.textContent = field.label;
    lbl.title = key; // tooltip = full key path
    row.appendChild(lbl);

    const inputWrap = document.createElement('div');
    inputWrap.style.flexShrink = '0';

    if (field.type === 'color') {
      inputWrap.appendChild(_makeColorInput(key, val));

    } else if (field.type === 'colors') {
      // Array of colors (chart palette)
      const arr = Array.isArray(val) ? val : ['#38bdf8','#818cf8','#34d399','#e2e8f0','#888888'];
      const wrap = document.createElement('div');
      wrap.style.cssText = 'display:flex;gap:4px;flex-wrap:wrap;';
      arr.forEach(function(c, i) {
        const sw = document.createElement('div');
        sw.style.cssText = `width:20px;height:20px;border-radius:4px;border:1px solid var(--border);cursor:pointer;background:${c};flex-shrink:0;`;
        const cp = document.createElement('input');
        cp.type = 'color';
        cp.value = c;
        cp.style.cssText = 'opacity:0;position:absolute;pointer-events:none;width:1px;height:1px;';
        sw.onclick = function() { cp.click(); };
        cp.oninput = function() {
          sw.style.background = cp.value;
          if (!Array.isArray(_advValues[key])) _advValues[key] = arr.slice();
          _advValues[key][i] = cp.value;
        };
        wrap.appendChild(sw);
        wrap.appendChild(cp);
      });
      inputWrap.appendChild(wrap);

    } else if (field.type === 'bool') {
      const toggle = _makeBoolToggle(key, val);
      inputWrap.appendChild(toggle);

    } else if (field.type === 'number') {
      const inp = document.createElement('input');
      inp.type = 'number';
      inp.step = 'any';
      inp.value = (val !== null && val !== undefined) ? val : '';
      inp.style.cssText = 'width:72px;background:var(--bg-card);border:1px solid var(--border);border-radius:4px;color:var(--txt);font-size:11px;padding:3px 6px;font-family:monospace;text-align:right;';
      inp.oninput = function() { _advValues[key] = parseFloat(inp.value); _notifyPreview(); };
      inputWrap.appendChild(inp);

    } else if (field.type === 'transparency') {
      // 0-100% slider + number input
      const curVal = (val !== null && val !== undefined) ? Math.round(val) : 0;
      const wrap2 = document.createElement('div');
      wrap2.style.cssText = 'display:flex;align-items:center;gap:6px;';
      const slider = document.createElement('input');
      slider.type = 'range'; slider.min = '0'; slider.max = '100'; slider.step = '1';
      slider.value = curVal;
      slider.style.cssText = 'width:80px;accent-color:var(--accent);cursor:pointer;';
      const numInp = document.createElement('input');
      numInp.type = 'number'; numInp.min = '0'; numInp.max = '100'; numInp.step = '1';
      numInp.value = curVal;
      numInp.style.cssText = 'width:44px;background:var(--bg-card);border:1px solid var(--border);border-radius:4px;color:var(--txt);font-size:11px;padding:3px 5px;font-family:monospace;text-align:right;';
      const pctLbl = document.createElement('span');
      pctLbl.style.cssText = 'font-size:10px;color:var(--txt-dim);';
      pctLbl.textContent = '%';
      function syncTransparency(v) {
        const clamped = Math.max(0, Math.min(100, Math.round(v)));
        slider.value = clamped; numInp.value = clamped;
        if (_advValues) _advValues[key] = clamped;
        _notifyPreview();
      }
      slider.oninput = function() { syncTransparency(parseInt(slider.value)); };
      numInp.oninput = function() { syncTransparency(parseInt(numInp.value) || 0); };
      wrap2.appendChild(slider);
      wrap2.appendChild(numInp);
      wrap2.appendChild(pctLbl);
      inputWrap.appendChild(wrap2);

    } else if (field.type === 'select') {
      const sel = document.createElement('select');
      sel.style.cssText = 'background:var(--bg-card);border:1px solid var(--border);border-radius:4px;color:var(--txt);font-size:11px;padding:3px 6px;';
      (field.options || []).forEach(function(opt) {
        const o = document.createElement('option');
        o.value = opt; o.textContent = opt;
        if (val === opt) o.selected = true;
        sel.appendChild(o);
      });
      sel.onchange = function() { _advValues[key] = sel.value; _notifyPreview(); };
      inputWrap.appendChild(sel);

    } else {
      // text
      const inp = document.createElement('input');
      inp.type = 'text';
      inp.value = (val !== null && val !== undefined) ? val : '';
      inp.style.cssText = 'width:110px;background:var(--bg-card);border:1px solid var(--border);border-radius:4px;color:var(--txt);font-size:11px;padding:3px 6px;';
      inp.oninput = function() { _advValues[key] = inp.value; _notifyPreview(); };
      inputWrap.appendChild(inp);
    }

    row.appendChild(inputWrap);
    return row;
  }

  /* ── Color input (swatch + hidden picker + hex label) ────────────── */
  function _makeColorInput(key, hex) {
    hex = (hex && typeof hex === 'string' && hex.startsWith('#')) ? hex : '#000000';
    const wrap = document.createElement('div');
    wrap.style.cssText = 'display:flex;align-items:center;gap:5px;';

    const swatch = document.createElement('div');
    swatch.style.cssText = `width:20px;height:20px;border-radius:4px;border:1px solid var(--border);cursor:pointer;flex-shrink:0;background:${hex};transition:transform 0.1s;`;
    swatch.onmouseenter = function() { swatch.style.transform = 'scale(1.15)'; };
    swatch.onmouseleave = function() { swatch.style.transform = 'scale(1)'; };

    const cp = document.createElement('input');
    cp.type = 'color';
    cp.value = hex;
    cp.style.cssText = 'opacity:0;position:absolute;pointer-events:none;width:1px;height:1px;';

    const hexSpan = document.createElement('span');
    hexSpan.style.cssText = 'font-size:9px;color:var(--txt-dim);font-family:monospace;width:50px;';
    hexSpan.textContent = hex;

    swatch.onclick = function() { cp.click(); };
    cp.oninput = function() {
      swatch.style.background = cp.value;
      hexSpan.textContent = cp.value;
      if (_advValues) _advValues[key] = cp.value;
      // cập nhật preview dots
      _refreshPreviewDots();
      _notifyPreview();
    };

    wrap.appendChild(swatch);
    wrap.appendChild(cp);
    wrap.appendChild(hexSpan);
    return wrap;
  }

  /* ── Bool toggle (ON/OFF pill) ───────────────────────────────────── */
  function _makeBoolToggle(key, val) {
    const isOn = val === true || val === 'true';
    const wrap = document.createElement('div');
    wrap.style.cssText = 'display:flex;border:1px solid var(--border);border-radius:20px;overflow:hidden;';

    const btnOn  = document.createElement('button');
    const btnOff = document.createElement('button');
    const baseStyle = 'padding:3px 10px;font-size:10px;font-weight:600;border:none;cursor:pointer;transition:all 0.15s;';

    btnOn.textContent  = 'ON';
    btnOff.textContent = 'OFF';

    function refresh(v) {
      btnOn.style.cssText  = baseStyle + (v ? 'background:#1e3a5f;color:#38bdf8;' : 'background:transparent;color:var(--txt-dim);');
      btnOff.style.cssText = baseStyle + (!v ? 'background:#3a1e1e;color:#f87171;' : 'background:transparent;color:var(--txt-dim);');
    }
    refresh(isOn);

    btnOn.onclick  = function() { if (_advValues) _advValues[key] = true;  refresh(true);  _notifyPreview(); };
    btnOff.onclick = function() { if (_advValues) _advValues[key] = false; refresh(false); _notifyPreview(); };

    wrap.appendChild(btnOn);
    wrap.appendChild(btnOff);
    return wrap;
  }

  /* ── Refresh color preview dots in accordion headers ─────────────── */
  function _refreshPreviewDots() {
    // Re-render chỉ preview dots (không full re-render để tránh mất state input)
    COMPONENTS.forEach(function(comp) {
      // Không cần làm gì vì dots chỉ render lúc ban đầu
      // TODO: nếu muốn live update dots thì track DOM refs
    });
  }

  /* ── Save / Reset ────────────────────────────────────────────────── */
  async function saveAdvanced() {
    const nested = _unflattenObj(_advValues);
    try {
      var res = await fetch('/api/design', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(nested)
      });
      var data = await res.json();
      var msg = document.getElementById('s2-adv-msg');
      if (msg) {
        msg.style.display = 'inline';
        msg.textContent = data.ok ? ('✅ Đã lưu ' + (data.saved || '?') + ' thay đổi') : '❌ Lỗi lưu';
        setTimeout(function() { msg.style.display = 'none'; }, 3000);
      }
    } catch(e) { console.error('saveAdvanced:', e); }
  }

  function resetAdvanced() {
    if (!_advOriginal) return;
    _advValues = Object.assign({}, _advOriginal);
    renderAdvanced();
    var msg = document.getElementById('s2-adv-msg');
    if (msg) {
      msg.style.display = 'inline';
      msg.textContent = '↩ Đã reset';
      setTimeout(function() { msg.style.display = 'none'; }, 2500);
    }
  }

  /* ── Notify Preview khi có thay đổi ─────────────────────────────── */
  function _notifyPreview() {
    if (typeof Preview !== 'undefined') {
      try {
        var colors = (typeof Step2Design !== 'undefined') ? Step2Design.getDesign().colors : null;
        Preview.onDesignChange(_advValues, colors);
      } catch(e) {}
    }
  }

  /* ── Public ──────────────────────────────────────────────────────── */
  return {
    init, switchTab, saveAdvanced, resetAdvanced,
    /** Trả về flat values hiện tại cho Preview module */
    getAdvValues: function() { return _advValues ? Object.assign({}, _advValues) : null; }
  };

})();
