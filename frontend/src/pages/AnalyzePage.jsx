import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Link2, FileText, Upload, UserCheck, Mail, Sparkles, ArrowRight, ShieldCheck, FileCheck } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { mockAnalysisHighRisk, mockAnalysisLowRisk, mockAnalysisModerateRisk } from '../data/mockData';

export const AnalyzePage = () => {
  const navigate = useNavigate();
  const { loadReport } = useAuth();
  const [activeTab, setActiveTab] = useState('url');

  // Input States
  const [urlInput, setUrlInput] = useState('');
  const [descInput, setDescInput] = useState('');
  const [fileName, setFileName] = useState('');
  const [recruiterEmail, setRecruiterEmail] = useState('');
  const [recruiterName, setRecruiterName] = useState('');
  const [messageInput, setMessageInput] = useState('');

  // Preset Loaders for quick demo
  const loadPresetScam = () => {
    setUrlInput('https://apex-global-careers-hire.net/jobs/entry-data-spec');
    setDescInput('We are looking for an Entry-Level Remote Data Specialist. $65/hr. High payout. Mandatory requirement: Candidates must accept a $2,000 cashier check reimbursement to purchase Apple hardware from our designated portal.');
    setFileName('Apex_Global_Offer_Letter.pdf');
    setRecruiterEmail('recruitment@apex-global-hr.net');
    setRecruiterName('Sarah Jenkins');
    setMessageInput('Hello! Your application for Data Entry Specialist has been approved. Please message our hiring manager on Telegram @apex_hr_dept immediately to claim your $2,000 equipment check.');
    loadReport(mockAnalysisHighRisk);
  };

  const loadPresetSafe = () => {
    setUrlInput('https://stripe.com/jobs/listing/software-engineer-intern');
    setDescInput('Stripe is hiring Software Engineer Interns for Summer 2026. You will build payment infrastructure with Ruby, Go, and React. $55/hr + housing stipend. Official university recruiting program.');
    setFileName('Stripe_Internship_Offer_2026.pdf');
    setRecruiterEmail('university-hiring@stripe.com');
    setRecruiterName('Elena Rostova');
    setMessageInput('Hi Nihar, Thank you for interviewing with Stripe. We are thrilled to offer you a Software Engineer Internship position for Summer 2026!');
    loadReport(mockAnalysisLowRisk);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    // Default load high risk if not prefilled
    if (urlInput.includes('stripe')) {
      loadReport(mockAnalysisLowRisk);
    } else if (urlInput.includes('vanguard')) {
      loadReport(mockAnalysisModerateRisk);
    } else {
      loadReport(mockAnalysisHighRisk);
    }
    navigate('/analyze/processing');
  };

  const tabs = [
    { id: 'url', label: 'Job URL', icon: Link2 },
    { id: 'description', label: 'Job Description', icon: FileText },
    { id: 'document', label: 'Upload Document', icon: Upload },
    { id: 'recruiter', label: 'Recruiter Details', icon: UserCheck },
    { id: 'email', label: 'Email / Message', icon: Mail },
  ];

  return (
    <div className="max-w-[1000px] mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
      
      {/* Header Banner */}
      <div className="text-center space-y-3">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-secondary-container text-primary text-xs font-semibold">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Multi-Modal Scam Analysis</span>
        </div>
        <h1 className="font-serif text-3xl sm:text-4xl font-semibold text-ink">
          Analyze Job & Internship Opportunity
        </h1>
        <p className="text-sm text-ink-muted max-w-xl mx-auto">
          Choose your input method below. You can submit a URL, paste job text, upload an offer PDF, or check recruiter contact details.
        </p>
      </div>

      {/* Preset Demo Buttons for Project Guide Demo */}
      <div className="bg-surface-2 p-4 rounded-2xl border border-ink/5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs font-semibold text-ink-muted">
          <Sparkles className="w-4 h-4 text-primary" />
          <span>1-Click Presentation Presets:</span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={loadPresetScam}
            className="px-3.5 py-1.5 rounded-full bg-risk-high-bg text-risk-high text-xs font-semibold hover:bg-risk-high-bg/80 transition-all flex items-center gap-1.5"
          >
            <span>⚡ Load High-Risk Scam Sample</span>
          </button>
          <button
            type="button"
            onClick={loadPresetSafe}
            className="px-3.5 py-1.5 rounded-full bg-risk-low-bg text-risk-low text-xs font-semibold hover:bg-risk-low-bg/80 transition-all flex items-center gap-1.5"
          >
            <span>⚡ Load Verified Safe Sample</span>
          </button>
        </div>
      </div>

      {/* Main Analysis Card */}
      <div className="bg-surface rounded-3xl shadow-floating border border-ink/5 overflow-hidden">
        
        {/* Navigation Tabs */}
        <div className="flex border-b border-ink/5 overflow-x-auto scrollbar-none bg-surface-2/50 p-2 gap-1">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isCurrent = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-5 py-3 rounded-2xl text-xs font-semibold whitespace-nowrap transition-all ${
                  isCurrent
                    ? 'bg-surface text-primary shadow-subtle'
                    : 'text-ink-muted hover:text-ink hover:bg-surface/50'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Tab Form Content */}
        <form onSubmit={handleSubmit} className="p-6 sm:p-10 space-y-6">
          
          {/* TAB 1: JOB URL */}
          {activeTab === 'url' && (
            <div className="space-y-4">
              <label className="block text-xs font-semibold uppercase tracking-wider text-ink-muted">
                Job Posting or Career Page URL
              </label>
              <input
                type="url"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                placeholder="https://company.com/careers/job-title or https://linkedin.com/jobs/view/..."
                className="w-full bg-canvas border border-ink/10 rounded-2xl px-5 py-3.5 text-sm text-ink placeholder-ink-subtle focus:outline-none focus:border-primary transition-all"
              />
              <p className="text-xs text-ink-subtle">
                HireShield checks WHOIS registrar age, SSL certificates, typosquatting, and official listing cross-indexes.
              </p>
            </div>
          )}

          {/* TAB 2: PASTE JOB DESCRIPTION */}
          {activeTab === 'description' && (
            <div className="space-y-4">
              <label className="block text-xs font-semibold uppercase tracking-wider text-ink-muted">
                Pasted Job Description Text
              </label>
              <textarea
                rows={6}
                value={descInput}
                onChange={(e) => setDescInput(e.target.value)}
                placeholder="Paste the full job post, responsibilities, compensation terms, and contact instructions..."
                className="w-full bg-canvas border border-ink/10 rounded-2xl p-5 text-sm text-ink placeholder-ink-subtle focus:outline-none focus:border-primary transition-all resize-none"
              />
              <p className="text-xs text-ink-subtle">
                Our NLP engine inspects pay rate benchmarks, urgency phrasing, and equipment purchase clauses.
              </p>
            </div>
          )}

          {/* TAB 3: UPLOAD DOCUMENT */}
          {activeTab === 'document' && (
            <div className="space-y-4">
              <label className="block text-xs font-semibold uppercase tracking-wider text-ink-muted">
                Upload Offer Letter or Contract PDF
              </label>
              <div className="border-2 border-dashed border-ink/15 bg-canvas rounded-3xl p-8 text-center space-y-3 hover:border-primary/40 transition-all cursor-pointer">
                <div className="w-12 h-12 rounded-full bg-secondary-container text-primary flex items-center justify-center mx-auto">
                  <Upload className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-ink">
                    {fileName ? fileName : 'Click to select or drag PDF offer document'}
                  </p>
                  <p className="text-xs text-ink-subtle mt-1">Supports PDF, DOCX (Max 10MB)</p>
                </div>
                {!fileName && (
                  <button
                    type="button"
                    onClick={() => setFileName('Sample_Job_Offer_Letter.pdf')}
                    className="px-4 py-1.5 rounded-full bg-surface border border-ink/10 text-xs font-semibold text-ink-muted hover:text-ink"
                  >
                    Simulate Selecting File
                  </button>
                )}
              </div>
            </div>
          )}

          {/* TAB 4: RECRUITER DETAILS */}
          {activeTab === 'recruiter' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-ink-muted mb-2">
                    Recruiter Email Address
                  </label>
                  <input
                    type="email"
                    value={recruiterEmail}
                    onChange={(e) => setRecruiterEmail(e.target.value)}
                    placeholder="recruiter@company-hr.com"
                    className="w-full bg-canvas border border-ink/10 rounded-2xl px-5 py-3 text-sm text-ink placeholder-ink-subtle focus:outline-none focus:border-primary"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-ink-muted mb-2">
                    Recruiter Name / Title
                  </label>
                  <input
                    type="text"
                    value={recruiterName}
                    onChange={(e) => setRecruiterName(e.target.value)}
                    placeholder="e.g. Sarah Jenkins (HR Director)"
                    className="w-full bg-canvas border border-ink/10 rounded-2xl px-5 py-3 text-sm text-ink placeholder-ink-subtle focus:outline-none focus:border-primary"
                  />
                </div>
              </div>
              <p className="text-xs text-ink-subtle">
                Validates MX records, DMARC/SPF authentication headers, and corporate directory alignment.
              </p>
            </div>
          )}

          {/* TAB 5: EMAIL / MESSAGE */}
          {activeTab === 'email' && (
            <div className="space-y-4">
              <label className="block text-xs font-semibold uppercase tracking-wider text-ink-muted">
                Pasted Email Message or Chat Transcript
              </label>
              <textarea
                rows={6}
                value={messageInput}
                onChange={(e) => setMessageInput(e.target.value)}
                placeholder="Paste the email, Telegram/WhatsApp interview message, or offer message received..."
                className="w-full bg-canvas border border-ink/10 rounded-2xl p-5 text-sm text-ink placeholder-ink-subtle focus:outline-none focus:border-primary transition-all resize-none"
              />
              <p className="text-xs text-ink-subtle">
                Detects messaging platform redirection (Telegram/Signal), check reimbursement language, and fake interview steps.
              </p>
            </div>
          )}

          {/* Submit Action */}
          <div className="pt-4 border-t border-ink/5 flex items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-xs text-ink-muted">
              <ShieldCheck className="w-4 h-4 text-primary" />
              <span>Multi-layer AI verification protocol active</span>
            </div>

            <button
              type="submit"
              className="px-8 py-3.5 rounded-full bg-primary text-surface text-xs font-bold shadow-subtle hover:bg-primary-container transition-all flex items-center gap-2"
            >
              <span>Run HireShield Scan</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>

        </form>
      </div>

    </div>
  );
};
