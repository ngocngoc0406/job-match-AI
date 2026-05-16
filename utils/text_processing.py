# -*- coding: utf-8 -*-
"""Text processing and helper functions"""

import unicodedata
import re
import hashlib
from collections import defaultdict
from config import SKILL_LEXICON, SECTION_HINTS, SECTION_WEIGHT, DETAIL_CUES, VN_CITY_ALIASES, ROLE_PATTERNS, MIN_KEEP_PROB

# TEXT HELPERS
def norm_text(t):
    """Normalize text for comparison, removing accents and handling Vietnamese 'd'"""
    if t is None:
        return ""
    # Handle Vietnamese 'đ' specifically as it doesn't decompose with NFKD
    s = str(t).lower().replace('đ', 'd')
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\s+", " ", s).strip()
    return s

def safe_id(t):
    """Create safe identifier from text"""
    s = norm_text(t)
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s if s else "unknown"

def short_label(text, maxlen=30):
    """Truncate text with ellipsis"""
    s = re.sub(r"\s+", " ", str(text)).strip()
    return s if len(s) <= maxlen else s[:maxlen-1] + "…"

def sid(prefix: str, raw: str, n=8):
    """Create stable identifier with hash"""
    raw = "" if raw is None else str(raw)
    base = norm_text(raw)
    h = hashlib.md5(base.encode("utf-8")).hexdigest()[:n]
    slug = re.sub(r"[^a-z0-9]+", "_", base).strip("_")
    return f"{prefix}_{slug}_{h}"

# LOCATION PARSING
def parse_location_city_detail(text: str):
    """Parse location into city and district/ward from CV header with strict filtering"""
    # 1. Focus on the header (first 1000 chars) to avoid footer noise
    full_text = str(text or "").strip()
    header_text = full_text[:1000]
    if not header_text:
        return "Unknown", ""
    
    # 2. Normalize text
    s = norm_text(header_text).replace(".", " ").replace("-", " ")
    s = re.sub(r"\s+", " ", s).strip()
    
    # 3. Try to find a known city alias (primary detection)
    city = None
    for k, v in VN_CITY_ALIASES.items():
        if re.search(rf"(?<!\w){re.escape(k)}(?!\w)", s):
            city = v
            break

    # 4. Split and filter for district/ward info
    parts = [p.strip() for p in re.split(r"[,;/|]+", s) if p.strip()]
    
    # Common geography filler words
    ignore_words = {"vietnam", "viet nam", "vn", "city", "tp", "phuong", "quan", "huyen"}
    # CV stop words that are NOT locations
    stop_words = {"orders", "experience", "education", "certificates", "summary", "profile", "skills", "projects", "academy"}
    
    # If no city found in aliasing, try to guess from parts ONLY if they contain a geography cue
    if city is None:
        meaningful_parts = [p for p in parts if p not in ignore_words and p not in stop_words and len(p.split()) <= 4]
        if meaningful_parts:
            tail = meaningful_parts[-1]
            tail_lower = tail.lower()
            
            # STALKER CHECK: Only accept as a city if it has a cue (like street/district) 
            # OR if it's already a known alias we somehow missed in the first pass
            has_cue = any(cue in tail_lower for cue in DETAIL_CUES)
            
            city_guess = VN_CITY_ALIASES.get(tail_lower, str(tail).title())
            # If it's a known alias OR it has a cue AND isn't a stop word
            if (tail_lower in VN_CITY_ALIASES or has_cue) and tail_lower not in stop_words:
                if len(city_guess) < 25: 
                    city = city_guess
        
    if city is None:
        city = "Unknown"

    # 5. Extract District/Ward (Details)
    detail_parts = []
    for p in parts:
        p_lower = p.lower()
        # Avoid picking up stop words as details
        if p_lower in stop_words:
            continue
            
        # Only keep if it contains a cue and is not the city name itself
        if any(cue in p_lower for cue in DETAIL_CUES) and p_lower != city.lower():
            detail_parts.append(p.title())
            
    # Keep only the most relevant part (usually the district/ward)
    detail = ", ".join(detail_parts[:2]).strip() 
    
    return city, detail

def location_match_score(user_city, user_detail, job_city, job_detail):
    """Calculate location match score"""
    if user_city == "Unknown" or job_city == "Unknown":
        return 0.0, {"city_match": 0, "detail_match": 0}
    if norm_text(user_city) != norm_text(job_city):
        return 0.0, {"city_match": 0, "detail_match": 0}

    ud = set(norm_text(user_detail).split()) if user_detail else set()
    jd = set(norm_text(job_detail).split()) if job_detail else set()
    if not ud or not jd:
        # Base score for city match only
        return 0.7, {"city_match": 1, "detail_match": 0}

    inter = len(ud & jd)
    union = len(ud | jd)
    jacc = inter / union if union else 0.0
    # Weighted combination: 0.7 base + up to 0.3 from district match
    score = 0.7 + 0.3*jacc
    return float(round(score, 3)), {"city_match": 1, "detail_match": round(jacc,3)}

# ROLE PARSING
def infer_role_canonical(title: str) -> str:
    """Infer canonical role from title using frequency-based keyword matching"""
    t = norm_text(title)
    if not t:
        return "Other"
        
    counts = defaultdict(int)
    for pat, role in ROLE_PATTERNS:
        # findall returns all non-overlapping matches
        matches = re.findall(pat, t)
        counts[role] += len(matches)
    
    if not counts:
        return "Other"
        
    # Get the role with the maximum count. 
    # In case of ties, the order in ROLE_PATTERNS still acts as a priority 
    # because of how we iterate, but frequency is the primary driver.
    best_role = max(counts.items(), key=lambda x: x[1])
    
    # Only return if we actually found matches
    if best_role[1] > 0:
        return best_role[0]
        
    return "Other"

def infer_role_raw(title: str) -> str:
    """Get raw role from title"""
    return str(title).strip() if title else "Unknown"

def role_sim(r1, r2):
    """Calculate role similarity"""
    from config import ROLE_SIM
    if r1 == r2:
        return 1.0
    return ROLE_SIM.get((r1, r2), ROLE_SIM.get((r2, r1), 0.0))

# EXPERIENCE PARSING
def parse_year_range(text):
    """Parse experience year range"""
    t = norm_text(text)
    if not t or t in ["unknown", "nan"]:
        return None, None, "Unknown"

    if re.search(r"duoi\s*1|<\s*1|less\s*than\s*1", t):
        return 0, 1, "Range"

    if any(k in t for k in ["fresher", "intern", "moi ra truong", "0 nam"]):
        return 0, 0, "Fixed"

    nums = [int(x) for x in re.findall(r"\d+", t)]
    if len(nums) >= 2:
        a, b = nums[0], nums[1]
        if a > b: a, b = b, a
        return a, b, "Range"

    if len(nums) == 1:
        return nums[0], nums[0], "Fixed"

    return None, None, "Unknown"

def exp_bucket(miny, maxy):
    """Get experience bucket"""
    if miny is None:
        return "Exp_Unknown"
    if maxy <= 1: return "Exp_0_1"
    if maxy <= 3: return "Exp_1_3"
    if maxy <= 5: return "Exp_3_5"
    return "Exp_5_plus"

def exp_sim(e1, e2):
    """Calculate experience similarity"""
    from config import EXP_NEAR
    if e1 == "Exp_Unknown" or e2 == "Exp_Unknown":
        return 0.0
    if e1 == e2:
        return 1.0
    return EXP_NEAR.get((e1, e2), EXP_NEAR.get((e2, e1), 0.0))

# SALARY PARSING
def parse_salary_vnd(text):
    """Parse salary in VND"""
    t = norm_text(text)
    if not t or t in ["unknown", "nan"]:
        return None, None, "Unknown"
    if any(k in t for k in ["thoả thuận", "thỏa thuận", "thoa thuan", "negotiable"]):
        return None, None, "Negotiable"
    nums = [int(x) for x in re.findall(r"\d+", t)]
    if not nums:
        return None, None, "Unknown"
    if len(nums) >= 2:
        lo, hi = nums[0], nums[1]
        if lo > hi: lo, hi = hi, lo
        if hi < 1000:
            return lo*1_000_000, hi*1_000_000, "Range"
        return lo, hi, "Range"
    v = nums[0]
    if v < 1000:
        v *= 1_000_000
    return v, v, "Fixed"

def salary_bucket(mins, maxs, sal_type):
    """Get salary bucket"""
    if sal_type == "Negotiable":
        return "Salary_Negotiable"
    if mins is None:
        return "Salary_Unknown"
    if maxs <= 10_000_000: return "Salary_0_10M"
    if maxs <= 20_000_000: return "Salary_10_20M"
    if maxs <= 40_000_000: return "Salary_20_40M"
    return "Salary_40M_plus"

def parse_salary(text):
    """Parse salary (VND or USD)"""
    t = norm_text(text)
    if not t:
        return None, None, "UNK", False

    if any(k in t for k in ["thoả thuận","thỏa thuận","thoa thuan","negotiable"]):
        return None, None, "UNK", True

    cur = "USD" if ("$" in t or "usd" in t) else "VND"
    nums = re.findall(r"\d+(?:[.,]\d+)*", t)
    if not nums:
        return None, None, cur, False

    def to_num(x):
        x = x.replace(",", "")
        v = float(x)
        if cur == "VND" and v < 1000:
            v *= 1_000_000
        return int(v)

    vals = [to_num(x) for x in nums[:2]]
    if len(vals) == 1:
        return vals[0], vals[0], cur, False

    lo, hi = sorted(vals)
    return lo, hi, cur, False

def salary_bucket_general(lo, hi, cur, nego):
    """Get general salary bucket"""
    if nego:
        return "Salary_Negotiable"
    if lo is None:
        return "Salary_Unknown"

    if cur == "USD":
        if hi <= 1000: return "Salary_USD_<1k"
        if hi <= 3000: return "Salary_USD_1k_3k"
        return "Salary_USD_3k_plus"

    if hi <= 10_000_000: return "Salary_0_10M"
    if hi <= 20_000_000: return "Salary_10_20M"
    if hi <= 40_000_000: return "Salary_20_40M"
    return "Salary_40M_plus"

# SKILL SECTION PARSING
def split_cv_sections(cv_text: str):
    """Split CV into sections"""
    raw = str(cv_text or "")
    lines = [l.strip() for l in raw.splitlines()]
    sections = defaultdict(list)
    cur = "unknown"

    def is_heading(line_norm: str):
        for sec, keys in SECTION_HINTS.items():
            for k in keys:
                kn = norm_text(k)
                if line_norm == kn or line_norm.startswith(kn + ":"):
                    return sec
        return None

    for line in lines:
        if not line:
            continue
        ln = norm_text(line)
        sec = is_heading(ln)
        if sec:
            cur = sec
            continue
        sections[cur].append(line)

    out = {k: "\n".join(v) for k, v in sections.items() if v}
    if not out:
        out = {"unknown": raw}
    return out

def _combine_probs(ps):
    """Combine probabilities"""
    out = 0.0
    for p in ps:
        out = 1 - (1 - out) * (1 - float(p))
    return float(min(0.999, max(0.0, out)))
