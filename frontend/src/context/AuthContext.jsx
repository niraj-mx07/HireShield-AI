import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { mockAnalysisHighRisk } from '../data/mockData';
import {
  apiSignup,
  apiLogin,
  apiGetUser,
  apiGetUserHistory,
  apiSaveUserHistory,
  apiDeleteHistoryItem,
  apiClearUserHistory,
} from '../services/api';

const AuthContext = createContext(null);

const STORAGE_USER_KEY = 'hireshield_auth_user';
const STORAGE_HISTORY_PREFIX = 'hireshield_user_history_';
const STORAGE_ACTIVE_REPORT_KEY = 'hireshield_active_report';

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

  // Active report persisted across page refreshes
  const [activeReport, setActiveReportState] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_ACTIVE_REPORT_KEY);
      return saved ? JSON.parse(saved) : mockAnalysisHighRisk;
    } catch {
      return mockAnalysisHighRisk;
    }
  });

  // MongoDB Cloud sync state
  const [dbSyncStatus, setDbSyncStatus] = useState('synced'); // 'synced' | 'syncing' | 'offline'
  const [lastSyncedAt, setLastSyncedAt] = useState(null);

  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState('login'); // 'login' | 'signup'
  const [authRedirectAction, setAuthRedirectAction] = useState(null);

  // Helper: Persist activeReport to localStorage
  const setActiveReport = useCallback((report) => {
    setActiveReportState(report);
    try {
      if (report) {
        localStorage.setItem(STORAGE_ACTIVE_REPORT_KEY, JSON.stringify(report));
      }
    } catch (e) {
      console.error('Failed to persist active report to localStorage:', e);
    }
  }, []);

  /**
   * Helper: Convert active assessment report to History item format
   */
  const reportToHistoryItem = useCallback((report) => {
    const rawScore = report.score ?? report.riskScore ?? 0;
    const score = Math.round(Number(rawScore) || 0);
    const level = report.riskLevel || (score >= 70 ? 'high' : score >= 35 ? 'moderate' : 'low');
    const jobTitle = report.jobTitle || report.title || (report.company ? `${report.company} Opportunity` : 'Opportunity Assessment');
    const company = report.company || 'Unknown Organisation';
    const recommendation = report.verdict || report.recommendation || (score >= 70 ? "DON'T APPLY" : score >= 35 ? 'HOLD' : 'APPLY');
    const date = report.date || (report.scanDate ? report.scanDate.split('•')[0].trim() : new Date().toISOString().split('T')[0]);

    return {
      id: report.id || `HS-${Date.now().toString().slice(-6)}`,
      jobTitle,
      title: jobTitle,
      company,
      date,
      scanDate: report.scanDate || date,
      riskScore: score,
      score,
      riskLevel: level,
      type: report.type || report.source || 'Job Listing',
      recommendation,
      verdict: recommendation,
      payload: {
        ...report,
        id: report.id || `HS-${Date.now().toString().slice(-6)}`,
        jobTitle,
        title: jobTitle,
        company,
        score,
        riskScore: score,
        riskLevel: level,
        verdict: recommendation,
        recommendation,
      },
    };
  }, []);

  /**
   * Sanitize list of history items
   */
  const sanitizeHistoryList = useCallback((rawList) => {
    if (!Array.isArray(rawList)) return [];
    return rawList.map((item) => {
      const actualScore =
        item.payload?.score !== undefined && item.payload?.score !== null
          ? item.payload.score
          : item.score !== undefined && item.score !== null
          ? item.score
          : item.riskScore !== undefined && item.riskScore !== null
          ? item.riskScore
          : 0;
      const score = Math.round(Number(actualScore) || 0);
      const level = item.riskLevel || item.payload?.riskLevel || (score >= 70 ? 'high' : score >= 35 ? 'moderate' : 'low');
      const jobTitle = item.jobTitle || item.title || item.payload?.jobTitle || item.payload?.title || 'Opportunity Assessment';
      const company = item.company || item.payload?.company || 'Unknown Organisation';
      const rec = item.recommendation || item.verdict || item.payload?.verdict || item.payload?.recommendation || (score >= 70 ? "DON'T APPLY" : score >= 35 ? 'HOLD' : 'APPLY');
      return {
        ...item,
        id: item.id || `HS-${Date.now().toString().slice(-6)}`,
        jobTitle,
        title: jobTitle,
        company,
        date: item.date || item.scanDate || new Date().toISOString().split('T')[0],
        riskScore: score,
        score,
        riskLevel: level,
        recommendation: rec,
        verdict: rec,
        payload: {
          ...(item.payload || {}),
          id: item.id || item.payload?.id || `HS-${Date.now().toString().slice(-6)}`,
          jobTitle,
          title: jobTitle,
          company,
          score,
          riskScore: score,
          riskLevel: level,
          verdict: rec,
          recommendation: rec,
        },
      };
    });
  }, []);

  /**
   * Sync user history with MongoDB database and local storage
   */
  const syncWithMongoDB = useCallback(async (currentUser) => {
    if (!currentUser || !currentUser.email) return;

    const email = currentUser.email.toLowerCase();
    const historyKey = `${STORAGE_HISTORY_PREFIX}${email}`;

    // Read cached local items first for instant display
    let localItems = [];
    try {
      const saved = localStorage.getItem(historyKey);
      if (saved) {
        localItems = sanitizeHistoryList(JSON.parse(saved));
      }
    } catch {
      localItems = [];
    }

    if (localItems.length > 0) {
      setUserHistory(localItems);
    }

    setDbSyncStatus('syncing');

    try {
      // 1. Fetch from MongoDB
      const res = await apiGetUserHistory(email);
      const remoteItems = sanitizeHistoryList(res.history || []);

      if (remoteItems.length > 0) {
        // Merge remote and local (remote takes precedence, deduplicated by id)
        const remoteIds = new Set(remoteItems.map((i) => i.id));
        const missingLocal = localItems.filter((l) => !remoteIds.has(l.id));

        const merged = [...remoteItems, ...missingLocal];
        setUserHistory(merged);
        localStorage.setItem(historyKey, JSON.stringify(merged));

        // If local had unsynced scans, save them to MongoDB
        if (missingLocal.length > 0) {
          await apiSaveUserHistory(email, missingLocal);
        }
      } else if (localItems.length > 0) {
        // MongoDB was empty for this user, upload all local items
        await apiSaveUserHistory(email, localItems);
        setUserHistory(localItems);
      } else {
        setUserHistory([]);
      }

      // Also refresh profile stats
      try {
        const profile = await apiGetUser(email);
        if (profile) {
          setUser((prev) => (prev ? { ...prev, ...profile } : profile));
        }
      } catch {
        // non-blocking
      }

      setDbSyncStatus('synced');
      setLastSyncedAt(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
    } catch (err) {
      console.warn('MongoDB history sync offline/error, using local cache:', err);
      setDbSyncStatus('offline');
      if (localItems.length > 0) {
        setUserHistory(localItems);
      }
    }
  }, [sanitizeHistoryList]);

  // Load user history & sync with MongoDB when user changes
  useEffect(() => {
    if (user && user.email) {
      syncWithMongoDB(user);
    } else {
      setUserHistory([]);
      setDbSyncStatus('synced');
    }
  }, [user?.email, syncWithMongoDB]);

  // Save to localStorage whenever user changes
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

  // Save userHistory to localStorage when it changes
  useEffect(() => {
    if (user && user.email) {
      try {
        const historyKey = `${STORAGE_HISTORY_PREFIX}${user.email.toLowerCase()}`;
        localStorage.setItem(historyKey, JSON.stringify(userHistory));
      } catch (e) {
        console.error('Failed to persist user history to localStorage:', e);
      }
    }
  }, [userHistory, user]);

  const isLoggedIn = !!user;

  /**
   * Add new assessment report to user's personal history & persist to MongoDB
   */
  const addReportToHistory = useCallback(async (report) => {
    const item = reportToHistoryItem(report);

    // Immediate optimistic local update
    setUserHistory((prev) => {
      const filtered = prev.filter((h) => h.id !== item.id);
      const nextList = [item, ...filtered];
      if (user && user.email) {
        try {
          const historyKey = `${STORAGE_HISTORY_PREFIX}${user.email.toLowerCase()}`;
          localStorage.setItem(historyKey, JSON.stringify(nextList));
        } catch (e) {
          console.error(e);
        }
      }
      return nextList;
    });

    // Asynchronous MongoDB save
    if (user && user.email) {
      try {
        setDbSyncStatus('syncing');
        await apiSaveUserHistory(user.email, [item]);
        setDbSyncStatus('synced');
        setLastSyncedAt(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
      } catch (err) {
        console.warn('MongoDB save scan failed, queued in localStorage:', err);
        setDbSyncStatus('offline');
      }
    }
  }, [reportToHistoryItem, user]);

  /**
   * Delete an assessment report from user history & delete from MongoDB
   */
  const deleteReportFromHistory = useCallback(async (reportId) => {
    setUserHistory((prev) => {
      const updated = prev.filter((h) => h.id !== reportId);
      if (user && user.email) {
        try {
          const historyKey = `${STORAGE_HISTORY_PREFIX}${user.email.toLowerCase()}`;
          localStorage.setItem(historyKey, JSON.stringify(updated));
        } catch (e) {
          console.error(e);
        }
      }
      return updated;
    });

    if (user && user.email) {
      try {
        setDbSyncStatus('syncing');
        await apiDeleteHistoryItem(user.email, reportId);
        setDbSyncStatus('synced');
        setLastSyncedAt(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
      } catch (err) {
        console.warn('MongoDB delete failed:', err);
        setDbSyncStatus('offline');
      }
    }
  }, [user]);

  /**
   * Clear all history for current user in MongoDB
   */
  const clearHistory = useCallback(async () => {
    setUserHistory([]);
    if (user && user.email) {
      try {
        const historyKey = `${STORAGE_HISTORY_PREFIX}${user.email.toLowerCase()}`;
        localStorage.removeItem(historyKey);
        setDbSyncStatus('syncing');
        await apiClearUserHistory(user.email);
        setDbSyncStatus('synced');
      } catch (err) {
        console.warn('MongoDB clear history failed:', err);
        setDbSyncStatus('offline');
      }
    }
  }, [user]);

  /**
   * Log in user with MongoDB persistence
   */
  const login = async (email, password, name) => {
    const enteredEmail = (email || 'candidate@hireshield.ai').trim();
    let displayName = name;
    if (!displayName) {
      const prefix = enteredEmail.split('@')[0].replace(/[._-]/g, ' ');
      displayName = prefix.charAt(0).toUpperCase() + prefix.slice(1);
    }

    let authUser = {
      id: `USR-${Date.now().toString().slice(-4)}`,
      name: displayName,
      email: enteredEmail,
      role: 'Student / Candidate',
      avatar: displayName.charAt(0).toUpperCase(),
      createdAt: new Date().toLocaleDateString(),
    };

    try {
      setDbSyncStatus('syncing');
      const remoteUser = await apiLogin({
        email: enteredEmail,
        password: password || undefined,
        name: displayName,
      });
      if (remoteUser && remoteUser.email) {
        authUser = {
          ...authUser,
          ...remoteUser,
        };
      }
    } catch (err) {
      console.warn('Backend login fallback to local profile:', err);
    }

    setUser(authUser);
    setIsAuthModalOpen(false);

    // Save any pending active report from this session to MongoDB
    if (activeReport && (activeReport.title || activeReport.company)) {
      try {
        const item = reportToHistoryItem(activeReport);
        apiSaveUserHistory(enteredEmail, [item]).catch((e) => console.warn(e));
      } catch (e) {
        console.warn('Could not format active report for MongoDB save:', e);
      }
    }

    // Sync history from MongoDB
    syncWithMongoDB(authUser);

    if (typeof authRedirectAction === 'function') {
      authRedirectAction();
      setAuthRedirectAction(null);
    }
    return { success: true };
  };

  /**
   * Register a brand new user in MongoDB
   */
  const signup = async (name, email, password) => {
    const cleanName = (name || 'New Member').trim();
    const cleanEmail = (email || 'user@hireshield.ai').trim();

    let authUser = {
      id: `USR-${Date.now().toString().slice(-4)}`,
      name: cleanName,
      email: cleanEmail,
      role: 'Candidate / Job Seeker',
      avatar: cleanName.charAt(0).toUpperCase(),
      createdAt: new Date().toLocaleDateString(),
    };

    try {
      setDbSyncStatus('syncing');
      const remoteUser = await apiSignup({
        name: cleanName,
        email: cleanEmail,
        password: password || undefined,
        role: 'Candidate / Job Seeker',
      });
      if (remoteUser && remoteUser.email) {
        authUser = {
          ...authUser,
          ...remoteUser,
        };
      }
    } catch (err) {
      console.warn('Backend signup fallback to local account:', err);
    }

    // Prepare initial scan history
    const initialItems = activeReport && activeReport.title ? [reportToHistoryItem(activeReport)] : [];
    const historyKey = `${STORAGE_HISTORY_PREFIX}${cleanEmail.toLowerCase()}`;
    try {
      localStorage.setItem(historyKey, JSON.stringify(initialItems));
    } catch (e) {
      console.error(e);
    }

    setUser(authUser);
    setUserHistory(initialItems);
    setIsAuthModalOpen(false);

    // Save initial items to MongoDB
    if (initialItems.length > 0) {
      apiSaveUserHistory(cleanEmail, initialItems).catch((e) => console.warn(e));
    }

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
    setDbSyncStatus('synced');
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

  const refreshDbSync = () => {
    if (user) {
      syncWithMongoDB(user);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoggedIn,
        userHistory,
        addReportToHistory,
        deleteReportFromHistory,
        clearHistory,
        login,
        signup,
        logout,
        activeReport,
        setActiveReport,
        loadReport,
        dbSyncStatus,
        lastSyncedAt,
        refreshDbSync,
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
