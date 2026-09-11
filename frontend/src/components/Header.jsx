import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ShieldCheck, Menu, X, User, LogOut, Search, Sparkles } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const Header = () => {
  const { isLoggedIn, toggleAuth } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const isActive = (path) => location.pathname === path;

  const navItems = [
    { name: 'Home', path: '/' },
    { name: 'Analyze', path: '/analyze' },
    { name: 'Dashboard', path: '/dashboard' },
    { name: 'History', path: '/history' },
  ];

  const handleNavClick = (path) => {
    setMobileMenuOpen(false);
    navigate(path);
  };

  return (
    <header className="sticky top-0 z-50 bg-surface/90 backdrop-blur-md border-b border-ink/5 transition-all">
      <div className="max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
        
        {/* Brand Logo */}
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center text-surface shadow-subtle group-hover:scale-105 transition-transform">
            <ShieldCheck className="w-5 h-5 text-surface" />
          </div>
          <div className="flex flex-col">
            <span className="font-serif text-xl font-semibold tracking-tight text-ink group-hover:text-primary transition-colors">
              HireShield<span className="text-primary font-bold">.ai</span>
            </span>
            <span className="text-[10px] font-sans font-medium tracking-wider text-ink-subtle uppercase -mt-1">
              Scam & Fraud Shield
            </span>
          </div>
        </Link>

        {/* Desktop Nav Links (lg and above) */}
        <nav className="hidden lg:flex items-center gap-1 bg-surface-2 px-3 py-1.5 rounded-full border border-ink/5">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`px-4 py-2 rounded-full text-xs font-semibold transition-all ${
                isActive(item.path)
                  ? 'bg-primary text-surface'
                  : 'text-ink-muted hover:text-ink hover:bg-surface/80'
              }`}
            >
              {item.name}
            </Link>
          ))}
        </nav>

        {/* Desktop Action & Mock Auth Toggle */}
        <div className="hidden lg:flex items-center gap-3">
          {/* Auth Toggle Button */}
          <button
            onClick={toggleAuth}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold border transition-all ${
              isLoggedIn
                ? 'bg-secondary-container text-primary border-primary/20 hover:bg-secondary-container/80'
                : 'bg-surface-2 text-ink-muted border-ink/10 hover:text-ink'
            }`}
            title="Toggle mock user login state"
          >
            {isLoggedIn ? (
              <>
                <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                <User className="w-3.5 h-3.5" />
                <span>Logged In</span>
                <span className="text-[10px] opacity-75 underline ml-1">(Logout)</span>
              </>
            ) : (
              <>
                <span className="w-2 h-2 rounded-full bg-ink-subtle" />
                <span>Guest Mode</span>
                <span className="text-[10px] text-primary font-bold underline ml-1">(Simulate Login)</span>
              </>
            )}
          </button>

          {/* Primary CTA */}
          <Link
            to="/analyze"
            className="px-5 py-2.5 rounded-full bg-primary text-surface text-xs font-semibold shadow-subtle hover:bg-primary-container transition-all flex items-center gap-1.5"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Check Offer Now</span>
          </Link>
        </div>

        {/* Mobile Hamburger Button (< lg) */}
        <div className="flex lg:hidden items-center gap-2">
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2.5 rounded-full bg-surface-2 text-ink hover:text-primary transition-colors focus:outline-none"
            aria-label="Toggle Navigation Menu"
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Navigation Drawer */}
      {mobileMenuOpen && (
        <div className="lg:hidden bg-surface border-b border-ink/10 px-6 py-6 space-y-4 shadow-floating animate-in slide-in-from-top-2 duration-200">
          <div className="flex flex-col gap-2">
            {navItems.map((item) => (
              <button
                key={item.path}
                onClick={() => handleNavClick(item.path)}
                className={`text-left px-4 py-3 rounded-2xl text-sm font-semibold transition-all ${
                  isActive(item.path)
                    ? 'bg-secondary-container text-primary'
                    : 'text-ink-muted hover:bg-surface-2'
                }`}
              >
                {item.name}
              </button>
            ))}
          </div>

          <div className="pt-4 border-t border-ink/5 flex flex-col gap-3">
            <button
              onClick={() => {
                toggleAuth();
                setMobileMenuOpen(false);
              }}
              className={`w-full flex items-center justify-center gap-2 py-3 rounded-full text-xs font-semibold border ${
                isLoggedIn
                  ? 'bg-secondary-container text-primary border-primary/20'
                  : 'bg-surface-2 text-ink-muted border-ink/10'
              }`}
            >
              {isLoggedIn ? 'Simulate Logout (Currently Logged In)' : 'Simulate Login (Currently Guest)'}
            </button>

            <button
              onClick={() => handleNavClick('/analyze')}
              className="w-full py-3 rounded-full bg-primary text-surface text-xs font-semibold text-center shadow-subtle"
            >
              Check Job Offer Now
            </button>
          </div>
        </div>
      )}
    </header>
  );
};
