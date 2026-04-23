/**
 * step2_slides.js — Step II: Danh sách Slide Cards (MID panel 20%)
 * ==================================================================
 * Mỗi card đại diện 1 slide, chứa:
 *   - Tiêu đề slide
 *   - Số lượng bảng (tables)
 *   - Toggle: vẽ Chart từ bảng không?
 *     → Khi ON: Layout tự thêm Chart cho TẤT CẢ bảng vào Thành phần
 *     → User có thể bật/tắt từng chip Chart bên Layout panel
 *   - Toggle: có content ban đầu không?
 *   - Toggle: sinh Insight cho slide không?
 *
 * Mặc định: tất cả toggle = OFF
 * KHÔNG còn dropdown [Bảng/Chart/Cả 2] — Logic được handle bởi Layout chips
 *
 * Phụ thuộc:
 *   - app_shell.html → #s2-slides-list, #s2-slide-count
 *   - step2_layout.js → Layout.onSlideSelected(slideIdx)
 */

const Step2Slides = (() => {

  /* ── State ──────────────────────────────────────────────── */
  let _slides = [];       // Array of slide objects từ parse
  let _selected = 0;      // Index slide đang được chọn
  let _configs = [];      // Array of per-slide config objects
  // layoutConfig: { layout, sizes, components } — lưu per-slide, set bởi Layout

  /**
   * Slide config object:
   * {
   *   useChart:    boolean   // toggle chart từ bảng (ON = thêm Chart chips vào Layout)
   *   hasContent:  boolean   // có content ban đầu
   *   genInsight:  boolean   // sinh insight
   * }
   * NOTE: tableMode đã bị xóa — khi useChart=ON, Layout tự thêm Chart cho mọi bảng
   */

  /* ── Init ───────────────────────────────────────────────── */
  /**
   * @param {Array} slides - [{title, table_count, has_content}, ...]
   */
  function init(slides) {
    _slides = slides;
    _configs = slides.map(s => {
      const cfg = {
        useChart:    false,
        hasContent:  s.has_content || false,
        genInsight:  false,
        imageCount:  s.image_count || 0,
        layoutConfig: null
      };
      // Pre-initialize layoutConfig so that if user doesn't click, we still have a valid default
      if (typeof Layout !== 'undefined' && Layout.buildDefaultConfig) {
        cfg.layoutConfig = Layout.buildDefaultConfig(s, cfg);
      }
      return cfg;
    });

    document.getElementById('s2-slide-count').textContent = slides.length;
    _initGlobalHeader();
    render();
    selectSlide(0);
  }

  /* ── Global Header ──────────────────────────────────────── */
  function _initGlobalHeader() {
    const hdr = document.getElementById('s2-global-header');
    if (!hdr) return;
    // Chỉ hiện header khi có >= 2 slides
    hdr.style.display = _slides.length >= 2 ? 'block' : 'none';
    // Chỉ hiện row Chart khi có ít nhất 1 slide có bảng
    const hasAnyTable = _slides.some(s => (s.table_count || 0) > 0);
    const chartRow = document.getElementById('s2-gh-chart-row');
    if (chartRow) chartRow.style.display = hasAnyTable ? 'flex' : 'none';
    _refreshGlobalHeader();
  }

  function _refreshGlobalHeader() {
    _refreshGlobalBtn('chart',   _getGlobalState('useChart'));
    _refreshGlobalBtn('content', _getGlobalState('hasContent'));
    _refreshGlobalBtn('insight', _getGlobalState('genInsight'));
  }

  /**
   * Trả về 'on' | 'off' | 'mixed' dựa trên tất cả _configs[]
   * Với useChart: chỉ tính những slide có bảng
   */
  function _getGlobalState(key) {
    let arr = _configs.map((c, i) => {
      if (key === 'useChart' && !(_slides[i].table_count > 0)) return null;
      return c[key];
    }).filter(v => v !== null);
    if (arr.length === 0) return 'off';
    const allOn  = arr.every(v => v === true);
    const allOff = arr.every(v => v === false);
    return allOn ? 'on' : allOff ? 'off' : 'mixed';
  }

  function _refreshGlobalBtn(name, state) {
    const btnOn  = document.getElementById(`s2-gh-${name}-on`);
    const btnOff = document.getElementById(`s2-gh-${name}-off`);
    if (!btnOn || !btnOff) return;
    // Reset
    btnOn.className  = 'mini-opt';
    btnOff.className = 'mini-opt';
    if (state === 'on')    { btnOn.classList.add('on');  btnOff.classList.add('off'); }
    else if (state === 'off') { btnOff.classList.add('on'); btnOn.classList.add('off'); }
    else { // mixed
      btnOn.classList.add('mixed');
      btnOff.classList.add('mixed');
    }
  }

  /* ── Render ─────────────────────────────────────────────── */
  function render() {
    const list = document.getElementById('s2-slides-list');
    list.innerHTML = _slides.map((s, i) => _renderCard(s, i)).join('');
  }

  function _renderCard(slide, i) {
    const cfg   = _configs[i];
    const nTbl  = slide.table_count || 0;
    const sel   = i === _selected;

    return `
<div class="slide-card ${sel ? 'selected' : ''}" id="sc-${i}" onclick="Step2Slides.selectSlide(${i})">
  <div class="slide-card-title" title="${slide.title}">
    <span style="font-size:10px; color:var(--txt-dim); margin-right:4px;">${i+1}.</span>
    ${slide.title || `Slide ${i+1}`}
  </div>
  <div class="slide-meta">
    ${nTbl ? `<span class="slide-meta-chip">📊 ${nTbl} bảng</span>` : ''}
    ${cfg.hasContent ? '<span class="slide-meta-chip">📝 content</span>' : ''}
    ${cfg.genInsight ? '<span class="slide-meta-chip" style="color:var(--accent5);">💡 insight</span>' : ''}
    ${cfg.useChart   ? '<span class="slide-meta-chip" style="color:var(--accent2);">📈 chart</span>' : ''}
  </div>

  <!-- Expanded config — chỉ show khi selected -->
  <div class="slide-card-expanded">

    <!-- Toggle: sinh chart từ bảng -->
    ${nTbl > 0 ? `
    <div class="expand-row">
      <span class="expand-label">Vẽ chart từ bảng</span>
      <div class="mini-toggle">
        <button class="mini-opt ${cfg.useChart ? 'on' : 'off'}" onclick="Step2Slides.toggleChart(${i},true);event.stopPropagation()">ON</button>
        <button class="mini-opt ${!cfg.useChart ? 'on' : 'off'}" onclick="Step2Slides.toggleChart(${i},false);event.stopPropagation()">OFF</button>
      </div>
    </div>
    ${cfg.useChart ? `<div style="margin-left:12px; font-size:10px; color:var(--accent2); opacity:0.8;">📈 ${nTbl} chart sẽ được thêm vào Thành phần</div>` : ''}
    ` : ''}

    <!-- Toggle: có content -->
    <div class="expand-row">
      <span class="expand-label">Content ban đầu</span>
      <div class="mini-toggle">
        <button class="mini-opt ${cfg.hasContent ? 'on' : 'off'}" onclick="Step2Slides.toggleContent(${i},true);event.stopPropagation()">ON</button>
        <button class="mini-opt ${!cfg.hasContent ? 'on' : 'off'}" onclick="Step2Slides.toggleContent(${i},false);event.stopPropagation()">OFF</button>
      </div>
    </div>

    <!-- Toggle: Insight -->
    <div class="expand-row">
      <span class="expand-label">Sinh Insight</span>
      <div class="mini-toggle">
        <button class="mini-opt ${cfg.genInsight ? 'on' : 'off'}" onclick="Step2Slides.toggleInsight(${i},true);event.stopPropagation()">ON</button>
        <button class="mini-opt ${!cfg.genInsight ? 'on' : 'off'}" onclick="Step2Slides.toggleInsight(${i},false);event.stopPropagation()">OFF</button>
      </div>
    </div>

    <!-- Image Count -->
    <div class="expand-row" style="margin-top:6px; padding-top:6px; border-top:1px dashed var(--border-color);">
      <span class="expand-label">🖼️ Image</span>
      <div style="display:flex; align-items:center; gap:8px;">
        <button class="mini-opt" style="padding:2px 8px; background:var(--bg); color:var(--txt-muted); border:1px solid var(--border);" 
                onclick="Step2Slides.changeImageCount(${i}, -1);event.stopPropagation()">-</button>
        <span style="font-size:12px; font-weight:600; min-width:16px; text-align:center; color:var(--txt);">${cfg.imageCount}</span>
        <button class="mini-opt" style="padding:2px 8px; background:var(--bg); color:var(--txt-muted); border:1px solid var(--border);" 
                onclick="Step2Slides.changeImageCount(${i}, 1);event.stopPropagation()">+</button>
      </div>
    </div>

  </div><!-- /expanded -->
</div>
`;
  }

  // _renderTableModes đã bị xóa — không còn dropdown per-table
  // Khi useChart=ON, Layout._buildComponents() tự thêm cả Bảng lẫn Chart cho mọi bảng

  /* ── Handlers ────────────────────────────────────────────── */
  function selectSlide(i) {
    _selected = i;
    render();  // Re-render to expand correct card
    Layout.onSlideSelected(i, _slides[i], _configs[i]);
  }

  function toggleChart(i, val) {
    _configs[i].useChart = val;
    _reRenderCard(i);
    _refreshGlobalHeader();
    if (_selected === i) Layout.onSlideSelected(i, _slides[i], _configs[i]);
  }

  function toggleContent(i, val) {
    _configs[i].hasContent = val;
    _reRenderCard(i);
    _refreshGlobalHeader();
    if (_selected === i) Layout.onSlideSelected(i, _slides[i], _configs[i]);
  }

  function toggleInsight(i, val) {
    _configs[i].genInsight = val;
    _reRenderCard(i);
    _refreshGlobalHeader();
    if (_selected === i) Layout.onSlideSelected(i, _slides[i], _configs[i]);
  }

  function changeImageCount(i, delta) {
    let newVal = (_configs[i].imageCount || 0) + delta;
    if (newVal < 0) newVal = 0;
    if (newVal > 6) newVal = 6; // Limit max images
    _configs[i].imageCount = newVal;
    _reRenderCard(i);
    if (_selected === i) Layout.onSlideSelected(i, _slides[i], _configs[i]);
  }

  /* ── Set All (Global) ─────────────────────────────────── */
  function setAllChart(val) {
    _configs.forEach((c, i) => {
      if (_slides[i].table_count > 0) c.useChart = val;
    });
    render();
    _refreshGlobalHeader();
    if (_selected !== null) Layout.onSlideSelected(_selected, _slides[_selected], _configs[_selected]);
  }

  function setAllContent(val) {
    _configs.forEach(c => { c.hasContent = val; });
    render();
    _refreshGlobalHeader();
    if (_selected !== null) Layout.onSlideSelected(_selected, _slides[_selected], _configs[_selected]);
  }

  function setAllInsight(val) {
    _configs.forEach(c => { c.genInsight = val; });
    render();
    _refreshGlobalHeader();
    if (_selected !== null) Layout.onSlideSelected(_selected, _slides[_selected], _configs[_selected]);
  }

  function _reRenderCard(i) {
    const old = document.getElementById(`sc-${i}`);
    if (old) old.outerHTML = _renderCard(_slides[i], i);
  }

  /* ── Public ─────────────────────────────────────────────── */
  function getConfig(i) { return _configs[i]; }
  function getAllConfigs() { return _configs; }
  function getSlides() { return _slides; }
  function getSelectedIdx() { return _selected; }

  /** Gọi bởi Layout để lưu layoutConfig của slide i trước khi chuyển sang slide khác */
  function setLayoutConfig(i, cfg) {
    if (_configs[i]) _configs[i].layoutConfig = cfg;
  }

  return { init, selectSlide, toggleChart, toggleContent, toggleInsight, changeImageCount,
           setAllChart, setAllContent, setAllInsight,
           getConfig, getAllConfigs, getSlides, getSelectedIdx, setLayoutConfig };
})();
