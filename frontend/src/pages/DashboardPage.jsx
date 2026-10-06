import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ShieldCheck, ShieldAlert, CheckCircle2, AlertCircle, Clock, Sparkles, PlusCircle, ArrowRight, Lock, User, FileText, Database } from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, CartesianGrid } from 'recharts';
import { useAuth } from '../context/AuthContext';
import { StatCard } from '../components/StatCard';
import { getScanCounts } from '../data/mockData';

export const DashboardPage = () => {
  const { user, isLoggedIn, userHistory, openAuthModal, loadReport, dbSyncStatus, lastSyncedAt } = useAuth();
  const navigate = useNavigate();

  // Locked Guest Preview State if not logged in
  if (!isLoggedIn) {
    return (
      <div className="max-w-[800px] mx-auto px-4 py-20 text-center space-y-6">
        <div className="w-20 h-20 rounded-full bg-secondary-container text-primary flex items-center justify-center mx-auto shadow-subtle">
          <Lock className="w-10 h-10" />
        </div>
        <div className="space-y-2">
          <h1 className="font-serif text-3xl font-semibold text-ink">
            Personal Security & Threat Dashboard
          </h1>
          <p className="text-sm text-ink-muted max-w-md mx-auto">
            Risk calculation is always free and open. Sign in or create a free candidate account to view your personal protection trends, weekly scan charts, and categorized threat intelligence.
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

  // Live scan counts from this specific user's history
  const historyList = userHistory || [];
  const counts = getScanCounts(historyList);
  const recentThree = historyList.slice(0, 3);

  // Dynamic Chart Data based on user scans
  const chartData = [
    { day: 'Mon', highRisk: 0, safe: 0 },
    { day: 'Tue', highRisk: 0, safe: 0 },
    { day: 'Wed', highRisk: 0, safe: 0 },
    { day: 'Thu', highRisk: 0, safe: 0 },
    { day: 'Fri', highRisk: 0, safe: 0 },
    { day: 'Sat', highRisk: counts.highRisk, safe: counts.verifiedSafe },
    { day: 'Sun', highRisk: 0, safe: counts.moderate },
  ];

  const handleRowClick = (item) => {
    loadReport(item.payload);
    navigate('/analyze/result');
  };

  return (
    <div className="max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-10">
      
      {/* Welcome Header with Dynamic User Name */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-secondary-container text-primary text-xs font-semibold">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Active Account • {user?.email}</span>
            </div>
          </div>
          <h1 className="font-serif text-3xl sm:text-4xl font-semibold text-ink">
            Welcome back, {user?.name || 'Candidate'}
          </h1>
          <p className="text-xs text-ink-muted mt-1">
            Here is your personal job opportunity risk summary and recent scans.
          </p>
        </div>

        <Link
          to="/analyze"
          className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-primary text-surface text-xs font-bold shadow-subtle hover:bg-primary-container transition-all self-start md:self-auto"
        >
          <PlusCircle className="w-4 h-4" />
          <span>Analyze New Opportunity</span>
        </Link>
      </div>

      {/* StatCards Row - Computed Dynamically for THIS User */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          label="Total Scans"
          value={counts.total}
          icon={ShieldCheck}
          trend={counts.total > 0 ? `${counts.total} recorded` : "0 recorded"}
          badgeColor="bg-secondary-container text-primary"
          valueColor="text-ink"
        />
        <StatCard
          label="High Risk Caught"
          value={counts.highRisk}
          icon={ShieldAlert}
          trend={counts.highRisk > 0 ? "Flagged red" : "None detected"}
          badgeColor="bg-risk-high-bg text-risk-high"
          valueColor="text-risk-high"
        />
        <StatCard
          label="Moderate Risk (Hold)"
          value={counts.moderate}
          icon={AlertCircle}
          trend={counts.moderate > 0 ? "Review needed" : "Clean"}
          badgeColor="bg-risk-moderate-bg text-risk-moderate"
          valueColor="text-risk-moderate"
        />
        <StatCard
          label="Verified Safe"
          value={counts.verifiedSafe}
          icon={CheckCircle2}
          trend={counts.verifiedSafe > 0 ? "Safe to apply" : "Ready to scan"}
          badgeColor="bg-risk-low-bg text-risk-low"
          valueColor="text-risk-low"
        />
      </div>

      {/* Main Grid: Chart & Recent Scans */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left: Weekly Scan Trend Chart */}
        <div className="lg:col-span-7 bg-surface rounded-3xl p-6 sm:p-8 border border-ink/5 shadow-subtle space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-serif text-lg font-semibold text-ink">
                Scan Activity & Threats Flagged
              </h2>
              <p className="text-xs text-ink-muted">Weekly detection distribution</p>
            </div>
          </div>

          <div className="h-[280px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" opacity={0.6} />
                <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fill: '#64748B', fontSize: 12 }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: '#64748B', fontSize: 12 }} allowDecimals={false} />
                <Tooltip
                  cursor={{ fill: '#F1F5F9', opacity: 0.5 }}
                  contentStyle={{ backgroundColor: '#0F172A', borderRadius: '12px', border: 'none', color: '#FFF', fontSize: '12px' }}
                />
                <Legend iconType="circle" wrapperStyle={{ paddingTop: '10px', fontSize: '12px' }} />
                <Bar dataKey="highRisk" name="High Risk Scams" fill="#EF4444" radius={[6, 6, 0, 0]} />
                <Bar dataKey="safe" name="Safe / Verified" fill="#22C55E" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Right: Recent Scans List */}
        <div className="lg:col-span-5 bg-surface rounded-3xl p-6 sm:p-8 border border-ink/5 shadow-subtle flex flex-col justify-between space-y-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="font-serif text-lg font-semibold text-ink">Recent Scans</h2>
              <Link to="/history" className="text-xs font-semibold text-primary hover:underline">
                View All ({historyList.length})
              </Link>
            </div>

            {historyList.length === 0 ? (
              <div className="py-12 text-center space-y-3">
                <FileText className="w-10 h-10 text-ink-subtle mx-auto" />
                <p className="text-xs font-semibold text-ink">No Scans Recorded Yet</p>
                <p className="text-[11px] text-ink-muted max-w-xs mx-auto">
                  Run your first opportunity scan on the Analyze page to see it logged here.
                </p>
                <Link
                  to="/analyze"
                  className="inline-block px-4 py-2 rounded-full bg-primary text-surface text-xs font-semibold shadow-subtle"
                >
                  Scan Now
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {recentThree.map((item) => {
                  const isHigh = item.riskLevel === 'high';
                  const isMod = item.riskLevel === 'moderate';
                  const badgeBg = isHigh ? 'bg-risk-high-bg text-risk-high' : isMod ? 'bg-risk-moderate-bg text-risk-moderate' : 'bg-risk-low-bg text-risk-low';

                  return (
                    <div
                      key={item.id}
                      onClick={() => handleRowClick(item)}
                      className="p-3.5 rounded-2xl bg-surface-2/60 hover:bg-surface-2 border border-ink/5 transition-all cursor-pointer flex items-center justify-between gap-3 group"
                    >
                      <div className="min-w-0">
                        <p className="text-xs font-semibold text-ink truncate group-hover:text-primary transition-colors">
                          {item.jobTitle || item.title || 'Opportunity Assessment'}
                        </p>
                        <p className="text-[11px] text-ink-muted truncate">
                          {item.company} • {item.date || item.scanDate}
                        </p>
                      </div>

                      <div className="flex items-center gap-2 flex-shrink-0">
                        <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold ${badgeBg}`}>
                          {item.riskScore ?? item.score ?? 0} pts
                        </span>
                        <ArrowRight className="w-3.5 h-3.5 text-ink-subtle group-hover:translate-x-0.5 transition-transform" />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="pt-4 border-t border-ink/5">
            <Link
              to="/analyze"
              className="w-full py-3 rounded-2xl bg-surface-2 hover:bg-surface-2/80 text-ink text-xs font-semibold flex items-center justify-center gap-2 transition-all border border-ink/5"
            >
              <PlusCircle className="w-4 h-4 text-primary" />
              <span>Verify Another Listing</span>
            </Link>
          </div>
        </div>

      </div>

    </div>
  );
};
