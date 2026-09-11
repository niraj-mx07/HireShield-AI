import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ShieldCheck, ShieldAlert, CheckCircle2, AlertCircle, Clock, Sparkles, PlusCircle, ArrowRight, Lock } from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, CartesianGrid } from 'recharts';
import { useAuth } from '../context/AuthContext';
import { StatCard } from '../components/StatCard';
import { mockWeeklyChartData, mockHistoryList, getScanCounts } from '../data/mockData';

export const DashboardPage = () => {
  const { isLoggedIn, toggleAuth, loadReport } = useAuth();
  const navigate = useNavigate();

  // Compute live scan counts from mockHistoryList
  const counts = getScanCounts(mockHistoryList);

  // Locked Guest Preview State if not logged in
  if (!isLoggedIn) {
    return (
      <div className="max-w-[800px] mx-auto px-4 py-20 text-center space-y-6">
        <div className="w-20 h-20 rounded-full bg-secondary-container text-primary flex items-center justify-center mx-auto shadow-subtle">
          <Lock className="w-10 h-10" />
        </div>
        <div className="space-y-2">
          <h1 className="font-serif text-3xl font-semibold text-ink">
            Dashboard Locked (Guest Mode)
          </h1>
          <p className="text-sm text-ink-muted max-w-md mx-auto">
            Simulate Login to preview your personal scam prevention dashboard, weekly scan analytics, and risk mitigation trends.
          </p>
        </div>
        <div>
          <button
            onClick={toggleAuth}
            className="px-8 py-3.5 rounded-full bg-primary text-surface text-xs font-bold shadow-subtle hover:bg-primary-container transition-all"
          >
            Simulate Login to Access Dashboard
          </button>
        </div>
      </div>
    );
  }

  // Authenticated State View
  const recentThree = mockHistoryList.slice(0, 3);

  const handleRowClick = (item) => {
    loadReport(item.payload);
    navigate('/analyze/result');
  };

  return (
    <div className="max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-10">
      
      {/* Welcome Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-secondary-container text-primary text-xs font-semibold mb-2">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Authenticated Protection Active</span>
          </div>
          <h1 className="font-serif text-3xl sm:text-4xl font-semibold text-ink">
            Welcome back, Nihar
          </h1>
          <p className="text-xs text-ink-muted mt-1">
            Here is your job application risk summary and recent scans.
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

      {/* StatCards Row - Fully Synchronized with getScanCounts */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          label="Total Scans"
          value={counts.total}
          icon={ShieldCheck}
          trend="+3 this week"
          badgeColor="bg-secondary-container text-primary"
          valueColor="text-ink"
        />
        <StatCard
          label="High Risk Caught"
          value={counts.highRisk}
          icon={ShieldAlert}
          trend="Protected from loss"
          badgeColor="bg-risk-high-bg text-risk-high"
          valueColor="text-risk-high"
        />
        <StatCard
          label="Moderate Caution"
          value={counts.moderate}
          icon={AlertCircle}
          trend="Review recommended"
          badgeColor="bg-risk-moderate-bg text-risk-moderate"
          valueColor="text-risk-moderate"
        />
        <StatCard
          label="Verified Safe"
          value={counts.verifiedSafe}
          icon={CheckCircle2}
          trend="100% verified safe"
          badgeColor="bg-risk-low-bg text-risk-low"
          valueColor="text-risk-low"
        />
      </div>


      {/* Recharts Chart Section */}
      <div className="bg-surface rounded-3xl p-6 sm:p-8 shadow-floating border border-ink/5 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-ink/5 pb-4">
          <div>
            <h2 className="font-serif text-xl font-semibold text-ink">
              Job Offer Scans & Scam Distribution
            </h2>
            <p className="text-xs text-ink-muted">
              Weekly breakdown of high-risk scams, moderate caution alerts, and verified safe listings.
            </p>
          </div>
          <div className="text-xs font-semibold text-ink-subtle">
            Last 6 Weeks
          </div>
        </div>

        <div className="h-72 w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={mockWeeklyChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f6f3f2" vertical={false} />
              <XAxis dataKey="week" stroke="#717970" fontSize={11} tickLine={false} />
              <YAxis stroke="#717970" fontSize={11} tickLine={false} allowDecimals={false} />
              <Tooltip
                contentStyle={{ backgroundColor: '#ffffff', borderRadius: '12px', border: '1px solid rgba(28,27,27,0.08)', fontSize: '12px' }}
              />
              <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
              <Bar dataKey="highRisk" name="High Risk Scam" fill="#ba1a1a" radius={[6, 6, 0, 0]} />
              <Bar dataKey="moderate" name="Moderate Caution" fill="#b45309" radius={[6, 6, 0, 0]} />
              <Bar dataKey="safe" name="Verified Safe" fill="#1e5631" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recent Activity Section */}
      <div className="bg-surface rounded-3xl p-6 sm:p-8 shadow-subtle border border-ink/5 space-y-6">
        <div className="flex items-center justify-between border-b border-ink/5 pb-4">
          <h2 className="font-serif text-xl font-semibold text-ink">
            Recent Opportunity Scans
          </h2>
          <Link to="/history" className="text-xs font-semibold text-primary hover:underline flex items-center gap-1">
            <span>View All Saved History</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="divide-y divide-ink/5">
          {recentThree.map((item) => (
            <div
              key={item.id}
              onClick={() => handleRowClick(item)}
              className="py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-surface-2/60 px-4 rounded-2xl cursor-pointer transition-all"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-ink">{item.jobTitle}</span>
                  <span className="text-xs text-ink-subtle">• {item.company}</span>
                </div>
                <div className="text-xs text-ink-muted">
                  Scanned on {item.scanDate} • Input: {item.type}
                </div>
              </div>

              <div className="flex items-center gap-4">
                <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                  item.riskLevel === 'high'
                    ? 'bg-risk-high-bg text-risk-high'
                    : item.riskLevel === 'moderate'
                    ? 'bg-risk-moderate-bg text-risk-moderate'
                    : 'bg-risk-low-bg text-risk-low'
                }`}>
                  Score {item.score} • {item.verdict}
                </span>
                <ArrowRight className="w-4 h-4 text-ink-subtle hidden sm:block" />
              </div>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
};
