import React from 'react';

export const RiskScoreGauge = ({ score = 88, riskLevel = 'high', size = 190 }) => {
  const radius = 72;
  const strokeWidth = 14;
  const center = size / 2;
  const circumference = 2 * Math.PI * radius;
  
  // Calculate dynamic strokeDashoffset based on score percentage
  const clampedScore = Math.max(0, Math.min(100, score));
  const strokeDashoffset = circumference - (clampedScore / 100) * circumference;

  let strokeColor = '#ba1a1a'; // risk-high
  let badgeText = 'DON\'T APPLY';
  let badgeClass = 'bg-risk-high-bg text-risk-high border border-risk-high/20';

  if (clampedScore < 30 || riskLevel === 'low') {
    strokeColor = '#1e5631'; // risk-low
    badgeText = 'APPLY';
    badgeClass = 'bg-risk-low-bg text-risk-low border border-risk-low/20';
  } else if (clampedScore < 70 || riskLevel === 'moderate') {
    strokeColor = '#b45309'; // risk-moderate
    badgeText = 'HOLD';
    badgeClass = 'bg-risk-moderate-bg text-risk-moderate border border-risk-moderate/20';
  }

  return (
    <div className="flex flex-col items-center justify-center relative">
      <div className="relative" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          className="transform -rotate-90 drop-shadow-sm"
        >
          {/* Track background arc */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            stroke="#f6f3f2"
            strokeWidth={strokeWidth}
            fill="transparent"
          />
          {/* Dynamic colored risk fill arc */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            stroke={strokeColor}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            fill="transparent"
            className="transition-all duration-1000 ease-out"
          />
        </svg>

        {/* Center score readout */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <span className="text-xs uppercase tracking-wider text-ink-subtle font-medium mb-0.5">
            Risk Score
          </span>
          <span className="font-serif text-5xl font-semibold text-ink tracking-tight">
            {clampedScore}
          </span>
          <span className="text-[11px] text-ink-muted mt-0.5">out of 100</span>
        </div>
      </div>

      {/* Verdict Badge */}
      <div className={`mt-4 px-5 py-1.5 rounded-full font-bold text-xs tracking-wider uppercase shadow-sm ${badgeClass}`}>
        Verdict: {badgeText}
      </div>
    </div>
  );
};
