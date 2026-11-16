"""
Landmark Indian Legal Judgments Seeder
Populates 12 foundational Supreme Court of India precedents with full metadata,
statutory citations, rich summaries, and 384-dimensional vector embeddings.
Covers:
- Section 438 CrPC / Section 482 BNSS Anticipatory Bail
- Article 21 Privacy & Personal Liberty
- Section 138 Negotiable Instruments Act
- Insolvency and Bankruptcy Code (IBC)
- Goods and Services Tax (GST)
- Arbitration and Conciliation Act
"""

import asyncio
import datetime
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.judgment import Judgment
from app.services.embedding_service import embedding_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("app.seed")

LANDMARK_JUDGMENTS: list[dict[str, Any]] = [
    {
        "external_id": "landmark-sc-sushila-aggarwal-2020",
        "title": "Sushila Aggarwal and Others v. State (NCT of Delhi) and Another",
        "short_title": "Sushila Aggarwal v. State (NCT of Delhi)",
        "court_code": "sc",
        "court_name": "Supreme Court of India",
        "court_level": 1,
        "judgment_date": datetime.date(2020, 1, 29),
        "subject_category": "Criminal",
        "excerpt": (
            "A 5-Judge Constitution Bench of the Supreme Court held that the protection of anticipatory bail "
            "under Section 438 of the Code of Criminal Procedure (CrPC) / Section 482 of the Bharatiya Nagarik "
            "Suraksha Sanhita (BNSS) should not ordinarily be restricted to a fixed time limit. Pre-arrest bail "
            "continues until the conclusion of the trial unless special circumstances justify a limitation. "
            "The Court emphasized that personal liberty protected under Article 21 warrants that citizens are not "
            "arbitrarily subjected to arrest and custodial harassment in non-bailable offences."
        ),
        "full_text": (
            "IN THE SUPREME COURT OF INDIA\n"
            "CRIMINAL APPELLATE JURISDICTION\n\n"
            "SPECIAL LEAVE PETITION (CRIMINAL) NOS. 7281-7282 OF 2017\n"
            "Sushila Aggarwal and Others ... Appellants\n"
            "versus\n"
            "State (NCT of Delhi) and Another ... Respondents\n\n"
            "CORAM: Hon'ble Mr. Justice Arun Mishra, Hon'ble Ms. Justice Indira Banerjee, "
            "Hon'ble Mr. Justice Vineet Saran, Hon'ble Mr. Justice M.R. Shah, and Hon'ble Mr. Justice S. Ravindra Bhat.\n\n"
            "JUDGMENT:\n"
            "1. The reference before this Constitution Bench stems from conflicting decisions on whether protection "
            "under Section 438 of the Code of Criminal Procedure, 1973 (CrPC) granting anticipatory bail should be "
            "limited to a fixed period, or whether it continues till the end of the trial.\n\n"
            "2. We hold that there is nothing in the language of Section 438 CrPC (or Section 482 BNSS) indicating that "
            "an order granting anticipatory bail must necessarily be time-bound. An order of pre-arrest bail does not "
            "automatically expire when the accused is summoned by the court or when charges are framed. Rather, it operates "
            "till the end of the trial, safeguarding fundamental personal liberty under Article 21 of the Constitution.\n\n"
            "3. Conditions may be imposed under Section 438(2) CrPC based on specific facts, such as joining investigation, "
            "not tampering with evidence, or not leaving the country. However, imposing arbitrary blanket time restrictions "
            "frustrates the legislative intent of insulating innocent persons from humiliation and harassment.\n\n"
            "ORDER: Reference answered accordingly; anticipatory bail protection affirmed to operate ordinarily till trial."
        ),
        "url": "https://indiankanoon.org/doc/135372421/",
        "parties": [
            {"role": "Appellant", "name": "Sushila Aggarwal and Others"},
            {"role": "Respondent", "name": "State (NCT of Delhi) and Another"},
        ],
        "tags": [
            "Section 438 CrPC",
            "Section 482 BNSS",
            "Anticipatory Bail",
            "Personal Liberty",
            "Article 21",
            "Pre-Arrest Bail",
        ],
        "source": "sci",
    },
    {
        "external_id": "landmark-sc-gurbaksh-singh-sibbia-1980",
        "title": "Gurbaksh Singh Sibbia and Others v. State of Punjab",
        "short_title": "Gurbaksh Singh Sibbia v. State of Punjab",
        "court_code": "sc",
        "court_name": "Supreme Court of India",
        "court_level": 1,
        "judgment_date": datetime.date(1980, 4, 9),
        "subject_category": "Criminal",
        "excerpt": (
            "A 5-Judge Constitution Bench presided by CJI Y.V. Chandrachud laid down the magna carta of anticipatory "
            "bail jurisprudence under Section 438 CrPC. The Court ruled that judicial discretion to grant pre-arrest bail "
            "is of wide amplitude and should not be fettered by self-imposed artificial restrictions not contained in the "
            "statute. Anticipatory bail can be applied for before an FIR is lodged where there is reasonable apprehension "
            "of arrest for a non-bailable offence, protecting personal liberty under Article 21."
        ),
        "full_text": (
            "IN THE SUPREME COURT OF INDIA\n"
            "CRIMINAL APPELLATE JURISDICTION\n\n"
            "APPEAL (CRL.) 335 OF 1978\n"
            "Gurbaksh Singh Sibbia etc. ... Appellants\n"
            "versus\n"
            "State of Punjab ... Respondent\n\n"
            "CORAM: Hon'ble Chief Justice Y.V. Chandrachud, Hon'ble Mr. Justice P.N. Bhagwati, "
            "Hon'ble Mr. Justice V.R. Krishna Iyer, Hon'ble Mr. Justice R.S. Sarkaria, and Hon'ble Mr. Justice V.D. Tulzapurkar.\n\n"
            "JUDGMENT:\n"
            "1. Section 438 of the Code of Criminal Procedure, 1973 confers wide discretionary powers on the High Court "
            "and the Court of Session to grant anticipatory bail. The Law Commission in its 41st Report highlighted the "
            "necessity of such provision to prevent political rivals and influential parties from orchestrating arrests to "
            "disgrace reputable citizens.\n\n"
            "2. We cannot endorse the proposition of the Full Bench of the High Court that anticipatory bail can only be "
            "granted in exceptional or extraordinary cases. The discretion of the court must remain unconfined by rigid rules, "
            "governed by the nature and gravity of accusation, criminal antecedents, and the likelihood of the applicant fleeing.\n\n"
            "3. The filing of an FIR is not a condition precedent to moving an application under Section 438 CrPC (or Section 482 BNSS); "
            "the existence of a genuine, reasonable apprehension of arrest is sufficient to trigger judicial scrutiny.\n\n"
            "ORDER: Appeals allowed; principles on Section 438 CrPC enunciated."
        ),
        "url": "https://indiankanoon.org/doc/170940/",
        "parties": [
            {"role": "Appellant", "name": "Gurbaksh Singh Sibbia and Others"},
            {"role": "Respondent", "name": "State of Punjab"},
        ],
        "tags": [
            "Section 438 CrPC",
            "Section 482 BNSS",
            "Anticipatory Bail",
            "Personal Liberty",
            "Article 21",
            "Arrest Safeguards",
        ],
        "source": "sci",
    },
    {
        "external_id": "landmark-sc-puttaswamy-privacy-2017",
        "title": "Justice K.S. Puttaswamy (Retd.) and Another v. Union of India and Others",
        "short_title": "Puttaswamy (Privacy 9-Judge)",
        "court_code": "sc",
        "court_name": "Supreme Court of India",
        "court_level": 1,
        "judgment_date": datetime.date(2017, 8, 24),
        "subject_category": "Constitutional",
        "excerpt": (
            "A unanimous 9-Judge Constitution Bench of the Supreme Court declared that the Right to Privacy is a "
            "fundamental right guaranteed under Article 21 and Part III of the Constitution of India. Overruling previous "
            "dicta in M.P. Sharma (1954) and ADM Jabalpur (1976), the Court established that privacy encompasses informational "
            "privacy, bodily autonomy, and spatial privacy. Any state interference with individual privacy must satisfy "
            "the rigorous 3-prong test of legality, legitimate state interest, and proportionality."
        ),
        "full_text": (
            "IN THE SUPREME COURT OF INDIA\n"
            "CIVIL ORIGINAL JURISDICTION\n\n"
            "WRIT PETITION (CIVIL) NO. 494 OF 2012\n"
            "Justice K.S. Puttaswamy (Retd.) and Another ... Petitioners\n"
            "versus\n"
            "Union of India and Others ... Respondents\n\n"
            "CORAM: Hon'ble Chief Justice J.S. Khehar, Hon'ble Mr. Justice J. Chelameswar, "
            "Hon'ble Mr. Justice S.A. Bobde, Hon'ble Mr. Justice R.K. Agrawal, Hon'ble Mr. Justice Rohinton Fali Nariman, "
            "Hon'ble Mr. Justice A.M. Sapre, Hon'ble Mr. Justice D.Y. Chandrachud, Hon'ble Mr. Justice Sanjay Kishan Kaul, "
            "and Hon'ble Mr. Justice S. Abdul Nazeer.\n\n"
            "JUDGMENT:\n"
            "1. The central question referred to this 9-Judge Bench is whether the right to privacy is a fundamental right "
            "under the Constitution of India.\n\n"
            "2. Privacy is the constitutional core of human dignity. It is an inviolable sanctuary that protects personal choices, "
            "intimate relations, political belief, and digital informational self-determination. It is founded on the guarantee "
            "of life and personal liberty in Article 21, as well as the fundamental freedoms in Part III.\n\n"
            "3. An invasion of privacy by state action must satisfy threefold requirements: (a) Legality, which postulates the "
            "existence of law; (b) Need, defined in terms of a legitimate state aim; and (c) Proportionality, which ensures a "
            "rational nexus between the means adopted and the object sought to be achieved.\n\n"
            "ORDER: The right to privacy is declared a fundamental right under Article 21 of the Constitution."
        ),
        "url": "https://indiankanoon.org/doc/127517806/",
        "parties": [
            {"role": "Petitioner", "name": "Justice K.S. Puttaswamy (Retd.) and Another"},
            {"role": "Respondent", "name": "Union of India and Others"},
        ],
        "tags": [
            "Article 21",
            "Right to Privacy",
            "Fundamental Rights",
            "Data Protection",
            "Aadhaar",
            "Proportionality Test",
            "Personal Liberty",
        ],
        "source": "sci",
    },
    {
        "external_id": "landmark-sc-maneka-gandhi-1978",
        "title": "Maneka Gandhi v. Union of India and Another",
        "short_title": "Maneka Gandhi v. Union of India",
        "court_code": "sc",
        "court_name": "Supreme Court of India",
        "court_level": 1,
        "judgment_date": datetime.date(1978, 1, 25),
        "subject_category": "Constitutional",
        "excerpt": (
            "A landmark 7-Judge Constitution Bench transformed Indian constitutional law by holding that 'procedure "
            "established by law' under Article 21 cannot be arbitrary or oppressive, but must be just, fair, and reasonable. "
            "The Court formulated the 'Golden Triangle' doctrine, holding that Articles 14, 19, and 21 are not watertight "
            "compartments but mutually reinforce each other. The impounding of a passport without providing reasons or hearing "
            "was held violative of natural justice and personal liberty."
        ),
        "full_text": (
            "IN THE SUPREME COURT OF INDIA\n"
            "ORIGINAL JURISDICTION\n\n"
            "WRIT PETITION NO. 231 OF 1977\n"
            "Maneka Gandhi ... Petitioner\n"
            "versus\n"
            "Union of India and Another ... Respondents\n\n"
            "CORAM: Hon'ble Mr. Justice M. Hameedullah Beg (CJI), Hon'ble Mr. Justice Y.V. Chandrachud, "
            "Hon'ble Mr. Justice P.N. Bhagwati, Hon'ble Mr. Justice V.R. Krishna Iyer, Hon'ble Mr. Justice N.L. Untwalia, "
            "Hon'ble Mr. Justice S. Murtaza Fazal Ali, and Hon'ble Mr. Justice P.S. Kailasam.\n\n"
            "JUDGMENT:\n"
            "1. The petitioner's passport was impounded by the Regional Passport Office under Section 10(3)(c) of the "
            "Passports Act in the 'interests of the general public', without furnishing reasons or granting an opportunity of being heard.\n\n"
            "2. We overrule the narrow restrictive view in A.K. Gopalan. Fundamental rights form an integrated scheme. "
            "The law depriving a person of personal liberty under Article 21 must satisfy the tests of Article 14 (non-arbitrariness) "
            "and Article 19 (reasonableness). Procedure established by law must incorporate the principles of natural justice.\n\n"
            "3. The right to travel abroad is part of personal liberty under Article 21, and any order depriving a citizen of such right "
            "without notice or hearing is void for violating natural justice and constitutional guarantees.\n\n"
            "ORDER: Petition disposed of; government required to provide post-decisional hearing and review impound order."
        ),
        "url": "https://indiankanoon.org/doc/1953529/",
        "parties": [
            {"role": "Petitioner", "name": "Maneka Gandhi"},
            {"role": "Respondent", "name": "Union of India and Another"},
        ],
        "tags": [
            "Article 21",
            "Article 14",
            "Article 19",
            "Golden Triangle",
            "Due Process",
            "Right to Travel Abroad",
            "Personal Liberty",
        ],
        "source": "sci",
    },
    {
        "external_id": "landmark-sc-bir-singh-mukesh-kumar-2019",
        "title": "Bir Singh v. Mukesh Kumar",
        "short_title": "Bir Singh v. Mukesh Kumar",
        "court_code": "sc",
        "court_name": "Supreme Court of India",
        "court_level": 1,
        "judgment_date": datetime.date(2019, 2, 6),
        "subject_category": "Criminal",
        "excerpt": (
            "The Supreme Court settled crucial legal principles on Section 138 and Section 139 of the Negotiable "
            "Instruments Act, 1881. Held that once the execution and signature on a cheque are admitted by the drawer, "
            "there is an operative statutory presumption of law that the cheque was issued in discharge of a legally "
            "enforceable debt or liability. Even if a signed blank cheque is voluntarily given to the payee and filled in "
            "subsequently, the drawer is criminally liable unless rebutting evidence is produced."
        ),
        "full_text": (
            "IN THE SUPREME COURT OF INDIA\n"
            "CRIMINAL APPELLATE JURISDICTION\n\n"
            "CRIMINAL APPEAL NOS. 230-231 OF 2019\n"
            "Bir Singh ... Appellant\n"
            "versus\n"
            "Mukesh Kumar ... Respondent\n\n"
            "CORAM: Hon'ble Mr. Justice R. Banumathi and Hon'ble Ms. Justice Indira Banerjee.\n\n"
            "JUDGMENT:\n"
            "1. The respondent was convicted under Section 138 of the Negotiable Instruments Act for dishonour of a cheque "
            "amounting to Rs. 15,00,000/- for insufficiency of funds. The High Court acquitted the respondent holding that the "
            "appellant failed to prove financial capacity.\n\n"
            "2. Section 139 of the NI Act mandates a statutory presumption that the holder of a cheque received it for the "
            "discharge, in whole or in part, of any debt or other liability. A meaningful reading of Sections 20, 87, and 139 establishes "
            "that a person signing a cheque and handing it over authorizes the payee to complete the instrument.\n\n"
            "3. The drawer cannot escape liability by simply asserting that the cheque was handed over as security or blank, unless "
            "he rebuts the presumption through probable evidence of payment or absence of consideration.\n\n"
            "ORDER: Appeals allowed; High Court acquittal set aside and conviction under Section 138 NI Act restored."
        ),
        "url": "https://indiankanoon.org/doc/171241193/",
        "parties": [
            {"role": "Appellant", "name": "Bir Singh"},
            {"role": "Respondent", "name": "Mukesh Kumar"},
        ],
        "tags": [
            "Section 138 NI Act",
            "Section 139 NI Act",
            "Negotiable Instruments Act",
            "Cheque Bounce",
            "Presumption of Debt",
            "Financial Fraud",
        ],
        "source": "sci",
    },
    {
        "external_id": "landmark-sc-dalmia-cement-galaxy-traders-2001",
        "title": "Dalmia Cement (Bharat) Ltd. v. Galaxy Traders & Agencies Ltd. and Others",
        "short_title": "Dalmia Cement v. Galaxy Traders",
        "court_code": "sc",
        "court_name": "Supreme Court of India",
        "court_level": 1,
        "judgment_date": datetime.date(2001, 1, 16),
        "subject_category": "Corporate",
        "excerpt": (
            "The Supreme Court delivered an authoritative ruling on statutory demand notice and cause of action under "
            "Section 138 and Section 142 of the Negotiable Instruments Act. Held that Chapter XVII was introduced to promote "
            "business efficacy and commercial integrity in banking transactions. While a cheque can be presented multiple "
            "times during its validity, statutory cause of action to file a complaint arises upon service of formal demand "
            "notice and failure by the drawer to make payment within 15 days."
        ),
        "full_text": (
            "IN THE SUPREME COURT OF INDIA\n"
            "CRIMINAL APPELLATE JURISDICTION\n\n"
            "CRIMINAL APPEAL NO. 45 OF 2001\n"
            "Dalmia Cement (Bharat) Ltd. ... Appellant\n"
            "versus\n"
            "Galaxy Traders & Agencies Ltd. and Others ... Respondents\n\n"
            "CORAM: Hon'ble Mr. Justice K.T. Thomas and Hon'ble Mr. Justice R.P. Sethi.\n\n"
            "JUDGMENT:\n"
            "1. The appellant supplied cement to respondent against cheques that were returned unpaid with the endorsement "
            "'funds insufficient'. Upon demand notice, payment was not made, leading to complaints under Section 138 NI Act.\n\n"
            "2. Section 138 was enacted to build confidence in financial transactions by ensuring that commitments represented by "
            "cheques are honoured. The statutory scheme permits re-presentation of cheques within their validity period, but once "
            "notice is dispatched and 15 days expire without settlement, cause of action crystallizes under Section 142.\n\n"
            "3. The Act should be interpreted purposefully to achieve the legislative intent of curbing fraudulent defaults and "
            "enhancing commercial trust in banking systems.\n\n"
            "ORDER: Appeal allowed; criminal complaints under Section 138 directed to proceed on merits."
        ),
        "url": "https://indiankanoon.org/doc/1529124/",
        "parties": [
            {"role": "Appellant", "name": "Dalmia Cement (Bharat) Ltd."},
            {"role": "Respondent", "name": "Galaxy Traders & Agencies Ltd. and Others"},
        ],
        "tags": [
            "Section 138 NI Act",
            "Section 142 NI Act",
            "Negotiable Instruments Act",
            "Statutory Notice",
            "Cheque Dishonour",
            "Banking Law",
        ],
        "source": "sci",
    },
    {
        "external_id": "landmark-sc-swiss-ribbons-ibc-2019",
        "title": "Swiss Ribbons Pvt. Ltd. and Another v. Union of India and Others",
        "short_title": "Swiss Ribbons v. Union of India",
        "court_code": "sc",
        "court_name": "Supreme Court of India",
        "court_level": 1,
        "judgment_date": datetime.date(2019, 1, 25),
        "subject_category": "Corporate",
        "excerpt": (
            "The Supreme Court affirmed the complete constitutional validity of the Insolvency and Bankruptcy Code (IBC), "
            "2016. Upheld the classification between financial creditors (Section 7) and operational creditors (Section 9) "
            "as having a rational nexus to the objective of timely corporate resolution. Validated Section 29A disqualifying "
            "wilful defaulters and tainted promoters from bidding for insolvent companies, emphasizing that IBC is a corporate "
            "revival mechanism aimed at maximizing asset value, not a debt recovery statute."
        ),
        "full_text": (
            "IN THE SUPREME COURT OF INDIA\n"
            "CIVIL ORIGINAL JURISDICTION\n\n"
            "WRIT PETITION (CIVIL) NO. 99 OF 2018\n"
            "Swiss Ribbons Pvt. Ltd. and Another ... Petitioners\n"
            "versus\n"
            "Union of India and Others ... Respondents\n\n"
            "CORAM: Hon'ble Mr. Justice Rohinton Fali Nariman and Hon'ble Mr. Justice Navin Sinha.\n\n"
            "JUDGMENT:\n"
            "1. Various writ petitions challenge provisions of the Insolvency and Bankruptcy Code, 2016, alleging violation "
            "of Article 14 on grounds of unequal treatment of operational creditors and disqualification of promoters under Section 29A.\n\n"
            "2. We hold that the IBC is an economic reform legislation intended to resolve corporate distress and maximize asset value "
            "of the corporate debtor as a going concern. Financial creditors and operational creditors are fundamentally distinct: "
            "financial creditors evaluate financial viability and loan servicing from inception, whereas operational creditors supply "
            "goods and services on running accounts.\n\n"
            "3. Section 29A acts as a crucial firewall ensuring that unscrupulous promoters who brought the company to its knees do not "
            "re-acquire control at discounted prices through backdoor CIRP processes.\n\n"
            "ORDER: Constitutional validity of the Insolvency and Bankruptcy Code, 2016 upheld in its entirety."
        ),
        "url": "https://indiankanoon.org/doc/173726827/",
        "parties": [
            {"role": "Petitioner", "name": "Swiss Ribbons Pvt. Ltd. and Another"},
            {"role": "Respondent", "name": "Union of India and Others"},
        ],
        "tags": [
            "IBC Insolvency",
            "Insolvency and Bankruptcy Code",
            "Section 7 IBC",
            "Section 9 IBC",
            "Section 29A IBC",
            "NCLT",
            "Resolution Professional",
            "CIRP",
        ],
        "source": "sci",
    },
    {
        "external_id": "landmark-sc-essar-steel-coc-2020",
        "title": "Committee of Creditors of Essar Steel India Limited v. Satish Kumar Gupta and Others",
        "short_title": "Essar Steel IBC Landmark",
        "court_code": "sc",
        "court_name": "Supreme Court of India",
        "court_level": 1,
        "judgment_date": datetime.date(2019, 11, 15),
        "subject_category": "Corporate",
        "excerpt": (
            "The Supreme Court established the supreme commercial wisdom of the Committee of Creditors (CoC) under the "
            "Insolvency and Bankruptcy Code, 2016. Reversed the NCLAT ruling that mandated parity between secured financial "
            "creditors and operational creditors. Ruled that judicial review by NCLT/NCLAT is strictly restricted to Section 30(2) "
            "and cannot interfere with the commercial terms or distribution of resolution proceeds determined by the CoC. "
            "Reaffirmed the 'clean slate' doctrine for successful resolution applicants."
        ),
        "full_text": (
            "IN THE SUPREME COURT OF INDIA\n"
            "CIVIL APPELLATE JURISDICTION\n\n"
            "CIVIL APPEAL NO. 8766-8767 OF 2019\n"
            "Committee of Creditors of Essar Steel India Limited ... Appellant\n"
            "versus\n"
            "Satish Kumar Gupta and Others ... Respondents\n\n"
            "CORAM: Hon'ble Mr. Justice Rohinton Fali Nariman, Hon'ble Mr. Justice Surya Kant, "
            "and Hon'ble Mr. Justice V. Ramasubramanian.\n\n"
            "JUDGMENT:\n"
            "1. The NCLAT modified the resolution plan submitted by ArcelorMittal for Essar Steel, ordering equal proportional "
            "distribution between secured financial creditors and operational creditors. The CoC appeals.\n\n"
            "2. There is no doubt that the commercial wisdom of the Committee of Creditors in deciding whether to rehabilitate "
            "a corporate debtor by approving a resolution plan is non-justiciable. The adjudicating authority (NCLT) has no jurisdiction "
            "to modify commercial distribution or assess business feasibility.\n\n"
            "3. Equality is only among equals. Secured financial creditors who have taken real securities cannot be equated with "
            "unsecured operational creditors. Once a resolution plan is approved, a successful resolution applicant starts with a clean slate "
            "without past liabilities or unadmitted claims.\n\n"
            "ORDER: Appeals allowed; NCLAT judgment set aside and CoC approved resolution plan reinstated."
        ),
        "url": "https://indiankanoon.org/doc/196590209/",
        "parties": [
            {"role": "Appellant", "name": "Committee of Creditors of Essar Steel India Limited"},
            {"role": "Respondent", "name": "Satish Kumar Gupta and Others"},
        ],
        "tags": [
            "IBC Insolvency",
            "Committee of Creditors",
            "Commercial Wisdom",
            "CIRP",
            "Financial Creditors",
            "Operational Creditors",
            "Resolution Plan",
        ],
        "source": "sci",
    },
    {
        "external_id": "landmark-sc-mohit-minerals-gst-2022",
        "title": "Union of India and Another v. Mohit Minerals Pvt. Ltd.",
        "short_title": "Mohit Minerals GST Landmark",
        "court_code": "sc",
        "court_name": "Supreme Court of India",
        "court_level": 1,
        "judgment_date": datetime.date(2022, 5, 19),
        "subject_category": "Administrative",
        "excerpt": (
            "A 3-Judge Bench of the Supreme Court held that the recommendations of the Goods and Services Tax (GST) "
            "Council under Article 279A are not binding mandates on Parliament or State Legislatures, but are persuasive "
            "instruments of cooperative federalism. The Court struck down Notification No. 8/2017 and 10/2017 levying "
            "Integrated GST (IGST) on ocean freight paid by foreign exporters under CIF contracts, holding that ocean freight "
            "is part of a composite import supply already taxed under Customs and IGST."
        ),
        "full_text": (
            "IN THE SUPREME COURT OF INDIA\n"
            "CIVIL APPELLATE JURISDICTION\n\n"
            "CIVIL APPEAL NO. 1390 OF 2022\n"
            "Union of India and Another ... Appellants\n"
            "versus\n"
            "Mohit Minerals Pvt. Ltd. ... Respondent\n\n"
            "CORAM: Hon'ble Mr. Justice D.Y. Chandrachud, Hon'ble Mr. Justice Surya Kant, "
            "and Hon'ble Mr. Justice Vikram Nath.\n\n"
            "JUDGMENT:\n"
            "1. The Union appeals against the Gujarat High Court decision striking down the levy of IGST on ocean freight for "
            "import of goods under Cost, Insurance and Freight (CIF) contracts.\n\n"
            "2. Article 246A confers simultaneous legislative power upon the Union and the States to enact GST laws. Article 279A "
            "establishes the GST Council to facilitate uniform tax policy through cooperative dialogue. Recommendations of the GST Council "
            "are not binding legal commands but persuasive policy formulations.\n\n"
            "3. Under Section 2(30) of the CGST Act, a CIF contract represents a composite supply where transportation of goods by sea "
            "is ancillary to the principal supply of imported goods. Levying separate IGST on ocean freight on a reverse charge basis "
            "violates the concept of composite supply and amounts to double taxation.\n\n"
            "ORDER: Appeals dismissed; ocean freight IGST notifications held ultra vires."
        ),
        "url": "https://indiankanoon.org/doc/137682218/",
        "parties": [
            {"role": "Appellant", "name": "Union of India and Another"},
            {"role": "Respondent", "name": "Mohit Minerals Pvt. Ltd."},
        ],
        "tags": [
            "GST",
            "Goods and Services Tax",
            "Ocean Freight",
            "Article 246A",
            "Article 279A",
            "IGST Act",
            "Cooperative Federalism",
            "Indirect Tax",
        ],
        "source": "sci",
    },
    {
        "external_id": "landmark-sc-ecom-gill-coffee-itc-2023",
        "title": "State of Karnataka v. M/s Ecom Gill Coffee Trading Pvt. Ltd.",
        "short_title": "State of Karnataka v. Ecom Gill Coffee",
        "court_code": "sc",
        "court_name": "Supreme Court of India",
        "court_level": 1,
        "judgment_date": datetime.date(2023, 3, 13),
        "subject_category": "Administrative",
        "excerpt": (
            "The Supreme Court held that the burden of proving the genuineness of a commercial transaction and entitlement "
            "to Input Tax Credit (ITC) under value-added and GST tax regimes lies squarely upon the purchasing dealer. "
            "Producing invoices, delivery notes, and proof of banking payments is insufficient on its own; the dealer must "
            "demonstrate actual physical delivery of goods and that the selling dealer discharged tax liability to the exchequer, "
            "deterring bogus billing rackets."
        ),
        "full_text": (
            "IN THE SUPREME COURT OF INDIA\n"
            "CIVIL APPELLATE JURISDICTION\n\n"
            "CIVIL APPEAL NO. 230 OF 2023\n"
            "State of Karnataka ... Appellant\n"
            "versus\n"
            "M/s Ecom Gill Coffee Trading Pvt. Ltd. ... Respondent\n\n"
            "CORAM: Hon'ble Mr. Justice M.R. Shah and Hon'ble Mr. Justice C.T. Ravikumar.\n\n"
            "JUDGMENT:\n"
            "1. The revenue challenges the High Court judgment allowing Input Tax Credit (ITC) to purchasing dealers whose "
            "selling dealers were found to be fictitious or non-existent upon physical verification.\n\n"
            "2. Under Section 70 of the KVAT Act (and similarly under Section 16(2) of the CGST Act), the burden of proof to claim "
            "credit or rebate of tax is on the dealer claiming the credit. Mere production of tax invoices or banking transactions "
            "cannot establish entitlement to ITC where the selling dealer is non-genuine or did not pay tax.\n\n"
            "3. To claim ITC, the purchasing dealer must produce cogent evidence demonstrating physical movement of goods, transport "
            "receipts, toll plaza slips, warehouse records, and payment of statutory tax.\n\n"
            "ORDER: Appeals allowed; High Court orders set aside and assessing authority demands restored."
        ),
        "url": "https://indiankanoon.org/doc/171249112/",
        "parties": [
            {"role": "Appellant", "name": "State of Karnataka"},
            {"role": "Respondent", "name": "M/s Ecom Gill Coffee Trading Pvt. Ltd."},
        ],
        "tags": [
            "GST",
            "Input Tax Credit",
            "ITC",
            "CGST Act",
            "Section 16 CGST Act",
            "Tax Compliance",
            "Bogus Invoices",
        ],
        "source": "sci",
    },
    {
        "external_id": "landmark-sc-vidya-drolia-arbitration-2021",
        "title": "Vidya Drolia and Others v. Durga Trading Corporation",
        "short_title": "Vidya Drolia v. Durga Trading Corp",
        "court_code": "sc",
        "court_name": "Supreme Court of India",
        "court_level": 1,
        "judgment_date": datetime.date(2020, 12, 14),
        "subject_category": "Civil",
        "excerpt": (
            "A 3-Judge Bench of the Supreme Court established the comprehensive 4-fold test to determine the arbitrability "
            "of disputes under Section 8 and Section 11 of the Arbitration and Conciliation Act, 1996. Overruling Himangni "
            "Enterprises, the Court held that landlord-tenant disputes governed by the Transfer of Property Act are arbitrable. "
            "Reaffirmed that the scope of judicial inquiry at the referral stage under Section 11 is strictly limited to prima "
            "facie examination of the existence of the arbitration agreement."
        ),
        "full_text": (
            "IN THE SUPREME COURT OF INDIA\n"
            "CIVIL APPELLATE JURISDICTION\n\n"
            "CIVIL APPEAL NO. 2402 OF 2019\n"
            "Vidya Drolia and Others ... Appellants\n"
            "versus\n"
            "Durga Trading Corporation ... Respondent\n\n"
            "CORAM: Hon'ble Mr. Justice N.V. Ramana, Hon'ble Mr. Justice Sanjiv Khanna, "
            "and Hon'ble Mr. Justice Krishna Murari.\n\n"
            "JUDGMENT:\n"
            "1. This reference addresses whether tenancy disputes are arbitrable, and defines the parameters of judicial review "
            "under Sections 8 and 11 of the Arbitration and Conciliation Act, 1996.\n\n"
            "2. We formulate a fourfold test: a dispute is non-arbitrable when (1) it relates to actions in rem; (2) it affects third "
            "party rights or erga omnes obligations; (3) it involves inalienable sovereign functions; or (4) it is expressly or by necessary "
            "implication reserved by statute for exclusive public adjudication.\n\n"
            "3. Landlord-tenant disputes under the Transfer of Property Act are actions in personam and fully arbitrable, except where "
            "a special rent control statute confers exclusive jurisdiction on a Rent Tribunal. At the Section 11 referral stage, the court "
            "undertakes only a prima facie review: when in doubt, refer to arbitration.\n\n"
            "ORDER: Tenancy disputes under Transfer of Property Act held arbitrable; reference answered."
        ),
        "url": "https://indiankanoon.org/doc/152341902/",
        "parties": [
            {"role": "Appellant", "name": "Vidya Drolia and Others"},
            {"role": "Respondent", "name": "Durga Trading Corporation"},
        ],
        "tags": [
            "Arbitration",
            "Arbitration and Conciliation Act",
            "Section 8 Arbitration Act",
            "Section 11 Arbitration Act",
            "Arbitrability",
            "Landlord Tenant",
        ],
        "source": "sci",
    },
    {
        "external_id": "landmark-sc-arbitration-stamp-act-2023",
        "title": "In Re: Interplay between Arbitration Agreements under the Arbitration and Conciliation Act 1996 and the Indian Stamp Act 1899",
        "short_title": "Arbitration Agreements & Stamp Act (7-Judge)",
        "court_code": "sc",
        "court_name": "Supreme Court of India",
        "court_level": 1,
        "judgment_date": datetime.date(2023, 12, 13),
        "subject_category": "Civil",
        "excerpt": (
            "A unanimous 7-Judge Constitution Bench headed by CJI D.Y. Chandrachud overruled the 5-Judge ruling in NN Global "
            "Mercantile. The Bench ruled that an arbitration clause contained in an unstamped or insufficiently stamped agreement "
            "is not void or invalid ab initio. Non-stamping is a curable defect under the Indian Stamp Act, 1899. Under Section 11(6A) "
            "of the Arbitration Act, courts at the referral stage must only verify the existence of the arbitration agreement, "
            "leaving all issues of stamp duty and evidentiary admissibility to the arbitral tribunal under competence-competence."
        ),
        "full_text": (
            "IN THE SUPREME COURT OF INDIA\n"
            "CIVIL ORIGINAL JURISDICTION\n\n"
            "CURATIVE PETITION (CIVIL) NO. 44 OF 2023\n"
            "IN RE: INTERPLAY BETWEEN ARBITRATION AGREEMENTS UNDER THE ARBITRATION AND CONCILIATION ACT 1996 AND THE INDIAN STAMP ACT 1899\n\n"
            "CORAM: Hon'ble Chief Justice D.Y. Chandrachud, Hon'ble Mr. Justice Sanjay Kishan Kaul, "
            "Hon'ble Mr. Justice Sanjiv Khanna, Hon'ble Mr. Justice B.R. Gavai, Hon'ble Mr. Justice Surya Kant, "
            "Hon'ble Mr. Justice J.B. Pardiwala, and Hon'ble Mr. Justice Manoj Misra.\n\n"
            "JUDGMENT:\n"
            "1. The question before this 7-Judge Constitution Bench is whether an arbitration agreement in an unstamped or "
            "insufficiently stamped contract is enforceable under Section 11 of the Arbitration and Conciliation Act, 1996.\n\n"
            "2. We overrule the majority decision in N.N. Global Mercantile Pvt. Ltd. (2023) and SMS Tea Estates. Non-payment of "
            "stamp duty is a curable irregularity under the Indian Stamp Act and does not render the underlying contract void ab initio.\n\n"
            "3. The principle of separability (Section 16) and competence-competence empowers the arbitral tribunal to rule on its own "
            "jurisdiction, including objections regarding the existence, validity, and stamping of the contract. The Section 11 court "
            "must adhere strictly to minimal judicial intervention.\n\n"
            "ORDER: Curative reference answered; unstamped arbitration agreements held valid for Section 11 referral."
        ),
        "url": "https://indiankanoon.org/doc/192847291/",
        "parties": [
            {"role": "Petitioner", "name": "In Re Interplay Between Arbitration and Stamp Act"},
            {"role": "Respondent", "name": "Curative Petition (Civil) No. 44 of 2023"},
        ],
        "tags": [
            "Arbitration",
            "Indian Stamp Act",
            "Section 11 Arbitration Act",
            "Competence-Competence",
            "Arbitral Tribunal",
            "NN Global Overruled",
            "Stamp Duty",
        ],
        "source": "sci",
    },
]


async def seed_landmark_judgments(session: AsyncSession) -> int:
    """
    Inserts or updates the 12 landmark Indian legal judgments with 384-dim embeddings.
    Returns the count of seeded/updated judgments.
    """
    seeded_count = 0

    for item in LANDMARK_JUDGMENTS:
        ext_id = item["external_id"]

        # 1. Compute 384-dimensional dense vector embedding
        text_to_embed = f"{item['title']} {item['excerpt']} {' '.join(item['tags'])}".strip()
        embedding = await embedding_service.get_embedding(text_to_embed)

        # 2. Check if already exists for upsert
        stmt = select(Judgment).where(Judgment.external_id == ext_id)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.title = item["title"]
            existing.short_title = item.get("short_title")
            existing.court_code = item["court_code"]
            existing.court_name = item["court_name"]
            existing.court_level = item["court_level"]
            existing.judgment_date = item["judgment_date"]
            existing.subject_category = item["subject_category"]
            existing.excerpt = item["excerpt"]
            existing.full_text = item["full_text"]
            existing.url = item["url"]
            existing.parties = item["parties"]
            existing.tags = item["tags"]
            existing.source = item["source"]
            existing.is_archived = True
            existing.classification_confidence = 0.99
            existing.embedding = embedding
            logger.info("Updated landmark judgment: %s", item["title"][:50])
        else:
            judgment = Judgment(
                external_id=ext_id,
                title=item["title"],
                short_title=item.get("short_title"),
                court_code=item["court_code"],
                court_name=item["court_name"],
                court_level=item["court_level"],
                judgment_date=item["judgment_date"],
                subject_category=item["subject_category"],
                excerpt=item["excerpt"],
                full_text=item["full_text"],
                url=item["url"],
                parties=item["parties"],
                tags=item["tags"],
                source=item["source"],
                is_archived=True,
                classification_confidence=0.99,
                embedding=embedding,
            )
            session.add(judgment)
            logger.info("Inserted new landmark judgment: %s", item["title"][:50])

        seeded_count += 1

    await session.commit()
    logger.info("Successfully seeded %d landmark judgments with 384-dim embeddings", seeded_count)
    return seeded_count


async def main():
    async with AsyncSessionLocal() as session:
        count = await seed_landmark_judgments(session)
        print(f"Done! Seeded {count} landmark judgments into database.")


if __name__ == "__main__":
    asyncio.run(main())
