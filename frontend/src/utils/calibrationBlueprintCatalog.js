const VENDOR_LABELS = {
  netscaler: 'NetScaler',
  f5: 'F5',
  cisco: 'Cisco',
  sdx: 'NetScaler SDX',
  juniper: 'Juniper',
  palo_alto: 'Palo Alto Networks',
  fortinet: 'Fortinet',
  checkpoint: 'Check Point',
  a10: 'A10 Networks',
  radware: 'Radware',
  haproxy: 'HAProxy / Kemp',
}

export function formatVendorLabel(vendor) {
  const key = String(vendor || '')
    .trim()
    .toLowerCase()
  if (!key) return 'Other'
  return VENDOR_LABELS[key] || key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export function formatDomainLabel(domain) {
  const value = String(domain || 'general').trim().toLowerCase()
  if (!value || value === 'general') return 'General'
  return value
    .split(/[-_]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

/** Infer product line from vendor + skill id (nexxus naming convention). */
export function inferBlueprintProduct({ skillId, vendor }) {
  const id = String(skillId || '').toLowerCase()
  const v = String(vendor || '').toLowerCase()

  if (id.includes('big-ip') || v === 'f5') {
    if (id.includes('local-traffic-management') || id.includes('-ltm')) return 'BIG-IP LTM'
    if (id.includes('dns') || id.includes('gtm')) return 'BIG-IP DNS'
    return 'BIG-IP'
  }
  if (v === 'sdx' || id.includes('-sdx-')) return 'NetScaler SDX'
  if (v === 'cisco' || id.includes('cisco-')) {
    if (id.includes('asa')) return 'Cisco ASA'
    if (id.includes('ios') || id.includes('switch')) return 'Cisco IOS/XE'
    return 'Cisco'
  }
  if (v === 'netscaler' || id.includes('netscaler') || id.includes('-adc-')) return 'NetScaler ADC'
  return formatVendorLabel(vendor)
}

export function enrichBlueprintRow(row) {
  const domains = Array.isArray(row.domains) && row.domains.length ? row.domains : ['general']
  const primaryDomain = domains[0]
  return {
    ...row,
    vendorKey: String(row.vendor || 'other').trim().toLowerCase() || 'other',
    vendorLabel: formatVendorLabel(row.vendor),
    product: inferBlueprintProduct(row),
    primaryDomain,
    primaryDomainLabel: formatDomainLabel(primaryDomain),
    domainLabels: domains.map(formatDomainLabel),
    searchText: [
      row.label,
      row.skillId,
      row.description,
      row.vendor,
      formatVendorLabel(row.vendor),
      inferBlueprintProduct(row),
      ...domains,
      ...domains.map(formatDomainLabel),
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase(),
  }
}

export function filterBlueprintRows(rows, { search = '', vendor = '', product = '', domain = '' } = {}) {
  const query = search.trim().toLowerCase()
  return rows.filter((row) => {
    if (vendor && row.vendorKey !== vendor) return false
    if (product && row.product !== product) return false
    if (domain && row.primaryDomain !== domain) return false
    if (query && !row.searchText.includes(query)) return false
    return true
  })
}

export function blueprintFilterOptions(rows) {
  const vendors = new Map()
  const products = new Map()
  const domains = new Map()

  for (const row of rows) {
    vendors.set(row.vendorKey, row.vendorLabel)
    products.set(row.product, row.product)
    domains.set(row.primaryDomain, row.primaryDomainLabel)
  }

  return {
    vendors: [...vendors.entries()]
      .map(([value, label]) => ({ value, label }))
      .sort((a, b) => a.label.localeCompare(b.label)),
    products: [...products.entries()]
      .map(([value, label]) => ({ value, label }))
      .sort((a, b) => a.label.localeCompare(b.label)),
    domains: [...domains.entries()]
      .map(([value, label]) => ({ value, label }))
      .sort((a, b) => a.label.localeCompare(b.label)),
  }
}

/** Vendor → product → domain hierarchy for grouped library UI. */
export function groupBlueprintRows(rows) {
  const vendorMap = new Map()

  for (const row of rows) {
    if (!vendorMap.has(row.vendorKey)) {
      vendorMap.set(row.vendorKey, {
        vendorKey: row.vendorKey,
        vendorLabel: row.vendorLabel,
        products: new Map(),
      })
    }
    const vendorGroup = vendorMap.get(row.vendorKey)

    if (!vendorGroup.products.has(row.product)) {
      vendorGroup.products.set(row.product, {
        product: row.product,
        domains: new Map(),
      })
    }
    const productGroup = vendorGroup.products.get(row.product)

    if (!productGroup.domains.has(row.primaryDomain)) {
      productGroup.domains.set(row.primaryDomain, {
        domain: row.primaryDomain,
        domainLabel: row.primaryDomainLabel,
        items: [],
      })
    }
    productGroup.domains.get(row.primaryDomain).items.push(row)
  }

  return [...vendorMap.values()]
    .sort((a, b) => a.vendorLabel.localeCompare(b.vendorLabel))
    .map((vendorGroup) => ({
      vendorKey: vendorGroup.vendorKey,
      vendorLabel: vendorGroup.vendorLabel,
      count: [...vendorGroup.products.values()].reduce(
        (sum, product) =>
          sum + [...product.domains.values()].reduce((inner, domain) => inner + domain.items.length, 0),
        0
      ),
      products: [...vendorGroup.products.values()]
        .sort((a, b) => a.product.localeCompare(b.product))
        .map((productGroup) => ({
          product: productGroup.product,
          count: [...productGroup.domains.values()].reduce((sum, domain) => sum + domain.items.length, 0),
          domains: [...productGroup.domains.values()]
            .sort((a, b) => a.domainLabel.localeCompare(b.domainLabel))
            .map((domainGroup) => ({
              ...domainGroup,
              items: [...domainGroup.items].sort((a, b) => a.label.localeCompare(b.label)),
            })),
        })),
    }))
}
