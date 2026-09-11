import React, { createContext, useContext, useState } from 'react';
import { mockAnalysisHighRisk } from '../data/mockData';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [activeReport, setActiveReport] = useState(mockAnalysisHighRisk);

  const toggleAuth = () => {
    setIsLoggedIn(prev => !prev);
  };

  const loadReport = (reportData) => {
    setActiveReport(reportData);
  };

  return (
    <AuthContext.Provider value={{ isLoggedIn, toggleAuth, activeReport, loadReport }}>
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
