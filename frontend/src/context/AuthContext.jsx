import React, {
  createContext,
  useContext,
  useState,
  useEffect,
} from "react";

import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInWithPopup,
  GoogleAuthProvider,
  updateProfile,
  signOut,
} from "firebase/auth";

import { auth } from "../firebase";
import { mockAnalysisHighRisk } from "../data/mockData";

const AuthContext = createContext(null);

const STORAGE_HISTORY_PREFIX = "hireshield_user_history_";

export const AuthProvider = ({ children }) => {
  // --------------------------------------------------
  // Firebase user
  // --------------------------------------------------

  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);

  // --------------------------------------------------
  // HireShield application state
  // --------------------------------------------------

  const [userHistory, setUserHistory] = useState([]);

  const [activeReport, setActiveReport] =
    useState(mockAnalysisHighRisk);

  const [isAuthModalOpen, setIsAuthModalOpen] =
    useState(false);

  const [authModalMode, setAuthModalMode] =
    useState("login");

  const [authRedirectAction, setAuthRedirectAction] =
    useState(null);

  // --------------------------------------------------
  // Listen for Firebase authentication changes
  // --------------------------------------------------

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(
      auth,
      (firebaseUser) => {
        setUser(firebaseUser);
        setAuthLoading(false);
      }
    );

    return unsubscribe;
  }, []);

  // --------------------------------------------------
  // Load user's scan history
  // --------------------------------------------------

  useEffect(() => {
    if (!user?.email) {
      setUserHistory([]);
      return;
    }

    try {
      const historyKey =
        `${STORAGE_HISTORY_PREFIX}${user.email.toLowerCase()}`;

      const savedHistory =
        localStorage.getItem(historyKey);

      if (savedHistory) {
        setUserHistory(JSON.parse(savedHistory));
      } else {
        if (activeReport?.title) {
          const initialItem =
            reportToHistoryItem(activeReport);

          setUserHistory([initialItem]);

          localStorage.setItem(
            historyKey,
            JSON.stringify([initialItem])
          );
        } else {
          setUserHistory([]);
        }
      }
    } catch (error) {
      console.error(
        "Failed to load user history:",
        error
      );

      setUserHistory([]);
    }
  }, [user]);

  // --------------------------------------------------
  // Save user history
  // --------------------------------------------------

  useEffect(() => {
    if (!user?.email) {
      return;
    }

    try {
      const historyKey =
        `${STORAGE_HISTORY_PREFIX}${user.email.toLowerCase()}`;

      localStorage.setItem(
        historyKey,
        JSON.stringify(userHistory)
      );
    } catch (error) {
      console.error(
        "Failed to save user history:",
        error
      );
    }
  }, [userHistory, user]);

  // --------------------------------------------------
  // Convert report into history item
  // --------------------------------------------------

  const reportToHistoryItem = (report) => {
    const score = report.riskScore ?? 50;

    const level =
      score >= 70
        ? "high"
        : score >= 35
          ? "moderate"
          : "low";

    return {
      id:
        report.id ||
        `HS-${Date.now().toString().slice(-6)}`,

      jobTitle:
        report.title ||
        "Opportunity Assessment",

      company:
        report.company ||
        "Unknown Organisation",

      date:
        new Date()
          .toISOString()
          .split("T")[0],

      riskScore: score,

      riskLevel: level,

      type:
        report.source ||
        "Job Listing",

      recommendation:
        report.recommendation ||
        (
          score >= 70
            ? "DON'T APPLY"
            : score >= 35
              ? "HOLD"
              : "APPLY"
        ),

      payload: report,
    };
  };

  // --------------------------------------------------
  // Add report to user's history
  // --------------------------------------------------

  const addReportToHistory = (report) => {
    const item = reportToHistoryItem(report);

    setUserHistory((previousHistory) => {
      const filtered =
        previousHistory.filter(
          (historyItem) =>
            historyItem.id !== item.id
        );

      return [
        item,
        ...filtered,
      ];
    });
  };

  // --------------------------------------------------
  // EMAIL LOGIN
  // --------------------------------------------------

  const login = async (email, password) => {
    try {
      const result =
        await signInWithEmailAndPassword(
          auth,
          email.trim(),
          password
        );

      setIsAuthModalOpen(false);

      if (
        typeof authRedirectAction ===
        "function"
      ) {
        authRedirectAction();
        setAuthRedirectAction(null);
      }

      return {
        success: true,
        user: result.user,
      };

    } catch (error) {
      console.error(
        "Firebase login error:",
        error
      );

      return {
        success: false,
        error: getFirebaseErrorMessage(error),
      };
    }
  };

  // --------------------------------------------------
  // EMAIL SIGNUP
  // --------------------------------------------------

  const signup = async (
    name,
    email,
    password
  ) => {
    try {
      const cleanName = name.trim();
      const cleanEmail = email.trim();

      const result =
        await createUserWithEmailAndPassword(
          auth,
          cleanEmail,
          password
        );

      // Store user's name in Firebase
      await updateProfile(
        result.user,
        {
          displayName: cleanName,
        }
      );

      // Create initial history for new user
      const historyKey =
        `${STORAGE_HISTORY_PREFIX}${cleanEmail.toLowerCase()}`;

      const initialItems =
        activeReport?.title
          ? [reportToHistoryItem(activeReport)]
          : [];

      try {
        localStorage.setItem(
          historyKey,
          JSON.stringify(initialItems)
        );
      } catch (storageError) {
        console.error(
          "Failed to save initial history:",
          storageError
        );
      }

      setUserHistory(initialItems);
      setIsAuthModalOpen(false);

      if (
        typeof authRedirectAction ===
        "function"
      ) {
        authRedirectAction();
        setAuthRedirectAction(null);
      }

      return {
        success: true,
        user: result.user,
      };

    } catch (error) {
      console.error(
        "Firebase signup error:",
        error
      );

      return {
        success: false,
        error: getFirebaseErrorMessage(error),
      };
    }
  };

  // --------------------------------------------------
  // GOOGLE LOGIN
  // --------------------------------------------------

  const loginWithGoogle = async () => {
    try {
      const provider =
        new GoogleAuthProvider();

      provider.setCustomParameters({
        prompt: "select_account",
      });

      const result =
        await signInWithPopup(
          auth,
          provider
        );

      setIsAuthModalOpen(false);

      if (
        typeof authRedirectAction ===
        "function"
      ) {
        authRedirectAction();
        setAuthRedirectAction(null);
      }

      return {
        success: true,
        user: result.user,
      };

    } catch (error) {
      console.error(
        "Google login error:",
        error
      );

      return {
        success: false,
        error: getFirebaseErrorMessage(error),
      };
    }
  };

  // --------------------------------------------------
  // LOGOUT
  // --------------------------------------------------

  const logout = async () => {
    try {
      await signOut(auth);

      setUser(null);
      setUserHistory([]);

    } catch (error) {
      console.error(
        "Logout error:",
        error
      );
    }
  };

  // --------------------------------------------------
  // Authentication modal controls
  // --------------------------------------------------

  const openAuthModal = (
    mode = "login",
    actionCallback = null
  ) => {
    setAuthModalMode(mode);

    setAuthRedirectAction(
      () => actionCallback
    );

    setIsAuthModalOpen(true);
  };

  const closeAuthModal = () => {
    setIsAuthModalOpen(false);
    setAuthRedirectAction(null);
  };

  // --------------------------------------------------
  // Report handling
  // --------------------------------------------------

  const loadReport = (reportData) => {
    setActiveReport(reportData);

    if (user) {
      addReportToHistory(reportData);
    }
  };

  // --------------------------------------------------
  // Authentication status
  // --------------------------------------------------

  const isLoggedIn = !!user;

  // --------------------------------------------------
  // Context provider
  // --------------------------------------------------

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoggedIn,
        authLoading,

        userHistory,
        addReportToHistory,

        login,
        signup,
        loginWithGoogle,
        logout,

        activeReport,
        loadReport,

        isAuthModalOpen,
        authModalMode,

        openAuthModal,
        closeAuthModal,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

// --------------------------------------------------
// Firebase error messages
// --------------------------------------------------

const getFirebaseErrorMessage = (error) => {
  switch (error.code) {
    case "auth/invalid-credential":
      return "Incorrect email or password.";

    case "auth/user-not-found":
      return "No account exists with this email.";

    case "auth/wrong-password":
      return "Incorrect password.";

    case "auth/email-already-in-use":
      return "An account already exists with this email.";

    case "auth/weak-password":
      return "Password should be at least 6 characters.";

    case "auth/invalid-email":
      return "Please enter a valid email address.";

    case "auth/popup-closed-by-user":
      return "Google sign-in was cancelled.";

    case "auth/popup-blocked":
      return "The sign-in popup was blocked by your browser.";

    case "auth/network-request-failed":
      return "Network error. Please check your internet connection.";

    default:
      return (
        error.message ||
        "Authentication failed. Please try again."
      );
  }
};

// --------------------------------------------------
// useAuth hook
// --------------------------------------------------

export const useAuth = () => {
  const context =
    useContext(AuthContext);

  if (!context) {
    throw new Error(
      "useAuth must be used within AuthProvider"
    );
  }

  return context;
};