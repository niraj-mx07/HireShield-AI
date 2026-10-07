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
  Chrome,
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
        p-4
        bg-ink/60
        backdrop-blur-sm
        animate-in
        fade-in
        duration-200
      "
    >
      <div
        className="
          relative
          w-full
          max-w-md
          bg-surface
          border
          border-ink/10
          rounded-3xl
          shadow-floating
          overflow-hidden
        "
      >

        {/* ----------------------------------------- */}
        {/* Close Button */}
        {/* ----------------------------------------- */}

        <button
          type="button"
          onClick={closeAuthModal}
          disabled={loading}
          className="
            absolute
            top-4
            right-4
            p-2
            rounded-full
            text-ink-muted
            hover:text-ink
            hover:bg-surface-2
            transition-colors
            z-10
            disabled:opacity-50
          "
        >
          <X className="w-5 h-5" />
        </button>


        {/* ----------------------------------------- */}
        {/* Header */}
        {/* ----------------------------------------- */}

        <div
          className="
            p-6
            sm:p-8
            bg-surface-2/60
            border-b
            border-ink/5
            text-center
            space-y-2
          "
        >

          <div
            className="
              w-12
              h-12
              rounded-2xl
              bg-primary
              text-surface
              flex
              items-center
              justify-center
              mx-auto
              shadow-subtle
            "
          >
            <ShieldCheck className="w-6 h-6" />
          </div>

          <h2
            className="
              font-serif
              text-2xl
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
            px-6
            py-2.5
            bg-secondary-container/40
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
            p-6
            sm:p-8
            space-y-5
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
                py-2
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
                py-2
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
                p-3
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
            className="space-y-4"
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
                      left-3.5
                      top-3
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
                      pl-10
                      pr-4
                      py-2.5
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
                    left-3.5
                    top-3
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
                    pl-10
                    pr-4
                    py-2.5
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
                    left-3.5
                    top-3
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
                    pl-10
                    pr-4
                    py-2.5
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
                py-3
                rounded-xl
                bg-primary
                text-surface
                text-xs
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

          <div className="relative pt-2">

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
              py-3
              rounded-xl
              bg-surface
              border
              border-ink/10
              text-xs
              font-semibold
              text-ink
              hover:bg-surface-2
              transition-all
              flex
              items-center
              justify-center
              gap-2
              disabled:opacity-60
              disabled:cursor-not-allowed
            "
          >

            <Chrome className="w-4 h-4" />

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
              pt-2
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
                mb-2
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