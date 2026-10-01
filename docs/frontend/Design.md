---
version: alpha
name: HireShield-AI-design-system
description: "A forensic-grade opportunity verification platform for job seekers, students, and career switchers. The system reads as warm-but-serious — an editorial sage-green identity paired with a strict, non-negotiable red/amber/green verdict language borrowed from clinical and security tooling. A serif display face (Playfair Display) carries emotional weight and trust on marketing surfaces; a clean grotesque (Plus Jakarta Sans) carries every functional UI element, because the product's core job — telling someone 'don't apply, this is a scam' — has to read as calm and certain, never decorative. Pill buttons, softly rounded cards, and circular data visualizations (the risk gauge) are the primary UI motifs."

colors:
  primary: "#003e1c"
  primary-container: "#1e5631"
  primary-hover: "#18512c"
  on-primary: "#ffffff"
  on-primary-container: "#8fca9b"
  secondary: "#506354"
  secondary-container: "#d0e5d2"
  on-secondary: "#ffffff"
  on-secondary-container: "#546758"
  tertiary: "#003d28"
  tertiary-container: "#00573a"
  on-tertiary-container: "#40d399"
  ink: "#1c1b1b"
  ink-muted: "#414941"
  ink-subtle: "#717970"
  canvas: "#fcf9f8"
  surface-1: "#ffffff"
  surface-2: "#f6f3f2"
  surface-3: "#f0eded"
  surface-4: "#e5e2e1"
  border: "#c0c9be"
  border-strong: "#717970"
  inverse-canvas: "#313030"
  inverse-ink: "#f3f0ef"
  risk-low: "#1e5631"
  risk-low-bg: "#d0e5d2"
  risk-moderate: "#b45309"
  risk-moderate-bg: "#fef3c7"
  risk-high: "#ba1a1a"
  risk-high-bg: "#ffdad6"
  accent-recruiter: "#5521b5"
  accent-recruiter-bg: "#edebfe"
  accent-document: "#9d174d"
  accent-document-bg: "#fce7f3"
  accent-url: "#0369a1"
  accent-url-bg: "#e0f2fe"

typography:
  display-hero:
    fontFamily: Playfair Display
    fontSize: 56px
    fontWeight: 600
    lineHeight: 64px
    letterSpacing: -0.02em
  display-hero-mobile:
    fontFamily: Playfair Display
    fontSize: 36px
    fontWeight: 600
    lineHeight: 44px
    letterSpacing: -0.01em
  headline-xl:
    fontFamily: Playfair Display
    fontSize: 40px
    fontWeight: 600
    lineHeight: 48px
    letterSpacing: -0.015em
  headline-lg:
    fontFamily: Playfair Display
    fontSize: 30px
    fontWeight: 500
    lineHeight: 38px
    letterSpacing: 0
  headline-md:
    fontFamily: Playfair Display
    fontSize: 22px
    fontWeight: 600
    lineHeight: 30px
    letterSpacing: 0
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: 600
    lineHeight: 26px
    letterSpacing: 0
  body-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: 400
    lineHeight: 28px
    letterSpacing: 0
  body-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 15px
    fontWeight: 400
    lineHeight: 24px
    letterSpacing: 0
  body-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 13px
    fontWeight: 400
    lineHeight: 20px
    letterSpacing: 0
  label-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 13px
    fontWeight: 600
    lineHeight: 18px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 11px
    fontWeight: 600
    lineHeight: 16px
    letterSpacing: 0.04em
  caption-code:
    fontFamily: Plus Jakarta Sans
    fontSize: 12px
    fontWeight: 500
    lineHeight: 16px
    letterSpacing: 0
  mono:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: 400
    lineHeight: 20px
    letterSpacing: 0

rounded:
  sm: 8px
  md: 1rem
  lg: 2rem
  xl: 3rem
  pill: 9999px
  full: 9999px

spacing:
  space-2xs: 4px
  space-xs: 8px
  space-sm: 12px
  space-md: 16px
  space-lg: 24px
  space-xl: 32px
  space-2xl: 48px
  space-3xl: 72px
  gutter-mobile: 16px
  gutter-desktop: 32px
  container-max: 1200px

components:
  button-primary:
    backgroundColor: "{colors.primary-container}"
    textColor: "{colors.on-primary}"
    typography: "{typography.label-md}"
    rounded: "{rounded.pill}"
    padding: 12px 24px
  button-primary-hover:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
  button-secondary:
    backgroundColor: "{colors.surface-1}"
    textColor: "{colors.ink}"
    typography: "{typography.label-md}"
    rounded: "{rounded.pill}"
    padding: 12px 24px
  button-outline:
    backgroundColor: transparent
    textColor: "{colors.on-primary}"
    typography: "{typography.label-md}"
    rounded: "{rounded.pill}"
    padding: 12px 24px
  risk-badge-low:
    backgroundColor: "{colors.risk-low-bg}"
    textColor: "{colors.on-secondary-container}"
    typography: "{typography.label-sm}"
    rounded: "{rounded.pill}"
    padding: 4px 12px
  risk-badge-moderate:
    backgroundColor: "{colors.risk-moderate-bg}"
    textColor: "{colors.risk-moderate}"
    typography: "{typography.label-sm}"
    rounded: "{rounded.pill}"
    padding: 4px 12px
  risk-badge-high:
    backgroundColor: "{colors.risk-high-bg}"
    textColor: "{colors.risk-high}"
    typography: "{typography.label-sm}"
    rounded: "{rounded.pill}"
    padding: 4px 12px
  card-base:
    backgroundColor: "{colors.surface-1}"
    textColor: "{colors.ink}"
    typography: "{typography.body-md}"
    rounded: "{rounded.md}"
    padding: 24px
  floating-card:
    backgroundColor: "{colors.surface-1}"
    textColor: "{colors.ink}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.sm}"
    padding: 16px
  icon-badge:
    backgroundColor: "{colors.secondary-container}"
    textColor: "{colors.primary}"
    rounded: "{rounded.full}"
    padding: 0
  risk-score-gauge:
    backgroundColor: "{colors.surface-2}"
    rounded: "{rounded.full}"
    padding: 0
  filter-chip:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.ink-muted}"
    typography: "{typography.label-md}"
    rounded: "{rounded.pill}"
    padding: 6px 16px
  filter-chip-active:
    backgroundColor: "{colors.primary-container}"
    textColor: "{colors.on-primary}"
  numbered-step:
    backgroundColor: "{colors.surface-3}"
    textColor: "{colors.primary}"
    typography: "{typography.display-hero}"
    rounded: "{rounded.full}"
    padding: 0
  text-input:
    backgroundColor: "{colors.surface-1}"
    textColor: "{colors.ink}"
    typography: "{typography.body-md}"
    rounded: "{rounded.pill}"
    padding: 12px 20px
---

# HireShield-AI Design System

## Mission
Create implementation-ready, token-driven UI guidance for HireShield-AI — an AI-powered job and internship scam verification platform — optimized for trust, clarity, and fast risk comprehension across a React + Tailwind product, so that a person deciding whether to trust a job offer never has to guess what the interface is telling them.

## Brand
- Product/brand: HireShield-AI
- Audience: students, freshers, job seekers, and career switchers evaluating job/internship offers
- Product surface: public marketing site + authenticated analysis dashboard (light-mode primary)
- Core job: turn a submitted opportunity into an instantly legible risk verdict — APPLY / HOLD / DON'T APPLY
- Brand alignment: sage-green primary evokes safety and growth (career, protection) without borrowing "corporate security" cliches like navy/black; the serif display face signals editorial trustworthiness rather than cold automation

## Overview
HireShield-AI is not a job board — it's a verification instrument. The system is built around one moment: a person pastes in an offer and needs to know, without ambiguity, whether it's safe. A warm, editorial marketing shell (serif headlines, soft mint gradients, floating result cards) builds initial trust and explains the product; the analysis/report experience then shifts weight onto a strict, high-contrast **three-state risk language — low / moderate / high** — expressed through a dedicated color trio that must never be confused with brand color. The serif face is reserved for marketing and section headlines; every functional UI element — buttons, labels, scores, evidence — uses Plus Jakarta Sans, because clarity under stress matters more than personality once someone is looking at their own risk report.

## Colors
- **Primary (#003e1c) / Primary Container (#1e5631):** Primary actions — "Check Now," "Get Started," "Analyze an Opportunity," active nav state.
- **Secondary (#506354) / Secondary Container (#d0e5d2):** Supporting UI — tag pills, "How It Works" icon backgrounds, secondary badges (e.g. "Verified Safe" trust badge, which is a *brand* affirmation, not a risk-state color).
- **Tertiary (#003d28) / Tertiary Container (#00573a):** Reserved for subtle decorative accents (ambient glows, gradient stops) — not used for text or interactive elements.
- **Ink (#1c1b1b) / Ink Muted (#414941) / Ink Subtle (#717970):** Three-step text hierarchy for headings, body, and metadata/timestamps.
- **Canvas (#fcf9f8):** App and marketing background — warm off-white, not stark white.
- **Surface 1 (#ffffff):** Cards, floating result cards, modals — sits lifted off canvas.
- **Surface 2/3/4:** Nested panels, evidence sub-panels, hover states, category tiles.
- **Risk Low (#1e5631) / bg (#d0e5d2):** APPLY verdict, "verified safe," clean/passed verification items. Deliberately reuses brand green — a low-risk result should feel like the product's default, trusted state.
- **Risk Moderate (#b45309) / bg (#fef3c7):** HOLD verdict, caution flags, compensation/language anomalies.
- **Risk High (#ba1a1a) / bg (#ffdad6):** DON'T APPLY verdict, critical fraud indicators, failed verification checks.
- **Category accents (recruiter purple, document pink, URL blue, financial amber):** Used only as icon-badge backgrounds on "What We Check" category cards — never as text color, button color, or a status indicator, to avoid competing with the risk-state language.

Risk colors must **never** be reused for generic UI feedback (no green "form saved!" toast reusing risk-low green) — they are reserved so that any green, amber, or red on screen unambiguously means a verification verdict. Category accent colors (purple/pink/blue) must never be used to represent risk severity, and risk colors must never be used to badge a category — this keeps "what kind of check is this?" and "how risky is this?" visually distinct at a glance.

## Typography
Two-family pairing, used with strict separation of duty:
- **Playfair Display** — marketing/editorial voice only: hero headlines, section headlines (`headline-xl/lg/md`), the big score number on the risk gauge, numbered step digits (01/02/03). Tops out at 600 weight — confident, not ornate.
- **Plus Jakarta Sans** — everything functional: nav, body copy, buttons, labels, badges, evidence text, table/list content, captions, code-style values (domains, IDs). This is the "believe me" typeface — clean and fast to scan under stress.
- **JetBrains Mono** (reserved, not yet in active use) — for verbatim technical evidence: email domains, DNS records, filing IDs — anywhere exactness matters more than tone. Currently rendered via monospace `<code>` tags in Plus Jakarta Sans contexts; promote to a true mono face when evidence panels get a dedicated redesign pass.

## Layout & Spacing
- **Base unit:** 4px, scaling `space-2xs(4) → space-xs(8) → space-sm(12) → space-md(16) → space-lg(24) → space-xl(32) → space-2xl(48) → space-3xl(72)`.
- Card interior padding: `space-lg`–`space-xl` (24–32px) for marketing cards; `space-md`–`space-lg` for dense report cards (risk factor list, verification matrix).
- Max content width: `container-max` (1200px) for both marketing and dashboard views.
- Marketing grid: 12-column, hero splits 7/5 (content/visual); category and step sections use 3-up desktop → 2-up tablet → 1-up mobile card grids.
- Report grid: 12-column hero score card splits 5/7 (gauge/summary); risk factor list and verification matrix run 1-up and 3-up respectively.

## Elevation & Depth
| Level | Treatment | Use |
|---|---|---|
| 0 (flat) | `{colors.canvas}`, no border | Page background, ambient ombré sections |
| 1 (card lift) | `{colors.surface-1}`, soft shadow (`0 4px 20px -2px rgba(30,86,49,0.04)`) | Standard cards, category tiles, testimonial cards |
| 2 (floating/overlap) | `{colors.surface-1}` at 95% opacity + backdrop blur, stronger shadow | Floating result cards overlapping hero imagery, score hero card |
| 3 (hover) | Shadow deepens (`0 12px 32px -4px rgba(26,26,26,0.06–0.08)`), slight `-translate-y` | Card hover states across marketing and report surfaces |
| 4 (focus ring) | 2px `{colors.primary-container}` ring at reduced opacity | Focused search/URL input, focused button |

Depth leans on soft ambient shadows and blurred color glows rather than hard borders — keeps the system feeling warm and editorial rather than clinical, while the risk-color system supplies all the "seriousness" the product needs.

## Shapes
| Token | Value | Use |
|---|---|---|
| `{rounded.sm}` | 8px | Floating result cards, evidence sub-panels |
| `{rounded.md}` | 1rem (16px) | Standard cards, category tiles, step cards, testimonial cards |
| `{rounded.lg}` | 2rem (32px) | Hero image container, CTA banner, primary score hero card |
| `{rounded.xl}` | 3rem (48px) | Large decorative containers (rare; use sparingly) |
| `{rounded.pill}` | 9999px | Buttons, badges, filter chips, tag pills, search/URL input bar |
| `{rounded.full}` | 9999px | Avatars, icon badges, numbered-step circles, risk gauge |

## Components

### Buttons
- **`button-primary`** — Green pill CTA for core actions ("Check Now," "Get Started," "Analyze an Opportunity"). Padding 12px 24px, fully rounded.
- **`button-secondary`** — White/neutral pill for secondary actions ("Re-run Scan," "Download PDF").
- **`button-outline`** — Transparent/translucent pill on dark surfaces (CTA banner "Explore Sample Report").
- No `button-danger` yet — destructive/report actions ("Report to Community Database") currently borrow `risk-high` directly rather than a dedicated danger token; formalize this if more destructive actions are added.

### Risk Badges
Three pill badges (`risk-badge-low/moderate/high`) are the single most important repeated component in the product — they must appear with identical shape and consistent placement (top-right of a card, or beside a score) across every surface: hero floating cards, risk factor list, verification matrix, history list. Severity must always read at a glance; never soften a high-risk badge's visual weight relative to a low-risk one.

### Risk Score Gauge
`risk-score-gauge` — the circular 0–100 SVG gauge at the center of the analysis report. Arc color must map directly to the risk band (`risk-low`/`risk-moderate`/`risk-high`), never to brand color regardless of context. The center label pairs a large `display-hero`-style number with a small `label-sm` "Risk Score" caption underneath.

### Risk Factor Card
The primary content unit of the analysis report's breakdown section. Structure: colored severity icon badge (left), category label (`caption-code`, uppercase), headline (`headline-sm`), description (`body-md`), an optional evidence sub-panel (`surface-2` background, `caption-code` key/value pairs), and a severity score chip (top-right, risk-colored).

### Verification Matrix Item
A compact card used in 3-up grids to show pass/fail/caution outcomes for a single verification check (domain, recruiter, registration, etc.). Structure: icon badge + Pass/Fail/Caution status chip (top row), check name (`headline-sm`), one-line explanation (`body-sm`), and a muted evidence footer (`surface-2` background).

### Floating Result Card
`floating-card` — used to overlap hero imagery with a compact preview of a real analysis outcome (mini risk badge + job title + verdict). Always paired with backdrop blur and elevated shadow so it reads as "floating" above the photo beneath it.

### Icon Badge / Category Tile
`icon-badge` — colored circle or rounded-square containing a Material Symbol, used for both "What We Check" categories (rotating accent colors) and step/process icons (brand green). Category accent colors are decorative only, never load-bearing for meaning.

### Numbered Step
`numbered-step` — large serif digit (01/02/03) paired with an icon badge, headline, and description. Used for "How It Works" and the analysis pipeline explainer. On hover, the digit and icon badge shift into brand-primary color.

### Filter Chip
`filter-chip` / `filter-chip-active` — pill-shaped toggle used to filter the risk factor list by severity (All / Critical / Moderate / Safe). Active state fills with `primary-container`; inactive chips sit on `surface-2` with muted text.

### Search / URL Input
`text-input` — the primary hero input for pasting a job URL, email, or domain. Fully pill-shaped, sits inside a floating "form" container with its own elevated shadow, with the submit button embedded at the trailing edge.

## Do's and Don'ts

### Do
- Reserve `risk-low` / `risk-moderate` / `risk-high` exclusively for verification severity — never repurpose them for generic UI feedback (form validation, success toasts, etc.).
- Keep the canvas warm and quiet; let the risk-color trio and the serif headlines be the only elements competing for attention on any given screen.
- Use `{rounded.pill}` consistently for every badge, chip, and button — no mixed-radius buttons anywhere in the system.
- Lead every report view with the risk score and verdict before any narrative explanation — the number and color come first, the story comes second.
- Reserve Playfair Display for headlines and the gauge's big number only; never set body copy, labels, or evidence text in it.
- Use category accent colors (purple/pink/blue/orange) deliberately and only for "what kind of check" icon badges — never let them imply severity.

### Don't
- Don't introduce a fourth risk state without updating this file first — the product's entire trust model depends on a fixed, well-understood three-state language.
- Don't use `risk-high` red or `risk-low` green as decorative or brand color anywhere outside an actual verification context.
- Don't let a moderate/high-risk factor card look visually softer or smaller than a low-risk one — severity must be legible from card size and color alone, not just badge text.
- Don't add unexplained statistics or confidence numbers to marketing/report copy — every stated metric should be real or clearly a placeholder pending backend data (see project safety principle: risk results are guidance, not guarantees).
- Don't mix serif and sans within the same UI element (e.g. a serif label inside a sans-only badge).
- Don't ship a dark theme as default; if added later, treat it as a secondary theme, not the brand identity.

## Responsive Behavior

### Breakpoints
| Name | Width | Key Changes |
|---|---|---|
| Desktop | 1280px | Full 12-col grid; hero 7/5 split; 3-up category/step cards |
| Tablet | 1024px | Hero stacks to single column below content; 2-up card grids |
| Mobile-Lg | 768px | Nav collapses to a menu/drawer (currently missing in the Stitch export — must be added); verification matrix and risk factor cards go single-column |
| Mobile | 480px | Floating hero result cards stack below the image instead of overlapping it; risk score gauge shrinks and centers full-width |

### Touch Targets
- Primary/secondary/outline buttons: ≥44px tap height on touch viewports.
- Filter chips: ≥40px tap height, adequate horizontal spacing to prevent mis-taps in the scrollable filter row.
- Risk badges are informational only — not tap targets, no minimum required.

### Collapsing Strategy
- **Floating hero cards** → drop the absolute-positioned overlap below `lg`; stack as normal flow cards beneath the hero image.
- **Verification matrix** → 3-up → 2-up → 1-up grid as viewport narrows.
- **Filter pill row** → horizontal scroll container on narrow viewports rather than wrapping, to preserve the pill shape and single-row rhythm.
- **Nav** → requires a drawer/hamburger pattern below `xl`; not yet implemented in current markup.

## Iteration Guide
1. Every new screen starts by asking: does this surface need to communicate a risk verdict? If yes, the risk-color trio and badge/gauge components take visual priority over everything else.
2. Reference components by their `components:` token name, not raw hex/px values.
3. Default headline copy to Playfair Display, default everything else to Plus Jakarta Sans — no exceptions without updating this file.
4. Risk states are locked at three (low/moderate/high) mapped to APPLY/HOLD/DON'T APPLY — do not add a fourth without revising this document and every existing badge/gauge instance.
5. Use category accent colors only for icon badges on "what we check" style content — if in doubt, default to secondary-container.
6. Add new card/table variants as separate component entries rather than one-off overrides.
7. Re-check contrast (WCAG 2.2 AA) any time a risk or accent color pairs with a new background surface, especially the amber `risk-moderate` pairing which trends light.

## Known Gaps
- Mobile navigation pattern (hamburger/drawer) is not yet designed — current markup only defines the desktop nav.
- The risk score gauge is currently a static SVG mockup; the arc's `stroke-dashoffset` must be computed dynamically from the real score once wired to data.
- `risk-moderate` and a couple of category accent colors are still expressed as raw Tailwind defaults (`amber-500`, etc.) rather than tokens in this system — should be formalized as first-class tokens in the Tailwind config.
- No dark theme is defined; treat as a future secondary theme, not a v1 requirement.
- Loading/in-progress states (the "✓ Extracting → ✓ Verifying → ✓ Scoring" pipeline animation) are not yet specified as a dedicated component.
- JetBrains Mono is specified for evidence values but not yet wired up in the actual markup (currently monospace via Tailwind's default `font-mono` on Plus Jakarta Sans contexts).