export const PRICING_PLAN_ORDER = ['free', 'enterprise', 'enterprise-pro']

export const PRICING_PLANS = [
  {
    id: 'free',
    name: 'Early Access',
    shortName: 'Early',
    tagline: 'Everything you need to start',
    priceLabel: null,
    priceDetail: 'Unlimited · on-prem',
    accent: null,
    highlighted: false,
    ctaLabel: null,
    ctaHref: null,
    ctaDisabled: true
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    shortName: 'Ent.',
    tagline: 'Identity, premium blueprints, and guided ADC rollout',
    priceLabel: null,
    priceDetail: 'Custom quote',
    accent: '#3b82f6',
    highlighted: false,
    ctaLabel: null,
    ctaHref: null,
    ctaDisabled: false
  },
  {
    id: 'enterprise-pro',
    name: 'Enterprise Pro',
    shortName: 'Ent. Pro',
    tagline: 'Customize personas & blueprints, with on-demand expert support',
    priceLabel: null,
    priceDetail: 'Support Credits included',
    accent: '#8b5cf6',
    highlighted: false,
    ctaLabel: null,
    ctaHref: null,
    ctaDisabled: false
  }
]

export function planAccentVars(plan) {
  if (!plan?.accent) return undefined
  return {
    '--plan-accent': plan.accent,
    '--tier-accent': plan.accent,
    '--tier-accent-soft': `color-mix(in srgb, ${plan.accent} 14%, transparent)`,
    '--card-accent': plan.accent
  }
}

export const PLAN_FEATURE_FOOTNOTES = {
  'llm-data-residency': {
    marker: '*',
    text:
      'Data residency and non-exfiltration assurances apply solely when inference is directed to locally hosted or privately deployed models operating within infrastructure under your organization\'s administrative control. Deployments utilizing third-party public cloud LLM services remain subject to the applicable data handling, residency, and subprocessors policies of the selected provider.'
  }
}

export const PLAN_FEATURE_GROUPS = [
  {
    id: 'base',
    title: 'Early Access includes',
    subtitle: 'Included in every plan',
    minPlan: 'free',
    features: [
      'Unlimited NetScaler appliances',
      'Password login and optional passkeys (WebAuthn)',
      {
        text: 'Multi-vendor LLM connectivity — public cloud, private, and on-premises endpoints (AWS, Azure)*',
        footnoteId: 'llm-data-residency'
      },
      'JPilot copilot with MCP — Next-Gen API and SSH CLI',
      'JPilot chat — Architect, Operator, and Analyst roles with appliance-aware tooling',
      'Diagnostics, SSL CSR tools, and admin user roles',
      'Encrypted appliance credentials — never sent to the LLM',
      'On-prem Docker — data stays in your network'
    ]
  },
  {
    id: 'enterprise',
    title: 'Enterprise adds',
    subtitle: 'Everything above, plus',
    minPlan: 'enterprise',
    features: [
      'SSO for JPilot — LDAP, Entra ID, Okta, or Google',
      'Custom infrastructure personalization — scope enabled vendor technologies to your environment (e.g., Cisco and Check Point only)',
      'Engineer-led WAF, GSLB, SSL, and CS/LB workflows across supported ADC platforms (e.g., NetScaler and F5 BIG-IP)',
      'Premium Blueprint Library — browse and install entitled premium skills, knowledge packs, and standard persona bundles from Nexxus',
      'HA deployment, backup, and upgrade assistance',
      'Email and ticket support (business hours)'
    ]
  },
  {
    id: 'enterprise-pro',
    title: 'Enterprise Pro adds',
    subtitle: 'Everything above, plus',
    minPlan: 'enterprise-pro',
    features: [
      'Advanced WAF programs — OWASP, bot management, tuning, security hardening, and security health checks (Support Credits)',
      'Stack Calibration Studio — customize personas and blueprints; encode org-specific standards, workflows, and operational knowledge (Support Credits)',
      'Custom JPilot personas — install specialized personas selectable in chat alongside Architect, Operator, and Analyst',
      'On-demand support via Support Credits — remote SME engineers when you need them',
      'Credits for migrations, production changes, and advanced implementations',
      'Dedicated architect and priority support channel',
      'Slack notifications — operational alerts and workflow updates routed to your team channels',
      'F5-to-NetScaler and multicloud ADC migration playbooks',
      'Production runbooks and change-window execution support'
    ]
  }
]

export const PLATFORM_HIGHLIGHTS = [
  {
    icon: 'pi pi-gift',
    title: 'Early access',
    description: 'Full platform access. No appliance or user limits.'
  },
  {
    icon: 'pi pi-th-large',
    title: 'Unlimited',
    description: 'As many appliances and LLM providers as you need (e.g., NetScaler).'
  },
  {
    icon: 'pi pi-server',
    title: 'On-premises',
    description: 'Docker on your network. Your data never leaves.'
  },
  {
    icon: 'pi pi-lock',
    title: 'Secure',
    description: 'Encrypted secrets, JWT sessions, optional passkeys, TLS-ready.'
  },
  {
    icon: 'pi pi-chart-line',
    title: 'Monitorable',
    description: 'Standard containers — plug into your existing observability stack.'
  },
  {
    icon: 'pi pi-shield',
    title: 'Best practices',
    description: 'Authenticated API access and least-privilege user roles.'
  }
]

function planRank(planId) {
  const index = PRICING_PLAN_ORDER.indexOf(planId)
  return index === -1 ? -1 : index
}

export function planIncludesGroup(planId, group) {
  return planRank(planId) >= planRank(group.minPlan)
}

export function groupsForPlan(planId) {
  return PLAN_FEATURE_GROUPS.filter((group) => planIncludesGroup(planId, group))
}

export function featureKey(feature) {
  return typeof feature === 'string' ? feature : feature.text
}

export function featureLabel(feature) {
  return typeof feature === 'string' ? feature : feature.text
}

export function featureFootnoteId(feature) {
  return typeof feature === 'object' && feature ? feature.footnoteId ?? null : null
}

export function comparisonFootnotes() {
  const ids = new Set()
  for (const group of PLAN_FEATURE_GROUPS) {
    for (const feature of group.features) {
      const footnoteId = featureFootnoteId(feature)
      if (footnoteId) ids.add(footnoteId)
    }
  }
  return [...ids]
    .map((id) => PLAN_FEATURE_FOOTNOTES[id])
    .filter(Boolean)
}
