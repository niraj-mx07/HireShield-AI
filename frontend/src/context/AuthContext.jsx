import React, { createContext, useContext, useState, useEffect } from 'react';
import { mockAnalysisHighRisk } from '../data/mockData';

const AuthContext = createContext(null);

const STORAGE_USER_KEY = 'hireshield_auth_user';
const STORAGE_HISTORY_PREFIX = 'hireshield_user_history_';

export const AuthProvider = ({ children }) => {
  // Load saved user from localStorage
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_USER_KEY);
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  // User-specific scan history
  const [userHistory, setUserHistory] = useState([]);

  const [activeReport, setActiveReport] = useState(mockAnalysisHighRisk);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState('login'); // 'login' | 'signup'
  const [authRedirectAction, setAuthRedirectAction] = useState(null);

  // Load user history when user changes
  useEffect(() => {
    if (user && user.email) {
      try {
        const historyKey = `${STORAGE_HISTORY_PREFIX}${user.email.toLowerCase()}`;
        const savedHistory = localStorage.getItem(historyKey);
        if (savedHistory) {
          setUserHistory(JSON.parse(savedHistory));
        } else {
          // If fresh user and activeReport exists, add activeReport as first item
          if (activeReport && activeReport.title) {
            const initialItem = reportToHistoryItem(activeReport);
            setUserHistory([initialItem]);
            localStorage.setItem(historyKey, JSON.stringify([initialItem]));
          } else {
            setUserHistory([]);
          }
        }
      } catch (e) {
        console.error('Failed to load user history:', e);
        setUserHistory([]);
      }
    } else {
      setUserHistory([]);
    }
  }, [user]);

  // Save to localStorage when user changes
  useEffect(() => {
    try {
      if (user) {
        localStorage.setItem(STORAGE_USER_KEY, JSON.stringify(user));
      } else {
        localStorage.removeItem(STORAGE_USER_KEY);
      }
    } catch (e) {
      console.error('Failed to update localStorage auth:', e);
    }
  }, [user]);

  // Save userHistory when it updates
  useEffect(() => {
    if (user && user.email) {
      try {
        const historyKey = `${STORAGE_HISTORY_PREFIX}${user.email.toLowerCase()}`;
        localStorage.setItem(historyKey, JSON.stringify(userHistory));
      } catch (e) {
        console.error('Failed to persist user history:', e);
      }
    }
  }, [userHistory, user]);

  const isLoggedIn = !!user;

  /**
   * Helper: Convert active assessment report to History item format
   */
  const reportToHistoryItem = (report) => {
    const score = report.riskScore ?? 50;
    const level = score >= 70 ? 'high' : score >= 35 ? 'moderate' : 'low';
    return {
      id: report.id || `HS-${Date.now().toString().slice(-6)}`,
      jobTitle: report.title || 'Opportunity Assessment',
      company: report.company || 'Unknown Organisation',
      date: new Date().toISOString().split('T')[0],
      riskScore: score,
      riskLevel: level,
      type: report.source || 'Job Listing',
      recommendation: report.recommendation || (score >= 70 ? "DON'T APPLY" : score >= 35 ? 'HOLD' : 'APPLY'),
      payload: report,
    };
  };

  /**
   * Add new assessment report to user's personal history
   */
  const addReportToHistory = (report) => {
    const item = reportToHistoryItem(report);
    setUserHistory((prev) => {
      const filtered = prev.filter((h) => h.id !== item.id);
      return [item, ...filtered];
    });
  };

  /**
   * Log in existing user
   */
  const login = (email, password, name) => {
    const enteredEmail = (email || 'candidate@hireshield.ai').trim();
    let displayName = name;
    if (!displayName) {
      const prefix = enteredEmail.split('@')[0].replace(/[._-]/g, ' ');
      displayName = prefix.charAt(0).toUpperCase() + prefix.slice(1);
    }

    const newUser = {
      id: `USR-${Date.now().toString().slice(-4)}`,
      name: displayName,
      email: enteredEmail,
      role: 'Student / Candidate',
      avatar: displayName.charAt(0).toUpperCase(),
      createdAt: new Date().toLocaleDateString(),
    };

    setUser(newUser);
    setIsAuthModalOpen(false);

    if (typeof authRedirectAction === 'function') {
      authRedirectAction();
      setAuthRedirectAction(null);
    }
    return { success: true };
  };

  /**
   * Register a brand new user with their custom name & email
   */
  const signup = (name, email, password) => {
    const cleanName = (name || 'New Member').trim();
    const cleanEmail = (email || 'user@hireshield.ai').trim();

    const newUser = {
      id: `USR-${Date.now().toString().slice(-4)}`,
      name: cleanName,
      email: cleanEmail,
      role: 'Candidate / Job Seeker',
      avatar: cleanName.charAt(0).toUpperCase(),
      createdAt: new Date().toLocaleDateString(),
    };

    // Save as new user with empty or current active scan history
    const historyKey = `${STORAGE_HISTORY_PREFIX}${cleanEmail.toLowerCase()}`;
    const initialItems = activeReport && activeReport.title ? [reportToHistoryItem(activeReport)] : [];
    try {
      localStorage.setItem(historyKey, JSON.stringify(initialItems));
    } catch (e) {
      console.error(e);
    }

    setUser(newUser);
    setUserHistory(initialItems);
    setIsAuthModalOpen(false);

    if (typeof authRedirectAction === 'function') {
      authRedirectAction();
      setAuthRedirectAction(null);
    }
    return { success: true };
  };

  /**
   * Log out user
   */
  const logout = () => {
    setUser(null);
    setUserHistory([]);
  };

  /**
   * Modal controls
   */
  const openAuthModal = (mode = 'login', actionCallback = null) => {
    setAuthModalMode(mode);
    setAuthRedirectAction(() => actionCallback);
    setIsAuthModalOpen(true);
  };

  const closeAuthModal = () => {
    setIsAuthModalOpen(false);
    setAuthRedirectAction(null);
  };

  const loadReport = (reportData) => {
    setActiveReport(reportData);
    if (isLoggedIn) {
      addReportToHistory(reportData);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoggedIn,
        userHistory,
        addReportToHistory,
        login,
        signup,
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

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
