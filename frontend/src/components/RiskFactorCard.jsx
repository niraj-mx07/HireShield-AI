import React from 'react';
import { AlertTriangle, AlertCircle, CheckCircle2, ShieldAlert, FileSearch, Globe, UserCheck } from 'lucide-react';

export const RiskFactorCard = ({
  severity = 'high',
  category = 'Financial Red Flags',
  headline = 'Advance Equipment Fee Clause',
  description = 'Detailed description of the detected risk factor.',
  evidence = 'Extracted clause or WHOIS record details.',
  severityScore = 85,
  categoryType = 'accent-document'
}) => {
  let severityBadge = 'bg-risk-high-bg text-risk-high';
  let SeverityIcon = AlertTriangle;

  if (severity === 'low') {
    severityBadge = 'bg-risk-low-bg text-risk-low';
    SeverityIcon = CheckCircle2;
  } else if (severity === 'moderate') {
    severityBadge = 'bg-risk-moderate-bg text-risk-moderate';
    SeverityIcon = AlertCircle;
  }

  let CategoryIcon = FileSearch;
  if (categoryType === 'accent-url' || category.includes('URL')) CategoryIcon = Globe;
  if (categoryType === 'accent-recruiter' || category.includes('Recruiter')) CategoryIcon = UserCheck;

  return (
    <div className="bg-surface rounded-2xl p-6 shadow-subtle border border-ink/5 flex flex-col justify-between hover:shadow-floating transition-all duration-300">
      <div>
        {/* Top bar: Category Badge + Severity Chip */}
        <div className="flex items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-2">
            <span className="p-2 rounded-xl bg-surface-2 text-ink-muted">
              <CategoryIcon className="w-4 h-4 text-primary" />
            </span>
            <span className="text-xs font-semibold tracking-wide text-ink-muted uppercase">
              {category}
            </span>
          </div>

          <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${severityBadge}`}>
            <SeverityIcon className="w-3.5 h-3.5" />
            {severity === 'high' ? `High Risk (${severityScore})` : severity === 'moderate' ? `Moderate (${severityScore})` : `Verified Safe (${severityScore})`}
          </span>
        </div>

        {/* Headline */}
        <h3 className="font-serif text-lg font-semibold text-ink mb-2 leading-snug">
          {headline}
        </h3>

        {/* Description */}
        <p className="text-sm text-ink-muted mb-4 leading-relaxed">
          {description}
        </p>
      </div>

      {/* Evidence Sub-Panel */}
      <div className="bg-surface-2 rounded-xl p-4 text-xs font-mono text-ink-muted border border-ink/5 relative overflow-hidden">
        <div className="text-[10px] font-sans font-bold uppercase tracking-wider text-ink-subtle mb-1">
          Extracted Evidence Signal
        </div>
        <p className="text-ink text-xs font-medium font-sans">
          {evidence}
        </p>
      </div>
    </div>
  );
};
