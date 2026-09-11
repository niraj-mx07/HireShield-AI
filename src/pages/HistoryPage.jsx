import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Filter, Lock, ArrowRight, ShieldAlert, CheckCircle2, AlertTriangle, Sparkles } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { mockHistoryList } from '../data/mockData';

export const HistoryPage = () => {
  const { isLoggedIn, toggleAuth, loadReport } = useAuth();
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
            Saved History Locked (Guest Mode)
          </h1>
          <p className="text-sm text-ink-muted max-w-md mx-auto">
            Simulate Login to view your full history of past opportunity scans, detailed evidence breakdowns, and saved risk reports.
          </p>
        </div>
        <div>
          <button
            onClick={toggleAuth}
            className="px-8 py-3.5 rounded-full bg-primary text-surface text-xs font-bold shadow-subtle hover:bg-primary-container transition-all"
          >
            Simulate Login to Access History
          </button>
        </div>
      </div>
    );
  }

  // Filter items by search query and risk level
  const filteredHistory = mockHistoryList.filter((item) => {
    const matchesSearch =
      item.jobTitle.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.company.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter =
      riskFilter === 'all' || item.riskLevel === riskFilter;
    return matchesSearch && matchesFilter;
  });

  const handleSelectReport = (item) => {
    loadReport(item.payload);
    navigate('/analyze/result');
  };

  return (
    <div className="max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
      
      {/* Header */}
      <div className="space-y-2">
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-secondary-container text-primary text-xs font-semibold">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Historical Analysis Archive</span>
        </div>
        <h1 className="font-serif text-3xl sm:text-4xl font-semibold text-ink">
          My Saved Risk Reports
        </h1>
        <p className="text-sm text-ink-muted">
          Review previous opportunity scans, re-inspect evidence signals, and manage saved verifications.
        </p>
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
            className="w-full bg-canvas border border-ink/10 rounded-full pl-10 pr-4 py-2.5 text-xs text-ink placeholder-ink-subtle focus:outline-none focus:border-primary"
          />
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1.5 w-full sm:w-auto overflow-x-auto scrollbar-none">
          <span className="text-xs font-semibold text-ink-subtle mr-1 hidden sm:inline">Filter:</span>
          {[
            { id: 'all', label: 'All Scans' },
            { id: 'high', label: 'High Risk' },
            { id: 'moderate', label: 'Moderate' },
            { id: 'low', label: 'Verified Safe' },
          ].map((filter) => (
            <button
              key={filter.id}
              onClick={() => setRiskFilter(filter.id)}
              className={`px-4 py-2 rounded-full text-xs font-semibold transition-all whitespace-nowrap ${
                riskFilter === filter.id
                  ? 'bg-primary text-surface shadow-subtle'
                  : 'bg-surface-2 text-ink-muted hover:text-ink'
              }`}
            >
              {filter.label}
            </button>
          ))}
        </div>

      </div>

      {/* History Table / List */}
      <div className="bg-surface rounded-3xl shadow-floating border border-ink/5 overflow-hidden">
        {filteredHistory.length === 0 ? (
          <div className="p-12 text-center text-ink-muted space-y-2">
            <p className="font-semibold text-sm">No scans match your search or filter criteria.</p>
            <button
              onClick={() => { setSearchQuery(''); setRiskFilter('all'); }}
              className="text-xs text-primary font-bold hover:underline"
            >
              Reset Filters
            </button>
          </div>
        ) : (
          <div className="divide-y divide-ink/5">
            {filteredHistory.map((item) => (
              <div
                key={item.id}
                onClick={() => handleSelectReport(item)}
                className="p-6 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-surface-2/70 transition-all cursor-pointer group"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-3">
                    <h3 className="font-serif text-lg font-semibold text-ink group-hover:text-primary transition-colors">
                      {item.jobTitle}
                    </h3>
                    <span className="text-xs text-ink-subtle hidden sm:inline">•</span>
                    <span className="text-xs font-semibold text-ink-muted">{item.company}</span>
                  </div>
                  <div className="flex flex-wrap items-center gap-3 text-xs text-ink-subtle">
                    <span>ID: {item.id}</span>
                    <span>•</span>
                    <span>Scanned: {item.scanDate}</span>
                    <span>•</span>
                    <span>Input: {item.type}</span>
                  </div>
                </div>

                <div className="flex items-center gap-4 self-end md:self-auto">
                  <div className="flex items-center gap-3">
                    <span className="font-serif text-xl font-semibold text-ink">
                      {item.score}<span className="text-xs text-ink-subtle">/100</span>
                    </span>

                    <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                      item.riskLevel === 'high'
                        ? 'bg-risk-high-bg text-risk-high'
                        : item.riskLevel === 'moderate'
                        ? 'bg-risk-moderate-bg text-risk-moderate'
                        : 'bg-risk-low-bg text-risk-low'
                    }`}>
                      {item.verdict}
                    </span>
                  </div>

                  <div className="w-8 h-8 rounded-full bg-surface-2 group-hover:bg-primary group-hover:text-surface flex items-center justify-center transition-all text-ink-subtle">
                    <ArrowRight className="w-4 h-4" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

    </div>
  );
};
