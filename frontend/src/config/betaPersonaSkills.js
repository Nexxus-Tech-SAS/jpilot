/**
 * Starter skills shown on the Chat Beta welcome after a persona is chosen.
 */

/** @typedef {{ id: string, label: string, description: string, icon: string, prompt: string }} BetaPersonaSkill */

/** @type {Record<string, BetaPersonaSkill[]>} */
export const BETA_PERSONA_SKILLS = {
  architect: [
    {
      id: 'deployment',
      label: 'Plan a deployment',
      description: 'Greenfield or expansion — topology, VIPs, HA, and a design document for Operator.',
      icon: 'pi pi-compass',
      prompt:
        'I am planning a new NetScaler deployment from scratch. Guide me through structured discovery and a formal design document.'
    },
    {
      id: 'change-control',
      label: 'Change control',
      description: 'Maintenance window scope, rollback plan, and an approval-ready change record.',
      icon: 'pi pi-file-edit',
      prompt: 'I need a change control record for a maintenance window on our NetScaler environment.'
    },
    {
      id: 'feature-config',
      label: 'Feature configuration',
      description: 'Design a new capability — Gateway, AAA, GSLB, WAF, or app delivery.',
      icon: 'pi pi-sliders-h',
      prompt: 'Help me design a new NetScaler feature or capability for our environment.'
    }
  ],
  operator: [
    {
      id: 'implement-design',
      label: 'Implement a design',
      description: 'Execute an Architect deliverable — attach a design .md or describe what to build.',
      icon: 'pi pi-file-import',
      prompt:
        'Implement a design on the connected appliance. I will attach or paste the design document — start with the Handoff for Operator section and use jpilot-form for any TBD values.'
    },
    {
      id: 'create-lb',
      label: 'Create a load balancer',
      description: 'Guided VIP, service type, backends, and monitors — forms before CLI writes.',
      icon: 'pi pi-sitemap',
      prompt:
        'Help me create a new load balancing virtual server on the connected appliance. Use jpilot-form to gather VIP, port, backends, and monitor details before applying changes.'
    },
    {
      id: 'apply-change',
      label: 'Apply a change',
      description: 'Targeted config update — networking, policies, SSL, or app delivery on the appliance.',
      icon: 'pi pi-cog',
      prompt:
        'I need to apply a configuration change on the connected appliance. Ask what is missing with jpilot-form, search CLI reference, then configure and save.'
    }
  ],
  analyst: [
    {
      id: 'triage-incident',
      label: 'Triage an incident',
      description: 'Describe symptoms — read-first checks, logs, and a structured findings summary.',
      icon: 'pi pi-exclamation-circle',
      prompt:
        'I need help triaging an issue on the connected appliance. I will describe symptoms — run read-first diagnostics and summarize likely causes before any changes.'
    },
    {
      id: 'health-check',
      label: 'Health & performance',
      description: 'Version, HA state, CPU/memory, LB counts, and obvious problems at a glance.',
      icon: 'pi pi-heart',
      prompt:
        'Quick health summary of the connected appliance: version, HA state, IP summary, LB vserver count, CPU and memory, and any obvious issues.'
    },
    {
      id: 'connectivity',
      label: 'Test connectivity',
      description: 'Ping, traceroute, or TCP port reachability from the appliance to a target you name.',
      icon: 'pi pi-wifi',
      prompt:
        'Run connectivity diagnostics from the connected appliance — ping or TCP port reachability to a backend I will specify. Report results only; no configuration changes.'
    }
  ]
}

export function getBetaPersonaSkills(roleId) {
  return BETA_PERSONA_SKILLS[roleId] || []
}
