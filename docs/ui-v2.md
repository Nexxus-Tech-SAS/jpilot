# UI V2 — switchable interface redesign (beta preview)

JPilot ships two complete user interfaces side by side:

- **Classic** — the existing UI, unchanged, and still the default.
- **V2** — a modern, animated redesign with first-class phone/iPad support.

Any user can switch at runtime — no reload, no data migration, no backend
involvement. The choice only affects the browser it was made in.

## Switching

- **Settings → Appearance → "New JPilot interface"** — toggle on/off
  (the Appearance section is visible to every user, not admin-gated).
- Inside V2, the **"New UI · Beta"** pill (nav rail footer on desktop, drawer
  on mobile) switches back to classic instantly.
- Deep link: `/settings?section=appearance`.

The preference is stored in `localStorage` under `jpilot_ui_version`
(`classic` | `v2`) following the same cookie-consent rules as the theme:
persisted only after *Accept all*, otherwise it lasts for the session.

## How it works

The mechanism mirrors dark mode (`.app-dark`):

1. `src/services/uiVersion.js` toggles a **`ui-v2` class on `<html>`**,
   exposes a reactive `useUiVersion()` ref, and dispatches a
   `jpilot-ui-version-change` window event. `applyStoredUiVersion()` runs in
   `main.js` before mount so there is no flash of the wrong UI.
2. The router mounts `src/layouts/LayoutGate.vue` at `/`, which renders
   `MainLayout.vue` (classic) or `MainLayoutV2.vue` (V2) based on that ref.
   Swapping unmounts the whole shell, so the two UIs cannot leak state into
   each other.
3. Six stylesheets under `src/assets/styles/v2/` are imported **last** in
   `main.js` (order: `tokens → base → animations → chat → views → public`).
   **Every rule is scoped under `html.ui-v2`** (dark variants under
   `html.ui-v2.app-dark`) and all keyframes are prefixed `v2-`, so the sheets
   are inert while the toggle is off. Because the class lives on `<html>`, the
   skin also reaches PrimeVue overlays teleported to `<body>` (dialogs,
   drawers, toasts, popovers).

### V2-only source

| Path | Purpose |
| --- | --- |
| `src/layouts/MainLayoutV2.vue` | V2 shell: session bootstrap, atmosphere, immersive chat, scroll contract |
| `src/components/v2/V2NavRail.vue` | Animated glass rail, sliding active indicator, collapse |
| `src/components/v2/V2BottomNav.vue` | Phone bottom dock (hidden on the chat route) |
| `src/components/v2/V2MobileDrawer.vue` | Phone/tablet drawer nav |
| `src/components/v2/V2TopBar.vue` | Phone top app bar |
| `src/components/v2/V2SunMoonIcon.vue` | Morphing theme-toggle icon |
| `src/components/v2/navModel.js` | Nav items + active-route semantics shared with classic |
| `src/components/settings-beta/AppearancePanel.vue` | The Appearance settings section |
| `src/services/uiVersion.js` | Version state, persistence, consent handling |
| `src/assets/styles/v2/*.css` | The entire V2 skin (scoped under `html.ui-v2`) |

Touches to pre-existing files are minimal and additive: one import swap in
`router/index.js` (`MainLayout` → `LayoutGate`), imports + two init calls in
`main.js`, additive class hooks in `ChatPane.vue` (no logic changes), the
Appearance registry entry in `SettingsBetaView.vue`, and a theme-sync listener
in classic `MainLayout.vue`.

## Behavior notes

- Both shells share the same routes, guards (auth/admin/license), stores,
  chat sessions, theme preference, and nav-collapse preference — switching
  UIs never changes what the app *does*.
- V2 keeps the classic contracts: `provide('openMobileNav')` for immersive
  chat, shell-level Toast/ConfirmDialog, `main-content-atmosphere` glass
  rules, and the `.main-view` scroll container.
- V2 fixes a classic iPad-portrait limitation: at 768–991 px the chat
  conversation sidebar is visible/usable again.
- Motion respects `prefers-reduced-motion` throughout; V2 sets the PrimeVue
  primary palette to the brand cyan ramp (classic keeps emerald).

## Adoption path

V2 is an evaluation preview. To make it the default later, flip the fallback
in `src/services/uiVersion.js` (`getUiVersion()` returns `UI_CLASSIC` today)
— or, once classic is retired, point the router back at a single layout and
drop the gate. Removing V2 entirely means deleting the V2-only files above
and reverting the small touches listed.
