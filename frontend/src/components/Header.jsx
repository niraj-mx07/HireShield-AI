import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ShieldCheck, Menu, X, User, LogOut, ChevronDown, CheckCircle2 } from 'lucide-react';
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

  const UserAvatar = ({ size = 'w-6 h-6', textSize = 'text-xs' }) => {
    const isImageUrl =
      user?.avatar &&
      typeof user.avatar === 'string' &&
      (user.avatar.startsWith('http://') || user.avatar.startsWith('https://'));
    const initial = user?.name ? user.name.charAt(0).toUpperCase() : (user?.avatar || 'U');

    return (
      <div className={`${size} rounded-full bg-primary text-surface flex items-center justify-center ${textSize} font-bold overflow-hidden flex-shrink-0 shadow-sm`}>
        {isImageUrl ? (
          <img
            src={user.avatar}
            alt={user?.name || 'User'}
            referrerPolicy="no-referrer"
            className="w-full h-full object-cover"
            onError={(e) => {
              e.currentTarget.style.display = 'none';
              if (e.currentTarget.nextSibling) {
                e.currentTarget.nextSibling.style.display = 'block';
              }
            }}
          />
        ) : null}
        <span style={{ display: isImageUrl ? 'none' : 'block' }}>{initial}</span>
      </div>
    );
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
                <div className="relative flex-shrink-0">
                  <UserAvatar size="w-6 h-6" textSize="text-xs" />
                  <span className="absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full bg-emerald-500 border border-surface" />
                </div>
                <span className="max-w-[120px] truncate">{user?.name || 'Account'}</span>
                <ChevronDown className="w-3.5 h-3.5 text-ink-subtle flex-shrink-0" />
              </button>

              {userDropdownOpen && (
                <div className="absolute right-0 mt-2 w-60 bg-surface border border-ink/10 rounded-2xl shadow-floating py-2 z-50 animate-in fade-in duration-150">
                  <div className="px-4 py-2.5 border-b border-ink/5 flex items-center gap-3">
                    <UserAvatar size="w-8 h-8" textSize="text-sm" />
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-semibold text-ink truncate">{user?.name}</p>
                      <p className="text-[11px] text-ink-subtle truncate">{user?.email}</p>
                    </div>
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
                className="px-4 py-2 rounded-full bg-primary text-surface text-xs font-semibold hover:bg-primary-container shadow-subtle transition-all"
              >
                Sign Up
              </button>
            </div>
          )}
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
                <div className="flex items-center gap-2.5 min-w-0">
                  <UserAvatar size="w-8 h-8" textSize="text-sm" />
                  <div className="text-xs min-w-0">
                    <p className="font-semibold text-ink truncate">{user?.name}</p>
                    <p className="text-ink-subtle truncate">{user?.email}</p>
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
          </div>
        </div>
      )}
    </header>
  );
};
