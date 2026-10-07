import React, { useState, useEffect } from "react";

import {
  X,
  ShieldCheck,
  Mail,
  Lock,
  User,
  ArrowRight,
  CheckCircle2,
  FileText,
  History,
  BarChart3,
} from "lucide-react";

import { useAuth } from "../context/AuthContext";

export const AuthModal = () => {
  const {
    isAuthModalOpen,
    authModalMode,
    closeAuthModal,
    login,
    signup,
    loginWithGoogle,
  } = useAuth();

  const [mode, setMode] =
    useState(authModalMode || "login");

  const [name, setName] =
    useState("");

  const [email, setEmail] =
    useState("");

  const [password, setPassword] =
    useState("");

  const [error, setError] =
    useState("");

  const [loading, setLoading] =
    useState(false);

  // --------------------------------------------------
  // Sync modal mode
  // --------------------------------------------------

  useEffect(() => {
    if (authModalMode) {
      setMode(authModalMode);
      setError("");
    }
  }, [authModalMode]);

  // --------------------------------------------------
  // Close on Escape key & lock body scroll
  // --------------------------------------------------

  useEffect(() => {
    if (!isAuthModalOpen) return;

    const handleKeyDown = (event) => {
      if (event.key === "Escape" && !loading) {
        closeAuthModal();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [isAuthModalOpen, loading, closeAuthModal]);

  // --------------------------------------------------
  // Don't render when closed
  // --------------------------------------------------

  if (!isAuthModalOpen) {
    return null;
  }

  // --------------------------------------------------
  // Email authentication
  // --------------------------------------------------

  const handleSubmit = async (event) => {
    event.preventDefault();

    setError("");

    // Validate email
    if (!email.trim()) {
      setError(
        "Please enter your email address."
      );
      return;
    }

    // Validate password
    if (!password) {
      setError(
        "Please enter your password."
      );
      return;
    }

    // Validate name during signup
    if (
      mode === "signup" &&
      !name.trim()
    ) {
      setError(
        "Please enter your name."
      );
      return;
    }

    setLoading(true);

    try {
      let result;

      if (mode === "signup") {
        result =
          await signup(
            name,
            email,
            password
          );
      } else {
        result =
          await login(
            email,
            password
          );
      }

      if (!result.success) {
        setError(result.error);
      }

    } catch (error) {
      console.error(error);

      setError(
        "Something went wrong. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  // --------------------------------------------------
  // Google authentication
  // --------------------------------------------------

  const handleGoogleLogin = async () => {
    setError("");
    setLoading(true);

    try {
      const result =
        await loginWithGoogle();

      if (!result.success) {
        setError(result.error);
      }

    } catch (error) {
      console.error(error);

      setError(
        "Google sign-in failed. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  // --------------------------------------------------
  // Render
  // --------------------------------------------------

  return (
    <div
      className="
        fixed
        inset-0
        z-50
        flex
        items-center
        justify-center
        p-3
        sm:p-4
        bg-ink/60
        backdrop-blur-sm
        animate-in
        fade-in
        duration-200
      "
      onClick={(event) => {
        if (event.target === event.currentTarget && !loading) {
          closeAuthModal();
        }
      }}
    >
      <div
        className="
          relative
          w-full
          max-w-md
          max-h-[90vh]
          overflow-y-auto
          overscroll-contain
          bg-surface
          border
          border-ink/10
          rounded-2xl
          sm:rounded-3xl
          shadow-floating
          my-auto
        "
        onClick={(event) => event.stopPropagation()}
      >

        {/* ----------------------------------------- */}
        {/* Close Button */}
        {/* ----------------------------------------- */}

        <button
          type="button"
          onClick={closeAuthModal}
          disabled={loading}
          aria-label="Close dialog"
          className="
            absolute
            top-3
            right-3
            sm:top-4
            sm:right-4
            p-1.5
            sm:p-2
            rounded-full
            text-ink-muted
            hover:text-ink
            hover:bg-surface-2
            transition-colors
            z-10
            disabled:opacity-50
          "
        >
          <X className="w-4 h-4 sm:w-5 sm:h-5" />
        </button>


        {/* ----------------------------------------- */}
        {/* Header */}
        {/* ----------------------------------------- */}

        <div
          className="
            px-5
            py-4
            sm:px-7
            sm:py-5
            bg-surface-2/60
            border-b
            border-ink/5
            text-center
            space-y-1.5
          "
        >

          <div
            className="
              w-9
              h-9
              sm:w-10
              sm:h-10
              rounded-xl
              bg-primary
              text-surface
              flex
              items-center
              justify-center
              mx-auto
              shadow-subtle
              mb-0.5
            "
          >
            <ShieldCheck className="w-5 h-5" />
          </div>

          <h2
            className="
              font-serif
              text-xl
              sm:text-2xl
              font-bold
              text-ink
            "
          >
            {mode === "login"
              ? "Welcome Back to HireShield"
              : "Create Your Free Account"}
          </h2>

          <p
            className="
              text-xs
              text-ink-muted
              max-w-xs
              mx-auto
              leading-relaxed
            "
          >
            {mode === "login"
              ? "Sign in to access your assessment history, analytics, and official PDF exports."
              : "Sign up to unlock PDF report downloads, personal history tracking, and security alerts."}
          </p>

        </div>


        {/* ----------------------------------------- */}
        {/* Free Account Message */}
        {/* ----------------------------------------- */}

        <div
          className="
            px-5
            py-2
            sm:px-6
            bg-secondary-container/30
            border-b
            border-ink/5
            flex
            items-center
            justify-between
            text-[11px]
            text-ink-muted
          "
        >

          <span
            className="
              flex
              items-center
              gap-1.5
              font-medium
              text-primary
            "
          >
            <CheckCircle2 className="w-3.5 h-3.5" />

            Risk Calculation is Always 100% Free
          </span>

          <span className="text-ink-subtle">
            No card needed
          </span>

        </div>


        {/* ----------------------------------------- */}
        {/* Form Body */}
        {/* ----------------------------------------- */}

        <div
          className="
            p-5
            sm:p-6
            space-y-3.5
            sm:space-y-4
          "
        >

          {/* --------------------------------------- */}
          {/* Login / Signup Tabs */}
          {/* --------------------------------------- */}

          <div
            className="
              flex
              rounded-full
              bg-surface-2
              p-1
              border
              border-ink/5
              text-xs
              font-semibold
            "
          >

            <button
              type="button"
              disabled={loading}
              onClick={() => {
                setMode("login");
                setError("");
              }}
              className={`
                flex-1
                py-1.5
                rounded-full
                transition-all
                ${mode === "login"
                  ? "bg-surface text-ink shadow-sm"
                  : "text-ink-muted hover:text-ink"
                }
              `}
            >
              Sign In
            </button>


            <button
              type="button"
              disabled={loading}
              onClick={() => {
                setMode("signup");
                setError("");
              }}
              className={`
                flex-1
                py-1.5
                rounded-full
                transition-all
                ${mode === "signup"
                  ? "bg-surface text-ink shadow-sm"
                  : "text-ink-muted hover:text-ink"
                }
              `}
            >
              Create Account
            </button>

          </div>


          {/* --------------------------------------- */}
          {/* Error */}
          {/* --------------------------------------- */}

          {error && (
            <div
              className="
                p-2.5
                rounded-xl
                bg-risk-high-bg
                text-risk-high
                text-xs
                font-medium
              "
            >
              {error}
            </div>
          )}


          {/* --------------------------------------- */}
          {/* Email / Password Form */}
          {/* --------------------------------------- */}

          <form
            onSubmit={handleSubmit}
            className="space-y-3 sm:space-y-3.5"
          >

            {/* Name */}
            {mode === "signup" && (
              <div className="space-y-1">

                <label
                  className="
                    text-[11px]
                    font-semibold
                    text-ink-muted
                    uppercase
                    tracking-wider
                  "
                >
                  Full Name
                </label>

                <div className="relative">

                  <User
                    className="
                      w-4
                      h-4
                      text-ink-subtle
                      absolute
                      left-3
                      top-2.5
                      sm:top-3
                    "
                  />

                  <input
                    type="text"
                    required
                    disabled={loading}
                    value={name}
                    onChange={(event) =>
                      setName(
                        event.target.value
                      )
                    }
                    placeholder="e.g. Alex Chen"
                    className="
                      w-full
                      pl-9
                      pr-3.5
                      py-2
                      sm:py-2.5
                      text-sm
                      bg-canvas
                      border
                      border-ink/10
                      rounded-xl
                      text-ink
                      placeholder-ink-subtle
                      focus:outline-none
                      focus:border-primary
                      disabled:opacity-60
                    "
                  />

                </div>

              </div>
            )}


            {/* Email */}
            <div className="space-y-1">

              <label
                className="
                  text-[11px]
                  font-semibold
                  text-ink-muted
                  uppercase
                  tracking-wider
                "
              >
                Email Address
              </label>

              <div className="relative">

                <Mail
                  className="
                    w-4
                    h-4
                    text-ink-subtle
                    absolute
                    left-3
                    top-2.5
                    sm:top-3
                  "
                />

                <input
                  type="email"
                  required
                  disabled={loading}
                  value={email}
                  onChange={(event) =>
                    setEmail(
                      event.target.value
                    )
                  }
                  placeholder="student@university.edu or candidate@email.com"
                  className="
                    w-full
                    pl-9
                    pr-3.5
                    py-2
                    sm:py-2.5
                    text-sm
                    bg-canvas
                    border
                    border-ink/10
                    rounded-xl
                    text-ink
                    placeholder-ink-subtle
                    focus:outline-none
                    focus:border-primary
                    disabled:opacity-60
                  "
                />

              </div>

            </div>


            {/* Password */}
            <div className="space-y-1">

              <label
                className="
                  text-[11px]
                  font-semibold
                  text-ink-muted
                  uppercase
                  tracking-wider
                "
              >
                Password
              </label>

              <div className="relative">

                <Lock
                  className="
                    w-4
                    h-4
                    text-ink-subtle
                    absolute
                    left-3
                    top-2.5
                    sm:top-3
                  "
                />

                <input
                  type="password"
                  required
                  minLength={6}
                  disabled={loading}
                  value={password}
                  onChange={(event) =>
                    setPassword(
                      event.target.value
                    )
                  }
                  placeholder="••••••••"
                  className="
                    w-full
                    pl-9
                    pr-3.5
                    py-2
                    sm:py-2.5
                    text-sm
                    bg-canvas
                    border
                    border-ink/10
                    rounded-xl
                    text-ink
                    placeholder-ink-subtle
                    focus:outline-none
                    focus:border-primary
                    disabled:opacity-60
                  "
                />

              </div>

              {mode === "signup" && (
                <p className="text-[10px] text-ink-subtle">
                  Password must be at least 6 characters.
                </p>
              )}

            </div>


            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="
                w-full
                py-2.5
                sm:py-3
                rounded-xl
                bg-primary
                text-surface
                text-xs
                sm:text-sm
                font-bold
                shadow-subtle
                hover:bg-primary-container
                transition-all
                flex
                items-center
                justify-center
                gap-2
                disabled:opacity-60
                disabled:cursor-not-allowed
              "
            >

              {loading ? (
                <span>
                  Please wait...
                </span>
              ) : (
                <>
                  <span>
                    {mode === "login"
                      ? "Sign In & Continue"
                      : "Create Free Account"}
                  </span>

                  <ArrowRight className="w-4 h-4" />
                </>
              )}

            </button>

          </form>


          {/* --------------------------------------- */}
          {/* Divider */}
          {/* --------------------------------------- */}

          <div className="relative py-1">

            <div
              className="
                absolute
                inset-0
                flex
                items-center
              "
            >
              <div
                className="
                  w-full
                  border-t
                  border-ink/10
                "
              />
            </div>

            <div
              className="
                relative
                flex
                justify-center
                text-[10px]
                uppercase
              "
            >
              <span
                className="
                  bg-surface
                  px-2
                  text-ink-subtle
                  font-medium
                "
              >
                Or continue with
              </span>
            </div>

          </div>


          {/* --------------------------------------- */}
          {/* Google Login */}
          {/* --------------------------------------- */}

          <button
            type="button"
            disabled={loading}
            onClick={handleGoogleLogin}
            className="
              w-full
              py-2.5
              sm:py-3
              rounded-xl
              bg-surface
              border
              border-ink/10
              text-xs
              font-semibold
              text-ink
              hover:bg-surface-2
              hover:border-ink/20
              transition-all
              flex
              items-center
              justify-center
              gap-2.5
              disabled:opacity-60
              disabled:cursor-not-allowed
            "
          >

            {/* Standard Google "G" multicolor SVG icon */}
            <svg
              className="w-4 h-4 flex-shrink-0"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
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

            <span>
              {loading
                ? "Please wait..."
                : "Continue with Google"}
            </span>

          </button>


          {/* --------------------------------------- */}
          {/* Benefits */}
          {/* --------------------------------------- */}

          <div
            className="
              pt-2.5
              border-t
              border-ink/5
            "
          >

            <p
              className="
                text-[10px]
                font-semibold
                text-ink-subtle
                uppercase
                tracking-wider
                mb-1.5
              "
            >
              Features with Free Account:
            </p>

            <div
              className="
                grid
                grid-cols-3
                gap-2
                text-[11px]
                text-ink-muted
              "
            >

              <div
                className="
                  flex
                  items-center
                  gap-1.5
                "
              >
                <FileText
                  className="
                    w-3.5
                    h-3.5
                    text-primary
                    flex-shrink-0
                  "
                />

                <span>
                  PDF Reports
                </span>
              </div>


              <div
                className="
                  flex
                  items-center
                  gap-1.5
                "
              >
                <History
                  className="
                    w-3.5
                    h-3.5
                    text-primary
                    flex-shrink-0
                  "
                />

                <span>
                  Scan History
                </span>
              </div>


              <div
                className="
                  flex
                  items-center
                  gap-1.5
                "
              >
                <BarChart3
                  className="
                    w-3.5
                    h-3.5
                    text-primary
                    flex-shrink-0
                  "
                />

                <span>
                  Threat Intel
                </span>
              </div>

            </div>

          </div>

        </div>

      </div>
    </div>
  );
};