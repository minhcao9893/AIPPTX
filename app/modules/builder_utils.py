from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

def _hex(h: str) -> RGBColor:
    h = h.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

def _align_map(s: str) -> PP_ALIGN:
    return {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT}.get(
        str(s).lower(), PP_ALIGN.LEFT
    )

def _fmt(value) -> str:
    if isinstance(value, bool):
        return str(value)
    try:
        v = float(value)
        if abs(v) >= 1_000_000_000: return f"{v/1_000_000_000:.1f}B"
        if abs(v) >= 1_000_000:     return f"{v/1_000_000:.1f}M"
        if 0 < abs(v) < 1:          return f"{v:.1%}"
        if abs(v) >= 1_000:         return f"{v:,.0f}"
        return f"{v:g}"
    except (TypeError, ValueError):
        return str(value)

def _unmask_fmt(text: str, mask_map: dict) -> str:
    result = str(text)
    for token, original in mask_map.items():
        if token in result:
            result = result.replace(token, _fmt(original))
    return result

def _solid_fill(shape, rgb: RGBColor):
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb

def _solid_fill_alpha(shape, rgb: RGBColor, alpha_pct: int = 0):
    """
    Fill solid + set alpha transparency.
    alpha_pct: 0=đặc hoàn toàn, 100=trong suốt hoàn toàn.
    """
    from lxml import etree
    from pptx.oxml.ns import qn
    
    # 1. Ép fill đặc
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb
    
    # 2. Tính toán alpha (0 -> 100000)
    # alpha_pct = 20 (20% transparent) -> opacity = 80% -> val = 80000
    alpha_val = int((100 - alpha_pct) * 1000)
    if alpha_val < 0: alpha_val = 0
    if alpha_val > 100000: alpha_val = 100000

    try:
        spPr = shape._element.spPr
        solidFill = spPr.find(qn('a:solidFill'))
        if solidFill is None:
            return
        
        # Tìm hoặc tạo color element (ưu tiên srgbClr)
        clr_el = solidFill.find(qn('a:srgbClr'))
        if clr_el is None:
            clr_el = solidFill.find(qn('a:schemeClr'))
        if clr_el is None:
            clr_el = solidFill.find(qn('a:sysClr'))
        
        if clr_el is None:
            clr_el = etree.SubElement(solidFill, qn('a:srgbClr'))
            clr_el.set('val', f"{rgb.r:02x}{rgb.g:02x}{rgb.b:02x}")

        # Xóa các thuộc tính alpha cũ
        for tag in [qn('a:alpha'), qn('a:alphaMod'), qn('a:alphaOff')]:
            for old in clr_el.findall(tag):
                clr_el.remove(old)
        
        # Chèn alphaMod (phương pháp này thường ổn định hơn trên nhiều bản Office)
        # val=80000 nghĩa là 80% opacity
        alpha_el = etree.SubElement(clr_el, qn('a:alphaMod'))
        alpha_el.set('val', str(alpha_val))
        
        # Đảm bảo shape không bị "ám" bởi style của slide master
        # (Xóa các hiệu ứng shadow/glow có thể gây nhiễu)
        effectLst = spPr.find(qn('a:effectLst'))
        if effectLst is not None:
            spPr.remove(effectLst)
            
    except Exception:
        pass

def _to_float(val) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0

def _get_layout(prs, preferred_index: int = 6):
    layouts = prs.slide_layouts
    idx = min(preferred_index, len(layouts) - 1)
    return layouts[idx]

def _remove_all_slides(prs):
    from pptx.oxml.ns import qn
    xml_slides = prs.slides._sldIdLst
    slides_info = []
    for sldId in list(xml_slides):
        rId = sldId.get(
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        )
        if rId is None:
            rId = sldId.get("r:id")
        slides_info.append((rId, sldId))

    for rId, sldId in slides_info:
        xml_slides.remove(sldId)
        if rId:
            try:
                prs.part.drop_rel(rId)
            except Exception:
                pass

    for leftover in list(xml_slides):
        xml_slides.remove(leftover)
