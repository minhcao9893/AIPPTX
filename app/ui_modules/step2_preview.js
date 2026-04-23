/**
 * step2_preview.js — Preview pane realtime: Theme + Advanced → canvas
 * ====================================================================
 * Quản lý #s2-preview-pane:
 *   - open()  : hiện pane, ẩn layout canvas
 *   - close() : đóng pane, hiện lại layout canvas
 *   - toggle(): mở/đóng
 *   - onDesignChange(advValues, themeColors): render lại canvas ngay lập tức
 *
 * Nút trigger: bất kỳ element có class "s2-preview-toggle-btn"
 * (Advanced footer + Theme tab đều dùng chung class này)
 */

const Preview = (() => {

  /* ── State ─────────────────────────────────────────────────── */
  let _isOpen      = false;
  let _advValues   = null;   // flat object từ Step2DesignPanel.getAdvValues()
  let _themeColors = null;   // { primary, secondary, accent, bg, text }
  let _rafId       = null;   // requestAnimationFrame handle

  /* ── DOM refs (lazy) ────────────────────────────────────────── */
  function _pane()       { return document.getElementById('s2-preview-pane');    }
  function _canvasWrap() { return document.getElementById('s2-canvas-wrap');     }
  function _canvas()     { return document.getElementById('s2-preview-canvas');  }
  function _statusEl()   { return document.getElementById('s2-preview-status'); }

  /* ── Open / Close / Toggle ──────────────────────────────────── */
  function open() {
    _isOpen = true;

    const pane = _pane();
    const wrap = _canvasWrap();
    if (pane) pane.style.display = 'flex';
    if (wrap) wrap.style.display = 'none';

    // Tất cả nút Preview → trạng thái active
    document.querySelectorAll('.s2-preview-toggle-btn').forEach(function(btn) {
      btn.classList.add('active');
      // Tránh duplicate ● nếu gọi open() nhiều lần
      if (!btn.textContent.includes('●')) {
        btn.textContent = btn.textContent.replace('Preview', 'Preview ●');
      }
    });

    // Lấy state hiện tại và render ngay
    _syncState();
    _render();
  }

  function close() {
    _isOpen = false;

    const pane = _pane();
    const wrap = _canvasWrap();
    if (pane) pane.style.display = 'none';
    if (wrap) wrap.style.display = '';  // trả về flex/block theo CSS

    // Tất cả nút Preview → trạng thái bình thường
    document.querySelectorAll('.s2-preview-toggle-btn').forEach(function(btn) {
      btn.classList.remove('active');
      btn.textContent = btn.textContent.replace(' ●', '').replace('●', '');
    });
  }

  function toggle() {
    if (_isOpen) close(); else open();
  }

  /* ── Lấy state mới nhất từ các module khác ─────────────────── */
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

  /* ── Callback: gọi từ step2_design.js & step2_design_panel.js ── */
  function onDesignChange(advValues, themeColors) {
    if (advValues   !== undefined) _advValues   = advValues;
    if (themeColors !== undefined) _themeColors = themeColors;

    if (!_isOpen) return;

    // Debounce bằng rAF để không render nhiều hơn 60fps
    if (_rafId) cancelAnimationFrame(_rafId);
    _rafId = requestAnimationFrame(function() { _render(); _rafId = null; });
  }

  /* ── Render slide mẫu lên canvas ───────────────────────────── */
  function _render() {
    var cvs = _canvas();
    if (!cvs) return;

    var ctx = cvs.getContext('2d');
    var W   = cvs.width  || 960;
    var H   = cvs.height || 540;

    // Đọc màu từ themeColors + advValues (fallback về mặc định)
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
    var bandAlpha   = _getNum('transparency.header_band_alpha', 0); // 0% transparency by default
    var autoText    = _getBool('header_band.auto_text_color', true);

    // ── Nền slide ──
    ctx.fillStyle = bgLight;
    ctx.fillRect(0, 0, W, H);

    // ── Header band ──
    if (bandEnabled) {
      ctx.fillStyle = _alpha(bg, (100 - bandAlpha) / 100);
      ctx.fillRect(0, 0, W, bandH);

      // Title text (adaptive color)
      var titleColor = heading;
      if (autoText) {
          // If band is very transparent (> 50% transparency), use dark heading color
          if (bandAlpha > 50) {
              titleColor = _getColor('colors.heading', '#1E2761');
          } else {
              titleColor = '#ffffff';
          }
      }

      ctx.fillStyle = titleColor;
      ctx.font = 'bold 18px Syne, sans-serif';
      ctx.textBaseline = 'middle';
      var titleX = 28;
      ctx.fillText('Tiêu đề Slide Mẫu', titleX, bandH / 2);
    }

    // ── Content area ──
    var contentTop = bandEnabled ? bandH + 8 : 8;
    var margin     = 24;
    var contentH   = H - contentTop - margin;

    // Nếu có insight panel bên phải
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

    // ── Content blocks (giả lập bảng / bullet) ──
    var blockColor = _alpha((_themeColors && _themeColors.secondary) || '#0055aa', 0.15);
    var blockBorder = (_themeColors && _themeColors.secondary) || '#0055aa';

    // Bullet lines
    var lineY = contentTop + 16;
    for (var i = 0; i < 5; i++) {
      var lineW = leftW * (0.9 - i * 0.05);
      ctx.fillStyle = _alpha(bodyTxt, 0.15);
      ctx.fillRect(margin + 16, lineY, lineW, 8);
      lineY += 20;
    }

    // Table giả lập
    var tableTop = lineY + 12;
    var tableH   = contentTop + contentH - tableTop - 8;
    if (tableH > 40) {
      var rows = 4;
      var rowH = tableH / rows;
      var cols = 3;
      var colW = (leftW - 16) / cols;

      for (var r = 0; r < rows; r++) {
        for (var c = 0; c < cols; c++) {
          var cellX = margin + 8 + c * colW;
          var cellY = tableTop + r * rowH;
          if (r === 0) {
            ctx.fillStyle = _alpha(bg, 0.7);
          } else {
            ctx.fillStyle = r % 2 === 0 ? _alpha(blockBorder, 0.06) : 'transparent';
          }
          ctx.fillRect(cellX, cellY, colW - 2, rowH - 2);

          ctx.fillStyle = r === 0 ? heading : bodyTxt;
          ctx.font = (r === 0 ? 'bold ' : '') + '10px JetBrains Mono, monospace';
          ctx.textBaseline = 'middle';
          ctx.fillText(r === 0 ? ['Hạng mục','Giá trị','%'][c] : '—', cellX + 6, cellY + rowH / 2);
        }
      }
    }

    // ── Divider ──
    if (divEnabled && insightEn) {
      ctx.strokeStyle = dividerC;
      ctx.lineWidth   = 1.5;
      ctx.setLineDash([]);
      ctx.beginPath();
      ctx.moveTo(rightX - 8, contentTop + 8);
      ctx.lineTo(rightX - 8, contentTop + contentH - 8);
      ctx.stroke();
    }

    // ── Insight panel ──
    if (insightEn && rightW > 20) {
      ctx.fillStyle = insightBg;
      _roundRect(ctx, rightX, contentTop, rightW, contentH, 6);
      ctx.fill();

      ctx.strokeStyle = _alpha(accent, 0.3);
      ctx.lineWidth   = 1;
      _roundRect(ctx, rightX, contentTop, rightW, contentH, 6);
      ctx.stroke();

      // Label "AI Insight"
      var labelText = _advValues && _advValues['right_panel.label.text'] ? _advValues['right_panel.label.text'] : 'AI Insight';
      ctx.fillStyle = accent;
      ctx.font = 'bold 11px Syne, sans-serif';
      ctx.textBaseline = 'top';
      ctx.fillText(labelText, rightX + 10, contentTop + 12);

      // Insight lines
      ctx.fillStyle = _alpha(bodyTxt, 0.5);
      ctx.font = '9px Syne, sans-serif';
      var iy = contentTop + 36;
      ['• Nhận xét 1...', '• Nhận xét 2...', '• Nhận xét 3...'].forEach(function(line) {
        ctx.fillText(line, rightX + 10, iy);
        iy += 20;
      });
    }

    // ── Update status badge ──
    var statusEl = _statusEl();
    if (statusEl) {
      var themeName = 'Custom';
      try {
        if (typeof Step2Design !== 'undefined') {
          var d = Step2Design.getDesign();
          themeName = d.theme || 'Custom';
        }
      } catch(e) {}
      statusEl.textContent = 'Theme: ' + themeName
        + '  |  Header: ' + (bandEnabled ? 'ON' : 'OFF')
        + '  |  Insight: ' + (insightEn ? 'ON' : 'OFF');
    }
  }

  /* ── Helpers ────────────────────────────────────────────────── */

  /** Lấy màu từ _advValues nếu có, nếu không dùng fallback */
  function _getColor(key, fallback) {
    var v = _advValues && _advValues[key];
    return (v && typeof v === 'string' && v.startsWith('#')) ? v : (fallback || '#888888');
  }

  /** Lấy số từ _advValues nếu có */
  function _getNum(key, fallback) {
    var v = _advValues && _advValues[key];
    return (v !== null && v !== undefined && !isNaN(parseFloat(v))) ? parseFloat(v) : fallback;
  }

  /** Lấy bool từ _advValues nếu có */
  function _getBool(key, fallback) {
    if (!_advValues || !(key in _advValues)) return fallback;
    var v = _advValues[key];
    return v === true || v === 'true';
  }

  /** hex → rgba string với alpha */
  function _alpha(hex, alpha) {
    if (!hex || !hex.startsWith('#')) return 'rgba(128,128,128,' + alpha + ')';
    var r = parseInt(hex.slice(1,3),16);
    var g = parseInt(hex.slice(3,5),16);
    var b = parseInt(hex.slice(5,7),16);
    return 'rgba('+r+','+g+','+b+','+alpha+')';
  }

  /** drawRoundRect helper */
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

  /* ── Public API ─────────────────────────────────────────────── */
  return { open, close, toggle, onDesignChange };

})();
