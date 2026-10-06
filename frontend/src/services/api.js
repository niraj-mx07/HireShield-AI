/**
 * HireShield-AI API Client
 *
 * Communicates with the FastAPI backend assessment endpoints.
 * Automatically adapts to VITE_API_BASE_URL for production deployment (Render, Vercel, Railway).
 */

const API_BASE_URL = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE_URL) || 'http://127.0.0.1:8000';

/**
 * Submit an assessment request with JSON body.
 */
export async function submitAssessment(payload) {
  const url = `${API_BASE_URL}/api/v1/assessments`;
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      url: payload.url || undefined,
      description: payload.description || undefined,
      company_name: payload.company_name || undefined,
      recruiter_email: payload.recruiter_email || undefined,
      recruiter_name: payload.recruiter_name || undefined,
      recruiter_phone: payload.recruiter_phone || undefined,
      message: payload.message || undefined,
      user_id: payload.user_id || undefined,
      user_email: payload.user_email || undefined,
      consent_for_external_lookups: true,
    }),
  });

  if (!response.ok) {
    const errText = await response.text();
    throw new Error(`API Error ${response.status}: ${errText}`);
  }

  return response.json();
}

/**
 * Submit an assessment with an uploaded document (PDF/text).
 */
export async function submitAssessmentWithUpload(formData) {
  const url = `${API_BASE_URL}/api/v1/assessments/upload`;
  const response = await fetch(url, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errText = await response.text();
    throw new Error(`API Error ${response.status}: ${errText}`);
  }

  return response.json();
}

/**
 * MongoDB Auth & User Profile API calls
 */
export async function apiSignup(userData) {
  const url = `${API_BASE_URL}/api/v1/auth/signup`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(userData),
  });

  if (!response.ok) {
    const errText = await response.text();
    throw new Error(`Signup Error ${response.status}: ${errText}`);
  }

  return response.json();
}

export async function apiLogin(credentials) {
  const url = `${API_BASE_URL}/api/v1/auth/login`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(credentials),
  });

  if (!response.ok) {
    const errText = await response.text();
    throw new Error(`Login Error ${response.status}: ${errText}`);
  }

  return response.json();
}

export async function apiGetUser(userEmailOrId) {
  const url = `${API_BASE_URL}/api/v1/auth/user/${encodeURIComponent(userEmailOrId)}`;
  const response = await fetch(url);
  if (!response.ok) {
    const errText = await response.text();
    throw new Error(`User Fetch Error ${response.status}: ${errText}`);
  }
  return response.json();
}

/**
 * MongoDB User History API calls
 */
export async function apiGetUserHistory(userEmailOrId) {
  const url = `${API_BASE_URL}/api/v1/users/${encodeURIComponent(userEmailOrId)}/history`;
  const response = await fetch(url);
  if (!response.ok) {
    const errText = await response.text();
    throw new Error(`History Fetch Error ${response.status}: ${errText}`);
  }
  return response.json();
}

export async function apiSaveUserHistory(userEmailOrId, items) {
  const url = `${API_BASE_URL}/api/v1/users/${encodeURIComponent(userEmailOrId)}/history`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(Array.isArray(items) ? items : [items]),
  });

  if (!response.ok) {
    const errText = await response.text();
    throw new Error(`History Save Error ${response.status}: ${errText}`);
  }

  return response.json();
}

export async function apiDeleteHistoryItem(userEmailOrId, itemId) {
  const url = `${API_BASE_URL}/api/v1/users/${encodeURIComponent(userEmailOrId)}/history/${encodeURIComponent(itemId)}`;
  const response = await fetch(url, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const errText = await response.text();
    throw new Error(`History Delete Error ${response.status}: ${errText}`);
  }

  return response.json();
}

export async function apiClearUserHistory(userEmailOrId) {
  const url = `${API_BASE_URL}/api/v1/users/${encodeURIComponent(userEmailOrId)}/history`;
  const response = await fetch(url, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const errText = await response.text();
    throw new Error(`History Clear Error ${response.status}: ${errText}`);
  }

  return response.json();
}

/**
 * Transform a backend AssessmentResponse into the frontend report format.
 */
export function formatBackendResponse(apiData, userInputs = {}) {
  const verdictMap = {
    APPLY: 'APPLY',
    HOLD: 'HOLD',
    "DON'T APPLY": "DON'T APPLY",
    DONT_APPLY: "DON'T APPLY",
  };

  const riskBand = (apiData.risk_band || 'low').toLowerCase();
  const verdict = verdictMap[apiData.recommendation] || (riskBand === 'high' || riskBand === 'very_high' ? "DON'T APPLY" : riskBand === 'moderate' ? 'HOLD' : 'APPLY');

  const riskFactors = (apiData.risk_factors || []).map((rf, idx) => ({
    id: `rf-live-${idx + 1}`,
    severity: rf.severity || 'low',
    severityScore: Math.round((rf.confidence || 0.8) * 100),
    category: rf.category ? rf.category.replace('_', ' ').toUpperCase() : 'General',
    headline: rf.description || 'Risk Indicator Detected',
    evidence: rf.evidence || '',
    categoryType: rf.category === 'url_website' ? 'accent-url' : rf.category === 'recruiter_verification' ? 'accent-recruiter' : 'accent-document',
  }));

  const matrix = (apiData.category_scores || []).map((cs) => {
    const isAnalyzed = cs.analyzed;
    const catScore = cs.score || 0;
    let status = 'PASS';
    if (!isAnalyzed) {
      status = 'CAUTION';
    } else if (catScore >= 60) {
      status = 'FAIL';
    } else if (catScore >= 30) {
      status = 'CAUTION';
    }

    const nameFormatted = cs.category
      .split('_')
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');

    return {
      checkName: `${nameFormatted} Check`,
      status,
      explanation: isAnalyzed
        ? `Score: ${catScore.toFixed(1)}/100 (Effective Weight: ${(cs.weight * 100).toFixed(1)}%)`
        : 'Not provided or unanalyzed in this scan',
      evidenceFooter: cs.risk_factors && cs.risk_factors.length > 0 ? cs.risk_factors[0].evidence : 'Standard parameters verified',
    };
  });

  const formattedScore = Math.round(Number(apiData.risk_score) || 0);
  const resolvedTitle = userInputs.title || userInputs.company_name ? `${userInputs.title || 'Opportunity Assessment'} — ${userInputs.company_name || 'Hiring Entity'}` : 'Opportunity Assessment';

  return {
    id: `HS-${(apiData.id || '').slice(0, 8).toUpperCase()}`,
      jobTitle: resolvedTitle,
      title: resolvedTitle,
      company: userInputs.company_name || 'Hiring Organization',
      url: userInputs.url || '',
      recruiterEmail: userInputs.recruiter_email || '',
      recruiterName: userInputs.recruiter_name || '',
      scanDate: new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) + ' • ' + new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
      date: new Date().toISOString().split('T')[0],
      score: formattedScore,
      riskScore: formattedScore,
      verdict,
      recommendation: verdict,
      riskLevel: riskBand === 'very_high' || riskBand === 'high' ? 'high' : riskBand === 'moderate' ? 'moderate' : 'low',
      confidence: `${Math.round((apiData.confidence || 0.85) * 100)}%`,
      summary:
        apiData.risk_score >= 60
          ? `High-risk indicators identified. The opportunity received a risk score of ${formattedScore}/100. Critical signals include ${riskFactors.map((r) => r.headline).slice(0, 2).join(' and ')}.`
          : apiData.risk_score >= 30
          ? `Moderate risk detected (${formattedScore}/100). Exercise caution before sharing sensitive documents or signing agreements.`
          : `Verified low-risk opportunity (${formattedScore}/100). All analyzed parameters align with verified employment standards.`,
      riskFactors,
      matrix,
    };
}
