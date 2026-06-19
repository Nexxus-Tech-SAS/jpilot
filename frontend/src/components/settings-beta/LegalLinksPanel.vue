<template>
  <div class="content-panel content-panel-padded">
    <h2 class="section-title">Legal</h2>
    <p class="section-copy">Policies and agreements that govern your use of JPilot.</p>

    <ul class="legal-links mt-4">
      <li>
        <RouterLink to="/legal/privacy">
          <i class="pi pi-shield" /> <span>Privacy Policy</span> <i class="pi pi-external-link" />
        </RouterLink>
      </li>
      <li>
        <RouterLink to="/legal/terms">
          <i class="pi pi-file" /> <span>Terms of Service</span> <i class="pi pi-external-link" />
        </RouterLink>
      </li>
      <li>
        <RouterLink to="/legal/eula">
          <i class="pi pi-key" /> <span>End-User License Agreement</span> <i class="pi pi-external-link" />
        </RouterLink>
      </li>
      <li>
        <RouterLink to="/legal/acceptable-use">
          <i class="pi pi-check-circle" /> <span>Acceptable Use Policy</span> <i class="pi pi-external-link" />
        </RouterLink>
      </li>
    </ul>

    <p class="section-copy mt-4">© {{ new Date().getFullYear() }} Nexxus-Tech SAS · Bogotá D.C., Colombia · contact@nexxus-tech.com</p>
  </div>
</template>

<script setup>
import { RouterLink } from 'vue-router'
</script>

<style scoped>
.section-title {
  font-size: 1.125rem;
  font-weight: 600;
  margin: 0;
}

.section-copy {
  margin: 0.35rem 0 0;
  color: var(--p-text-muted-color);
}

.legal-links {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.legal-links a {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.65rem 0.75rem;
  border-radius: 0.5rem;
  text-decoration: none;
  color: var(--p-text-color);
  border: 1px solid transparent;
}

.legal-links a:hover {
  background: var(--app-nested-surface);
  border-color: var(--p-content-border-color);
}

.legal-links a span {
  flex: 1;
  font-weight: 500;
}

.legal-links a .pi-external-link {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}
</style>
