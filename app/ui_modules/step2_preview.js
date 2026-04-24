/**
 * step2_preview.js — Preview pane realtime: Theme + Advanced → canvas
 * ====================================================================
 * Quan ly #s2-preview-pane:
 *   - open()  : hien pane, an layout canvas
 *   - close() : dong pane, hien lai layout canvas
 *   - toggle(): mo/dong
 *   - onDesignChange(advValues, themeColors): render lai canvas ngay lap tuc
 *
 * Nut trigger: bat ky element co class "s2-preview-toggle-btn"
 * (Advanced footer + Theme tab deu dung chung class nay)
 *
 * v2: Render noi dung slide thuc te (title, bullets, table) tu window._slideFullData
 */

const Preview = (() => {

  /* -- State -------------------------------------------------------- */
  let _isOpen      = false;
  let _advValues   = null;   // flat object tu Step2DesignPanel.getAdvValues()
  let _themeColors = null;   // { primary, secondary, accent, bg, text }
  let _rafId       = null;   // requestAnimationFrame handle

  /* -- DOM refs (lazy) --------------------------------------------- */
  function _pane()       { return document.getElementById('s2-preview-pane');    }
  function _canvasWrap() { return document.getElementById('s2-canvas-wrap');     }
  function _canvas()     { return document.getElementById('s2-preview-canvas');  }
  function _statusEl()   { return document.getElementById('s2-preview-status'); }

  /* -- Open / Close / Toggle --------------------------------------- */
  function open() {
    _isOpen = true;

    const pane = _pane();
    const wrap = _canvasWrap();
    if (pane) pane.style.display = 'flex';
    if (wrap) wrap.style.display = 'none';

    document.querySelectorAll('.s2-preview-toggle-btn').forEach(function(btn) {
      btn.classList.add('active');
      if (!btn.textContent.includes('\u25cf')) {
        btn.textContent = btn.textContent.replace('Preview', 'Preview \u25cf');
      }
    });

    _syncState();
    _render();
  }

  function close() {
    _isOpen = false;

    const pane = _pane();
    const wrap = _canvasWrap();
    if (pane) pane.style.display = 'none';
    if (wrap) wrap.style.display = '';

    document.querySelectorAll('.s2-preview-toggle-btn').forEach(function(btn) {
      btn.classList.remove('active');
      btn.textContent = btn.textContent.replace(' \u25cf', '').replace('\u25cf', '');
    });
  }

  function toggle() {
    if (_isOpen) close(); else open();
  }

  /* -- Lay state moi nhat tu cac module khac ----------------------- */
  function _syncState() {
    try {
      if (typeof Step2Design !== 'undefined') {
        var design = Step2Design.getDesign();
        _themeColors = design.colors || null;
      }
    } catch(e) {}
    try {
      if (typeof Step2DesignPanel !== 'undefined') {
        _advValues = Step2DesignPanel.getAdvValues() || null;
      }
    } catch(e) {}
  }

  /* -- Callback: goi tu step2_design.js & step2_design_panel.js --- */
  function onDesignChange(advValues, themeColors) {
    if (advValues   !== undefined) _advValues   = advValues;
    if (themeColors !== undefined) _themeColors = themeColors;

    if (!_isOpen) return;

    if (_rafId) cancelAnimationFrame(_rafId);
    _rafId = requestAnimationFrame(function() { _render(); _rafId = null; });
  }

  /* -- Lay slide dang active (full data) --------------------------- */
  function _getActiveSlide() {
    try {
      var idx = (typeof Step2Slides !== 'undefined') ? Step2Slides.getSelectedIdx() : null;
      if (idx === null || idx === undefined) return null;
      var slides = (typeof Step2Slides !== 'undefined') ? Step2Slides.getSlides() : [];
      var meta = slides[idx] || null;
      // slides list co the 0-based, slide.index la 1-based
      var slideIndex = meta ? (meta.index || idx + 1) : (idx + 1);
      var full = window._slideFullData && window._slideFullData[slideIndex];
      return { meta: meta, full: full, idx: idx, slideIndex: slideIndex };
    } catch(e) { return null; }
  }

  /* -- Render slide len canvas ------------------------------------- */
  function _render() {
    var cvs = _canvas();
    if (!cvs) return;

    var ctx = cvs.getContext('2d');
    var W   = cvs.width  || 960;
    var H   = cvs.height || 540;

    // Mau tu themeColors + advValues
    var bg        = _getColor('colors.bg_dark',       (_themeColors && _themeColors.primary)  || '#1E2761');
    var bgLight   = _getColor('colors.bg_light',      (_themeColors && _themeColors.bg)       || '#F5F7FF');
    var accent    = _getColor('colors.accent',         (_themeColors && _themeColors.accent)   || '#f4a020');
    var heading   = _getColor('colors.heading',        (_themeColors && _themeColors.text)     || '#ffffff');
    var bodyTxt   = _getColor('colors.body',           (_themeColors && _themeColors.text)     || '#e2e8f0');
    var insightBg = _getColor('colors.insight_bg',     _alpha(accent, 0.12));
    var dividerC  = _getColor('colors.divider_line',   accent);

    var bandH       = _getNum('header_band.height_inches', 0.9) / 7.5 * H;
    var bandEnabled = _getBool('header_band.enabled', true);
    var divEnabled  = _getBool('divider.enabled', true);
    var insightEn   = _getBool('right_panel.enabled', true);
    var splitRatio  = _getNum('split_layout.split_ratio', 0.62);
    var bandAlpha   = _getNum('transparency.header_band_alpha', 0);
    var autoText    = _getBool('header_band.auto_text_color', true);

    // -- Nen slide --
    ctx.fillStyle = bgLight;
    ctx.fillRect(0, 0, W, H);

    // -- Lay slide data --
    var activeSlide = _getActiveSlide();
    var slideTitle  = 'Tieu de Slide Mau';
    var slideType   = 'text';
    var slideContent = null;
    var slideFull   = null;

    if (activeSlide) {
      slideFull = activeSlide.full;
      if (slideFull) {
        slideTitle   = slideFull.title   || slideTitle;
        slideType    = slideFull.type    || 'text';
        slideContent = slideFull.content || null;
      } else if (activeSlide.meta) {
        slideTitle = activeSlide.meta.title || slideTitle;
      }
    }

    // -- Header band --
    if (bandEnabled) {
      ctx.fillStyle = _alpha(bg, (100 - bandAlpha) / 100);
      ctx.fillRect(0, 0, W, bandH);

      var titleColor = heading;
      if (autoText) {
        titleColor = bandAlpha > 50 ? _getColor('colors.heading', '#1E2761') : '#ffffff';
      }

      ctx.fillStyle = titleColor;
      ctx.font = 'bold 18px Syne, sans-serif';
      ctx.textBaseline = 'middle';
      _fillTextEllipsis(ctx, slideTitle, 28, bandH / 2, W - 56);
    }

    // -- Content area --
    var contentTop = bandEnabled ? bandH + 10 : 10;
    var margin     = 24;
    var contentH   = H - contentTop - margin;

    var leftW, rightX, rightW;
    if (insightEn) {
      leftW  = (W - margin * 2) * splitRatio;
      rightX = margin + leftW + 12;
      rightW = W - rightX - margin;
    } else {
      leftW  = W - margin * 2;
      rightX = W;
      rightW = 0;
    }

    // -- Render content theo type --
    if (slideType === 'table' || slideType === 'chart') {
      _renderTable(ctx, slideContent, margin, contentTop, leftW, contentH, bg, accent, heading, bodyTxt);
    } else if (slideType === 'bullet' || (Array.isArray(slideContent) && slideContent.length)) {
      _renderBullets(ctx, slideContent, margin, contentTop, leftW, contentH, accent, bodyTxt);
    } else {
      _renderTextBody(ctx, slideContent, margin, contentTop, leftW, contentH, bodyTxt);
    }

    // -- Divider --
    if (divEnabled && insightEn) {
      ctx.strokeStyle = dividerC;
      ctx.lineWidth   = 1.5;
      ctx.setLineDash([]);
      ctx.beginPath();
      ctx.moveTo(rightX - 8, contentTop + 8);
      ctx.lineTo(rightX - 8, contentTop + contentH - 8);
      ctx.stroke();
    }

    // -- Insight panel --
    if (insightEn && rightW > 20) {
      ctx.fillStyle = insightBg;
      _roundRect(ctx, rightX, contentTop, rightW, contentH, 6);
      ctx.fill();

      ctx.strokeStyle = _alpha(accent, 0.3);
      ctx.lineWidth   = 1;
      _roundRect(ctx, rightX, contentTop, rightW, contentH, 6);
      ctx.stroke();

      var labelText = _advValues && _advValues['right_panel.label.text'] ? _advValues['right_panel.label.text'] : 'AI Insight';
      ctx.fillStyle = accent;
      ctx.font = 'bold 11px Syne, sans-serif';
      ctx.textBaseline = 'top';
      ctx.fillText(labelText, rightX + 10, contentTop + 12);

      ctx.fillStyle = _alpha(bodyTxt, 0.5);
      ctx.font = '9px Syne, sans-serif';
      var iy = contentTop + 36;
      ['\u2022 Nhan xet 1...', '\u2022 Nhan xet 2...', '\u2022 Nhan xet 3...'].forEach(function(line) {
        ctx.fillText(line, rightX + 10, iy);
        iy += 20;
      });
    }

    // -- Status badge --
    var statusEl = _statusEl();
    if (statusEl) {
      var themeName = 'Custom';
      try {
        if (typeof Step2Design !== 'undefined') {
          var d = Step2Design.getDesign();
          themeName = d.theme || 'Custom';
        }
      } catch(e) {}
      var slideLabel = activeSlide ? ('Slide ' + activeSlide.slideIndex) : 'No slide';
      statusEl.textContent = 'Theme: ' + themeName
        + '  |  ' + slideLabel
        + '  |  ' + (slideType.toUpperCase())
        + '  |  Header: ' + (bandEnabled ? 'ON' : 'OFF')
        + '  |  Insight: ' + (insightEn ? 'ON' : 'OFF');
    }
  }

  /* -- Content renderers ------------------------------------------ */

  /** Render HTML table (columns + rows) len canvas */
  function _renderTable(ctx, tbl, x, y, w, h, bg, accent, heading, bodyTxt) {
    if (!tbl || !tbl.columns || !tbl.columns.length) {
      _renderPlaceholderTable(ctx, x, y, w, h, bg, heading, bodyTxt);
      return;
    }
    var cols    = tbl.columns;
    var rows    = tbl.rows || [];
    var nCols   = cols.length;
    var maxRows = Math.min(rows.length, 12);  // toi da 12 hang tren canvas
    var rowH    = Math.min(26, (h - 4) / (maxRows + 1));
    var colW    = w / nCols;

    // Header row
    for (var c = 0; c < nCols; c++) {
      var cx = x + c * colW;
      ctx.fillStyle = _alpha(bg, 0.85);
      ctx.fillRect(cx, y, colW - 1, rowH - 1);
      ctx.fillStyle = heading;
      ctx.font = 'bold 10px JetBrains Mono, monospace';
      ctx.textBaseline = 'middle';
      _fillTextEllipsis(ctx, String(cols[c]), cx + 6, y + rowH / 2, colW - 12);
    }

    // Data rows
    for (var r = 0; r < maxRows; r++) {
      var ry = y + (r + 1) * rowH;
      var row = rows[r];
      var cells = Array.isArray(row) ? row : cols.map(function(c) { return row[c] !== undefined ? row[c] : ''; });
      for (var c2 = 0; c2 < nCols; c2++) {
        var cx2 = x + c2 * colW;
        ctx.fillStyle = r % 2 === 0 ? _alpha(accent, 0.04) : 'transparent';
        ctx.fillRect(cx2, ry, colW - 1, rowH - 1);
        ctx.fillStyle = _alpha(bodyTxt, 0.85);
        ctx.font = '10px JetBrains Mono, monospace';
        ctx.textBaseline = 'middle';
        _fillTextEllipsis(ctx, String(cells[c2] !== undefined ? cells[c2] : ''), cx2 + 6, ry + rowH / 2, colW - 12);
      }
    }

    // Gach ngang duoi header
    ctx.strokeStyle = _alpha(accent, 0.5);
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x, y + rowH);
    ctx.lineTo(x + w, y + rowH);
    ctx.stroke();

    // Row count info
    if (rows.length > maxRows) {
      var infoY = y + (maxRows + 1) * rowH + 8;
      ctx.fillStyle = _alpha(bodyTxt, 0.4);
      ctx.font = '9px Syne, sans-serif';
      ctx.textBaseline = 'top';
      ctx.fillText('... va ' + (rows.length - maxRows) + ' hang khac', x + 6, infoY);
    }
  }

  /** Placeholder khi khong co data table */
  function _renderPlaceholderTable(ctx, x, y, w, h, bg, heading, bodyTxt) {
    var rows = 4, cols = 3;
    var rowH = Math.min(28, h / rows);
    var colW = w / cols;
    for (var r = 0; r < rows; r++) {
      for (var c = 0; c < cols; c++) {
        var cx = x + c * colW, cy = y + r * rowH;
        ctx.fillStyle = r === 0 ? _alpha(bg, 0.7) : (r % 2 === 0 ? _alpha('#0055aa', 0.06) : 'transparent');
        ctx.fillRect(cx, cy, colW - 2, rowH - 2);
        ctx.fillStyle = r === 0 ? heading : _alpha(bodyTxt, 0.4);
        ctx.font = (r === 0 ? 'bold ' : '') + '10px JetBrains Mono, monospace';
        ctx.textBaseline = 'middle';
        ctx.fillText(r === 0 ? ['Hang muc', 'Gia tri', '%'][c] : '\u2014', cx + 6, cy + rowH / 2);
      }
    }
  }

  /** Render bullet list len canvas */
  function _renderBullets(ctx, bullets, x, y, w, h, accent, bodyTxt) {
    var items = Array.isArray(bullets) ? bullets : (typeof bullets === 'string' ? bullets.split('\n').filter(function(l){return l.trim();}) : []);
    if (!items.length) {
      // Placeholder
      var lineY = y + 16;
      for (var i = 0; i < 5; i++) {
        ctx.fillStyle = _alpha(bodyTxt, 0.15);
        ctx.fillRect(x + 16, lineY, w * (0.9 - i * 0.05), 8);
        lineY += 22;
      }
      return;
    }
    var lineH   = Math.min(22, (h - 8) / Math.min(items.length, 14));
    var maxShow = Math.min(items.length, Math.floor((h - 8) / lineH));
    var curY    = y + 10;

    for (var j = 0; j < maxShow; j++) {
      var txt = String(items[j]).replace(/^[\-\u2022\*\u00b7\u25cf\+]\s*/, '');
      // Bullet dot
      ctx.fillStyle = accent;
      ctx.beginPath();
      ctx.arc(x + 12, curY + lineH / 2, 3, 0, Math.PI * 2);
      ctx.fill();
      // Text
      ctx.fillStyle = _alpha(bodyTxt, 0.9);
      ctx.font = '11px Syne, sans-serif';
      ctx.textBaseline = 'middle';
      _fillTextEllipsis(ctx, txt, x + 22, curY + lineH / 2, w - 26);
      curY += lineH;
    }
    if (items.length > maxShow) {
      ctx.fillStyle = _alpha(bodyTxt, 0.35);
      ctx.font = '9px Syne, sans-serif';
      ctx.textBaseline = 'top';
      ctx.fillText('... va ' + (items.length - maxShow) + ' muc khac', x + 22, curY + 4);
    }
  }

  /** Render body text (plain text) len canvas */
  function _renderTextBody(ctx, content, x, y, w, h, bodyTxt) {
    var txt = typeof content === 'string' ? content : '';
    if (!txt.trim()) {
      // Placeholder lines
      var lineY = y + 16;
      for (var i = 0; i < 5; i++) {
        ctx.fillStyle = _alpha(bodyTxt, 0.15);
        ctx.fillRect(x + 16, lineY, w * (0.9 - i * 0.05), 8);
        lineY += 22;
      }
      return;
    }
    var lines   = txt.split('\n').filter(function(l){return l.trim();});
    var lineH   = 18;
    var maxShow = Math.min(lines.length, Math.floor((h - 8) / lineH));
    var curY    = y + 10;
    ctx.fillStyle = _alpha(bodyTxt, 0.85);
    ctx.font = '11px Syne, sans-serif';
    ctx.textBaseline = 'top';
    for (var i = 0; i < maxShow; i++) {
      _fillTextEllipsis(ctx, lines[i], x + 16, curY, w - 20);
      curY += lineH;
    }
  }

  /* -- Helpers ----------------------------------------------------- */

  function _fillTextEllipsis(ctx, text, x, y, maxW) {
    if (!text) return;
    var str = String(text);
    if (ctx.measureText(str).width <= maxW) {
      ctx.fillText(str, x, y);
      return;
    }
    while (str.length > 0 && ctx.measureText(str + '\u2026').width > maxW) {
      str = str.slice(0, -1);
    }
    ctx.fillText(str + '\u2026', x, y);
  }

  function _getColor(key, fallback) {
    var v = _advValues && _advValues[key];
    return (v && typeof v === 'string' && v.startsWith('#')) ? v : (fallback || '#888888');
  }

  function _getNum(key, fallback) {
    var v = _advValues && _advValues[key];
    return (v !== null && v !== undefined && !isNaN(parseFloat(v))) ? parseFloat(v) : fallback;
  }

  function _getBool(key, fallback) {
    if (!_advValues || !(key in _advValues)) return fallback;
    var v = _advValues[key];
    return v === true || v === 'true';
  }

  function _alpha(hex, alpha) {
    if (!hex || !hex.startsWith('#')) return 'rgba(128,128,128,' + alpha + ')';
    var r = parseInt(hex.slice(1,3),16);
    var g = parseInt(hex.slice(3,5),16);
    var b = parseInt(hex.slice(5,7),16);
    return 'rgba('+r+','+g+','+b+','+alpha+')';
  }

  function _roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
  }

  /* -- Public API -------------------------------------------------- */
  return { open, close, toggle, onDesignChange };

})();
