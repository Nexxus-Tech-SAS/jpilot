# Generic NetScaler Design and Configuration Document Reference

## Purpose

This Markdown file is a sanitized and optimized reference template for generating NetScaler design and configuration documents with AI.

It consolidates design-document patterns, configuration-document patterns, Citrix Gateway / MFA design patterns, SDX migration patterns, VPX provisioning patterns, management/monitoring sections, backup/restore guidance, and operational validation sections into one generic structure.

This file must be treated as a **reference template**, not as a customer-specific document.

---

## Sanitization Rules

When using customer design or configuration material as input, remove or replace all confidential information before generating a final document.

### Replace These Values

| Confidential Value Type | Replace With |
|---|---|
| Customer name | `<CUSTOMER_NAME>` |
| Customer industry | `<CUSTOMER_INDUSTRY>` |
| Datacenter name | `<PRIMARY_DATACENTER>`, `<SECONDARY_DATACENTER>` |
| Site name | `<SITE_A>`, `<SITE_B>` |
| Internal domain | `<INTERNAL_DOMAIN>` |
| External domain | `<EXTERNAL_DOMAIN>` |
| FQDN | `<APP_FQDN>`, `<GATEWAY_FQDN>`, `<STOREFRONT_FQDN>` |
| Public IP | `<PUBLIC_VIP>` |
| Private IP | `<PRIVATE_IP>` |
| NSIP | `<ADC_NODE_1_NSIP>`, `<ADC_NODE_2_NSIP>` |
| SNIP | `<SNIP_DATA_NETWORK>` |
| VIP | `<APPLICATION_VIP>`, `<GATEWAY_VIP>`, `<STOREFRONT_VIP>` |
| Server hostname | `<SERVER_NAME_1>`, `<SERVER_NAME_2>` |
| User group | `<AUTHORIZED_AD_GROUP>` |
| Bind DN | `<LDAP_BIND_DN>` |
| Password / secret / key | `<SECRET_VALUE>` |
| Certificate name | `<CERTKEY_NAME>` |
| Email address | `<EMAIL_ADDRESS>` |
| Named individual | `<PROJECT_RESOURCE>` |
| Legal / copyright text | Remove unless explicitly required |
| Revision author | `<AUTHOR>` |
| Exact dates | `<DATE>` or generic project phase |

### Do Not Include

- Real customer names.
- Real IP addresses.
- Real domains or FQDNs.
- Real server hostnames.
- Real usernames, bind DNs, emails, or passwords.
- Real AD group names.
- Real certificate CN/SAN values.
- Real ADM/Console tenant details.
- Real legal disclaimers from previous engagements.
- Real diagrams containing customer labels, topology names, IPs, or logos.

---

# Optimized Document Structure

## 1. Executive Summary

### 1.1 Project Overview

`<CUSTOMER_NAME>` requires a NetScaler solution to provide secure, resilient, and centrally managed application delivery services for internal and/or external users.

The solution may include one or more of the following components:

- NetScaler ADC VPX or MPX appliances.
- NetScaler SDX appliances hosting VPX instances.
- NetScaler Gateway / Unified Gateway.
- StoreFront load balancing.
- LDAP / LDAPS / DNS load balancing.
- AAA / nFactor / MFA integration.
- NetScaler Console / ADM for monitoring, reporting, licensing, backups, and centralized management.
- Firmware migration or upgrade activities.
- Security hardening for SSL/TLS, HTTP settings, logging, and operational controls.

This document provides a reusable design and configuration framework for documenting the target-state architecture, configuration decisions, migration approach, validation plan, operational handover, and support model.

---

### 1.2 Project Scope

The scope of the engagement should be clearly stated.

Example scope items:

- Deploy or document a NetScaler ADC high availability pair.
- Deploy or document NetScaler SDX appliances and VPX instances.
- Migrate existing VPX instances from legacy SDX or legacy ADC appliances.
- Upgrade NetScaler SDX, VPX, or Console/ADM firmware.
- Configure Citrix Gateway or Unified Gateway for secure remote access.
- Integrate MFA using SAML, RADIUS, LDAP, or nFactor.
- Configure StoreFront load balancing.
- Configure LDAPS and/or DNS load balancing.
- Configure SSL profiles and cipher groups.
- Configure monitoring, syslog, SNMP, backups, and operational diagnostics.
- Provide design risks, recommendations, next steps, and validation criteria.

Out-of-scope items should also be documented.

Example out-of-scope items:

- Application code changes.
- Backend application remediation.
- Firewall policy implementation by third-party teams.
- DNS delegation changes by third-party teams.
- Certificate procurement by third-party teams.
- Identity provider tenant configuration outside the agreed scope.
- Production cutover outside the approved change window.

---

### 1.3 Project Goals

Document the business and technical goals.

Example:

| Goal ID | Goal | Description | Success Criteria |
|---|---|---|---|
| G-01 | High Availability | Provide resilient ADC services using an active/passive HA pair. | HA state is healthy and failover has been tested. |
| G-02 | Secure Remote Access | Provide secure Citrix Gateway access for users. | Users can authenticate and launch resources successfully. |
| G-03 | MFA Integration | Integrate MFA using SAML, RADIUS, LDAP, or nFactor. | Required user groups complete MFA successfully. |
| G-04 | Application Load Balancing | Load balance StoreFront, LDAP/LDAPS, DNS, or application services. | vServers and backend services are UP and monitored. |
| G-05 | Security Hardening | Apply TLS, HTTP, logging, and access-control hardening. | SSL profile, ciphers, HTTP protections, and logs are validated. |
| G-06 | Migration / Upgrade | Migrate or upgrade NetScaler components safely. | Backup, failover, validation, and rollback plans are documented. |
| G-07 | Operational Readiness | Document support procedures, backups, diagnostics, and monitoring. | Operations team has clear runbook sections and commands. |

---

### 1.4 Design Risks and Recommendations

Document known risks, unknowns, dependencies, and mitigations.

| Risk ID | Risk / Unknown | Impact | Recommendation | Owner | Status |
|---|---|---|---|---|---|
| R-01 | Identity provider registration is incomplete for some users. | Authentication failures during MFA rollout. | Validate user registration before migration. | `<OWNER>` | Open |
| R-02 | HA propagation or file synchronization may fail after migration. | Config mismatch after failover. | Validate HA sync, disable propagation only during controlled migration steps, then re-enable and verify. | `<OWNER>` | Open |
| R-03 | Legacy policies may block firmware upgrade compatibility. | Upgrade failure or unsupported configuration. | Convert classic policies to advanced policies before upgrade. | `<OWNER>` | Open |
| R-04 | External inspection devices may alter Gateway or nFactor traffic. | Login or session failures. | Validate bypass/inspection exceptions or design separate virtual servers if required. | `<OWNER>` | Open |
| R-05 | Certificate chain or TLS profile is incomplete. | Browser warnings or failed client connections. | Validate cert chain, expiry, TLS versions, and cipher compatibility. | `<OWNER>` | Open |
| R-06 | Firewall or routing dependencies are incomplete. | Backend reachability failures. | Validate SNIP-to-backend connectivity, routes, VLAN tagging, ACLs, and NAT. | `<OWNER>` | Open |

---

### 1.5 Next Steps

#### Short Term: 2-4 Weeks

- Complete functional validation.
- Validate authentication flows.
- Validate Citrix Gateway login and resource launch.
- Validate StoreFront, LDAP/LDAPS, DNS, and application load balancing.
- Confirm HA failover and failback.
- Confirm monitoring, syslog, SNMP, and backup jobs.
- Complete security validation and certificate review.
- Update operational runbooks.

#### Long Term: 3+ Months

- Maintain firmware lifecycle and patch cadence.
- Review SSL Labs / TLS posture periodically.
- Review NetScaler Console/ADM reports and alerts.
- Convert remaining legacy policy syntax if present.
- Expand automation and configuration drift checks.
- Review capacity, throughput, SSL TPS, and license usage.
- Review disaster recovery and multi-site designs.

---

# 2. Design

## 2.1 Document Purpose

This document provides architecture and engineering teams with a generic design and configuration reference for NetScaler deployments.

It can also be repurposed as:

- A service support document.
- A migration design document.
- A configuration baseline document.
- An operational handover document.
- A validation checklist.
- An AI reference document for generating future NetScaler design deliverables.

---

## 2.2 Deliverable Overview

The final design deliverable should describe:

- Current-state architecture.
- Target-state architecture.
- Configuration decisions.
- Network design.
- High availability design.
- Application delivery design.
- Authentication and MFA design.
- Load balancing design.
- Security design.
- Monitoring and management design.
- Migration or upgrade strategy.
- Validation and rollback plan.
- Operational support procedures.

---

## 2.3 Document Structure

| Section | Description |
|---|---|
| Executive Summary | Business and technical overview, goals, risks, and next steps. |
| Design | Conceptual architecture, target-state design, platform sizing, dependencies, and assumptions. |
| Configuration | Detailed settings, platform parameters, HA, networking, authentication, LB, Gateway, AppExpert, security, and monitoring. |
| Migration / Upgrade | Migration sequence, firmware lifecycle, cutover, validation, and rollback. |
| Management | Console/ADM, backups, restore, logs, diagnostic tools, and operational processes. |
| Appendix | Training, certifications, reference links, diagrams, revision history, and placeholder tables. |

---

## 2.4 Conceptual Architecture

### 2.4.1 Architecture Overview

Insert a sanitized diagram that shows the logical placement of NetScaler components.

The diagram should include, where applicable:

- Users.
- Firewall or perimeter boundary.
- NetScaler ADC VPX or MPX pair.
- NetScaler SDX appliances, if applicable.
- VPX instances hosted on SDX, if applicable.
- Internal and external networks.
- Management network.
- StoreFront servers.
- Delivery Controllers / XML brokers.
- LDAP/LDAPS servers.
- DNS servers.
- MFA provider.
- SAML Identity Provider.
- RADIUS servers.
- NetScaler Console / ADM.
- Syslog / SIEM.
- SNMP monitoring.
- Backend application servers.

Do not include real customer names, IPs, hostnames, or logos.

### 2.4.2 Diagram Placeholder

```text
[Users]
   |
[Internet / Internal Network]
   |
[Firewall / Edge Security]
   |
[NetScaler Gateway / Content Switching / LB VIP]
   |
[NetScaler ADC HA Pair]
   |             |               |
[StoreFront]  [LDAP/LDAPS]    [Applications]
   |
[Citrix Virtual Apps and Desktops / DaaS / Resource Location]

[NetScaler Console / ADM] --> Monitoring, licensing, backups, analytics
[Syslog / SIEM]           --> Security and operational logs
[SNMP Platform]           --> Alerts and metrics
```

---

## 2.5 Overall Design

### 2.5.1 Platform Design Summary

| Design Area | Target Decision |
|---|---|
| Deployment Type | `<VPX_HA_PAIR>`, `<MPX_HA_PAIR>`, or `<SDX_WITH_VPX_INSTANCES>` |
| Datacenters / Sites | `<PRIMARY_SITE>`, `<SECONDARY_SITE>` |
| ADC Form Factor | `<VPX / MPX / SDX>` |
| HA Model | Active/Passive HA |
| Firmware Version | `<TARGET_VERSION_AND_BUILD>` |
| License Edition | `<LICENSE_EDITION>` |
| License Model | `<LOCAL / POOLED / CONSOLE_MANAGED>` |
| Traffic Model | One-arm or two-arm |
| Data Interfaces | `<INTERFACE_LIST>` |
| Management Interfaces | `<MGMT_INTERFACE_LIST>` |
| VLAN Strategy | Tagged or access VLANs |
| Routing Strategy | Default route, static routes, PBR, or no routing |
| Monitoring | NetScaler Console/ADM, Syslog, SNMP |
| Backup Strategy | ADM/Console backups plus manual `/nsconfig` backup |
| Security Model | TLS hardening, AAA, MFA, audit logging, least privilege |

---

### 2.5.2 Component Sizing Summary

| Component | Version | Description | Quantity | CPU | RAM | Storage | Notes |
|---|---|---|---:|---:|---:|---:|---|
| NetScaler ADC VPX | `<VERSION>` | ADC virtual appliance | `<QTY>` | `<CPU>` | `<RAM>` | `<STORAGE>` | Size based on throughput, SSL TPS, and feature usage. |
| NetScaler SDX | `<VERSION>` | SDX hardware hosting VPX instances | `<QTY>` | `<CPU>` | `<RAM>` | N/A | Include port, license, and instance capacity. |
| NetScaler Console / ADM | `<VERSION>` | Central management, monitoring, backup, licensing | `<QTY>` | `<CPU>` | `<RAM>` | `<STORAGE>` | Cloud or on-prem deployment. |
| StoreFront | `<VERSION>` | Citrix StoreFront servers | `<QTY>` | `<CPU>` | `<RAM>` | `<STORAGE>` | Load balanced by ADC. |
| FAS | `<VERSION>` | Federated Authentication Service | `<QTY>` | `<CPU>` | `<RAM>` | `<STORAGE>` | Required for selected federated auth designs. |
| MFA Provider | `<VERSION>` | RADIUS/SAML/MFA provider | `<QTY>` | N/A | N/A | N/A | Cloud or on-prem integration. |
| Syslog/SIEM | `<VERSION>` | Log collection and alerting | `<QTY>` | `<CPU>` | `<RAM>` | `<STORAGE>` | Retention based on policy. |

---

# 3. Configuration Reference

## 3.1 Configuration Overview

NetScaler ADC acts as a full proxy. Client connections terminate on the ADC and are re-initiated toward backend services through SNIP or configured source address behavior.

The configuration section should document:

- Platform hardware and firmware.
- SDX settings, if applicable.
- VPX provisioning details.
- Network interfaces, channels, VLANs, routes, PBRs, and IP addresses.
- High availability settings.
- Modes and features.
- TCP and HTTP parameters.
- Authentication and MFA.
- Load balancing.
- AppExpert policies.
- AAA and nFactor flows.
- Gateway virtual servers.
- SSL profiles and cipher groups.
- Monitoring, logging, and alerts.

---

## 3.2 NetScaler SDX Platform Design

Use this section only when SDX appliances are in scope.

### 3.2.1 SDX Hardware Specifications

| Attribute | Value |
|---|---|
| Platform | NetScaler SDX |
| Model | `<SDX_MODEL>` |
| Memory | `<MEMORY>` |
| Data Ports | `<DATA_PORTS>` |
| Management Ports | `<MGMT_PORTS>` |
| LOM Port | `<LOM_PORT_STATUS>` |
| Power Supplies | `<POWER_SUPPLY_COUNT>` |
| License Model | `<LICENSE_MODEL>` |
| Maximum Throughput | `<THROUGHPUT>` |
| Maximum Instances | `<MAX_INSTANCES>` |

### 3.2.2 SDX Firmware

| Setting | Value |
|---|---|
| SDX Firmware Release | `<SDX_MAJOR_VERSION>` |
| Build | `<SDX_BUILD>` |
| Target Firmware | `<TARGET_SDX_BUILD>` |
| Upgrade Method | `<SINGLE_BUNDLE / PLATFORM_ONLY / OTHER>` |
| Reboot Required | Yes |
| VPX Impact | Document whether VPX instances reboot or fail over. |

### 3.2.3 SDX Network Topology

| Network | Interface / Channel | Mode | VLAN | Description |
|---|---|---|---|---|
| Management | `<MGMT_INTERFACE>` | Access / Tagged | `<MGMT_VLAN>` | SDX management. |
| Production | `<DATA_CHANNEL>` | LACP / Static / Access | `<DATA_VLANS>` | VPX data traffic. |
| LOM | `<LOM_INTERFACE>` | Access | `<LOM_VLAN>` | Out-of-band management. |
| Internal | `<INTERNAL_CHANNEL>` | Tagged | `<INTERNAL_VLANS>` | Internal VPX traffic. |
| External | `<EXTERNAL_CHANNEL>` | Tagged | `<EXTERNAL_VLANS>` | External VPX traffic. |

### 3.2.4 SDX IP Addressing

| Site | Type | Placeholder | Description |
|---|---|---|---|
| `<SITE_A>` | SDX Management IP | `<SDX_SITE_A_MGMT_IP>` | SDX management address. |
| `<SITE_A>` | Hypervisor IP | `<SDX_SITE_A_HYPERVISOR_IP>` | Hypervisor management address, if applicable. |
| `<SITE_A>` | LOM IP | `<SDX_SITE_A_LOM_IP>` | Out-of-band management. |
| `<SITE_B>` | SDX Management IP | `<SDX_SITE_B_MGMT_IP>` | SDX management address. |
| `<SITE_B>` | Hypervisor IP | `<SDX_SITE_B_HYPERVISOR_IP>` | Hypervisor management address, if applicable. |
| `<SITE_B>` | LOM IP | `<SDX_SITE_B_LOM_IP>` | Out-of-band management. |
| Shared | DNS | `<DNS_SERVER_IPS>` | Name resolution. |
| Shared | NTP | `<NTP_SERVER_IPS>` | Time synchronization. |

---

## 3.3 NetScaler VPX Provisioning

Use this table for each VPX instance or HA pair.

| Setting | Node 1 | Node 2 | Notes |
|---|---|---|---|
| Site | `<SITE_A>` | `<SITE_B>` | Distributed HA if applicable. |
| Hostname | `<ADC_NODE_1_HOSTNAME>` | `<ADC_NODE_2_HOSTNAME>` | Sanitized. |
| NSIP | `<ADC_NODE_1_NSIP>` | `<ADC_NODE_2_NSIP>` | Management IPs. |
| Firmware | `<VERSION_BUILD>` | `<VERSION_BUILD>` | Must match for HA. |
| Total Memory | `<RAM_MB>` | `<RAM_MB>` | Based on sizing. |
| CPU | `<CPU_COUNT>` | `<CPU_COUNT>` | Dedicated or shared. |
| Throughput | `<THROUGHPUT>` | `<THROUGHPUT>` | License dependent. |
| Crypto VF | `<CRYPTO_VF_COUNT>` | `<CRYPTO_VF_COUNT>` | If SDX crypto resources are assigned. |
| Management VLAN | `<MGMT_VLAN>` | `<MGMT_VLAN>` | NSVLAN if applicable. |
| Data Interface | `<DATA_INTERFACE>` | `<DATA_INTERFACE>` | Channel or interface. |
| Data VLANs | `<DATA_VLAN_LIST>` | `<DATA_VLAN_LIST>` | Tagged or access. |
| HA Status | Enabled | Enabled | Active/passive. |
| HA Sync | Enabled | Enabled | Disable only temporarily during controlled migrations. |
| HA Propagation | Enabled | Enabled | Disable only temporarily during controlled migrations. |

---

## 3.4 Base Configuration

| Category | Setting | Design Decision |
|---|---|---|
| System | Time Zone | `<TIME_ZONE>` |
| System | NTP Servers | `<NTP_SERVER_LIST>` |
| System | NTP Sync | Enabled |
| System | DNS Servers | `<DNS_SERVER_LIST>` |
| System | Hostname | `<ADC_HOSTNAME>` |
| Notifications | Syslog Server | `<SYSLOG_SERVER>` |
| Notifications | Syslog Port | 514 or `<CUSTOM_PORT>` |
| Notifications | Log Levels | Emergency, Alert, Critical, Error, Warning, Notice, Informational, Debug as required |
| Notifications | SNMP Server | `<SNMP_SERVER>` |
| Notifications | SNMP Port | 162 |
| Notifications | SNMP Community / User | `<SNMP_SECRET_OR_USER>` |
| Alerts | Event Rule | `<EVENT_RULE_NAME>` |
| Alerts | Severity | Major, Critical, or per operational policy |
| Admin | Admin Profiles | `<ADMIN_PROFILE>` |
| Admin | Authentication | Local, LDAP, TACACS+, RADIUS, or SAML as required |
| Security | Management Access | Restrict to management networks only |
| Security | Audit Logging | Enabled |

---

## 3.5 Network Design

### 3.5.1 Network Topology

Document whether the ADC is deployed in one-arm or two-arm mode.

| Design Option | Description | When to Use |
|---|---|---|
| One-arm | Client and backend traffic use the same logical network path, usually with SNIP as source. | Common for Gateway, StoreFront, and application LB. |
| Two-arm | Client and server-side traffic are separated by different interfaces or VLANs. | Use when routing or security zones require separation. |
| SDX hosted VPX | VPX instances run on SDX and consume SDX interfaces/channels/VLANs. | Multi-instance, multi-tenant, or hardware consolidation designs. |

### 3.5.2 Interfaces and Channels

| Interface / Channel | Type | VLANs | Purpose |
|---|---|---|---|
| `<MGMT_INTERFACE>` | Access / Tagged | `<MGMT_VLAN>` | Management. |
| `<DATA_INTERFACE_OR_CHANNEL>` | Access / Tagged / LACP | `<DATA_VLANS>` | Application traffic. |
| `<HA_INTERFACE>` | Access / Tagged | `<HA_OR_MGMT_VLAN>` | HA monitoring/sync path if applicable. |
| `<LOM_INTERFACE>` | Access | `<LOM_VLAN>` | Out-of-band management. |

### 3.5.3 VLANs

| VLAN Name | VLAN ID | Interface / Channel | Type | Description |
|---|---:|---|---|---|
| Management | `<MGMT_VLAN_ID>` | `<MGMT_INTERFACE>` | Access / Tagged | ADC management. |
| Internal Data | `<INTERNAL_DATA_VLAN_ID>` | `<DATA_INTERFACE>` | Access / Tagged | Internal applications. |
| External Data | `<EXTERNAL_DATA_VLAN_ID>` | `<DATA_INTERFACE>` | Access / Tagged | External applications or DMZ. |
| StoreFront | `<STOREFRONT_VLAN_ID>` | `<DATA_INTERFACE>` | Access / Tagged | StoreFront LB traffic. |
| Gateway | `<GATEWAY_VLAN_ID>` | `<DATA_INTERFACE>` | Access / Tagged | Gateway VIP traffic. |

### 3.5.4 IP Addressing

| IP Type | Placeholder | Description |
|---|---|---|
| NSIP Node 1 | `<ADC_NODE_1_NSIP>` | Management IP for primary ADC node. |
| NSIP Node 2 | `<ADC_NODE_2_NSIP>` | Management IP for secondary ADC node. |
| SNIP | `<SNIP_DATA_NETWORK>` | Server-side communication for data network. |
| VIP StoreFront | `<STOREFRONT_VIP>` | StoreFront load balancing VIP. |
| VIP Gateway | `<GATEWAY_VIP>` | Citrix Gateway VIP. |
| VIP LDAPS | `<LDAPS_VIP>` | LDAPS load balancing VIP. |
| VIP DNS | `<DNS_VIP>` | DNS load balancing VIP. |
| ADM / Console Agent | `<CONSOLE_AGENT_IP>` | NetScaler Console/ADM agent IP. |
| Syslog | `<SYSLOG_IP>` | Logging platform. |

### 3.5.5 Routing

| Network | Mask | Next Hop | Purpose |
|---|---|---|---|
| `0.0.0.0` | `0.0.0.0` | `<DEFAULT_GATEWAY>` | Default route. |
| `<BACKEND_NETWORK>` | `<MASK>` | `<NEXT_HOP>` | Backend reachability. |
| `<MGMT_NETWORK>` | `<MASK>` | `<MGMT_NEXT_HOP>` | Management reachability if separate. |

### 3.5.6 Policy Based Routing

Use Policy Based Routing only when management and data traffic must be forced through different next hops or when security segmentation requires it.

| PBR Name | Source | Destination | Next Hop | Purpose |
|---|---|---|---|---|
| `<PBR_NAME>` | `<SOURCE_IP_OR_SUBNET>` | `<DESTINATION>` | `<NEXT_HOP>` | Isolate management or application traffic. |

---

## 3.6 High Availability

### 3.6.1 HA Design

| Setting | Value |
|---|---|
| HA Mode | Active/Passive |
| Node 1 NSIP | `<ADC_NODE_1_NSIP>` |
| Node 2 NSIP | `<ADC_NODE_2_NSIP>` |
| Primary Node | `<PRIMARY_NODE>` |
| Secondary Node | `<SECONDARY_NODE>` |
| HA Sync | Enabled |
| HA Propagation | Enabled |
| Fail-Safe Mode | `<ENABLED_OR_DISABLED>` |
| Sync VLAN | `<SYNC_VLAN>` |
| Hello Interval | `<HELLO_INTERVAL_MS>` |
| Dead Interval | `<DEAD_INTERVAL>` |
| Max Flips Count | `<MAX_FLIPS_COUNT>` |
| Interfaces Monitored | `<MONITORED_INTERFACES>` |

### 3.6.2 HA Design Notes

- Firmware versions should match between HA nodes.
- License capabilities should match between HA nodes.
- Interfaces and VLANs should be consistent between nodes.
- HA propagation and synchronization should be enabled during steady state.
- During controlled migrations, HA propagation may be temporarily disabled to avoid overwriting modified network configuration.
- Failover and failback should be tested during an approved maintenance window.
- Save and backup configuration before HA changes.

---

## 3.7 Modes and Features

### 3.7.1 Modes

| Mode | Recommended Setting | Notes |
|---|---|---|
| Fast Ramp | Enabled | Common optimization for server-side connections. |
| Layer 2 Mode | Disabled unless required | Avoid unintended bridging. |
| Use Source IP | Disabled unless two-arm or source-IP preservation is required | SNIP is usually used in one-arm designs. |
| Client Keep-Alive | Enabled | Improves client connection reuse. |
| TCP Buffering | Disabled unless required | Enable only after application validation. |
| MAC Based Forwarding | Disabled unless topology requires it | Use cautiously. |
| Edge Configuration | Enabled if applicable | Depends on topology. |
| Use Subnet IP | Enabled | Common in proxy designs. |
| Layer 3 Mode | Disabled or carefully controlled | Avoid unintended routing/network bypass. |
| Path MTU Discovery | Enabled | Helps PMTU handling. |
| Route Advertisement | Disabled unless ADC is participating in routing | Avoid unexpected route propagation. |

### 3.7.2 Features

| Feature | Recommended Setting | Notes |
|---|---|---|
| SSL Offloading | Enabled | Required for SSL vServers. |
| Load Balancing | Enabled | Required for LB vServers. |
| Content Switching | Enabled if used | Required for CS vServers. |
| Rewrite | Enabled if used | Header insertion/removal and response/request rewrites. |
| Responder | Enabled if used | Redirects, blocks, or direct responses. |
| Citrix Gateway | Enabled if used | Required for Gateway. |
| AAA | Enabled if using nFactor/MFA/AAA | Required for advanced authentication. |
| Application Firewall | Disabled unless WAF is in scope | Enable only when WAF design exists. |
| GSLB | Disabled unless multi-site DNS traffic management is in scope | Requires GSLB design. |
| HTML Injection | Depends on ADM/analytics requirements | Enable only if required. |
| Bot / Reputation / DoS | Disabled unless in scope | Requires separate security design. |

---

## 3.8 TCP and HTTP Parameters

### 3.8.1 TCP Parameters

| Setting | Recommended Value | Rationale |
|---|---|---|
| Window Scaling | Enabled | Supports large traffic flows. |
| Window Scaling Factor | `<VALUE>` | Use platform default unless tuning is required. |
| Selective Acknowledgment | Enabled | Improves TCP recovery. |
| Nagle Algorithm | Depends on application | Validate before enabling globally. |
| RNAT TCP Proxy | Enabled if required | Use for specific TCP session handling requirements. |

### 3.8.2 HTTP Parameters

| Setting | Recommended Value | Rationale |
|---|---|---|
| Cookie Version 1 | Enabled | Improves cookie standards handling. |
| Drop Invalid HTTP Requests | Enabled | Security hardening. |
| Mark HTTP/0.9 Requests Invalid | Enabled | HTTP/0.9 is obsolete. |
| Mark CONNECT Requests Invalid | Enabled unless proxy use case exists | Prevents unintended proxy behavior. |

---

# 4. Application Delivery Configuration

## 4.1 StoreFront Load Balancing

| Module | Option | Value |
|---|---|---|
| Service Group | Name | `<SG_STOREFRONT>` |
| Service Group | Members | `<STOREFRONT_SERVER_1>`, `<STOREFRONT_SERVER_2>` |
| Service Protocol | Protocol | SSL or HTTP |
| Service Port | Port | 443 or 80 |
| Monitor | Type | HTTP, HTTPS, StoreFront-specific, or custom |
| LB vServer | Name | `<LB_STOREFRONT>` |
| LB vServer | VIP | `<STOREFRONT_VIP>` |
| LB vServer | Port | 443 |
| LB Method | Method | Least Connection or per application requirement |
| Persistence | Type | COOKIEINSERT, SOURCEIP, SSLSESSION, or None |
| SSL Certificate | CertKey | `<CERTKEY_STOREFRONT>` |
| Validation | Expected State | vServer UP, service group members UP |

---

## 4.2 LDAPS Load Balancing

| Module | Option | Value |
|---|---|---|
| Service Group | Name | `<SG_LDAPS>` |
| Members | LDAP/AD Servers | `<LDAP_SERVER_1>`, `<LDAP_SERVER_2>` |
| Protocol | Protocol | TCP or SSL_TCP |
| Port | Port | 636 |
| Monitor | Type | TCP, LDAP, or custom LDAPS monitor |
| LB vServer | Name | `<LB_LDAPS>` |
| LB vServer | VIP | `<LDAPS_VIP>` |
| LB vServer | Port | 636 |
| Persistence | Type | SOURCEIP or per identity provider requirement |
| Validation | Expected State | LDAP bind/search succeeds through VIP |

---

## 4.3 DNS Load Balancing

| Module | Option | Value |
|---|---|---|
| Service Group | Name | `<SG_DNS>` |
| Members | DNS Servers | `<DNS_SERVER_1>`, `<DNS_SERVER_2>` |
| Protocol | Protocol | DNS / UDP / TCP as required |
| Port | Port | 53 |
| LB vServer | Name | `<LB_DNS>` |
| LB vServer | VIP | `<DNS_VIP>` |
| LB Method | Method | Least Connection, Round Robin, or per requirement |
| Persistence | Type | None or SOURCEIP if required |
| Validation | Expected State | DNS queries resolve through VIP |

---

## 4.4 Generic Application Load Balancing

| Module | Option | Value |
|---|---|---|
| Application | Name | `<APPLICATION_NAME>` |
| FQDN | Name | `<APP_FQDN>` |
| LB vServer | Name | `<LB_APP_NAME>` |
| VIP | Address | `<APPLICATION_VIP>` |
| Protocol / Port | Value | `<PROTOCOL>/<PORT>` |
| Service Group | Name | `<SG_APP_NAME>` |
| Backend Servers | Members | `<APP_SERVER_1>`, `<APP_SERVER_2>` |
| Monitor | Type | `<MONITOR_TYPE>` |
| Persistence | Type | `<PERSISTENCE_TYPE>` |
| SSL Certificate | CertKey | `<CERTKEY_NAME>` |
| Security Policies | Rewrite / Responder / WAF | `<POLICY_LIST>` |
| Validation | Expected State | vServer and service members UP |

---

## 4.5 Content Switching

Use this section when one VIP must serve multiple applications, domains, paths, or routing decisions.

| Item | Value |
|---|---|
| CS vServer Name | `<CS_VSERVER_NAME>` |
| VIP | `<CS_VIP>` |
| Protocol / Port | SSL / 443 |
| Certificate Strategy | Wildcard, SAN, or SNI certificates |
| Default Target | `<DEFAULT_LB_VSERVER>` or reject |
| Policy Type | Host, path, header, or expression-based |
| Target LB vServers | `<LB_APP_1>`, `<LB_APP_2>`, `<LB_API>` |

### Content Switching Policy Matrix

| Priority | Match Condition | Target LB vServer |
|---:|---|---|
| 100 | Host equals `<APP1_FQDN>` | `<LB_APP_1>` |
| 110 | Host equals `<APP2_FQDN>` | `<LB_APP_2>` |
| 120 | Path starts with `/api` | `<LB_API>` |
| 999 | Default | `<LB_DEFAULT>` |

---

## 4.6 AppExpert: Responder and Rewrite

### 4.6.1 HTTP to HTTPS Redirect

| Item | Value |
|---|---|
| Responder Action Name | `<ACT_HTTP_TO_HTTPS>` |
| Action Type | Redirect |
| Redirect Expression | `https://` + host + URL |
| Status Code | 301 or 302 |
| Policy Name | `<POL_HTTP_TO_HTTPS>` |
| Bind Point | HTTP LB or CS vServer |

### 4.6.2 Security Headers

| Header | Recommended Value | Notes |
|---|---|---|
| Strict-Transport-Security | `max-age=<SECONDS>; includeSubDomains` | Use only after HTTPS validation. |
| X-Frame-Options | `DENY` or `SAMEORIGIN` | Depends on application framing needs. |
| X-Content-Type-Options | `nosniff` | Common hardening. |
| Referrer-Policy | `strict-origin-when-cross-origin` | Adjust per privacy requirements. |
| Content-Security-Policy | `<CSP_VALUE>` | Must be application-specific. |
| Permissions-Policy | `<PERMISSIONS_POLICY>` | Optional hardening. |

---

# 5. Authentication, AAA, MFA, and Gateway

## 5.1 Authentication Design

| Authentication Type | Use Case | Notes |
|---|---|---|
| Local | Emergency or fallback admin access | Restrict and audit. |
| LDAP / LDAPS | AD-based authentication and group extraction | Prefer LDAPS for secure bind/search. |
| RADIUS | MFA provider integration | Validate ports, shared secret, timeout. |
| SAML | Cloud IdP integration | Validate metadata, entity ID, ACS URL, signing certificate. |
| nFactor | Multi-step authentication flows | Requires AAA vServer and authentication profile. |
| TACACS+ | Admin authentication | Use for management plane if required. |

---

## 5.2 LDAP / LDAPS Authentication

| Module | Option | Value |
|---|---|---|
| Authentication Server | Name | `<LDAP_ACTION_NAME>` |
| Authentication Type | Type | AD / LDAP |
| Server IP / FQDN | Value | `<LDAP_SERVER_OR_LB_VIP>` |
| Port | Value | 636 |
| Security Type | Value | SSL |
| Base DN | Value | `<BASE_DN>` |
| Bind DN | Value | `<LDAP_BIND_DN>` |
| Password | Value | `<SECRET_VALUE>` |
| Login Name Attribute | Value | `sAMAccountName`, `userPrincipalName`, or required attribute |
| Group Attribute | Value | `<GROUP_ATTRIBUTE>` |
| Search Filter | Value | `<LDAP_SEARCH_FILTER>` |
| Authentication Policy | Name | `<LDAP_POLICY_NAME>` |
| Policy Expression | Value | `true` or specific expression |

---

## 5.3 RADIUS / MFA Authentication

| Module | Option | Value |
|---|---|---|
| RADIUS Action | Name | `<RADIUS_ACTION_NAME>` |
| Server IP | Value | `<RADIUS_SERVER_IP>` |
| Port | Value | `<RADIUS_PORT>` |
| Shared Secret | Value | `<SECRET_VALUE>` |
| Timeout | Value | `<TIMEOUT_SECONDS>` |
| Accounting | Value | Enabled/Disabled as required |
| Authentication Policy | Name | `<RADIUS_POLICY_NAME>` |
| Policy Expression | Value | `true` or group/context specific |

---

## 5.4 SAML Authentication

| Module | Option | Value |
|---|---|---|
| SAML Action | Name | `<SAML_ACTION_NAME>` |
| IdP Metadata | Value | `<IDP_METADATA_URL_OR_FILE>` |
| IdP Entity ID | Value | `<IDP_ENTITY_ID>` |
| SP Entity ID | Value | `<SP_ENTITY_ID>` |
| ACS URL | Value | `<ACS_URL>` |
| User Field | Value | `<SAML_USER_ATTRIBUTE>` |
| Signing Certificate | Value | `<IDP_SIGNING_CERT>` |
| Authentication Policy | Name | `<SAML_POLICY_NAME>` |
| Policy Expression | Value | `true` or group/context specific |

---

## 5.5 nFactor Authentication

### 5.5.1 nFactor Flow Summary

| Factor | Authentication Method | Policy | Next Factor |
|---|---|---|---|
| Factor 1 | LDAP / SAML / RADIUS | `<FACTOR_1_POLICY>` | `<FACTOR_2_LABEL>` |
| Factor 2 | RADIUS / LDAP / Certificate / EPA | `<FACTOR_2_POLICY>` | `<FACTOR_3_LABEL_OR_NONE>` |
| Factor 3 | Optional | `<FACTOR_3_POLICY>` | None |

### 5.5.2 AAA vServer

| Module | Option | Value |
|---|---|---|
| AAA vServer | Name | `<AAA_VSERVER_NAME>` |
| IP Address Type | Value | Non-addressable or dedicated VIP |
| Protocol | Value | SSL |
| Port | Value | 443 |
| SSL Certificate | CertKey | `<AAA_CERTKEY_NAME>` |
| Portal Theme | Value | `<PORTAL_THEME>` |
| Bound Policy | Policy | `<AUTH_POLICY_NAME>` |
| Authentication Profile | Name | `<AUTH_PROFILE_NAME>` |

### 5.5.3 nFactor Notes

- Document whether nFactor is required for all users or only selected groups.
- Document group extraction and search filters.
- Document separate flows for internal users, external users, contractors, vendors, or VPN users if needed.
- Document fallback or exception flows.
- Document MFA provider timeout values.
- Document endpoint analysis if used before or during authentication.

---

## 5.6 Endpoint Analysis

Use only if EPA is in scope.

| Item | Value |
|---|---|
| EPA Purpose | Validate endpoint security before granting access. |
| EPA Stage | Pre-authentication or post-authentication factor. |
| Checks | `<EPA_CHECK_LIST>` |
| Failure Action | Deny, quarantine, or alternate flow. |
| User Experience | Document plug-in and browser requirements. |
| Validation | Test compliant and non-compliant devices. |

---

## 5.7 Citrix Gateway / Unified Gateway

### 5.7.1 Gateway Summary

| Module | Option | Value |
|---|---|---|
| Gateway vServer | Name | `<GATEWAY_VSERVER_NAME>` |
| VIP | Address | `<GATEWAY_VIP>` |
| FQDN | Name | `<GATEWAY_FQDN>` |
| Protocol | Value | SSL |
| Port | Value | 443 |
| SSL Certificate | CertKey | `<GATEWAY_CERTKEY_NAME>` |
| Authentication Profile | Name | `<AUTH_PROFILE_NAME>` |
| Primary Authentication | Value | None when auth profile invokes AAA/nFactor, or LDAP/RADIUS/SAML as designed |
| Portal Theme | Value | `<PORTAL_THEME>` |
| StoreFront URL | Value | `<STOREFRONT_LB_URL>` |
| Store Name | Value | `<STORE_NAME>` |
| STA Servers | Value | `<STA_SERVER_1>`, `<STA_SERVER_2>` |
| Session Policy | Name | `<SESSION_POLICY_NAME>` |
| Authorization | Value | Allow/Deny per design |
| Split Tunnel | Value | On/Off per VPN design |
| ICA Proxy | Value | On/Off per design |

### 5.7.2 Gateway User Segmentation

| Gateway | User Population | Authentication Flow | StoreFront / Resource Target |
|---|---|---|---|
| `<GATEWAY_EXTERNAL>` | External users | `<AUTH_FLOW_EXTERNAL>` | `<STOREFRONT_EXTERNAL>` |
| `<GATEWAY_INTERNAL>` | Internal users | `<AUTH_FLOW_INTERNAL>` | `<STOREFRONT_INTERNAL>` |
| `<GATEWAY_VPN>` | VPN users | `<AUTH_FLOW_VPN>` | `<VPN_RESOURCES>` |
| `<GATEWAY_EXCEPTION>` | Exception users | `<AUTH_FLOW_EXCEPTION>` | `<RESOURCE_TARGET>` |

---

# 6. Security Design

## 6.1 SSL Profiles

| Setting | Recommended Value |
|---|---|
| SSL Profile Type | FrontEnd |
| SSLv3 | Disabled |
| TLS 1.0 | Disabled |
| TLS 1.1 | Disabled |
| TLS 1.2 | Enabled |
| TLS 1.3 | Enabled if supported and tested |
| Deny SSL Renegotiation | Non-secure or all, depending on compatibility |
| HSTS | Enabled for internet-facing HTTPS after validation |
| HSTS Max Age | `<HSTS_MAX_AGE>` |
| DH Parameters | Enabled where required |
| OCSP Stapling | Enabled if required and supported |
| Cipher Group | `<CIPHER_GROUP_NAME>` |

## 6.2 Cipher Group

| Cipher Group | Purpose | Notes |
|---|---|---|
| `<CIPHER_GROUP_NAME>` | Internet-facing TLS hardening | Include only approved ciphers. |
| `<LEGACY_CIPHER_GROUP_NAME>` | Temporary compatibility | Use only with approved risk acceptance. |

## 6.3 Certificate Inventory

| Certificate | Bound vServers | Expiry | Chain Linked | Owner | Renewal Process |
|---|---|---|---|---|---|
| `<CERTKEY_NAME>` | `<VSERVER_LIST>` | `<EXPIRY_DATE>` | Yes/No | `<OWNER>` | `<PROCESS>` |

## 6.4 Security Controls

| Control | Design Decision |
|---|---|
| Management ACLs | Restrict management access to approved subnets. |
| Admin Authentication | Use centralized authentication where possible. |
| Role-Based Access | Use least privilege. |
| Audit Logging | Enabled and forwarded to syslog/SIEM. |
| TLS Hardening | Disable legacy protocols and weak ciphers. |
| HTTP Hardening | Drop invalid requests and insert security headers if appropriate. |
| MFA | Required for external or privileged access where applicable. |
| Backup Protection | Protect `/nsconfig`, certs, keys, and license files. |
| Secrets Handling | Never store cleartext credentials in design documents. |

---

# 7. Migration and Firmware Upgrade Strategy

Use this section when migrating VPX instances, replacing SDX hardware, or upgrading firmware.

## 7.1 Migration Principles

- Back up the existing configuration before any change.
- Inventory interfaces, VLANs, routes, PBRs, certificates, licenses, and custom scripts.
- Validate firmware compatibility and required upgrade path.
- Convert unsupported classic policies to advanced policies before upgrade where required.
- Maintain HA protection during migration when possible.
- Avoid enabling HA propagation until network-specific changes are validated.
- Test each migrated VPX pair independently.
- Maintain rollback checkpoints at each phase.

## 7.2 Recommended Migration Sequence

### Step 1: Backup and Prepare

| Activity | Description |
|---|---|
| Backup Configuration | Export `ns.conf`, `/nsconfig`, certificates, keys, licenses, scripts, and custom files. |
| Inventory Network | Document interfaces, VLANs, channels, NSIPs, SNIPs, VIPs, routes, and PBRs. |
| Inventory Features | Document enabled features, modes, LB/CS/Gateway/AAA/AppExpert objects. |
| Adjust Config | Update interface names, channels, VLANs, routes, and platform-specific settings for target environment. |
| Validate Syntax | Check configuration compatibility before import. |

### Step 2: Temporary Node Introduction

| Activity | Description |
|---|---|
| Deploy Temporary VPX | Provision temporary VPX in target platform. |
| Disable HA Propagation Temporarily | Prevent unwanted overwrite of target-specific network configuration. |
| Join HA Carefully | Pair legacy or current node with temporary target node as required by migration design. |
| Fail Over in Maintenance Window | Promote temporary or target node after validation. |
| Validate Services | Confirm vServers, services, authentication, and Gateway behavior. |

### Step 3: Target Node Deployment

| Activity | Description |
|---|---|
| Deploy Final VPX Node | Provision final VPX in target platform/site. |
| Rebuild HA Pair | Pair target nodes together. |
| Enable Sync and Propagation | Re-enable steady-state HA behavior. |
| Replicate Configuration | Confirm configuration sync and file propagation. |
| Execute Controlled Failover | Validate both nodes can become primary. |

### Step 4: Final Validation and Decommission

| Activity | Description |
|---|---|
| Validate HA | Confirm node states, sync, monitored interfaces, and failover. |
| Validate Traffic | Confirm application VIPs, Gateway, StoreFront, LDAPS, DNS, and app services. |
| Validate Logs | Confirm syslog/SNMP/Console data. |
| Validate Backups | Confirm automatic and manual backups. |
| Decommission Legacy | Remove old nodes only after validation and rollback window expiration. |

---

## 7.3 Firmware Upgrade Plan

| Phase | Activity |
|---|---|
| Pre-check | Verify firmware path, release notes, known issues, compatibility, license, disk space, and backups. |
| Backup | Backup `/nsconfig`, certificates, keys, licenses, scripts, and running/saved configuration. |
| Upgrade Secondary | Upgrade the secondary HA node first when using HA. |
| Validate Secondary | Confirm node returns healthy. |
| Failover | Promote upgraded node. |
| Upgrade Former Primary | Upgrade the remaining node. |
| Final Validation | Confirm HA, sync, services, Gateway, authentication, SSL, and logs. |
| Rollback | Restore previous firmware/config if validation fails according to approved plan. |

---

## 7.4 Rollback Plan

| Rollback Trigger | Rollback Action |
|---|---|
| HA fails to synchronize | Stop migration, restore known-good HA state, validate config. |
| Authentication failure | Revert authentication profile or Gateway binding to previous state. |
| Gateway launch failure | Revert session policies, STA settings, or StoreFront integration. |
| Backend service outage | Revert LB/CS bindings or restore previous vServer config. |
| Firmware issue | Roll back to previous build using approved vendor procedure. |
| Certificate issue | Rebind prior certificate if not expired and approved. |

---

# 8. Management and Operations

## 8.1 NetScaler Console / ADM Design

| Item | Value |
|---|---|
| Deployment Type | Cloud service, on-prem appliance, or HA pair |
| Primary Use | Monitoring, licensing, backups, analytics, configuration jobs |
| Agents | `<AGENT_COUNT>` |
| Managed Instances | `<ADC_INSTANCE_LIST>` |
| Admin Profiles | `<ADMIN_PROFILE_LIST>` |
| Backup Schedule | `<BACKUP_SCHEDULE>` |
| Syslog Role | Yes/No |
| SNMP Role | Yes/No |
| Analytics | Enabled/Disabled |
| AppFlow | Enabled/Disabled |
| Licensing | Local, pooled, Console-managed |

## 8.2 Instance Onboarding

| Instance | NSIP | Site | Profile | Status |
|---|---|---|---|---|
| `<ADC_INSTANCE_1>` | `<ADC_NODE_1_NSIP>` | `<SITE_A>` | `<ADMIN_PROFILE>` | `<STATUS>` |
| `<ADC_INSTANCE_2>` | `<ADC_NODE_2_NSIP>` | `<SITE_B>` | `<ADMIN_PROFILE>` | `<STATUS>` |

## 8.3 Configuration Files

| Directory / File | Purpose |
|---|---|
| `/nsconfig/ns.conf` | Saved ADC configuration. |
| `/nsconfig/ns.conf.0` to `/nsconfig/ns.conf.4` | Previous saved configuration versions. |
| `/nsconfig/ssl/` | Certificates and key files. |
| `/nsconfig/license/` | License files. |
| `/nsconfig/rc.netscaler` | Optional startup commands. |
| `/nsconfig/resolv.conf` | DNS resolver configuration. |
| `/nsconfig/ntp.conf` | NTP client configuration. |
| `/nsconfig/nsbefore.sh` | Optional script before licensing. |
| `/nsconfig/nsafter.sh` | Optional script after licensing. |

---

## 8.4 Backup and Restore

### 8.4.1 Backup Strategy

| Backup Type | Method | Frequency | Scope |
|---|---|---|---|
| Console/ADM Auto Backup | NetScaler Console / ADM | `<FREQUENCY>` | Config backup for managed instances. |
| Manual Config Backup | CLI/SCP/SFTP | Before and after major changes | `/nsconfig`, certs, keys, licenses, custom files. |
| Certificate Backup | Secure file transfer | During certificate changes | `/nsconfig/ssl`. |
| Firmware Backup | Snapshot or approved backup method | Before upgrade | Platform-specific backup. |
| Documentation Backup | Repository or document system | Each revision | Sanitized design/config docs. |

### 8.4.2 Major Changes Requiring Backup

- Firmware upgrade.
- SDX replacement or migration.
- VPX migration or reprovisioning.
- HA rebuild or failover testing.
- Certificate renewal.
- License change.
- Gateway authentication change.
- nFactor or MFA flow change.
- SSL profile or cipher change.
- WAF or AppExpert policy change.
- Routing, VLAN, SNIP, NSIP, or VIP change.

### 8.4.3 Restore Requirements

Before restoring configuration to a replacement appliance:

- Confirm platform compatibility.
- Confirm firmware compatibility.
- Confirm interface naming and VLAN compatibility.
- Copy certificate and key files to `/nsconfig/ssl`.
- Copy license files to `/nsconfig/license` if applicable.
- Copy custom scripts and supporting files.
- Restore `ns.conf` to `/nsconfig`.
- Reboot or load configuration according to approved procedure.
- Validate HA, vServers, services, SSL, authentication, Gateway, and logs.

---

## 8.5 Diagnostic Tools

| Tool | Purpose |
|---|---|
| NetScaler CLI | Configuration and operational inspection. |
| NetScaler GUI | Configuration, monitoring, and visualization. |
| NetScaler Console / ADM | Centralized management, monitoring, analytics, backups, licensing. |
| nstrace | Packet capture on ADC. |
| nstcpdump | Tcpdump-like packet capture and filtering. |
| nsconmsg | Event, counter, and console message analysis. |
| ns.log | Local system and audit logs. |
| aaad.debug | Authentication troubleshooting. |
| Wireshark | Packet analysis. |
| SCP/SFTP client | Secure backup and file transfer. |
| Browser Developer Tools | Gateway and SAML troubleshooting. |
| SSL Labs or internal TLS scanner | TLS posture validation. |

## 8.6 Command Line Diagnostics

### General Health

```bash
show version
show ns config
show ns runningConfig
show feature
show mode
show ns ip
show route
show vlan
show interface
show channel
```

### HA

```bash
show ha node
show ha status
show ns runningConfig
```

### Load Balancing

```bash
show lb vserver
show lb vserver <LB_VSERVER_NAME>
stat lb vserver <LB_VSERVER_NAME>
show service
show serviceGroup
show serviceGroup <SERVICEGROUP_NAME>
show lb monitor
```

### SSL

```bash
show ssl certKey
show ssl certKey <CERTKEY_NAME>
show ssl vserver
show ssl profile
show ssl cipher
```

### Gateway and AAA

```bash
show vpn vserver
show vpn vserver <GATEWAY_VSERVER_NAME>
show authentication vserver
show authentication policy
show authentication ldapAction
show authentication radiusAction
show authentication samlAction
show authentication policylabel
show authentication loginSchema
```

### Logs and Authentication Debug

```bash
shell
tail -f /var/log/ns.log
cat /tmp/aaad.debug
```

### Packet Capture

```bash
shell
/netscaler/nstcpdump.sh -ni <INTERFACE> host <HOST_IP>
/netscaler/nstrace.sh -sz 0 -tcpdump 1
```

### Event and Counter Analysis

```bash
shell
nsconmsg -K /var/nslog/newnslog -d event
nsconmsg -K /var/nslog/newnslog -d consmsg
nsconmsg -K /var/nslog/newnslog -d current
```

---

# 9. Validation Plan

## 9.1 Technical Validation

| Area | Validation |
|---|---|
| HA | Failover and failback tested successfully. |
| Network | NSIP, SNIP, VIP, VLANs, routes, PBRs validated. |
| Load Balancing | vServers and services are UP. |
| StoreFront | Login, enumeration, and launch tested. |
| Gateway | Internal/external/VPN login tested. |
| MFA | SAML/RADIUS/nFactor flows tested. |
| LDAP/LDAPS | Authentication and group extraction tested. |
| DNS | Queries through DNS VIP tested. |
| SSL | Certificate chain, TLS versions, and ciphers validated. |
| Monitoring | Console/ADM, syslog, SNMP, and alerts validated. |
| Backups | Backup and restore artifacts confirmed. |
| Logs | ns.log, aaad.debug, and Console/ADM logs validated. |

## 9.2 User Acceptance Testing

| Test Case | User Type | Expected Result | Status |
|---|---|---|---|
| Gateway login | Internal user | Authentication succeeds. | `<STATUS>` |
| Gateway login | External user | MFA succeeds. | `<STATUS>` |
| Gateway login | VPN user | VPN session starts. | `<STATUS>` |
| StoreFront enumeration | Citrix user | Resources display. | `<STATUS>` |
| ICA launch | Citrix user | Application/desktop launches. | `<STATUS>` |
| MFA failure | Test user | Access is denied. | `<STATUS>` |
| Backend outage | Test service | Monitor marks member down. | `<STATUS>` |
| HA failover | Admin | Services remain reachable. | `<STATUS>` |

---

# 10. Comparison: Source Document Patterns vs Optimized Template

| Area | Design Pattern 1 | Configuration Pattern | Gateway/MFA Pattern | Optimized Output |
|---|---|---|---|---|
| Executive Summary | Strong project overview, goals, risks, next steps. | Adds migration and firmware upgrade emphasis. | Adds Gateway, user groups, MFA, and EPA emphasis. | Unified executive summary with scope, risks, goals, and short/long-term actions. |
| Conceptual Architecture | Gateway and StoreFront architecture. | SDX/VPX migration architecture and multi-site hosted VPX model. | Multiple Gateway personas and MFA flows. | Generic diagram model supporting VPX, SDX, Gateway, StoreFront, MFA, Console/ADM, and monitoring. |
| Platform Design | VPX HA pair and base appliance parameters. | SDX hardware, VPX provisioning, firmware, channels, NSVLAN, migration. | VPX HA with Gateway focus. | Combined platform section for VPX, MPX, SDX, Console/ADM, and hosted VPX instances. |
| Network Design | VLANs, SNIP, VIP, PBR, routing, HA. | SDX channels, LACP, NSVLAN, management/data segmentation. | Management/data interfaces and Gateway VIP segmentation. | Unified networking model with topology, interfaces, VLANs, IP types, routing, and PBR. |
| Authentication | Azure/SAML and FAS patterns. | Mainly migration/configuration focused. | LDAP, RADIUS, Duo, nFactor, EPA patterns. | Generic auth framework covering LDAP, RADIUS, SAML, nFactor, EPA, Gateway, and FAS where required. |
| Load Balancing | StoreFront LB. | Migrated LB and VPX/application references. | StoreFront, LDAPS, DNS LB. | Standard LB modules for StoreFront, LDAPS, DNS, generic apps, and Content Switching. |
| AppExpert | Minimal or not required. | Migration may include AppExpert policy preservation. | HTTP-to-HTTPS responder and security logic. | Added responder/rewrite patterns for redirects and security headers. |
| Security | SSL profiles, ciphers, certificates. | Firmware security and migration risks. | MFA, EPA, TLS, traffic isolation. | Security section includes TLS, certs, headers, management ACLs, MFA, and logging. |
| Management | ADM, config files, backups, diagnostics. | Strong backup/restore and diagnostic structure. | ADM/Console cloud service and licensing/monitoring. | Operations section integrates Console/ADM, backup/restore, diagnostics, and validation. |
| Migration | Limited. | Strong four-step SDX/VPX migration approach. | Not primary focus. | Dedicated migration and firmware upgrade strategy with rollback. |

---

# 11. AI Generation Instructions

Use the following instruction when asking an AI to generate a customer-ready NetScaler design document from this reference.

```text
You are creating a professional NetScaler design and configuration document.

Use the supplied Markdown reference as the structure and style guide.

Requirements:
1. Generate a clean design document for the target NetScaler environment.
2. Keep the document generic unless customer-approved values are explicitly provided.
3. Do not invent IP addresses, domains, hostnames, certificates, user groups, credentials, or firmware versions.
4. Use placeholders where values are unknown.
5. Include executive summary, scope, goals, risks, design, configuration, migration/upgrade, management, backup/restore, diagnostics, validation, and appendix sections.
6. Separate design decisions from implementation commands.
7. Use tables for platform, networking, HA, authentication, load balancing, SSL, monitoring, and validation.
8. Include a rollback plan for upgrades, migrations, authentication changes, and Gateway changes.
9. Include a validation plan and operational handover section.
10. Remove all confidential information before producing the final output.
11. Use vendor terminology accurately: NSIP, SNIP, VIP, HA, LB vServer, CS vServer, service group, certKey, AAA vServer, authentication profile, Gateway vServer, NetScaler Console/ADM.
12. If a required value is missing, insert a placeholder and list it under assumptions or open items.
```

---

# 12. Open Items Checklist

| Item | Required Value | Owner | Status |
|---|---|---|---|
| Target firmware version | `<TARGET_VERSION>` | `<OWNER>` | Open |
| License edition/model | `<LICENSE_MODEL>` | `<OWNER>` | Open |
| NSIP addresses | `<ADC_NODE_NSIPS>` | `<OWNER>` | Open |
| SNIP addresses | `<SNIP_LIST>` | `<OWNER>` | Open |
| VIP addresses | `<VIP_LIST>` | `<OWNER>` | Open |
| VLAN IDs | `<VLAN_LIST>` | `<OWNER>` | Open |
| Routing / PBR | `<ROUTING_DECISION>` | `<OWNER>` | Open |
| Certificates | `<CERTKEY_LIST>` | `<OWNER>` | Open |
| StoreFront servers | `<STOREFRONT_SERVER_LIST>` | `<OWNER>` | Open |
| LDAP/LDAPS servers | `<LDAP_SERVER_LIST>` | `<OWNER>` | Open |
| MFA provider | `<MFA_PROVIDER>` | `<OWNER>` | Open |
| Gateway FQDNs | `<GATEWAY_FQDN_LIST>` | `<OWNER>` | Open |
| Syslog/SIEM | `<SYSLOG_SERVER>` | `<OWNER>` | Open |
| SNMP platform | `<SNMP_SERVER>` | `<OWNER>` | Open |
| Backup location | `<BACKUP_LOCATION>` | `<OWNER>` | Open |
| Maintenance window | `<CHANGE_WINDOW>` | `<OWNER>` | Open |
| Rollback owner | `<ROLLBACK_OWNER>` | `<OWNER>` | Open |

---

# 13. Public Vendor References

Use official public documentation when grounding final design documents.

- NetScaler High Availability: https://docs.netscaler.com/en-us/citrix-adc/current-release/system/high-availability-introduction.html
- NetScaler HA Upgrade: https://docs.netscaler.com/en-us/citrix-adc/current-release/upgrade-downgrade-citrix-adc-appliance/upgrade-downgrade-ha-pair.html
- Provision NetScaler VPX Instances on SDX: https://docs.netscaler.com/en-us/sdx/current-release/provision-netscaler-instances.html
- NetScaler Console Service Overview: https://docs.netscaler.com/en-us/netscaler-console-service/overview.html
- NetScaler Console Getting Started: https://docs.netscaler.com/en-us/netscaler-console-service/getting-started.html
- NetScaler nFactor Authentication: https://docs.netscaler.com/en-us/citrix-adc/current-release/aaa-tm/authentication-methods/multi-factor-nfactor-authentication.html
- Configure nFactor Authentication: https://docs.netscaler.com/en-us/citrix-adc/current-release/aaa-tm/authentication-methods/multi-factor-nfactor-authentication/nfactor-authentication-configuring.html
- Endpoint Analysis as nFactor: https://docs.netscaler.com/en-us/citrix-adc/current-release/aaa-tm/configure-periodic-epascan-as-factor-in-nfactor.html
- NetScaler Console Analytics: https://docs.netscaler.com/en-us/netscaler-console-service/analytics.html

---

# 14. Revision History

| Revision | Change Description | Updated By | Date |
|---|---|---|---|
| 0.1 | Initial sanitized generic template created. | `<AUTHOR>` | `<DATE>` |
| 0.2 | Added SDX/VPX migration and firmware upgrade sections. | `<AUTHOR>` | `<DATE>` |
| 0.3 | Added Gateway, MFA, nFactor, EPA, and application delivery sections. | `<AUTHOR>` | `<DATE>` |
| 1.0 | Optimized sanitized reference version. | `<AUTHOR>` | `<DATE>` |
