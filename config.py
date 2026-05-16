# -*- coding: utf-8 -*-
"""Configuration settings for NCKH job matching system"""

# USER–JOB MATCHING
TOPK_USER_JOB = 3
W_SKILL = 0.78
W_LOC = 0.22

SIM_THRESHOLD = 0.45
CANDIDATES_TOP = 15
TOPK_SIMILAR = 3

# DRAW
FOCUS_ONLY = True
MAX_SKILLS_DRAW = 10
EDGE_LABEL_MODE = "important"
SHOW_EDGE_SCORES = True
CENTER_MODE = "user"
CENTER_JOB_ID = None
RANDOM_SEED = 42

# CV PDF OCR settings
OCR_LANG = "vie+eng"
OCR_DPI = 300
OCR_MAX_PAGES = 99
FORCE_OCR = True

# Prob skill
MIN_KEEP_PROB = 0.08

# DOMAIN-BASED SKILL LEXICON
DOMAIN_SKILL_LEXICON = {
    "sales_business": {
        "CRM": ["crm", "salesforce", "hubspot", "zoho", "quan ly khach hang"],
        "Negotiation": ["negotiation", "dam phan", "thuong luong"],
        "Customer Service": ["customer service", "cham soc khach hang", "customer success", "ho tro khach hang"],
        "Business Development": ["business development", "phat trien kinh doanh", "bizdev"],
        "Lead Generation": ["lead generation", "tim kiem khach hang", "leads"],
        "Sales Strategy": ["sales strategy", "chien luoc ban hang", "sales plan"],
        "Market Research": ["market research", "nghien cuu thi truong"],
        "Insurance Consulting": ["insurance consulting", "tư vấn bảo hiểm", "insurance advisor", "insurance consultant"],
        "Health Insurance": ["bao hiem y te", "health insurance"],
        "Life Insurance": ["bao hiem nhan tho", "life insurance"],
        "Property Insurance": ["bao hiem nha cua", "bao hiem tai san", "property insurance"],
        "Contract Negotiation": ["hop dong", "ky ket", "contract negotiation"],
    },
    "it_software": {
        "Python":        ["python", "py", "python3", "python 3"],
        "Java":          ["java", "spring", "hibernate"],
        "JavaScript":    ["javascript", "js", "ecmascript"],
        "TypeScript":    ["typescript", "ts"],
        "React":         ["react", "reactjs", "react.js", "nextjs"],
        "NodeJS":        ["nodejs", "node.js", "node", "express"],
        "SQL":           ["sql", "mysql", "postgresql", "postgres", "mssql", "sql server"],
        "NoSQL":         ["nosql", "mongodb", "redis", "firebase"],
        "Docker":        ["docker", "kubernetes", "k8s"],
        "AWS":           ["aws", "azure", "gcp", "cloud"],
        "Git":           ["git", "github", "gitlab"],
        "C++":           ["c++", "cpp"],
        "Go":            ["golang", "go"],
        "PHP":           ["php", "laravel"],
        "Data Science":  ["data science", "machine learning", "ai", "pandas", "numpy"],
        "Big Data":      ["big data", "hadoop", "spark"],
    },
    "accounting_finance": {
        "Excel":         ["excel", "pivot", "vlookup", "power query"],
        "SAP":           ["sap"],
        "MISA":          ["misa"],
        "QuickBooks":    ["quickbooks"],
        "VAT":           ["vat", "gtgt"],
        "Invoice":       ["hoa don", "invoice", "e-invoice", "einvoice", "e invoice"],
        "Tax":           ["thue", "tax"],
        "Audit":         ["kiem toan", "audit"],
        "AR/AP":         ["cong no", "ar", "ap", "accounts payable", "accounts receivable"],
        "Financial Analysis": ["phan tich tai chinh", "financial analysis", "p&l", "budgeting"],
        "Banking":       ["ngan hang", "banking", "credit", "loan"],
        "Investment":    ["dau tu", "investment", "stock", "equity"],
        "Financial Reporting": ["bao cao tai chinh", "financial reporting"],
    },
    "engineering_construction": {
        "AutoCAD":       ["autocad", "cad", "2d design", "3d design"],
        "Project Management": ["project management", "quan ly du an", "pmp"],
        "Manufacturing": ["manufacturing", "san xuat", "production"],
        "Construction":  ["construction", "xay dung", "thi cong"],
        "Mechanical Engineering": ["mechanical", "co khi", "solidworks"],
        "Electrical Engineering": ["electrical", "dien", "plc"],
        "Civil Engineering": ["civil engineering", "ky su xay dung"],
        "Quality Control": ["qc", "qa", "kiem tra chat luong"],
    },
    "hr_admin": {
        "Recruitment":   ["tuyen dung", "recruitment", "talent acquisition"],
        "Payroll":       ["luong", "payroll", "c&b"],
        "Training":      ["dao tao", "training", "l&d"],
        "Office Management": ["hanh chinh", "office management", "admin"],
        "Operations":    ["van hanh", "operations", "supply chain"],
        "Human Resources": ["nhan su", "hr", "hrm"],
        "Policy":        ["chinh sach", "policy", "quy dinh"],
    },
    "marketing_media": {
        "SEO":           ["seo", "search engine optimization"],
        "Content Marketing": ["content marketing", "sang tao noi dung", "copywriting"],
        "Social Media":  ["social media", "facebook ads", "google ads", "tik tok"],
        "Digital Marketing": ["digital marketing", "marketing online"],
        "Email Marketing": ["email marketing", "mailchimp"],
        "Photoshop": ["photoshop", "ps", "adobe photoshop"],
        "Illustrator": ["illustrator", "ai", "adobe illustrator"],
        "InDesign": ["indesign", "id"],
        "Premiere Pro": ["premiere", "pr"],
        "After Effects": ["after effects", "ae"],
        "Figma": ["figma"],
        "UI/UX Design": ["ui/ux", "user interface", "user experience", "giao dien nguoi dung"],
        "Branding": ["branding", "nhan dien thuong hieu", "logo design"],
        "Motion Graphics": ["motion graphics", "do hoa chuyen dong"],
        "Graphic Design": ["thiet ke do hoa", "graphic design"],
        "Photography": ["chup anh", "photography"],
        "Videography": ["quay phim", "videography"],
    },
    "general": {
        "Negotiation": ["negotiation", "dam phan", "thuong luong"],
        "Communication": ["communication", "giao tiep"],
    }
}

# DOMAIN DETECTION KEYWORDS
DOMAIN_KEYWORDS = {
    "sales_business": ["sales", "ban hang", "kinh doanh", "marketing", "thi truong", "bao hiem", "insurance", "customer success", "client relationship", "business development"],
    "accounting_finance": ["ke toan", "accountant", "audit", "tax", "finance", "billing", "bookkeeping"],
    "it_software": ["software", "developer", "engineer", "programming", "coding", "it", "data", "web development"],
    "engineering_construction": ["ky su", "engineer", "manufacturing", "construction", "xay dung", "san xuat", "mechanical", "electrical"],
    "hr_admin": ["hr", "nhan su", "admin", "operations", "van hanh", "hanh chinh", "recruitment"],
    "marketing_media": ["marketing", "content", "media", "truyen thong", "social media", "design", "graphic design", "thiet ke"]
}

# FLATTEN FOR BACKWARD COMPATIBILITY
SKILL_LEXICON = {}
for domain, skills in DOMAIN_SKILL_LEXICON.items():
    SKILL_LEXICON.update(skills)

CORE_SKILLS_CANON = {
    "Excel", "Tax", "VAT", "Invoice", "Financial Reporting", "Audit", "SAP", "MISA", "AR/AP", "Bookkeeping",
    "Python", "Java", "JavaScript", "SQL", "React", "NodeJS", "Project Management", "Data Science", "SEO", "Graphic Design"
}

# LOCATION
VN_CITY_ALIASES = {
    "tp hcm": "Ho Chi Minh City",
    "tphcm": "Ho Chi Minh City",
    "hcm": "Ho Chi Minh City",
    "sai gon": "Ho Chi Minh City",
    "ho chi minh": "Ho Chi Minh City",
    "ha noi": "Ha Noi",
    "hanoi": "Ha Noi",
    "da nang": "Da Nang",
    "danang": "Da Nang",
    "can tho": "Can Tho",
    "hai phong": "Hai Phong",
    "binh duong": "Binh Duong",
    "dong nai": "Dong Nai",
    "vinh": "Vinh",
    "hue": "Hue",
    "nha trang": "Nha Trang",
    "qui nhon": "Qui Nhon",
    "quynhon": "Qui Nhon",
    "da lat": "Da Lat",
    "dalat": "Da Lat",
    "vung tau": "Vung Tau",
    "vungtau": "Vung Tau",
    "buon ma thuot": "Buon Ma Thuot",
    "bmt": "Buon Ma Thuot",
}

DETAIL_CUES = ["quan","q","huyen","phuong","duong","street","ward","district","tp","thi xa","thi tran"]

# ROLE PATTERNS
ROLE_PATTERNS = [
    (r"\bbao hiem\b|\binsurance\b|\btu van tai chinh\b", "Insurance Consultant"),
    (r"\bke toan thue\b|\btax accountant\b", "Tax Accountant"),
    (r"\bke toan tong hop\b|\bgeneral accountant\b", "General Accountant"),
    (r"\bke toan noi bo\b|\binternal accountant\b", "Internal Accountant"),
    (r"\bke toan\b|\baccountant\b", "Accountant"),
    (r"\bkiem toan\b|\baudit\b", "Auditor"),
    (r"\bfinance\b|\bfinancial\b", "Finance"),
    (r"\bhr\b|\bnhan su\b|\btuyen dung\b", "HR"),
    (r"\bsales\b|\bkinh doanh\b|\bban hang\b", "Sales"),
    (r"\bmarketing\b|\bcontent\b", "Marketing"),
    (r"\bthiet ke do hoa\b|\bgraphic designer\b|\bui/ux\b", "Designer"),
    (r"\bdata scientist\b|\bdata analyst\b|\bdata engineer\b", "Data Specialist"),
    (r"\bbackend\b|\bfrontend\b|\bfullstack\b|\bweb developer\b", "Software Engineer"),
    (r"\bdeveloper\b|\bengineer\b|\bsoftware\b|\blap trinh vien\b", "Software Engineer"),
    (r"\bquan ly du an\b|\bproject manager\b", "Project Manager"),
]

# ROLE SIMILARITY
ROLE_SIM = {
    ("Tax Accountant", "General Accountant"): 0.75,
    ("Internal Accountant", "General Accountant"): 0.70,
    ("Accountant", "General Accountant"): 0.65,
    ("Accountant", "Tax Accountant"): 0.60,
    ("Software Engineer", "Data Specialist"): 0.50,
    ("Software Engineer", "Project Manager"): 0.40,
    ("Marketing", "Sales"): 0.45,
    ("Designer", "Marketing"): 0.35,
    ("Finance", "Accountant"): 0.55,
}

# EXPERIENCE SIMILARITY
EXP_NEAR = {
    ("Exp_0_1","Exp_1_3"): 0.6,
    ("Exp_1_3","Exp_3_5"): 0.6,
    ("Exp_3_5","Exp_5_plus"): 0.5,
}

# SECTION HINTS
SECTION_HINTS = {
    "skills":     ["ky nang", "kỹ năng", "skills", "technical skills", "skill set", "core skills"],
    "experience": ["kinh nghiem", "kinh nghiệm", "experience", "work history", "employment"],
    "projects":   ["du an", "dự án", "projects", "project"],
    "education":  ["hoc van", "học vấn", "education"],
    "summary":    ["tom tat", "tóm tắt", "summary", "profile", "about"],
    "certs":      ["chung chi", "chứng chỉ", "certifications", "certificate"],
}

SECTION_WEIGHT = {
    "skills": 0.70,
    "experience": 0.45,
    "projects": 0.35,
    "certs": 0.40,
    "summary": 0.30,
    "education": 0.15,
    "unknown": 0.25,
}

# JOB INFO COLUMN MAPPING
COL = {
    "job_id": "JobID",
    "job_url": "URL_Job",
    "job_title": "Title",
    "company": "Name company",
    "location": "Job Address",
    "location_detail": "Job Address detail",
    "requirements": "Job Requirements",
    "salary": "Salary",
    "experience": "Experience",
    "job_desc": "Job description",
    "job_type": "Job type",
    "benefit": "benefit"
}

# RDF CLASSES
RDF_CLASSES = ["User","JobPosting","JobRoleCanonical","JobRoleRaw","Company","Location","ExperienceBucket","SalaryBucket","Skill","SkillRaw"]

# RDF OBJECT PROPERTIES
RDF_OBJ_PROPS = [
    "HAS_ROLE_CANONICAL","HAS_ROLE_RAW","POSTED_BY","LOCATED_IN",
    "REQUIRES_EXP_BUCKET","HAS_SALARY_BUCKET","REQUIRES_SKILL",
    "HAS_SKILL","MATCHES_JOB","SIMILAR_TO","NORMALIZES_TO","MENTIONS_SKILL_RAW"
]

# EVALUATION SETTINGS
SAMPLE_N = 100
TRIALS = 5
KS = [1, 3, 5, 10]

# Graph visualization helpers (no duplicates)
CENTER_JOB_ID = None
CENTER_MODE = "user"
USER_ID = "user::cv_001"
IMPORTANT_EDGES = ["MATCHES_JOB", "SIMILAR_TO"]
