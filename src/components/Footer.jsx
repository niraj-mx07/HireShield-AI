import React from 'react';
import { ShieldCheck, Lock, CheckCircle2, FileText } from 'lucide-react';
import { Link } from 'react-router-dom';

export const Footer = () => {
  return (
    <footer className="bg-surface-2 border-t border-ink/5 pt-16 pb-12 mt-20">
      <div className="max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-10 mb-12">
          
          {/* Col 1: Brand & Mission */}
          <div className="md:col-span-1 space-y-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-surface">
                <ShieldCheck className="w-4 h-4 text-surface" />
              </div>
              <span className="font-serif text-lg font-semibold text-ink">
                HireShield<span className="text-primary font-bold">.ai</span>
              </span>
            </div>
            <p className="text-xs text-ink-muted leading-relaxed">
              AI-powered job scam detection engine. Validating offer letters, recruiter domains, company registrations, and financial clauses before you apply.
            </p>
            <div className="flex items-center gap-2 text-[11px] text-ink-subtle">
              <Lock className="w-3.5 h-3.5 text-primary" />
              <span>Zero Data Resale • Privacy Protected</span>
            </div>
          </div>

          {/* Col 2: Navigation */}
          <div>
            <h4 className="font-serif text-sm font-semibold text-ink mb-4">Platform</h4>
            <ul className="space-y-2.5 text-xs text-ink-muted">
              <li><Link to="/" className="hover:text-primary transition-colors">Home</Link></li>
              <li><Link to="/analyze" className="hover:text-primary transition-colors">Submit Job Scan</Link></li>
              <li><Link to="/dashboard" className="hover:text-primary transition-colors">Analytics Dashboard</Link></li>
              <li><Link to="/history" className="hover:text-primary transition-colors">Saved Reports History</Link></li>
            </ul>
          </div>

          {/* Col 3: Detection Layers */}
          <div>
            <h4 className="font-serif text-sm font-semibold text-ink mb-4">What We Check</h4>
            <ul className="space-y-2.5 text-xs text-ink-muted">
              <li className="flex items-center gap-1.5"><CheckCircle2 className="w-3.5 h-3.5 text-primary" /> WHOIS Domain Age & DNS</li>
              <li className="flex items-center gap-1.5"><CheckCircle2 className="w-3.5 h-3.5 text-primary" /> Recruiter Email SPF / DKIM</li>
              <li className="flex items-center gap-1.5"><CheckCircle2 className="w-3.5 h-3.5 text-primary" /> Advance Equipment Fee NLP</li>
              <li className="flex items-center gap-1.5"><CheckCircle2 className="w-3.5 h-3.5 text-primary" /> State SOS Business Records</li>
            </ul>
          </div>

          {/* Col 4: Demo Disclaimer */}
          <div>
            <h4 className="font-serif text-sm font-semibold text-ink mb-4">Project Demo Note</h4>
            <p className="text-xs text-ink-muted leading-relaxed mb-3">
              This is an interactive design demo for project presentation. Populated with realistic sample datasets.
            </p>
            <div className="inline-block px-3 py-1 rounded-full bg-secondary-container text-primary text-[11px] font-semibold">
              Status: Interactive Prototype
            </div>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="pt-8 border-t border-ink/10 flex flex-col sm:flex-row items-center justify-between text-xs text-ink-subtle gap-4">
          <p>© 2026 HireShield-AI. All rights reserved.</p>
          <div className="flex gap-6">
            <span className="hover:text-ink cursor-pointer">Privacy Policy</span>
            <span className="hover:text-ink cursor-pointer">Terms of Service</span>
            <span className="hover:text-ink cursor-pointer">Security Standards</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
