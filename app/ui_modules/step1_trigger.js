/**
 * step1_trigger.js — Popup hướng dẫn cấu trúc Trigger
 * =====================================================
 * Hiển thị popup khi user nhấn "Hướng dẫn cấu trúc Trigger"
 *
 * Phụ thuộc:
 *   - app_shell.html → popup-overlay#popup-trigger-guide, #popup-trigger-content
 */

const Step1Trigger = (() => {

  const GUIDE_HTML = `
<div style="display:flex; flex-direction:column; gap:14px;">

  <div style="font-size:12px; color:var(--txt-muted); line-height:1.6;">
    File Word cần chứa các <strong style="color:var(--accent);">từ khoá trigger</strong> để app nhận biết điểm bắt đầu mỗi slide và vị trí chart.
  </div>

  <!-- Slide trigger -->
  <div style="background:var(--bg-card); border-radius:8px; padding:14px 16px; border:1px solid var(--border);">
    <div style="font-size:11px; font-weight:700; color:var(--accent); letter-spacing:1px; text-transform:uppercase; margin-bottom:8px;">
      📌 Trigger Slide
    </div>
    <div style="font-family:'JetBrains Mono',monospace; font-size:13px; background:var(--bg); padding:10px 14px; border-radius:6px; color:#e2e8f0; margin-bottom:8px;">
      {Slide 1} Tên tiêu đề slide<br>
      {Slide 2} Tên tiêu đề khác<br>
      {Slide 3} ...
    </div>
    <div style="font-size:11px; color:var(--txt-muted);">
      Dòng bắt đầu bằng <code style="color:var(--accent);">{Slide N}</code> sẽ tạo ra một slide mới.<br>
      Số N phải tăng dần, bắt đầu từ 1.
    </div>
  </div>

  <!-- Ví dụ -->
  <div style="background:var(--bg-card); border-radius:8px; padding:14px 16px; border:1px solid var(--border);">
    <div style="font-size:11px; font-weight:700; color:var(--accent4); letter-spacing:1px; text-transform:uppercase; margin-bottom:8px;">
      📄 Ví dụ đầy đủ
    </div>
    <div style="font-family:'JetBrains Mono',monospace; font-size:12px; background:var(--bg); padding:10px 14px; border-radius:6px; color:#e2e8f0; line-height:1.8;">
      {Slide 1} Tổng quan doanh thu 2024<br><br>
      Doanh thu Q4 đạt 120 tỷ, tăng 15% YoY...<br><br>
      [Bảng Excel dán vào đây]<br><br>
      {Slide 2} Phân tích theo vùng<br><br>
      Miền Nam dẫn đầu với 45%...
    </div>
  </div>

  <!-- Tips -->
  <div style="font-size:11px; color:var(--txt-dim); line-height:1.7;">
    💡 <strong style="color:var(--txt-muted);">Lưu ý:</strong>
    Mỗi bảng dữ liệu nên có hàng tiêu đề rõ ràng.
    Dữ liệu nhạy cảm (tên công ty, số liệu) sẽ được <em>mask</em> trước khi gửi AI — không bao giờ rời khỏi máy bạn.
  </div>
</div>
`;

  function show() {
    document.getElementById('popup-trigger-content').innerHTML = GUIDE_HTML;
    document.getElementById('popup-trigger-guide').classList.add('show');
  }

  function close() {
    document.getElementById('popup-trigger-guide').classList.remove('show');
  }

  return { show, close };
})();
