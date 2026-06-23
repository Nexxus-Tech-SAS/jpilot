<template>
  <div class="updates-panel flex flex-column gap-4">
    <div class="content-panel content-panel-padded">
      <div class="flex align-items-start justify-content-between gap-3 flex-wrap">
        <div>
          <h2 class="section-title">About JPilot</h2>
          <p class="section-copy">
            Installed version and release checks against GitHub.
          </p>
        </div>
        <div class="version-tags flex align-items-center gap-2 flex-wrap">
          <Tag :value="updateInfo?.display_version || '…'" severity="secondary" />
          <Tag v-if="JPILOT_BETA" value="Beta" severity="warn" />
        </div>
      </div>

      <div v-if="loading" class="mt-4">
        <ProgressSpinner style="width: 2rem; height: 2rem" />
      </div>

      <div v-else class="flex flex-column gap-4 mt-4">
        <Message
          v-if="updateInfo?.update_available"
          severity="warn"
          :closable="false"
        >
          <span>
            <strong>{{ updateInfo.latest_display_version }}</strong> is available
            (you are on {{ updateInfo.display_version }}).
            <a
              v-if="updateInfo.release_url"
              :href="updateInfo.release_url"
              target="_blank"
              rel="noopener noreferrer"
              class="release-link"
            >View release notes</a>
          </span>
        </Message>

        <Message
          v-else-if="updateInfo && !updateInfo.check_error"
          severity="success"
          :closable="false"
        >
          You are on the latest release.
        </Message>

        <Message
          v-if="updateInfo?.check_error"
          severity="info"
          :closable="false"
        >
          {{ updateInfo.check_error }} You can try again later.
        </Message>

        <!-- One-click update button (admin only, shown when update is available) -->
        <div
          v-if="isAdmin && updateInfo?.update_available && !updateRunning && !updateDone"
          class="flex gap-2 align-items-center flex-wrap"
        >
          <Button
            :label="`Update to ${updateInfo.latest_display_version}`"
            icon="pi pi-cloud-download"
            size="small"
            severity="warn"
            :disabled="updateTriggered"
            @click="confirmUpdate"
          />
          <span class="checked-at">Rebuilds the stack on the host — the app will briefly restart.</span>
        </div>

        <!-- Update progress panel -->
        <div v-if="updateTriggered || updateRunning || updateDone" class="update-progress-panel">
          <div class="flex align-items-center gap-2 mb-2">
            <ProgressSpinner
              v-if="updateRunning || (updateTriggered && !updateDone)"
              style="width: 1.25rem; height: 1.25rem"
            />
            <span class="update-progress-title">
              <template v-if="updateStatus?.state === 'success'">Update complete</template>
              <template v-else-if="updateStatus?.state === 'failed'">Update failed</template>
              <template v-else-if="updateStatus?.state === 'running'">Updating…</template>
              <template v-else>Waiting for host agent…</template>
            </span>
          </div>

          <Message
            v-if="updateStatus?.state === 'success'"
            severity="success"
            :closable="false"
            class="mb-2"
          >
            JPilot was updated to {{ updateStatus.target_tag }} successfully.
          </Message>

          <Message
            v-if="updateStatus?.state === 'failed'"
            severity="error"
            :closable="false"
            class="mb-2"
          >
            {{ updateStatus.error || 'Update failed — check host system logs.' }}
          </Message>

          <div v-if="updateStatus?.progress?.length" class="update-log">
            <div
              v-for="(line, i) in updateStatus.progress"
              :key="i"
              class="update-log-line"
            >{{ line }}</div>
          </div>

          <div v-if="updateDone" class="mt-3">
            <Button
              label="Dismiss"
              icon="pi pi-check"
              size="small"
              severity="secondary"
              outlined
              @click="resetUpdateUi"
            />
          </div>
        </div>

        <div class="flex gap-2 flex-wrap">
          <Button
            label="Check for updates"
            icon="pi pi-refresh"
            size="small"
            :loading="checking"
            :disabled="updateRunning"
            @click="runCheck(true)"
          />
          <span v-if="lastCheckedLabel" class="checked-at">{{ lastCheckedLabel }}</span>
        </div>

        <!-- Collapsible CLI tutorial: arm the host auto-updater -->
        <div class="cli-tutorial-wrap">
          <button type="button" class="tutorial-toggle" @click="toggleTutorial">
            <i :class="tutorialOpen ? 'pi pi-chevron-down' : 'pi pi-chevron-right'" />
            <span>Enable auto-updates from the CLI</span>
            <span class="tutorial-toggle-hint">tutorial</span>
          </button>

          <transition name="tut-slide">
            <div v-if="tutorialOpen" class="cli-tutorial">
              <p class="section-copy">
                Run this once on the server (where Docker runs) so the
                <strong>Update</strong> button can rebuild the platform automatically:
              </p>
              <div class="terminal" title="Click to replay" @click="restartTyping">
                <div class="terminal-bar">
                  <span class="term-dot term-dot-r"></span>
                  <span class="term-dot term-dot-y"></span>
                  <span class="term-dot term-dot-g"></span>
                  <span class="terminal-title">host shell</span>
                </div>
                <div class="terminal-body">
                  <div
                    v-for="(row, i) in renderedTutorialLines"
                    :key="i"
                    :class="['term-line', 'term-' + row.kind]"
                  ><span v-if="row.kind === 'cmd'" class="term-prompt">$</span><span>{{ row.visible }}</span><span v-if="i === renderedTutorialLines.length - 1" class="term-cursor"></span></div>
                </div>
              </div>
              <Button
                label="Copy commands"
                icon="pi pi-copy"
                size="small"
                severity="secondary"
                outlined
                class="mt-2"
                @click="copyCommands(tutorialCommands)"
              />
            </div>
          </transition>
        </div>
      </div>
    </div>

    <!-- Confirm dialog -->
    <Dialog
      v-model:visible="showConfirmDialog"
      modal
      header="Confirm update"
      :style="{ width: '28rem' }"
    >
      <p class="confirm-copy">
        This will pull <strong>{{ updateInfo?.latest_display_version }}</strong> from GitHub
        and rebuild the JPilot Docker stack on the host machine.
        The app will be briefly unreachable while it restarts.
      </p>
      <p class="confirm-copy mt-2">
        Your <code>.env</code> configuration and MongoDB data will be preserved.
      </p>
      <template #footer>
        <Button label="Cancel" severity="secondary" outlined @click="showConfirmDialog = false" />
        <Button
          label="Update now"
          icon="pi pi-cloud-download"
          severity="warn"
          :loading="triggerLoading"
          @click="doTriggerUpdate"
        />
      </template>
    </Dialog>

    <div
      v-if="updateInfo?.update_available"
      class="content-panel content-panel-padded"
    >
      <div class="update-layout">
        <div class="update-instructions">
          <h2 class="section-title">How to update</h2>
          <p class="section-copy">{{ updateInfo.update_instructions.summary }}</p>

          <ol class="update-steps mt-4">
            <li v-for="(step, index) in updateInfo.update_instructions.steps" :key="index">
              {{ step }}
            </li>
          </ol>

          <p class="section-copy mt-4">
            From the repository root, run the upgrade helper. It pulls <code>origin/main</code>, asks
            whether to rebuild the <strong>development</strong> or <strong>production</strong> stack, then runs
            <code>docker compose build</code> and <code>up -d</code>. Your <code>.env</code> and MongoDB data
            are kept.
          </p>

          <div class="install-grid mt-4">
            <div class="command-block">
              <div class="command-label">macOS / Linux</div>
              <pre class="command-pre"><code>{{ upgradeLinuxCommands }}</code></pre>
              <Button
                label="Copy"
                icon="pi pi-copy"
                size="small"
                severity="secondary"
                outlined
                class="mt-2"
                @click="copyCommands(upgradeLinuxCommands)"
              />
            </div>

            <div class="command-block">
              <div class="command-label">Windows (PowerShell)</div>
              <pre class="command-pre"><code>{{ upgradeWindowsCommands }}</code></pre>
              <Button
                label="Copy"
                icon="pi pi-copy"
                size="small"
                severity="secondary"
                outlined
                class="mt-2"
                @click="copyCommands(upgradeWindowsCommands)"
              />
            </div>
          </div>

          <p class="section-copy mt-4">
            Alternatively, re-run the bootstrap installer from the project README on the host;
            it updates an existing checkout and rebuilds the stack.
          </p>
        </div>

        <aside class="release-notes-panel">
          <h2 class="section-title">
            {{ releaseNotesTitle }}
          </h2>
          <p v-if="!updateInfo.release_notes" class="section-copy">
            Release notes are not available for this version.
            <a
              v-if="updateInfo.release_url"
              :href="updateInfo.release_url"
              target="_blank"
              rel="noopener noreferrer"
              class="release-link"
            >Open on GitHub</a>
          </p>
          <div v-else class="release-notes-body">
            <ChatMarkdown :content="updateInfo.release_notes" />
          </div>
          <a
            v-if="updateInfo.release_url && updateInfo.release_notes"
            :href="updateInfo.release_url"
            target="_blank"
            rel="noopener noreferrer"
            class="release-link release-notes-github"
          >View on GitHub</a>
        </aside>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import Tag from 'primevue/tag'
import ChatMarkdown from './ChatMarkdown.vue'
import { JPILOT_BETA } from '../config/product'
import { checkForUpdates, getUpdateStatus, triggerUpdate } from '../services/system'

const props = defineProps({
  isAdmin: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update-status'])

const loading = ref(true)
const checking = ref(false)
const updateInfo = ref(null)

// One-click update state
const showConfirmDialog = ref(false)
const triggerLoading = ref(false)
const updateTriggered = ref(false)  // request sent, waiting for agent
const updateRunning = ref(false)    // agent is running
const updateDone = ref(false)       // success or failed
const updateStatus = ref(null)
let pollTimer = null

const upgradeLinuxCommands = './scripts/upgrade.sh'
const upgradeWindowsCommands = '.\\scripts\\upgrade.ps1'

const lastCheckedLabel = computed(() => {
  if (!updateInfo.value?.checked_at) return ''
  const when = new Date(updateInfo.value.checked_at)
  if (Number.isNaN(when.getTime())) return ''
  return `Last checked ${when.toLocaleString()}`
})

const releaseNotesTitle = computed(() => {
  const label =
    updateInfo.value?.release_name ||
    updateInfo.value?.latest_display_version ||
    'Release notes'
  return label.startsWith('Release notes') ? label : `Release notes — ${label}`
})

async function runCheck(force = false) {
  checking.value = true
  try {
    updateInfo.value = await checkForUpdates(force)
    emit('update-status', updateInfo.value)
  } catch (error) {
    updateInfo.value = {
      display_version: updateInfo.value?.display_version || 'unknown',
      check_error: error.response?.data?.detail || 'Could not check for updates.',
      update_available: false,
      update_instructions: { summary: '', steps: [], commands_linux_mac: [], commands_windows: [] }
    }
  } finally {
    checking.value = false
    loading.value = false
  }
}

async function copyCommands(text) {
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    // Clipboard may be blocked; ignore.
  }
}

// ── CLI tutorial (typewriter terminal) ────────────────────────────────────
const tutorialOpen = ref(false)
const tutorialLines = [
  { kind: 'comment', text: '# one-time: arm the host update agent' },
  { kind: 'cmd', text: 'cd /opt/workspace/jpilot' },
  { kind: 'cmd', text: 'sudo ./scripts/auto-updater.sh enable' },
  { kind: 'out', text: '==> Cleaning any existing agent units...' },
  { kind: 'out', text: '==> Auto-update ENABLED.' },
  { kind: 'comment', text: '# done — the Update button now updates JPilot' }
]
const tutorialCommands = 'cd /opt/workspace/jpilot\nsudo ./scripts/auto-updater.sh enable'
const tutorialTotalChars = tutorialLines.reduce((n, l) => n + l.text.length, 0)
const typedChars = ref(0)
let typingTimer = null

const renderedTutorialLines = computed(() => {
  let remaining = typedChars.value
  const rows = []
  for (const line of tutorialLines) {
    const show = Math.min(line.text.length, Math.max(0, remaining))
    rows.push({ kind: line.kind, visible: line.text.slice(0, show) })
    remaining -= line.text.length
    if (remaining <= 0) break
  }
  return rows
})

function stopTyping() {
  if (typingTimer) {
    clearTimeout(typingTimer)
    typingTimer = null
  }
}

function startTyping() {
  stopTyping()
  typedChars.value = 0
  const tick = () => {
    if (typedChars.value < tutorialTotalChars) {
      typedChars.value += 1
      typingTimer = setTimeout(tick, 26)
    } else {
      typingTimer = null
    }
  }
  typingTimer = setTimeout(tick, 220)
}

function toggleTutorial() {
  tutorialOpen.value = !tutorialOpen.value
  if (tutorialOpen.value) startTyping()
  else stopTyping()
}

function restartTyping() {
  if (tutorialOpen.value) startTyping()
}

// ── One-click update ──────────────────────────────────────────────────────

function confirmUpdate() {
  showConfirmDialog.value = true
}

async function doTriggerUpdate() {
  triggerLoading.value = true
  try {
    const result = await triggerUpdate()
    showConfirmDialog.value = false
    updateTriggered.value = true
    updateStatus.value = result.status
    startPolling()
  } catch (err) {
    showConfirmDialog.value = false
    // 409 = already running; show that as the current status.
    const detail = err.response?.data?.detail || 'Could not trigger update.'
    updateTriggered.value = true
    updateStatus.value = { state: 'failed', error: detail, progress: [] }
    updateDone.value = true
  } finally {
    triggerLoading.value = false
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(pollStatus, 3000)
}

function stopPolling() {
  if (pollTimer !== null) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function pollStatus() {
  try {
    const status = await getUpdateStatus()
    updateStatus.value = status

    const state = status.state
    updateRunning.value = state === 'running'

    if (state === 'success' || state === 'failed') {
      stopPolling()
      updateDone.value = true
      updateRunning.value = false
    }
  } catch {
    // Backend may be temporarily unreachable while the stack restarts.
    // Keep retrying; append a note only if we haven't already.
    if (updateStatus.value && !updateStatus.value._retrying) {
      updateStatus.value = {
        ...(updateStatus.value || {}),
        _retrying: true,
        progress: [
          ...(updateStatus.value?.progress || []),
          'Backend unreachable — waiting for stack to come back up…'
        ]
      }
    }
  }
}

function resetUpdateUi() {
  stopPolling()
  updateTriggered.value = false
  updateRunning.value = false
  updateDone.value = false
  updateStatus.value = null
  // Re-check version so the UI reflects the new installed version.
  runCheck(true)
}

onMounted(() => runCheck(false))

onUnmounted(() => {
  stopPolling()
  stopTyping()
})

defineExpose({ refresh: () => runCheck(true) })
</script>

<style scoped>
.updates-panel {
  width: 100%;
}

.section-title {
  font-size: 1.125rem;
  font-weight: 600;
  margin: 0;
}

.section-copy {
  margin: 0.35rem 0 0;
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
  line-height: 1.55;
}

.section-copy code {
  font-size: 0.8125rem;
}

/* ── CLI tutorial ──────────────────────────────────────────────────────── */
.tutorial-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: none;
  border: none;
  padding: 0.2rem 0;
  font: inherit;
  font-size: 0.875rem;
  color: var(--p-primary-color);
  cursor: pointer;
}
.tutorial-toggle:hover { text-decoration: underline; }
.tutorial-toggle-hint {
  font-size: 0.66rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--p-text-muted-color);
  border: 1px solid var(--p-content-border-color);
  border-radius: 999px;
  padding: 0.05rem 0.45rem;
}
.cli-tutorial { margin-top: 0.75rem; }
.terminal {
  border-radius: 0.6rem;
  overflow: hidden;
  border: 1px solid #1f2937;
  background: #0b1020;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
  cursor: pointer;
  max-width: 36rem;
}
.terminal-bar {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 0.75rem;
  background: #11182b;
  border-bottom: 1px solid #1f2937;
}
.term-dot { width: 0.7rem; height: 0.7rem; border-radius: 50%; }
.term-dot-r { background: #ff5f56; }
.term-dot-y { background: #ffbd2e; }
.term-dot-g { background: #27c93f; }
.terminal-title {
  margin-left: 0.5rem;
  font-size: 0.72rem;
  letter-spacing: 0.02em;
  color: #7c8aa5;
}
.terminal-body {
  padding: 0.85rem 1rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.8125rem;
  line-height: 1.7;
  color: #d6deeb;
  min-height: 8rem;
}
.term-line { white-space: pre-wrap; word-break: break-word; }
.term-comment { color: #5f7e97; }
.term-out { color: #7ee787; }
.term-prompt { color: #56d364; margin-right: 0.45rem; user-select: none; }
.term-cursor {
  display: inline-block;
  width: 0.55ch;
  height: 1.05em;
  margin-left: 1px;
  vertical-align: text-bottom;
  background: #d6deeb;
  animation: term-blink 1s steps(1) infinite;
}
@keyframes term-blink { 50% { opacity: 0; } }
.tut-slide-enter-active,
.tut-slide-leave-active { transition: opacity 0.18s ease, transform 0.18s ease; }
.tut-slide-enter-from,
.tut-slide-leave-to { opacity: 0; transform: translateY(-4px); }

.release-link {
  margin-left: 0.35rem;
  color: inherit;
  font-weight: 600;
}

.checked-at {
  align-self: center;
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
}

.update-steps {
  margin: 0;
  padding-left: 1.25rem;
  color: var(--p-text-color);
  line-height: 1.6;
  font-size: 0.875rem;
}

.update-steps li + li {
  margin-top: 0.5rem;
}

.update-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(0, 0.85fr);
  gap: 1.5rem;
  align-items: start;
}

@media (max-width: 991px) {
  .update-layout {
    grid-template-columns: 1fr;
  }
}

.release-notes-panel {
  padding: 1rem 1.15rem;
  border-radius: 0.75rem;
  border: 1px solid var(--p-content-border-color);
  background: var(--app-nested-surface, var(--p-surface-100));
  max-height: min(70vh, 32rem);
  overflow-y: auto;
}

.release-notes-body {
  margin-top: 0.75rem;
  font-size: 0.875rem;
}

.release-notes-body :deep(.chat-markdown) {
  line-height: 1.55;
}

.release-notes-body :deep(.chat-markdown h2),
.release-notes-body :deep(.chat-markdown h3) {
  font-size: 0.9375rem;
  margin-top: 0.75rem;
}

.release-notes-github {
  display: inline-block;
  margin-top: 1rem;
  font-size: 0.8125rem;
}

/* ── One-click update ── */
.update-progress-panel {
  padding: 1rem 1.15rem;
  border-radius: 0.75rem;
  border: 1px solid var(--p-content-border-color);
  background: var(--app-nested-surface, var(--p-surface-100));
}

.update-progress-title {
  font-size: 0.9375rem;
  font-weight: 600;
}

.update-log {
  font-family: ui-monospace, 'Cascadia Code', 'Fira Mono', monospace;
  font-size: 0.78125rem;
  line-height: 1.6;
  padding: 0.75rem;
  border-radius: 0.5rem;
  background: color-mix(in srgb, var(--p-surface-950) 6%, transparent);
  max-height: 16rem;
  overflow-y: auto;
}

:global(.app-dark) .update-log {
  background: rgba(0, 0, 0, 0.25);
}

.update-log-line {
  white-space: pre-wrap;
  word-break: break-word;
}

.confirm-copy {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--p-text-color);
}

.install-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
  align-items: start;
}

@media (max-width: 991px) {
  .install-grid {
    grid-template-columns: 1fr;
  }
}

.command-block {
  padding: 1rem;
  border-radius: 0.75rem;
  border: 1px solid var(--p-content-border-color);
  background: var(--app-nested-surface, var(--p-surface-100));
}

.command-label {
  font-size: 0.8125rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.command-hint {
  margin: 0;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  line-height: 1.45;
}

.command-hint code {
  font-size: 0.6875rem;
}

.command-pre {
  margin: 0;
  padding: 0.75rem;
  border-radius: 0.5rem;
  background: color-mix(in srgb, var(--p-surface-950) 6%, transparent);
  overflow-x: auto;
  font-size: 0.8125rem;
  line-height: 1.5;
}

:global(.app-dark) .command-pre {
  background: rgba(0, 0, 0, 0.25);
}
</style>
