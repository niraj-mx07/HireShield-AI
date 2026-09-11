# HireShield-AI Component Specification

## Design foundations

Use `font-display` only for large, editorial-style statements. All navigation, labels, controls, body copy, tables, and risk evidence use `font-sans`. Load the font families once in the app stylesheet:

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');
```

The shared visual grammar is: white `rounded-card` surfaces, `border-neutral-border`, `shadow-card`, and full-radius controls. Interactive controls have a visible keyboard focus ring (`focus-visible:ring-2 focus-visible:ring-brand-primary/35`) and honor reduced-motion preferences. Do not rely on color alone for risk status: pair it with a label, icon, and/or text.

## Button

**Purpose.** Primary interaction control for submissions, navigation, and report actions. All buttons are pill-shaped (`rounded-full`).

| Variant | Base treatment | Use |
| --- | --- | --- |
| `primary` | `bg-brand-primary text-white` | Submit opportunity, start analysis, primary confirmation |
| `secondary` | `bg-brand-forest text-white` | Secondary high-emphasis actions |
| `outline` | White surface, `border-neutral-border`, `text-brand-primary` | Cancel, back, low-emphasis actions |

**States.** Default; hover (slightly darker/raised); active (reduced shadow); disabled (50% opacity, no pointer events); loading (spinner, stable button width, `aria-busy=true`).

**Props.** `variant`, `size` (`sm`, `md`, `lg`), `type`, `disabled`, `loading`, `leadingIcon`, `trailingIcon`, `children`, `onClick`.

**Screens.** Landing, opportunity input, analysis progress, results, saved assessments.

## Card

**Purpose.** Base content container for forms, summaries, evidence, and dashboard sections.

**Variants/states.** `default` (white, border, `shadow-card`); `interactive` (hover uses `shadow-card-hover`); `selected` (brand-primary border/ring); `muted` (neutral-soft background). Static cards have no hover treatment.

**Props.** `as`, `padding` (`sm`, `md`, `lg`), `interactive`, `selected`, `children`, `className`, `onClick`.

**Screens.** All screens; especially input methods, analysis summary, evidence, and history.

## IconBadge

**Purpose.** Compact colored icon container for selecting or labeling an analysis input method. Use a centered SVG icon with an accessible label supplied by adjacent text or `aria-label`.

**Variants/states.** `circle` and `square` (rounded square); accent color `pink`, `purple`, `teal`, `orange`, or `blue`; default, hover, selected, disabled. Selected adds a brand-primary ring rather than changing the accent color.

**Props.** `icon`, `label`, `color`, `shape`, `size` (`sm`, `md`, `lg`), `selected`, `disabled`.

**Input mapping.** URL → blue; Job Description → purple; Document → pink; Recruiter Details → teal; Email/Message → orange.

**Screens.** Landing, new assessment, input-method selection, onboarding.

## RiskBadge

**Purpose.** Display an assessment risk score and its recommended action. This is a semantic status component, not a generic tag.

| Score | Token | Label | Recommendation |
| --- | --- | --- | --- |
| 0–30 | `risk.low` | Low risk | APPLY |
| 31–60 | `risk.moderate` | Moderate risk | HOLD |
| 61–80 | `risk.moderate` | High risk | HOLD |
| 81–100 | `risk.high` | Very high risk | DON'T APPLY |

**Variants/states.** `compact` for lists; `summary` for report headers; `hero` for the main score card. A score that is unavailable renders `Verification incomplete` in neutral styling. Hover is not required; status is non-interactive unless wrapped in a link.

**Props.** `score` (integer 0–100 or `null`), `riskBand`, `recommendation`, `size`, `confidence`, `showConfidence`.

**Screens.** Analysis complete, result detail, saved assessments, dashboard history.

## RiskFactorCard

**Purpose.** Explain one risk factor in the result breakdown with its severity, category, narrative, and supporting evidence.

**Variants/states.** `high` (red severity icon), `medium` (orange severity icon), `low` (green severity icon), and `unverified` (neutral warning icon). Default is expanded; collapsible mode exposes a focused/expanded state. Evidence unavailable must say `Unable to verify`, never imply a negative finding.

**Props.** `severity`, `category`, `description`, `evidence`, `source`, `verified`, `confidence`, `expanded`, `onToggle`.

**Screens.** Result detail, downloadable/shared report.

## FilterChip

**Purpose.** Toggle a category, source, date, or risk-band filter. Chips are pill-shaped and should be used in a grouped filter control, not as primary navigation.

**Variants/states.** Inactive uses white/outline; active uses `bg-brand-primary text-white`; hover; keyboard focus; disabled. When multi-select is supported, expose `aria-pressed`; use radio semantics for one-of-many selection.

**Props.** `label`, `active`, `disabled`, `count`, `icon`, `onChange`.

**Screens.** Saved assessments, evidence filters, dataset/rule views.

## AvatarStack

**Purpose.** Present compact social proof or collaborator attribution through overlapping circular avatars. It is decorative unless identities are actionable.

**Variants/states.** Sizes `sm`, `md`; maximum visible count; overflow badge (`+N`). Avatars use a white 2px border to separate overlaps. No interactive states unless avatars link to profiles.

**Props.** `avatars` (`name`, `imageUrl`, `initials`), `max`, `size`, `ariaLabel`.

**Screens.** Landing trust section, team/collaboration areas, shared reports.

## NumberedStep

**Purpose.** Explain a short ordered process using a two-digit circular badge (`01`, `02`, `03`), title, and description.

**Variants/states.** Default; `active` (brand-primary emphasis); `complete` (check icon); `upcoming` (muted). Static in explanatory content; active/complete apply when used for progress.

**Props.** `number`, `title`, `description`, `status`, `icon`.

**Screens.** Landing “How it works,” onboarding, analysis pipeline explainer.

## FloatingCard

**Purpose.** Elevated Card positioned over a hero image or visual section. Use it to surface the key Risk Score result where it remains readable independent of the background.

**Variants/states.** `result` (contains `RiskBadge` and key recommendation); `insight` (short fact/evidence); `metric` (small statistic). Uses `shadow-float`, a white surface, and a stable placement that does not obscure essential responsive content. Non-interactive by default.

**Props.** `variant`, `position` (`start`, `end`, `center`), `children`, `className`.

**Screens.** Landing hero, result detail evidence section.

## ProgressChecklist

**Purpose.** Show asynchronous assessment progress while preserving transparency about which analysis stages have completed, are running, or could not run.

**Default steps.** Extracting information; Analyzing job content; Checking company; Verifying recruiter; Inspecting URL/website; Reviewing documents; Calculating risk score.

**Variants/states.** Each row is `pending`, `running`, `complete`, `warning`, or `failed`. Complete uses a green check; running uses an animated but accessible spinner; warning uses amber and explains skipped/unavailable verification; failed uses red plus a retry path if supported. Announce status changes through a polite live region.

**Props.** `steps` (`id`, `label`, `status`, `detail`), `currentStep`, `onRetry`, `compact`.

**Screens.** Analysis progress, result detail when a verification check is incomplete.

## Responsive behavior

- Use a single-column form and stacked cards below `md`; move result summaries and evidence into two columns at `lg` where content density supports it.
- Keep primary actions full width on narrow screens and content-sized from `sm` upward.
- Preserve a minimum 44px interactive target and do not use hover as the only way to reveal controls or evidence.
- On result screens, keep `RiskBadge` and recommendation before detailed factor cards in reading order, even when the FloatingCard is visually positioned elsewhere.
