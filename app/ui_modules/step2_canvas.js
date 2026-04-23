/**
 * step2_canvas.js — Step II: Render preview layout canvas
 */

const Canvas = (() => {

  const ICONS = { title:'📌', table:'📋', chart:'📈', content:'📝', insight:'💡', image:'🖼️' };
  const TYPE_CLASS = { title:'cv-title', table:'cv-table', chart:'cv-chart', content:'cv-content', insight:'cv-insight', image:'cv-image' };

  function draw(components, layout, sizes) {
    const canvas = document.getElementById('s2-canvas');
    if (!canvas) return;

    // Xóa tất cả block cũ (KHÔNG xóa #s2-canvas-empty)
    Array.from(canvas.children).forEach(child => {
      if (child.id !== 's2-canvas-empty') child.remove();
    });

    const empty = document.getElementById('s2-canvas-empty');

    if (!components || components.length === 0) {
      if (empty) empty.style.display = 'flex';
      return;
    }

    if (empty) empty.style.display = 'none';

    if (layout === 'vertical')                           _drawVertical(canvas, components, sizes);
    else if (layout === 'horizontal')                    _drawHorizontal(canvas, components, sizes);
    else if (layout === 'table2' || layout === 'table3') _drawTable(canvas, components, sizes);
  }

  function _drawVertical(canvas, comps, sizes) {
    let y = 0;
    comps.forEach((c, i) => {
      const pct = (sizes[i] !== null && sizes[i] !== undefined) ? sizes[i] : _autoRemainder(sizes, i);
      canvas.appendChild(_makeBlock(c, { top:`${y}%`, left:'0', width:'100%', height:`${pct}%` }));
      y += pct;
    });
  }

  function _drawHorizontal(canvas, comps, sizes) {
    let x = 0;
    comps.forEach((c, i) => {
      const pct = (sizes[i] !== null && sizes[i] !== undefined) ? sizes[i] : _autoRemainder(sizes, i);
      canvas.appendChild(_makeBlock(c, { top:'0', left:`${x}%`, width:`${pct}%`, height:'100%' }));
      x += pct;
    });
  }

  function _drawTable(canvas, comps, tableRows) {
    if (!tableRows || !tableRows.length) return;
    const numRows = tableRows.length;
    const rowH = 100 / numRows;
    tableRows.forEach((row, r) => {
      let x = 0;
      (row.items || []).forEach((c, ci) => {
        const pct = (row.pcts[ci] !== null && row.pcts[ci] !== undefined) ? row.pcts[ci] : _autoRemainder(row.pcts, ci);
        canvas.appendChild(_makeBlock(c, {
          top:`${r * rowH}%`, left:`${x}%`, width:`${pct}%`, height:`${rowH}%`
        }));
        x += pct;
      });
    });
  }

  function _makeBlock(comp, pos) {
    const div = document.createElement('div');
    div.className = `cv-block ${TYPE_CLASS[comp.type] || 'cv-content'}`;
    div.style.cssText = `top:${pos.top};left:${pos.left};width:${pos.width};height:${pos.height};`;
    div.dataset.id = comp.id;

    if (comp.type === 'image' && comp.url) {
       div.style.backgroundImage = `url('${comp.url}')`;
       div.style.backgroundSize = 'cover';
       div.style.backgroundPosition = 'center';
       // Add a semi-transparent overlay for text
       div.innerHTML = `<div style="background:rgba(0,0,0,0.5);color:#fff;width:100%;text-align:center;padding:2px;font-size:10px;">${comp.label}</div>`;
    } else {
       const inner = document.createElement('div');
       inner.style.cssText = 'display:flex;flex-direction:column;align-items:center;gap:4px;';
       inner.innerHTML = `<div class="cv-block-icon">${ICONS[comp.type]||'▪'}</div>
                          <div class="cv-block-lbl">${comp.label}</div>`;
       div.appendChild(inner);
    }
    
    if (comp.type === 'image') {
       div.style.cursor = 'pointer';
       div.onclick = (e) => {
           document.querySelectorAll('.cv-block.cv-image').forEach(el => el.classList.remove('selected-img'));
           div.classList.add('selected-img');
           if (typeof Step2Design !== 'undefined') Step2Design.onSelectImageBlock(comp.id);
       };
    }

    return div;
  }

  function _autoRemainder(sizes, autoIdx) {
    const sum = sizes.reduce((acc, v, i) => (i !== autoIdx && v !== null && v !== undefined ? acc + v : acc), 0);
    return Math.max(5, 100 - sum);
  }

  function setColors(colors) { /* future: apply theme tints */ }

  return { draw, setColors };
})();
