/**
 * step1_ai_processor.js — Step I Mode 2: Word dài → AI → Trigger structured
 * ===========================================================================
 * File này không render UI trực tiếp.
 * Chỉ expose hàm Step1AI.run() dùng bởi step1_input.js
 *
 * Luồng phía client:
 *   1. Nhận File object từ step1_input.js
 *   2. POST /api/ai-split-docx (form-data)
 *   3. Server xử lý: parse docx → mask → gửi AI → unmask → trả text trigger
 *   4. Trả về { ok, text, slide_count }
 *
 * Phụ thuộc:
 *   - Không phụ thuộc module JS khác
 *   - Python backend: input_ai_splitter.py, input_mask.py
 */

const Step1AI = (() => {

  /**
   * Gửi file Word dài lên server để AI phân tích và phân slide
   * @param {File}   file        - File object .docx
   * @param {object} opts        - { maxSlides, lang }
   * @param {function} onProgress - Callback(message: string) khi có progress
   * @returns {Promise<{ok, text, slide_count, error}>}
   */
  async function run(file, opts = {}, onProgress = () => {}) {
    const { maxSlides = 10, lang = 'vi' } = opts;

    const fd = new FormData();
    fd.append('file', file);
    fd.append('max_slides', maxSlides);
    fd.append('lang', lang);

    onProgress('Đang upload file...');

    // Gọi API (xử lý mask + AI + unmask ở server)
    const res = await fetch('/api/ai-split-docx', { method: 'POST', body: fd });
    if (!res.ok) {
      const err = await res.text();
      return { ok: false, error: err };
    }

    const data = await res.json();
    return data;  // { ok, text, slide_count }
  }

  return { run };
})();
