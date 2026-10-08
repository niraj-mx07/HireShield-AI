import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Search, Filter, Lock, ArrowRight, ShieldAlert, CheckCircle2, AlertTriangle, AlertCircle, ShieldCheck, Sparkles, FileText, PlusCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { getScanCounts } from '../data/mockData';
import { StatCard } from '../components/StatCard';

export const HistoryPage = () => {
  const { user, isLoggedIn, userHistory, openAuthModal, loadReport } = useAuth();
  const navigate = useNavigate();

  const [searchQuery, setSearchQuery] = useState('');
  const [riskFilter, setRiskFilter] = useState('all');

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

  // ------------------------------------------------------------------
  // Classify a single item by verdict (identical to DashboardPage)
  // ------------------------------------------------------------------
  const getItemBucket = (item) => {
    const v = item.verdict || item.recommendation || null;
    if (v === "DON'T APPLY" || v === "DONT_APPLY") return 'high';
    if (v === 'HOLD') return 'moderate';
    if (v === 'APPLY') return 'low';
    if (item.riskLevel) return item.riskLevel;
    const s = item.score ?? item.riskScore ?? 0;
    return s >= 60 ? 'high' : s >= 30 ? 'moderate' : 'low';
  };

  // Filter items by search query and risk level
  const filteredHistory = historySource.filter((item) => {
    const matchesSearch =
      (item.jobTitle || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.company || '').toLowerCase().includes(searchQuery.toLowerCase());
    const bucket = getItemBucket(item);
    const matchesFilter =
      riskFilter === 'all' || bucket === riskFilter;
    return matchesSearch && matchesFilter;
  });

  const handleSelectReport = (item) => {
    loadReport(item.payload);
    navigate('/analyze/result');
  };

  return (
    <div className="max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
      
      {/* Header with Dynamic User Name */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-secondary-container text-primary text-xs font-semibold mb-1">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Archive • {user?.name || 'Account'}</span>
          </div>
          <h1 className="font-serif text-3xl sm:text-4xl font-semibold text-ink">
            Saved Risk Reports
          </h1>
          <p className="text-xs text-ink-muted">
            Personal archive for <span className="font-semibold text-ink">{user?.email}</span>
          </p>
        </div>

        <Link
          to="/analyze"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-primary text-surface text-xs font-semibold shadow-subtle hover:bg-primary-container transition-all self-start sm:self-auto"
        >
          <PlusCircle className="w-3.5 h-3.5" />
          <span>New Opportunity Scan</span>
        </Link>
      </div>

      {/* Filter & Search Bar */}
      <div className="bg-surface p-4 rounded-3xl shadow-subtle border border-ink/5 flex flex-col sm:flex-row items-center justify-between gap-4">
        
        {/* Search Input */}
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-ink-subtle absolute left-4 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by job title or company..."
            className="w-full pl-10 pr-4 py-2.5 text-xs bg-canvas border border-ink/10 rounded-2xl text-ink placeholder-ink-subtle focus:outline-none focus:border-primary"
          />
        </div>

        {/* Filter Pills */}
        <div className="flex flex-wrap items-center gap-1.5 w-full sm:w-auto overflow-x-auto pb-1 sm:pb-0">
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
              <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${riskFilter === f.id ? 'bg-surface/20 text-surface' : 'bg-ink/5 text-ink-subtle'}`}>
                {f.count}
              </span>
            </button>
          ))}
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
                ? 'Scan an opportunity on the Analyze page to automatically archive your risk reports and evidence.'
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
                  <th className="py-4 px-6 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ink/5 text-xs font-medium text-ink">
                {filteredHistory.map((item) => {
                  const bucket = getItemBucket(item);
                  const isHigh = bucket === 'high';
                  const isMod = bucket === 'moderate';
                  const badgeBg = isHigh
                    ? 'bg-risk-high-bg text-risk-high'
                    : isMod
                      ? 'bg-risk-moderate-bg text-risk-moderate'
                      : 'bg-risk-low-bg text-risk-low';
                  const verdictLabel = item.verdict || (isHigh ? "DON'T APPLY" : isMod ? 'HOLD' : 'APPLY');

                  return (
                    <tr
                      key={item.id}
                      onClick={() => handleSelectReport(item)}
                      className="hover:bg-surface-2/50 transition-colors cursor-pointer group"
                    >
                      <td className="py-4 px-6 font-semibold group-hover:text-primary transition-colors">
                        {item.jobTitle}
                      </td>
                      <td className="py-4 px-6 text-ink-muted">{item.company}</td>
                      <td className="py-4 px-6 text-ink-subtle">{item.scanDate}</td>
                      <td className="py-4 px-6">
                        <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold ${badgeBg}`}>
                          {item.score ?? item.riskScore ?? '–'} / 100
                        </span>
                      </td>
                      <td className="py-4 px-6">
                        <span className={`font-bold text-[11px] ${isHigh ? 'text-risk-high' : isMod ? 'text-risk-moderate' : 'text-risk-low'}`}>
                          {verdictLabel}
                        </span>
                      </td>
                      <td className="py-4 px-6 text-right">
                        <span className="inline-flex items-center gap-1 text-primary text-xs font-semibold group-hover:underline">
                          <span>View Report</span>
                          <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

    </div>
  );
};
