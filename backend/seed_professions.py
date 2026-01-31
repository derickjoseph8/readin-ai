"""Seed database with global professions for all careers."""

from datetime import datetime
from database import SessionLocal, engine
from models import Base, Profession

# Create all tables
Base.metadata.create_all(bind=engine)

# Global professions organized by category
PROFESSIONS = [
    # ==========================================================================
    # LEGAL
    # ==========================================================================
    {
        "name": "Lawyer / Attorney",
        "category": "Legal",
        "description": "Legal professional providing advice and representation",
        "terminology": ["litigation", "deposition", "discovery", "precedent", "statute", "jurisdiction", "tort", "contract law", "due diligence", "fiduciary"],
        "common_topics": ["case strategy", "legal precedents", "client representation", "court procedures", "contracts", "compliance"],
        "system_prompt_additions": "You are assisting a legal professional. Use appropriate legal terminology. Reference relevant legal concepts when applicable. Maintain a professional, precise tone suitable for legal discussions. Be careful about liability implications.",
        "communication_style": "formal",
        "icon": "scale"
    },
    {
        "name": "Paralegal",
        "category": "Legal",
        "description": "Legal assistant supporting attorneys",
        "terminology": ["case file", "legal research", "filing", "affidavit", "subpoena", "brief", "docket"],
        "common_topics": ["case preparation", "document review", "legal research", "client communication"],
        "system_prompt_additions": "You are assisting a paralegal. Focus on practical legal support tasks. Use clear legal terminology.",
        "communication_style": "formal",
        "icon": "file-text"
    },
    {
        "name": "Judge / Magistrate",
        "category": "Legal",
        "description": "Judicial officer presiding over legal proceedings",
        "terminology": ["ruling", "verdict", "sentencing", "objection", "sustained", "overruled", "bench", "chambers"],
        "common_topics": ["case law", "judicial procedure", "sentencing guidelines", "court administration"],
        "system_prompt_additions": "You are assisting a judicial officer. Maintain impartiality. Reference procedural rules and case law.",
        "communication_style": "formal",
        "icon": "gavel"
    },
    {
        "name": "Corporate Counsel",
        "category": "Legal",
        "description": "In-house legal advisor for corporations",
        "terminology": ["M&A", "compliance", "SEC", "corporate governance", "bylaws", "shareholder", "fiduciary duty"],
        "common_topics": ["corporate compliance", "mergers", "contracts", "risk management", "regulatory issues"],
        "system_prompt_additions": "You are assisting corporate legal counsel. Focus on business law, compliance, and corporate governance. Balance legal precision with business practicality.",
        "communication_style": "formal",
        "icon": "briefcase"
    },

    # ==========================================================================
    # MEDICAL & HEALTHCARE
    # ==========================================================================
    {
        "name": "Doctor / Physician",
        "category": "Medical & Healthcare",
        "description": "Medical doctor providing patient care",
        "terminology": ["diagnosis", "prognosis", "differential", "etiology", "contraindication", "comorbidity", "pathology"],
        "common_topics": ["patient care", "diagnosis", "treatment plans", "medical research", "clinical outcomes"],
        "system_prompt_additions": "You are assisting a medical professional. Use appropriate medical terminology. Focus on evidence-based medicine. Be precise about clinical details.",
        "communication_style": "technical",
        "icon": "stethoscope"
    },
    {
        "name": "Surgeon",
        "category": "Medical & Healthcare",
        "description": "Medical specialist performing surgical procedures",
        "terminology": ["incision", "resection", "anastomosis", "laparoscopic", "minimally invasive", "operative", "post-op"],
        "common_topics": ["surgical techniques", "patient outcomes", "operative planning", "recovery protocols"],
        "system_prompt_additions": "You are assisting a surgeon. Focus on surgical procedures, techniques, and patient outcomes. Be precise and direct.",
        "communication_style": "technical",
        "icon": "scissors"
    },
    {
        "name": "Nurse",
        "category": "Medical & Healthcare",
        "description": "Healthcare professional providing patient care",
        "terminology": ["vitals", "assessment", "care plan", "charting", "medication administration", "patient education"],
        "common_topics": ["patient care", "care coordination", "medication management", "patient education"],
        "system_prompt_additions": "You are assisting a nursing professional. Focus on patient care, safety, and practical clinical guidance.",
        "communication_style": "professional",
        "icon": "heart-pulse"
    },
    {
        "name": "Pharmacist",
        "category": "Medical & Healthcare",
        "description": "Medication and pharmaceutical expert",
        "terminology": ["dosage", "drug interaction", "contraindication", "generic", "brand", "compounding", "formulary"],
        "common_topics": ["medication management", "drug interactions", "patient counseling", "pharmaceutical care"],
        "system_prompt_additions": "You are assisting a pharmacist. Focus on medications, interactions, and pharmaceutical care. Be precise about dosages and contraindications.",
        "communication_style": "technical",
        "icon": "pill"
    },
    {
        "name": "Dentist",
        "category": "Medical & Healthcare",
        "description": "Oral health specialist",
        "terminology": ["cavity", "crown", "root canal", "periodontal", "extraction", "implant", "orthodontic"],
        "common_topics": ["oral health", "dental procedures", "patient care", "preventive dentistry"],
        "system_prompt_additions": "You are assisting a dental professional. Focus on oral health and dental procedures.",
        "communication_style": "professional",
        "icon": "smile"
    },
    {
        "name": "Psychologist / Therapist",
        "category": "Medical & Healthcare",
        "description": "Mental health professional",
        "terminology": ["cognitive behavioral", "therapeutic alliance", "assessment", "intervention", "DSM", "psychotherapy"],
        "common_topics": ["mental health", "therapeutic techniques", "patient progress", "psychological assessment"],
        "system_prompt_additions": "You are assisting a mental health professional. Be empathetic and clinically precise. Focus on therapeutic approaches and patient wellbeing.",
        "communication_style": "empathetic",
        "icon": "brain"
    },

    # ==========================================================================
    # TECHNOLOGY
    # ==========================================================================
    {
        "name": "Software Engineer",
        "category": "Technology",
        "description": "Developer building software applications",
        "terminology": ["API", "microservices", "CI/CD", "agile", "sprint", "refactor", "deployment", "scalability"],
        "common_topics": ["system design", "code review", "architecture", "debugging", "performance", "best practices"],
        "system_prompt_additions": "You are assisting a software engineer. Use technical terminology appropriately. Focus on clean code, best practices, and practical solutions.",
        "communication_style": "technical",
        "icon": "code"
    },
    {
        "name": "Data Scientist",
        "category": "Technology",
        "description": "Analytics and machine learning specialist",
        "terminology": ["model", "training", "inference", "feature engineering", "regression", "classification", "neural network"],
        "common_topics": ["data analysis", "model performance", "statistical methods", "ML pipelines", "insights"],
        "system_prompt_additions": "You are assisting a data scientist. Focus on data-driven insights, statistical rigor, and ML best practices.",
        "communication_style": "technical",
        "icon": "chart-bar"
    },
    {
        "name": "Product Manager",
        "category": "Technology",
        "description": "Product strategy and development leader",
        "terminology": ["roadmap", "sprint", "backlog", "stakeholder", "MVP", "user story", "KPI", "metrics"],
        "common_topics": ["product strategy", "feature prioritization", "user feedback", "market analysis", "roadmap planning"],
        "system_prompt_additions": "You are assisting a product manager. Balance technical feasibility with business value. Focus on user needs and strategic priorities.",
        "communication_style": "professional",
        "icon": "layout"
    },
    {
        "name": "DevOps Engineer",
        "category": "Technology",
        "description": "Infrastructure and deployment specialist",
        "terminology": ["container", "orchestration", "Kubernetes", "Docker", "pipeline", "infrastructure as code", "monitoring"],
        "common_topics": ["deployment", "automation", "infrastructure", "reliability", "scaling", "security"],
        "system_prompt_additions": "You are assisting a DevOps engineer. Focus on automation, reliability, and infrastructure best practices.",
        "communication_style": "technical",
        "icon": "server"
    },
    {
        "name": "Cybersecurity Analyst",
        "category": "Technology",
        "description": "Information security specialist",
        "terminology": ["vulnerability", "penetration testing", "firewall", "encryption", "threat", "incident response", "compliance"],
        "common_topics": ["security threats", "risk assessment", "compliance", "incident response", "security architecture"],
        "system_prompt_additions": "You are assisting a cybersecurity professional. Focus on security best practices, threat mitigation, and compliance.",
        "communication_style": "technical",
        "icon": "shield"
    },
    {
        "name": "UX/UI Designer",
        "category": "Technology",
        "description": "User experience and interface designer",
        "terminology": ["wireframe", "prototype", "user flow", "usability", "accessibility", "design system", "interaction"],
        "common_topics": ["user research", "design decisions", "usability testing", "visual design", "accessibility"],
        "system_prompt_additions": "You are assisting a UX/UI designer. Focus on user-centered design principles and practical design solutions.",
        "communication_style": "creative",
        "icon": "palette"
    },

    # ==========================================================================
    # FINANCE & ACCOUNTING
    # ==========================================================================
    {
        "name": "Accountant / CPA",
        "category": "Finance & Accounting",
        "description": "Financial accounting professional",
        "terminology": ["GAAP", "audit", "reconciliation", "depreciation", "accrual", "balance sheet", "P&L"],
        "common_topics": ["financial reporting", "tax compliance", "audit preparation", "budgeting", "financial analysis"],
        "system_prompt_additions": "You are assisting an accounting professional. Focus on accuracy, compliance, and financial best practices. Reference relevant accounting standards.",
        "communication_style": "formal",
        "icon": "calculator"
    },
    {
        "name": "Financial Analyst",
        "category": "Finance & Accounting",
        "description": "Investment and financial analysis specialist",
        "terminology": ["DCF", "valuation", "portfolio", "ROI", "EBITDA", "equity", "derivatives", "risk-adjusted"],
        "common_topics": ["financial modeling", "investment analysis", "market trends", "valuation", "risk assessment"],
        "system_prompt_additions": "You are assisting a financial analyst. Focus on data-driven analysis, market insights, and investment rationale.",
        "communication_style": "formal",
        "icon": "trending-up"
    },
    {
        "name": "Investment Banker",
        "category": "Finance & Accounting",
        "description": "M&A and capital markets specialist",
        "terminology": ["deal flow", "pitch book", "due diligence", "valuation", "LBO", "IPO", "syndication"],
        "common_topics": ["deal structuring", "client relationships", "market conditions", "valuation", "transaction execution"],
        "system_prompt_additions": "You are assisting an investment banker. Focus on deal dynamics, client relationships, and market positioning.",
        "communication_style": "formal",
        "icon": "landmark"
    },
    {
        "name": "Tax Consultant",
        "category": "Finance & Accounting",
        "description": "Tax planning and compliance specialist",
        "terminology": ["deduction", "credit", "filing", "audit", "compliance", "tax planning", "provision"],
        "common_topics": ["tax strategy", "compliance", "tax planning", "regulatory changes", "client advisory"],
        "system_prompt_additions": "You are assisting a tax professional. Focus on compliance, tax optimization, and regulatory requirements.",
        "communication_style": "formal",
        "icon": "receipt"
    },
    {
        "name": "CFO / Finance Director",
        "category": "Finance & Accounting",
        "description": "Chief financial officer",
        "terminology": ["capital allocation", "cash flow", "forecasting", "treasury", "investor relations", "financial strategy"],
        "common_topics": ["financial strategy", "capital allocation", "investor relations", "risk management", "growth planning"],
        "system_prompt_additions": "You are assisting a CFO. Focus on strategic financial decisions, stakeholder communication, and long-term planning.",
        "communication_style": "executive",
        "icon": "briefcase"
    },

    # ==========================================================================
    # SALES & MARKETING
    # ==========================================================================
    {
        "name": "Sales Representative",
        "category": "Sales & Marketing",
        "description": "Direct sales professional",
        "terminology": ["pipeline", "quota", "close rate", "prospect", "objection handling", "upsell", "CRM"],
        "common_topics": ["sales strategy", "client relationships", "deal negotiation", "pipeline management"],
        "system_prompt_additions": "You are assisting a sales professional. Focus on value propositions, client needs, and closing techniques. Be persuasive but authentic.",
        "communication_style": "persuasive",
        "icon": "handshake"
    },
    {
        "name": "Marketing Manager",
        "category": "Sales & Marketing",
        "description": "Marketing strategy and campaign leader",
        "terminology": ["campaign", "ROI", "conversion", "brand", "segmentation", "funnel", "engagement"],
        "common_topics": ["campaign strategy", "brand positioning", "market research", "performance metrics"],
        "system_prompt_additions": "You are assisting a marketing professional. Focus on brand messaging, audience engagement, and measurable results.",
        "communication_style": "creative",
        "icon": "megaphone"
    },
    {
        "name": "Business Development",
        "category": "Sales & Marketing",
        "description": "Partnership and growth specialist",
        "terminology": ["partnership", "strategic alliance", "market expansion", "opportunity", "stakeholder"],
        "common_topics": ["partnership development", "market opportunities", "relationship building", "strategic growth"],
        "system_prompt_additions": "You are assisting a business development professional. Focus on relationship building and strategic opportunities.",
        "communication_style": "professional",
        "icon": "users"
    },
    {
        "name": "Digital Marketer",
        "category": "Sales & Marketing",
        "description": "Online marketing specialist",
        "terminology": ["SEO", "PPC", "social media", "content marketing", "analytics", "conversion rate", "A/B testing"],
        "common_topics": ["digital campaigns", "social media strategy", "content performance", "analytics"],
        "system_prompt_additions": "You are assisting a digital marketer. Focus on data-driven marketing, channel optimization, and engagement metrics.",
        "communication_style": "creative",
        "icon": "globe"
    },

    # ==========================================================================
    # ENGINEERING
    # ==========================================================================
    {
        "name": "Civil Engineer",
        "category": "Engineering",
        "description": "Infrastructure and construction engineer",
        "terminology": ["structural", "load bearing", "foundation", "surveying", "specifications", "compliance"],
        "common_topics": ["project design", "safety standards", "construction methods", "regulatory compliance"],
        "system_prompt_additions": "You are assisting a civil engineer. Focus on technical accuracy, safety standards, and project requirements.",
        "communication_style": "technical",
        "icon": "building"
    },
    {
        "name": "Mechanical Engineer",
        "category": "Engineering",
        "description": "Mechanical systems specialist",
        "terminology": ["CAD", "thermodynamics", "materials", "manufacturing", "tolerance", "prototype"],
        "common_topics": ["design optimization", "manufacturing processes", "system performance", "testing"],
        "system_prompt_additions": "You are assisting a mechanical engineer. Focus on technical specifications, design principles, and practical solutions.",
        "communication_style": "technical",
        "icon": "cog"
    },
    {
        "name": "Electrical Engineer",
        "category": "Engineering",
        "description": "Electrical systems specialist",
        "terminology": ["circuit", "voltage", "current", "semiconductor", "PCB", "embedded", "power systems"],
        "common_topics": ["circuit design", "power systems", "electronics", "system integration"],
        "system_prompt_additions": "You are assisting an electrical engineer. Focus on technical accuracy and practical circuit/system design.",
        "communication_style": "technical",
        "icon": "zap"
    },
    {
        "name": "Chemical Engineer",
        "category": "Engineering",
        "description": "Chemical process specialist",
        "terminology": ["process", "reaction", "catalyst", "yield", "separation", "scale-up", "safety"],
        "common_topics": ["process optimization", "safety protocols", "scale-up challenges", "quality control"],
        "system_prompt_additions": "You are assisting a chemical engineer. Focus on process efficiency, safety, and technical accuracy.",
        "communication_style": "technical",
        "icon": "flask"
    },

    # ==========================================================================
    # EXECUTIVE & MANAGEMENT
    # ==========================================================================
    {
        "name": "CEO / Managing Director",
        "category": "Executive & Management",
        "description": "Chief executive officer",
        "terminology": ["strategy", "vision", "stakeholder", "board", "growth", "transformation", "leadership"],
        "common_topics": ["company strategy", "leadership", "stakeholder management", "organizational change"],
        "system_prompt_additions": "You are assisting a CEO. Focus on strategic thinking, leadership communication, and high-level decision making.",
        "communication_style": "executive",
        "icon": "crown"
    },
    {
        "name": "COO / Operations Director",
        "category": "Executive & Management",
        "description": "Chief operating officer",
        "terminology": ["operations", "efficiency", "process", "scaling", "execution", "KPIs"],
        "common_topics": ["operational efficiency", "process improvement", "team management", "execution"],
        "system_prompt_additions": "You are assisting a COO. Focus on operational excellence, efficiency, and practical execution.",
        "communication_style": "executive",
        "icon": "settings"
    },
    {
        "name": "HR Director",
        "category": "Executive & Management",
        "description": "Human resources leader",
        "terminology": ["talent", "culture", "engagement", "compensation", "benefits", "compliance", "retention"],
        "common_topics": ["talent management", "company culture", "employee relations", "HR strategy"],
        "system_prompt_additions": "You are assisting an HR leader. Focus on people management, culture, and organizational effectiveness.",
        "communication_style": "empathetic",
        "icon": "users"
    },
    {
        "name": "Project Manager",
        "category": "Executive & Management",
        "description": "Project planning and execution leader",
        "terminology": ["scope", "timeline", "milestone", "deliverable", "risk", "stakeholder", "Gantt"],
        "common_topics": ["project planning", "risk management", "stakeholder communication", "team coordination"],
        "system_prompt_additions": "You are assisting a project manager. Focus on planning, coordination, and clear communication.",
        "communication_style": "professional",
        "icon": "clipboard"
    },

    # ==========================================================================
    # CONSULTING
    # ==========================================================================
    {
        "name": "Management Consultant",
        "category": "Consulting",
        "description": "Business strategy consultant",
        "terminology": ["framework", "analysis", "recommendation", "implementation", "stakeholder", "deliverable"],
        "common_topics": ["strategy development", "problem solving", "client presentations", "recommendations"],
        "system_prompt_additions": "You are assisting a management consultant. Focus on structured thinking, clear recommendations, and client value.",
        "communication_style": "formal",
        "icon": "lightbulb"
    },
    {
        "name": "Strategy Consultant",
        "category": "Consulting",
        "description": "Corporate strategy specialist",
        "terminology": ["market analysis", "competitive advantage", "growth strategy", "M&A", "transformation"],
        "common_topics": ["strategic analysis", "market dynamics", "growth opportunities", "competitive positioning"],
        "system_prompt_additions": "You are assisting a strategy consultant. Focus on analytical rigor, strategic frameworks, and actionable insights.",
        "communication_style": "formal",
        "icon": "target"
    },
    {
        "name": "IT Consultant",
        "category": "Consulting",
        "description": "Technology consulting specialist",
        "terminology": ["digital transformation", "system integration", "architecture", "vendor", "implementation"],
        "common_topics": ["technology strategy", "system selection", "implementation planning", "change management"],
        "system_prompt_additions": "You are assisting an IT consultant. Balance technical expertise with business understanding.",
        "communication_style": "technical",
        "icon": "monitor"
    },

    # ==========================================================================
    # EDUCATION
    # ==========================================================================
    {
        "name": "Teacher / Professor",
        "category": "Education",
        "description": "Educator and instructor",
        "terminology": ["curriculum", "pedagogy", "assessment", "learning outcomes", "syllabus", "engagement"],
        "common_topics": ["teaching methods", "student engagement", "curriculum design", "assessment"],
        "system_prompt_additions": "You are assisting an educator. Focus on clear explanations, pedagogical approaches, and student success.",
        "communication_style": "educational",
        "icon": "book-open"
    },
    {
        "name": "School Administrator",
        "category": "Education",
        "description": "Educational institution leader",
        "terminology": ["policy", "accreditation", "budget", "faculty", "enrollment", "compliance"],
        "common_topics": ["school management", "policy implementation", "stakeholder relations", "institutional goals"],
        "system_prompt_additions": "You are assisting a school administrator. Focus on institutional leadership and educational excellence.",
        "communication_style": "professional",
        "icon": "graduation-cap"
    },
    {
        "name": "Academic Researcher",
        "category": "Education",
        "description": "Research scholar",
        "terminology": ["methodology", "hypothesis", "peer review", "publication", "grant", "citation"],
        "common_topics": ["research methodology", "publication", "grant writing", "academic collaboration"],
        "system_prompt_additions": "You are assisting an academic researcher. Focus on research rigor, methodology, and scholarly communication.",
        "communication_style": "formal",
        "icon": "microscope"
    },

    # ==========================================================================
    # MEDIA & COMMUNICATIONS
    # ==========================================================================
    {
        "name": "Journalist",
        "category": "Media & Communications",
        "description": "News and media professional",
        "terminology": ["source", "story", "deadline", "editorial", "fact-check", "angle", "scoop"],
        "common_topics": ["story development", "source management", "editorial decisions", "news coverage"],
        "system_prompt_additions": "You are assisting a journalist. Focus on accuracy, objectivity, and compelling storytelling.",
        "communication_style": "professional",
        "icon": "newspaper"
    },
    {
        "name": "TV Presenter / Anchor",
        "category": "Media & Communications",
        "description": "Television host and presenter",
        "terminology": ["segment", "live", "teleprompter", "interview", "breaking news", "ratings"],
        "common_topics": ["show preparation", "interview techniques", "audience engagement", "live broadcasting"],
        "system_prompt_additions": "You are assisting a TV presenter. Focus on engaging delivery, varied talking points, and audience connection. Avoid repetition of previous appearances.",
        "communication_style": "engaging",
        "icon": "tv"
    },
    {
        "name": "Public Relations",
        "category": "Media & Communications",
        "description": "PR and communications specialist",
        "terminology": ["press release", "media relations", "crisis", "spokesperson", "messaging", "pitch"],
        "common_topics": ["media strategy", "crisis management", "brand messaging", "stakeholder communication"],
        "system_prompt_additions": "You are assisting a PR professional. Focus on messaging clarity, reputation management, and strategic communication.",
        "communication_style": "professional",
        "icon": "message-circle"
    },
    {
        "name": "Content Creator",
        "category": "Media & Communications",
        "description": "Digital content professional",
        "terminology": ["engagement", "algorithm", "monetization", "audience", "viral", "brand deal"],
        "common_topics": ["content strategy", "audience growth", "monetization", "platform optimization"],
        "system_prompt_additions": "You are assisting a content creator. Focus on engaging content, audience connection, and platform best practices.",
        "communication_style": "creative",
        "icon": "video"
    },

    # ==========================================================================
    # REAL ESTATE
    # ==========================================================================
    {
        "name": "Real Estate Agent",
        "category": "Real Estate",
        "description": "Property sales professional",
        "terminology": ["listing", "closing", "escrow", "appraisal", "MLS", "commission", "contingency"],
        "common_topics": ["property marketing", "client relationships", "market analysis", "negotiations"],
        "system_prompt_additions": "You are assisting a real estate professional. Focus on market knowledge, client needs, and transaction success.",
        "communication_style": "persuasive",
        "icon": "home"
    },
    {
        "name": "Property Manager",
        "category": "Real Estate",
        "description": "Property management specialist",
        "terminology": ["lease", "tenant", "maintenance", "occupancy", "rent", "HOA"],
        "common_topics": ["tenant relations", "property maintenance", "lease management", "operational efficiency"],
        "system_prompt_additions": "You are assisting a property manager. Focus on tenant satisfaction, property upkeep, and operational efficiency.",
        "communication_style": "professional",
        "icon": "key"
    },

    # ==========================================================================
    # GOVERNMENT & PUBLIC SECTOR
    # ==========================================================================
    {
        "name": "Civil Servant",
        "category": "Government & Public Sector",
        "description": "Government employee",
        "terminology": ["policy", "regulation", "compliance", "stakeholder", "public interest", "budget"],
        "common_topics": ["policy implementation", "public service", "regulatory compliance", "stakeholder engagement"],
        "system_prompt_additions": "You are assisting a civil servant. Focus on public interest, policy compliance, and professional communication.",
        "communication_style": "formal",
        "icon": "landmark"
    },
    {
        "name": "Policy Analyst",
        "category": "Government & Public Sector",
        "description": "Public policy specialist",
        "terminology": ["analysis", "impact assessment", "recommendation", "stakeholder", "legislation"],
        "common_topics": ["policy analysis", "research", "recommendations", "stakeholder impact"],
        "system_prompt_additions": "You are assisting a policy analyst. Focus on evidence-based analysis and clear policy recommendations.",
        "communication_style": "formal",
        "icon": "file-text"
    },
    {
        "name": "Diplomat",
        "category": "Government & Public Sector",
        "description": "International relations professional",
        "terminology": ["bilateral", "multilateral", "treaty", "negotiation", "protocol", "diplomatic"],
        "common_topics": ["international relations", "negotiations", "diplomatic protocol", "policy coordination"],
        "system_prompt_additions": "You are assisting a diplomat. Focus on diplomatic language, cultural sensitivity, and strategic communication.",
        "communication_style": "diplomatic",
        "icon": "globe"
    },

    # ==========================================================================
    # CREATIVE & DESIGN
    # ==========================================================================
    {
        "name": "Graphic Designer",
        "category": "Creative & Design",
        "description": "Visual design professional",
        "terminology": ["branding", "typography", "layout", "color theory", "vector", "mockup"],
        "common_topics": ["design concepts", "brand guidelines", "client feedback", "creative direction"],
        "system_prompt_additions": "You are assisting a graphic designer. Focus on visual communication, design principles, and creative solutions.",
        "communication_style": "creative",
        "icon": "pen-tool"
    },
    {
        "name": "Architect",
        "category": "Creative & Design",
        "description": "Building and space designer",
        "terminology": ["blueprint", "elevation", "zoning", "sustainable", "load-bearing", "CAD"],
        "common_topics": ["design concepts", "building codes", "client requirements", "sustainable design"],
        "system_prompt_additions": "You are assisting an architect. Balance creative vision with technical requirements and regulations.",
        "communication_style": "technical",
        "icon": "compass"
    },
    {
        "name": "Interior Designer",
        "category": "Creative & Design",
        "description": "Interior space designer",
        "terminology": ["space planning", "mood board", "finish", "furniture", "lighting", "aesthetic"],
        "common_topics": ["design concepts", "client preferences", "space optimization", "material selection"],
        "system_prompt_additions": "You are assisting an interior designer. Focus on aesthetics, functionality, and client vision.",
        "communication_style": "creative",
        "icon": "layout"
    },

    # ==========================================================================
    # HOSPITALITY & SERVICE
    # ==========================================================================
    {
        "name": "Hotel Manager",
        "category": "Hospitality & Service",
        "description": "Hospitality management professional",
        "terminology": ["occupancy", "RevPAR", "guest experience", "housekeeping", "front desk", "concierge"],
        "common_topics": ["guest satisfaction", "operations", "staff management", "service quality"],
        "system_prompt_additions": "You are assisting a hospitality professional. Focus on guest experience, service excellence, and operational efficiency.",
        "communication_style": "professional",
        "icon": "building-2"
    },
    {
        "name": "Restaurant Manager",
        "category": "Hospitality & Service",
        "description": "Food service management professional",
        "terminology": ["covers", "table turn", "food cost", "BOH", "FOH", "reservation"],
        "common_topics": ["service quality", "staff management", "menu planning", "customer satisfaction"],
        "system_prompt_additions": "You are assisting a restaurant professional. Focus on service excellence and operational efficiency.",
        "communication_style": "professional",
        "icon": "utensils"
    },

    # ==========================================================================
    # MANUFACTURING & OPERATIONS
    # ==========================================================================
    {
        "name": "Manufacturing Manager",
        "category": "Manufacturing & Operations",
        "description": "Production and manufacturing leader",
        "terminology": ["lean", "Six Sigma", "throughput", "yield", "quality control", "OEE"],
        "common_topics": ["production efficiency", "quality management", "process improvement", "safety"],
        "system_prompt_additions": "You are assisting a manufacturing professional. Focus on efficiency, quality, and continuous improvement.",
        "communication_style": "technical",
        "icon": "factory"
    },
    {
        "name": "Supply Chain Manager",
        "category": "Manufacturing & Operations",
        "description": "Logistics and supply chain specialist",
        "terminology": ["logistics", "inventory", "procurement", "vendor", "lead time", "just-in-time"],
        "common_topics": ["supply chain optimization", "vendor management", "inventory control", "logistics"],
        "system_prompt_additions": "You are assisting a supply chain professional. Focus on efficiency, cost optimization, and reliability.",
        "communication_style": "professional",
        "icon": "truck"
    },

    # ==========================================================================
    # SPORTS & FITNESS
    # ==========================================================================
    {
        "name": "Professional Athlete",
        "category": "Sports & Fitness",
        "description": "Competitive sports professional",
        "terminology": ["training", "performance", "recovery", "competition", "contract", "endorsement"],
        "common_topics": ["performance", "training", "media interviews", "team dynamics"],
        "system_prompt_additions": "You are assisting a professional athlete. Focus on performance mindset, media preparation, and professional communication.",
        "communication_style": "confident",
        "icon": "trophy"
    },
    {
        "name": "Coach / Trainer",
        "category": "Sports & Fitness",
        "description": "Sports coaching professional",
        "terminology": ["training plan", "periodization", "technique", "performance metrics", "recovery"],
        "common_topics": ["athlete development", "training programs", "performance analysis", "motivation"],
        "system_prompt_additions": "You are assisting a sports coach. Focus on development, motivation, and performance optimization.",
        "communication_style": "motivational",
        "icon": "dumbbell"
    },

    # ==========================================================================
    # NON-PROFIT & SOCIAL
    # ==========================================================================
    {
        "name": "Non-Profit Director",
        "category": "Non-Profit & Social",
        "description": "Non-profit organization leader",
        "terminology": ["mission", "impact", "donor", "grant", "volunteer", "fundraising", "stakeholder"],
        "common_topics": ["mission advancement", "fundraising", "stakeholder engagement", "impact measurement"],
        "system_prompt_additions": "You are assisting a non-profit leader. Focus on mission-driven communication and stakeholder engagement.",
        "communication_style": "passionate",
        "icon": "heart"
    },
    {
        "name": "Social Worker",
        "category": "Non-Profit & Social",
        "description": "Social services professional",
        "terminology": ["case management", "intervention", "advocacy", "resources", "assessment"],
        "common_topics": ["client support", "resource coordination", "advocacy", "case management"],
        "system_prompt_additions": "You are assisting a social worker. Focus on empathy, client advocacy, and practical support.",
        "communication_style": "empathetic",
        "icon": "users"
    },

    # ==========================================================================
    # ENTREPRENEURSHIP
    # ==========================================================================
    {
        "name": "Startup Founder",
        "category": "Entrepreneurship",
        "description": "Startup entrepreneur",
        "terminology": ["pitch", "runway", "pivot", "MVP", "traction", "funding", "valuation", "burn rate"],
        "common_topics": ["fundraising", "product development", "team building", "growth strategy"],
        "system_prompt_additions": "You are assisting a startup founder. Focus on compelling storytelling, investor communication, and strategic thinking.",
        "communication_style": "entrepreneurial",
        "icon": "rocket"
    },
    {
        "name": "Small Business Owner",
        "category": "Entrepreneurship",
        "description": "Small business entrepreneur",
        "terminology": ["cash flow", "customer", "inventory", "margins", "growth", "operations"],
        "common_topics": ["business operations", "customer relations", "growth strategies", "financial management"],
        "system_prompt_additions": "You are assisting a small business owner. Focus on practical business advice and customer-centric thinking.",
        "communication_style": "practical",
        "icon": "store"
    },
]


def seed_professions():
    """Seed the database with all professions."""
    db = SessionLocal()
    try:
        # Check if professions already exist
        existing_count = db.query(Profession).count()
        if existing_count > 0:
            print(f"Database already has {existing_count} professions. Skipping seed.")
            return

        # Add all professions
        for prof_data in PROFESSIONS:
            profession = Profession(
                name=prof_data["name"],
                category=prof_data["category"],
                description=prof_data["description"],
                terminology=prof_data["terminology"],
                common_topics=prof_data["common_topics"],
                system_prompt_additions=prof_data["system_prompt_additions"],
                communication_style=prof_data["communication_style"],
                icon=prof_data["icon"],
                is_active=True
            )
            db.add(profession)

        db.commit()
        print(f"Successfully seeded {len(PROFESSIONS)} professions!")

        # Print categories summary
        categories = {}
        for prof in PROFESSIONS:
            cat = prof["category"]
            categories[cat] = categories.get(cat, 0) + 1

        print("\nProfessions by category:")
        for cat, count in sorted(categories.items()):
            print(f"  {cat}: {count}")

    except Exception as e:
        print(f"Error seeding professions: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_professions()
