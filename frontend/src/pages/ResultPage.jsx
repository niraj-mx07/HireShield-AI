import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ShieldCheck, ArrowLeft, Download, RefreshCw, PlusCircle, Lock, CheckCircle2, AlertTriangle, UserCheck, Calendar, ExternalLink, Sparkles } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { RiskScoreGauge } from '../components/RiskScoreGauge';
import { RiskFactorCard } from '../components/RiskFactorCard';
import { VerificationMatrixItem } from '../components/VerificationMatrixItem';

export const ResultPage = () => {
  const navigate = useNavigate();
  const { isLoggedIn, activeReport, toggleAuth } = useAuth();
  const [downloadToast, setDownloadToast] = useState(false);

  const report = activeReport;

  const handleDownloadPDF = () => {
    setDownloadToast(true);
    setTimeout(() => setDownloadToast(false), 3000);
  };

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
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download PDF</span>
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
            <span>Mock PDF Report generated successfully! Preparing download stream...</span>
          </div>
          <button onClick={() => setDownloadToast(false)} className="underline text-[10px]">Dismiss</button>
        </div>
      )}

      {/* GUEST MODE SAVE BANNER */}
      {!isLoggedIn && (
        <div className="bg-secondary-container/60 border border-primary/20 rounded-3xl p-6 sm:p-8 flex flex-col sm:flex-row items-center justify-between gap-6 shadow-subtle">
          <div className="space-y-1 text-center sm:text-left">
            <div className="flex items-center justify-center sm:justify-start gap-2 text-primary font-semibold text-xs uppercase tracking-wider">
              <Lock className="w-4 h-4" />
              <span>Guest Mode Analysis</span>
            </div>
            <h3 className="font-serif text-xl font-semibold text-ink">
              Save this report to your profile history?
            </h3>
            <p className="text-xs text-ink-muted">
              Simulate logging in to access saved historical scans, monitoring alerts, and PDF exports.
            </p>
          </div>
          <button
            onClick={toggleAuth}
            className="px-6 py-3 rounded-full bg-primary text-surface text-xs font-bold shadow-subtle hover:bg-primary-container transition-all whitespace-nowrap"
          >
            Simulate Login Now
          </button>
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
              <div className="flex items-center gap-2 text-xs font-semibold text-ink-subtle uppercase tracking-wider mb-1">
                <span>Scan Report #{report.id}</span>
                <span>•</span>
                <span className="text-primary font-bold">{report.confidence} Confidence Score</span>
              </div>

              <h1 className="font-serif text-3xl sm:text-4xl font-semibold text-ink">
                {report.jobTitle}
              </h1>
              <p className="text-sm font-semibold text-ink-muted mt-1">
                Company: <span className="text-ink">{report.company}</span>
              </p>
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
