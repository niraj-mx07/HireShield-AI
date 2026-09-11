import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  ShieldCheck,
  Search,
  Lock,
  Sparkles,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  Building2,
  UserCheck,
  DollarSign,
  FileCheck,
  Globe,
  MessageSquare,
  Shield,
  Star
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { mockAnalysisHighRisk, mockAnalysisLowRisk } from '../data/mockData';

export const LandingPage = () => {
  const navigate = useNavigate();
  const { loadReport } = useAuth();
  const [heroInput, setHeroInput] = useState('');

  const handleHeroSubmit = (e) => {
    e.preventDefault();
    if (heroInput.toLowerCase().includes('stripe') || heroInput.toLowerCase().includes('safe')) {
      loadReport(mockAnalysisLowRisk);
    } else {
      loadReport(mockAnalysisHighRisk);
    }
    navigate('/analyze/processing');
  };

  return (
    <div className="space-y-24 pb-12">
      
      {/* HERO SECTION */}
      <section className="pt-12 md:pt-20 max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          
          {/* Left Column: Headline & Search Bar */}
          <div className="lg:col-span-7 space-y-8 text-left">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-secondary-container text-primary text-xs font-semibold">
              <Sparkles className="w-3.5 h-3.5" />
              <span>AI-Powered Job Scam Prevention Engine</span>
            </div>

            <h1 className="font-serif text-5xl sm:text-6xl font-semibold text-ink leading-[1.1] tracking-tight">
              Know Before You <span className="text-primary italic font-normal">Apply.</span>
            </h1>

            <p className="text-base sm:text-lg text-ink-muted leading-relaxed max-w-xl font-sans">
              Protect your career, personal data, and bank account. HireShield-AI instantly validates job offers, recruiter emails, WHOIS domain age, and payment clauses before you hit submit.
            </p>

            {/* Pill Search Input Bar */}
            <form onSubmit={handleHeroSubmit} className="relative max-w-2xl">
              <div className="flex flex-col sm:flex-row items-center bg-surface p-2 rounded-3xl sm:rounded-full shadow-floating border border-ink/10 gap-2">
                <div className="flex items-center gap-3 px-4 w-full sm:w-auto flex-1">
                  <Search className="w-5 h-5 text-ink-subtle flex-shrink-0" />
                  <input
                    type="text"
                    value={heroInput}
                    onChange={(e) => setHeroInput(e.target.value)}
                    placeholder="Paste job URL, recruiter email, or company domain..."
                    className="w-full bg-transparent border-none text-sm text-ink placeholder-ink-subtle focus:outline-none py-2"
                  />
                </div>
                <button
                  type="submit"
                  className="w-full sm:w-auto px-7 py-3 rounded-full bg-primary text-surface text-xs font-semibold hover:bg-primary-container shadow-subtle transition-all flex items-center justify-center gap-2 flex-shrink-0"
                >
                  <span>Check Risk Free</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </form>

            {/* Quick Demo Loader Hints */}
            <div className="flex items-center gap-3 text-xs text-ink-subtle pt-1">
              <span className="font-semibold text-ink-muted">Quick Demos:</span>
              <button
                onClick={() => {
                  loadReport(mockAnalysisHighRisk);
                  navigate('/analyze/processing');
                }}
                className="text-risk-high hover:underline font-medium"
              >
                ⚡ High-Risk Scam Offer
              </button>
              <span>•</span>
              <button
                onClick={() => {
                  loadReport(mockAnalysisLowRisk);
                  navigate('/analyze/processing');
                }}
                className="text-risk-low hover:underline font-medium"
              >
                ⚡ Legitimate Stripe Internship
              </button>
            </div>

            {/* Trust Indicator Row */}
            <div className="pt-4 border-t border-ink/5 flex flex-wrap items-center gap-6 text-xs text-ink-muted">
              <div className="flex items-center gap-2">
                <Lock className="w-4 h-4 text-primary" />
                <span>Zero Data Sharing</span>
              </div>
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-primary" />
                <span>Multi-Layer Verification</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-primary" />
                <span>Instant Risk Score</span>
              </div>
            </div>
          </div>

          {/* Right Column: Floating Overlapping Result Cards Visual */}
          <div className="lg:col-span-5 relative flex justify-center py-6">
            <div className="relative w-full max-w-md">
              
              {/* Back Card: High Risk (Red) */}
              <div className="bg-surface rounded-2xl p-6 shadow-floating border border-risk-high/20 transform translate-x-2 -translate-y-4 hover:translate-y-0 transition-transform duration-500">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-semibold text-ink-muted">Apex Global Solutions</span>
                  <span className="px-3 py-1 rounded-full bg-risk-high-bg text-risk-high text-xs font-bold uppercase tracking-wider">
                    Verdict: DON'T APPLY
                  </span>
                </div>
                <div className="flex items-baseline justify-between mb-2">
                  <span className="text-sm font-semibold text-ink">Senior Operations Assistant</span>
                  <span className="font-serif text-2xl font-semibold text-risk-high">88/100</span>
                </div>
                <div className="bg-surface-2 p-3 rounded-xl text-xs text-ink-muted flex items-start gap-2 border border-risk-high/10">
                  <AlertTriangle className="w-4 h-4 text-risk-high flex-shrink-0 mt-0.5" />
                  <span>Domain created 9 days ago. Requires $1,450 advance check for home equipment.</span>
                </div>
              </div>

              {/* Front Card: Low Risk (Green) - Overlapping */}
              <div className="bg-surface rounded-2xl p-6 shadow-floating border border-risk-low/20 transform -translate-x-3 translate-y-6 hover:translate-y-2 transition-transform duration-500 relative z-10">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-semibold text-ink-muted">Stripe, Inc.</span>
                  <span className="px-3 py-1 rounded-full bg-risk-low-bg text-risk-low text-xs font-bold uppercase tracking-wider">
                    Verdict: APPLY
                  </span>
                </div>
                <div className="flex items-baseline justify-between mb-2">
                  <span className="text-sm font-semibold text-ink">Software Engineer Intern</span>
                  <span className="font-serif text-2xl font-semibold text-risk-low">12/100</span>
                </div>
                <div className="bg-surface-2 p-3 rounded-xl text-xs text-ink-muted flex items-start gap-2 border border-risk-low/10">
                  <CheckCircle2 className="w-4 h-4 text-risk-low flex-shrink-0 mt-0.5" />
                  <span>100% verified corporate domain, SPF/DKIM authenticated recruiter email.</span>
                </div>
              </div>

              {/* Subtle background glow circle */}
              <div className="absolute -inset-4 bg-primary/5 rounded-full blur-3xl -z-10" />
            </div>
          </div>
        </div>
      </section>

      {/* HOW IT WORKS SECTION */}
      <section className="max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-16 space-y-3">
          <h2 className="font-serif text-3xl sm:text-4xl font-semibold text-ink">
            How HireShield Safeguards You
          </h2>
          <p className="text-sm text-ink-muted">
            Three simple steps to verify job credibility before investing your time or personal documents.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Step 1 */}
          <div className="bg-surface rounded-2xl p-8 shadow-subtle border border-ink/5 space-y-4 hover:shadow-floating transition-all">
            <span className="font-serif text-3xl font-semibold text-primary">01</span>
            <h3 className="font-serif text-xl font-semibold text-ink">Submit Opportunity</h3>
            <p className="text-sm text-ink-muted leading-relaxed">
              Paste the job post URL, upload an offer PDF, or enter recruiter contact details into our multi-input portal.
            </p>
          </div>

          {/* Step 2 */}
          <div className="bg-surface rounded-2xl p-8 shadow-subtle border border-ink/5 space-y-4 hover:shadow-floating transition-all">
            <span className="font-serif text-3xl font-semibold text-primary">02</span>
            <h3 className="font-serif text-xl font-semibold text-ink">AI & Web Verification</h3>
            <p className="text-sm text-ink-muted leading-relaxed">
              Our system checks WHOIS domain registration age, state business records, email SPF auth, and advance-fee NLP patterns.
            </p>
          </div>

          {/* Step 3 */}
          <div className="bg-surface rounded-2xl p-8 shadow-subtle border border-ink/5 space-y-4 hover:shadow-floating transition-all">
            <span className="font-serif text-3xl font-semibold text-primary">03</span>
            <h3 className="font-serif text-xl font-semibold text-ink">Clear Risk Report</h3>
            <p className="text-sm text-ink-muted leading-relaxed">
              Get an explainable 0–100 risk score, verdict badge (APPLY / HOLD / DON'T APPLY), and itemized evidence matrix.
            </p>
          </div>
        </div>
      </section>

      {/* WHAT WE CHECK SECTION */}
      <section className="max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-16 space-y-3">
          <h2 className="font-serif text-3xl sm:text-4xl font-semibold text-ink">
            What We Check
          </h2>
          <p className="text-sm text-ink-muted">
            We evaluate multiple weak signals to detect coordinated employment scams.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          
          {/* Card 1 */}
          <div className="bg-surface rounded-2xl p-6 shadow-subtle border border-ink/5 space-y-3">
            <div className="w-10 h-10 rounded-2xl bg-accent-recruiter-bg text-accent-recruiter flex items-center justify-center">
              <Building2 className="w-5 h-5" />
            </div>
            <h3 className="font-serif text-lg font-semibold text-ink">Company Verification</h3>
            <p className="text-xs text-ink-muted leading-relaxed">
              Cross-references corporate state Secretary of State registrations, HQ physical addresses, and active tax standing.
            </p>
          </div>

          {/* Card 2 */}
          <div className="bg-surface rounded-2xl p-6 shadow-subtle border border-ink/5 space-y-3">
            <div className="w-10 h-10 rounded-2xl bg-accent-url-bg text-accent-url flex items-center justify-center">
              <UserCheck className="w-5 h-5" />
            </div>
            <h3 className="font-serif text-lg font-semibold text-ink">Recruiter Identity</h3>
            <p className="text-xs text-ink-muted leading-relaxed">
              Validates email DMARC/SPF records, recruiter domain alignment, and LinkedIn professional history.
            </p>
          </div>

          {/* Card 3 */}
          <div className="bg-surface rounded-2xl p-6 shadow-subtle border border-ink/5 space-y-3">
            <div className="w-10 h-10 rounded-2xl bg-accent-document-bg text-accent-document flex items-center justify-center">
              <DollarSign className="w-5 h-5" />
            </div>
            <h3 className="font-serif text-lg font-semibold text-ink">Financial Red Flags</h3>
            <p className="text-xs text-ink-muted leading-relaxed">
              Detects cashier check reimbursement schemes, mandatory equipment vendor links, and application fee requests.
            </p>
          </div>

          {/* Card 4 */}
          <div className="bg-surface rounded-2xl p-6 shadow-subtle border border-ink/5 space-y-3">
            <div className="w-10 h-10 rounded-2xl bg-accent-recruiter-bg text-accent-recruiter flex items-center justify-center">
              <FileCheck className="w-5 h-5" />
            </div>
            <h3 className="font-serif text-lg font-semibold text-ink">Document Analysis</h3>
            <p className="text-xs text-ink-muted leading-relaxed">
              Inspects PDF offer letters for structural metadata, copied boilerplate text, and conflicting company contact info.
            </p>
          </div>

          {/* Card 5 */}
          <div className="bg-surface rounded-2xl p-6 shadow-subtle border border-ink/5 space-y-3">
            <div className="w-10 h-10 rounded-2xl bg-accent-url-bg text-accent-url flex items-center justify-center">
              <Globe className="w-5 h-5" />
            </div>
            <h3 className="font-serif text-lg font-semibold text-ink">URL & Domain Safety</h3>
            <p className="text-xs text-ink-muted leading-relaxed">
              Checks domain registration age, privacy shields, SSL certificate chain, and lookalike domain typosquatting.
            </p>
          </div>

          {/* Card 6 */}
          <div className="bg-surface rounded-2xl p-6 shadow-subtle border border-ink/5 space-y-3">
            <div className="w-10 h-10 rounded-2xl bg-accent-document-bg text-accent-document flex items-center justify-center">
              <MessageSquare className="w-5 h-5" />
            </div>
            <h3 className="font-serif text-lg font-semibold text-ink">Linguistic Patterns</h3>
            <p className="text-xs text-ink-muted leading-relaxed">
              Identifies artificial urgency language, messaging app interview redirection (Telegram/WhatsApp), and unrealistic pay rates.
            </p>
          </div>

        </div>
      </section>

      {/* TESTIMONIALS SECTION */}
      <section className="max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-16 space-y-3">
          <h2 className="font-serif text-3xl sm:text-4xl font-semibold text-ink">
            Trusted by Job Seekers
          </h2>
          <p className="text-sm text-ink-muted">
            See how HireShield-AI prevented students and graduates from falling victim to job scams.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="bg-surface rounded-2xl p-6 shadow-subtle border border-ink/5 flex flex-col justify-between space-y-4">
            <div className="space-y-3">
              <div className="flex gap-1 text-primary">
                {[...Array(5)].map((_, i) => (
                  <Star key={i} className="w-4 h-4 fill-current" />
                ))}
              </div>
              <p className="text-xs text-ink leading-relaxed">
                "I almost deposited a $2,200 equipment check from a remote data entry company. HireShield caught that the recruiter's email domain was registered 6 days ago!"
              </p>
            </div>
            <div className="pt-4 border-t border-ink/5 text-xs">
              <div className="font-semibold text-ink">Rohan M.</div>
              <div className="text-ink-subtle">CS Senior • State University</div>
            </div>
          </div>

          <div className="bg-surface rounded-2xl p-6 shadow-subtle border border-ink/5 flex flex-col justify-between space-y-4">
            <div className="space-y-3">
              <div className="flex gap-1 text-primary">
                {[...Array(5)].map((_, i) => (
                  <Star key={i} className="w-4 h-4 fill-current" />
                ))}
              </div>
              <p className="text-xs text-ink leading-relaxed">
                "Checking my Stripe intern offer gave me complete peace of mind. The verification matrix confirmed 100% official DMARC records."
              </p>
            </div>
            <div className="pt-4 border-t border-ink/5 text-xs">
              <div className="font-semibold text-ink">Ananya Sharma</div>
              <div className="text-ink-subtle">Recent Business Graduate</div>
            </div>
          </div>

          <div className="bg-surface rounded-2xl p-6 shadow-subtle border border-ink/5 flex flex-col justify-between space-y-4">
            <div className="space-y-3">
              <div className="flex gap-1 text-primary">
                {[...Array(5)].map((_, i) => (
                  <Star key={i} className="w-4 h-4 fill-current" />
                ))}
              </div>
              <p className="text-xs text-ink leading-relaxed">
                "Super fast scan. The evidence breakdown makes it crystal clear why a job post is flagged so you're not just guessing."
              </p>
            </div>
            <div className="pt-4 border-t border-ink/5 text-xs">
              <div className="font-semibold text-ink">David K.</div>
              <div className="text-ink-subtle">Junior Developer</div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA BANNER */}
      <section className="max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-primary rounded-3xl p-10 sm:p-14 text-surface text-center space-y-6 shadow-floating relative overflow-hidden">
          <h2 className="font-serif text-3xl sm:text-5xl font-semibold max-w-2xl mx-auto leading-tight">
            Protect Your Career Search Before You Apply.
          </h2>
          <p className="text-sm sm:text-base text-surface/80 max-w-xl mx-auto font-sans">
            Don't share your SSN, bank details, or address with unverified employers. Run a 30-second HireShield scan now.
          </p>
          <div className="pt-2">
            <Link
              to="/analyze"
              className="inline-flex items-center gap-2 px-8 py-3.5 rounded-full bg-surface text-primary text-xs font-bold hover:bg-secondary-container shadow-subtle transition-all"
            >
              <span>Scan Opportunity Now</span>
              <ArrowRight className="w-4 h-4 text-primary" />
            </Link>
          </div>
        </div>
      </section>

    </div>
  );
};
