import React, { useState } from 'react';
import { X, ShieldCheck, Mail, Lock, User, ArrowRight, CheckCircle2, FileText, History, BarChart3, Loader2, Eye, EyeOff } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const AuthModal = () => {
  const { isAuthModalOpen, authModalMode, closeAuthModal, login, signup, loginWithGoogle } = useAuth();
  const [mode, setMode] = useState(authModalMode || 'login'); // 'login' | 'signup'
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const GOOGLE_CLIENT_ID =
    import.meta.env?.VITE_GOOGLE_CLIENT_ID ||
    '673762437253-ck9la636bc3o7s97qia89r8rcct9o1di.apps.googleusercontent.com';

  // Sync mode and setup Google One-Tap if client ID is configured
  React.useEffect(() => {
    if (authModalMode) {
      setMode(authModalMode);
      setError('');
    }

    if (isAuthModalOpen && GOOGLE_CLIENT_ID && window.google?.accounts?.id) {
      try {
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: async (response) => {
            if (response.credential) {
              setLoading(true);
              try {
                await loginWithGoogle(response.credential);
              } catch (err) {
                setError(err?.message || 'Google authentication failed.');
              } finally {
                setLoading(false);
              }
            }
          },
        });
        window.google.accounts.id.prompt();
      } catch (err) {
        console.warn('Google One-Tap initialization error:', err);
      }
    }
  }, [authModalMode, isAuthModalOpen, loginWithGoogle, GOOGLE_CLIENT_ID]);

  if (!isAuthModalOpen) return null;

  const handleGoogleSignIn = () => {
    setError('');
    if (!GOOGLE_CLIENT_ID) {
      setError('Google Sign-In is ready! Please configure VITE_GOOGLE_CLIENT_ID in your environment variables.');
      return;
    }

    if (window.google?.accounts?.id) {
      setLoading(true);
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: async (response) => {
          if (response.credential) {
            try {
              await loginWithGoogle(response.credential);
            } catch (err) {
              setError(err?.message || 'Google authentication failed.');
            } finally {
              setLoading(false);
            }
          }
        },
      });
      window.google.accounts.id.prompt();
    } else {
      setError('Google Identity Service is loading. Please try again in a moment.');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    const cleanEmail = email.trim().toLowerCase();
    const cleanName = name.trim();

    if (!cleanEmail) {
      setError('Please enter your email address.');
      return;
    }

    if (mode === 'signup') {
      if (!cleanName) {
        setError('Please enter your name.');
        return;
      }
      if (!password || password.length < 6) {
        setError('Password must be at least 6 characters long.');
        return;
      }
    }

    setLoading(true);
    try {
      if (mode === 'signup') {
        await signup(cleanName, cleanEmail, password);
      } else {
        await login(cleanEmail, password);
      }
    } catch (err) {
      setError(err?.message || 'Authentication error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-md bg-surface border border-ink/10 rounded-3xl shadow-floating overflow-hidden">
        
        {/* Close Button */}
        <button
          onClick={closeAuthModal}
          className="absolute top-4 right-4 p-2 rounded-full text-ink-muted hover:text-ink hover:bg-surface-2 transition-colors z-10"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="p-6 sm:p-8 bg-surface-2/60 border-b border-ink/5 text-center space-y-2">
          <div className="w-12 h-12 rounded-2xl bg-primary text-surface flex items-center justify-center mx-auto shadow-subtle">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <h2 className="font-serif text-2xl font-bold text-ink">
            {mode === 'login' ? 'Welcome Back to HireShield' : 'Create Your Free Account'}
          </h2>
          <p className="text-xs text-ink-muted max-w-xs mx-auto">
            {mode === 'login'
              ? 'Sign in to access your assessment history, analytics, and official PDF exports.'
              : 'Sign up to unlock PDF report downloads, personal history tracking, and security alerts.'}
          </p>
        </div>

        {/* Value Callout */}
        <div className="px-6 py-2.5 bg-secondary-container/40 border-b border-ink/5 flex items-center justify-between text-[11px] text-ink-muted">
          <span className="flex items-center gap-1.5 font-medium text-primary">
            <CheckCircle2 className="w-3.5 h-3.5 text-primary" />
            Risk Calculation is Always 100% Free
          </span>
          <span className="text-ink-subtle">No card needed</span>
        </div>

        {/* Form Body */}
        <div className="p-6 sm:p-8 space-y-5">
          
          {/* Tabs: Sign In vs Sign Up */}
          <div className="flex rounded-full bg-surface-2 p-1 border border-ink/5 text-xs font-semibold">
            <button
              type="button"
              onClick={() => { setMode('login'); setError(''); }}
              className={`flex-1 py-2 rounded-full transition-all ${
                mode === 'login' ? 'bg-surface text-ink shadow-sm' : 'text-ink-muted hover:text-ink'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => { setMode('signup'); setError(''); }}
              className={`flex-1 py-2 rounded-full transition-all ${
                mode === 'signup' ? 'bg-surface text-ink shadow-sm' : 'text-ink-muted hover:text-ink'
              }`}
            >
              Create Account
            </button>
          </div>

          {error && (
            <div className="p-3 rounded-xl bg-risk-high-bg text-risk-high text-xs font-medium">
              {error}
            </div>
          )}

          {/* Google One-Tap / OAuth Sign-In Button */}
          <button
            type="button"
            disabled={loading}
            onClick={handleGoogleSignIn}
            className="w-full py-3 px-4 rounded-2xl bg-surface hover:bg-surface-2 border border-ink/15 text-xs font-semibold text-ink shadow-sm transition-all flex items-center justify-center gap-3 disabled:opacity-60 group"
          >
            <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24">
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
              />
            </svg>
            <span>Continue with Google</span>
          </button>

          {/* Divider */}
          <div className="relative flex items-center justify-center my-1">
            <div className="border-t border-ink/10 w-full" />
            <span className="bg-surface px-3 text-[10px] text-ink-subtle uppercase tracking-wider font-semibold">
              or continue with email
            </span>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'signup' && (
              <div className="space-y-1">
                <label className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider">
                  Full Name
                </label>
                <div className="relative">
                  <User className="w-4 h-4 text-ink-subtle absolute left-3.5 top-3" />
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Enter your full name"
                    className="w-full pl-10 pr-4 py-2.5 text-sm bg-canvas border border-ink/10 rounded-xl text-ink placeholder-ink-subtle focus:outline-none focus:border-primary"
                  />
                </div>
              </div>
            )}

            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider">
                Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-ink-subtle absolute left-3.5 top-3" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter your email address"
                  className="w-full pl-10 pr-4 py-2.5 text-sm bg-canvas border border-ink/10 rounded-xl text-ink placeholder-ink-subtle focus:outline-none focus:border-primary"
                />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <label className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider">
                  Password
                </label>
                {mode === 'signup' && (
                  <span className="text-[10px] text-ink-subtle">
                    Min 6 characters
                  </span>
                )}
              </div>
              <div className="relative">
                <Lock className="w-4 h-4 text-ink-subtle absolute left-3.5 top-3" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={mode === 'signup' ? 'Create password (min 6 characters)' : 'Enter your password'}
                  className="w-full pl-10 pr-10 py-2.5 text-sm bg-canvas border border-ink/10 rounded-xl text-ink placeholder-ink-subtle focus:outline-none focus:border-primary"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-2.5 p-0.5 text-ink-subtle hover:text-ink transition-colors"
                  tabIndex={-1}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-xl bg-primary text-surface text-xs font-bold shadow-subtle hover:bg-primary-container transition-all flex items-center justify-center gap-2 disabled:opacity-60"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>{mode === 'login' ? 'Signing in...' : 'Creating account...'}</span>
                </>
              ) : (
                <>
                  <span>{mode === 'login' ? 'Sign In & Continue' : 'Create Free Account'}</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Mode Switch Text Prompt */}
          <div className="text-center pt-1">
            {mode === 'login' ? (
              <p className="text-xs text-ink-muted">
                Don't have an account?{' '}
                <button
                  type="button"
                  onClick={() => { setMode('signup'); setError(''); }}
                  className="font-semibold text-primary hover:underline ml-1"
                >
                  Create one for free
                </button>
              </p>
            ) : (
              <p className="text-xs text-ink-muted">
                Already have an account?{' '}
                <button
                  type="button"
                  onClick={() => { setMode('login'); setError(''); }}
                  className="font-semibold text-primary hover:underline ml-1"
                >
                  Sign in
                </button>
              </p>
            )}
          </div>

          {/* Unlocked Benefits list */}
          <div className="pt-4 border-t border-ink/5">
            <p className="text-[10px] font-semibold text-ink-subtle uppercase tracking-wider mb-2.5">
              Features with Free Account:
            </p>
            <div className="grid grid-cols-3 gap-2 text-[11px] text-ink-muted">
              <div className="flex items-center gap-1.5 p-2 rounded-xl bg-surface-2/60">
                <FileText className="w-3.5 h-3.5 text-primary flex-shrink-0" />
                <span>PDF Reports</span>
              </div>
              <div className="flex items-center gap-1.5 p-2 rounded-xl bg-surface-2/60">
                <History className="w-3.5 h-3.5 text-primary flex-shrink-0" />
                <span>Scan History</span>
              </div>
              <div className="flex items-center gap-1.5 p-2 rounded-xl bg-surface-2/60">
                <BarChart3 className="w-3.5 h-3.5 text-primary flex-shrink-0" />
                <span>Threat Intel</span>
              </div>
            </div>
          </div>

        </div>

      </div>
    </div>
  );
};
