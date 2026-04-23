"""
sanitizer_core.py — Data Privacy Core Functions
==========================================
Core functions for data masking and sanitization.
"""

import re
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

try:
    from .list_store import load_lists
except Exception:
    load_lists = None


# ── Pipeline Debug Logger ────────────────────────────────────────────────────────
_DEBUG_LOG = Path(__file__).parent.parent.parent / "pipeline_debug.log"

def _dlog(section: str, content: str) -> None:
    try:
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"\n{'='*60}\n[{ts}] {section}\n{'='*60}\n{content}\n"
        with open(_DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass

# ── Constants ──────────────────────────────────────────────────────────────────────────

VN_PROVINCES = {
    "An Giang", "Bà Rịa", "Bạc Liêu", "Bắc Giang", "Bắc Kạn", "Bắc Ninh",
    "Bến Tre", "Bình Dương", "Bình Định", "Bình Phước", "Bình Thuận",
    "Cà Mau", "Cần Thơ", "Cao Bằng", "Đà Nẵng", "Đắk Lắk", "Đắk Nông",
    "Điện Biên", "Đồng Nai", "Đồng Tháp", "Gia Lai", "Hà Giang", "Hà Nam",
    "Hà Nội", "Hà Tĩnh", "Hải Dương", "Hải Phòng", "Hậu Giang", "Hòa Bình",
    "Hưng Yên", "Khánh Hòa", "Kiên Giang", "Kon Tum", "Lai Châu", "Lạng Sơn",
    "Lào Cai", "Lâm Đồng", "Long An", "Nam Định", "Nghệ An", "Ninh Bình",
    "Ninh Thuận", "Phú Thọ", "Phú Yên", "Quảng Bình", "Quảng Nam",
    "Quảng Ngãi", "Quảng Ninh", "Quảng Trị", "Sóc Trăng", "Sơn La",
    "Tây Ninh", "Thái Bình", "Thái Nguyên", "Thanh Hóa", "Thừa Thiên Huế",
    "Tiền Giang", "TP.HCM", "TP HCM", "Hồ Chí Minh", "Trà Vinh", "Tuyên Quang",
    "Vĩnh Long", "Vĩnh Phúc", "Yên Bái",
    "Miền Bắc", "Miền Nam", "Miền Trung", "Tây Nguyên", "Đông Nam Bộ",
    "Đồng Bằng Sông Cửu Long", "ĐBSCL", "Đồng Bằng Sông Hồng",
    "Việt Nam", "Vietnam", "Viet Nam",
}

_VN_PROVINCES_SORTED = sorted(VN_PROVINCES, key=lambda x: -len(x))

EN_REGION_KEYWORDS = {
    "North", "South", "East", "West", "Central",
    "Northeast", "Northwest", "Southeast", "Southwest",
    "Asia", "Europe", "Americas", "Africa", "Pacific", "APAC", "EMEA",
}

ORG_SUFFIXES = re.compile(
    r"\b\w[\w\s]*?\s*"
    r"(Co\.?,?\s*Ltd\.?|Limited|LLC|Inc\.?|Corp\.?|Corporation|"
    r"Group|Holdings?|Partners?|Associates?|Enterprises?|Solutions?|"
    r"Technologies?|Consulting|International|Industries|Services|"
    r"Công\s*ty|TNHH|Cổ\s*Phần|JSC|VN|Vietnam|Viet\s*Nam)"
    r"\b",
    re.IGNORECASE,
)

VN_SURNAMES = {
    "Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ",
    "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý", "Đinh", "Đoàn",
}

VN_PERSON_RE = re.compile(
    r"\b(" + "|".join(VN_SURNAMES) + r")\s+[A-ZÁÀẢÃẠĂẮẶẤẦẨẪẬÂĐÊ][a-záàảãạăắặấầẩẫậâđê]+"
    r"(\s+[A-ZÁÀẢÃẠĂẮẶẤẦẨẪẬÂĐÊ][a-záàảãạăắặấầẩẫậâđê]+)*\b"
)

EN_STOP = {
    "The", "This", "That", "These", "Those", "With", "From", "Into", "Over",
    "And", "But", "For", "Not", "Are", "Has", "Was", "Been", "Have",
    "Total", "Grand", "Year", "Month", "Quarter", "Report", "Data",
    "Chart", "Table", "Slide", "Figure", "Revenue", "Profit", "Sales",
    "Market", "Growth", "Share", "Plan", "Target", "Actual",
    "North", "South", "East", "West", "Central",
}

EN_NAME_RE = re.compile(r"\b([A-Z][a-z]{1,})(\s+[A-Z][a-z]{1,}){1,3}\b")
EN_BRAND_RE = re.compile(r"\b([A-Z][a-zA-Z]{3,})\b")

EN_COMMON_WORDS = {
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
    "Jan", "Feb", "Mar", "Apr", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    "Total", "Grand", "Budget", "Actual", "Forecast", "Target", "Variance",
    "Revenue", "Profit", "Sales", "Cost", "Margin", "Growth", "Share",
    "Report", "Summary", "Overview", "Dashboard", "Slide", "Chart",
    "Table", "Figure", "Index", "Ratio", "Rate", "Score", "Count",
    "Plan", "Trend", "Analysis", "Review", "Result", "Output", "Input",
    "Amount", "Value", "Price", "Unit", "Volume", "Quantity", "Number",
    "Average", "Median", "Subtotal", "Percentage", "Percent",
    "New", "Old", "High", "Low", "Good", "Best", "First", "Last",
    "Next", "Previous", "Current", "Annual", "Monthly", "Weekly", "Daily",
    "Full", "Part", "Main", "Primary", "Secondary", "Final", "Draft",
    "Active", "Inactive", "Pending", "Complete", "Open", "Closed",
    "Store", "Branch", "Region", "Zone", "Area", "City", "Country",
    "Team", "Group", "Division", "Department", "Category", "Channel",
    "Product", "Service", "Customer", "Client", "User", "Staff", "Manager",
    "Quarter", "Half", "Year", "Month", "Week", "Day", "Date", "Time",
    "Other", "Various", "Multiple", "Single", "Both",
    "True", "False", "None", "Null", "Empty", "Unknown",
}

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

NEVER_MASK_KEYS = {"type", "chart_hint", "chart_type_hint", "columns", "index", "images"}
MASK_IN_PLACE_KEYS = {"title", "presentation_title", "raw_text"}


class NameMasker:
    """Phát hiện và mask tên (org, region, person) trong text."""

    def __init__(self, whitelist: Optional[List[str]] = None, blacklist: Optional[List[str]] = None):
        self.name_map: dict[str, str] = {}
        self._reverse: dict[str, str] = {}
        self._counters = {"Company": 0, "Region": 0, "Person": 0, "Email": 0}
        self._whitelist = {str(x).strip().lower() for x in (whitelist or []) if str(x).strip()}
        self._blacklist = [str(x).strip() for x in (blacklist or []) if str(x).strip()]
        self._blacklist.sort(key=lambda s: -len(s))

    def _is_whitelisted(self, token: str) -> bool:
        return token.strip().lower() in self._whitelist

    def _next_alpha(self, category: str) -> str:
        n = self._counters[category]
        self._counters[category] += 1
        label = ""
        n += 1
        while n > 0:
            n, r = divmod(n - 1, 26)
            label = chr(65 + r) + label
        return f"{category}-{label}"

    def _next_num(self, category: str) -> str:
        self._counters[category] += 1
        return f"{category}-{self._counters[category]}"

    def _alias_for(self, name: str, category: str) -> str:
        key = name.strip()
        if key in self._reverse:
            return self._reverse[key]
        alias = self._next_num(category) if category == "Region" else self._next_alpha(category)
        self.name_map[alias] = key
        self._reverse[key] = alias
        return alias

    def _classify(self, text: str) -> Optional[str]:
        t = text.strip()
        if not t:
            return None
        if EMAIL_RE.fullmatch(t):
            return "Email"
        if VN_PERSON_RE.fullmatch(t):
            return "Person"
        for prov in _VN_PROVINCES_SORTED:
            if t.lower() == prov.lower():
                return "Region"
        if t in EN_REGION_KEYWORDS:
            return "Region"
        if ORG_SUFFIXES.search(t):
            return "Company"
        m = EN_NAME_RE.fullmatch(t)
        if m:
            words = t.split()
            if not any(w in EN_STOP for w in words) and len(words) >= 2:
                return "Company"
        mb = EN_BRAND_RE.fullmatch(t)
        if mb:
            if (t not in EN_STOP and t not in EN_COMMON_WORDS and t not in EN_REGION_KEYWORDS):
                return "Company"
        return None

    def _replace_vn_regions(self, text: str) -> str:
        result = text
        for prov in _VN_PROVINCES_SORTED:
            if prov in result:
                alias = self._alias_for(prov, "Region")
                result = result.replace(prov, alias)
        return result

    def _apply_blacklist(self, text: str) -> str:
        if not text or not self._blacklist:
            return text
        lowered = text.lower()
        hits = [p for p in self._blacklist if p and p.lower() in lowered and not self._is_whitelisted(p)]
        if not hits:
            return text
        out = text
        for phrase in hits:
            pat = re.compile(re.escape(phrase), re.IGNORECASE)
            def _repl(m: re.Match) -> str:
                return self._alias_for(m.group(0), "Company")
            out = pat.sub(_repl, out)
        return out

    def mask_value(self, value: str) -> str:
        if self._is_whitelisted(value):
            return value

        def replace_email(m):
            email = m.group(0)
            if email not in self._reverse:
                self._counters["Email"] += 1
                alias = f"Email-{self._counters['Email']}"
                self.name_map[alias] = email
                self._reverse[email] = alias
            return self._reverse[email]

        result = EMAIL_RE.sub(replace_email, value)
        result = self._apply_blacklist(result)

        # Chỉ classify toàn chuỗi nếu ngắn (≤ 5 words) — tránh mask cả câu dài
        words = result.split()
        if len(words) <= 5:
            category = self._classify(result)
            if category and category != "Email":
                return self._alias_for(result, category)

        def replace_vn_person(m):
            return self._alias_for(m.group(0), "Person")

        result = VN_PERSON_RE.sub(replace_vn_person, result)
        result = self._replace_vn_regions(result)

        def replace_org(m):
            return self._alias_for(m.group(0).strip(), "Company")

        result = ORG_SUFFIXES.sub(replace_org, result)
        return result

    def mask_tree(self, node: Any, parent_key: str = "") -> Any:
        pk = parent_key.lower()
        if isinstance(node, dict):
            return {k: self.mask_tree(v, parent_key=k) for k, v in node.items()}
        elif isinstance(node, list):
            return [self.mask_tree(item, parent_key=parent_key) for item in node]
        elif isinstance(node, str):
            if pk in NEVER_MASK_KEYS:
                return node
            return self.mask_value(node)
        return node

    def unmask_text(self, text: str) -> str:
        for alias, original in sorted(self.name_map.items(), key=lambda x: -len(x[0])):
            text = text.replace(alias, original)
        return text


# ── Helper Functions ───────────────────────────────────────────────────────────

def _infer_col_types(columns: list, rows: list) -> list:
    types = []
    for ci, col in enumerate(columns):
        sample = None
        if rows and isinstance(rows[0], list) and ci < len(rows[0]):
            sample = rows[0][ci]
        if isinstance(sample, (int, float)):
            v = abs(sample)
            if v >= 1_000_000_000:
                types.append("currency_B")
            elif v >= 1_000_000:
                types.append("currency_M")
            elif v < 1 and v > 0:
                types.append("percentage")
            else:
                types.append("number")
        else:
            types.append("label")
    return types


def build_skeleton_metadata(skeleton: dict) -> dict:
    for slide in skeleton.get("slides", []):
        content = slide.get("content")
        if not isinstance(content, dict):
            continue
        if slide.get("type") in ("table", "table_chart"):
            cols = content.get("columns", [])
            rows = content.get("rows", [])
            content["_meta"] = {
                "n_cols": len(cols),
                "n_rows": len(rows),
                "col_types": _infer_col_types(cols, rows),
            }
    return skeleton


# ── API Functions ───────────────────────────────────────────────────────

_masker: Optional[NameMasker] = None


def get_masker() -> NameMasker:
    global _masker
    if _masker is None:
        _masker = NameMasker()
    return _masker


def sanitize(
    raw_data: dict,
    whitelist: Optional[List[str]] = None,
    blacklist: Optional[List[str]] = None,
) -> tuple:
    """
    Main entry — Name-Preserving Masking. Thread-safe: tạo masker mới mỗi call.
    Nếu whitelist/blacklist được truyền vào (từ Stage 1 pipeline), dùng luôn.
    Nếu không, load từ GitHub/cache như cũ (backward compatible).
    """
    if whitelist is None or blacklist is None:
        # Fallback: load từ GitHub/cache như cũ
        _wl, _bl = [], []
        if load_lists is not None:
            try:
                _wl, _bl = load_lists()
            except Exception:
                pass
        whitelist = whitelist if whitelist is not None else _wl
        blacklist = blacklist if blacklist is not None else _bl

    masker = NameMasker(whitelist=whitelist, blacklist=blacklist)
    skeleton = deepcopy(raw_data)
    skeleton = masker.mask_tree(skeleton)

    # DEBUG: log what was masked
    name_map = masker.name_map
    _dlog(
        "SANITIZE — Kết quả mask",
        f"Whitelist đang dùng ({len(whitelist)}): {whitelist[:20]}\n"
        f"Blacklist đang dùng ({len(blacklist)}): {blacklist[:20]}\n"
        f"Các tên đã được mask ({len(name_map)}):\n"
        + "\n".join(f"  {alias} → '{original}'" for alias, original in name_map.items())
    )

    return skeleton, name_map


def unmask_names(text: str, name_map: dict) -> str:
    for alias, original in sorted(name_map.items(), key=lambda x: -len(x[0])):
        text = text.replace(alias, original)
    return text


def unmask(text: str, mask_map: dict = None, scale_map: dict = None,
           slide_index: int = None) -> str:
    return unmask_names(text, mask_map or {})


def unmask_data(data: Any, mask_map: dict = None, scale_map: dict = None,
              slide_index: int = None) -> Any:
    effective_map = mask_map or {}
    if isinstance(data, dict):
        return {k: unmask_data(v, effective_map) for k, v in data.items()}
    elif isinstance(data, list):
        return [unmask_data(item, effective_map) for item in data]
    elif isinstance(data, str):
        return unmask_names(data, effective_map)
    return data