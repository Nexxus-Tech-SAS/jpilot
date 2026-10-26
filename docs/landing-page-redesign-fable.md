# Fable task: Redesign JPilot landing page (Nexxus)

Spec for implementing a modern, scroll-animated JPilot marketing landing page with a new product hero image and an animated install terminal.

---

## Context

Redesign the **JPilot marketing landing page** (product by Nexxus Tech) at route `/home`. The page is Vue 3 + Vite + PrimeVue 4. Keep the existing brand: dark cyan/indigo gradients, `ConstellationCanvas`, JPilot wordmark, and current copy tone.

### Entry point

`frontend/src/views/HomeView.vue`

### Current section order

1. `LandingHero.vue` — hero copy + `hero-img-1.png` / `hero-img-2.png`
2. `LandingFeatures.vue` — section head + **dashboard showcase** (`saas-feature-img-2.png`, alt: "JPilot platform dashboard preview") + feature card grid
3. `LandingSolutions.vue` — two static alternating image/copy blocks
4. `LandingInstall.vue` — install section at the bottom (`LandingInstallBlock.vue` — static terminal, copy-only)
5. `LandingFooterCta.vue`

### Key paths

| Resource | Path |
|----------|------|
| Shared styles | `frontend/src/assets/styles/landing.css` |
| Images | `frontend/src/assets/landing/` |
| Scroll animation (existing) | PrimeVue `v-animateonscroll` in `LoginView.vue` |

Prefer extending the existing PrimeVue scroll pattern before adding heavy dependencies.

### Reference assets (attach when assigning)

| Asset | Purpose |
|-------|---------|
| Architect UI screenshot | Product hero image reference — dark theme, sidebar, "What are you planning?", Architect/Operator/Analyst tabs, action cards, cyan streak background |
| Terminal Phase 1 screenshot | `image-00e1ca18-4b34-48a0-8b87-9d8888133d3e.png` — curl + installer intro |
| Terminal Phase 2 screenshot | `image-1245ead7-a5ad-4f6f-9517-719c4808dcf9.png` — download, Docker build, ready state |

---

## Target layout

```
[Hero]
[Product screenshot — Architect UI]
[Install section]
  ├── Headline: "Install JPilot in one command"
  ├── Lead copy (existing)
  ├── LandingInstallTerminalAnimation  ← NEW (animated demo)
  ├── LandingInstallBlock              ← REAL copy/paste + platform tabs (keep functional)
  └── Support links
[Scroll sections — alternating image/copy]
[Footer CTA]
```

---

## Goal 1 — Replace the dashboard image

Replace **`saas-feature-img-2.png`** (the "dashboard" showcase in `LandingFeatures.vue`) with a **new product screenshot** that reflects real JPilot UI.

### Style reference

Use the **Architect UI screenshot** — not a generic SaaS mockup. Match: dark theme, sidebar, planning cards, cyan streak background, Architect/Operator/Analyst mode switcher.

### Implementation options (pick one, document choice)

- **A)** Generate/export a polished PNG (browser frame, subtle shadow, rounded corners) and save as e.g. `frontend/src/assets/landing/jpilot-architect-showcase.png`
- **B)** Build a lightweight **CSS/HTML mock** of the Architect view if a static PNG is not feasible — must match the reference closely

### Details

- Update alt text to something accurate, e.g. `"JPilot Architect — AI-assisted deployment planning"`.
- Keep the dark gradient panel wrapper (`.landing-features-showcase`) but refine it so the screenshot feels premium (perspective, glow, optional parallax on scroll).

---

## Goal 2 — Move install under the product image + animated terminal

### Layout change

Pull install **up** from the bottom of the page. New flow after the hero:

1. Hero (unchanged or lightly refined)
2. **Product showcase block** — large Architect screenshot
3. **Install block directly below** — headline, lead, animated terminal, platform tabs, support links
4. Features / solutions with scroll animations (Goal 3)
5. Footer CTA

### Implementation

- Refactor so install lives in the showcase section (new component e.g. `LandingProductShowcase.vue`, or merge into `LandingFeatures.vue`).
- Remove or slim down standalone `LandingInstall.vue` so install is not duplicated at the bottom.
- Keep `#install` anchor for navbar/CTA links (`LandingNavbar.vue`, hero "Install JPilot", footer).

The **animated terminal** is the hero of the install block; the **static copy terminal** below stays for macOS/Linux/Windows tabs and the Copy button.

---

## Terminal animation spec

### Visual style (match reference screenshots)

| Element | Style |
|---------|--------|
| Background | `#000000` / `#020617` |
| Body text | `#e2e8f0` / white |
| Prompt/user | `#22d3ee` or cyan (match existing `.cmd-prompt`) |
| Success / checkmarks | `#22c55e` / `#4ade80` |
| Docker build lines | `#60a5fa` / blue (`=>` prefix) |
| Header title | Bold green: **JPilot / NSAgent installer** |
| "Ready" box | White border, centered text inside |
| Font | `ui-monospace`, SF Mono, Menlo — same as `LandingInstallBlock.vue` |
| Cursor | Blinking block cursor `█` at prompts |

Reuse existing terminal chrome from `LandingInstallBlock.vue` (traffic-light dots, title bar). The animation runs **inside** that frame — not a raw screenshot PNG.

### Animation structure: 2 phases, loop or scroll-triggered

- **Trigger:** Start when the install block enters viewport (~25% visible). Loop every ~18–22s, or restart on each scroll-into-view.
- **Pacing:** Line-by-line reveal (~40–80ms per line); Docker build lines faster (~25–40ms). Use `requestAnimationFrame` or a typed queue — no layout thrashing.
- **Reduced motion:** Respect `prefers-reduced-motion` — show Phase 2 final frame statically, no typing loop.
- **Performance:** Pause when off-screen via `IntersectionObserver` (save CPU).

### Phase 1 — Command + installer banner (~6–8s)

```text
juano@jpilot-demo:~$ cd /opt
juano@jpilot-demo:/opt$ curl -fsSL https://install.nexxus-tech.com/jpilot | bash

JPilot / NSAgent installer                    ← bold green

Published by Nexxus-Tech SAS - https://nexxus-tech.com
Source code: https://github.com/Nexxus-Tech-SAS/jpilot.git (branch: main)

This script downloads JPilot from the repository above, then runs its setup wizard.
Read it first: https://raw.githubusercontent.com/Nexxus-Tech-SAS/jpilot/main/get.sh

Need help or run into trouble? Contact us at https://www.nexxus-tech.com or support@nexxus-tech.com

✓ Docker is ready                             ← green checkmark

Where should JPilot be downloaded on this machine?
Pick a folder you can write to. Press Enter for the default, or type another path
(for example /opt/jpilot – the installer can create system folders with sudo).

Install folder [/home/juano/jpilot]: /opt/jpilot█   ← simulate typing "/opt/jpilot" then Enter
```

**Notes:**

- Phase 1 ends with simulated user input `/opt/jpilot` (typed char-by-char, ~60ms/char).
- URLs stay plain text inside the terminal body (no real links).
- Pause ~400ms before Phase 2.

### Phase 2 — Download, Docker build, ready (~10–12s)

```text
Downloading JPilot into /opt/jpilot...
✓ Downloaded

Starting the setup wizard...
Building and starting the setup wizard...

[+] Building 3.6s (17/17) FINISHED             ← white

=> [internal] load local bake definitions         0.0s   ← blue lines
=> => reading from stdin 548B                      0.0s
=> [internal] load build definition from Dockerfile 0.0s
=> => transferring dockerfile: 1.04kB             0.0s
=> [internal] load metadata for docker.io/library/python:3.12-slim  0.6s
=> [internal] load .dockerignore                  0.0s
=> => transferring context: 2B                      0.0s
=> [ 1/10] FROM docker.io/library/python:3.12-slim@sha256:...  0.0s
=> => resolve docker.io/library/python:3.12-slim@sha256:...    0.0s
=> [internal] load build context                  0.0s
=> => transferring context: 1.38kB                0.0s
=> CACHED [ 2/10] RUN apt-get update && apt-get install -y --no-install-recommends openssl  0.0s
=> CACHED [ 3/10] WORKDIR /app                    0.0s
=> CACHED [ 4/10] COPY backend-api/requirements.txt .  0.0s
=> CACHED [ 5/10] RUN pip install --no-cache-dir -r requirements.txt  0.0s
=> CACHED [ 6/10] COPY backend-api/app ./app      0.0s
=> CACHED [ 7/10] COPY installer/static ./static  0.0s
=> CACHED [ 8/10] COPY frontend/public/jpilot-favicon.png frontend/public/nexxus-tech-logo-full.svg /installer/static/  0.0s
=> CACHED [ 9/10] COPY installer/entrypoint.sh /entrypoint.sh  0.0s
=> CACHED [10/10] RUN chmod +x /entrypoint.sh     0.0s
=> exporting to image                             0.1s
=> => exporting layers                            0.0s
=> => exporting manifest sha256:...               0.0s
=> => exporting config sha256:...                 0.0s
=> => exporting attestation manifest sha256:...   0.0s
=> => exporting manifest list sha256:...         0.0s
=> => naming to docker.io/library/jpilot-installer-installer:latest  0.0s
=> => unpacking to docker.io/library/jpilot-installer-installer:latest  0.0s
=> resolving provenance for metadata file         0.0s

[+] up 3/3
✓ Image jpilot-installer-installer  Built
✓ Network jpilot-installer_default  Created
✓ Container jpilot-installer-installer-1  Started

┌─────────────────────────────────────┐
│  JPilot setup is ready.             │          ← bordered box, hold 2s
└─────────────────────────────────────┘

▶ Open https://localhost:9443                   ← ▶ in white/cyan

It uses a self-signed certificate, so your browser will show a security
warning the first time — that is expected for the installer. Accept it to continue.

Waiting for you to finish the wizard (Ctrl-C to abort)...
```

**Notes:**

- Docker block: scroll inside terminal if overflow; ~12–15 blue lines is enough (full list optional).
- Timestamps on the right (`0.0s`, `3.5s`) add realism — fade in with each line.
- Final box + URL hold for ~2s before loop/restart.
- Optional: subtle green pulse on `✓` lines when they appear.

### Suggested component structure

```vue
<!-- LandingInstallTerminalAnimation.vue -->
<!-- props: autoplay (default true), loop (default true) -->
<!-- composable: useTerminalTypewriter({ lines, speed, onComplete }) -->
<!-- line model: { text, class: 'line-default' | 'line-green' | 'line-blue' | 'line-prompt' | 'line-box' } -->
<!-- max-height + overflow-y: auto; auto-scroll to bottom as lines append -->
<!-- IntersectionObserver to start/pause when off-screen -->
```

Do **not** add Typewriter.js unless necessary — a small composable is enough.

---

## Goal 3 — Scroll-driven alternating layout (modern, 60fps)

Replace static feature/solution blocks with **scroll-triggered alternating rows**: image on one side, copy/features on the other; **swap sides** on the next row as the user scrolls.

### Pattern (desktop ≥960px)

| Row | Image | Copy |
|-----|-------|------|
| 1 | Right | Left |
| 2 | Left | Right |
| 3 | Right | Left |

### Animation requirements

- Smooth **horizontal slide + fade** (translateX ~40–80px → 0), optional subtle scale (0.96 → 1).
- Stagger copy bullets/cards within each row (~80–120ms).
- Use **`transform` and `opacity` only** (GPU-friendly); avoid animating `width`, `height`, `top`, `left`.
- **`will-change: transform`** only while animating; remove after.
- Pause/offscreen: use **`IntersectionObserver`** (threshold ~0.2–0.35) or PrimeVue **`v-animateonscroll`** — mirror `LoginView.vue` enter classes.
- Optional: subtle **parallax** on product screenshots (±8–16px) tied to scroll; disable on mobile and reduced-motion.
- Mobile: stack vertically (image above copy); simpler fade-up, no horizontal slide.

### Suggested structure

- New composable: `frontend/src/composables/useScrollReveal.js`
- New component: `LandingScrollSection.vue` — props: `imageSrc`, `imageAlt`, `reverse`, `eyebrow`, `title`, `lead`, `items[]`
- Refactor `LandingFeatures.vue` (feature grid can stay below scroll rows) and `LandingSolutions.vue` (convert two blocks into `LandingScrollSection` instances).

### Performance

- No GSAP unless justified; prefer CSS + IntersectionObserver.
- Test Chrome DevTools Performance: sustained 60fps while scrolling through all sections.
- Lazy-load images below the fold (`loading="lazy"`).

---

## Design system (do not break)

Keep existing CSS variables from `landing.css`:

- Primary: `#22d3ee` (dark) / `#0891b2` (light)
- Indigo accent: `#6366f1`
- Hero gradient: `#051221` → `#0b2b47`
- Radius: `--landing-radius-xl: 2rem`
- Motion: `cubic-bezier(0.22, 1, 0.36, 1)` (already used in `.landing-card`, `.landing-fade-in`)

Reuse: `ConstellationCanvas`, `JPilotMark`, `.landing-eyebrow`, `.landing-title`, `.landing-lead`, `.landing-check-list`.

---

## Files to touch

| File | Action |
|------|--------|
| `frontend/src/views/HomeView.vue` | Reorder sections; wire new components |
| `frontend/src/components/landing/LandingFeatures.vue` | Showcase + install grouping; scroll rows |
| `frontend/src/components/landing/LandingInstall.vue` | Remove standalone section or reduce to anchor-only |
| `frontend/src/components/landing/LandingInstallBlock.vue` | Extract shared terminal chrome |
| `frontend/src/components/landing/LandingInstallTerminalAnimation.vue` | **New** — animated install demo |
| `frontend/src/components/landing/LandingScrollSection.vue` | **New** — alternating scroll sections |
| `frontend/src/composables/useScrollReveal.js` | **New** — optional |
| `frontend/src/assets/styles/landing.css` | Scroll animation keyframes + utilities |
| `frontend/src/assets/landing/` | New product PNG; deprecate unused placeholders if replaced |

---

## Acceptance criteria

- [ ] Dashboard placeholder replaced with Architect-style product visual
- [ ] Install section sits **directly under** the product screenshot with `#install` still working
- [ ] Terminal animation matches both reference screenshots in content, colors, and sequence
- [ ] Phase 1 → Phase 2 transition feels continuous (same terminal session)
- [ ] Animation pauses when off-screen; respects `prefers-reduced-motion`
- [ ] Functional copy terminal + platform tabs remain below the animation
- [ ] At least **2–3 scroll sections** alternate image left/right with smooth 60fps motion
- [ ] No new npm deps unless necessary; if added, justify in a short comment
- [ ] Light and dark theme (`html.app-dark`) both look correct
- [ ] Mobile layout readable; no horizontal overflow from animations
- [ ] `npm run build` passes

---

## Out of scope

- Do not change auth, routing beyond `/home`, or app dashboard
- Do not bump `VERSION` or create a release unless explicitly asked
- Do not rewrite marketing copy unless needed for layout

---

## Deliverables

1. Working implementation in the repo
2. Brief summary: layout structure, animation approach, new assets
3. List any screenshots still needed for terminal polish
