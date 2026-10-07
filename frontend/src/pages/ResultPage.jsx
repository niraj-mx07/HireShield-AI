import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  ShieldCheck,
  ArrowLeft,
  Download,
  RefreshCw,
  PlusCircle,
  Lock,
  CheckCircle2,
  AlertTriangle,
  UserCheck,
  Calendar,
  ExternalLink,
  Sparkles,
  FileText,
  User,
  Mail,
  Phone,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { RiskScoreGauge } from '../components/RiskScoreGauge';
import { RiskFactorCard } from '../components/RiskFactorCard';
import { VerificationMatrixItem } from '../components/VerificationMatrixItem';
import { generateAssessmentPDF } from '../services/pdfGenerator';

export const ResultPage = () => {
  const navigate = useNavigate();
  const { isLoggedIn, activeReport, openAuthModal } = useAuth();
  const [downloadToast, setDownloadToast] = useState(false);

  const report = activeReport;

  // Safe fallback if report is missing
  if (!report) {
    return (
      <div className="max-w-[800px] mx-auto px-4 py-20 text-center space-y-6">
        <div className="w-16 h-16 rounded-full bg-secondary-container text-primary flex items-center justify-center mx-auto shadow-subtle">
          <ShieldCheck className="w-8 h-8" />
        </div>
        <div className="space-y-2">
          <h1 className="font-serif text-3xl font-semibold text-ink">
            No Active Assessment Found
          </h1>
          <p className="text-sm text-ink-muted max-w-md mx-auto">
            Please run an opportunity scan or select a previous report from your assessment history.
          </p>
        </div>
        <Link
          to="/analyze"
          className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-primary text-surface text-xs font-bold shadow-subtle hover:bg-primary-container transition-all"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Go to Analysis Page</span>
        </Link>
      </div>
    );
  }

  const handleDownloadPDF = () => {
    if (isLoggedIn) {
      try {
        generateAssessmentPDF(report);
        setDownloadToast(true);
        setTimeout(() => setDownloadToast(false), 4000);
      } catch (err) {
        console.error('PDF generation error:', err);
      }
    } else {
      openAuthModal('login', () => {
        generateAssessmentPDF(report);
        setDownloadToast(true);
        setTimeout(() => setDownloadToast(false), 4000);
      });
    }
  };

  // -------------------------------------------------------------------------
  // Derive active Source Material Badges
  // -------------------------------------------------------------------------
  const rawSources = report.detectedSources || report.activeInputs || [];
  const sourceBadges = [];

  const hasSource = (keyword) =>
    rawSources.some((s) => typeof s === 'string' && s.toLowerCase().includes(keyword.toLowerCase()));

  // 1. Job URL / Career Page
  if (report.url || hasSource('url') || hasSource('career')) {
    sourceBadges.push({
      id: 'url',
      label: '🌐 Job URL / Career Page',
    });
  }

  // 2. Pasted Job Description
  if (
    hasSource('description') ||
    hasSource('pasted') ||
    hasSource('transcript') ||
    rawSources.includes('Pasted Job Description')
  ) {
    sourceBadges.push({
      id: 'description',
      label: '📝 Pasted Job Description',
    });
  }

  // 3. Offer Letter / Contract PDF
  if (
    hasSource('document') ||
    hasSource('pdf') ||
    hasSource('offer letter') ||
    hasSource('contract') ||
    rawSources.includes('Offer Letter / Contract PDF')
  ) {
    sourceBadges.push({
      id: 'document',
      label: '📄 Offer Letter / Contract PDF',
    });
  }

  // 4. Recruiter Details
  if (
    report.recruiterName ||
    report.recruiterEmail ||
    report.recruiterPhone ||
    report.recruiterLinkedin ||
    hasSource('recruiter') ||
    rawSources.includes('Recruiter Details')
  ) {
    sourceBadges.push({
      id: 'recruiter',
      label: '👤 Recruiter Details',
    });
  }

  // 5. Email / Message
  if (
    hasSource('email') ||
    hasSource('message') ||
    hasSource('chat') ||
    rawSources.includes('Email / Message')
  ) {
    sourceBadges.push({
      id: 'message',
      label: '💬 Email / Message',
    });
  }

  // Fallback badge if empty
  if (sourceBadges.length === 0) {
    sourceBadges.push({
      id: 'default',
      label: '📝 Pasted Job Description',
    });
  }

  const hasRecruiterInfo = Boolean(
    report.recruiterName ||
    report.recruiterEmail ||
    report.recruiterPhone ||
    report.recruiterLinkedin
  );

  return (
    <div className="max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-10">
      
      {/* Top Bar: Back Link & Action Buttons */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-ink/5 pb-6">
        <Link
          to="/analyze"
          className="inline-flex items-center gap-2 text-xs font-semibold text-ink-muted hover:text-ink transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Analyze Another Opportunity</span>
        </Link>

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => navigate('/analyze/processing')}
            className="px-4 py-2 rounded-full bg-surface border border-ink/10 text-xs font-semibold text-ink-muted hover:text-ink hover:bg-surface-2 transition-all flex items-center gap-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Re-run Scan</span>
          </button>

          <button
            onClick={handleDownloadPDF}
            className="px-4 py-2 rounded-full bg-surface border border-ink/10 text-xs font-semibold text-ink-muted hover:text-ink hover:bg-surface-2 transition-all flex items-center gap-1.5"
            title={isLoggedIn ? 'Download PDF Report' : 'Sign in to download PDF Report'}
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download PDF Report</span>
            {!isLoggedIn && <Lock className="w-3 h-3 text-ink-subtle ml-0.5" />}
          </button>

          <Link
            to="/analyze"
            className="px-5 py-2 rounded-full bg-primary text-surface text-xs font-semibold shadow-subtle hover:bg-primary-container transition-all flex items-center gap-1.5"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>Scan Another</span>
          </Link>
        </div>
      </div>

      {/* PDF Download Toast Notification */}
      {downloadToast && (
        <div className="bg-primary text-surface px-6 py-3 rounded-2xl text-xs font-semibold shadow-floating flex items-center justify-between animate-in fade-in duration-300">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-secondary-container" />
            <span>Official HireShield Risk Report generated and downloaded successfully!</span>
          </div>
          <button onClick={() => setDownloadToast(false)} className="underline text-[10px]">Dismiss</button>
        </div>
      )}

      {/* GUEST MODE SAVE BANNER */}
      {!isLoggedIn && (
        <div className="bg-secondary-container/60 border border-primary/20 rounded-3xl p-6 sm:p-8 flex flex-col sm:flex-row items-center justify-between gap-6 shadow-subtle">
          <div className="space-y-1 text-center sm:text-left">
            <div className="flex items-center justify-center sm:justify-start gap-2 text-primary font-semibold text-xs uppercase tracking-wider">
              <Sparkles className="w-4 h-4" />
              <span>Guest Mode Analysis Active</span>
            </div>
            <h3 className="font-serif text-xl font-semibold text-ink">
              Save this report to your profile & unlock PDF export
            </h3>
            <p className="text-xs text-ink-muted">
              Risk analysis is always free. Create an account to save historical scans, download audit PDFs, and set job alert monitors.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => openAuthModal('signup')}
              className="px-6 py-3 rounded-full bg-primary text-surface text-xs font-bold shadow-subtle hover:bg-primary-container transition-all whitespace-nowrap"
            >
              Create Free Account
            </button>
            <button
              onClick={() => openAuthModal('login')}
              className="px-5 py-3 rounded-full bg-surface border border-ink/10 text-xs font-semibold text-ink hover:bg-surface-2 transition-all whitespace-nowrap"
            >
              Sign In
            </button>
          </div>
        </div>
      )}

      {/* HERO REPORT CARD */}
      <div className="bg-surface rounded-3xl p-8 sm:p-12 shadow-floating border border-ink/5">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
          
          {/* Left: Dynamic Circular Risk Gauge */}
          <div className="lg:col-span-4 flex justify-center border-b lg:border-b-0 lg:border-r border-ink/5 pb-8 lg:pb-0 lg:pr-8">
            <RiskScoreGauge score={report.score} riskLevel={report.riskLevel} size={210} />
          </div>

          {/* Right: Executive Summary & Opportunity Details */}
          <div className="lg:col-span-8 space-y-6">
            <div>
              <div className="flex items-center gap-2 text-xs font-semibold text-ink-subtle uppercase tracking-wider mb-1.5">
                <span>Scan Report #{report.id}</span>
                <span>•</span>
                <span className="text-primary font-bold">{report.confidence} Confidence Score</span>
              </div>

              {/* Dynamic Job Title Heading */}
              <h1 className="font-serif text-3xl sm:text-4xl font-semibold text-ink">
                {report.jobTitle || 'Job Opportunity'}
              </h1>

              {/* Dynamic Company Name & Subtitle */}
              <p className="text-sm font-medium text-ink-muted mt-1.5 flex flex-wrap items-center gap-1.5">
                Company: <span className="font-bold text-primary">{report.companyName || report.company || 'N/A'}</span>
                {report.jobTitle && (
                  <>
                    <span className="text-ink-subtle">•</span>
                    <span>{report.jobTitle}</span>
                  </>
                )}
              </p>

              {/* Source Material Metadata Badges */}
              <div className="flex flex-wrap items-center gap-2 pt-3">
                <span className="text-[11px] font-semibold text-ink-subtle uppercase tracking-wider mr-1">
                  Sources Scanned:
                </span>
                {sourceBadges.map((badge) => (
                  <span
                    key={badge.id}
                    className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-surface-2 border border-ink/10 text-ink shadow-2xs hover:border-ink/20 transition-all"
                  >
                    {badge.label}
                  </span>
                ))}
              </div>
            </div>

            {/* Executive Summary */}
            <div className="bg-surface-2 rounded-2xl p-5 border border-ink/5 space-y-2">
              <div className="text-xs font-bold uppercase tracking-wider text-ink-subtle flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-primary" />
                <span>Executive AI Synthesis</span>
              </div>
              <p className="text-xs sm:text-sm text-ink leading-relaxed">
                {report.summary}
              </p>
            </div>

            {/* Metadata Pills Row */}
            <div className="flex flex-wrap gap-4 text-xs text-ink-muted pt-2 border-t border-ink/5">
              <div className="flex items-center gap-1.5">
                <Calendar className="w-4 h-4 text-primary" />
                <span>Scanned: {report.scanDate}</span>
              </div>
              {report.url && (
                <div className="flex items-center gap-1.5 truncate max-w-xs">
                  <ExternalLink className="w-4 h-4 text-primary flex-shrink-0" />
                  <span className="truncate">{report.url}</span>
                </div>
              )}
            </div>
          </div>

        </div>
      </div>

      {/* RECRUITER & CONTACT CREDENTIALS CARD */}
      {hasRecruiterInfo && (
        <div className="bg-surface rounded-3xl p-6 sm:p-8 shadow-floating border border-ink/5 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-ink/5 pb-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-primary text-xs font-bold uppercase tracking-wider">
                <UserCheck className="w-4 h-4" />
                <span>Recruiter & Contact Information</span>
              </div>
              <h2 className="font-serif text-xl sm:text-2xl font-semibold text-ink">
                Hiring Representative Credentials
              </h2>
            </div>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-secondary-container/60 text-primary text-xs font-semibold self-start sm:self-auto">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Extracted From Submission</span>
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Recruiter Name */}
            <div className="bg-surface-2/70 rounded-2xl p-4 border border-ink/5 space-y-1">
              <div className="text-[10px] font-semibold text-ink-subtle uppercase tracking-wider flex items-center gap-1.5">
                <User className="w-3.5 h-3.5 text-primary" />
                <span>Recruiter Name</span>
              </div>
              <p className="text-sm font-bold text-ink truncate" title={report.recruiterName || 'Not Provided'}>
                {report.recruiterName || 'Not Provided'}
              </p>
            </div>

            {/* Email */}
            <div className="bg-surface-2/70 rounded-2xl p-4 border border-ink/5 space-y-1">
              <div className="text-[10px] font-semibold text-ink-subtle uppercase tracking-wider flex items-center gap-1.5">
                <Mail className="w-3.5 h-3.5 text-primary" />
                <span>Contact Email</span>
              </div>
              {report.recruiterEmail ? (
                <a
                  href={`mailto:${report.recruiterEmail}`}
                  className="text-sm font-bold text-primary hover:underline truncate block"
                  title={report.recruiterEmail}
                >
                  {report.recruiterEmail}
                </a>
              ) : (
                <p className="text-sm font-medium text-ink-subtle">Not Provided</p>
              )}
            </div>

            {/* Phone / WhatsApp */}
            <div className="bg-surface-2/70 rounded-2xl p-4 border border-ink/5 space-y-1">
              <div className="text-[10px] font-semibold text-ink-subtle uppercase tracking-wider flex items-center gap-1.5">
                <Phone className="w-3.5 h-3.5 text-primary" />
                <span>Phone / Contact</span>
              </div>
              <p className="text-sm font-bold text-ink truncate" title={report.recruiterPhone || 'Not Provided'}>
                {report.recruiterPhone || 'Not Provided'}
              </p>
            </div>

            {/* LinkedIn Profile */}
            <div className="bg-surface-2/70 rounded-2xl p-4 border border-ink/5 space-y-1">
              <div className="text-[10px] font-semibold text-ink-subtle uppercase tracking-wider flex items-center gap-1.5">
                <ExternalLink className="w-3.5 h-3.5 text-primary" />
                <span>LinkedIn Profile</span>
              </div>
              {report.recruiterLinkedin ? (
                <a
                  href={report.recruiterLinkedin}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-bold text-primary hover:underline truncate flex items-center gap-1"
                  title={report.recruiterLinkedin}
                >
                  <span className="truncate">View Profile</span>
                  <ExternalLink className="w-3 h-3 flex-shrink-0" />
                </a>
              ) : (
                <p className="text-sm font-medium text-ink-subtle">Not Provided</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* RISK FACTORS BREAKDOWN SECTION */}
      <div className="space-y-6">
        <div className="space-y-1">
          <h2 className="font-serif text-2xl font-semibold text-ink">
            Itemized Risk Factors Breakdown
          </h2>
          <p className="text-xs text-ink-muted">
            Detailed evaluation of signals extracted from URL registration, PDF text, and recruiter credentials.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {report.riskFactors.map((rf) => (
            <RiskFactorCard
              key={rf.id}
              severity={rf.severity}
              severityScore={rf.severityScore}
              category={rf.category}
              headline={rf.headline}
              description={rf.description}
              evidence={rf.evidence}
              categoryType={rf.categoryType}
            />
          ))}
        </div>
      </div>

      {/* VERIFICATION MATRIX SECTION */}
      <div className="space-y-6">
        <div className="space-y-1">
          <h2 className="font-serif text-2xl font-semibold text-ink">
            Multi-Layer Verification Matrix
          </h2>
          <p className="text-xs text-ink-muted">
            Pass, Fail, and Caution indicators across standard corporate credibility checks.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {report.matrix.map((item, idx) => (
            <VerificationMatrixItem
              key={idx}
              checkName={item.checkName}
              status={item.status}
              explanation={item.explanation}
              evidenceFooter={item.evidenceFooter}
            />
          ))}
        </div>
      </div>

    </div>
  );
};

