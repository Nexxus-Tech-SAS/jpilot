<template>
  <div ref="rootEl" class="deck-page" tabindex="-1">
    <canvas ref="bgcanvas" class="deck-canvas"></canvas>
    <div class="aurora a1"></div>
    <div class="aurora a2"></div>
    <div class="aurora a3"></div>
    <div class="deck-progress" :style="{ width: progressPct }"></div>

    <div ref="stage" class="stage"></div>

    <button class="deck-nav deck-prev" aria-label="Previous slide" @click="go(cur - 1)">
      <svg viewBox="0 0 24 24"><polyline points="15 18 9 12 15 6" /></svg>
    </button>
    <button class="deck-nav deck-next" aria-label="Next slide" @click="go(cur + 1)">
      <svg viewBox="0 0 24 24"><polyline points="9 18 15 12 9 6" /></svg>
    </button>

    <div class="chrome">
      <div class="brandmini">
        <JPilotMark :size="22" tone="dark" />
        <span class="ld-cursor brand-mini-name">JPilot</span>
        <span>&nbsp;· Nexxus Tech SAS</span>
      </div>
      <div class="dots">
        <b
          v-for="(s, i) in slideCount"
          :key="i"
          :class="{ on: i === cur }"
          @click="go(i)"
        ></b>
      </div>
      <div class="chrome-end">
        <div class="counter">{{ counterText }}</div>
        <button
          class="fs-btn"
          :aria-label="isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'"
          :title="(isFullscreen ? 'Exit fullscreen' : 'Fullscreen') + ' (F)'"
          @click="toggleFullscreen"
        >
          <svg v-if="!isFullscreen" viewBox="0 0 24 24"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" /></svg>
          <svg v-else viewBox="0 0 24 24"><path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3" /></svg>
        </button>
      </div>
    </div>
    <div class="hint">← → or Space to navigate · F for fullscreen</div>
  </div>
</template>

<script setup>
import { computed, h, onBeforeUnmount, onMounted, ref, render } from 'vue'
import JPilotMark from '../components/JPilotMark.vue'

const LOGO_NEXXUS = '/nexxus-tech-logo-full.svg'

const rootEl = ref(null)
const bgcanvas = ref(null)
const stage = ref(null)
const cur = ref(0)
const slideCount = ref(0)
const isFullscreen = ref(false)

const counterText = computed(
  () =>
    String(cur.value + 1).padStart(2, '0') +
    ' / ' +
    String(slideCount.value).padStart(2, '0')
)
const progressPct = computed(() =>
  slideCount.value ? ((cur.value + 1) / slideCount.value) * 100 + '%' : '0%'
)

const I = {
  terminal: '<polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>',
  user: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
  alert: '<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
  robot: '<rect x="3" y="8" width="18" height="12" rx="3"/><circle cx="8.5" cy="14" r="1.4"/><circle cx="15.5" cy="14" r="1.4"/><line x1="12" y1="3" x2="12" y2="8"/><circle cx="12" cy="3" r="1.4"/>',
  chat: '<path d="M21 11.5a8.38 8.38 0 0 1-8.5 8.5 8.5 8.5 0 0 1-3.8-.9L3 21l1.9-5.7A8.5 8.5 0 0 1 12.5 3 8.38 8.38 0 0 1 21 11.5z"/>',
  brain: '<path d="M9 3a3 3 0 0 0-3 3 3 3 0 0 0-1 5.8V15a3 3 0 0 0 4 2.8A3 3 0 0 0 12 19V5a2 2 0 0 0-3-2z"/><path d="M15 3a3 3 0 0 1 3 3 3 3 0 0 1 1 5.8V15a3 3 0 0 1-4 2.8A3 3 0 0 1 12 19"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
  server: '<rect x="3" y="4" width="18" height="6" rx="2"/><rect x="3" y="14" width="18" height="6" rx="2"/><line x1="7" y1="7" x2="7.01" y2="7"/><line x1="7" y1="17" x2="7.01" y2="17"/>',
  key: '<path d="M21 2l-2 2m-7.6 7.6a5 5 0 1 0-7.07 7.07 5 5 0 0 0 7.07-7.07zm0 0L15 8m0 0l3 3 3-3-3-3"/>',
  users: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
  magic: '<path d="M15 4V2m0 20v-2M8.5 8.5 7 7m10 10-1.5-1.5M4 15H2m20 0h-2M9.5 9.5 3 16l5 5 6.5-6.5z"/><path d="M18 6l1 1"/>',
  cubes: '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22" x2="12" y2="12"/>',
  compass: '<circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/>',
  tools: '<path d="M14.7 6.3a4 4 0 0 0 5 5l-7 7-3-3 7-7zM6 10l3 3-5 5-3-3 5-5z"/>',
  search: '<circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
  desktop: '<rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>',
  cogs: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-2.82 1.17V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 8 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 3 12H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 8 1.65 1.65 0 0 0 4.27 6.18l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 3.6 1.65 1.65 0 0 0 11 2v.09"/>',
  plug: '<path d="M9 2v6m6-6v6M7 8h10v3a5 5 0 0 1-10 0V8zM12 16v6"/>',
  db: '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5"/><path d="M3 12c0 1.7 4 3 9 3s9-1.3 9-3"/>',
  chip: '<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v3m6-3v3M9 19v3m6-3v3M2 9h3m-3 6h3m14-6h3m-3 6h3"/>',
  book: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
  comment: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
  bookmark: '<path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>',
  list: '<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><circle cx="3.5" cy="6" r="1"/><circle cx="3.5" cy="12" r="1"/><circle cx="3.5" cy="18" r="1"/>',
  bolt: '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
  check: '<polyline points="20 6 9 17 4 12"/>',
  checkc: '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
  fingerprint: '<path d="M12 11a2 2 0 0 0-2 2c0 2 .5 4 1 5"/><path d="M12 7a6 6 0 0 0-6 6c0 3 1 5 1 5"/><path d="M12 3a10 10 0 0 0-10 10"/><path d="M12 3a10 10 0 0 1 10 10c0 4-1 7-1 7"/><path d="M16 13a4 4 0 0 0-8 0c0 2 .5 4 1 5"/>',
  lock: '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
  contract: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="13" y2="17"/>',
  usertie: '<circle cx="12" cy="7" r="4"/><path d="M5.5 21a6.5 6.5 0 0 1 13 0"/><path d="M12 11l1.5 4-1.5 2-1.5-2z"/>',
  box: '<path d="M21 8l-9-5-9 5 9 5 9-5zM3 8v8l9 5 9-5V8"/>',
  net: '<rect x="9" y="3" width="6" height="5" rx="1"/><rect x="2" y="16" width="6" height="5" rx="1"/><rect x="16" y="16" width="6" height="5" rx="1"/><path d="M12 8v4M12 12H5v4m7-4h7v4"/>',
  trend: '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
  handshake: '<path d="M11 17l2 2 4-4M2 12l4-4 5 5M22 12l-4-4-3 3M6 8l3 3M14 8l-2 2"/>',
  seed: '<path d="M12 22V12M12 12C12 7 8 4 3 4c0 5 4 8 9 8zM12 12c0-5 4-8 9-8 0 5-4 8-9 8z"/>',
  bullhorn: '<path d="M3 11l14-6v14L3 13zM3 11v2a3 3 0 0 0 3 3M17 8a4 4 0 0 1 0 8"/>',
  globe: '<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15 15 0 0 1 0 20 15 15 0 0 1 0-20z"/>',
  mail: '<rect x="2" y="4" width="20" height="16" rx="2"/><polyline points="22 6 12 13 2 6"/>',
  play: '<polygon points="6 4 20 12 6 20 6 4"/>',
  plus: '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
  cube: '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22" x2="12" y2="12"/>'
}
const sv = (n, cls = '') => `<svg class="${cls}" viewBox="0 0 24 24">${I[n] || ''}</svg>`
const ic = (n, g = '') => `<div class="ico ${g}">${sv(n)}</div>`

const eb = (t) => `<div class="eyebrow r">${t}</div>`
const h1t = (t) => `<h1 class="title r">${t}</h1>`
const card = (o, d = 0) =>
  `<div class="card r" style="animation-delay:${d}s">${ic(o.i, o.g || '')}<h3>${o.t}</h3><p>${o.d}</p></div>`
const rowcard = (o, d = 0) =>
  `<div class="card row r" style="animation-delay:${d}s">${ic(o.i, o.g || '')}<div class="tx"><h3>${o.t}</h3><p>${o.d}</p></div></div>`
const DELAY = (i) => (0.12 + i * 0.07).toFixed(2)
const mark = (variant, size) =>
  `<span class="deck-mark" data-variant="${variant}" data-size="${size}"></span>`

function buildSlides() {
  const SLIDES = []

  /* 1 TITLE */
  SLIDES.push(`<div class="wrap">
 <div class="brandrow r">${mark('full', 96)}<span class="bn ld-cursor jp-wordmark-bright">JPilot</span></div>
 <div class="hero"><span class="l1 r" style="animation-delay:.15s">The AI copilot for</span>
   <span class="l2 r" style="animation-delay:.28s"><span class="grad">network infrastructure</span></span></div>
 <p class="lead r" style="animation-delay:.45s;margin-top:1.2rem">Register your NetScaler, F5, Cisco and SDX appliances. Bring your own AI keys. Then design, configure and troubleshoot in plain language — with vendor-aware tools, memory and guardrails.</p>
 <div class="chips r" style="animation-delay:.6s">
   <span class="chip">NetScaler ADC</span><span class="chip">F5 BIG-IP</span><span class="chip">Cisco IOS/XE</span><span class="chip">NetScaler SDX</span></div>
 <p class="r" style="animation-delay:.75s;margin-top:2rem;color:#6f84a3;font-size:.9rem">Tech demo · Nexxus Tech SAS &nbsp;·&nbsp; <span style="color:var(--cyan);font-weight:600">nexxus-tech.com</span></p>
</div>`)

  /* 2 PROBLEM */
  SLIDES.push(`<div class="wrap">${eb('The problem')}${h1t('Running network infrastructure is still a manual, expert-only craft')}
 <div class="grid g2">
 ${[
   { i: 'terminal', t: 'CLI sprawl across vendors', d: 'Every appliance — NetScaler, F5, Cisco, SDX — has its own CLI, syntax and quirks. Engineers context-switch constantly and memorize thousands of commands.' },
   { i: 'user', t: 'Knowledge locked in a few experts', d: 'Principal-level skill for ADC, WAF and Zero-Trust is scarce and expensive. When the expert is unavailable, change slows to a crawl.' },
   { i: 'alert', t: 'Change is slow and risky', d: 'A mistyped command on a production load balancer can take down critical apps. Teams move cautiously, lengthening every maintenance window.' },
   { i: 'robot', t: "Generic AI tools don't fit", d: "ChatGPT-style assistants don't know your appliances, can't run vendor tools safely, and have no memory of your environment or guardrails." }
 ].map((o, i) => card(o, DELAY(i))).join('')}</div></div>`)

  /* 3 STATS */
  SLIDES.push(`<div class="wrap">${eb('Why it matters')}${h1t('The cost of expert-bound, manual operations')}
 <div class="grid g4">
 ${[
   ['1,000s', 'of vendor CLI commands an engineer must know across ADC, F5, Cisco & SDX'],
   ['Hours', 'to design, document and safely deploy a single load-balancing change'],
   ['20+', 'countries where Nexxus has seen the same operational bottleneck first-hand'],
   ['1', 'mistyped command can take a production application offline']
 ].map((s, i) => `<div class="card r" style="animation-delay:${DELAY(i)}s;text-align:center"><div class="stat">${s[0]}</div><div class="statlbl">${s[1]}</div></div>`).join('')}</div>
 <p class="note r" style="animation-delay:.5s;font-size:1.05rem;color:var(--ice)">JPilot turns that scarce, manual expertise into an always-available, vendor-aware copilot.</p></div>`)

  /* 4 VISION */
  SLIDES.push(`<div class="wrap">${eb('The vision')}${h1t('A conversational control plane for the network')}
 <div class="split">
  <div>
   <div class="panel glow r" style="animation-delay:.2s;margin-bottom:18px"><p style="font-family:var(--head);font-style:italic;color:var(--ice);font-size:1.05rem;line-height:1.45">“We spent 15 years mastering NetScaler, WAF and Zero-Trust by hand. JPilot encodes that craft into an agent that any team can run — safely.”</p></div>
   ${[
     { i: 'chat', t: 'Plain language, not syntax', d: 'Describe the outcome. JPilot plans, references the right docs, and executes vendor commands for you.' },
     { i: 'brain', t: 'Vendor-aware intelligence', d: 'A multi-vendor "brain" gives the agent memory, prompts and tools specific to each appliance family.' },
     { i: 'shield', t: 'Safe by construction', d: 'Read-first roles, plan-and-confirm changes, and your credentials never leave your environment.' }
   ].map((o, i) => rowcard(o, DELAY(i + 3))).join('')}
  </div>
  <div class="panel r" style="animation-delay:.35s">
   <div class="ptitle">One platform, every vendor</div>
   <p style="color:var(--mute);font-size:.9rem;margin-bottom:1rem">JPilot is the engine. Each appliance family is a module that plugs in.</p>
   ${['NetScaler ADC (MPX / VPX)', 'NetScaler SDX', 'F5 BIG-IP (TMSH)', 'Cisco IOS / XE'].map((m) => `<div class="modrow">${sv('cube')}${m}</div>`).join('')}
   <div class="modrow new">${sv('plus')}Your next vendor →</div>
  </div>
 </div></div>`)

  /* 5 PRODUCT */
  SLIDES.push(`<div class="wrap">${eb('Product overview')}${h1t('What JPilot does')}
 <div class="grid g3">
 ${[
   { i: 'server', t: 'Appliance inventory', d: 'A guided wizard registers each device with encrypted (Fernet) credentials and tags for filtering.' },
   { i: 'key', t: 'Bring-your-own AI', d: 'Connect OpenAI, Anthropic, Gemini, Bedrock, Azure, OpenRouter and more. You hold the keys; you pay the provider.' },
   { i: 'chat', t: 'Conversational chat', d: 'A tool-calling agent bound to the selected appliance. Credentials are never sent to the LLM.' },
   { i: 'users', t: 'Three expert roles', d: 'Architect designs, Operator configures, Analyst troubleshoots — each with the right tools and permissions.' },
   { i: 'magic', t: 'Guided workflows', d: 'Interactive forms for load balancers, design documents, and one-click Architect → Operator handoff.' },
   { i: 'cubes', t: 'Calibration Studio', d: 'Install skills, personas and knowledge packs from the Nexxus Blueprint Library to specialize the agent.' }
 ].map((o, i) => card(o, DELAY(i))).join('')}</div></div>`)

  /* 6 ROLES */
  SLIDES.push(`<div class="wrap">${eb('How it works · roles')}${h1t('One agent, three expert personas')}
 <div class="grid g3">
 ${[
   ['compass', 'Architect', 'var(--violet)', 'Plan-only', 'Structured discovery via interactive forms, then produces formal design & change-control documents. Never touches the appliance.'],
   ['tools', 'Operator', 'var(--blue)', 'Full control', 'Configures the appliance from chat or an attached design — but always presents a plan and waits for your approval before any change.'],
   ['search', 'Analyst', 'var(--green)', 'Read-only', 'Read-first troubleshooting: diagnostics, inventory, service status and performance — with zero risk of modifying state.']
 ].map((r, i) => `<div class="card r" style="animation-delay:${DELAY(i)}s">
   <div class="ico" style="border-color:${r[2]}"><svg viewBox="0 0 24 24" style="stroke:${r[2]}">${I[r[0]]}</svg></div>
   <h3 class="ld-cursor" style="font-size:1.25rem;--ink:#fff;--cur:${r[2]}">${r[1]}</h3>
   <span class="badge" style="color:${r[2]}">${r[3]}</span>
   <div class="hr"></div><p style="font-size:.92rem">${r[4]}</p></div>`).join('')}</div>
 <p class="note r" style="animation-delay:.5s">Personas extend these base roles — e.g. "Security Architect" — layering specialist prompts on top of the role's tools and guardrails.</p></div>`)

  /* 7 ARCHITECTURE */
  SLIDES.push(`<div class="wrap">${eb('Architecture')}${h1t('How JPilot is built')}
 <div class="split">
  <div>${[
    { i: 'desktop', t: 'Frontend (Vue 3)', d: 'Chat, inventory, settings, Calibration Studio. Served via nginx with TLS.' },
    { i: 'cogs', t: 'Backend API (FastAPI)', d: 'Orchestration, roles, memory-gated RAG, auth, licensing, AI-provider routing.' },
    { i: 'plug', t: 'MCP server', d: 'Model Context Protocol tools: Next-Gen API, classic CLI over SSH, NITRO, diagnostics.' },
    { i: 'db', t: 'MongoDB', d: 'Inventory, users, settings, encrypted credentials and usage — all on your infrastructure.' }
  ].map((o, i) => rowcard(o, DELAY(i))).join('')}</div>
  <div class="panel r" style="animation-delay:.35s">
   <div class="ptitle">Connects out to — nothing stored there</div>
   ${[
     { i: 'chip', t: 'Your appliances', d: 'NetScaler, F5, Cisco, SDX — reached via Next-Gen API or SSH/TMSH from the MCP server.' },
     { i: 'robot', t: 'Your AI provider', d: 'The LLM you configured. Receives the task and tool results — never your device credentials.' },
     { i: 'book', t: 'Official docs (opt-in)', d: 'Vendor-isolated documentation search to ground answers in Citrix / F5 / Cisco references.' },
     { i: 'cubes', t: 'Blueprint Library', d: 'Calibration Studio pulls skills, personas and knowledge packs over a license-gated catalog.' }
   ].map((o) => `<div class="li" style="margin:.85rem 0">${sv(o.i)}<div><b style="color:#fff;font-family:var(--head)">${o.t}</b><div style="color:var(--mute);font-size:.84rem;margin-top:.2rem">${o.d}</div></div></div>`).join('')}
  </div>
 </div></div>`)

  /* 8 AGENT LOOP */
  SLIDES.push(`<div class="wrap">${eb('Inside a chat turn')}${h1t('Grounded, gated, and guarded by design')}
 <div class="steps">
 ${[
   ['comment', 'Intent', 'Your request is routed to a role and the minimal set of vendor tools it needs.'],
   ['bookmark', 'Memory gate', 'A RAG layer validates the right API/CLI usage before any command is allowed to run.'],
   ['list', 'Plan', 'For changes, Operator drafts a plan and waits for your explicit approval.'],
   ['bolt', 'Execute', 'Vendor tools run via MCP — Next-Gen API, NITRO, or CLI over SSH — against the appliance.'],
   ['checkc', 'Verify & report', 'Results are summarized; loop-breakers pause and ask if a run gets stuck instead of grinding.']
 ].map((s, i) => `<div class="card step r" style="animation-delay:${DELAY(i)}s">
   <div style="display:flex;justify-content:space-between;align-items:center"><span class="n">${i + 1}</span>${ic(s[0])}</div>
   <h3 style="margin-top:.6rem">${s[1]}</h3><p>${s[2]}</p>
   ${i < 4 ? '<span class="chev">›</span>' : ''}</div>`).join('')}</div>
 <p class="note r" style="animation-delay:.5s">Token-optimized throughout: intent-based tool routing, model-aware context limits, prompt caching and blueprint-first matching.</p></div>`)

  /* 9 SECURITY */
  SLIDES.push(`<div class="wrap">${eb('Security & trust')}${h1t("Built for environments that can't take risks")}
 <div class="grid g3">
 ${[
   { i: 'user', t: 'Credentials never sent to the LLM', d: 'Device passwords are encrypted with Fernet and used only by the MCP server — never placed in a prompt.' },
   { i: 'key', t: 'You own the AI relationship', d: 'Bring your own provider keys. Nexxus supplies no inference and sees none of your traffic.' },
   { i: 'fingerprint', t: 'Passkeys & lockout', d: 'WebAuthn passkey policy, password lockout, and rate-limited recovery codes protect access.' },
   { i: 'server', t: 'Self-hosted by default', d: 'Runs as a Docker stack on your infrastructure. Your inventory and data never leave your network.' },
   { i: 'lock', t: 'TLS everywhere', d: 'nginx terminates HTTPS; admins can rotate the certificate from the UI with validation.' },
   { i: 'contract', t: 'Licensed & governed', d: 'Fingerprint-bound licensing with an activation gate, plus an audit-friendly, role-based model.' }
 ].map((o, i) => `<div class="card r" style="animation-delay:${DELAY(i)}s">${ic(o.i, 'g')}<h3>${o.t}</h3><p>${o.d}</p></div>`).join('')}</div></div>`)

  /* 10 CALIBRATION */
  SLIDES.push(`<div class="wrap">${eb('The differentiator')}${h1t('Stack Calibration Studio: where the expertise lives')}
 <div class="split">
  <div>
   <p class="lead r" style="animation-delay:.2s;color:var(--ice);margin-bottom:1rem">JPilot is the engine. The Nexxus Blueprint Library is the accumulated craft — packaged, versioned and license-gated — that makes the agent an expert in your stack.</p>
   ${[
     { i: 'magic', t: 'Skills', d: 'Blueprint-first recipes that match a request and inject the exact prompts, memory and steps to execute it reliably.' },
     { i: 'usertie', t: 'Personas', d: 'Specialist roles (e.g. Security Architect) that layer expert behavior onto a base role and pull in their skills.' },
     { i: 'box', t: 'Knowledge packs', d: 'Curated reference and deliverable templates that ground design and change work in proven patterns.' }
   ].map((o, i) => rowcard(o, DELAY(i + 2))).join('')}
  </div>
  <div class="panel glow r" style="animation-delay:.4s">
   <div class="ptitle">Why it's a moat</div>
   ${['Every engagement and release deepens the library.', 'Tiered entitlements gate premium blueprints by plan.', "Customers can't easily replicate 15+ years of tuned, vendor-specific know-how.", 'New vendors ship as content — not new infrastructure.']
     .map((m) => `<div class="li" style="margin:.9rem 0">${sv('checkc')}<span>${m}</span></div>`).join('')}
  </div>
 </div></div>`)

  /* 11 DEMO */
  SLIDES.push(`<div class="wrap" style="text-align:center">
 <div class="playbtn r" style="animation-delay:.1s">${sv('play')}</div>
 <h1 class="title r" style="animation-delay:.2s;text-align:center">LIVE DEMO</h1>
 <p class="lead r" style="animation-delay:.3s;margin:0 auto;text-align:center">From a plain-language request to a deployed, verified change</p>
 <div class="flow">
 ${['Register an appliance', 'Ask in plain language', 'Architect designs', 'Hand off to Operator', 'Operator deploys', 'Analyst verifies']
   .map((f, i) => `<div class="fstep r" style="animation-delay:${DELAY(i + 2)}s"><div class="n">${i + 1}</div><p>${f}</p></div>`).join('')}</div>
 <p class="note r" style="animation-delay:.7s">Watch credentials stay local, the plan-and-confirm gate, and live generation metrics (tok/s) as the agent works.</p></div>`)

  /* 12 ROADMAP */
  SLIDES.push(`<div class="wrap">${eb('Roadmap')}${h1t('From four vendors to a network operations platform')}
 <div class="grid g3">
 ${[
   ['NOW', 'var(--cyan)', ['NetScaler ADC — GA', 'F5, Cisco, SDX — beta', '3 roles + custom personas', 'Calibration Studio + Blueprints', 'One-click self-update']],
   ['NEXT', 'var(--ice)', ['Promote F5 / Cisco / SDX to GA', 'Custom personas for security & other roles', 'Deeper change-control automation', 'Expanded blueprint library', 'Team workspaces, RBAC & audit reporting']],
   ['LATER', '#b6c2d6', ['New vendor modules (firewalls, DNS, cloud LBs)', 'Multi-appliance orchestration', 'Proactive drift detection', 'Partner blueprint marketplace', 'Managed / SaaS option']]
 ].map((c, i) => `<div class="card col r" style="animation-delay:${DELAY(i)}s"><span class="pill" style="color:${c[1]}">${c[0]}</span>
   ${c[2].map((it) => `<div class="li"><span class="dot" style="background:${c[1]}"></span><span>${it}</span></div>`).join('')}</div>`).join('')}</div></div>`)

  /* 13 PRICING */
  SLIDES.push(`<div class="wrap">${eb('Business model')}${h1t('Free to try, monetized through expertise')}
 <div class="grid g3">
 ${[
   ['Early-Access', 'var(--mute)', 'Get started', ['Full platform, self-hosted', 'All four vendor integrations', 'Bring your own AI keys', 'Built-in roles & guided forms'], false],
   ['Enterprise', 'var(--blue)', 'Scale with blueprints', ['Everything in Early-Access', 'Premium Blueprint Library', 'Curated knowledge packs', 'Priority support'], false],
   ['Enterprise Pro', 'var(--violet)', 'Customize the agent', ['Everything in Enterprise', 'Stack Calibration Studio', 'Custom personas in chat', 'Bespoke calibration & onboarding'], true]
 ].map((t, i) => `<div class="card tier r" style="animation-delay:${DELAY(i)}s;${t[4] ? 'border-color:' + t[1] + ';box-shadow:0 0 50px -20px ' + t[1] : ''}">
   <h2>${t[0]}</h2><div class="tagm" style="color:${t[1]}">${t[2]}</div><div class="hr"></div>
   ${t[3].map((f) => `<div class="li"><svg viewBox="0 0 24 24" style="stroke:${t[1]}">${I.check}</svg><span>${f}</span></div>`).join('')}</div>`).join('')}</div>
 <p class="note r" style="animation-delay:.5s">Land with a free, self-hosted product that practitioners adopt bottom-up; expand into Enterprise blueprints and Pro calibration — plus Nexxus consulting services.</p></div>`)

  /* 14 WHY NOW */
  SLIDES.push(`<div class="wrap">${eb('Why now · why us')}${h1t('The right team at the right moment')}
 <div class="split">
  <div>${[
    { i: 'trend', t: 'AI is finally tool-capable', d: 'LLMs can now plan and call tools reliably enough to operate real infrastructure under guardrails.' },
    { i: 'net', t: 'Networks grow, teams shrink', d: 'More vendors and clouds, fewer experts — the operational gap is widening every year.' },
    { i: 'shield', t: "Security can't be an afterthought", d: 'BYO-keys, self-hosting and read-first roles meet the bar that regulated enterprises require.' }
  ].map((o, i) => rowcard(o, DELAY(i))).join('')}</div>
  <div class="panel glow r" style="animation-delay:.35s">
   <div class="credit"><img src="${LOGO_NEXXUS}" style="height:38px;width:auto;border-radius:8px" alt="Nexxus Tech"/><div><b style="font-family:var(--head);font-size:1.1rem;color:#fff">Nexxus Tech SAS</b><div style="color:var(--ice);font-size:.78rem">Principal-level NetScaler, WAF &amp; Zero-Trust consulting</div></div></div>
   <div class="hr"></div>
   ${[
     ['15+', 'years of principal-level delivery'],
     ['20+', 'countries served'],
     ['Fortune 500', '& government engagements'],
     ['SME', 'Citrix, Cisco &amp; Oracle — deep ADC, WAF &amp; cloud']
   ].map((s) => `<div style="display:flex;align-items:center;gap:1rem;margin:.7rem 0"><div class="stat" style="font-size:1.5rem;min-width:120px">${s[0]}</div><div style="color:var(--text);font-size:.86rem">${s[1]}</div></div>`).join('')}
  </div>
 </div></div>`)

  /* 15 ASK */
  SLIDES.push(`<div class="wrap">${eb('The ask')}${h1t("What we're looking for")}
 <div class="grid g3">
 ${[
   { i: 'handshake', t: 'Design partners', d: "Enterprises running NetScaler / F5 / Cisco who'll co-develop blueprints and validate in production." },
   { i: 'seed', t: 'Investment', d: 'To accelerate vendor GA, grow the Blueprint Library, and build the team behind a self-serve motion.' },
   { i: 'bullhorn', t: 'Channel & advisors', d: 'Introductions to security and networking leaders, partners, and operators who know this pain.' }
 ].map((o, i) => `<div class="card r" style="animation-delay:${DELAY(i)}s;text-align:center"><div class="ico" style="margin:0 auto 14px">${sv(o.i)}</div><h3>${o.t}</h3><p>${o.d}</p></div>`).join('')}</div>
 <div class="codebar r" style="animation-delay:.5s"><span class="pmpt">Try it now:&nbsp;&nbsp;</span>curl -fsSL https://install.nexxus-tech.com/jpilot | bash</div></div>`)

  /* 16 CLOSE */
  SLIDES.push(`<div class="wrap closewrap">
 <div class="r" style="animation-delay:.1s;display:flex;align-items:center;justify-content:center;gap:18px;margin-bottom:1.4rem">
   ${mark('full', 84)}
   <span class="ld-cursor jp-wordmark-bright" style="font-size:2.6rem;letter-spacing:.06em">JPilot</span></div>
 <h1 class="title r" style="animation-delay:.25s;text-align:center">Let's make network operations conversational.</h1>
 <p class="r" style="animation-delay:.4s;color:var(--ice);font-size:1.1rem;margin-bottom:1.6rem">JPilot — by Nexxus Tech SAS</p>
 <div class="r" style="animation-delay:.55s;display:flex;gap:2rem;justify-content:center;flex-wrap:wrap;color:var(--text)">
   <span style="display:flex;align-items:center;gap:.5rem">${sv('globe')}nexxus-tech.com</span>
   <span style="display:flex;align-items:center;gap:.5rem">${sv('mail')}support@nexxus-tech.com</span>
 </div></div>`)

  return SLIDES
}

let slides = []
let mountedMarks = []
let raf = 0

function applyStagger(slide) {
  slide.querySelectorAll('.r').forEach((el, i) => {
    el.style.animation = 'none'
    void el.offsetHeight
    el.style.animation = ''
    el.style.animationDelay = (0.18 + i * 0.09).toFixed(2) + 's'
  })
}

function go(n) {
  if (n < 0 || n >= slides.length || n === cur.value) return
  const back = n < cur.value
  const prev = slides[cur.value]
  prev.classList.remove('active', 'enter-back')
  prev.classList.add('leaving')
  prev.classList.toggle('leave-back', back)
  setTimeout(() => prev.classList.remove('leaving', 'leave-back'), 500)
  cur.value = n
  const next = slides[n]
  next.classList.toggle('enter-back', back)
  applyStagger(next)
  next.classList.add('active')
}

function toggleFullscreen() {
  if (document.fullscreenElement) {
    document.exitFullscreen()
  } else {
    rootEl.value?.requestFullscreen?.()
  }
}

function onFullscreenChange() {
  isFullscreen.value = Boolean(document.fullscreenElement)
}

function onKey(e) {
  if (['ArrowRight', 'PageDown', ' '].includes(e.key)) {
    e.preventDefault()
    go(cur.value + 1)
  }
  if (['ArrowLeft', 'PageUp'].includes(e.key)) {
    e.preventDefault()
    go(cur.value - 1)
  }
  if (e.key === 'Home') go(0)
  if (e.key === 'End') go(slides.length - 1)
  if (e.key === 'f' || e.key === 'F') toggleFullscreen()
}

let touchX = 0
function onTouchStart(e) {
  touchX = e.touches[0].clientX
}
function onTouchEnd(e) {
  const dx = e.changedTouches[0].clientX - touchX
  if (Math.abs(dx) > 50) go(cur.value + (dx < 0 ? 1 : -1))
}
function onPointerMove(e) {
  const c = e.target.closest && e.target.closest('.card')
  if (c) {
    const r = c.getBoundingClientRect()
    c.style.setProperty('--mx', e.clientX - r.left + 'px')
    c.style.setProperty('--my', e.clientY - r.top + 'px')
  }
}

let resizeHandler = null

onMounted(() => {
  const SLIDES = buildSlides()
  slideCount.value = SLIDES.length
  SLIDES.forEach((html) => {
    const d = document.createElement('section')
    d.className = 'slide'
    d.innerHTML = html
    stage.value.appendChild(d)
  })
  slides = [...stage.value.querySelectorAll('.slide')]
  applyStagger(slides[0])
  slides[0].classList.add('active')
  rootEl.value?.focus()

  stage.value.querySelectorAll('.deck-mark').forEach((el) => {
    render(
      h(JPilotMark, {
        variant: el.dataset.variant,
        size: Number(el.dataset.size),
        tone: 'dark'
      }),
      el
    )
    mountedMarks.push(el)
  })

  window.addEventListener('keydown', onKey)
  window.addEventListener('touchstart', onTouchStart, { passive: true })
  window.addEventListener('touchend', onTouchEnd, { passive: true })
  window.addEventListener('pointermove', onPointerMove)
  document.addEventListener('fullscreenchange', onFullscreenChange)

  const cv = bgcanvas.value
  const cx = cv.getContext('2d')
  let W, H, pts, DPR
  const LINK = 150
  function resize() {
    DPR = Math.min(devicePixelRatio || 1, 2)
    W = cv.width = innerWidth * DPR
    H = cv.height = innerHeight * DPR
    cv.style.width = innerWidth + 'px'
    cv.style.height = innerHeight + 'px'
    const n = Math.min(70, Math.floor((innerWidth * innerHeight) / 22000))
    pts = Array.from({ length: n }, () => ({
      x: Math.random() * W,
      y: Math.random() * H,
      vx: (Math.random() - 0.5) * 0.18 * DPR,
      vy: (Math.random() - 0.5) * 0.18 * DPR
    }))
  }
  resize()
  resizeHandler = resize
  window.addEventListener('resize', resizeHandler)
  function frame() {
    cx.clearRect(0, 0, W, H)
    for (const p of pts) {
      p.x += p.vx
      p.y += p.vy
      if (p.x < 0 || p.x > W) p.vx *= -1
      if (p.y < 0 || p.y > H) p.vy *= -1
    }
    for (let i = 0; i < pts.length; i++) {
      for (let j = i + 1; j < pts.length; j++) {
        const a = pts[i]
        const b = pts[j]
        const dx = a.x - b.x
        const dy = a.y - b.y
        const d = Math.hypot(dx, dy)
        const lk = LINK * DPR
        if (d < lk) {
          cx.strokeStyle = 'rgba(34,211,238,' + 0.14 * (1 - d / lk) + ')'
          cx.lineWidth = DPR
          cx.beginPath()
          cx.moveTo(a.x, a.y)
          cx.lineTo(b.x, b.y)
          cx.stroke()
        }
      }
    }
    for (const p of pts) {
      cx.fillStyle = 'rgba(103,232,249,.55)'
      cx.beginPath()
      cx.arc(p.x, p.y, 1.5 * DPR, 0, 7)
      cx.fill()
    }
    raf = requestAnimationFrame(frame)
  }
  frame()
})

onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  window.removeEventListener('keydown', onKey)
  window.removeEventListener('touchstart', onTouchStart)
  window.removeEventListener('touchend', onTouchEnd)
  window.removeEventListener('pointermove', onPointerMove)
  document.removeEventListener('fullscreenchange', onFullscreenChange)
  if (document.fullscreenElement) document.exitFullscreen().catch(() => {})
  if (resizeHandler) window.removeEventListener('resize', resizeHandler)
  mountedMarks.forEach((el) => render(null, el))
  mountedMarks = []
})
</script>

<!-- Not scoped: slide markup is injected via innerHTML, so every rule is
     namespaced under .deck-page instead. -->
<style>
.deck-page {
  --bg: #070b15;
  --card: rgba(18, 28, 50, 0.62);
  --card2: rgba(24, 37, 66, 0.7);
  --line: rgba(120, 160, 210, 0.16);
  --line2: rgba(120, 160, 210, 0.3);
  --cyan: #22d3ee;
  --elec: #67e8f9;
  --ice: #a5f3fc;
  --indigo: #6366f1;
  --text: #e9f1fb;
  --mute: #9bb0cc;
  --green: #2dd4a7;
  --violet: #a78bfa;
  --blue: #60a5fa;
  --head: 'Cambria', 'Georgia', serif;
  --body: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
  position: fixed;
  inset: 0;
  z-index: 10;
  overflow: hidden;
  background: var(--bg);
  font-family: var(--body);
  color: var(--text);
}
.deck-page .deck-canvas { position: absolute; inset: 0; z-index: 0; display: block; }
.deck-page .aurora { position: absolute; border-radius: 50%; filter: blur(90px); opacity: 0.45; z-index: 0; pointer-events: none; mix-blend-mode: screen; }
.deck-page .a1 { width: 46vw; height: 46vw; left: -10vw; top: -12vw; background: radial-gradient(circle, #0e7490, transparent 65%); animation: deckDrift1 26s ease-in-out infinite; }
.deck-page .a2 { width: 40vw; height: 40vw; right: -8vw; bottom: -10vw; background: radial-gradient(circle, #312e81, transparent 65%); animation: deckDrift2 32s ease-in-out infinite; }
.deck-page .a3 { width: 34vw; height: 34vw; right: 18vw; top: -14vw; background: radial-gradient(circle, #155e75, transparent 70%); animation: deckDrift3 38s ease-in-out infinite; }
@keyframes deckDrift1 { 0%, 100% { transform: translate(0, 0) scale(1); } 50% { transform: translate(8vw, 6vh) scale(1.12); } }
@keyframes deckDrift2 { 0%, 100% { transform: translate(0, 0) scale(1); } 50% { transform: translate(-7vw, -5vh) scale(1.15); } }
@keyframes deckDrift3 { 0%, 100% { transform: translate(0, 0) scale(1); } 50% { transform: translate(-5vw, 7vh) scale(1.1); } }

.deck-page { outline: none; }
.deck-page .stage { position: absolute; inset: 0; z-index: 2; display: flex; align-items: center; justify-content: center; }
.deck-page .slide { position: absolute; inset: 0; display: none; flex-direction: column; justify-content: center; padding: clamp(28px, 5vw, 84px); --dirX: 52px; }
.deck-page .slide.active { display: flex; z-index: 2; animation: deckSlideIn 0.55s cubic-bezier(0.22, 1, 0.36, 1) both; }
.deck-page .slide.leaving { display: flex; z-index: 1; pointer-events: none; animation: deckSlideOut 0.45s cubic-bezier(0.55, 0, 0.55, 0.2) both; }
.deck-page .slide.enter-back, .deck-page .slide.leave-back { --dirX: -52px; }
@keyframes deckSlideIn {
  from { opacity: 0; transform: translateX(var(--dirX)) scale(0.985); filter: blur(6px); }
  to { opacity: 1; transform: none; filter: none; }
}
@keyframes deckSlideOut {
  from { opacity: 1; transform: none; filter: none; }
  to { opacity: 0; transform: translateX(calc(var(--dirX) * -1)) scale(0.985); filter: blur(6px); }
}
.deck-page .wrap { width: 100%; max-width: 1180px; margin: 0 auto; }

.deck-page .grid, .deck-page .split, .deck-page .steps, .deck-page .flow { perspective: 1100px; }
.deck-page .r { opacity: 0; }
.deck-page .slide.active .r { animation: deckRise 0.7s cubic-bezier(0.22, 1, 0.36, 1) both; }
.deck-page .slide.active .card.r,
.deck-page .slide.active .panel.r,
.deck-page .slide.active .fstep.r { animation-name: deckCardIn; animation-duration: 0.8s; transform-origin: 50% 100%; }
.deck-page .slide.active h1.title.r { animation-name: deckTitleIn; animation-duration: 0.75s; }
.deck-page .slide.active .eyebrow.r { animation-name: deckEyebrowIn; animation-duration: 0.65s; }
@keyframes deckRise {
  from { opacity: 0; transform: translateY(26px); filter: blur(6px); }
  to { opacity: 1; transform: none; filter: none; }
}
@keyframes deckCardIn {
  from { opacity: 0; transform: perspective(900px) translateY(36px) rotateX(10deg) scale(0.96); filter: blur(5px); }
  65% { filter: none; }
  to { opacity: 1; transform: none; filter: none; }
}
@keyframes deckTitleIn {
  from { opacity: 0; transform: translateY(24px); clip-path: inset(0 0 100% 0); }
  to { opacity: 1; transform: none; clip-path: inset(-10% 0 -12% 0); }
}
@keyframes deckEyebrowIn {
  from { opacity: 0; transform: translateX(-20px); letter-spacing: 0.45em; }
  to { opacity: 1; transform: none; letter-spacing: 0.22em; }
}

.deck-page .eyebrow { font-size: 0.82rem; font-weight: 700; letter-spacing: 0.22em; text-transform: uppercase; color: var(--cyan); margin-bottom: 0.7rem; display: flex; align-items: center; gap: 0.6rem; }
.deck-page .eyebrow::before { content: ''; width: 30px; height: 2px; background: repeating-linear-gradient(90deg, var(--cyan) 0 5px, transparent 5px 10px); animation: deckFlow 1.1s linear infinite; }
@keyframes deckFlow { to { background-position: 10px 0; } }
.deck-page h1.title { font-family: var(--head); font-weight: 700; font-size: clamp(1.7rem, 3.4vw, 2.85rem); line-height: 1.1; color: #fff; margin-bottom: 1.4rem; letter-spacing: -0.01em; }
.deck-page .lead { color: var(--mute); font-size: clamp(0.95rem, 1.25vw, 1.12rem); line-height: 1.5; max-width: 60ch; }

.deck-page .grid { display: grid; gap: 18px; }
.deck-page .g2 { grid-template-columns: 1fr 1fr; }
.deck-page .g3 { grid-template-columns: repeat(3, 1fr); }
.deck-page .g4 { grid-template-columns: repeat(4, 1fr); }
.deck-page .card { background: var(--card); border: 1px solid var(--line); border-radius: 18px; padding: 22px; backdrop-filter: blur(10px); position: relative; overflow: hidden; transition: transform 0.35s, border-color 0.35s, box-shadow 0.35s; }
.deck-page .card:hover { transform: translateY(-4px); border-color: var(--line2); box-shadow: 0 18px 50px -20px rgba(34, 211, 238, 0.45); }
.deck-page .card::after { content: ''; position: absolute; inset: 0; background: radial-gradient(420px circle at var(--mx, 50%) var(--my, 0%), rgba(103, 232, 249, 0.1), transparent 40%); opacity: 0; transition: opacity 0.4s; }
.deck-page .card:hover::after { opacity: 1; }
.deck-page .ico { width: 50px; height: 50px; border-radius: 13px; display: grid; place-items: center; background: rgba(8, 16, 30, 0.7); border: 1px solid rgba(34, 211, 238, 0.5); margin-bottom: 14px; flex: none; }
.deck-page .ico svg { width: 24px; height: 24px; stroke: var(--elec); fill: none; stroke-width: 1.8; }
.deck-page .ico.g { border-color: rgba(45, 212, 167, 0.55); }
.deck-page .ico.g svg { stroke: var(--green); }
.deck-page .card h3 { font-family: var(--head); font-size: 1.06rem; color: #fff; margin-bottom: 0.4rem; font-weight: 700; }
.deck-page .card p { color: var(--mute); font-size: 0.86rem; line-height: 1.45; }
.deck-page .card.row { display: flex; gap: 16px; align-items: flex-start; padding: 18px 20px; }
.deck-page .card.row .ico { margin-bottom: 0; }
.deck-page .card.row .tx h3 { margin-bottom: 0.25rem; }

.deck-page .chips { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 1.3rem; }
.deck-page .chip { padding: 0.5rem 0.95rem; border: 1px solid var(--line2); border-radius: 999px; background: var(--card2); color: var(--ice); font-size: 0.84rem; backdrop-filter: blur(6px); }

.deck-page .ld-cursor::after { color: var(--cur, currentColor); }
.deck-page .brandrow { display: flex; align-items: center; gap: 18px; margin-bottom: 2.4rem; }
.deck-page .brandrow .bn { font-size: 2.2rem; letter-spacing: 0.06em; }
.deck-page .hero { font-family: var(--head); font-weight: 700; line-height: 1.04; letter-spacing: -0.02em; }
.deck-page .hero .l1 { display: block; font-size: clamp(1.6rem, 3.1vw, 2.4rem); color: var(--ice); font-style: italic; font-weight: 400; }
.deck-page .hero .l2 { display: block; font-size: clamp(2.8rem, 6.6vw, 5.4rem); }
.deck-page .grad { background: linear-gradient(100deg, #fff 20%, var(--elec) 45%, var(--indigo) 60%, #fff 80%); background-size: 200% auto; -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; animation: deckShine 6s linear infinite; }
@keyframes deckShine { to { background-position: 200% center; } }

.deck-page .stat { font-family: var(--head); font-weight: 700; font-size: clamp(2.2rem, 4.4vw, 3.4rem); background: linear-gradient(180deg, #fff, var(--cyan)); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.deck-page .statlbl { color: var(--mute); font-size: 0.84rem; line-height: 1.4; margin-top: 0.5rem; }
.deck-page .badge { display: inline-block; padding: 0.28rem 0.8rem; border-radius: 999px; font-size: 0.74rem; font-weight: 700; letter-spacing: 0.04em; border: 1px solid currentColor; margin-top: 0.5rem; }

.deck-page .col h2, .deck-page .tier h2 { font-family: var(--head); font-size: 1.35rem; color: #fff; margin-bottom: 0.2rem; }
.deck-page .pill { display: inline-block; font-family: var(--head); font-weight: 700; letter-spacing: 0.18em; font-size: 0.82rem; padding: 0.34rem 0.9rem; border-radius: 999px; border: 1px solid currentColor; margin-bottom: 1rem; }
.deck-page .li { display: flex; gap: 0.6rem; align-items: flex-start; color: var(--text); font-size: 0.9rem; line-height: 1.4; margin: 0.5rem 0; }
.deck-page .li .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--cyan); margin-top: 0.45rem; flex: none; }
.deck-page .li svg { width: 16px; height: 16px; stroke: var(--cyan); fill: none; stroke-width: 2.4; margin-top: 0.15rem; flex: none; }
.deck-page .tagm { font-size: 0.74rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; margin: 0.1rem 0 1rem; }
.deck-page .hr { height: 1px; background: var(--line); margin: 0.7rem 0 1rem; }

.deck-page .split { display: grid; grid-template-columns: 1fr 1fr; gap: 26px; align-items: start; }
.deck-page .panel { background: var(--card2); border: 1px solid var(--line); border-radius: 20px; padding: 24px; backdrop-filter: blur(10px); }
.deck-page .panel.glow { border-color: rgba(34, 211, 238, 0.5); box-shadow: 0 0 60px -25px rgba(34, 211, 238, 0.6) inset; }
.deck-page .ptitle { font-size: 0.74rem; font-weight: 700; letter-spacing: 0.18em; text-transform: uppercase; color: var(--cyan); margin-bottom: 0.7rem; }
.deck-page .modrow { display: flex; align-items: center; gap: 0.7rem; padding: 0.62rem 0.85rem; border: 1px solid var(--line); border-radius: 11px; margin-bottom: 0.55rem; background: rgba(15, 22, 40, 0.5); font-size: 0.9rem; color: var(--text); }
.deck-page .modrow.new { border-style: dashed; border-color: var(--cyan); color: var(--cyan); font-weight: 600; }
.deck-page .modrow svg { width: 17px; height: 17px; stroke: var(--ice); fill: none; stroke-width: 2; }
.deck-page .modrow.new svg { stroke: var(--elec); }

.deck-page .steps { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; }
.deck-page .step { position: relative; }
.deck-page .step .n { font-family: var(--head); font-weight: 700; font-size: 1.5rem; color: var(--cyan); }
.deck-page .step .chev { position: absolute; right: -13px; top: 50%; color: var(--line2); font-size: 1.2rem; }

.deck-page .flow { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; margin-top: 1.6rem; }
.deck-page .fstep { flex: 1; min-width: 140px; max-width: 185px; background: var(--card); border: 1px solid var(--line); border-radius: 13px; padding: 14px; backdrop-filter: blur(8px); }
.deck-page .fstep .n { font-family: var(--head); font-weight: 700; color: var(--cyan); font-size: 1.05rem; }
.deck-page .fstep p { font-size: 0.82rem; color: var(--text); margin-top: 0.25rem; line-height: 1.3; }
.deck-page .playbtn { width: 96px; height: 96px; border-radius: 50%; margin: 0 auto 1.4rem; display: grid; place-items: center; background: var(--card); border: 1.5px solid var(--cyan); box-shadow: 0 0 50px -10px rgba(34, 211, 238, 0.7); animation: deckPulse 2.6s ease-in-out infinite; }
.deck-page .playbtn svg { width: 34px; height: 34px; fill: var(--elec); stroke: none; margin-left: 5px; }
@keyframes deckPulse { 0%, 100% { box-shadow: 0 0 50px -14px rgba(34, 211, 238, 0.6); } 50% { box-shadow: 0 0 70px -6px rgba(99, 102, 241, 0.9); } }

.deck-page .codebar { margin-top: 1.4rem; background: #081020; border: 1px solid var(--line2); border-radius: 12px; padding: 0.95rem 1.2rem; font-family: 'JetBrains Mono', 'SFMono-Regular', Consolas, monospace; font-size: 0.95rem; color: var(--ice); }
.deck-page .codebar .pmpt { color: var(--mute); }
.deck-page .note { margin-top: 1.5rem; text-align: center; color: #7f93b3; font-size: 0.86rem; font-style: italic; }
.deck-page .credit { display: flex; align-items: center; gap: 0.7rem; margin-bottom: 0.4rem; }
.deck-page .closewrap { text-align: center; }

.deck-page .chrome { position: absolute; z-index: 5; left: 0; right: 0; bottom: 0; display: flex; align-items: center; justify-content: space-between; padding: 14px 26px; pointer-events: none; }
.deck-page .brandmini { display: flex; align-items: center; gap: 0.5rem; color: #6f84a3; font-size: 0.78rem; }
.deck-page .brand-mini-name { color: #8fa6c4; font-size: 0.85rem; }
.deck-page .dots { display: flex; gap: 7px; pointer-events: auto; }
.deck-page .dots b { width: 8px; height: 8px; border-radius: 50%; background: rgba(150, 180, 215, 0.3); cursor: pointer; transition: all 0.3s; }
.deck-page .dots b.on { background: linear-gradient(90deg, var(--cyan), var(--indigo)); width: 22px; border-radius: 5px; }
.deck-page .chrome-end { display: flex; align-items: center; gap: 0.7rem; pointer-events: auto; }
.deck-page .counter { color: var(--mute); font-size: 0.8rem; font-variant-numeric: tabular-nums; }
.deck-page .fs-btn { width: 34px; height: 34px; border-radius: 50%; border: 1px solid var(--line2); background: rgba(12, 20, 36, 0.6); color: var(--ice); display: grid; place-items: center; cursor: pointer; backdrop-filter: blur(8px); transition: 0.3s; }
.deck-page .fs-btn:hover { border-color: var(--cyan); background: rgba(34, 211, 238, 0.18); }
.deck-page .fs-btn svg { width: 16px; height: 16px; stroke: currentColor; fill: none; stroke-width: 2; stroke-linecap: round; }
.deck-page .deck-progress { position: absolute; top: 0; left: 0; height: 3px; background: linear-gradient(90deg, var(--cyan), var(--indigo)); z-index: 6; transition: width 0.5s; }
.deck-page .deck-nav { position: absolute; z-index: 5; top: 50%; transform: translateY(-50%); width: 46px; height: 46px; border-radius: 50%; border: 1px solid var(--line2); background: rgba(12, 20, 36, 0.6); color: var(--ice); display: grid; place-items: center; cursor: pointer; backdrop-filter: blur(8px); transition: 0.3s; }
.deck-page .deck-nav:hover { border-color: var(--cyan); background: rgba(34, 211, 238, 0.18); }
.deck-page .deck-nav svg { width: 20px; height: 20px; stroke: currentColor; fill: none; stroke-width: 2; }
.deck-page .deck-prev { left: 18px; }
.deck-page .deck-next { right: 18px; }
.deck-page .hint { position: absolute; z-index: 5; bottom: 54px; left: 50%; transform: translateX(-50%); font-size: 0.74rem; color: #64769a; animation: deckFade 5s forwards; }
@keyframes deckFade { 0%, 70% { opacity: 1; } 100% { opacity: 0; } }

@media (max-width: 820px) {
  .deck-page .g2, .deck-page .g3, .deck-page .g4, .deck-page .split, .deck-page .steps { grid-template-columns: 1fr; }
  .deck-page .steps { gap: 10px; }
  .deck-page .deck-nav { display: none; }
}
@media (prefers-reduced-motion: reduce) {
  .deck-page .aurora, .deck-page .grad, .deck-page .playbtn, .deck-page .eyebrow::before { animation: none; }
  .deck-page .r { opacity: 1; }
  .deck-page .slide.active, .deck-page .slide.leaving, .deck-page .slide.active .r { animation: none !important; }
  .deck-page .slide.leaving { display: none; }
}
</style>
