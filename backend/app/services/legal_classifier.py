"""
Lightweight Deterministic Legal Subject & Citation Classifier
India Legal News Aggregator - Free-Tier Architecture (< 50 MB RAM)

Categorizes Indian legal judgments and articles into standardized domains
and extracts court metadata, case citations, statutory sections, and parties
without loading heavy PyTorch or transformer models.
"""

import re
from dataclasses import dataclass, field
from typing import Any, ClassVar

# Standardized 10 Indian legal categories defined in Master Execution Plan
CANONICAL_CATEGORIES = [
    "Constitutional",
    "Criminal",
    "Civil",
    "Corporate",
    "Administrative",
    "Human Rights",
    "Environment",
    "Labour",
    "Family",
    "Education",
]

# Additional domain categories mapped smoothly to canonical or exposed directly
EXTENDED_CATEGORIES = {
    "Tax": "Corporate",
    "Intellectual Property": "Civil",
}


@dataclass
class CourtInfo:
    """Metadata describing the originating judicial body."""
    court_code: str
    court_name: str
    court_level: int  # 1 = Supreme Court, 2 = High Court, 3 = Tribunal


@dataclass
class ClassificationResult:
    """Structured extraction and classification outcome."""
    subject_category: str
    confidence: float
    statute_tags: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    parties: list[dict[str, str]] = field(default_factory=list)
    court: CourtInfo | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject_category": self.subject_category,
            "confidence": round(self.confidence, 4),
            "statute_tags": self.statute_tags,
            "citations": self.citations,
            "parties": self.parties,
            "court": {
                "court_code": self.court.court_code,
                "court_name": self.court.court_name,
                "court_level": self.court.court_level,
            } if self.court else None,
        }


class LegalClassifier:
    """
    High-speed, memory-efficient (< 10 MB RAM) rule and regex-based classifier
    tailored for Indian jurisprudence, statutes, courts, and case citations.
    """

    # --------------------------------------------------------------------------
    # 1. Statutory Patterns & Normalization
    # --------------------------------------------------------------------------
    STATUTE_PATTERNS: ClassVar[list[tuple[str, str]]] = [
        # Constitutional Articles
        (
            r"\b(?:Article|Art\.?)\s*(\d+[A-Z]?(?:\s*\([0-9a-zA-Z]+\))*)\s*(?:of\s+(?:the\s+)?Constitution(?:\s+of\s+India)?)?\b",
            "Article {0}",
        ),
        # CrPC Sections
        (
            r"\b(?:Section|Sec\.?)\s*(\d+[A-Z]?(?:\s*\([0-9a-zA-Z]+\))*)\s*(?:of\s+)?(?:the\s+)?(?:Cr\.?P\.?C\.?|Code\s+of\s+Criminal\s+Procedure)\b",
            "Section {0} CrPC",
        ),
        # IPC Sections
        (
            r"\b(?:Section|Sec\.?)\s*(\d+[A-Z]?(?:\s*\([0-9a-zA-Z]+\))*)\s*(?:of\s+)?(?:the\s+)?(?:I\.?P\.?C\.?|Indian\s+Penal\s+Code)\b",
            "Section {0} IPC",
        ),
        # Bharatiya Nyaya Sanhita (BNS) 2023 Sections
        (
            r"\b(?:Section|Sec\.?)\s*(\d+[A-Z]?(?:\s*\([0-9a-zA-Z]+\))*)\s*(?:of\s+)?(?:the\s+)?(?:BNS|Bharatiya\s+Nyaya\s+Sanhita)\b",
            "Section {0} BNS",
        ),
        # Bharatiya Nagarik Suraksha Sanhita (BNSS) 2023 Sections
        (
            r"\b(?:Section|Sec\.?)\s*(\d+[A-Z]?(?:\s*\([0-9a-zA-Z]+\))*)\s*(?:of\s+)?(?:the\s+)?(?:BNSS|Bharatiya\s+Nagarik\s+Suraksha\s+Sanhita)\b",
            "Section {0} BNSS",
        ),
        # Bharatiya Sakshya Adhiniyam (BSA) 2023 Sections
        (
            r"\b(?:Section|Sec\.?)\s*(\d+[A-Z]?(?:\s*\([0-9a-zA-Z]+\))*)\s*(?:of\s+)?(?:the\s+)?(?:BSA|Bharatiya\s+Sakshya\s+Adhiniyam)\b",
            "Section {0} BSA",
        ),
        # Indian Evidence Act Sections
        (
            r"\b(?:Section|Sec\.?)\s*(\d+[A-Z]?(?:\s*\([0-9a-zA-Z]+\))*)\s*(?:of\s+)?(?:the\s+)?(?:Indian\s+Evidence\s+Act|IEA)\b",
            "Section {0} Evidence Act",
        ),
        # Negotiable Instruments Act (Cheque Bounce)
        (
            r"\b(?:Section|Sec\.?)\s*(\d+[A-Z]?)\s*(?:of\s+)?(?:the\s+)?(?:N\.?I\.?\s*Act|Negotiable\s+Instruments\s+Act)\b",
            "Section {0} NI Act",
        ),
        # Insolvency and Bankruptcy Code (IBC)
        (
            r"\b(?:Section|Sec\.?)\s*(\d+[A-Z]?(?:\s*\([0-9a-zA-Z]+\))*)\s*(?:of\s+)?(?:the\s+)?(?:I\.?B\.?C\.?|Insolvency\s+(?:and\s+)?Bankruptcy\s+Code)\b",
            "Section {0} IBC",
        ),
        # Civil Procedure Code (CPC) Orders and Rules
        (
            r"\bOrder\s*([0-9IVXLCDM]+)\s*Rule\s*([0-9A-Z]+)\s*(?:of\s+)?(?:the\s+)?C\.?P\.?C\.?\b",
            "Order {0} Rule {1} CPC",
        ),
        (
            r"\b(?:Section|Sec\.?)\s*(\d+[A-Z]?)\s*(?:of\s+)?(?:the\s+)?(?:C\.?P\.?C\.?|Code\s+of\s+Civil\s+Procedure)\b",
            "Section {0} CPC",
        ),
        # Companies Act
        (
            r"\b(?:Section|Sec\.?)\s*(\d+[A-Z]?)\s*(?:of\s+)?(?:the\s+)?(?:Companies\s+Act(?:\s*,\s*\d{4})?)\b",
            "Section {0} Companies Act",
        ),
        # Prevention of Money Laundering Act (PMLA)
        (
            r"\b(?:Section|Sec\.?)\s*(\d+[A-Z]?)\s*(?:of\s+)?(?:the\s+)?P\.?M\.?L\.?A\.?\b",
            "Section {0} PMLA",
        ),
        # Unlawful Activities (Prevention) Act (UAPA)
        (
            r"\b(?:Section|Sec\.?)\s*(\d+[A-Z]?(?:\s*\([0-9a-zA-Z]+\))*)\s*(?:of\s+)?(?:the\s+)?U\.?A\.?P\.?A\.?\b",
            "Section {0} UAPA",
        ),
        # POCSO Act
        (
            r"\b(?:Section|Sec\.?)\s*(\d+[A-Z]?)\s*(?:of\s+)?(?:the\s+)?POCSO(?:\s+Act)?\b",
            "Section {0} POCSO Act",
        ),
        # NDPS Act
        (
            r"\b(?:Section|Sec\.?)\s*(\d+[A-Z]?)\s*(?:of\s+)?(?:the\s+)?NDPS(?:\s+Act)?\b",
            "Section {0} NDPS Act",
        ),
        # Income Tax Act / GST Act
        (
            r"\b(?:Section|Sec\.?)\s*(\d+[A-Z]?)\s*(?:of\s+)?(?:the\s+)?(?:Income\s+Tax\s+Act|IT\s+Act)\b",
            "Section {0} Income Tax Act",
        ),
        (
            r"\b(?:Section|Sec\.?)\s*(\d+[A-Z]?)\s*(?:of\s+)?(?:the\s+)?(?:C?GST\s+Act|Goods\s+and\s+Services\s+Tax\s+Act)\b",
            "Section {0} GST Act",
        ),
        # Hindu Marriage Act / Domestic Violence Act
        (
            r"\b(?:Section|Sec\.?)\s*(\d+[A-Z]?(?:\s*\([0-9a-zA-Z]+\))*)\s*(?:of\s+)?(?:the\s+)?(?:Hindu\s+Marriage\s+Act|HMA)\b",
            "Section {0} Hindu Marriage Act",
        ),
        (
            r"\b(?:Section|Sec\.?)\s*(\d+[A-Z]?)\s*(?:of\s+)?(?:the\s+)?(?:Domestic\s+Violence\s+Act|DV\s+Act)\b",
            "Section {0} DV Act",
        ),
        # Environment Protection Act / NGT Act
        (
            r"\b(?:Section|Sec\.?)\s*(\d+[A-Z]?)\s*(?:of\s+)?(?:the\s+)?(?:Environment\s+Protection\s+Act|NGT\s+Act)\b",
            "Section {0} Environment Act",
        ),
        # Trade Marks / Copyright / Patents
        (
            r"\b(?:Section|Sec\.?)\s*(\d+[A-Z]?)\s*(?:of\s+)?(?:the\s+)?(?:Trade\s*Marks\s+Act|Copyright\s+Act|Patents\s+Act)\b",
            "Section {0} IP Act",
        ),
    ]

    # Pre-compiled general statute recognizers
    STATUTE_STANDALONE: ClassVar[list[re.Pattern[str]]] = [
        re.compile(r"\bArticle\s+(?:14|19(?:\([0-9a-z]+\))*|21|22|32|136|142|226|227|300A)\b", re.IGNORECASE),
        re.compile(r"\bSection\s+438\s+(?:Cr\.?P\.?C\.?|BNSS)\b", re.IGNORECASE),
        re.compile(r"\bSection\s+482\s+(?:Cr\.?P\.?C\.?|BNSS)\b", re.IGNORECASE),
        re.compile(r"\bSection\s+138\s+(?:N\.?I\.?\s*Act|Negotiable\s+Instruments)\b", re.IGNORECASE),
        re.compile(r"\bSection\s+(?:7|9|10|31|53)\s+(?:IBC|Insolvency)\b", re.IGNORECASE),
        re.compile(r"\bSection\s+302\s+(?:IPC|BNS)\b", re.IGNORECASE),
        re.compile(r"\bSection\s+420\s+(?:IPC|BNS)\b", re.IGNORECASE),
        re.compile(r"\bSection\s+125\s+(?:Cr\.?P\.?C\.?|BNSS)\b", re.IGNORECASE),
    ]

    # --------------------------------------------------------------------------
    # 2. Case Citation Regex Patterns
    # --------------------------------------------------------------------------
    CITATION_PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        # Supreme Court Neutral Citation (e.g. 2024 INSC 123)
        re.compile(r"\b\d{4}\s+INSC\s+\d+\b", re.IGNORECASE),
        # High Court Neutral Citations (e.g. 2024 DHC 456, 2023 BHC-OS 12)
        re.compile(r"\b\d{4}\s+(?:DHC|BHC|MHC|CALHC|ALLHC|KHC|GHC|KERHC)\s*[-A-Za-z0-9]*\s*\d+\b", re.IGNORECASE),
        # Supreme Court Cases (SCC, SCR)
        re.compile(r"\(\d{4}\)\s+\d+\s+SCC\s+\d+", re.IGNORECASE),
        re.compile(r"\(\d{4}\)\s+\d+\s+SCR\s+\d+", re.IGNORECASE),
        # All India Reporter (AIR)
        re.compile(r"\bAIR\s+\d{4}\s+(?:SC|Del|Bom|Mad|Cal|All|Kar|Guj|Ker)\s+\d+\b", re.IGNORECASE),
        # SCC OnLine Citations
        re.compile(r"\b\d{4}\s+SCC\s+OnLine\s+[A-Za-z\s]+\d+\b", re.IGNORECASE),
        # Criminal Law Journal (Cri LJ)
        re.compile(r"\b\d{4}\s+Cri\s*L\.?J\.?\s+\d+\b", re.IGNORECASE),
        # Writ Petitions / Criminal Appeals / SLPs
        re.compile(r"\b(?:W\.?P\.?|Writ\s+Petition)\s*(?:\([A-Za-z]+\))?\s*(?:No\.?)?\s*\d+\s*(?:of|/)\s*\d{4}\b", re.IGNORECASE),
        re.compile(r"\b(?:Criminal|Civil)\s+Appeal\s*(?:No\.?)?\s*\d+\s*(?:of|/)\s*\d{4}\b", re.IGNORECASE),
        re.compile(r"\b(?:S\.?L\.?P\.?|Special\s+Leave\s+Petition)\s*(?:\([A-Za-z]+\))?\s*(?:No\.?)?\s*\d+\s*(?:of|/)\s*\d{4}\b", re.IGNORECASE),
        re.compile(r"\b(?:Company\s+Appeal|Comp\.?\s*App\.?)\s*(?:\([A-Za-z]+\))?\s*(?:No\.?)?\s*\d+\s*(?:of|/)\s*\d{4}\b", re.IGNORECASE),
    ]

    # --------------------------------------------------------------------------
    # 3. Court Heuristics & Mappings
    # --------------------------------------------------------------------------
    COURT_MAPPINGS: ClassVar[list[tuple[re.Pattern[str], CourtInfo]]] = [
        # Supreme Court
        (re.compile(r"\b(?:Supreme\s+Court(?:\s+of\s+India)?|Apex\s+Court|SCI|SC\b|INSC)\b", re.IGNORECASE),
         CourtInfo(court_code="sc", court_name="Supreme Court of India", court_level=1)),

        # High Courts
        (re.compile(r"\b(?:Delhi\s+High\s+Court|High\s+Court\s+of\s+Delhi|DHC)\b", re.IGNORECASE),
         CourtInfo(court_code="delhi-hc", court_name="High Court of Delhi", court_level=2)),
        (re.compile(r"\b(?:Bombay\s+High\s+Court|High\s+Court\s+of\s+Bombay|BHC)\b", re.IGNORECASE),
         CourtInfo(court_code="bombay-hc", court_name="High Court of Bombay", court_level=2)),
        (re.compile(r"\b(?:Madras\s+High\s+Court|High\s+Court\s+of\s+Madras|MHC)\b", re.IGNORECASE),
         CourtInfo(court_code="madras-hc", court_name="High Court of Judicature at Madras", court_level=2)),
        (re.compile(r"\b(?:Calcutta\s+High\s+Court|High\s+Court\s+at\s+Calcutta)\b", re.IGNORECASE),
         CourtInfo(court_code="calcutta-hc", court_name="High Court at Calcutta", court_level=2)),
        (re.compile(r"\b(?:Allahabad\s+High\s+Court|High\s+Court\s+of\s+Judicature\s+at\s+Allahabad)\b", re.IGNORECASE),
         CourtInfo(court_code="allahabad-hc", court_name="High Court of Judicature at Allahabad", court_level=2)),
        (re.compile(r"\b(?:Karnataka\s+High\s+Court|High\s+Court\s+of\s+Karnataka)\b", re.IGNORECASE),
         CourtInfo(court_code="karnataka-hc", court_name="High Court of Karnataka", court_level=2)),
        (re.compile(r"\b(?:Gujarat\s+High\s+Court|High\s+Court\s+of\s+Gujarat)\b", re.IGNORECASE),
         CourtInfo(court_code="gujarat-hc", court_name="High Court of Gujarat", court_level=2)),
        (re.compile(r"\b(?:Kerala\s+High\s+Court|High\s+Court\s+of\s+Kerala)\b", re.IGNORECASE),
         CourtInfo(court_code="kerala-hc", court_name="High Court of Kerala", court_level=2)),
        (re.compile(r"\b(?:Punjab\s+(?:and|&)\s+Haryana\s+High\s+Court)\b", re.IGNORECASE),
         CourtInfo(court_code="punjab-haryana-hc", court_name="High Court of Punjab and Haryana", court_level=2)),
        (re.compile(r"\b(?:Telangana\s+High\s+Court|High\s+Court\s+for\s+the\s+State\s+of\s+Telangana)\b", re.IGNORECASE),
         CourtInfo(court_code="telangana-hc", court_name="High Court for the State of Telangana", court_level=2)),
        (re.compile(r"\b(?:Patna\s+High\s+Court|High\s+Court\s+of\s+Judicature\s+at\s+Patna)\b", re.IGNORECASE),
         CourtInfo(court_code="patna-hc", court_name="High Court of Judicature at Patna", court_level=2)),
        (re.compile(r"\b(?:Rajasthan\s+High\s+Court|High\s+Court\s+of\s+Rajasthan)\b", re.IGNORECASE),
         CourtInfo(court_code="rajasthan-hc", court_name="High Court of Rajasthan", court_level=2)),

        # Tribunals (Level 3)
        (re.compile(r"\b(?:NCLAT|National\s+Company\s+Law\s+Appellate\s+Tribunal)\b", re.IGNORECASE),
         CourtInfo(court_code="nclat", court_name="National Company Law Appellate Tribunal", court_level=3)),
        (re.compile(r"\b(?:NCLT|National\s+Company\s+Law\s+Tribunal)\b", re.IGNORECASE),
         CourtInfo(court_code="nclt", court_name="National Company Law Tribunal", court_level=3)),
        (re.compile(r"\b(?:NGT|National\s+Green\s+Tribunal)\b", re.IGNORECASE),
         CourtInfo(court_code="ngt", court_name="National Green Tribunal", court_level=3)),
        (re.compile(r"\b(?:ITAT|Income\s+Tax\s+Appellate\s+Tribunal)\b", re.IGNORECASE),
         CourtInfo(court_code="itat", court_name="Income Tax Appellate Tribunal", court_level=3)),
        (re.compile(r"\b(?:CAT|Central\s+Administrative\s+Tribunal)\b", re.IGNORECASE),
         CourtInfo(court_code="cat", court_name="Central Administrative Tribunal", court_level=3)),
        (re.compile(r"\b(?:CCI|Competition\s+Commission\s+of\s+India)\b", re.IGNORECASE),
         CourtInfo(court_code="cci", court_name="Competition Commission of India", court_level=3)),
        (re.compile(r"\b(?:NCDRC|National\s+Consumer\s+Disputes\s+Redressal\s+Commission)\b", re.IGNORECASE),
         CourtInfo(court_code="ncdrc", court_name="National Consumer Disputes Redressal Commission", court_level=3)),
    ]

    # --------------------------------------------------------------------------
    # 4. Domain Keywords & Weighted Categories
    # --------------------------------------------------------------------------
    CATEGORY_KEYWORDS: ClassVar[dict[str, dict[str, float]]] = {
        "Constitutional": {
            "constitution": 3.0,
            "constitutional": 3.0,
            "article 21": 4.0,
            "article 32": 4.0,
            "article 226": 4.0,
            "article 14": 4.0,
            "article 19": 4.0,
            "fundamental rights": 3.5,
            "basic structure": 4.0,
            "writ petition": 2.5,
            "habeas corpus": 3.5,
            "mandamus": 3.0,
            "certiorari": 3.0,
            "quo warranto": 3.0,
            "constitution bench": 4.0,
            "governor": 2.0,
            "presidential": 2.0,
            "federalism": 3.0,
            "judicial review": 3.5,
            "ultra vires": 2.5,
            "doctrine of severability": 3.5,
            "preamble": 3.0,
            "legislative competence": 3.5,
        },
        "Criminal": {
            "bail": 3.5,
            "anticipatory bail": 4.5,
            "crpc": 3.5,
            "bnss": 4.0,
            "ipc": 3.5,
            "bns": 4.0,
            "fir": 3.0,
            "quash": 3.0,
            "quashing of fir": 4.0,
            "murder": 3.0,
            "culpable homicide": 3.5,
            "section 438": 4.5,
            "section 482": 4.5,
            "section 302": 4.5,
            "section 420": 3.5,
            "section 103": 3.5,
            "pocso": 4.0,
            "ndps": 4.0,
            "pmla": 3.5,
            "uapa": 4.0,
            "cognizance": 2.5,
            "police custody": 3.0,
            "judicial custody": 3.0,
            "chargesheet": 3.0,
            "conviction": 2.5,
            "acquittal": 2.5,
            "accused": 2.0,
            "prosecution": 2.0,
            "offence": 2.0,
            "criminal appeal": 3.0,
        },
        "Civil": {
            "cpc": 3.5,
            "code of civil procedure": 3.5,
            "order vii rule 11": 4.5,
            "suit for declaration": 3.5,
            "permanent injunction": 3.5,
            "specific performance": 4.0,
            "specific relief act": 3.5,
            "partition suit": 3.5,
            "damages": 2.0,
            "breach of contract": 3.0,
            "property dispute": 3.0,
            "possession of property": 3.0,
            "title suit": 3.5,
            "execution petition": 3.5,
            "limitation act": 3.0,
            "arbitration": 3.0,
            "arbitral award": 3.5,
            "section 9 cpc": 3.5,
            "civil revision": 3.0,
        },
        "Corporate": {
            "insolvency": 4.0,
            "bankruptcy": 4.0,
            "ibc": 4.5,
            "section 7 ibc": 4.5,
            "section 9 ibc": 4.5,
            "nclt": 4.0,
            "nclat": 4.0,
            "cirp": 4.0,
            "corporate debtor": 4.0,
            "moratorium": 3.5,
            "committee of creditors": 4.0,
            "resolution professional": 4.0,
            "liquidation": 3.0,
            "companies act": 3.5,
            "board of directors": 2.5,
            "shareholder": 2.5,
            "sebi": 4.0,
            "insider trading": 4.0,
            "competition commission": 3.5,
            "merger": 2.5,
            "amalgamation": 2.5,
            "ni act": 3.0,
            "section 138": 3.5,
            "cheque bounce": 3.5,
            "taxation": 3.0,
            "income tax": 3.5,
            "gst": 3.5,
        },
        "Administrative": {
            "service law": 4.0,
            "central administrative tribunal": 4.0,
            "disciplinary proceedings": 3.5,
            "termination of service": 3.5,
            "pension": 3.0,
            "public employment": 3.0,
            "recruitment process": 3.0,
            "promotion": 2.5,
            "seniority": 2.5,
            "tender": 3.5,
            "public procurement": 3.5,
            "government contract": 3.0,
            "natural justice": 3.0,
            "audi alteram partem": 3.5,
            "administrative tribunal": 3.5,
        },
        "Human Rights": {
            "human rights": 4.0,
            "custodial death": 4.5,
            "custodial torture": 4.5,
            "illegal detention": 4.5,
            "fake encounter": 4.0,
            "nhrc": 4.0,
            "right to privacy": 3.5,
            "right to health": 3.0,
            "right to shelter": 3.0,
            "child labour": 3.5,
            "prisoner rights": 3.5,
            "transgender rights": 3.5,
            "untouchability": 3.5,
            "discrimination": 2.5,
        },
        "Environment": {
            "national green tribunal": 4.5,
            "ngt": 4.0,
            "environment protection act": 4.5,
            "pollution": 3.5,
            "air pollution": 4.0,
            "water pollution": 4.0,
            "forest conservation": 4.0,
            "wildlife protection": 4.0,
            "coastal regulation zone": 4.0,
            "crz": 3.5,
            "environmental clearance": 4.0,
            "eia": 3.5,
            "stubble burning": 4.0,
            "deforestation": 3.5,
            "solid waste management": 3.5,
            "polluter pays principle": 4.0,
        },
        "Labour": {
            "industrial disputes act": 4.5,
            "trade union": 4.0,
            "workman": 3.5,
            "workmen": 3.5,
            "gratuity": 4.0,
            "provident fund": 3.5,
            "epfo": 3.5,
            "minimum wages": 4.0,
            "retrenchment": 4.0,
            "unfair labour practice": 4.0,
            "labour court": 4.0,
            "reinstatement with back wages": 4.5,
            "factory act": 3.5,
            "contract labour": 3.5,
        },
        "Family": {
            "hindu marriage act": 4.5,
            "divorce": 4.0,
            "custody of child": 4.5,
            "child custody": 4.5,
            "maintenance": 3.5,
            "alimony": 4.0,
            "restitution of conjugal rights": 4.5,
            "domestic violence": 4.0,
            "dv act": 4.0,
            "guardians and wards act": 4.0,
            "special marriage act": 4.0,
            "matrimonial dispute": 3.5,
            "streedhan": 4.0,
            "section 125": 4.0,
            "irretrievable breakdown of marriage": 4.5,
        },
        "Education": {
            "neet": 4.5,
            "university grant commission": 4.0,
            "ugc": 3.5,
            "aicte": 3.5,
            "right to education": 4.5,
            "rte act": 4.5,
            "college admission": 3.5,
            "reservation in education": 3.5,
            "examination": 2.5,
            "medical admissions": 4.0,
            "university statute": 3.5,
            "school fee": 3.5,
            "capitation fee": 4.0,
            "cancellation of exam": 4.0,
        },
    }

    # --------------------------------------------------------------------------
    # 5. Core Classification & Extraction Methods
    # --------------------------------------------------------------------------
    @classmethod
    def extract_statutes(cls, text: str) -> list[str]:
        """
        Extracts and normalizes Indian statutory sections, articles, and orders.
        Guarantees deduplication while preserving discovery order.
        """
        if not text:
            return []

        statutes: list[str] = []
        seen: set[str] = set()

        # Check parameterized patterns
        for pattern_str, format_template in cls.STATUTE_PATTERNS:
            matches = re.finditer(pattern_str, text, re.IGNORECASE)
            for m in matches:
                groups = [g.strip() for g in m.groups() if g]
                if not groups:
                    continue
                # Normalize formatting
                try:
                    formatted = format_template.format(*groups)
                except (IndexError, KeyError):
                    formatted = groups[0]

                # Clean internal whitespace
                formatted = re.sub(r"\s+", " ", formatted).strip()
                if formatted.lower() not in seen:
                    seen.add(formatted.lower())
                    statutes.append(formatted)

        # Check standalone curated high-impact statutes
        for regex in cls.STATUTE_STANDALONE:
            matches = regex.finditer(text)
            for m in matches:
                matched_str = re.sub(r"\s+", " ", m.group(0)).strip()
                if matched_str.lower() not in seen:
                    seen.add(matched_str.lower())
                    statutes.append(matched_str)

        return statutes

    @classmethod
    def extract_citations(cls, text: str) -> list[str]:
        """
        Extracts case citations including Neutral Citations, SCC, AIR, and Appeal numbers.
        """
        if not text:
            return []

        citations: list[str] = []
        seen: set[str] = set()

        for pattern in cls.CITATION_PATTERNS:
            matches = pattern.finditer(text)
            for m in matches:
                cite = re.sub(r"\s+", " ", m.group(0)).strip()
                if cite.lower() not in seen:
                    seen.add(cite.lower())
                    citations.append(cite)

        return citations

    @classmethod
    def extract_court(cls, text: str, default_court: CourtInfo | None = None) -> CourtInfo:
        """
        Detects Indian court or tribunal from title and text.
        Falls back to default_court or generic Supreme Court.
        """
        if text:
            for pattern, court_info in cls.COURT_MAPPINGS:
                if pattern.search(text):
                    return court_info

        if default_court:
            return default_court

        return CourtInfo(
            court_code="sc",
            court_name="Supreme Court of India",
            court_level=1,
        )

    @classmethod
    def extract_parties(cls, text: str) -> list[dict[str, str]]:
        """
        Extracts opposing parties from legal title or text (e.g. 'Petitioner v. Respondent').
        """
        if not text:
            return []

        # Common party vs opponent patterns
        party_regex = re.compile(
            r"(?P<petitioner>[A-Z][A-Za-z0-9\s\.\,\&\'\-]+?)\s+(?:v\.|vs\.?|versus|V/S)\s+(?P<respondent>[A-Z][A-Za-z0-9\s\.\,\&\'\-]+?)(?:\s*(?:\||\-|\—|\;|\n|\.|\(|\bJudgment\b|$))",
            re.IGNORECASE,
        )

        match = party_regex.search(text)
        if match:
            petitioner = match.group("petitioner").strip(" ,.-;")
            respondent = match.group("respondent").strip(" ,.-;")
            # Filter out generic titles or false positives
            if 3 <= len(petitioner) <= 120 and 3 <= len(respondent) <= 120:
                return [
                    {"role": "petitioner", "name": petitioner},
                    {"role": "respondent", "name": respondent},
                ]

        return []

    @classmethod
    def categorize(cls, text: str, statute_tags: list[str]) -> tuple[str, float]:
        """
        Deterministic keyword and statute scoring algorithm.
        Returns the top legal domain and normalized confidence score in [0.0, 1.0].
        """
        if not text:
            return "Civil", 0.30

        text_lower = text.lower()
        scores: dict[str, float] = {cat: 0.0 for cat in CANONICAL_CATEGORIES}

        # 1. Score based on extracted statute tags (strongest semantic indicator)
        for tag in statute_tags:
            tag_lower = tag.lower()
            if "article" in tag_lower:
                scores["Constitutional"] += 5.0
            if any(term in tag_lower for term in ["crpc", "ipc", "bns", "bnss", "pocso", "ndps", "uapa", "pmla"]):
                scores["Criminal"] += 5.0
            if any(term in tag_lower for term in ["cpc", "order vii", "rule", "specific relief"]):
                scores["Civil"] += 5.0
            if any(term in tag_lower for term in ["ibc", "companies", "ni act"]):
                scores["Corporate"] += 5.0
            if any(term in tag_lower for term in ["hindu marriage", "dv act"]):
                scores["Family"] += 5.0
            if "environment" in tag_lower:
                scores["Environment"] += 5.0

        # 2. Score based on domain keywords
        for category, kw_weights in cls.CATEGORY_KEYWORDS.items():
            for kw, weight in kw_weights.items():
                # Word boundary check for short words to avoid substrings
                if len(kw) <= 4:
                    if re.search(r"\b" + re.escape(kw) + r"\b", text_lower):
                        scores[category] += weight
                else:
                    count = text_lower.count(kw)
                    if count > 0:
                        # Diminishing returns for repeated keywords
                        scores[category] += weight * min(count, 3)

        # 3. Find top scoring category
        best_category = max(scores, key=lambda k: scores[k])
        best_score = scores[best_category]

        # Calculate confidence score
        if best_score >= 12.0:
            confidence = min(0.96, 0.85 + (best_score - 12.0) * 0.01)
        elif best_score >= 6.0:
            confidence = 0.70 + (best_score - 6.0) * 0.025
        elif best_score >= 2.0:
            confidence = 0.50 + (best_score - 2.0) * 0.05
        else:
            best_category = "Civil"  # Default generic civil law category
            confidence = 0.35

        return best_category, round(confidence, 4)

    @classmethod
    def classify(
        cls,
        title: str,
        text: str = "",
        source: str | None = None,
        default_court: CourtInfo | None = None,
    ) -> ClassificationResult:
        """
        Full classification pipeline executing all extractors in < 1 millisecond.
        """
        combined_text = f"{title}\n{text}".strip()

        # 1. Extract statutory references
        statute_tags = cls.extract_statutes(combined_text)

        # 2. Extract citations
        citations = cls.extract_citations(combined_text)

        # 3. Extract court
        court = cls.extract_court(combined_text, default_court=default_court)

        # 4. Extract opposing parties
        parties = cls.extract_parties(title) or cls.extract_parties(text[:300])

        # 5. Determine category & confidence
        subject_category, confidence = cls.categorize(combined_text, statute_tags)

        return ClassificationResult(
            subject_category=subject_category,
            confidence=confidence,
            statute_tags=statute_tags,
            citations=citations,
            parties=parties,
            court=court,
        )
