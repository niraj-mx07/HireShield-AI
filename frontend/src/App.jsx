import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { Header } from './components/Header';
import { Footer } from './components/Footer';
import { LandingPage } from './pages/LandingPage';
import { AnalyzePage } from './pages/AnalyzePage';
import { ProcessingPage } from './pages/ProcessingPage';
import { ResultPage } from './pages/ResultPage';
import { DashboardPage } from './pages/DashboardPage';
import { HistoryPage } from './pages/HistoryPage';

export function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="min-h-screen flex flex-col justify-between bg-canvas text-ink font-sans">
          <div>
            <Header />
            <main>
              <Routes>
                <Route path="/" element={<LandingPage />} />
                <Route path="/analyze" element={<AnalyzePage />} />
                <Route path="/analyze/processing" element={<ProcessingPage />} />
                <Route path="/analyze/result" element={<ResultPage />} />
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/history" element={<HistoryPage />} />
                <Route path="*" element={<LandingPage />} />
              </Routes>
            </main>
          </div>
          <Footer />
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;
