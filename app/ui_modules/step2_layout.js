/**
 * step2_layout.js — Step II: Layout picker + % ô config
 * =======================================================
 * Quản lý:
 *   - Chips thành phần (Title luôn xanh đậm, không vào layout)
 *   - Dropdown layout: Vertical / Horizontal / Table 2 dòng / Table 3 dòng
 *   - Table mode: dropdown chọn phân bổ [a:b] hoặc [a:b:c]
 *   - Ô % kích thước: ô cuối mỗi dòng = auto (readonly, hiện mờ)
 *
 * Phụ thuộc:
 *   - app_shell.html → #s2-comp-chips, #s2-layout-select, #s2-pct-inputs
 *   - step2_canvas.js → Canvas.draw(components, layout, sizes)
 */

const Layout = (() => {

  /* ── State ──────────────────────────────────────────────── */
  let _slide      = null;
  let _cfg        = null;
  let _slideIdx   = null;   // index slide hiện tại (dùng để save trước khi chuyển)
  let _comps      = [];     // Array of { id, label, type, active }
  let _layout     = 'vertical';
  let _sizes      = [];     // vertical/horizontal: array of % (null = auto)
  let _tableRows  = null;   // table mode: [{ items, pcts }]
  let _tableDist  = null;   // phân bổ đang chọn, vd [2,3] cho table2
  let _dragSrcId  = null;

  /* ── Called by step2_slides when a slide is selected ─────── */
  function onSlideSelected(idx, slide, cfg) {
    _slide = slide;
    _cfg   = cfg;
    _buildComponents(slide, cfg);
    renderChips();
    renderPctInputs();
    Canvas.draw(_comps.filter(c => c.active), _layout, _tableRows || _sizes);
  }

  /* ── Build component list từ slide + config ──────────────── */
  function _generateBaseComponents(slide, cfg) {
    const comps = [];
    comps.push({ id: 'title', label: 'Title', type: 'title', active: true });

    const nTbl = slide.table_count || 0;
    for (let t = 0; t < nTbl; t++) {
      comps.push({ id: `tbl${t}`, label: `Bảng ${t+1}`, type: 'table', active: true });
      if (cfg.useChart) {
        comps.push({ id: `cht${t}`, label: `Chart ${t+1}`, type: 'chart', active: true });
      }
    }
    if (cfg.hasContent)  comps.push({ id: 'content', label: 'Content',  type: 'content',  active: true });
    if (cfg.genInsight)  comps.push({ id: 'insight', label: 'Insight',  type: 'insight',  active: true });
    
    for (let k = 0; k < (cfg.imageCount || 0); k++) {
      let url = null;
      if (cfg.imageUrls && cfg.imageUrls[k]) url = cfg.imageUrls[k];
      else if (slide.images && slide.images[k]) url = '/api/media/' + slide.images[k];
      comps.push({ id: `img${k}`, label: `Image ${k+1}`, type: 'image', active: true, url: url });
    }
    return comps;
  }

  function _mergeComponents(prev, base) {
    if (!prev || prev.length === 0) return base;

    const baseMap = new Map(base.map(c => [c.id, c]));
    const merged = [];

    // Giữ nguyên các component cũ (và trạng thái active) nếu nó vẫn tồn tại trong base
    for (const p of prev) {
      if (baseMap.has(p.id)) {
        const b = baseMap.get(p.id);
        merged.push({ ...b, active: p.active });
        baseMap.delete(p.id);
      }
    }

    // Thêm các component mới vào cuối
    for (const b of base) {
      if (baseMap.has(b.id)) {
        merged.push(b);
      }
    }

    return merged;
  }

  /* ── Chips (with drag-and-drop reorder) ─────────────────── */
  function renderChips() {
    const el = document.getElementById('s2-comp-chips');
    el.innerHTML = _comps.map(c => {
      const isTitle = c.id === 'title';
      // Title: xanh đậm riêng, không drag, không toggle
      const chipStyle = isTitle
        ? 'background:var(--accent,#1a56db); color:#fff; opacity:1; cursor:default; user-select:none;'
        : `cursor:grab; user-select:none; transition: opacity 0.15s, transform 0.15s;`;
      return `
        <span class="chip ${isTitle ? '' : (c.active ? 'active' : 'inactive')} ${isTitle ? 'chip-nodrag' : ''}"
              draggable="${!isTitle}"
              data-id="${c.id}"
              onclick="Layout.toggleComp('${c.id}')"
              ondragstart="Layout._onDragStart(event, '${c.id}')"
              ondragover="Layout._onDragOver(event)"
              ondrop="Layout._onDrop(event, '${c.id}')"
              ondragend="Layout._onDragEnd(event)"
              ondragenter="Layout._onDragEnter(event)"
              ondragleave="Layout._onDragLeave(event)"
              style="${chipStyle}">
          ${_compIcon(c.type)} ${c.label}
        </span>
      `;
    }).join('');
  }

  /* ── Drag handlers ───────────────────────────────────────── */
  function _onDragStart(e, id) {
    _dragSrcId = id;
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', id);
    // Fade ra chip đang kéo
    setTimeout(() => {
      const el = document.querySelector(`#s2-comp-chips [data-id="${id}"]`);
      if (el) el.style.opacity = '0.35';
    }, 0);
  }

  function _onDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  }

  function _onDragEnter(e) {
    const chip = e.currentTarget;
    const targetId = chip.dataset.id;
    if (targetId && targetId !== _dragSrcId) {
      chip.style.transform = 'scale(1.08)';
      chip.style.boxShadow = '0 0 0 2px var(--accent)';
    }
  }

  function _onDragLeave(e) {
    const chip = e.currentTarget;
    chip.style.transform = '';
    chip.style.boxShadow = '';
  }

  function _onDrop(e, targetId) {
    e.preventDefault();
    const chip = e.currentTarget;
    chip.style.transform = '';
    chip.style.boxShadow = '';

    if (!_dragSrcId || _dragSrcId === targetId) return;
    // Title không thể bị đẩy khỏi vị trí đầu
    if (targetId === 'title') return;

    const srcIdx = _comps.findIndex(c => c.id === _dragSrcId);
    const dstIdx = _comps.findIndex(c => c.id === targetId);
    if (srcIdx === -1 || dstIdx === -1) return;

    // Reorder
    const [moved] = _comps.splice(srcIdx, 1);
    _comps.splice(dstIdx, 0, moved);

    _dragSrcId = null;
    _recalcSizes();
    renderChips();
    renderPctInputs();
    _draw();
  }

  function _onDragEnd(e) {
    _dragSrcId = null;
    // Reset opacity tất cả chips
    document.querySelectorAll('#s2-comp-chips .chip').forEach(el => {
      el.style.opacity = '';
      el.style.transform = '';
      el.style.boxShadow = '';
    });
  }

  function _compIcon(type) {
    return { title:'📌', table:'📋', chart:'📈', content:'📝', insight:'💡', image:'🖼️' }[type] || '▪';
  }

  function toggleComp(id) {
    // Nếu đang kéo thì không toggle
    if (_dragSrcId) return;
    const c = _comps.find(c => c.id === id);
    if (!c) return;
    // Title không được tắt
    if (id === 'title') return;
    // Lưu lại danh sách active cũ để xem số lượng có thay đổi không
    const prevActiveCount = _comps.filter(x => x.active && x.id !== 'title').length;

    c.active = !c.active;

    renderChips();
    
    const newActiveCount = _comps.filter(x => x.active && x.id !== 'title').length;
    if (prevActiveCount !== newActiveCount) {
      _recalcSizes(); // Nếu toggle làm đổi số lượng active, phải recalc
    } else {
      // Trường hợp hiếm, nhưng nếu không đổi, ít nhất update lại rows cho table
      if (_layout.startsWith('table')) {
         const active = _comps.filter(x => x.active && x.id !== 'title');
         if (_tableDist && _tableRows) {
            _tableRows = _buildTableRows(active, _tableDist);
         }
      }
    }

    renderPctInputs();
    _draw();
  }

  /* ── Layout change ───────────────────────────────────────── */
  function onLayoutChange() {
    _layout = document.getElementById('s2-layout-select').value;
    _tableDist = null; // reset phân bổ khi đổi layout
    _recalcSizes();
    _renderDistDropdown();
    renderPctInputs();
    _draw();
  }

  /* ── Dropdown phân bổ [a:b] / [a:b:c] ───────────────────── */

  /** Sinh tất cả cách chia n vào k phần, mỗi phần >= 1 */
  function _genDistributions(n, k) {
    if (k === 1) return [[n]];
    const result = [];
    for (let a = 1; a <= n - k + 1; a++) {
      _genDistributions(n - a, k - 1).forEach(rest => result.push([a, ...rest]));
    }
    return result;
  }

  function _renderDistDropdown() {
    const el = document.getElementById('s2-dist-wrap');
    if (!el) return;

    const isTable = _layout === 'table2' || _layout === 'table3';
    if (!isTable) { el.innerHTML = ''; return; }

    const numRows = _layout === 'table2' ? 2 : 3;
    // n = số chip active KHÔNG tính Title
    const active = _comps.filter(c => c.active && c.id !== 'title');
    const n = active.length;
    if (n < numRows) {
      el.innerHTML = `<span style="font-size:11px;color:var(--txt-dim);">Cần ít nhất ${numRows} chip</span>`;
      return;
    }

    const dists = _genDistributions(n, numRows);
    // Chọn default: chia đều nhất (dist đầu tiên có các giá trị gần nhau)
    if (!_tableDist) {
      _tableDist = dists[Math.floor(dists.length / 2)];
    }
    const curKey = _tableDist.join(':');

    el.innerHTML = `
      <label style="font-size:11px; color:var(--txt-dim); margin-right:4px;">Phân bổ:</label>
      <select id="s2-dist-select"
              onchange="Layout.onDistChange(this.value)"
              style="font-size:12px; padding:2px 4px; border-radius:4px;">
        ${dists.map(d => {
          const key = d.join(':');
          const label = d.map((v, i) => `R${i+1}:${v}`).join(' / ');
          return `<option value="${key}" ${key === curKey ? 'selected' : ''}>${label}</option>`;
        }).join('')}
      </select>
    `;
  }

  function onDistChange(val) {
    _tableDist = val.split(':').map(Number);
    _recalcSizes();
    renderPctInputs();
    _draw();
  }

  /* ── Size calculation ────────────────────────────────────── */
  function _recalcSizes() {
    // active KHÔNG tính Title cho layout body
    const active = _comps.filter(c => c.active && c.id !== 'title');
    const n = active.length;
    if (n === 0) { _sizes = []; _tableRows = null; return; }

    if (_layout === 'vertical' || _layout === 'horizontal') {
      const per = Math.floor(100 / n);
      _sizes = active.map((_, i) => i < n - 1 ? per : null);
      _tableRows = null;
    } else if (_layout === 'table2' || _layout === 'table3') {
      const numRows = _layout === 'table2' ? 2 : 3;
      // Nếu chưa có dist hoặc dist không hợp lệ, chọn default
      if (!_tableDist || _tableDist.length !== numRows || _tableDist.reduce((a,b)=>a+b,0) !== n) {
        const dists = _genDistributions(n, numRows);
        _tableDist = dists.length ? dists[Math.floor(dists.length / 2)] : null;
      }
      _tableRows = _tableDist ? _buildTableRows(active, _tableDist) : null;
    }
  }

  /**
   * Xây dựng rows từ dist đã chọn.
   * dist = [a, b] hoặc [a, b, c] — số chip mỗi dòng.
   * Mỗi dòng: các ô trước chia đều, ô cuối = auto (null, hiện mờ).
   */
  function _buildTableRows(active, dist) {
    const rows = [];
    let idx = 0;
    dist.forEach(count => {
      const items = active.slice(idx, idx + count);
      idx += count;
      const per = Math.floor(100 / count);
      // ô cuối = null (auto)
      const pcts = items.map((_, i) => i < count - 1 ? per : null);
      rows.push({ items, pcts });
    });
    return rows;
  }

  /* ── Render % inputs ─────────────────────────────────────── */
  function renderPctInputs() {
    const el = document.getElementById('s2-pct-inputs');
    if (!el) return;

    const active = _comps.filter(c => c.active && c.id !== 'title');
    if (active.length === 0) { el.innerHTML = ''; return; }

    if (_layout === 'vertical' || _layout === 'horizontal') {
      el.innerHTML = active.map((c, i) => {
        const val = _sizes[i];
        const isAuto = val === null;
        return `
          <input class="pct-inp" ${isAuto ? 'readonly' : ''}
                 value="${isAuto ? '' : val}"
                 placeholder="${isAuto ? 'auto' : ''}"
                 title="${c.label}" data-idx="${i}"
                 onchange="Layout.onSizeChange(${i}, this.value)"
                 style="width:50px; ${isAuto ? 'opacity:0.45;' : ''}">
          <span style="font-size:10px; color:var(--txt-dim);">%</span>
        `;
      }).join(' ');

    } else if (_tableRows) {
      // Chỉ hiện khi đã có dist hợp lệ
      el.innerHTML = _tableRows.map((row, r) => `
        <div style="display:flex; gap:4px; align-items:center; margin-bottom:2px;">
          <span style="font-size:10px; color:var(--txt-dim); min-width:24px;">R${r+1}</span>
          ${row.items.map((c, ci) => {
            const val = row.pcts[ci];
            const isAuto = val === null;
            return `
              <input class="pct-inp" ${isAuto ? 'readonly' : ''}
                     value="${isAuto ? '' : val}"
                     placeholder="${isAuto ? 'auto' : ''}"
                     title="${c.label}" data-row="${r}" data-col="${ci}"
                     onchange="Layout.onTableSizeChange(${r}, ${ci}, this.value)"
                     style="width:46px; ${isAuto ? 'opacity:0.4;' : ''}">
              <span style="font-size:10px; color:var(--txt-dim);">%</span>
            `;
          }).join('')}
        </div>
      `).join('');
    } else if (_layout.startsWith('table')) {
      el.innerHTML = `<span style="font-size:11px; color:var(--txt-dim);">Chọn phân bổ dòng ở trên</span>`;
    }
  }

  function onSizeChange(idx, val) {
    val = Math.max(5, Math.min(95, parseInt(val) || 0));
    _sizes[idx] = val;
    // ô cuối luôn null (auto)
    _sizes[_sizes.length - 1] = null;
    renderPctInputs();
    _draw();
  }

  function onTableSizeChange(r, ci, val) {
    if (!_tableRows) return;
    const row = _tableRows[r];
    val = Math.max(5, Math.min(95, parseInt(val) || 0));
    row.pcts[ci] = val;
    // ô cuối dòng luôn null (auto)
    row.pcts[row.pcts.length - 1] = null;
    renderPctInputs();
    _draw();
  }

  /* ── Draw ────────────────────────────────────────────────── */
  function _draw() {
    const bodyComps = _comps.filter(c => c.active && c.id !== 'title');
    Canvas.draw(bodyComps, _layout, _layout.startsWith('table') ? _tableRows : _sizes);
  }

  /* ── onSlideSelected — re-render dist dropdown khi slide thay đổi */
  function onSlideSelected(idx, slide, cfg) {
    const isSameSlide = (_slideIdx === idx);

    // Lưu layoutConfig của slide trước khi rời khỏi (nếu chuyển slide)
    if (_slideIdx !== null && !isSameSlide) {
      Step2Slides.setLayoutConfig(_slideIdx, getLayoutConfig());
    }

    const previousComps = isSameSlide ? [..._comps] : (cfg.layoutConfig ? cfg.layoutConfig.allComps : null);

    _slideIdx = idx;
    _slide = slide;
    _cfg   = cfg;

    const saved = cfg.layoutConfig;

    if (saved && !isSameSlide) {
      _layout    = saved.layout    || 'vertical';
      _tableDist = saved.tableDist || null;
    } else if (!isSameSlide) {
      _layout    = 'vertical';
      _tableDist = null;
      _tableRows = null;
    }

    const baseComps = _generateBaseComponents(slide, cfg);
    _comps = _mergeComponents(previousComps, baseComps);

    // Xử lý sizes và tableRows
    if (saved && !isSameSlide) {
      _sizes     = saved.sizes     && saved.sizes.length     ? saved.sizes     : _sizes;
      _tableRows = saved.tableRows && saved.tableRows.length ? saved.tableRows : _tableRows;
    } else {
      // Khi tương tác trên cùng slide (toggle/thay đổi số lượng hình), 
      // nếu số lượng component active thay đổi thì cần recalc size
      const activeCount = _comps.filter(c => c.active && c.id !== 'title').length;
      let needRecalc = false;

      if (_layout === 'vertical' || _layout === 'horizontal') {
        if (!_sizes || _sizes.length !== activeCount) needRecalc = true;
      } else if (_layout.startsWith('table')) {
        if (!_tableDist || _tableDist.reduce((a,b)=>a+b,0) !== activeCount) needRecalc = true;
      }

      if (needRecalc) {
        if (!isSameSlide) _tableDist = null; // chỉ reset dist nếu là slide mới
        _recalcSizes();
      } else if (isSameSlide && _layout.startsWith('table')) {
        // Cập nhật lại tableRows nếu thứ tự/nội dung đổi nhưng số lượng không đổi
        const active = _comps.filter(c => c.active && c.id !== 'title');
        if (_tableDist) _tableRows = _buildTableRows(active, _tableDist);
      }
    }

    // Sync dropdown UI với _layout
    const sel = document.getElementById('s2-layout-select');
    if (sel) sel.value = _layout;

    renderChips();
    _renderDistDropdown();
    renderPctInputs();
    _draw();
  }

  /* ── Getters (dùng bởi step2_export) ────────────────────── */
  function getLayoutConfig() {
    const bodyComps = _comps.filter(c => c.active && c.id !== 'title');
    // Tính pct per-slide đúng cho backend:
    // vertical/horizontal: dùng _sizes (giữ nguyên null = auto, backend tự tính phần còn lại)
    // table: dùng _tableRows
    let pctForBackend;
    if (_layout === 'vertical' || _layout === 'horizontal') {
      // Gửi tỷ lệ thực tế, null = auto (backend tính phần còn lại)
      pctForBackend = _sizes.map(s => s === null ? 0 : s);
    } else {
      // Table mode: flatten pct từ tất cả rows, null → 0
      pctForBackend = (_tableRows || []).flatMap(r => r.pcts.map(p => p === null ? 0 : p));
    }
    return {
      layout:     _layout,
      sizes:      _layout.startsWith('table') ? _tableRows : _sizes,
      tableDist:  _tableDist,
      tableRows:  _tableRows,
      components: bodyComps,
      allComps:   _comps, // Lưu tất cả comps (kể cả inactive) để phục hồi UI state
      // field dùng cho backend
      layout_type: _layout,
      pct:        pctForBackend,
      margin:     0.25
    };
  }

  function buildDefaultConfig(slide, cfg) {
    const baseComps = _generateBaseComponents(slide, cfg);
    const bodyComps = baseComps.filter(c => c.active && c.id !== 'title');
    const n = bodyComps.length;
    
    // Mặc định là vertical, chia đều
    const per = n > 0 ? Math.floor(100 / n) : 0;
    const sizes = bodyComps.map((_, i) => i < n - 1 ? per : null);
    const pct = sizes.map(s => s === null ? 0 : s);
    
    return {
      layout:      'vertical',
      sizes:       sizes,
      tableDist:   null,
      tableRows:   null,
      components:  bodyComps,
      allComps:    baseComps,
      layout_type: 'vertical',
      pct:         pct,
      margin:      0.25
    };
  }

  return {
    onSlideSelected, toggleComp, onLayoutChange, onDistChange,
    onSizeChange, onTableSizeChange, getLayoutConfig, buildDefaultConfig,
    _onDragStart, _onDragOver, _onDragEnter, _onDragLeave, _onDrop, _onDragEnd
  };
})();
