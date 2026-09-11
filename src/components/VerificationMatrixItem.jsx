import React from 'react';
import { CheckCircle2, XCircle, AlertCircle } from 'lucide-react';

export const VerificationMatrixItem = ({
  checkName = 'Corporate Domain Legitimacy',
  status = 'FAIL',
  explanation = 'Domain age < 10 days.',
  evidenceFooter = 'Mismatch detected'
}) => {
  let badgeStyle = 'bg-risk-high-bg text-risk-high';
  let Icon = XCircle;

  if (status === 'PASS') {
    badgeStyle = 'bg-risk-low-bg text-risk-low';
    Icon = CheckCircle2;
  } else if (status === 'CAUTION') {
    badgeStyle = 'bg-risk-moderate-bg text-risk-moderate';
    Icon = AlertCircle;
  }

  return (
    <div className="bg-surface rounded-2xl p-5 shadow-subtle border border-ink/5 flex flex-col justify-between hover:border-primary/20 transition-all">
      <div>
        <div className="flex items-center justify-between gap-2 mb-2">
          <span className="text-sm font-semibold text-ink">
            {checkName}
          </span>
          <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold tracking-wider uppercase ${badgeStyle}`}>
            <Icon className="w-3 h-3" />
            {status}
          </span>
        </div>
        <p className="text-xs text-ink-muted leading-relaxed mb-3">
          {explanation}
        </p>
      </div>

      {evidenceFooter && (
        <div className="pt-2.5 border-t border-ink/5 text-[11px] text-ink-subtle truncate">
          <span className="font-semibold text-ink-muted">Detail:</span> {evidenceFooter}
        </div>
      )}
    </div>
  );
};
