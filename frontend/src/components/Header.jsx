import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ShieldCheck, Menu, X, User, LogOut, Sparkles, ChevronDown, CheckCircle2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const Header = () => {
  const { user, isLoggedIn, logout, openAuthModal, userHistory, dbSyncStatus } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);

  const isActive = (path) => location.pathname === path;

  const navItems = [
    { name: 'Home', path: '/' },
    { name: 'Analyze', path: '/analyze' },
    { name: 'Dashboard', path: '/dashboard' },
    { name: 'History', path: '/history' },
  ];

  const handleNavClick = (path) => {
    setMobileMenuOpen(false);
    setUserDropdownOpen(false);
    navigate(path);
  };

  return (
    <header className="sticky top-0 z-40 bg-surface/90 backdrop-blur-md border-b border-ink/5 transition-all">
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

        {/* Desktop Action & Auth State */}
        <div className="hidden lg:flex items-center gap-3">
          {isLoggedIn ? (
            /* Logged-In User Profile Menu */
            <div className="relative">
              <button
                onClick={() => setUserDropdownOpen(!userDropdownOpen)}
                className="flex items-center gap-2.5 px-3.5 py-1.5 rounded-full bg-surface-2 border border-ink/10 hover:bg-surface transition-all text-xs font-semibold text-ink"
              >
                <div className="w-6 h-6 rounded-full bg-primary text-surface flex items-center justify-center text-xs font-bold relative">
                  {user?.avatar || 'U'}
                  <span className="absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full bg-emerald-500 border border-surface" />
                </div>
                <span>{user?.name || 'Account'}</span>
                <ChevronDown className="w-3.5 h-3.5 text-ink-subtle" />
              </button>

              {userDropdownOpen && (
                <div className="absolute right-0 mt-2 w-60 bg-surface border border-ink/10 rounded-2xl shadow-floating py-2 z-50 animate-in fade-in duration-150">
                  <div className="px-4 py-2.5 border-b border-ink/5">
                    <p className="text-xs font-semibold text-ink truncate">{user?.name}</p>
                    <p className="text-[11px] text-ink-subtle truncate">{user?.email}</p>
                  </div>

                  <Link
                    to="/history"
                    onClick={() => setUserDropdownOpen(false)}
                    className="flex items-center gap-2 px-4 py-2 text-xs text-ink-muted hover:text-ink hover:bg-surface-2"
                  >
                    <span>Assessment History</span>
                  </Link>
                  <Link
                    to="/dashboard"
                    onClick={() => setUserDropdownOpen(false)}
                    className="flex items-center gap-2 px-4 py-2 text-xs text-ink-muted hover:text-ink hover:bg-surface-2"
                  >
                    <span>Threat Dashboard</span>
                  </Link>

                  <div className="pt-1 border-t border-ink/5">
                    <button
                      onClick={() => {
                        logout();
                        setUserDropdownOpen(false);
                      }}
                      className="w-full flex items-center gap-2 px-4 py-2 text-xs text-risk-high hover:bg-risk-high-bg transition-colors text-left"
                    >
                      <LogOut className="w-3.5 h-3.5" />
                      <span>Sign Out</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* Guest Mode Auth Buttons */
            <div className="flex items-center gap-2">
              <button
                onClick={() => openAuthModal('login')}
                className="px-4 py-2 rounded-full text-xs font-semibold text-ink-muted hover:text-ink hover:bg-surface-2 transition-all"
              >
                Sign In
              </button>
              <button
                onClick={() => openAuthModal('signup')}
                className="px-4 py-2 rounded-full bg-surface-2 border border-ink/10 text-xs font-semibold text-ink hover:bg-surface hover:border-primary/30 transition-all"
              >
                Sign Up
              </button>
            </div>
          )}

          {/* Primary Action Button */}
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
            {isLoggedIn ? (
              <div className="flex items-center justify-between p-3 rounded-2xl bg-surface-2">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-full bg-primary text-surface flex items-center justify-center text-xs font-bold">
                    {user?.avatar || 'U'}
                  </div>
                  <div className="text-xs">
                    <p className="font-semibold text-ink">{user?.name}</p>
                    <p className="text-ink-subtle">{user?.email}</p>
                  </div>
                </div>
                <button
                  onClick={() => {
                    logout();
                    setMobileMenuOpen(false);
                  }}
                  className="p-2 text-risk-high hover:bg-risk-high-bg rounded-full text-xs font-semibold"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => {
                    openAuthModal('login');
                    setMobileMenuOpen(false);
                  }}
                  className="py-2.5 rounded-full bg-surface-2 border border-ink/10 text-xs font-semibold text-ink text-center"
                >
                  Sign In
                </button>
                <button
                  onClick={() => {
                    openAuthModal('signup');
                    setMobileMenuOpen(false);
                  }}
                  className="py-2.5 rounded-full bg-primary text-surface text-xs font-semibold text-center"
                >
                  Create Account
                </button>
              </div>
            )}

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
