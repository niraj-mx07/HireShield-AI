# HireShield-AI Frontend Plan

## HireShield-AI — Frontend Structure & Flow

**Frontend Stack:** React 18 · Tailwind CSS · shadcn/ui · Recharts

*(Assumption — swap in Next.js 15 if you want file-based routing/middleware auth guards like TrackWise; adjust Section 4 accordingly if so.)*

---

## 1. Page List (by access level)

### Public

| Page | Route | Contents |
|---|---|---|
| Landing | `/` | Hero + "Know Before You Apply" pitch, URL/opportunity input bar, "How It Works," "What We Check" category grid, testimonials, CTA banner |
| Login | `/login` | Single login form, redirects to Dashboard after auth |
| Sign Up | `/signup` | Account creation — name, email, password (saves history going forward) |
| Forgot Password | `/forgot-password` | User enters registered email → receives reset link → sets new password |

### Guest (no account required)

| Page | Route | Contents |
|---|---|---|
| Quick Analyze | `/analyze` | Multi-tab submission form (URL / Job Description / Document / Recruiter Details / Email-Message) — usable without login |
| Analysis Progress | `/analyze/processing` | Step checklist animation ("✓ Extracting → ✓ Verifying → ✓ Scoring") while the pipeline runs |
| Result (unsaved) | `/analyze/result` | Full risk report for a guest session — score gauge, verdict, risk factor breakdown, verification matrix. Prompts "Sign up to save this report" |

### Authenticated (Job Seeker — single role)

| Page | Route | Contents |
|---|---|---|
| Dashboard | `/dashboard` | Recent checks summary, quick stats (total analyzed, high-risk caught), shortcut to "Analyze New Opportunity" |
| History ("My Checks") | `/history` | List of all past analyses — title, company, risk score, recommendation, date |
| Report Detail | `/history/[analysisId]` | Full saved risk report — same layout as guest result page, plus "Re-run Scan" and "Share with Advisor" actions |
| Settings | `/settings` | Profile info, password change, notification preferences |

Total: ~11 pages

---

## 2. Shared Components

| Component | Used For |
|---|---|
| Header / Nav | Logo, nav links, "Get Started"/account menu, mobile drawer |
| InputTabs | The 5-tab submission selector (URL / Description / Document / Recruiter / Email) on the Analyze page |
| ProgressChecklist | Animated step-by-step loader shown while a submission is being analyzed |
| RiskScoreGauge | Circular 0–100 SVG gauge, color-coded by risk band, used on every result view |
| RiskBadge | Small pill — APPLY / HOLD / DON'T APPLY — used on gauge, history list, floating cards |
| RiskFactorCard | One flagged issue: severity icon, category, description, evidence sub-panel, severity score chip |
| VerificationMatrixItem | Pass/Fail/Caution tile for a single verification check (domain, recruiter, registration, etc.) |
| FilterChip | Pill toggle for filtering the risk factor list (All / Critical / Moderate / Safe) |
| HistoryListItem | One row in the "My Checks" list — title, company, score, recommendation, date |
| ChartWrapper | Reused Recharts component — for a future "risk trend over time" or "checks per month" chart on the Dashboard |
| StatCard | Small metric box on the Dashboard (e.g. total checks, high-risk caught) |

---

## 3. App Flow

**Guest:** Lands on Landing page → pastes a job URL or pastes details into `/analyze` → sees the Analysis Progress checklist → views the full Result report → is prompted to sign up to save the report and unlock History.

**New user:** Signs up on `/signup` → lands on Dashboard (empty state, "Analyze your first opportunity") → runs an analysis → report auto-saves to History → can revisit it anytime from `/history`.

**Returning user:** Logs in → Dashboard shows recent checks and quick stats → either starts a new analysis or opens a past report from History → can re-run a stale analysis from the Report Detail page.

---

## 4. Access Control

There is currently only **one authenticated role** (Job Seeker) — no mentor/reviewer/admin roles exist yet in the product spec, so this is simpler than a multi-role RBAC system, but a few boundaries still matter:

- `/analyze` and its result view are accessible **without login** (guest mode) — this matches the project's "100% Free for job seekers" positioning and keeps the friction low for a first-time check.
- `/dashboard`, `/history`, `/history/[analysisId]`, and `/settings` require authentication — a guest hitting these routes should be redirected to `/login`.
- A guest's analysis result is **not persisted** to their account until they sign up immediately after — the frontend should hold the just-completed result in memory/local session and offer to attach it to the new account on signup, rather than losing it.
- Role check (guest vs. authenticated) should happen via Next.js middleware or a layout-level guard if you move to Next.js, or a route-guard wrapper component if staying on React Router — checking session state from Supabase/your auth provider before rendering protected pages.

**Future scope (not v1):** if a Moderator/Admin role is added later (e.g. to review community-reported scams — see the project's "Future Scope" section), it would need its own route group (`/admin/*`) and its own guard, following the same pattern as the job-seeker guard above.

---

## 5. Guest-to-Account Handoff

Because HireShield-AI's core value ("check before you apply") should work with zero friction, the guest flow is treated as a first-class path rather than a stripped-down demo:

- A guest can run a full analysis and see the complete report with no account.
- Directly after viewing a guest result, the report page shows a persistent but non-blocking prompt: "Create a free account to save this report and track future checks."
- If the guest signs up within the same session, the in-memory result is attached to their new account and immediately appears in `/history` — avoiding the frustrating pattern of a user redoing a check they already ran.
- If they leave without signing up, the result is discarded — HireShield-AI does not currently persist anonymous analyses server-side (keeps scope aligned with the project's "ephemeral storage" privacy principle carried over from the design system's trust-first posture).

Note: this guest-first approach trades off some backend complexity (holding a result in session state, attaching it post-signup) for a much lower barrier to the product's core safety check — worth confirming this is the right call for your timeline before building it, versus simply requiring signup before any analysis runs.