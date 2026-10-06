export const mockAnalysisHighRisk = {
  id: "HS-2026-8891",
  jobTitle: "Senior Remote Data Specialist / Operations Assistant",
  company: "Apex Global Solutions Inc. (Unverified)",
  url: "https://apex-global-careers-hire.net/jobs/entry-data-spec",
  recruiterEmail: "recruitment@apex-global-hr.net",
  recruiterName: "Sarah Jenkins (Claimed HR Director)",
  scanDate: "Sept 11, 2026 • 09:15 AM",
  score: 88,
  verdict: "DON'T APPLY",
  riskLevel: "high",
  confidence: "96%",
  summary: "Critical high-risk scam indicators detected. The domain was registered only 9 days ago, recruiter uses a lookalike domain separate from the legitimate company site, and the offer document mandates an advance equipment purchase via wire transfer.",
  riskFactors: [
    {
      id: "rf-1",
      severity: "high",
      severityScore: 92,
      category: "Financial Red Flags",
      headline: "Advance Equipment Payment Requirement",
      description: "Job offer specifies candidate must transfer $1,450 for 'certified home office hardware' via vendor check reimbursement.",
      evidence: "Extracted Clause: 'The candidate will receive a check for $2,000 to purchase mandatory Apple equipment from our designated hardware portal prior to onboarding.'",
      categoryType: "accent-document"
    },
    {
      id: "rf-2",
      severity: "high",
      severityScore: 85,
      category: "URL & Domain Safety",
      headline: "Newly Registered Lookalike Domain",
      description: "Domain apex-global-careers-hire.net was created 9 days ago with anonymized registrar details.",
      evidence: "WHOIS Registry: Created on Sep 02, 2026. Official firm operates on apex-global.com (Registered 2011).",
      categoryType: "accent-url"
    },
    {
      id: "rf-3",
      severity: "moderate",
      severityScore: 68,
      category: "Recruiter Identity",
      headline: "Unverified Recruiter Profile & Chat Channel",
      description: "Recruiter conducted entire interview via Telegram messaging app with no video confirmation.",
      evidence: "Channel Check: Recruiter email domain @apex-global-hr.net fails SPF/DKIM verification against parent entity.",
      categoryType: "accent-recruiter"
    },
    {
      id: "rf-4",
      severity: "low",
      severityScore: 12,
      category: "Linguistic Patterns",
      headline: "Professional Job Description Formatting",
      description: "Syntactic structure and job responsibilities match standard technical operations templates.",
      evidence: "NLP Analysis: 94% grammatical accuracy, standard corporate phrasing detected.",
      categoryType: "accent-document"
    }
  ],
  matrix: [
    {
      checkName: "Corporate Domain Legitimacy",
      status: "FAIL",
      explanation: "Domain registered <10 days ago with privacy shield.",
      evidenceFooter: "Mismatch: apex-global-careers-hire.net vs apex-global.com"
    },
    {
      checkName: "Recruiter Identity & Auth",
      status: "FAIL",
      explanation: "Email domain fails MX records & corporate directory match.",
      evidenceFooter: "Email sender domain differs from registered business"
    },
    {
      checkName: "State Business Registration",
      status: "CAUTION",
      explanation: "Similar corporate entity exists in Delaware, but HQ address conflicts.",
      evidenceFooter: "SOS DB Match: Apex Global (DE) active since 2018"
    },
    {
      checkName: "Payment & Fee Clause",
      status: "FAIL",
      explanation: "Includes advance check equipment purchase clause.",
      evidenceFooter: "Classic check fraud pattern detected in PDF"
    },
    {
      checkName: "Official Careers Page Match",
      status: "FAIL",
      explanation: "Listing absent from official verified careers page.",
      evidenceFooter: "Index scan on apex-global.com/careers returned 0 matches"
    },
    {
      checkName: "Salary & Compensation Range",
      status: "CAUTION",
      explanation: "$65/hr for entry data entry is 180% above market median.",
      evidenceFooter: "BLS Median: $24.50/hr for comparable titles"
    }
  ]
};

export const mockAnalysisModerateRisk = {
  id: "HS-2026-5240",
  jobTitle: "Junior Financial Analyst (Contract)",
  company: "Vanguard Tech Partners",
  url: "https://vanguardtech-recruiting.com/jobs/fin-analyst",
  recruiterEmail: "m.roberts@vanguardtech-recruiting.com",
  recruiterName: "Mark Roberts (Third-Party Talent Recruiter)",
  scanDate: "Sept 10, 2026 • 02:40 PM",
  score: 52,
  verdict: "HOLD",
  riskLevel: "moderate",
  confidence: "89%",
  summary: "Proceed with caution. The hiring company is an independent third-party recruitment agency, but compensation is significantly above industry standards and the interview process was conducted solely over chat.",
  riskFactors: [
    {
      id: "rf-m1",
      severity: "moderate",
      severityScore: 58,
      category: "Recruiter Identity",
      headline: "Third-Party Staffing Agency Representation",
      description: "Recruiter represents an agency, not the end client company.",
      evidence: "Entity Verification: Domain belongs to Vanguard Recruiting LLC (Registered 2022).",
      categoryType: "accent-recruiter"
    },
    {
      id: "rf-m2",
      severity: "moderate",
      severityScore: 54,
      category: "Linguistic Patterns",
      headline: "Urgency Language & Short Response Deadline",
      description: "Offer contains language pressing for acceptance within 12 hours.",
      evidence: "Extracted Text: 'Must sign offer within 12 hours or position will be re-assigned.'",
      categoryType: "accent-document"
    },
    {
      id: "rf-m3",
      severity: "low",
      severityScore: 5,
      category: "URL & Domain Safety",
      headline: "Valid Domain SSL & Registered Business",
      description: "Website has valid SSL certificate and clean Google Safe Browsing record.",
      evidence: "Security Check: SSL Issuer DigiCert, 0 blacklists reported.",
      categoryType: "accent-url"
    }
  ],
  matrix: [
    {
      checkName: "Corporate Domain Legitimacy",
      status: "PASS",
      explanation: "Domain registered 4 years ago with valid SSL.",
      evidenceFooter: "Domain age: 4 years 2 months"
    },
    {
      checkName: "Recruiter Identity & Auth",
      status: "CAUTION",
      explanation: "LinkedIn profile active, but missing mutual network verification.",
      evidenceFooter: "Agency profile verified on LinkedIn"
    },
    {
      checkName: "State Business Registration",
      status: "PASS",
      explanation: "Registered LLC in Texas with active standing.",
      evidenceFooter: "TX Secretary of State: Active LLC"
    },
    {
      checkName: "Payment & Fee Clause",
      status: "PASS",
      explanation: "No payment or equipment purchase requests found.",
      evidenceFooter: "Standard W-2 contract language"
    },
    {
      checkName: "Official Careers Page Match",
      status: "CAUTION",
      explanation: "Agency listing; direct client name obscured.",
      evidenceFooter: "Client confidentiality clause cited"
    },
    {
      checkName: "Salary & Compensation Range",
      status: "CAUTION",
      explanation: "$48/hr contract rate is 35% above regional average.",
      evidenceFooter: "High range for entry-level title"
    }
  ]
};

export const mockAnalysisLowRisk = {
  id: "HS-2026-1205",
  jobTitle: "Software Engineer Intern (Summer 2026)",
  company: "Stripe, Inc.",
  url: "https://stripe.com/jobs/listing/software-engineer-intern",
  recruiterEmail: "university-hiring@stripe.com",
  recruiterName: "Elena Rostova (University Recruiting)",
  scanDate: "Sept 11, 2026 • 08:30 AM",
  score: 12,
  verdict: "APPLY",
  riskLevel: "low",
  confidence: "99%",
  summary: "Verified legitimate opportunity. 100% verified domain matching official corporate records, recruiter email authenticated via SPF/DKIM, official university recruiting pipeline.",
  riskFactors: [
    {
      id: "rf-l1",
      severity: "low",
      severityScore: 2,
      category: "Company Verification",
      headline: "Verified Corporate Entity & Official Domain",
      description: "Direct match with official stripe.com primary corporate domain.",
      evidence: "Verified SSL: Stripe, Inc. [US] • Primary domain verified.",
      categoryType: "accent-recruiter"
    },
    {
      id: "rf-l2",
      severity: "low",
      severityScore: 4,
      category: "Recruiter Identity",
      headline: "Authenticated Recruiter Credentials",
      description: "Recruiter email passes strict DMARC, SPF, and corporate directory cross-check.",
      evidence: "Email Auth: PASS (DMARC strict policy enforced by stripe.com).",
      categoryType: "accent-recruiter"
    },
    {
      id: "rf-l3",
      severity: "low",
      severityScore: 0,
      category: "Document & Fee Safety",
      headline: "No Financial Red Flags",
      description: "Zero fees, no upfront payments, standard university recruiting process.",
      evidence: "Policy Match: Aligns 100% with standard enterprise hiring practices.",
      categoryType: "accent-document"
    }
  ],
  matrix: [
    {
      checkName: "Corporate Domain Legitimacy",
      status: "PASS",
      explanation: "Official primary domain with Enterprise SSL.",
      evidenceFooter: "stripe.com verified since 2010"
    },
    {
      checkName: "Recruiter Identity & Auth",
      status: "PASS",
      explanation: "Verified Stripe corporate employee email.",
      evidenceFooter: "SPF / DKIM / DMARC verified"
    },
    {
      checkName: "State Business Registration",
      status: "PASS",
      explanation: "Delaware Corporation in Good Standing.",
      evidenceFooter: "DE Corp ID: 4729105"
    },
    {
      checkName: "Payment & Fee Clause",
      status: "PASS",
      explanation: "No advance payment or check clauses.",
      evidenceFooter: "Clean compensation breakdown"
    },
    {
      checkName: "Official Careers Page Match",
      status: "PASS",
      explanation: "Direct listing on official stripe.com/jobs board.",
      evidenceFooter: "Job ID: SR-INT-2026"
    },
    {
      checkName: "Salary & Compensation Range",
      status: "PASS",
      explanation: "$55/hr intern rate matches verified tech benchmark.",
      evidenceFooter: "Glassdoor / Levels.fyi benchmark match"
    }
  ]
};

export const mockAnalysisIndiaScam = {
  id: "HS-2026-9042",
  jobTitle: "Accounts Assistant & Data Executive (MNC Placement)",
  company: "Excel Career Solutions (Unverified)",
  url: "https://excel-careers-india.in/jobs/accounts-assistant",
  recruiterEmail: "placementfee@gmail.com",
  recruiterName: "Rajesh Kumar (WhatsApp Recruiter)",
  scanDate: "Sept 18, 2026 • 09:30 PM",
  score: 94,
  verdict: "DON'T APPLY",
  riskLevel: "high",
  confidence: "98%",
  summary: "Extreme risk fake placement consultancy detected. The listing demands an advance 'refundable' security deposit / registration charge of ₹5,000, recruiter conducts onboarding exclusively via WhatsApp (+91 9812345678), and uses a free @gmail.com address.",
  riskFactors: [
    {
      id: "rf-in-1",
      severity: "high",
      severityScore: 96,
      category: "Financial Scam Signals",
      headline: "Mandatory Registration / Security Deposit Fee",
      evidence: "Extracted Clause: 'Our consultancy charges are ₹5,000 only, which is a small refundable deposit to guarantee placement.' Legitimate corporate employers never charge job-seekers placement fees.",
      categoryType: "accent-document"
    },
    {
      id: "rf-in-2",
      severity: "high",
      severityScore: 92,
      category: "Recruiter Verification",
      headline: "WhatsApp-Only Recruitment Channel & Free Webmail",
      evidence: "Channel Check: Recruiter provides free webmail (placementfee@gmail.com) and directs all communications to WhatsApp (+91 9812345678).",
      categoryType: "accent-recruiter"
    },
    {
      id: "rf-in-3",
      severity: "high",
      severityScore: 88,
      category: "Job Content Analysis (ML)",
      headline: "Statistical Fake Job Linguistic Markers",
      evidence: "ML Text Classifier detected 94.2% similarity with fraudulent Indian consultancy job posting patterns (Key signals: 'placement guarantee', 'registration fee', 'whatsapp').",
      categoryType: "accent-document"
    }
  ],
  matrix: [
    {
      checkName: "Advance Placement Fee Check",
      status: "FAIL",
      explanation: "Mandatory ₹5,000 registration fee requested.",
      evidenceFooter: "Violates ethical employment guidelines"
    },
    {
      checkName: "Corporate Email Verification",
      status: "FAIL",
      explanation: "Recruiter uses free webmail @gmail.com address.",
      evidenceFooter: "No enterprise email domain found"
    },
    {
      checkName: "WhatsApp-Only Interview Channel",
      status: "FAIL",
      explanation: "Directs applicant to WhatsApp instead of official ATS portal.",
      evidenceFooter: "WhatsApp recruitment flag"
    },
    {
      checkName: "Company Registry Check",
      status: "FAIL",
      explanation: "No active MCA CIN or verified corporate office found.",
      evidenceFooter: "MCA / Public directory scan returned 0 records"
    }
  ]
};

export const mockAnalysisTelegramScam = {
  id: "HS-2026-9721",
  jobTitle: "Remote Crypto Portfolio & Task Specialist",
  company: "Global Fast Growth Ltd",
  url: "https://global-fast-remote-jobs.site/apply",
  recruiterEmail: "hr@global-fast-remote-jobs.site",
  recruiterName: "Alex Vance (@fast_crypto_jobs)",
  scanDate: "Sept 18, 2026 • 09:40 PM",
  score: 91,
  verdict: "DON'T APPLY",
  riskLevel: "high",
  confidence: "95%",
  summary: "Critical task-investment scam detected. Guarantees $1,500/week payout for simple tasks, directs communication to anonymous Telegram bot handles, and uses a disposable .site domain.",
  riskFactors: [
    {
      id: "rf-tg-1",
      severity: "high",
      severityScore: 94,
      category: "Financial Scam Signals",
      headline: "Prepaid Task & Crypto Wallet Recharge Pattern",
      evidence: "Scam pattern: Candidate is promised $1,500 weekly payout and asked to deposit crypto to 'recharge wallet' for commission tasks.",
      categoryType: "accent-document"
    },
    {
      id: "rf-tg-2",
      severity: "high",
      severityScore: 90,
      category: "Recruiter Verification",
      headline: "Anonymous Telegram Recruiter Channel",
      evidence: "Channel Check: Recruiter operates exclusively via Telegram handle @fast_crypto_jobs with no verifiable corporate email or identity.",
      categoryType: "accent-recruiter"
    },
    {
      id: "rf-tg-3",
      severity: "high",
      severityScore: 86,
      category: "URL & Website Analysis",
      headline: "Disposable Scam TLD (.site)",
      evidence: "Domain 'global-fast-remote-jobs.site' uses high-risk low-cost disposable TLD.",
      categoryType: "accent-url"
    }
  ],
  matrix: [
    {
      checkName: "Prepaid Task Scam Check",
      status: "FAIL",
      explanation: "Promises unrealistic payouts for liking/subscribing or task recharge.",
      evidenceFooter: "Classic high-yield investment/task trap"
    },
    {
      checkName: "Telegram Channel Check",
      status: "FAIL",
      explanation: "Recruiter refuses formal interview, operates on Telegram.",
      evidenceFooter: "Anonymous handle detected"
    },
    {
      checkName: "URL & TLD Reputation",
      status: "FAIL",
      explanation: "Registered on low-reputation .site TLD.",
      evidenceFooter: "Disposable phishing host"
    }
  ]
};

export const mockHistoryList = [
  {
    id: "HS-2026-8891",
    jobTitle: "Senior Remote Data Specialist",
    title: "Senior Remote Data Specialist",
    company: "Apex Global Solutions Inc.",
    scanDate: "Sept 11, 2026",
    date: "2026-09-11",
    score: 88,
    riskScore: 88,
    verdict: "DON'T APPLY",
    recommendation: "DON'T APPLY",
    riskLevel: "high",
    type: "Job URL & PDF",
    payload: mockAnalysisHighRisk
  },
  {
    id: "HS-2026-1205",
    jobTitle: "Software Engineer Intern",
    title: "Software Engineer Intern",
    company: "Stripe, Inc.",
    scanDate: "Sept 11, 2026",
    date: "2026-09-11",
    score: 12,
    riskScore: 12,
    verdict: "APPLY",
    recommendation: "APPLY",
    riskLevel: "low",
    type: "Job URL",
    payload: mockAnalysisLowRisk
  },
  {
    id: "HS-2026-7412",
    jobTitle: "Remote Operations Assistant",
    title: "Remote Operations Assistant",
    company: "Global Logistics Hub LLC",
    scanDate: "Sept 09, 2026",
    date: "2026-09-09",
    score: 74,
    riskScore: 74,
    verdict: "DON'T APPLY",
    recommendation: "DON'T APPLY",
    riskLevel: "high",
    type: "Email Message",
    payload: {
      ...mockAnalysisHighRisk,
      id: "HS-2026-7412",
      jobTitle: "Remote Operations Assistant",
      company: "Global Logistics Hub LLC",
      score: 74,
      riskScore: 74,
      verdict: "DON'T APPLY",
      recommendation: "DON'T APPLY",
      scanDate: "Sept 09, 2026 • 11:20 AM"
    }
  },
  {
    id: "HS-2026-5240",
    jobTitle: "Junior Financial Analyst (Contract)",
    title: "Junior Financial Analyst (Contract)",
    company: "Vanguard Tech Partners",
    scanDate: "Sept 08, 2026",
    date: "2026-09-08",
    score: 52,
    riskScore: 52,
    verdict: "HOLD",
    recommendation: "HOLD",
    riskLevel: "moderate",
    type: "Pasted Description",
    payload: mockAnalysisModerateRisk
  },
  {
    id: "HS-2026-0819",
    jobTitle: "DevOps Engineer",
    title: "DevOps Engineer",
    company: "CloudScale Systems",
    scanDate: "Sept 06, 2026",
    date: "2026-09-06",
    score: 8,
    riskScore: 8,
    verdict: "APPLY",
    recommendation: "APPLY",
    riskLevel: "low",
    type: "Job URL",
    payload: {
      ...mockAnalysisLowRisk,
      id: "HS-2026-0819",
      jobTitle: "DevOps Engineer",
      company: "CloudScale Systems",
      score: 8,
      riskScore: 8,
      verdict: "APPLY",
      recommendation: "APPLY",
      scanDate: "Sept 06, 2026 • 04:15 PM"
    }
  },
  {
    id: "HS-2026-8201",
    jobTitle: "Content Marketing Lead",
    title: "Content Marketing Lead",
    company: "NextGen Media Group",
    scanDate: "Sept 04, 2026",
    date: "2026-09-04",
    score: 82,
    riskScore: 82,
    verdict: "DON'T APPLY",
    recommendation: "DON'T APPLY",
    riskLevel: "high",
    type: "Recruiter Email",
    payload: {
      ...mockAnalysisHighRisk,
      id: "HS-2026-8201",
      jobTitle: "Content Marketing Lead",
      company: "NextGen Media Group",
      score: 82,
      riskScore: 82,
      verdict: "DON'T APPLY",
      recommendation: "DON'T APPLY",
      scanDate: "Sept 04, 2026 • 01:10 PM"
    }
  },
  {
    id: "HS-2026-3844",
    jobTitle: "Research Assistant (Part-time)",
    title: "Research Assistant (Part-time)",
    company: "Innovate Bio Labs",
    scanDate: "Sept 01, 2026",
    date: "2026-09-01",
    score: 38,
    riskScore: 38,
    verdict: "HOLD",
    recommendation: "HOLD",
    riskLevel: "moderate",
    type: "Pasted Description",
    payload: {
      ...mockAnalysisModerateRisk,
      id: "HS-2026-3844",
      jobTitle: "Research Assistant (Part-time)",
      company: "Innovate Bio Labs",
      score: 38,
      riskScore: 38,
      verdict: "HOLD",
      recommendation: "HOLD",
      scanDate: "Sept 01, 2026 • 10:05 AM"
    }
  },
  {
    id: "HS-2026-0511",
    jobTitle: "Product Design Intern",
    title: "Product Design Intern",
    company: "Shopify",
    scanDate: "Aug 28, 2026",
    date: "2026-08-28",
    score: 5,
    riskScore: 5,
    verdict: "APPLY",
    recommendation: "APPLY",
    riskLevel: "low",
    type: "Job URL",
    payload: {
      ...mockAnalysisLowRisk,
      id: "HS-2026-0511",
      jobTitle: "Product Design Intern",
      company: "Shopify",
      score: 5,
      riskScore: 5,
      verdict: "APPLY",
      recommendation: "APPLY",
      scanDate: "Aug 28, 2026 • 03:50 PM"
    }
  }
];

export const mockDashboardStats = {
  totalChecks: 14,
  highRiskCaught: 3,
  safeFound: 9,
  moderateCount: 2,
  lastCheck: "2 hours ago"
};

export const mockWeeklyChartData = [
  { week: "Aug 01", highRisk: 1, moderate: 0, safe: 2 },
  { week: "Aug 08", highRisk: 0, moderate: 1, safe: 3 },
  { week: "Aug 15", highRisk: 1, moderate: 0, safe: 1 },
  { week: "Aug 22", highRisk: 0, moderate: 0, safe: 2 },
  { week: "Aug 29", highRisk: 1, moderate: 1, safe: 1 },
  { week: "Sep 05", highRisk: 2, moderate: 0, safe: 3 }
];

export const getScanCounts = (analyses = mockHistoryList) => {
  const list = Array.isArray(analyses) ? analyses : [];
  let highRisk = 0;
  let moderate = 0;
  let verifiedSafe = 0;

  list.forEach((item) => {
    const level = item.riskLevel || (item.score >= 61 ? 'high' : item.score >= 31 ? 'moderate' : 'low');
    if (level === 'high') {
      highRisk++;
    } else if (level === 'moderate') {
      moderate++;
    } else {
      verifiedSafe++;
    }
  });

  return {
    total: list.length,
    highRisk,
    moderate,
    verifiedSafe
  };
};

