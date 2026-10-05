"""Generate parameter-aligned synthetic and curated dataset for job fraud detection.

Aligns directly with the detection parameters used across HireShield-AI:
1. Financial Signals:
   - Upfront registration, interview, BGV, training, and uniform fees
   - Laptop / hardware caution deposits & gate pass charges
   - Cashier's check / mobile check deposit equipment scams
   - Prepaid task, YouTube rating, Google Maps review, & crypto USDT traps
   - Direct personal UPI handles (@okaxis, @paytm, @ybl)
2. Recruiter Verification:
   - Unsolicited WhatsApp / Telegram direct hiring with no interview
   - Enterprise MNC impersonation using free webmail (@gmail.com, @yahoo.com)
   - Spot offers and extreme urgency pressure
3. Contractual Traps:
   - Mandatory submission of original academic certificates
   - Signed blank cheque submission as bond guarantee
   - Service bond penalty clauses and withheld salary
4. Low Barrier Tropes:
   - 10th/12th pass, zero experience, ₹40k+/month for typing / captcha / copy paste
   - Mandatory purchase of software license keys or portal credentials
5. Legitimate Counterparts:
   - Real tech startups, YC companies, AI/ML engineering, full-stack roles
   - Legitimate MNC listings (TCS, Infosys, Wipro, Google, Amazon, Deloitte)
   - Legitimate customer support (Teleperformance, Concentrix) & paid internships
   - Postings with explicit anti-fraud disclaimers ("we never ask for fees")
"""

from __future__ import annotations

import json
import random
from pathlib import Path

random.seed(42)

OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "parameter_based_job_postings.json"

DATA: list[dict] = []


def add(
    title: str = "",
    company_profile: str = "",
    description: str = "",
    requirements: str = "",
    benefits: str = "",
    fraudulent: int = 0,
    parameter_tag: str = "",
    **kwargs,
):
    comp = company_profile or kwargs.get("company", "")
    desc = description or kwargs.get("desc", "")
    req = requirements or kwargs.get("req", "")
    fraud = fraudulent if "fraudulent" in kwargs or fraudulent != 0 else kwargs.get("fraud", 0)
    tag = parameter_tag or kwargs.get("tag", "")

    DATA.append({
        "title": title,
        "company_profile": comp,
        "description": desc,
        "requirements": req,
        "benefits": benefits,
        "fraudulent": int(fraud),
        "parameter_tag": tag,
    })


# ==============================================================================
# 1. FINANCIAL SIGNALS: ADVANCE FEES, DEPOSITS, GATE PASS, UNIFORM (FRAUD = 1)
# ==============================================================================
fee_companies = [
    "AeroFly Ground Handling Services", "Tata Tech Recruitment Hub Partner", "Reliance Retail Logistics Partner",
    "Apex Aviation Security Solutions", "Metro Cargo Dispatch Services", "QuickServe Retail Operations",
    "Universal Facilities & Security", "National Health Staffing Agency", "Skylark Airport Ground Staff",
    "Nexus Tech Solutions India", "Frontier Data Processing Centre", "Global BPO Workforce Solutions"
]
fee_roles = [
    ("Airport Ground Support Associate", "aviation_ground"),
    ("Customer Care Trainee", "bpo_trainee"),
    ("Billing & Inventory Clerk", "retail_billing"),
    ("Corporate Security Supervisor", "security_gate"),
    ("Airlines Baggage Handling Executive", "airport_baggage"),
    ("Railway Reservation Assistant", "rail_assist"),
    ("Hospital Records Clerk", "hospital_clerk"),
    ("Warehouse Operations Executive", "warehouse_exec"),
]
fee_scenarios = [
    ("RFID Gate Pass & Background Verification Kit Fee", "Candidates selected must deposit a refundable fee of ₹2,450 for digital RFID access card and police BGV processing. Transfer via Google Pay or PhonePe to hr.gatepass@okaxis and submit transaction ID."),
    ("Laptop Security Caution Deposit", "A company-configured Dell Latitude laptop will be dispatched. Candidate must submit a 100% refundable security deposit of ₹3,500 prior to courier dispatch. Refundable in the first payroll slip."),
    ("Mandatory Corporate Uniform & Induction Charge", "To maintain corporate standards, selected candidates must pay ₹1,850 for uniform stitching, ID lanyard, and training material kit. Pay to onboarding.desk@paytm."),
    ("Hardware Shipping & Courier Insurance Charge", "Your remote IT workstation package is prepared at our central warehouse. To insure transit, please transfer ₹1,999 shipping insurance fee to logistics.dept@ybl."),
    ("Registration & Interview Slot Booking Charge", "Due to high volume of applicants, a mandatory slot confirmation fee of ₹950 is required. Walk-in token will only be generated after receipt verification."),
    ("Medical Examination & Fitness Certificate Charge", "Pre-employment medical fitness clearance is compulsory. Transfer ₹1,650 for accredited diagnostic kit testing to medical.hr@okicici."),
]

for comp in fee_companies:
    for (role, r_tag), (fee_title, fee_clause) in zip(fee_roles, fee_scenarios):
        add(
            title=f"{role} - {fee_title}",
            company=comp,
            description=(
                f"We are hiring for the position of {role} across major regional hubs. "
                f"Responsibilities include managing daily operations, logging customer entries, and coordinating with shift leaders. "
                f"Monthly salary: ₹26,000 to ₹34,000 with PF and overtime allowance. "
                f"{fee_clause} Urgent joining within 48 hours."
            ),
            requirements="10th, 12th or any graduate. Basic English or Hindi communication. Immediate joining required.",
            benefits="Monthly incentives, shift allowances, medical coverage after confirmation.",
            fraud=1,
            tag="financial_advance_fee",
        )


# ==============================================================================
# 2. FINANCIAL SIGNALS: CASHIER'S CHECK & REIMBURSEMENT EQUIPMENT SCAM (FRAUD = 1)
# ==============================================================================
check_companies = [
    "Summit Peak Global Consulting Inc", "Vanguard Health Logistics LLC", "Horizon Biopharma Solutions",
    "Pinnacle Asset Management Group", "Beacon Strategic Advisors Inc", "Titan Energy Solutions Corp",
    "Silverline Financial Advisory", "Crestwood Digital Media LLC", "BlueStone Global Logistics"
]
check_roles = [
    "Remote Executive Administrative Assistant", "US Remote Data Entry Specialist",
    "Virtual Project Coordinator", "Remote Medical Records Billing Specialist",
    "Remote Customer Experience Representative", "Executive Operations Assistant",
]

for i, comp in enumerate(check_companies):
    for j, role in enumerate(check_roles):
        amount = random.choice(["$3,850", "$4,200", "$4,650", "$5,200"])
        hourly = random.choice(["$36.50", "$38.00", "$42.50", "$45.00"])
        add(
            title=f"{role} (100% Work from Home) - Equipment Check Provided",
            company=comp,
            description=(
                f"{comp} is actively seeking a dependable {role} to support our expanding executive team. "
                f"Compensation is {hourly} per hour on a W-2/1099 contract with comprehensive medical and dental benefits. "
                f"You will coordinate schedules, manage digital spreadsheets, and prepare weekly reports. "
                f"Upon acceptance of our offer letter, our finance department will issue an official cashier's check of {amount} "
                f"drawn on our corporate account. You must deposit this check into your personal bank account via mobile deposit, "
                f"deduct your first week's sign-on bonus of $500, and immediately wire the remaining balance to our certified hardware vendor "
                f"portal via Zelle, wire transfer, or Venmo to release your Apple MacBook Pro, encrypted workstation, and dual-monitor setup."
            ),
            requirements="Must have active checking account capable of mobile check deposit within 24 hours. Good typing speed, dependable internet connection.",
            benefits=f"{hourly}/hr, 401(k) matching, health and vision insurance, paid home workstation stipend.",
            fraud=1,
            tag="financial_check_reimbursement",
        )


# ==============================================================================
# 3. FINANCIAL SIGNALS: PREPAID TASKS, YOUTUBE/MAPS RATINGS & CRYPTO TRAPS (FRAUD = 1)
# ==============================================================================
task_schemes = [
    ("YouTube Video Like & Subscribe Partner", "Earn ₹3,000 - ₹5,000 daily by simply watching, liking YouTube videos and subscribing to creator channels. Payouts credited after every 3 completed screenshots via UPI or Paytm."),
    ("Google Maps 5-Star Rating Assistant", "Part-time work from home on mobile. Review restaurants and hotels on Google Maps. Earn ₹80 per review. Daily payout directly to your GPay / PhonePe. Join our mentor group on Telegram @maps_review_tasks."),
    ("Binance VIP Quantitative Task Force", "Execute algorithmic rating and cryptocurrency buy-sell arbitrage orders. Level 1 trial: recharge 200 USDT to earn 260 USDT within 20 minutes. Withdrawals guaranteed to your Trust Wallet or Binance account."),
    ("E-Commerce Order Volume Boost Associate", "Help merchant stores boost sales rankings on Amazon & Flipkart by placing mock prepaid orders. Recharge your platform balance to unlock VIP task commission tiers up to 35% commission."),
    ("Instagram Creator Engagement Executive", "Follow designated celebrity profiles and like promotional posts. Simple 1-2 hours work from phone. Instant commission transfer to UPI handle after every 5 tasks."),
    ("App Store Application Testing & Rating Task", "Download listed apps and submit positive 5-star ratings. Daily payout ₹2,500 to ₹4,500. To activate high-tier payouts, a refundable security recharge of ₹1,000 is required."),
]

for title, desc in task_schemes:
    for variant in range(4):
        payout = random.choice(["₹2,500 - ₹5,000 daily", "₹3,500 daily guaranteed", "150 - 300 USDT daily"])
        add(
            title=f"{title} - Part Time Remote (Variant {variant + 1})",
            company="Global Social Media Task Optimization Network",
            description=(
                f"{desc} Daily income: {payout}. No technical background or interview needed. "
                f"Contact task manager directly on Telegram or WhatsApp to get your unique worker ID and task recharge link."
            ),
            requirements="Smartphone with internet connection, active Telegram account, UPI ID or crypto wallet address.",
            benefits=f"Daily payout, instant withdrawal, high commission tiers, flexible working hours anytime.",
            fraud=1,
            tag="financial_task_crypto",
        )


# ==============================================================================
# 4. RECRUITER VERIFICATION: UNSOLICITED WHATSAPP & TELEGRAM RECRUITMENT (FRAUD = 1)
# ==============================================================================
enterprise_brands = [
    ("Amazon India Recruitment", "Amazon Customer Support Associate"),
    ("Flipkart Logistics Operations", "Flipkart Operations Executive"),
    ("Tata Consultancy Services", "TCS Back Office Data Specialist"),
    ("Infosys BPM Careers", "Infosys Process Associate"),
    ("Wipro BPO Hub", "Wipro Voice & Non-Voice Executive"),
    ("Reliance Digital Retail", "Reliance Customer Relationship Associate"),
]
whatsapp_numbers = ["+91 9823411223", "+91 9711223344", "+91 8800112233", "+91 9988776655", "+91 7011223344"]

for brand, role in enterprise_brands:
    for num in whatsapp_numbers:
        add(
            title=f"Urgent Requirement: {role} (Direct WhatsApp Selection)",
            company=brand,
            description=(
                f"Dear Job Seeker, Your profile has been shortlisted on Naukri / Monster for {role} at {brand}. "
                f"Monthly salary: ₹32,000 - ₹45,000 + ₹3,000 monthly attendance bonus. "
                f"No formal written test or technical interview. Direct selection based on resume screening. "
                f"To confirm your hiring slot and collect your offer letter today, send your resume directly to our Senior HR Manager on WhatsApp: {num}. "
                f"Limited vacancies available. Hurry up!"
            ),
            requirements="12th pass, Any degree, Freshers eligible. Laptop or mobile phone required.",
            benefits="Work from home, 5 day week, annual bonus, corporate benefits.",
            fraud=1,
            tag="recruiter_unsolicited_whatsapp_telegram",
        )


# ==============================================================================
# 5. RECRUITER VERIFICATION: ENTERPRISE IMPERSONATION VIA FREE WEBMAIL (FRAUD = 1)
# ==============================================================================
mnc_names = ["Google India", "Microsoft Corporation", "Tata Consultancy Services", "Infosys", "Deloitte India", "Amazon Web Services"]
free_domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "rediffmail.com"]

for mnc in mnc_names:
    for domain in free_domains:
        fake_email = f"careers.{mnc.lower().replace(' ', '')}2024@{domain}"
        upi_vpa = f"recruitment.{mnc.lower().replace(' ', '')[:6]}@okaxis"
        add(
            title=f"Official Offer Letter: Associate Analyst - {mnc}",
            company=f"{mnc} Human Capital Management Partner",
            description=(
                f"Congratulations! Based on your credentials, {mnc} is pleased to offer you the position of Associate Analyst. "
                f"Annual CTC: ₹7,20,000 per annum. Orientation and onboarding commence next Monday at our regional headquarters. "
                f"Please reply with your acceptance to our recruitment desk at {fake_email}. "
                f"Note: As per corporate compliance policy, candidates must complete biometric identity registration by remitting ₹2,100 to our verification coordinator at UPI handle {upi_vpa}."
            ),
            requirements="Bachelor's degree in Engineering, Science, or Commerce. Immediate acceptance required.",
            benefits="Health insurance, relocation assistance, provident fund, corporate transport.",
            fraud=1,
            tag="recruiter_enterprise_webmail",
        )


# ==============================================================================
# 6. CONTRACTUAL TRAPS: CERTIFICATES, BLANK CHEQUES & EXTREME BONDS (FRAUD = 1)
# ==============================================================================
bond_companies = [
    "Apex Tech Infra Pvt Ltd", "Zenith Software Development Hub", "Quantum IT Solutions Hyderabad",
    "Paramount Infotech Pune", "Vanguard Systems Bangalore", "Matrix Cloud Technologies Chennai"
]
bond_roles = ["Junior Software Developer", "Trainee QA Engineer", "Graduate Technical Associate", "Full Stack Intern"]

for comp in bond_companies:
    for role in bond_roles:
        penalty = random.choice(["₹1,50,000", "₹2,00,000", "₹2,50,000", "₹3,00,000"])
        add(
            title=f"{role} - Mandatory Service Agreement & Retention Policy",
            company=comp,
            description=(
                f"We are hiring a {role} to work on mission-critical client projects. "
                f"Salary during training: ₹14,000/month; after 6 months: ₹28,000/month. "
                f"Conditions of Employment: Candidate must execute a mandatory 3-year service bond agreement with a breach penalty clause of {penalty}. "
                f"Furthermore, candidate must submit original educational certificates (10th, 12th, and Degree marksheets) and two signed blank cheques "
                f"at the time of document verification. 20% of monthly salary will be withheld for the first 6 months as security deposit."
            ),
            requirements="B.Tech, BCA, MCA, or B.Sc IT. Agreement to certificate submission and service bond terms.",
            benefits="Training on live projects, experience certificate on completion of full 3-year term.",
            fraud=1,
            tag="contractual_bond_certificate",
        )


# ==============================================================================
# 7. LOW BARRIER TROPES: TYPING, CAPTCHA, FORM FILLING & SOFTWARE KEYS (FRAUD = 1)
# ==============================================================================
typing_scenarios = [
    ("Offline Document Typing & Captcha Entry Job", "Earn ₹25,000 - ₹40,000 per month typing PDF documents into Word format. Simple copy paste work. Earn ₹40 per page. Work 2-3 hours daily from home. Candidates must purchase licensed typing software utility key for ₹1,299 which will be reimbursed with your first weekly payout."),
    ("Online Form Filling & SMS Sending Project", "Simple part time online job. Fill 100 forms daily and earn ₹1,500 daily. No technical skills required. 10th pass or 12th pass can apply. To activate user credentials on the client portal, pay one-time server registration charge of ₹850 via UPI."),
    ("Medical Transcription & Audio Typing Trainee", "Listen to audio recordings and type text. High daily income guaranteed. Zero interview. Work anytime from home. Requires purchase of authorized transcription audio codec license for ₹1,800."),
    ("Student & Housewife Part-Time Copy Paste Job", "Guaranteed daily payout ₹1,800 - ₹3,200. No experience, no resume, spot joining. Pay ₹650 portal activation charge to begin receiving daily assignments immediately."),
]

for title, desc in typing_scenarios:
    for v in range(6):
        add(
            title=f"{title} (Batch #{v + 1})",
            company="Digital Content Typing Solutions Hub",
            description=desc,
            requirements="Basic computer knowledge, laptop/PC or Android smartphone, internet connection.",
            benefits="Daily / weekly bank transfer, flexible working hours, unlimited workload.",
            fraud=1,
            tag="low_barrier_typing_software",
        )


# ==============================================================================
# 8. LEGITIMATE TECH STARTUPS & MODERN ROLES (FRAUD = 0)
# ==============================================================================
startup_companies = [
    ("PromptEngine AI (YC W24)", "PromptEngine AI is building synthetic data generation pipelines for frontier reasoning models. Backed by Y Combinator and top Silicon Valley angels."),
    ("VectorScale Technologies", "VectorScale is an open-source distributed vector database company serving real-time semantic search applications for high-scale enterprise workloads."),
    ("DevPulse Systems", "DevPulse builds developer observability and continuous profiling tools for Kubernetes microservices. Series A funded with a remote-first culture across India and the US."),
    ("NeuroMesh Labs", "NeuroMesh is a seed-stage applied AI startup building multimodal medical imaging diagnostics tools for radiologists."),
    ("CloudForge Data", "CloudForge is an infrastructure platform simplifying real-time stream processing on Apache Flink and Kafka."),
    ("AuthArmor Cyber", "AuthArmor provides modern identity verification and passwordless authentication APIs for fintech and banking clients."),
]
startup_roles = [
    ("Senior Full Stack Engineer (React + FastAPI)", "Python, FastAPI, TypeScript, React, PostgreSQL, Docker, AWS. 4+ years shipping production web applications. Competitive salary + 0.25%-0.75% equity."),
    ("AI / LLM Research Engineer", "PyTorch, HuggingFace, vLLM, RLHF, CUDA kernels. Strong background in fine-tuning open-weights models (Llama, Mistral). Competitive salary + equity."),
    ("DevOps & Platform Engineer", "Terraform, Kubernetes, GitHub Actions, AWS/GCP, Prometheus, Datadog. Experience with multi-tenant cloud architecture. Competitive salary + equity."),
    ("Product Designer (UI/UX)", "Figma, design systems, user research, rapid prototyping. Portfolio demonstrating complex SaaS workflows. Competitive salary + equity."),
    ("Technical Support Specialist (Remote)", "SQL, REST APIs, debugging client integrations, writing developer docs. Excellent written English communication. Competitive salary + health insurance."),
]

for comp_name, comp_prof in startup_companies:
    for role_title, tech_desc in startup_roles:
        add(
            title=f"{role_title} - Remote / Hybrid",
            company=comp_name,
            description=(
                f"{comp_prof} We are hiring a {role_title} to join our core engineering squad. "
                f"You will take full ownership of features from architectural design to deployment. "
                f"Tech stack & focus: {tech_desc}. "
                f"Our hiring process consists of a 30-min intro chat, a practical code pairing exercise, and an architecture deep dive. "
                f"We never ask candidates for fees or deposits. A $2,000 remote equipment budget and health insurance are provided upon joining."
            ),
            requirements=f"Strong problem solving, clear communication, collaborative mindset. {tech_desc}",
            benefits="Competitive compensation, early-stage equity (ESOPs), flexible remote work, comprehensive health coverage, equipment stipend.",
            fraud=0,
            tag="legitimate_startup_tech",
        )


# ==============================================================================
# 9. LEGITIMATE ENTERPRISE & MNC LISTINGS (FRAUD = 0)
# ==============================================================================
mnc_legit = [
    ("Tata Consultancy Services (TCS)", "TCS is a global leader in IT services, consulting, and business solutions with over 600,000 consultants worldwide.", "tcs.com/careers"),
    ("Infosys Limited", "Infosys is a global leader in next-generation digital services and consulting operating in over 56 countries.", "infosys.com/careers"),
    ("Wipro Limited", "Wipro Limited is a leading technology services and consulting company focused on building innovative solutions.", "wipro.com/careers"),
    ("Google India", "Google's mission is to organize the world's information and make it universally accessible and useful.", "google.com/about/careers"),
    ("Microsoft India Development Centre", "Microsoft enables digital transformation for the era of an intelligent cloud and an intelligent edge.", "careers.microsoft.com"),
    ("Amazon India", "Amazon is guided by four principles: customer obsession, passion for invention, commitment to operational excellence, and long-term thinking.", "amazon.jobs"),
    ("Deloitte Touche Tohmatsu India", "Deloitte provides industry-leading audit, consulting, tax, and advisory services to many of the world's most admired brands.", "deloitte.com/careers"),
    ("Reliance Industries Limited", "Reliance is India's largest private sector enterprise with businesses across energy, retail, telecom, and digital services.", "ril.com/careers"),
]
mnc_legit_roles = [
    ("Systems Engineer", "Bachelor of Engineering / B.Tech in CS/IT/ECE. Hands-on coding in Java, Python, or C#. Strong fundamental knowledge of OOP, DBMS, and data structures. Formal written test on portal followed by technical and HR interview."),
    ("Cloud Infrastructure Architect", "8+ years in enterprise cloud migration, Azure/AWS architecture, microservices, and containerization. Excellent stakeholder management skills."),
    ("Senior Software Development Engineer (SDE-II)", "5+ years building highly available distributed systems. Deep knowledge of concurrency, caching, relational and NoSQL databases. Multi-round system design and coding evaluation."),
    ("Data Analyst - Global Business Operations", "Strong SQL, Power BI / Tableau, Python data analysis (pandas/numpy). Experience in exploratory data analysis, business metric forecasting, and executive reporting."),
]

for comp_name, comp_prof, career_url in mnc_legit:
    for role_title, role_spec in mnc_legit_roles:
        add(
            title=f"{role_title} - {comp_name}",
            company=comp_name,
            description=(
                f"{comp_prof} We are currently looking for qualified professionals for the role of {role_title}. "
                f"Responsibilities: Deliver high-quality engineering solutions, participate in sprint planning, code reviews, and cross-functional design discussions. "
                f"Qualifications: {role_spec} "
                f"NOTICE: {comp_name} does not charge any fee or deposit at any stage of the recruitment process. "
                f"All official applications must be submitted directly via our official careers portal at {career_url}. "
                f"Official communication is conducted strictly through our verified corporate domain."
            ),
            requirements=f"{role_spec} Clear communication and team collaboration skills.",
            benefits="Provident Fund (EPF), Gratuity, comprehensive medical insurance for family, performance bonus, paid time off, education reimbursement.",
            fraud=0,
            tag="legitimate_mnc_enterprise",
        )


# ==============================================================================
# 10. LEGITIMATE CUSTOMER OPERATIONS, BPO & INTERNSHIPS (FRAUD = 0)
# ==============================================================================
bpo_legit = [
    ("Teleperformance India", "Teleperformance is a global digital business services company connecting the world's biggest brands with their customers."),
    ("Concentrix Services India", "Concentrix is a leading global provider of customer experience solutions and technology."),
    ("Genpact India", "Genpact is a global professional services and solutions firm delivering outcomes that shape the future."),
]
bpo_roles = [
    ("Customer Support Associate (Voice / Semi-Voice)", "Handling inbound customer queries via phone and chat, resolving order issues, updating CRM records. Shift: 5 days working with rotational week-offs. Salary: ₹22,000 - ₹30,000/month + incentives."),
    ("Technical Support Representative", "Troubleshooting hardware/software issues for enterprise SaaS products. Excellent written English communication. Shift allowance and cab facilities provided."),
    ("Operations Trainee (Freshers Eligible)", "Processing digital documentation, verifying transactional records, ensuring SLA compliance. Comprehensive paid training provided by company upon joining."),
]

for bpo, prof in bpo_legit:
    for role, desc in bpo_roles:
        add(
            title=f"{role} - {bpo}",
            company=bpo,
            description=(
                f"{prof} We are hiring candidates for our customer operations team in Gurgaon, Noida, Hyderabad, and Bangalore. "
                f"Job Details: {desc} "
                f"Hiring Process: Walk-in or virtual HR interview, voice assessment round, and operational briefing. "
                f"Anti-Fraud Notice: {bpo} is an equal opportunity employer and maintains a strict zero-fee recruitment policy. "
                f"We never request candidates to pay registration fees, security deposits, or uniform charges."
            ),
            requirements="Graduate or 12th pass with good communication skills. Basic computer literacy.",
            benefits="Free corporate transport (cab facility), health insurance, subsidized cafeteria, monthly performance incentives.",
            fraud=0,
            tag="legitimate_bpo_customer_support",
        )

# Legitimate Internships with stipends
internship_companies = ["Razorpay", "Swiggy", "Zomato", "Freshworks", "Zerodha"]
internship_roles = [
    ("Software Engineering Intern (Summer)", "Work alongside core product teams building high-throughput payment and logistics systems. Monthly stipend: ₹40,000 - ₹50,000/month. No fees or certificates withheld."),
    ("Data Science Intern", "Build predictive models and analytics dashboards. Monthly stipend: ₹35,000/month. Pre-placement offer (PPO) opportunity based on performance."),
]

for comp in internship_companies:
    for role, desc in internship_roles:
        add(
            title=f"{role} - {comp}",
            company=comp,
            description=(
                f"{comp} invites applications for our intensive 3-6 month internship program. "
                f"{desc} Mentorship from senior engineering leaders, real production impact, and modern tech stacks. "
                f"All applications must be submitted via our official careers page. Zero fees, no bond agreements."
            ),
            requirements="Enrolled in penultimate or final year of B.Tech/M.Tech/MCA/B.Sc. Strong coding and problem-solving skills.",
            benefits="Monthly stipend, company laptop provided for internship duration, certificate of completion, PPO opportunity.",
            fraud=0,
            tag="legitimate_internship",
        )

# ==============================================================================
# 11. LEGITIMATE BANKING, HEALTHCARE, MARKETING & SALES ROLES (FRAUD = 0)
# ==============================================================================
banking_legit = [
    ("HDFC Bank Limited", "HDFC Bank is one of India's leading private banks, offering a wide range of banking services across retail, wholesale, and treasury operations.", "hdfcbank.com/careers"),
    ("ICICI Bank", "ICICI Bank is a large Indian multinational bank and financial services company headquartered in Mumbai.", "icicibank.com/careers"),
    ("Axis Bank", "Axis Bank is India's third largest private sector bank, delivering full-suite financial services to individuals and corporates.", "axisbank.com/careers"),
    ("Apollo Hospitals Enterprise", "Apollo Hospitals is India's leading integrated healthcare delivery system with hospitals, pharmacies, and diagnostic clinics.", "apollohospitals.com/careers"),
    ("Zomato Limited", "Zomato is an Indian multinational restaurant aggregator and food delivery company.", "zomato.com/careers"),
    ("Swiggy (Bundl Technologies)", "Swiggy is India's leading on-demand convenience delivery platform.", "swiggy.com/careers"),
]
banking_roles = [
    ("Branch Relationship Manager", "Manage client portfolios, handle retail banking inquiries, cross-sell wealth products. 2+ years banking or financial sales experience. Standard campus or branch interview. Strictly zero charges."),
    ("Credit Risk Underwriter", "Analyze creditworthiness of corporate and retail loan applicants, verify income documentation, assess debt-to-income ratios. CA/MBA Finance. Formal assessment process."),
    ("Growth Marketing Specialist", "Manage performance marketing campaigns across Google Ads, Meta, and LinkedIn. Optimize CPA and CAC metrics. 3+ years experience."),
    ("Business Development Representative", "Identify outbound leads, schedule enterprise product demonstrations, coordinate with regional sales directors. Base salary + competitive uncapped commission."),
    ("Clinical Operations Coordinator", "Manage patient intake workflows, schedule consultations, ensure medical compliance records. B.Sc Nursing / Healthcare Admin. Formal hospital interview."),
]

for b_name, b_prof, b_url in banking_legit:
    for r_title, r_desc in banking_roles:
        add(
            title=f"{r_title} - {b_name}",
            company=b_name,
            description=(
                f"{b_prof} We are seeking a talented {r_title} to join our growing team. "
                f"Responsibilities: {r_desc} "
                f"Selection Process: Resume screening, structured competency interview, and formal background verification conducted directly by authorized HR. "
                f"SECURITY NOTICE: {b_name} never requests monetary payments, gate pass fees, or refundable deposits from candidates. "
                f"Applications must only be submitted through our verified website at {b_url}."
            ),
            requirements="Relevant bachelor's degree or professional qualification. Strong ethical standards and communication skills.",
            benefits="Provident Fund (EPF), National Pension Scheme (NPS), annual performance bonus, comprehensive medical insurance.",
            fraud=0,
            tag="legitimate_corporate_banking_healthcare",
        )


def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(DATA, f, indent=2, ensure_ascii=False)
    
    total = len(DATA)
    frauds = sum(1 for d in DATA if d["fraudulent"] == 1)
    legit = total - frauds
    print(f"[OK] Generated {total} parameter-based samples ({frauds} fraudulent, {legit} legitimate) -> {OUT_PATH}")


if __name__ == "__main__":
    main()
