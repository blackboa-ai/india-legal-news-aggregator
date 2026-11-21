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
    content_type: str = "unknown"
    content_type_confidence: float = 0.0

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
            "content_type": self.content_type,
            "content_type_confidence": round(self.content_type_confidence, 4),
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
        if default_court and default_court.court_code == "international":
            return default_court

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
    def classify_content_type(
        cls,
        title: str = "",
        text: str = "",
        source: str = "",
        url: str = "",
    ) -> tuple[str, float]:
        """
        Determines 3-state content classification ('judgment', 'news', 'unknown')
        and confidence score (0.0 to 1.0).
        """
        return classify_content_type(title=title, text=text, source=source, url=url)

    @classmethod
    def is_substantive_judgment_or_major_case(
        cls,
        title: str = "",
        text: str = "",
        source: str = "",
    ) -> tuple[bool, str]:
        """Filters out routine procedural hearing logs, adjournments, and clerical listings."""
        return is_substantive_judgment_or_major_case(title=title, text=text, source=source)

    @classmethod
    def is_procedural_noise(
        cls,
        title: str = "",
        text: str = "",
    ) -> bool:
        """Helper checking if content is purely procedural hearing noise."""
        return is_procedural_noise(title=title, text=text)

    @classmethod
    def classify(
        cls,
        title: str,
        text: str = "",
        source: str | None = None,
        default_court: CourtInfo | None = None,
        url: str | None = None,
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
        if default_court and default_court.court_code == "international":
            subject_category, confidence = "International", 1.0
        else:
            subject_category, confidence = cls.categorize(combined_text, statute_tags)

        # 6. Determine content type & confidence
        content_type, content_type_confidence = classify_content_type(
            title=title,
            text=text,
            source=source or "",
            url=url or "",
        )

        return ClassificationResult(
            subject_category=subject_category,
            confidence=confidence,
            statute_tags=statute_tags,
            citations=citations,
            parties=parties,
            court=court,
            content_type=content_type,
            content_type_confidence=content_type_confidence,
        )


# --------------------------------------------------------------------------
# Content Type Heuristic Classifier Patterns & Standalone Function
# --------------------------------------------------------------------------

# Rule A: URL Patterns
RE_URL_NEWS = re.compile(
    r"/(?:columns|interviews|news|law-firms)(?:/|$|\?|#)",
    re.IGNORECASE,
)
RE_URL_JUDGMENT = re.compile(
    r"/(?:orders|judgment-summary)(?:/|$|\?|#)",
    re.IGNORECASE,
)

# Rule B: Syntactic Judicial Markers
RE_JUDGMENT_PARTY = re.compile(
    r"\b(?:vs\.?|v\.|versus)\b|\bin\s+re\s*:?",
    re.IGNORECASE,
)
RE_JUDGMENT_CASE_NUMS = re.compile(
    r"\b(?:s\.?l\.?p\.?|special\s+leave\s+petition|w\.?p\.?|writ\s+petition|crl\.?\s*a\.?|criminal\s+appeal|civil\s+appeal|c\.?a\.?|crl\.?\s*rev\.?|crl\.?\s*m\.?c\.?|l\.?p\.?a\.?|original\s+suit|o\.?s\.?)\b",
    re.IGNORECASE,
)
RE_JUDGMENT_BENCH = re.compile(
    r"\bcoram\s*:?|\bhon(?:'|\u2019)?ble\s+(?:mr\.|ms\.|mrs\.|dr\.)?\s*justice\b|\bhon(?:'|\u2019)?ble\s+(?:the\s+)?chief\s+justice\b|\b(?:division\s+bench|full\s+bench|constitution\s+bench)\b",
    re.IGNORECASE,
)
RE_JUDGMENT_DISPOSITIVE = re.compile(
    r"\[\s*read\s+(?:order|judgment)\s*\]|\bread\s+(?:order|judgment)\b"
    r"|\b(?:bail\s+granted|grants?\s+bail|granted\s+bail|bail\s+allowed|anticipatory\s+bail|interim\s+bail)\b"
    r"|\b(?:bail\s+rejected|bail\s+denied|denies?\s+bail|rejects?\s+bail|cancels?\s+bail|bail\s+cancelled)\b"
    r"|\b(?:bail\s+application\s+(?:is\s+)?(?:allowed|dismissed|rejected|disposed\s+of))\b"
    r"|\b(?:disposed\s+of|disposes?\s+of|disposal\s+of)\b"
    r"|\b(?:quashed|quashes?|quashing)(?:\s+(?:the\s+)?(?:fir|proceedings|chargesheet|order|complaint|conviction))?\b"
    r"|\b(?:fir|proceedings|chargesheet|order|complaint)\s+quashed\b"
    r"|\b(?:conviction\s+upheld|upholds?\s+conviction|conviction\s+confirmed|conviction\s+set\s+aside)\b"
    r"|\b(?:acquitted|acquittal\s+upheld|acquits?|acquittal\s+confirmed)\b"
    r"|\b(?:order\s+reserved|reserves?\s+order|judgment\s+reserved|reserves?\s+judgment|verdict\s+reserved|reserves?\s+verdict)\b"
    r"|\b(?:petition\s+allowed|petition\s+dismissed|appeal\s+allowed|appeal\s+dismissed)\b"
    r"|\b(?:writ\s+petition\s+(?:is\s+)?(?:allowed|dismissed)|writ\s+issued)\b"
    r"|\b(?:stay\s+granted|stays?\s+order|injunction\s+granted|restrains?\s+from)\b"
    r"|\b(?:stay\s+vacated|vacates?\s+stay|injunction\s+refused|refuses?\s+to\s+stay)\b"
    r"|\b(?:suit\s+(?:is\s+)?(?:decreed|dismissed)|decree\s+passed)\b"
    r"|\b(?:sentence\s+(?:is\s+)?(?:suspended|reduced)|suspends?\s+sentence)\b"
    r"|\b(?:impugned\s+order\s+(?:is\s+)?(?:set\s+aside|quashed)|sets?\s+aside\s+(?:the\s+)?(?:order|judgment))\b"
    r"|\b(?:arbitral\s+award\s+(?:upheld|set\s+aside)|awards?\s+compensation)\b",
    re.IGNORECASE,
)

# Rule C: Journalistic & Hearing Report Markers
RE_NEWS_JOURNALISTIC = re.compile(
    r"\breported\s+on\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b"
    r"|\b(?:told|speaking\s+to|briefed|informed)\s+reporters\b"
    r"|\bpress\s+(?:release|conference|statement|briefing)\b"
    r"|\bcollegium\s+(?:recommends?|recommended|recommendation)\b"
    r"|\b(?:supreme\s+court\s+)?collegium\b"
    r"|\bbar\s+council\s+election[s]?\b|\bbar\s+association\s+election[s]?\b"
    r"|\bcabinet\s+(?:approves?|approved|decision|clears?)\b|\bunion\s+cabinet\b"
    r"|\b(?:appointed|appointment\s+of)\s+(?:as\s+)?(?:judges?|chief\s+justice|cai|ag|attorney\s+general|solicitor\s+general|additional\s+solicitor)\b"
    r"|\belevation\s+(?:to|of)\s+(?:high\s+court|supreme\s+court|bench)\b"
    r"|\b(?:sworn\s+in|takes?\s+oath)\s+(?:as\s+)?(?:chief\s+justice|judge|union\s+minister)\b"
    r"|\b(?:farewell\s+function|farewell\s+address|retirement\s+of|tenure\s+extended)\b"
    r"|\b(?:law\s+minister|union\s+minister\s+for\s+law)\b"
    r"|\b(?:parliament\s+passes?|lok\s+sabha\s+passes?|rajya\s+sabha\s+passes?|bill\s+(?:introduced|tabled|passed))\b"
    r"|\b(?:inaugurated?|book\s+launch|annual\s+lecture|symposium|webinar|seminar|conference)\b",
    re.IGNORECASE,
)

# Rule C2: News Reporting of Ongoing Court Hearings (Not Dispositive Judgments)
RE_HEARING_REPORT = re.compile(
    r"\b(?:"
    r"to\s+hear\b"
    r"|hearing\s+(?:on|in|of|adjourned|deferred|postponed|continues|resumes)"
    r"|hearing\s+(?:\w+\s+)*(?:plea|petition|matter|bail|case|appeal)"
    r"|before\s+hearing\b"
    r"|adjourns?\s+(?:hearing|plea|matter|case|proceedings)"
    r"|seeks?\s+(?:response|reply|explanation|report|status\s+report)"
    r"|issues?\s+notice(?:\s+to|\s+on|\s+in)?"
    r"|notice\s+issued\s+(?:to|on|in)"
    r"|questions?\s+(?:its\s+)?(?:registry|cbi|ed|state|police|centre|govt|petitioner)"
    r"|asks?\s+(?:centre|state|cbi|ed|police|registry|parties)\s+to"
    r"|to\s+await\b"
    r"|await(?:s|ing)?\s+(?:\w+\s+)*(?:decision|order|judgment|verdict)"
    r"|plea\s+(?:in|filed\s+in|moved\s+in)\s+(?:sc|supreme\s+court|high\s+court|hc)"
    r"|oral\s+remarks?\s+(?:by|of|during)"
    r"|oral\s+observations?"
    r"|arguments\s+(?:continue|underway|heard|commence)"
    r"|matter\s+listed\s+for"
    r"|deferred\s+to"
    r"|re-?notifi(?:es|ed)\s+for"
    r")\b",
    re.IGNORECASE,
)

# Rule E: Procedural Noise in Court Dockets / Orders
RE_PROCEDURAL_NOISE = re.compile(
    r"\b(?:"
    r"matter\s+is\s+adjourned"
    r"|adjourned\s+to\b"
    r"|adjourned\s+for\b"
    r"|adjourned\s+at\s+the\s+request"
    r"|case\s+is\s+adjourned"
    r"|hearing\s+is\s+adjourned"
    r"|stand(?:s)?\s+over\s+to\b"
    r"|stands?\s+adjourned"
    r"|re-?notify\s+on\b"
    r"|re-?notified\s+for\b"
    r"|list\s+on\s+\d{1,2}(?:st|nd|rd|th)?[\s./-]"
    r"|list\s+after\s+\w+\s+weeks?"
    r"|list\s+in\s+the\s+month\s+of"
    r"|list\s+before\s+the\s+roster\s+bench"
    r"|list\s+for\s+hearing\s+on"
    r"|post\s+for\s+hearing\s+on"
    r"|put\s+up\s+on\s+\d"
    r"|weeks?\s+time\s+is\s+granted\s+to\s+file"
    r"|time\s+is\s+granted\s+to\s+file\s+(?:counter|rejoinder|reply|affidavit|status\s+report)"
    r"|time\s+granted\s+to\s+take\s+steps"
    r"|steps\s+not\s+taken"
    r"|service\s+is\s+awaited"
    r"|service\s+awaited"
    r"|process\s+fee\s+not\s+paid"
    r"|pf\s+not\s+filed"
    r"|fresh\s+steps\s+be\s+taken"
    r"|fresh\s+notice\s+be\s+issued"
    r"|notice\s+is\s+issued\s+returnable"
    r"|notice\s+returnable\s+on"
    r"|dasti\s+notice"
    r"|exemption\s+from\s+filing\s+(?:c/c|certified\s+copy|official\s+translation)\s+is\s+allowed"
    r")\b",
    re.IGNORECASE,
)

# Rule F: Major Cases of Public/Constitutional Significance
RE_MAJOR_CASE = re.compile(
    r"\b(?:"
    r"constitution\s+bench"
    r"|[579]\s*[- ]\s*judge\s+bench"
    r"|larger\s+bench"
    r"|reference\s+to\s+(?:a\s+)?larger\s+bench"
    r"|referred\s+to\s+(?:a\s+)?larger\s+bench"
    r"|chief\s+justice\s+of\s+india"
    r"|cji\b"
    r"|pmla\b|prevention\s+of\s+money\s+laundering"
    r"|uapa\b|unlawful\s+activities"
    r"|insolvency\s+and\s+bankruptcy\b|\bibc\b|cirp\b"
    r"|article\s+21\b|article\s+32\b|article\s+370\b|basic\s+structure"
    r"|vires\s+of|unconstitutional|strikes?\s+down"
    r"|public\s+interest\s+litigation|\bpil\b"
    r"|verdict\s+reserved|judgment\s+reserved|order\s+reserved"
    r"|cur\.\s*adv\.\s*vult"
    r")\b",
    re.IGNORECASE,
)

RE_SIGNATURE_BOILERPLATE = re.compile(
    r"\b(?:Signature\s+Not\s+Verified|Digitally\s+Signed\s+By|Signing\s+Date\s*:\s*\d{2}\.\d{2}\.\d{4})\b.*",
    re.IGNORECASE,
)


def is_substantive_judgment_or_major_case(
    title: str = "",
    text: str = "",
    source: str = "",
) -> tuple[bool, str]:
    """
    Evaluates whether a judicial record is a substantive dispositive judgment or a major case,
    filtering out routine procedural hearing logs, listing notices, and filing extensions.
    Returns (is_substantive: bool, reason: str).
    """
    combined = f"{title}\n{text}".strip()
    if not combined:
        return False, "empty_content"

    clean_text_no_sig = RE_SIGNATURE_BOILERPLATE.sub("", combined).strip()
    has_dispositive = bool(RE_JUDGMENT_DISPOSITIVE.search(combined))
    has_major_case = bool(RE_MAJOR_CASE.search(combined))
    has_procedural_noise = bool(RE_PROCEDURAL_NOISE.search(combined))

    # Clerical signature notice with no substantive content (< 40 chars)
    if RE_SIGNATURE_BOILERPLATE.search(combined) and len(clean_text_no_sig) < 40 and not has_dispositive and not has_major_case:
        return False, "clerical_signature_slip"

    # Procedural noise without substantive holding or major case status
    if has_procedural_noise and not has_dispositive and not has_major_case:
        return False, "procedural_noise"

    return True, "substantive_judgment_or_major_case"


def is_procedural_noise(title: str = "", text: str = "") -> bool:
    """Helper checking if content is purely procedural hearing noise."""
    substantive, _ = is_substantive_judgment_or_major_case(title, text)
    return not substantive


def classify_content_type(
    title: str = "",
    text: str = "",
    source: str = "",
    url: str = "",
) -> tuple[str, float]:
    """
    Deterministic heuristic content classifier (3-state: 'judgment', 'news', 'unknown').
    Operates in < 1ms with 0 MB memory allocation (pure compiled regex).
    """
    clean_source = (source or "").strip().lower()
    clean_title = (title or "").strip()
    clean_text = (text or "").strip()
    clean_url = (url or "").strip().lower()

    # Rule A: Authoritative source override
    if clean_source in ("sci", "indiankanoon"):
        # Check if the court order is purely procedural noise (routine adjournment, listing slip, filing notice)
        substantive, _ = is_substantive_judgment_or_major_case(clean_title, clean_text, source=clean_source)
        if not substantive:
            return ("unknown", 0.40)
        return ("judgment", 1.0)
    if clean_source == "bbc":
        return ("news", 1.0)

    j_score = 0.0
    n_score = 0.0
    j_content_matches = 0
    n_content_matches = 0

    # Rule A: URL Route Bias
    has_news_url = any(m in clean_url for m in ("/columns/", "/interviews/", "/news/", "/law-firms/")) or bool(
        RE_URL_NEWS.search(clean_url)
    )
    has_judgment_url = any(m in clean_url for m in ("/orders/", "/judgment-summary/")) or bool(
        RE_URL_JUDGMENT.search(clean_url)
    )

    if has_news_url:
        n_score += 2.5
    if has_judgment_url:
        j_score += 2.5

    # Rule B: Syntactic Judicial Markers
    # 1. Party indicators (vs, v., versus, In re:)
    if RE_JUDGMENT_PARTY.search(clean_title):
        j_score += 2.5
        j_content_matches += 1
    elif RE_JUDGMENT_PARTY.search(clean_text):
        j_score += 1.2
        j_content_matches += 1

    # 2. Case numbers (SLP, W.P., Crl.A., Civil Appeal)
    if RE_JUDGMENT_CASE_NUMS.search(clean_title):
        j_score += 2.5
        j_content_matches += 1
    elif RE_JUDGMENT_CASE_NUMS.search(clean_text):
        j_score += 1.2
        j_content_matches += 1

    # 3. Bench markers (CORAM:, HON'BLE MR. JUSTICE)
    if RE_JUDGMENT_BENCH.search(clean_title):
        j_score += 2.5
        j_content_matches += 1
    elif RE_JUDGMENT_BENCH.search(clean_text):
        j_score += 1.2
        j_content_matches += 1

    # 4. Dispositive verbs (BAIL GRANTED, DISPOSED OF, QUASHED, CONVICTION UPHELD, [Read Order])
    disp_title_matches = len(RE_JUDGMENT_DISPOSITIVE.findall(clean_title))
    if disp_title_matches > 0:
        j_score += min(5.0, 2.5 * disp_title_matches)
        j_content_matches += disp_title_matches

    disp_text_matches = len(RE_JUDGMENT_DISPOSITIVE.findall(clean_text))
    if disp_text_matches > 0:
        j_score += min(3.0, 1.2 * disp_text_matches)
        j_content_matches += disp_text_matches

    # 5. Major ongoing cases (Constitution Bench, CJI, Reserved verdict, Landmark statutory challenge)
    major_title_matches = len(RE_MAJOR_CASE.findall(clean_title))
    if major_title_matches > 0:
        j_score += min(4.0, 2.5 * major_title_matches)
        j_content_matches += major_title_matches

    # Rule C: Journalistic & Hearing Report markers
    news_title_matches = len(RE_NEWS_JOURNALISTIC.findall(clean_title))
    if news_title_matches > 0:
        n_score += min(5.0, 2.5 * news_title_matches)
        n_content_matches += news_title_matches

    news_text_matches = len(RE_NEWS_JOURNALISTIC.findall(clean_text))
    if news_text_matches > 0:
        n_score += min(3.0, 1.2 * news_text_matches)
        n_content_matches += news_text_matches

    # Rule C2: News reporting of ongoing hearings without dispositive rulings
    hearing_title_matches = len(RE_HEARING_REPORT.findall(clean_title))
    if hearing_title_matches > 0:
        n_score += min(5.0, 3.0 * hearing_title_matches)
        n_content_matches += hearing_title_matches

    hearing_text_matches = len(RE_HEARING_REPORT.findall(clean_text))
    if hearing_text_matches > 0:
        n_score += min(3.0, 1.5 * hearing_text_matches)
        n_content_matches += hearing_text_matches

    # If article reports a hearing/procedural step and lacks dispositive rulings, heavily bias to news
    if (hearing_title_matches > 0 or hearing_text_matches > 0) and disp_title_matches == 0 and disp_text_matches == 0:
        n_score += 2.5
        n_content_matches += 1

    # Rule D: Signal Conflict & Threshold Check
    # Conflicting signals: both sides have strong textual content matches with close scores
    if j_content_matches > 0 and n_content_matches > 0:
        min_score = min(j_score, n_score)
        max_score = max(j_score, n_score)
        if max_score > 0 and (min_score / max_score >= 0.65 or abs(j_score - n_score) < 1.5):
            return ("unknown", 0.5)

    # Insufficient signals (< 2.0 total score)
    if max(j_score, n_score) < 2.0:
        return ("unknown", 0.5)

    if j_score > n_score:
        margin = j_score - n_score
        confidence = min(0.98, 0.65 + 0.06 * margin)
        if confidence < 0.65:
            return ("unknown", round(confidence, 2))
        return ("judgment", round(confidence, 2))
    elif n_score > j_score:
        margin = n_score - j_score
        confidence = min(0.98, 0.65 + 0.06 * margin)
        if confidence < 0.65:
            return ("unknown", round(confidence, 2))
        return ("news", round(confidence, 2))
    else:
        return ("unknown", 0.5)
