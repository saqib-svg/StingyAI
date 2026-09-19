---
name: Autonomous Infrastructure Console
colors:
  surface: '#0f131c'
  surface-dim: '#0f131c'
  surface-bright: '#353943'
  surface-container-lowest: '#0a0e17'
  surface-container-low: '#181b25'
  surface-container: '#1c1f29'
  surface-container-high: '#262a34'
  surface-container-highest: '#31353f'
  on-surface: '#dfe2ef'
  on-surface-variant: '#bcc9cd'
  inverse-surface: '#dfe2ef'
  inverse-on-surface: '#2c303a'
  outline: '#869397'
  outline-variant: '#3d494c'
  surface-tint: '#4cd7f6'
  primary: '#4cd7f6'
  on-primary: '#003640'
  primary-container: '#06b6d4'
  on-primary-container: '#00424f'
  inverse-primary: '#00687a'
  secondary: '#bdc2ff'
  on-secondary: '#131e8c'
  secondary-container: '#2f3aa3'
  on-secondary-container: '#a8afff'
  tertiary: '#4edea3'
  on-tertiary: '#003824'
  tertiary-container: '#1bbd85'
  on-tertiary-container: '#00452e'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#acedff'
  primary-fixed-dim: '#4cd7f6'
  on-primary-fixed: '#001f26'
  on-primary-fixed-variant: '#004e5c'
  secondary-fixed: '#e0e0ff'
  secondary-fixed-dim: '#bdc2ff'
  on-secondary-fixed: '#000767'
  on-secondary-fixed-variant: '#2f3aa3'
  tertiary-fixed: '#6ffbbe'
  tertiary-fixed-dim: '#4edea3'
  on-tertiary-fixed: '#002113'
  on-tertiary-fixed-variant: '#005236'
  background: '#0f131c'
  on-background: '#dfe2ef'
  surface-variant: '#31353f'
typography:
  headline-xl:
    fontFamily: Space Grotesk
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-xl-mobile:
    fontFamily: Space Grotesk
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: Space Grotesk
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Space Grotesk
    fontSize: 18px
    fontWeight: '500'
    lineHeight: 24px
  headline-sm:
    fontFamily: Space Grotesk
    fontSize: 15px
    fontWeight: '500'
    lineHeight: 20px
  body-lg:
    fontFamily: Geist
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 22px
  body-md:
    fontFamily: Geist
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  body-sm:
    fontFamily: Geist
    fontSize: 11px
    fontWeight: '400'
    lineHeight: 16px
  label-lg:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.04em
  label-md:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 10px
    fontWeight: '400'
    lineHeight: 12px
    letterSpacing: 0.05em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 0.75rem
  gutter-desktop: 1rem
  margin: 1rem
  margin-desktop: 1.5rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1rem
  space-xl: 1.5rem
---

## Brand & Style
The design system targets cloud architects, DevOps leads, and FinOps engineers managing mission-critical enterprise infrastructure. It projects precision, deterministic control, absolute operational transparency, and intelligence. The emotional target is calm mastery over volatile distributed cloud spend. 

The aesthetic is a high-density, technical console marrying clean data-dense brutalism with refined developer-tool glassmorphism. It rejects decorative embellishments in favor of crisp delineation, explicit bounding boxes, strict telemetry alignments, and illuminated agent feedback states.

## Colors
The palette is engineered specifically for prolonged, low-fatigue operations room observation and rapid visual parsing:

- **Canvas Base (`#0a0e17` & `#0f172a`):** Deep space navy foundation providing maximum optical contrast without the stark eye-strain of pure `#000000`.
- **Card & Surface Tiers (`#131c2e` to `#1a243b`):** Progressively lighter navy-slate layers to articulate panel hierarchy without reliance on heavy dropshadows.
- **Structural Lines (`#22324f`):** Precision division borders for dense tabular views and architectural wiring diagrams.
- **Primary Kinetic Accent (`#06b6d4` & `#38bdf8`):** Electric cyan used exclusively for active focus points, live operational pathways, active toggles, and confirmed optimizations.
- **Cognitive / Agent State (`#818cf8`):** Atmospheric purple/indigo reserved for AI inference passes, plan generation, autonomous decision steps, and ML confidence metrics.
- **Telemetry Semantics:**
  - **Healthy / Realized Savings (`#10b981`):** Emerald green for verified cost cuts, healthy clusters, and passing invariants.
  - **Guardrail / Alert (`#f59e0b`):** Warning amber for approaching threshold budget limits, low-confidence proposed rightsizing, or required manual interventions.
  - **Violation / Rollback (`#f43f5e`):** Rose red for rejected actions, SLA infractions, or breached provisioning thresholds.

## Typography
The system employs a strict tripartite typographical hierarchy:

1. **Space Grotesk (Display & Section Headers):** Delivers clean structural engineering presence, anchoring major operational metrics and console region headers.
2. **Geist (Body & Analytical Copy):** Neutral, hyper-legible neo-grotesque crafted for complex user interfaces, dense metadata displays, and clear audit narratives.
3. **JetBrains Mono (Telemetry, Code, Identifiers & Data Tables):** Provides non-proportional tabular lining for monetary amounts, node tags, AWS/GCP/Azure resource IDs, latency durations, and agent reasoning traces.

## Layout & Spacing
A fluid 12-column workspace built for maximum information utility. Layout standards optimize for high-density horizontal monitoring viewports (1440px to 2560px) alongside adaptive multi-pane collapsibility:

- **Rhythm & Grid:** Built on an absolute 4px/8px micro-grid. Component paddings stay compressed (`space-xs` to `space-md`) to ensure critical operational metrics remain above the fold.
- **Desktop (1200px+):** Fixed global telemetry sidebar (240px or 64px collapsed), collapsible agent execution stream (380px right-hand rail), and a dynamic multi-panel canvas.
- **Tablet / Responsive (768px - 1199px):** Agent stream shifts into a modal pullout drawer; panels reflow from 3-column splits into dual 6-column arrangements.
- **Mobile (<768px):** Single column stack; table views convert to atomic card lists with strict visual prioritization of monthly burn rates and pending agent actions.

## Elevation & Depth
Depth is constructed through structured surface luminescence, borders, and deliberate optical radiance rather than heavy drop shadows:

- **Surface Layering:**
  - **Level 0 (Canvas):** `#0a0e17`
  - **Level 1 (Panels, Navbars, Side Rails):** `#0f172a` with a 1px border of `#22324f`
  - **Level 2 (Cards, Table Modules, Telemetry Blocks):** `#131c2e` with a 1px border of `#22324f`
  - **Level 3 (Modals, Context Menus, Hover Flyouts):** `#1a243b` with a 1px border of `#38bdf8` at 35% opacity
- **Subtle Glow & Agent Execution Radiance:**
  - Active nodes running automated cloud operations carry a localized perimeter glow: `box-shadow: 0 0 12px 1px rgba(6, 182, 212, 0.25)`.
  - Cognitive/planning steps introduce an ambient indigo aura: `box-shadow: 0 0 14px 2px rgba(129, 140, 248, 0.2)`.

## Shapes
The system relies on compact, sharp radii (`0.25rem` / 4px base) to convey industrial rigor and structural stability. 

- Core containers, metric blocks, input rows, and data tables use strict 4px corners (`roundedness: 1`).
- Telemetry pills and status indicator badges use full pill geometry for rapid contrast against square-edged data grids.
- Node connection connectors and agent decision graphs feature crisp right-angle chamfers and sharp vectors to avoid whimsical or playful interpretations.

## Components

### Buttons
- **Primary Autonomous Action (Apply/Execute):** Solid `#06b6d4` background, `#0a0e17` text (JetBrains Mono, bold), 4px border radius. Hover introduces an electric cyan drop-glow (`0 0 10px rgba(6, 182, 212, 0.4)`).
- **Secondary / Review Action:** Transparent fill with 1px border of `#22324f`, text in `#e2e8f0`. Hover transitions border to `#38bdf8` and background to `rgba(56, 189, 248, 0.05)`.
- **Destructive / Rollback:** Low-opacity rose surface (`rgba(244, 63, 94, 0.1)`), 1px `#f43f5e` border, `#f43f5e` text.

### Chips & Telemetry Badges
- **Size & Type:** Micro-scaled, `label-sm` monospaced font, pill-rounded.
- **States:**
  - *Healthy Savings:* Emerald background tint (`rgba(16, 185, 129, 0.1)`), border `rgba(16, 185, 129, 0.3)`, text `#10b981`. Preceded by a 4px solid green pulse beacon.
  - *Agent Reasoning:* Indigo background tint (`rgba(129, 140, 248, 0.1)`), border `rgba(129, 140, 248, 0.3)`, text `#818cf8`.
  - *Policy Guardrail:* Amber tint (`rgba(245, 158, 11, 0.1)`), border `rgba(245, 158, 11, 0.3)`, text `#f59e0b`.

### Cards & Telemetry Panels
- High-contrast containers on `#131c2e` with a continuous 1px `#22324f` border.
- Cards feature an upper 28px utility bar containing node title, time delta, and agent confidence scores rendered in `label-sm`.

### Input Fields & Filter Bars
- Dark recessed background (`#0a0e17`), 1px structural border (`#22324f`).
- Text in `Geist` or `JetBrains Mono`. Focus ring triggers a sharp, 1px border illumination in `#06b6d4` with no thick offset ring.

### Data Tables & Resource Matrices
- Alternating subtle row zebra striping using `#0f172a` and `#131c2e`.
- Sticky column headers with uppercase `label-md` tracking, separated by a crisp 1px `#22324f` horizontal line.

### Agent Cognitive Timeline (Specialized Component)
- Vertical node-link graph tracking autonomous agent operations:
  - Inactive/historical nodes: 1px `#22324f` border, muted text.
  - Active execution step: Electric cyan pulsating beacon with cyan directional connector lines.
  - Thought/Evaluation step: Indigo perimeter glow with inline parameter comparison badges.