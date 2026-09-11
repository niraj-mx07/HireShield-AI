import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, CheckCircle2, Loader2, Sparkles } from 'lucide-react';

export const ProcessingPage = () => {
  const navigate = useNavigate();
  const [completedSteps, setCompletedSteps] = useState([false, false, false, false, false, false]);

  const steps = [
    "Extracting entity information",
    "Analyzing job description content & financial clauses",
    "Checking company Secretary of State records",
    "Verifying WHOIS website domain & SSL security",
    "Checking recruiter identity & DMARC email auth",
    "Calculating normalized weighted risk score"
  ];

  useEffect(() => {
    const timers = [];
    
    // Step completion timeline over ~3.5 seconds
    steps.forEach((_, index) => {
      const timer = setTimeout(() => {
        setCompletedSteps(prev => {
          const next = [...prev];
          next[index] = true;
          return next;
        });
      }, (index + 1) * 500);
      timers.push(timer);
    });

    // Auto-navigate to result page
    const navTimer = setTimeout(() => {
      navigate('/analyze/result');
    }, 3600);
    timers.push(navTimer);

    return () => timers.forEach(t => clearTimeout(t));
  }, [navigate]);

  const activeIndex = completedSteps.filter(Boolean).length;
  const progressPercent = Math.min(100, Math.round((activeIndex / steps.length) * 100));

  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center max-w-[700px] mx-auto px-4 py-12 text-center space-y-8">
      
      {/* Radar Pulse Animation & Shield Icon */}
      <div className="relative flex items-center justify-center my-4">
        <div className="w-28 h-28 rounded-full bg-primary/10 animate-pulse-ring absolute" />
        <div className="w-20 h-20 rounded-full bg-primary flex items-center justify-center text-surface shadow-floating relative z-10">
          <ShieldCheck className="w-10 h-10 text-surface animate-pulse" />
        </div>
      </div>

      {/* Headline & Progress Text */}
      <div className="space-y-2">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-secondary-container text-primary text-xs font-semibold">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Real-time Risk Engine Active</span>
        </div>
        <h2 className="font-serif text-3xl font-semibold text-ink">
          Analyzing Opportunity Credibility
        </h2>
        <p className="text-xs text-ink-muted">
          Aggregating signals across multi-layer web verifications and NLP neural models...
        </p>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-surface-2 rounded-full h-3 p-0.5 border border-ink/5 overflow-hidden">
        <div
          className="bg-primary h-full rounded-full transition-all duration-300 ease-out"
          style={{ width: `${progressPercent}%` }}
        />
      </div>
      <div className="text-xs font-semibold text-ink-muted tracking-wider">
        {progressPercent}% COMPLETE
      </div>

      {/* Animated Sequential Step Checklist */}
      <div className="w-full bg-surface rounded-3xl p-6 sm:p-8 shadow-subtle border border-ink/5 text-left space-y-4">
        {steps.map((step, idx) => {
          const isDone = completedSteps[idx];
          const isCurrent = activeIndex === idx;

          return (
            <div
              key={idx}
              className={`flex items-center justify-between p-3.5 rounded-2xl transition-all duration-300 ${
                isDone
                  ? 'bg-secondary-container/40 text-primary'
                  : isCurrent
                  ? 'bg-surface-2 text-ink font-semibold border border-ink/5'
                  : 'text-ink-subtle opacity-50'
              }`}
            >
              <div className="flex items-center gap-3">
                {isDone ? (
                  <CheckCircle2 className="w-5 h-5 text-primary flex-shrink-0" />
                ) : isCurrent ? (
                  <Loader2 className="w-5 h-5 text-primary animate-spin flex-shrink-0" />
                ) : (
                  <div className="w-5 h-5 rounded-full border border-ink/20 flex-shrink-0" />
                )}
                <span className="text-xs sm:text-sm font-medium">
                  {step}
                </span>
              </div>

              {isDone && (
                <span className="text-[10px] font-bold tracking-wider uppercase text-primary">
                  VERIFIED
                </span>
              )}
            </div>
          );
        })}
      </div>

    </div>
  );
};
