/**
 * HireShield-AI API Client
 *
 * Communicates with the FastAPI backend assessment endpoints.
 * Automatically adapts to VITE_API_BASE_URL for production deployment (Render, Vercel, Railway).
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

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
      chat_transcript: payload.chat_transcript || undefined,
      message_log: payload.message_log || undefined,
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
    const factors = cs.risk_factors || [];
    const hasHigh = factors.some((f) => f.severity === 'high');
    const hasMedium = factors.some((f) => f.severity === 'medium');

    // Severity outranks the raw score so a section carrying a high-severity
    // indicator can never render as PASS/CAUTION (single-section contradiction).
    let status = 'PASS';
    if (!isAnalyzed) {
      status = 'CAUTION';
    } else if (hasHigh || catScore >= 60) {
      status = 'FAIL';
    } else if (hasMedium || catScore >= 30) {
      status = 'CAUTION';
    }

    const nameFormatted = cs.category
      .split('_')
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');

    // The evidence footer must agree with the rendered status: a FAIL row
    // never quotes a "verified" line, and a PASS row never quotes an alarm.
    let footerFactor;
    if (status === 'FAIL') {
      footerFactor = factors.find((f) => f.severity === 'high') || factors[0];
    } else if (status === 'CAUTION') {
      footerFactor =
        factors.find((f) => f.severity === 'medium') ||
        factors.find((f) => f.severity !== 'high') ||
        factors[0];
    } else {
      footerFactor = factors.find((f) => f.severity === 'low') || factors[0];
    }

    return {
      checkName: `${nameFormatted} Check`,
      status,
      explanation: isAnalyzed
        ? `Score: ${catScore.toFixed(1)}/100 (Effective Weight: ${(cs.weight * 100).toFixed(1)}%)`
        : 'Not provided or unanalyzed in this scan',
      evidenceFooter: footerFactor ? footerFactor.evidence : 'Standard parameters verified',
    };
  });

  return {
    id: `HS-${(apiData.id || '').slice(0, 8).toUpperCase()}`,
    jobTitle: userInputs.title || userInputs.company_name ? `${userInputs.title || 'Opportunity Assessment'} — ${userInputs.company_name || 'Hiring Entity'}` : 'Opportunity Assessment',
    company: userInputs.company_name || 'Hiring Organization',
    url: userInputs.url || '',
    recruiterEmail: userInputs.recruiter_email || '',
    recruiterName: userInputs.recruiter_name || '',
    scanDate: new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) + ' • ' + new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
    score: Math.round(apiData.risk_score || 0),
    verdict,
    riskLevel: riskBand === 'very_high' || riskBand === 'high' ? 'high' : riskBand === 'moderate' ? 'moderate' : 'low',
    confidence: `${Math.round((apiData.confidence || 0.85) * 100)}%`,
    summary:
      apiData.risk_score >= 60
        ? `High-risk indicators identified. The opportunity received a risk score of ${apiData.risk_score}/100. Critical signals include ${riskFactors.map((r) => r.headline).slice(0, 2).join(' and ')}.`
        : apiData.risk_score >= 30
        ? `Moderate risk detected (${apiData.risk_score}/100). Exercise caution before sharing sensitive documents or signing agreements.`
        : `Verified low-risk opportunity (${apiData.risk_score}/100). All analyzed parameters align with verified employment standards.`,
    riskFactors,
    matrix,
  };
}
