import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Search,
  Filter,
  Lock,
  ArrowRight,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  ShieldCheck,
  Sparkles,
  FileText,
  PlusCircle,
  Download,
  Trash2,
  RefreshCw,
  Database,
  Eye,
  X,
  ExternalLink,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { getScanCounts } from '../data/mockData';
import { generateAssessmentPDF } from '../services/pdfGenerator';

export const HistoryPage = () => {
  const {
    user,
    isLoggedIn,
    userHistory,
    openAuthModal,
    loadReport,
    dbSyncStatus,
    lastSyncedAt,
    refreshDbSync,
    deleteReportFromHistory,
  } = useAuth();
  const navigate = useNavigate();

  const [searchQuery, setSearchQuery] = useState('');
  const [riskFilter, setRiskFilter] = useState('all');
  const [sortBy, setSortBy] = useState('newest'); // 'newest' | 'highest' | 'lowest'
  const [deletingId, setDeletingId] = useState(null);
  const [previewItem, setPreviewItem] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [pdfToast, setPdfToast] = useState(false);

  // Locked Guest Preview State if not logged in
  if (!isLoggedIn) {
    return (
      <div className="max-w-[800px] mx-auto px-4 py-20 text-center space-y-6">
        <div className="w-20 h-20 rounded-full bg-secondary-container text-primary flex items-center justify-center mx-auto shadow-subtle">
          <Lock className="w-10 h-10" />
        </div>
        <div className="space-y-2">
          <h1 className="font-serif text-3xl font-semibold text-ink">
            Personal Assessment History
          </h1>
          <p className="text-sm text-ink-muted max-w-md mx-auto">
            Risk calculation is always free and open. Sign in or create a free candidate account to track your past opportunity scans, export PDF reports, and view historical evidence.
          </p>
        </div>
        <div className="flex items-center justify-center gap-3">
          <button
            onClick={() => openAuthModal('signup')}
            className="px-8 py-3.5 rounded-full bg-primary text-surface text-xs font-bold shadow-subtle hover:bg-primary-container transition-all"
          >
            Create Free Account
          </button>
          <button
            onClick={() => openAuthModal('login')}
            className="px-6 py-3.5 rounded-full bg-surface border border-ink/10 text-xs font-semibold text-ink hover:bg-surface-2 transition-all"
          >
            Sign In
          </button>
        </div>
      </div>
    );
  }

  const historySource = userHistory || [];
  const counts = getScanCounts(historySource);

  // Filter items by search query and risk level
  let filteredHistory = historySource.filter((item) => {
    const jobStr = (item.jobTitle || item.title || '').toLowerCase();
    const compStr = (item.company || '').toLowerCase();
    const query = searchQuery.toLowerCase();
    const matchesSearch = jobStr.includes(query) || compStr.includes(query);
    const matchesFilter = riskFilter === 'all' || item.riskLevel === riskFilter;
    return matchesSearch && matchesFilter;
  });

  // Sorting
  filteredHistory = [...filteredHistory].sort((a, b) => {
    const scoreA = Number(a.riskScore ?? a.score ?? 0);
    const scoreB = Number(b.riskScore ?? b.score ?? 0);
    if (sortBy === 'highest') return scoreB - scoreA;
    if (sortBy === 'lowest') return scoreA - scoreB;
    // default: newest first
    const dateA = new Date(a.date || a.scanDate || 0).getTime();
    const dateB = new Date(b.date || b.scanDate || 0).getTime();
    return dateB - dateA;
  });

  const handleSelectReport = (item) => {
    loadReport(item.payload || item);
    navigate('/analyze/result');
  };

  const handleDownloadPDF = (e, item) => {
    e.stopPropagation();
    try {
      generateAssessmentPDF(item.payload || item);
      setPdfToast(true);
      setTimeout(() => setPdfToast(false), 3000);
    } catch (err) {
      console.error('PDF error:', err);
    }
  };

  const handleDeleteScan = async (e, id) => {
    e.stopPropagation();
    if (confirm('Delete this assessment record from your history?')) {
      setDeletingId(id);
      await deleteReportFromHistory(id);
      setDeletingId(null);
    }
  };

  const handleManualSync = async () => {
    setIsRefreshing(true);
    refreshDbSync();
    setTimeout(() => setIsRefreshing(false), 800);
  };

  return (
    <div className="max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
      {/* Toast Notification for PDF */}
      {pdfToast && (
        <div className="fixed bottom-6 right-6 z-50 bg-ink text-surface text-xs font-semibold px-4 py-3 rounded-2xl shadow-floating flex items-center gap-2 animate-in fade-in duration-200">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>Audit Report PDF downloaded successfully!</span>
        </div>
      )}

      {/* Header with Dynamic User Name */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-secondary-container text-primary text-xs font-semibold">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Archive • {user?.name || 'Account'}</span>
            </div>
          </div>

          <h1 className="font-serif text-3xl sm:text-4xl font-semibold text-ink">
            Saved Risk Reports
          </h1>
          <p className="text-xs text-ink-muted">
            Saved assessments for <span className="font-semibold text-ink">{user?.email}</span> •{' '}
            <span className="font-medium text-ink">{historySource.length} Total Records</span>
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <button
            onClick={handleManualSync}
            title="Refresh database sync"
            className="p-2.5 rounded-full bg-surface border border-ink/10 text-ink-muted hover:text-ink hover:bg-surface-2 transition-all shadow-subtle flex items-center justify-center"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-primary' : ''}`} />
          </button>

          <Link
            to="/analyze"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-primary text-surface text-xs font-semibold shadow-subtle hover:bg-primary-container transition-all"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>New Opportunity Scan</span>
          </Link>
        </div>
      </div>

      {/* Filter, Search & Sorting Bar */}
      <div className="bg-surface p-4 rounded-3xl shadow-subtle border border-ink/5 flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4">
        {/* Search Input */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-ink-subtle absolute left-4 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by job title or company name..."
            className="w-full pl-10 pr-10 py-2.5 text-xs bg-canvas border border-ink/10 rounded-2xl text-ink placeholder-ink-subtle focus:outline-none focus:border-primary"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-subtle hover:text-ink p-1"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Filter Pills & Sort Selector */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Filter Pills */}
          <div className="flex flex-wrap items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
            {[
              { id: 'all', label: 'All Scans', count: counts.total },
              { id: 'high', label: 'High Risk', count: counts.highRisk },
              { id: 'moderate', label: 'Moderate', count: counts.moderate },
              { id: 'low', label: 'Verified Safe', count: counts.verifiedSafe },
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => setRiskFilter(f.id)}
                className={`px-3.5 py-1.5 rounded-full text-xs font-semibold transition-all flex items-center gap-1.5 whitespace-nowrap ${
                  riskFilter === f.id
                    ? 'bg-primary text-surface'
                    : 'bg-surface-2 text-ink-muted hover:text-ink'
                }`}
              >
                <span>{f.label}</span>
                <span
                  className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                    riskFilter === f.id ? 'bg-surface/20 text-surface' : 'bg-ink/5 text-ink-subtle'
                  }`}
                >
                  {f.count}
                </span>
              </button>
            ))}
          </div>

          {/* Sort Selector */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="bg-surface-2 border border-ink/10 rounded-2xl text-xs font-medium text-ink px-3 py-1.5 focus:outline-none focus:border-primary"
          >
            <option value="newest">Sort: Newest First</option>
            <option value="highest">Sort: Highest Risk First</option>
            <option value="lowest">Sort: Lowest Risk First</option>
          </select>
        </div>
      </div>

      {/* Scans Table / Empty State */}
      {filteredHistory.length === 0 ? (
        <div className="bg-surface rounded-3xl p-12 text-center border border-ink/5 space-y-4 shadow-subtle">
          <FileText className="w-12 h-12 text-ink-subtle mx-auto" />
          <div className="space-y-1">
            <h3 className="font-serif text-lg font-semibold text-ink">
              {historySource.length === 0 ? 'No Saved Scans Yet' : 'No Matching Scans Found'}
            </h3>
            <p className="text-xs text-ink-muted max-w-sm mx-auto">
              {historySource.length === 0
                ? 'Scan an opportunity on the Analyze page to automatically save your risk reports and evidence.'
                : 'Try adjusting your search terms or risk filter.'}
            </p>
          </div>
          {historySource.length === 0 && (
            <Link
              to="/analyze"
              className="inline-flex items-center gap-2 px-6 py-2.5 rounded-full bg-primary text-surface text-xs font-bold shadow-subtle hover:bg-primary-container"
            >
              <PlusCircle className="w-4 h-4" />
              <span>Scan Your First Job Listing</span>
            </Link>
          )}
        </div>
      ) : (
        <div className="bg-surface rounded-3xl shadow-subtle border border-ink/5 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-ink/5 bg-surface-2/40 text-[11px] font-semibold uppercase tracking-wider text-ink-subtle">
                  <th className="py-4 px-6">Opportunity & Role</th>
                  <th className="py-4 px-6">Company</th>
                  <th className="py-4 px-6">Scan Date</th>
                  <th className="py-4 px-6">Risk Score</th>
                  <th className="py-4 px-6">Recommendation</th>
                  <th className="py-4 px-6 text-right">Quick Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ink/5 text-xs font-medium text-ink">
                {filteredHistory.map((item) => {
                  const isHigh = item.riskLevel === 'high';
                  const isMod = item.riskLevel === 'moderate';
                  const badgeBg = isHigh
                    ? 'bg-risk-high-bg text-risk-high'
                    : isMod
                    ? 'bg-risk-moderate-bg text-risk-moderate'
                    : 'bg-risk-low-bg text-risk-low';

                  return (
                    <tr
                      key={item.id}
                      onClick={() => handleSelectReport(item)}
                      className="hover:bg-surface-2/50 transition-colors cursor-pointer group"
                    >
                      <td className="py-4 px-6 font-semibold group-hover:text-primary transition-colors">
                        <div className="flex items-center gap-2">
                          <span>{item.jobTitle || item.title || 'Opportunity Assessment'}</span>
                        </div>
                      </td>
                      <td className="py-4 px-6 text-ink-muted">{item.company || 'Hiring Entity'}</td>
                      <td className="py-4 px-6 text-ink-subtle">{item.date || item.scanDate}</td>
                      <td className="py-4 px-6">
                        <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold ${badgeBg}`}>
                          {item.riskScore ?? item.score ?? 0} / 100
                        </span>
                      </td>
                      <td className="py-4 px-6">
                        <span className="font-semibold text-[11px]">
                          {item.recommendation || item.verdict}
                        </span>
                      </td>
                      <td className="py-4 px-6 text-right">
                        <div className="inline-flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                          {/* Quick Preview Button */}
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setPreviewItem(item);
                            }}
                            title="Quick preview scan signals"
                            className="p-1.5 rounded-lg text-ink-subtle hover:text-ink hover:bg-surface-2 transition-colors"
                          >
                            <Eye className="w-4 h-4" />
                          </button>

                          {/* Quick Download PDF Button */}
                          <button
                            type="button"
                            onClick={(e) => handleDownloadPDF(e, item)}
                            title="Download PDF report"
                            className="p-1.5 rounded-lg text-ink-subtle hover:text-primary hover:bg-surface-2 transition-colors"
                          >
                            <Download className="w-4 h-4" />
                          </button>

                          {/* Delete Item Button */}
                          <button
                            type="button"
                            onClick={(e) => handleDeleteScan(e, item.id)}
                            title="Delete scan"
                            disabled={deletingId === item.id}
                            className="p-1.5 rounded-lg text-ink-subtle hover:text-red-500 hover:bg-red-50 transition-colors disabled:opacity-50"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>

                          {/* Full Report Link */}
                          <button
                            type="button"
                            onClick={() => handleSelectReport(item)}
                            className="inline-flex items-center gap-1 text-primary text-xs font-semibold hover:underline ml-1"
                          >
                            <span>Open</span>
                            <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Quick Scan Details Preview Modal */}
      {previewItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/60 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="relative w-full max-w-lg bg-surface border border-ink/10 rounded-3xl shadow-floating p-6 sm:p-8 space-y-5 max-h-[90vh] overflow-y-auto">
            <button
              onClick={() => setPreviewItem(null)}
              className="absolute top-4 right-4 p-2 rounded-full text-ink-muted hover:text-ink hover:bg-surface-2 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="space-y-1">
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-secondary-container text-primary text-[10px] font-semibold">
                <span>Scan ID: {previewItem.id}</span>
              </div>
              <h3 className="font-serif text-xl font-bold text-ink">
                {previewItem.jobTitle || previewItem.title || 'Opportunity Assessment'}
              </h3>
              <p className="text-xs text-ink-muted">
                {previewItem.company} • {previewItem.date || previewItem.scanDate}
              </p>
            </div>

            {/* Score & Verdict Row */}
            <div className="flex items-center justify-between p-4 rounded-2xl bg-surface-2 border border-ink/5">
              <div>
                <span className="text-[10px] uppercase font-bold text-ink-subtle">Risk Score</span>
                <div className="text-2xl font-bold text-ink">
                  {previewItem.riskScore ?? previewItem.score ?? 0}{' '}
                  <span className="text-xs font-normal text-ink-subtle">/ 100</span>
                </div>
              </div>
              <div className="text-right">
                <span className="text-[10px] uppercase font-bold text-ink-subtle">Verdict</span>
                <div className="text-sm font-bold text-primary">
                  {previewItem.recommendation || previewItem.verdict}
                </div>
              </div>
            </div>

            {/* Risk Factors Highlight */}
            {previewItem.payload?.riskFactors && previewItem.payload.riskFactors.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-xs font-bold text-ink uppercase tracking-wider">
                  Surfaced Risk Indicators
                </h4>
                <div className="space-y-2">
                  {previewItem.payload.riskFactors.slice(0, 3).map((rf, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-xl bg-risk-high-bg border border-risk-high/10 text-xs space-y-1"
                    >
                      <div className="font-semibold text-risk-high">{rf.headline || rf.description}</div>
                      {rf.evidence && <div className="text-ink-muted text-[11px]">{rf.evidence}</div>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex items-center justify-end gap-3 pt-2 border-t border-ink/5">
              <button
                onClick={(e) => handleDownloadPDF(e, previewItem)}
                className="px-4 py-2.5 rounded-full bg-surface border border-ink/10 text-xs font-semibold text-ink hover:bg-surface-2 transition-all flex items-center gap-1.5"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export PDF</span>
              </button>
              <button
                onClick={() => handleSelectReport(previewItem)}
                className="px-5 py-2.5 rounded-full bg-primary text-surface text-xs font-bold shadow-subtle hover:bg-primary-container transition-all flex items-center gap-1.5"
              >
                <span>View Full Analysis</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
