import React from 'react';

export const StatCard = ({
  label = 'Total Checks',
  value = '14',
  icon: Icon,
  trend,
  badgeColor = 'bg-secondary-container text-primary',
  valueColor = 'text-ink'
}) => {
  return (
    <div className="bg-surface rounded-2xl p-6 shadow-subtle border border-ink/5 flex items-center justify-between">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-ink-subtle mb-1">
          {label}
        </p>
        <h3 className={`font-serif text-3xl font-semibold ${valueColor}`}>
          {value}
        </h3>
        {trend && (
          <p className="text-xs text-ink-muted mt-1.5 font-medium">
            {trend}
          </p>
        )}
      </div>

      {Icon && (
        <div className={`p-3.5 rounded-2xl ${badgeColor}`}>
          <Icon className="w-6 h-6" />
        </div>
      )}
    </div>
  );
};

