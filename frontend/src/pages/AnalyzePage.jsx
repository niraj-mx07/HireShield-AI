import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Link2, FileText, Upload, UserCheck, Mail, Sparkles, ArrowRight, ShieldCheck, CheckCircle2, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import {
  mockAnalysisHighRisk,
  mockAnalysisLowRisk,
  mockAnalysisIndiaScam,
  mockAnalysisTelegramScam,
} from '../data/mockData';
import { submitAssessment, submitAssessmentWithUpload, formatBackendResponse } from '../services/api';

export const AnalyzePage = () => {
  const navigate = useNavigate();
  const { loadReport } = useAuth();
  const [activeTab, setActiveTab] = useState('url');

  // Input States (Persist simultaneously across all tabs)
  const [urlInput, setUrlInput] = useState('');
  const [descInput, setDescInput] = useState('');
  const [fileName, setFileName] = useState('');
  const [fileObject, setFileObject] = useState(null);
  const [companyName, setCompanyName] = useState('');
  const [recruiterEmail, setRecruiterEmail] = useState('');
  const [recruiterName, setRecruiterName] = useState('');
  const [recruiterPhone, setRecruiterPhone] = useState('');
  const [messageInput, setMessageInput] = useState('');

  const [validationError, setValidationError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Preset Loaders for quick demo (populates both Link & Description together!)
  const loadPresetScam = () => {
    setUrlInput('https://apex-global-careers-hire.net/jobs/entry-data-spec');
    setDescInput('We are looking for an Entry-Level Remote Data Specialist. $65/hr. High payout. Mandatory requirement: Candidates must accept a $2,000 cashier check reimbursement to purchase Apple hardware from our designated portal.');
    setFileName('Apex_Global_Offer_Letter.pdf');
    setCompanyName('Apex Global Careers');
    setRecruiterEmail('recruitment@apex-global-hr.net');
    setRecruiterName('Sarah Jenkins');
    setRecruiterPhone('');
    setMessageInput('Hello! Your application for Data Entry Specialist has been approved. Please message our hiring manager on Telegram @apex_hr_dept immediately to claim your $2,000 equipment check.');
    setValidationError('');
    loadReport(mockAnalysisHighRisk);
  };

  const loadPresetIndiaScam = () => {
    setUrlInput('https://excel-careers-india.in/jobs/accounts-assistant');
    setDescInput('Accounts Assistant Job Openings in Mumbai | ₹25,000/month Salary | Placement Guarantee. Join our Placement Consultant today and get placed in top MNCs. Our consultancy charges are ₹5,000 refundable security deposit only.');
    setFileName('Excel_Placement_Agreement.pdf');
    setCompanyName('Excel Career Solutions');
    setRecruiterEmail('placementfee@gmail.com');
    setRecruiterName('Rajesh Kumar (WhatsApp Consultant)');
    setRecruiterPhone('+91 9812345678');
    setMessageInput('Congratulations! Selected for MNC Accounts role. Pay ₹5,000 refundable security deposit via UPI/GPay to confirm slot. Contact WhatsApp: +91 9812345678.');
    setValidationError('');
    loadReport(mockAnalysisIndiaScam);
  };

  const loadPresetTelegramScam = () => {
    setUrlInput('https://global-fast-remote-jobs.site/apply');
    setDescInput('Remote Crypto Portfolio & Task Specialist. Guaranteed $1,500 weekly payout + free MacBook Pro shipped immediately. Complete daily simple tasks and earn commission.');
    setFileName('Contract_Bond_Agreement.pdf');
    setCompanyName('Global Fast Remote Jobs');
    setRecruiterEmail('hr@global-fast-remote-jobs.site');
    setRecruiterName('Alex Vance (@fast_crypto_jobs)');
    setRecruiterPhone('');
    setMessageInput('Hi! To activate your daily $1,500 crypto task bot, connect with our supervisor on Telegram @fast_crypto_jobs.');
    setValidationError('');
    loadReport(mockAnalysisTelegramScam);
  };

  const loadPresetSafe = () => {
    setUrlInput('https://stripe.com/jobs/listing/software-engineer-intern');
    setDescInput('Stripe is hiring Software Engineer Interns for Summer 2026. You will build payment infrastructure with Ruby, Go, and React. $55/hr + housing stipend. Official university recruiting program.');
    setFileName('Stripe_Internship_Offer_2026.pdf');
    setCompanyName('Stripe');
    setRecruiterEmail('university-hiring@stripe.com');
    setRecruiterName('Elena Rostova');
    setRecruiterPhone('');
    setMessageInput('Hi Nihar, Thank you for interviewing with Stripe. We are thrilled to offer you a Software Engineer Internship position for Summer 2026!');
    setValidationError('');
    loadReport(mockAnalysisLowRisk);
  };

  const MAX_FILE_BYTES = 10 * 1024 * 1024; // 10MB, matches the upload hint

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > MAX_FILE_BYTES) {
        setValidationError(
          `"${file.name}" is ${(file.size / (1024 * 1024)).toFixed(1)} MB — the limit is 10 MB. Please export or scan the document smaller.`
        );
        return;
      }
      setFileObject(file);
      setFileName(file.name);
      setValidationError('');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setValidationError('');

    const trimmedUrl = urlInput.trim();
    const trimmedDesc = descInput.trim();
    const trimmedMsg = messageInput.trim();

    // Check if at least one input across all tabs is provided.
    // A real file object is required — a display name alone is not an upload.
    if (!trimmedUrl && !trimmedDesc && !trimmedMsg && !fileObject && !recruiterEmail.trim()) {
      setValidationError('Please provide a Job URL, Description text, Email/Message, or upload a Document.');
      return;
    }

    setIsSubmitting(true);

    try {
      // 1. Live API submission to FastAPI backend (all provided fields submitted together).
      // When a file is present the multipart endpoint is used so the document
      // actually reaches the analysis pipeline.
      let apiResult;
      if (fileObject) {
        const formData = new FormData();
        formData.append('document', fileObject);
        if (trimmedUrl) formData.append('url', trimmedUrl);
        if (trimmedDesc) formData.append('description', trimmedDesc);
        if (companyName.trim()) formData.append('company_name', companyName.trim());
        if (recruiterEmail.trim()) formData.append('recruiter_email', recruiterEmail.trim());
        if (recruiterName.trim()) formData.append('recruiter_name', recruiterName.trim());
        if (recruiterPhone.trim()) formData.append('recruiter_phone', recruiterPhone.trim());
        if (trimmedMsg) formData.append('message', trimmedMsg);
        formData.append('consent_for_external_lookups', 'true');

        apiResult = await submitAssessmentWithUpload(formData);
      } else {
        apiResult = await submitAssessment({
          url: trimmedUrl || undefined,
          description: trimmedDesc || undefined,
          company_name: companyName.trim() || undefined,
          recruiter_email: recruiterEmail.trim() || undefined,
          recruiter_name: recruiterName.trim() || undefined,
          recruiter_phone: recruiterPhone.trim() || undefined,
          message: trimmedMsg || undefined,
        });
      }

      const formatted = formatBackendResponse(apiResult, {
        url: trimmedUrl,
        description: trimmedDesc || trimmedMsg,
        company_name: companyName.trim(),
        recruiter_email: recruiterEmail,
        recruiter_name: recruiterName,
      });

      loadReport(formatted);
      navigate('/analyze/processing');
    } catch (err) {
      // Honest failure: report what went wrong instead of fabricating a verdict.
      console.error('Assessment submission failed:', err);
      const detail = err?.message || 'Unknown error';
      setValidationError(
        `Analysis unavailable — no report was generated. ${detail}. ` +
        'If the backend is not running, start it (see COMMANDS.md); no mock result will be shown.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  // Tabs definition with active indicators when content exists
  const tabs = [
    { id: 'url', label: 'Job URL', icon: Link2, hasValue: !!urlInput.trim() },
    { id: 'description', label: 'Job Description', icon: FileText, hasValue: !!descInput.trim() },
    { id: 'document', label: 'Upload Document', icon: Upload, hasValue: !!fileName },
    { id: 'recruiter', label: 'Recruiter Details', icon: UserCheck, hasValue: !!(companyName.trim() || recruiterEmail.trim() || recruiterName.trim() || recruiterPhone.trim()) },
    { id: 'email', label: 'Email / Message', icon: Mail, hasValue: !!messageInput.trim() },
  ];

  return (
    <div className="max-w-[1000px] mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
      
      {/* Header Banner */}
      <div className="text-center space-y-3">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-secondary-container text-primary text-xs font-semibold">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Multi-Modal Scam Analysis • Free & Open</span>
        </div>
        <h1 className="font-serif text-3xl sm:text-4xl font-semibold text-ink">
          Analyze Job & Internship Opportunity
        </h1>
        <p className="text-sm text-ink-muted max-w-xl mx-auto">
          You can provide a <strong>Job URL</strong>, paste <strong>Job Description</strong> text, or <strong>both together</strong>. You can also attach offer letters or recruiter messages for deeper verification.
        </p>
      </div>

      {/* Preset Demo Buttons */}
      <div className="bg-surface-2 p-4 rounded-2xl border border-ink/5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs font-semibold text-ink-muted">
          <Sparkles className="w-4 h-4 text-primary" />
          <span>1-Click Test Presets:</span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={loadPresetScam}
            className="px-3.5 py-1.5 rounded-full bg-risk-high-bg text-risk-high text-xs font-semibold hover:bg-risk-high-bg/80 transition-all flex items-center gap-1.5"
          >
            <span>⚡ Check Reimbursement Scam</span>
          </button>
          <button
            type="button"
            onClick={loadPresetIndiaScam}
            className="px-3.5 py-1.5 rounded-full bg-amber-500/10 text-amber-700 dark:text-amber-400 text-xs font-semibold hover:bg-amber-500/20 transition-all flex items-center gap-1.5"
          >
            <span>⚡ ₹5,000 Placement Deposit Scam</span>
          </button>
          <button
            type="button"
            onClick={loadPresetTelegramScam}
            className="px-3.5 py-1.5 rounded-full bg-purple-500/10 text-purple-700 dark:text-purple-400 text-xs font-semibold hover:bg-purple-500/20 transition-all flex items-center gap-1.5"
          >
            <span>⚡ Telegram Crypto Task Scam</span>
          </button>
          <button
            type="button"
            onClick={loadPresetSafe}
            className="px-3.5 py-1.5 rounded-full bg-risk-low-bg text-risk-low text-xs font-semibold hover:bg-risk-low-bg/80 transition-all flex items-center gap-1.5"
          >
            <span>⚡ Verified Safe Enterprise</span>
          </button>
        </div>
      </div>

      {/* Main Analysis Card */}
      <div className="bg-surface rounded-3xl shadow-floating border border-ink/5 overflow-hidden">
        
        {/* Navigation Tabs with Active Dots */}
        <div className="flex border-b border-ink/5 overflow-x-auto scrollbar-none bg-surface-2/50 p-2 gap-1">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isCurrent = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-5 py-3 rounded-2xl text-xs font-semibold whitespace-nowrap transition-all relative ${
                  isCurrent
                    ? 'bg-primary text-surface shadow-subtle'
                    : 'text-ink-muted hover:text-ink hover:bg-surface/80'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{tab.label}</span>
                {tab.hasValue && (
                  <span
                    className={`w-2 h-2 rounded-full ${isCurrent ? 'bg-secondary-container' : 'bg-primary'}`}
                    title="Contains data"
                  />
                )}
              </button>
            );
          })}
        </div>

        {/* Tab Form Content */}
        <form onSubmit={handleSubmit} className="p-6 sm:p-10 space-y-6">
          
          {validationError && (
            <div className="p-4 rounded-2xl bg-risk-high-bg border border-risk-high/20 text-risk-high text-xs font-semibold flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{validationError}</span>
            </div>
          )}

          {/* TAB 1: JOB URL */}
          {activeTab === 'url' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <label className="block text-xs font-semibold uppercase tracking-wider text-ink-muted">
                  Job Posting or Career Page URL
                </label>
                {descInput.trim() && (
                  <span className="text-[11px] text-primary font-medium flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Description text also provided in Tab 2
                  </span>
                )}
              </div>
              <input
                type="url"
                value={urlInput}
                onChange={(e) => { setUrlInput(e.target.value); setValidationError(''); }}
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
              <div className="flex items-center justify-between">
                <label className="block text-xs font-semibold uppercase tracking-wider text-ink-muted">
                  Pasted Job Description Text
                </label>
                {urlInput.trim() && (
                  <span className="text-[11px] text-primary font-medium flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Job URL also provided in Tab 1
                  </span>
                )}
              </div>
              <textarea
                rows={6}
                value={descInput}
                onChange={(e) => { setDescInput(e.target.value); setValidationError(''); }}
                placeholder="Paste the full job post, responsibilities, compensation terms, and contact instructions..."
                className="w-full bg-canvas border border-ink/10 rounded-2xl p-5 text-sm text-ink placeholder-ink-subtle focus:outline-none focus:border-primary transition-all resize-none font-sans"
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
              <label className="border-2 border-dashed border-ink/15 bg-canvas rounded-3xl p-8 text-center space-y-3 hover:border-primary/40 transition-all cursor-pointer block">
                <input
                  type="file"
                  accept=".pdf,.docx,.txt"
                  onChange={handleFileChange}
                  className="hidden"
                />
                <div className="w-12 h-12 rounded-full bg-secondary-container text-primary flex items-center justify-center mx-auto">
                  <Upload className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-ink">
                    {fileName ? fileName : 'Click to select or drag PDF offer document'}
                  </p>
                  <p className="text-xs text-ink-subtle mt-1">Supports PDF, DOCX (Max 10MB)</p>
                </div>
              </label>
            </div>
          )}

          {/* TAB 4: RECRUITER DETAILS */}
          {activeTab === 'recruiter' && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-ink-muted mb-2">
                  Company / Organization Name
                </label>
                <input
                  type="text"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  placeholder="e.g. Tata Consultancy Services, Stripe, Infosys"
                  className="w-full bg-canvas border border-ink/10 rounded-2xl px-5 py-3 text-sm text-ink placeholder-ink-subtle focus:outline-none focus:border-primary"
                />
              </div>
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
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-ink-muted mb-2">
                  Recruiter Phone / WhatsApp Number
                </label>
                <input
                  type="tel"
                  value={recruiterPhone}
                  onChange={(e) => setRecruiterPhone(e.target.value)}
                  placeholder="e.g. +91 9876543210"
                  className="w-full bg-canvas border border-ink/10 rounded-2xl px-5 py-3 text-sm text-ink placeholder-ink-subtle focus:outline-none focus:border-primary"
                />
              </div>
              <p className="text-xs text-ink-subtle">
                Validates MX records, DMARC/SPF authentication headers, corporate directory alignment, and WhatsApp/Telegram identity.
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
                className="w-full bg-canvas border border-ink/10 rounded-2xl p-5 text-sm text-ink placeholder-ink-subtle focus:outline-none focus:border-primary transition-all resize-none font-sans"
              />
              <p className="text-xs text-ink-subtle">
                Detects messaging platform redirection (Telegram/Signal), check reimbursement language, and fake interview steps.
              </p>
            </div>
          )}

          {/* Cross-Tab Inputs Summary Banner */}
          {(urlInput.trim() && descInput.trim()) && (
            <div className="p-3.5 px-5 rounded-2xl bg-secondary-container/40 border border-primary/20 flex items-center gap-2 text-xs text-ink">
              <CheckCircle2 className="w-4 h-4 text-primary flex-shrink-0" />
              <span><strong>Cross-Verification Active:</strong> Both Job URL and Description text are provided and will be evaluated together.</span>
            </div>
          )}

          {/* Submit Action */}
          <div className="pt-4 border-t border-ink/5 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-xs text-ink-muted">
              <ShieldCheck className="w-4 h-4 text-primary" />
              <span>Multi-layer AI verification protocol active (Free • No sign-in required)</span>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full sm:w-auto px-8 py-3.5 rounded-full bg-primary text-surface text-xs font-bold shadow-subtle hover:bg-primary-container transition-all flex items-center justify-center gap-2 disabled:opacity-50"
            >
              <span>{isSubmitting ? 'Scanning...' : 'Run HireShield Scan'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>

        </form>
      </div>

    </div>
  );
};
