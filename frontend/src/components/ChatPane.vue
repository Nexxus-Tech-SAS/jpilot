<template>
  <div
    class="chat-pane flex flex-column flex-1"
    :class="{
      'pane-empty': !session.messages.length,
      'pane-generating': isGenerating,
      'chat-pane-beta': uiVariant === 'beta',
      'chat-pane-lab': showBetaLabel,
      'chat-pane-architect': isArchitectPane(),
      'chat-pane-design-panel-open':
        isArchitectPane() && designPanelVisible && !useDetachedDesignPanel
    }"
    @mousedown="markPaneFocused"
    @focusin="markPaneFocused"
  >
    <!-- shared hidden file inputs + attach menu -->
    <input
      ref="imageInputRef"
      id="chat-attach-image"
      name="chatAttachImage"
      type="file"
      accept="image/png,image/jpeg,image/webp,image/gif"
      multiple
      hidden
      @change="onImageSelected"
    />
    <input
      ref="configInputRef"
      id="chat-attach-config"
      name="chatAttachConfig"
      type="file"
      :accept="configAccept"
      multiple
      hidden
      @change="onConfigSelected"
    />
    <Menu ref="attachMenu" :model="attachMenuItems" popup />

    <!-- Beta chat UI (Diamond ChatBox-style) -->
    <template v-if="uiVariant === 'beta'">
      <div class="beta-shell flex flex-column h-full" :class="{ 'beta-shell-compact': showConversationSwitcher }">
        <div class="beta-header" :class="{ 'beta-header-compact': showConversationSwitcher }">
          <div class="beta-header-start">
            <Button
              v-if="showConversationSwitcher"
              v-tooltip.bottom="'App menu'"
              icon="pi pi-bars"
              text
              rounded
              severity="secondary"
              class="beta-header-nav"
              aria-label="Open app menu"
              @click="openAppNav()"
            />
            <div v-if="!showConversationSwitcher" class="beta-header-identity">
              <div class="beta-avatar-wrap">
                <span
                  v-if="showBetaLabel"
                  class="beta-avatar beta-avatar-role"
                  :style="{ '--role-accent': activeRole.accent }"
                  :aria-label="activeRole.label"
                >
                  <i :class="activeRole.icon" aria-hidden="true" />
                </span>
                <img v-else src="/jpilot-favicon.png" alt="JPilot" class="beta-avatar" />
                <span
                  class="beta-status-dot"
                  :class="{
                    'beta-status-active': session.connectedAppliance && isApplianceConnected(),
                    'beta-status-busy': isGenerating,
                    'beta-status-away': session.applianceChoice && !isApplianceConnected()
                  }"
                />
              </div>
              <div class="beta-header-copy">
                <span class="beta-title">
                  <span class="beta-title-brand">JPilot</span>
                  <span class="beta-title-sep" aria-hidden="true"> · </span>
                  <span class="ld-cursor beta-title-role-cursor">{{ activeRole.label }}</span>
                </span>
                <span class="beta-subtitle">{{ betaStatusLine }}</span>
              </div>
            </div>
          </div>

          <div v-if="showConversationSwitcher" class="beta-header-mobile-title">
            <RouterLink to="/" class="beta-header-logo-link" aria-label="JPilot home">
              <JPilotMark class="beta-header-trio-logo" />
            </RouterLink>
            <span
              class="beta-subtitle-compact beta-role-chip"
              :style="{ '--role-chip-accent': activeRole.accent }"
            >
              <i :class="activeRole.icon" class="beta-role-chip-icon" aria-hidden="true" />
              <div class="ld-cursor beta-role-chip-label">{{ activeRole.label }}</div>
            </span>
          </div>

          <div v-if="!showConversationSwitcher" class="beta-header-center">
            <div class="beta-header-center-stack">
              <SelectButton
                :model-value="activeRolePickerId"
                :options="roleOptions"
                option-label="label"
                option-value="id"
                data-key="id"
                :allow-empty="false"
                class="beta-role-toggle"
                :disabled="isGenerating"
                aria-label="JPilot role"
                @update:model-value="onRolePickerChange"
              >
                <template #option="slotProps">
                  <span
                    class="role-toggle-option"
                    :class="{ 'role-toggle-option-persona': slotProps.option.isCustomPersona }"
                    :style="{ '--role-option-accent': slotProps.option.accent }"
                  >
                    <i
                      :class="slotProps.option.icon"
                      v-tooltip.bottom="roleOptionTooltip(slotProps.option)"
                      :aria-label="slotProps.option.label"
                    />
                  </span>
                </template>
              </SelectButton>
              <div v-if="roleProviders.length" class="beta-header-model">
                <Select
                  v-if="roleProviders.length > 1"
                  v-model="session.providerId"
                  :options="providerOptions"
                  option-label="label"
                  option-value="value"
                  placeholder="Model"
                  class="beta-header-model-select"
                  :disabled="isGenerating"
                  aria-label="AI model"
                />
                <span
                  v-else
                  v-tooltip.bottom="activeProviderTooltip"
                  class="beta-header-model-name"
                >
                  <i class="pi pi-sparkles" aria-hidden="true" />
                  {{ activeProviderDisplayLabel }}
                </span>
              </div>
            </div>
          </div>

          <div class="beta-header-actions">
            <Button
              v-if="isGenerating"
              v-tooltip.bottom="'Stop generating'"
              icon="pi pi-stop"
              severity="danger"
              :text="showConversationSwitcher"
              :outlined="!showConversationSwitcher"
              rounded
              class="beta-action-stop"
              @click="stopChat"
            />
            <template v-if="!showConversationSwitcher">
              <Button
                v-if="webSearchAvailable && !isGenerating"
                v-tooltip.bottom="session.webSearch ? 'Web search on' : 'Web search off'"
                :icon="session.webSearch ? 'pi pi-globe' : 'pi pi-ban'"
                outlined
                severity="secondary"
                rounded
                class="beta-action-websearch"
                @click="session.webSearch = !session.webSearch"
              />
              <Button
                v-if="session.messages.length"
                v-tooltip.bottom="'Clear conversation'"
                icon="pi pi-eraser"
                outlined
                severity="secondary"
                rounded
                :disabled="isGenerating"
                aria-label="Clear conversation"
                class="beta-action-clear"
                @click="clearBetaConversation"
              />
            </template>
            <Button
              v-if="showConversationSwitcher && !isGenerating"
              v-tooltip.bottom="'Chats'"
              icon="pi pi-comments"
              text
              rounded
              severity="secondary"
              aria-label="Open chats"
              class="beta-action-chats"
              @click="$emit('open-conversations')"
            />
            <Button
              v-if="isArchitectPane()"
              v-tooltip.bottom="designPanelVisible ? 'Hide Document Editor' : 'Show Document Editor'"
              :icon="designPanelVisible ? 'pi pi-eye-slash' : 'pi pi-file-edit'"
              text
              rounded
              severity="secondary"
              class="beta-header-design-toggle"
              aria-label="Toggle Document Editor"
              @click="toggleDesignPanel"
            />
            <Button
              v-if="showChatSidebarToggle"
              v-tooltip.bottom="chatSidebarVisible ? 'Hide chat list' : 'Show chat list'"
              :icon="chatSidebarVisible ? 'pi pi-angle-left' : 'pi pi-comments'"
              :text="showConversationSwitcher"
              :outlined="!showConversationSwitcher"
              severity="secondary"
              rounded
              :aria-label="chatSidebarVisible ? 'Hide chat list' : 'Show chat list'"
              @click="$emit('toggle-chat-sidebar')"
            />
            <Button
              v-tooltip.bottom="'Chat options'"
              icon="pi pi-ellipsis-v"
              :text="showConversationSwitcher"
              :outlined="!showConversationSwitcher"
              severity="secondary"
              rounded
              class="beta-action-options"
              @click="toggleBetaOptions"
            />
          </div>
        </div>

        <Popover ref="betaOptionsOp" class="beta-options-popover">
          <div class="beta-options-panel">
            <div class="beta-options-meta">
              <span class="beta-options-hint">Saved on this device until you delete them</span>
            </div>

            <div v-if="showConversationSwitcher" class="beta-options-group beta-options-group-roles">
              <span class="beta-options-label">Role</span>
              <div class="beta-role-picker-mobile">
                <div class="beta-role-picker-base" role="group" aria-label="JPilot role">
                  <button
                    v-for="role in baseRoleOptions"
                    :key="role.id"
                    type="button"
                    class="beta-role-picker-btn"
                    :class="{ 'beta-role-picker-btn-active': activeRolePickerId === role.id }"
                    :style="{ '--role-option-accent': role.accent }"
                    :disabled="isGenerating"
                    :aria-label="role.label"
                    :aria-pressed="activeRolePickerId === role.id"
                    @click="onRolePickerChange(role.id)"
                  >
                    <span class="role-toggle-option">
                      <i :class="role.icon" aria-hidden="true" />
                    </span>
                    <span class="beta-role-toggle-label">{{ role.label }}</span>
                    <span v-if="role.capability" class="beta-role-toggle-capability">{{ role.capability }}</span>
                  </button>
                </div>

                <div v-if="customPersonaOptions.length" class="beta-role-picker-personas">
                  <span class="beta-role-picker-personas-label">Personas</span>
                  <div class="beta-role-picker-personas-grid" role="group" aria-label="Custom personas">
                    <button
                      v-for="persona in customPersonaOptions"
                      :key="persona.id"
                      type="button"
                      class="beta-role-picker-btn beta-role-picker-btn-persona"
                      :class="{ 'beta-role-picker-btn-active': activeRolePickerId === persona.id }"
                      :style="{ '--role-option-accent': persona.accent }"
                      :disabled="isGenerating"
                      :aria-label="persona.label"
                      :aria-pressed="activeRolePickerId === persona.id"
                      @click="onRolePickerChange(persona.id)"
                    >
                      <span class="role-toggle-option role-toggle-option-persona">
                        <i :class="persona.icon" aria-hidden="true" />
                      </span>
                      <span class="beta-role-toggle-label">{{ persona.label }}</span>
                      <span v-if="persona.capability" class="beta-role-toggle-capability">{{ persona.capability }}</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="showConversationSwitcher && webSearchAvailable" class="beta-options-group">
              <span class="beta-options-label">Web search</span>
              <Button
                :label="session.webSearch ? 'On' : 'Off'"
                :icon="session.webSearch ? 'pi pi-globe' : 'pi pi-ban'"
                severity="secondary"
                outlined
                class="w-full"
                @click="session.webSearch = !session.webSearch"
              />
            </div>

            <div v-if="showConversationSwitcher && session.messages.length" class="beta-options-group">
              <Button
                label="Clear conversation"
                icon="pi pi-eraser"
                severity="secondary"
                outlined
                class="w-full"
                :disabled="isGenerating"
                @click="clearBetaConversation(); closeBetaOptions()"
              />
            </div>

            <div class="beta-options-group">
              <span class="beta-options-label">Chat window transparency</span>
              <div class="beta-transparency-row">
                <Slider
                  v-model="chatPanelTransparency"
                  :min="0"
                  :max="100"
                  class="beta-transparency-slider"
                  aria-label="Chat window transparency"
                  @update:model-value="onChatPanelTransparencyChange"
                />
                <span class="beta-transparency-value">{{ chatPanelTransparency }}%</span>
              </div>
            </div>

            <div class="beta-options-group">
              <span class="beta-options-label">Conversations transparency</span>
              <div class="beta-transparency-row">
                <Slider
                  v-model="chatSidebarTransparency"
                  :min="0"
                  :max="100"
                  class="beta-transparency-slider"
                  aria-label="Conversations list transparency"
                  @update:model-value="onChatSidebarTransparencyChange"
                />
                <span class="beta-transparency-value">{{ chatSidebarTransparency }}%</span>
              </div>
            </div>

            <div class="beta-options-group">
              <span class="beta-options-label">Background</span>
              <div class="beta-bg-picker">
                <button
                  v-for="bg in betaBackgrounds"
                  :key="bg.id"
                  type="button"
                  class="beta-bg-thumb beta-bg-thumb-animated"
                  :class="{
                    'beta-bg-thumb-active': betaBackground === bg.id,
                    'beta-bg-thumb-theme': bg.base === 'theme'
                  }"
                  :aria-label="`${bg.label} (${bg.base} background)`"
                  @click="chooseBetaBackground(bg.id)"
                >
                  <BetaChatBackground :background-id="bg.id" preview />
                  <span class="beta-bg-thumb-label">{{ bg.label }}</span>
                </button>
                <button
                  type="button"
                  class="beta-bg-thumb beta-bg-thumb-none"
                  :class="{ 'beta-bg-thumb-active': betaBackground === 'none' }"
                  aria-label="Plain background"
                  @click="chooseBetaBackground('none')"
                >
                  None
                </button>
              </div>
            </div>

            <div class="beta-options-group">
              <span class="beta-options-label">Appliance</span>
              <Select
                v-model="session.applianceChoice"
                :options="roleApplianceOptions"
                option-value="name"
                :placeholder="roleNeedsAppliance ? 'Appliance' : 'Appliance (optional)'"
                class="beta-select beta-select-appliance w-full"
                :disabled="isGenerating || connecting || !roleApplianceOptions.length"
                :option-disabled="(appliance) => isApplianceDisabledForRole(appliance, session.role)"
                @change="onApplianceChange"
              >
                <template #option="{ option }">
                  <ApplianceNameLabel :appliance="option" />
                </template>
                <template #value="{ placeholder }">
                  <ApplianceNameLabel v-if="selectedAppliance" :appliance="selectedAppliance" />
                  <span v-else>{{ placeholder }}</span>
                </template>
              </Select>
            </div>
            <div v-if="roleProviders.length > 1" class="beta-options-group">
              <span class="beta-options-label">Model</span>
              <Select
                v-model="session.providerId"
                :options="providerOptions"
                option-label="label"
                option-value="value"
                placeholder="LLM"
                class="beta-select w-full"
                :disabled="isGenerating"
              />
            </div>
            <div v-if="activeProvider" class="beta-options-group beta-options-context">
              <ContextUsageRing
                :percent-used="contextUsage.percentUsed"
                :prompt-tokens="contextUsage.promptTokens"
                :context-token-limit="contextUsage.contextTokenLimit"
                :trimmed-count="contextUsage.trimmedCount"
                :max-history-messages="contextUsage.maxHistoryMessages"
                :model="activeProvider.model"
              />
            </div>
            <div class="beta-options-actions">
              <Button
                label="JPilot settings"
                icon="pi pi-cog"
                size="small"
                severity="secondary"
                outlined
                @click="router.push('/settings?section=jpilot'); closeBetaOptions()"
              />
            </div>
          </div>
        </Popover>

        <div ref="messagesEl" class="beta-messages user-message-container">
          <div v-if="!session.messages.length" class="beta-empty" :class="{ 'beta-empty-welcome': showBetaLabel }">
            <template v-if="!showBetaLabel">
              <p class="beta-empty-title">{{ showConversationSwitcher ? 'What can I help with?' : `Ask JPilot — ${activeRole.label}` }}</p>
              <p class="beta-empty-hint">{{ activeRole.description }}</p>
              <div v-if="showConversationSwitcher" class="beta-mobile-prompts">
                <button
                  v-for="prompt in mobileQuickPrompts"
                  :key="prompt.id"
                  type="button"
                  class="beta-mobile-prompt"
                  :disabled="chatInputDisabled"
                  @click="onMobileQuickPrompt(prompt.text)"
                >
                  {{ prompt.label }}
                </button>
              </div>
            </template>
            <BetaWelcome
              v-else
              :active-role="session.role"
              :provider-name="activeProviderName"
              :ready="ready"
              :disabled="chatInputDisabled"
              @select-persona="onSelectPersona"
              @select-skill="onSelectSkill"
            />
          </div>

          <template v-else>
            <div
              v-for="(msg, index) in session.messages"
              :key="index"
              class="beta-msg-row"
              :class="msg.role === 'user' ? 'beta-msg-row-user' : 'beta-msg-row-assistant'"
              :style="{ '--msg-index': index }"
            >
              <div
                v-if="msg.roleSwitchNotice"
                class="role-switch-notice"
                :class="`role-switch-notice-${msg.roleSwitchNotice.toRole}`"
              >
                <i :class="msg.roleSwitchNotice.icon" aria-hidden="true" />
                <span>
                  Switched to <strong>{{ msg.roleSwitchNotice.label }}</strong>
                  — you chose to handle this request there.
                </span>
              </div>

              <div v-else-if="msg.role !== 'user'" class="beta-msg-grid beta-msg-grid-assistant">
                <div class="beta-msg-avatar-col">
                  <span
                    v-if="showBetaLabel"
                    class="beta-msg-avatar beta-msg-avatar-role"
                    :style="{ '--role-accent': activeRole.accent }"
                    :aria-label="activeRole.label"
                  >
                    <i :class="activeRole.icon" aria-hidden="true" />
                  </span>
                  <img v-else src="/jpilot-favicon.png" alt="JPilot" class="beta-msg-avatar" />
                </div>
                <div class="beta-msg-content-col">
                  <p class="beta-message-author">JPilot</p>
                  <div v-if="msg.attachments?.length" class="chat-attachments beta-attachments">
                    <div v-for="(a, ai) in msg.attachments" :key="ai" class="attachment-chip">
                      <img v-if="a.kind === 'image' && a.data" :src="attachmentPreviewUrl(a)" :alt="a.name" class="attachment-thumb" />
                      <i v-else class="pi pi-file" />
                      <span>{{ a.name }}</span>
                    </div>
                  </div>
                  <div v-if="assistantView(msg).content || msg.designDocRevision" :class="{ 'chat-error-block': msg.isError }">
                    <ArchitectDeliverableCard
                      v-if="msg.designDocRevision"
                      :revision="msg.designDocRevision"
                      :type="session.designDocument?.type"
                      class="mb-2"
                      @open-panel="openDesignPanel"
                    />
                    <span
                      v-if="assistantView(msg).content"
                      class="beta-bubble beta-bubble-assistant"
                      :class="{ 'architect-summary-bubble': msg.designDocRevision }"
                    >
                      <ChatMarkdown compact :content="assistantView(msg).content" />
                    </span>
                    <div
                      v-if="isArchitectPane() && msg.designDocRevision && session.designDocument?.markdown"
                      class="design-doc-download"
                    >
                      <Button
                        v-if="canSendDeliverableToOperator(designDocumentHandoffContent())"
                        label="Send to Operator"
                        icon="pi pi-arrow-right"
                        size="small"
                        :disabled="isGenerating"
                        @click="sendDesignToOperator()"
                      />
                      <Button
                        :label="architectDeliverableDownloadLabel(designDocumentHandoffContent())"
                        icon="pi pi-download"
                        size="small"
                        outlined
                        :disabled="isGenerating"
                        @click="downloadDesignDocumentFromPanel()"
                      />
                    </div>
                  </div>
                  <span v-else-if="msg.content" class="beta-bubble beta-bubble-assistant">{{ msg.content }}</span>
                  <div v-if="msg.webSources?.length" class="web-sources">
                    <span class="web-badge"><i class="pi pi-globe" /> Web</span>
                    <a
                      v-for="src in msg.webSources"
                      :key="src.url"
                      :href="src.url"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="web-source-link"
                    >
                      {{ hostOf(src.url) }}
                    </a>
                  </div>
                  <ChatAppliancePicker
                    v-if="msg.appliancePicker"
                    :appliances="msg.appliances || []"
                    :role="session.role"
                    :loading="msg.pickerLoading"
                    :connecting="connecting"
                    @select="connectAppliance"
                  />
                  <ChatConfigForm
                    v-if="assistantView(msg).inputForm && !assistantView(msg).formSubmitted"
                    :form="assistantView(msg).inputForm"
                    :submitting="isGenerating && submittingFormIndex === index"
                    @submit="(values) => submitConfigForm(values, index)"
                  />
                  <ChatRoleSwitchPrompt
                    v-if="msg.roleSwitchPrompt"
                    :prompt="msg.roleSwitchPrompt"
                    :disabled="isGenerating"
                    @stay="stayInCurrentRole"
                    @switch="acceptRoleSwitch"
                  />
                  <ChatDeploymentSubtasks
                    :subtasks="msg.deploymentSubtasks || msg.deploymentContinuation?.subtasks"
                    :title="msg.progressTitle || (session.role === 'architect' ? 'Planning in progress' : 'Operation progress')"
                  />
                  <div
                    v-if="msg.deploymentContinuation?.required && !isGenerating"
                    class="deployment-continue-actions"
                  >
                    <Button
                      label="Continue deployment"
                      icon="pi pi-play"
                      size="small"
                      :disabled="isGenerating"
                      @click="resumeDeployment"
                    />
                  </div>
                  <ChatBlueprintSuggestion
                    v-if="msg.blueprintSuggestion && !msg.blueprintSuggestionDismissed && !isGenerating"
                    :suggestion="msg.blueprintSuggestion"
                    :disabled="isGenerating"
                    @apply="applyBlueprintSuggestion(msg)"
                    @skip="skipBlueprintSuggestion(msg)"
                  />
                  <ChatToolTrace v-if="msg.toolCalls?.length" :tools="msg.toolCalls" />
                  <p class="beta-message-time">
                    <span
                      v-if="formatMessageGenerationStats(msg.generationStats)"
                      class="beta-message-meta"
                    >
                      {{ formatMessageGenerationStats(msg.generationStats) }}
                      <span class="beta-message-meta-sep" aria-hidden="true">·</span>
                    </span>
                    {{ formatMessageTime(msg) }}
                    <i class="pi pi-check beta-check-icon" />
                  </p>
                </div>
              </div>

              <div v-else class="beta-msg-grid beta-msg-grid-user">
                <div class="beta-msg-content-col beta-msg-content-user">
                  <div v-if="msg.attachments?.length" class="chat-attachments beta-attachments">
                    <div v-for="(a, ai) in msg.attachments" :key="ai" class="attachment-chip">
                      <img v-if="a.kind === 'image' && a.data" :src="attachmentPreviewUrl(a)" :alt="a.name" class="attachment-thumb" />
                      <i v-else class="pi pi-file" />
                      <span>{{ a.name }}</span>
                    </div>
                  </div>
                  <span v-if="msg.content" class="beta-bubble beta-bubble-user">{{ displayContent(msg) }}</span>
                  <p class="beta-message-time">
                    {{ formatMessageTime(msg) }}
                    <i class="pi pi-check beta-check-icon" />
                  </p>
                </div>
              </div>
            </div>

            <div v-if="isGenerating" class="beta-msg-grid beta-msg-grid-assistant beta-msg-generating">
              <div class="beta-msg-avatar-col">
                <span
                  v-if="showBetaLabel"
                  class="beta-msg-avatar beta-msg-avatar-role"
                  :style="{ '--role-accent': activeRole.accent }"
                  :aria-label="activeRole.label"
                >
                  <i :class="activeRole.icon" aria-hidden="true" />
                </span>
                <img v-else src="/jpilot-favicon.png" alt="JPilot" class="beta-msg-avatar" />
              </div>
              <div class="beta-msg-content-col">
                <div class="beta-bubble beta-bubble-assistant beta-bubble-loading">
                  <ProgressSpinner style="width: 1.25rem; height: 1.25rem" stroke-width="4" />
                  <div class="generation-status">
                    <span class="generation-label">{{ generationStatus.label }}</span>
                    <span class="generation-meta">{{ generationStatusMeta(generationStatus) }}</span>
                  </div>
                  <ChatDeploymentSubtasks
                    v-if="liveDeploymentSubtasks.length"
                    :subtasks="liveDeploymentSubtasks"
                    :title="liveProgressTitle"
                  />
                </div>
              </div>
            </div>
          </template>

          <AskJpilotCommandMenu
            v-if="!showBetaLabel"
            ref="commandMenuRef"
            variant="beta"
            :headless="session.messages.length > 0"
            :show-trigger="!showConversationSwitcher"
            :show-inline-preview="!showConversationSwitcher"
            :active-role="session.role"
            :appliance-vendor="commandMenuVendor"
            :disabled="chatInputDisabled"
            @pick="onCommandPick"
          />

          <template v-if="!showBetaLabel">
            <p v-if="!session.messages.length && !ready" class="beta-empty-note">
              No LLM assigned to {{ activeRole.label }} — configure one in Settings → AI Providers.
            </p>
            <p v-else-if="!session.messages.length && activeProviderName && !showConversationSwitcher" class="beta-empty-note">
              <i class="pi pi-sparkles" aria-hidden="true" />
              Using <strong>{{ activeProviderName }}</strong>
            </p>
            <p v-if="!session.messages.length && !showConversationSwitcher" class="beta-empty-note chat-support-note">
              <i class="pi pi-life-ring" aria-hidden="true" />
              Need help? Email
              <a href="mailto:support@nexxus-tech.com">support@nexxus-tech.com</a>
              or visit
              <a href="https://www.nexxus-tech.com" target="_blank" rel="noopener noreferrer">nexxus-tech.com</a>.
            </p>
          </template>
        </div>

        <div v-if="pendingAttachments.length" class="pending-attachments beta-pending">
          <div v-for="(a, i) in pendingAttachments" :key="i" class="pending-attachment">
            <img v-if="a.kind === 'image'" :src="attachmentPreviewUrl(a)" :alt="a.name" class="pending-thumb" />
            <i v-else class="pi pi-file" />
            <span class="pending-name">{{ a.name }}</span>
            <Button icon="pi pi-times" text rounded size="small" @click="removeAttachment(i)" />
          </div>
        </div>

        <div class="beta-footer" :class="{ 'beta-footer-compact': showConversationSwitcher }">
          <div class="beta-composer">
            <Button
              v-if="!showBetaLabel"
              v-tooltip.top="'Browse recommended actions'"
              icon="pi pi-search"
              severity="secondary"
              text
              rounded
              class="beta-composer-icon"
              :disabled="chatInputDisabled"
              @click="openCommandMenu"
            />
            <InputText
              ref="betaComposerRef"
              id="beta-message"
              name="message"
              v-model="session.input"
              type="text"
              class="beta-input beta-composer-input flex-1 w-full"
              :placeholder="showConversationSwitcher ? 'Message JPilot…' : rolePlaceholder"
              :disabled="chatInputDisabled"
              @keydown.enter="sendMessage()"
            />
            <Button
              v-tooltip.top="'Attach file'"
              icon="pi pi-paperclip"
              severity="secondary"
              text
              rounded
              class="beta-composer-icon"
              :disabled="chatInputDisabled"
              @click="toggleAttachMenu"
            />
            <Button
              v-if="showConversationSwitcher"
              icon="pi pi-arrow-up"
              rounded
              class="beta-composer-send"
              aria-label="Send"
              :disabled="sendDisabled"
              @click="sendMessage()"
            />
          </div>
          <div v-if="!showConversationSwitcher" class="beta-footer-actions">
            <Button
              v-if="showCalibrationOffer"
              v-tooltip.top="'Send to Calibration Studio'"
              icon="pi pi-sliders-h"
              severity="secondary"
              outlined
              class="beta-footer-calibration"
              aria-label="Send to Calibration Studio"
              :disabled="calibrationSubmitting"
              @click="openCalibrationDialog"
            />
            <Button
              v-if="!showBetaLabel"
              v-tooltip.top="'Browse recommended actions (⌘K)'"
              icon="pi pi-search"
              severity="secondary"
              outlined
              class="beta-footer-browse"
              :disabled="chatInputDisabled"
              @click="openCommandMenu"
            />
            <Button
              v-tooltip.top="'Attach file'"
              icon="pi pi-paperclip"
              severity="secondary"
              outlined
              class="beta-footer-attach"
              :disabled="chatInputDisabled"
              @click="toggleAttachMenu"
            />
            <Button
              label="Send"
              icon="pi pi-send"
              class="beta-footer-send"
              :disabled="sendDisabled"
              @click="sendMessage()"
            />
          </div>
        </div>
      </div>
    </template>

    <!-- Classic chat UI -->
    <template v-else>
    <div class="pane-toolbar">
      <SelectButton
        :model-value="activeRolePickerId"
        :options="roleOptions"
        option-label="label"
        option-value="id"
        data-key="id"
        :allow-empty="false"
        class="pane-role-toggle"
        :disabled="isGenerating"
        aria-label="JPilot role"
        @update:model-value="onRolePickerChange"
      >
        <template #option="slotProps">
          <span
            class="role-toggle-option"
            :class="{ 'role-toggle-option-persona': slotProps.option.isCustomPersona }"
            :style="{ '--role-option-accent': slotProps.option.accent }"
          >
            <i
              :class="slotProps.option.icon"
              v-tooltip.bottom="roleOptionTooltip(slotProps.option)"
              :aria-label="slotProps.option.label"
            />
          </span>
        </template>
      </SelectButton>
      <Select
        v-model="session.applianceChoice"
        :options="roleApplianceOptions"
        option-value="name"
        :placeholder="roleNeedsAppliance ? 'Appliance' : 'Appliance (optional)'"
        class="pane-select pane-select-appliance"
        :disabled="isGenerating || connecting || !roleApplianceOptions.length"
        :option-disabled="(appliance) => isApplianceDisabledForRole(appliance, session.role)"
        @change="onApplianceChange"
      >
        <template #option="{ option }">
          <ApplianceNameLabel :appliance="option" />
        </template>
        <template #value="{ value, placeholder }">
          <ApplianceNameLabel v-if="selectedAppliance" :appliance="selectedAppliance" />
          <span v-else>{{ placeholder }}</span>
        </template>
      </Select>
      <div v-if="roleProviders.length" class="pane-llm">
        <Select
          v-if="roleProviders.length > 1"
          v-model="session.providerId"
          :options="providerOptions"
          option-label="label"
          option-value="value"
          placeholder="LLM"
          class="pane-select pane-select-llm"
          :disabled="isGenerating"
        />
        <span
          v-else
          v-tooltip.bottom="activeProviderTooltip"
          class="pane-llm-name"
        >
          <i class="pi pi-sparkles" aria-hidden="true" />
          {{ activeProviderName }}
        </span>
      </div>
      <ContextUsageRing
        v-if="activeProvider"
        :percent-used="contextUsage.percentUsed"
        :prompt-tokens="contextUsage.promptTokens"
        :context-token-limit="contextUsage.contextTokenLimit"
        :trimmed-count="contextUsage.trimmedCount"
        :max-history-messages="contextUsage.maxHistoryMessages"
        :model="activeProvider.model"
      />
      <span class="pane-spacer" />
      <span
        v-if="session.connectedAppliance && isApplianceConnected()"
        v-tooltip.bottom="connectedApplianceTooltip"
        class="pane-connected"
      >
        <i class="pi pi-check-circle" /> {{ session.connectedAppliance }}
      </span>
      <span
        v-else-if="session.applianceChoice && !roleNeedsAppliance"
        v-tooltip.bottom="'Planning reference — no live connection required'"
        class="pane-appliance-ref"
      >
        <i class="pi pi-compass" /> {{ session.applianceChoice }}
      </span>
      <span
        v-else-if="session.applianceChoice && roleNeedsAppliance"
        v-tooltip.bottom="'Selected appliance is not connected yet'"
        class="pane-disconnected"
      >
        <i class="pi pi-exclamation-circle" /> {{ session.applianceChoice }}
      </span>
      <Button
        v-if="isGenerating"
        v-tooltip.bottom="'Stop generating'"
        label="Stop"
        icon="pi pi-stop"
        size="small"
        severity="danger"
        outlined
        @click="stopChat"
      />
      <Button
        v-if="webSearchAvailable && !isGenerating"
        v-tooltip.bottom="session.webSearch ? 'Web search: on (official domains, only when docs fall short). Click to disable.' : 'Web search: off for this chat. Click to enable.'"
        :icon="session.webSearch ? 'pi pi-globe' : 'pi pi-ban'"
        text
        rounded
        size="small"
        :class="{ 'websearch-off': !session.webSearch }"
        @click="session.webSearch = !session.webSearch"
      />
      <Button
        v-if="isArchitectPane()"
        v-tooltip.bottom="designPanelVisible ? 'Hide Document Editor' : 'Show Document Editor'"
        :icon="designPanelVisible ? 'pi pi-eye-slash' : 'pi pi-file-edit'"
        text
        rounded
        size="small"
        @click="toggleDesignPanel"
      />
      <Button
        v-if="session.messages.length"
        v-tooltip.bottom="'Clear conversation'"
        icon="pi pi-eraser"
        text
        rounded
        size="small"
        :disabled="isGenerating"
        @click="clearConversation"
      />
      <Button
        v-if="canClose"
        v-tooltip.bottom="'Close chat'"
        icon="pi pi-times"
        text
        rounded
        size="small"
        @click="$emit('close')"
      />
    </div>

    <!-- EMPTY STATE: glass command-menu "ask" panel -->
    <div v-if="!session.messages.length" class="ask-hero">
      <div class="glass-card">
        <div class="glass-head">
          <i class="pi pi-sparkles" />
          <span>Ask JPilot — {{ activeRole.label }}</span>
        </div>
        <p class="glass-role-hint">{{ activeRole.description }}</p>
        <div class="glass-input" @click="focusAskInput">
          <i class="pi pi-search glass-input-icon" />
          <input
            ref="askInputRef"
            id="ask-message"
            name="message"
            v-model="session.input"
            type="text"
            class="glass-input-field"
            :placeholder="rolePlaceholder"
            :disabled="chatInputDisabled"
            @keydown.enter.prevent="sendMessage()"
          />
          <button
            class="glass-attach"
            type="button"
            :disabled="chatInputDisabled"
            @click="toggleAttachMenu"
          >
            <i class="pi pi-paperclip" />
          </button>
          <span class="kbd">⏎</span>
        </div>

        <div v-if="pendingAttachments.length" class="pending-attachments glass-pending">
          <div v-for="(a, i) in pendingAttachments" :key="i" class="pending-attachment">
            <img v-if="a.kind === 'image'" :src="attachmentPreviewUrl(a)" :alt="a.name" class="pending-thumb" />
            <i v-else class="pi pi-file" />
            <span class="pending-name">{{ a.name }}</span>
            <Button icon="pi pi-times" text rounded size="small" @click="removeAttachment(i)" />
          </div>
        </div>

        <AskJpilotCommandMenu
          ref="commandMenuRef"
          :active-role="session.role"
          :appliance-vendor="commandMenuVendor"
          :disabled="isGenerating || !ready"
          @pick="onCommandPick"
        />

        <p v-if="!ready" class="glass-hint">
          No LLM assigned to {{ activeRole.label }} — configure one in Settings → AI Providers.
        </p>
        <p v-else-if="activeProviderName" class="glass-hint glass-llm-hint">
          <i class="pi pi-sparkles" aria-hidden="true" />
          Using <strong>{{ activeProviderName }}</strong> for {{ activeRole.label }}
        </p>
        <p class="glass-hint chat-support-note">
          <i class="pi pi-life-ring" aria-hidden="true" />
          Need help? Email
          <a href="mailto:support@nexxus-tech.com">support@nexxus-tech.com</a>
          or visit
          <a href="https://www.nexxus-tech.com" target="_blank" rel="noopener noreferrer">nexxus-tech.com</a>.
        </p>
      </div>
    </div>

    <!-- ACTIVE CONVERSATION -->
    <template v-else>
      <div ref="messagesEl" class="chat-messages flex-1">
        <template v-for="(msg, index) in session.messages" :key="index">
          <div
            v-if="msg.roleSwitchNotice"
            class="role-switch-notice"
            :class="`role-switch-notice-${msg.roleSwitchNotice.toRole}`"
          >
            <i :class="msg.roleSwitchNotice.icon" aria-hidden="true" />
            <span>
              Switched to <strong>{{ msg.roleSwitchNotice.label }}</strong>
              — you chose to handle this request there.
            </span>
          </div>

          <div
            v-else
            class="chat-message"
            :class="msg.role === 'user' ? 'chat-message-user' : 'chat-message-assistant'"
          >
          <div class="chat-bubble">
            <div class="chat-role">{{ msg.role === 'user' ? 'You' : 'JPilot' }}</div>
            <div v-if="msg.attachments?.length" class="chat-attachments mb-2">
              <div v-for="(a, ai) in msg.attachments" :key="ai" class="attachment-chip">
                <img v-if="a.kind === 'image' && a.data" :src="attachmentPreviewUrl(a)" :alt="a.name" class="attachment-thumb" />
                <i v-else class="pi pi-file" />
                <span>{{ a.name }}</span>
              </div>
            </div>
            <div v-if="assistantView(msg).content || msg.designDocRevision" :class="{ 'chat-error-block': msg.isError }">
              <ArchitectDeliverableCard
                v-if="msg.designDocRevision"
                :revision="msg.designDocRevision"
                :type="session.designDocument?.type"
                class="mb-2"
                @open-panel="openDesignPanel"
              />
              <ChatMarkdown v-if="assistantView(msg).content" :content="assistantView(msg).content" />
              <div
                v-if="isArchitectPane() && msg.designDocRevision && session.designDocument?.markdown"
                class="design-doc-download"
              >
                <Button
                  v-if="canSendDeliverableToOperator(designDocumentHandoffContent())"
                  label="Send to Operator"
                  icon="pi pi-arrow-right"
                  size="small"
                  :disabled="isGenerating"
                  @click="sendDesignToOperator()"
                />
                <Button
                  :label="architectDeliverableDownloadLabel(designDocumentHandoffContent())"
                  icon="pi pi-download"
                  size="small"
                  outlined
                  :disabled="isGenerating"
                  @click="downloadDesignDocumentFromPanel()"
                />
              </div>
            </div>
            <div v-else-if="msg.content" class="chat-content">{{ displayContent(msg) }}</div>
            <div v-if="msg.webSources?.length" class="web-sources">
              <span class="web-badge" v-tooltip.top="'This reply used live web results from allowed domains'">
                <i class="pi pi-globe" /> Web
              </span>
              <a
                v-for="src in msg.webSources"
                :key="src.url"
                :href="src.url"
                target="_blank"
                rel="noopener noreferrer"
                class="web-source-link"
                :title="src.title"
              >
                {{ hostOf(src.url) }}
              </a>
            </div>
            <ChatAppliancePicker
              v-if="msg.appliancePicker"
              :appliances="msg.appliances || []"
              :role="session.role"
              :loading="msg.pickerLoading"
              :connecting="connecting"
              @select="connectAppliance"
            />
            <ChatConfigForm
              v-if="assistantView(msg).inputForm && !assistantView(msg).formSubmitted"
              :form="assistantView(msg).inputForm"
              :submitting="isGenerating && submittingFormIndex === index"
              @submit="(values) => submitConfigForm(values, index)"
            />
            <ChatRoleSwitchPrompt
              v-if="msg.roleSwitchPrompt"
              :prompt="msg.roleSwitchPrompt"
              :disabled="isGenerating"
              @stay="stayInCurrentRole"
              @switch="acceptRoleSwitch"
            />
            <ChatDeploymentSubtasks
              :subtasks="msg.deploymentSubtasks || msg.deploymentContinuation?.subtasks"
              :title="msg.progressTitle || (session.role === 'architect' ? 'Planning in progress' : 'Operation progress')"
            />
            <div
              v-if="msg.deploymentContinuation?.required && !isGenerating"
              class="deployment-continue-actions"
            >
              <Button
                label="Continue deployment"
                icon="pi pi-play"
                size="small"
                :disabled="isGenerating"
                @click="resumeDeployment"
              />
            </div>
            <ChatBlueprintSuggestion
              v-if="msg.blueprintSuggestion && !msg.blueprintSuggestionDismissed && !isGenerating"
              :suggestion="msg.blueprintSuggestion"
              :disabled="isGenerating"
              @apply="applyBlueprintSuggestion(msg)"
              @skip="skipBlueprintSuggestion(msg)"
            />
            <ChatToolTrace v-if="msg.toolCalls?.length" :tools="msg.toolCalls" />
            <p
              v-if="msg.role === 'assistant' && formatMessageGenerationStats(msg.generationStats)"
              class="generation-stats-footer"
            >
              {{ formatMessageGenerationStats(msg.generationStats) }}
            </p>
          </div>
        </div>
        </template>

        <div v-if="isGenerating" class="chat-message chat-message-assistant">
          <div class="chat-bubble chat-bubble-loading">
            <ProgressSpinner style="width: 1.25rem; height: 1.25rem" stroke-width="4" />
            <div class="generation-status">
              <span class="generation-label">{{ generationStatus.label }}</span>
              <span class="generation-meta">{{ generationStatusMeta(generationStatus) }}</span>
            </div>
            <ChatDeploymentSubtasks
              v-if="liveDeploymentSubtasks.length"
              :subtasks="liveDeploymentSubtasks"
              :title="liveProgressTitle"
            />
            <Button
              label="Stop"
              icon="pi pi-stop"
              size="small"
              severity="danger"
              text
              @click="stopChat"
            />
          </div>
        </div>
      </div>

      <div v-if="pendingAttachments.length" class="pending-attachments">
        <div v-for="(a, i) in pendingAttachments" :key="i" class="pending-attachment">
          <img v-if="a.kind === 'image'" :src="attachmentPreviewUrl(a)" :alt="a.name" class="pending-thumb" />
          <i v-else class="pi pi-file" />
          <span class="pending-name">{{ a.name }}</span>
          <Button icon="pi pi-times" text rounded size="small" @click="removeAttachment(i)" />
        </div>
      </div>

      <div v-if="showCalibrationOffer" class="calibration-offer-row">
        <Button
          label="Send to Calibration"
          icon="pi pi-sliders-h"
          size="small"
          severity="secondary"
          text
          :disabled="calibrationSubmitting"
          @click="openCalibrationDialog"
        />
        <span class="calibration-offer-hint">Didn't get the result you needed?</span>
      </div>

      <div class="chat-input-bar">
        <Button
          v-tooltip.top="'Attach file'"
          icon="pi pi-paperclip"
          text
          rounded
          :disabled="isGenerating || !ready"
          @click="toggleAttachMenu"
        />
        <Textarea
          id="chat-message"
          name="message"
          v-model="session.input"
          rows="2"
          auto-resize
          class="chat-input flex-1"
          :placeholder="rolePlaceholder"
          :disabled="isGenerating || !ready"
          @keydown.enter.exact.prevent="sendMessage()"
        />
        <Button
          v-if="isGenerating"
          v-tooltip.top="'Stop generating'"
          icon="pi pi-stop"
          severity="danger"
          @click="stopChat"
        />
        <Button
          v-else
          icon="pi pi-send"
          :disabled="(!session.input.trim() && !pendingAttachments.length) || !ready"
          @click="sendMessage()"
        />
      </div>
    </template>
    </template>

    <Teleport v-if="useDetachedDesignPanel && isArchitectPane() && designPanelVisible" to="#beta-architect-design-slot">
      <ArchitectDesignPanel
        class="architect-design-rail architect-design-rail-detached"
        :document="session.designDocument"
        :disabled="isGenerating"
        @close="closeDesignPanel"
        @update:markdown="onDesignDocumentEdit"
        @send-revision="sendDesignDocumentRevision"
        @send-to-operator="sendDesignToOperator()"
        @download="downloadDesignDocumentFromPanel()"
      />
    </Teleport>
    <ArchitectDesignPanel
      v-else-if="isArchitectPane() && designPanelVisible"
      class="architect-design-rail"
      :document="session.designDocument"
      :disabled="isGenerating"
      @close="closeDesignPanel"
      @update:markdown="onDesignDocumentEdit"
      @send-revision="sendDesignDocumentRevision"
      @send-to-operator="sendDesignToOperator()"
      @download="downloadDesignDocumentFromPanel()"
    />

    <Dialog
      v-model:visible="calibrationDialogVisible"
      header="Send to Calibration Studio"
      modal
      class="calibration-feedback-dialog"
      :style="{ width: 'min(32rem, 94vw)' }"
      @hide="resetCalibrationDialog"
    >
      <p class="calibration-dialog-lead m-0">
        Share this conversation with Stack Calibration Studio so SMEs can improve skills and workflows.
        Secrets and credentials are redacted before send.
      </p>
      <div class="calibration-dialog-fields">
        <label for="calibration-goal">What were you trying to accomplish?</label>
        <Textarea
          id="calibration-goal"
          v-model="calibrationForm.userGoal"
          rows="2"
          auto-resize
          class="w-full"
        />
        <label for="calibration-category">What went wrong?</label>
        <Select
          id="calibration-category"
          v-model="calibrationForm.category"
          :options="calibrationCategoryOptions"
          option-label="label"
          option-value="value"
          class="w-full"
        />
        <label for="calibration-comment">Additional notes (optional)</label>
        <Textarea
          id="calibration-comment"
          v-model="calibrationForm.userComment"
          rows="2"
          auto-resize
          class="w-full"
          placeholder="e.g. Too many discovery forms before the document was generated"
        />
        <div v-if="calibrationSuggestedSkillLabel" class="calibration-suggested-skill">
          <Tag severity="info" :value="calibrationSuggestedSkillLabel" />
        </div>
        <label class="calibration-checkbox">
          <input
            id="calibration-include-appliance"
            name="includeApplianceName"
            v-model="calibrationForm.includeApplianceName"
            type="checkbox"
          />
          Include connected appliance name in the report
        </label>
      </div>
      <template #footer>
        <Button label="Cancel" severity="secondary" text @click="calibrationDialogVisible = false" />
        <Button
          label="Send to Calibration"
          icon="pi pi-send"
          :loading="calibrationSubmitting"
          @click="submitCalibrationFeedback"
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { computed, inject, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import Menu from 'primevue/menu'
import ProgressSpinner from 'primevue/progressspinner'
import InputText from 'primevue/inputtext'
import Popover from 'primevue/popover'
import Slider from 'primevue/slider'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'
import Textarea from 'primevue/textarea'
import ChatAppliancePicker from './ChatAppliancePicker.vue'
import ApplianceNameLabel from './ApplianceNameLabel.vue'
import ContextUsageRing from './ContextUsageRing.vue'
import ChatConfigForm from './ChatConfigForm.vue'
import AskJpilotCommandMenu from './AskJpilotCommandMenu.vue'
import BetaWelcome from './BetaWelcome.vue'
import ChatMarkdown from './ChatMarkdown.vue'
import ChatToolTrace from './ChatToolTrace.vue'
import ChatBlueprintSuggestion from './ChatBlueprintSuggestion.vue'
import ChatDeploymentSubtasks from './ChatDeploymentSubtasks.vue'
import JPilotMark from './JPilotMark.vue'
import { isDeploymentContinueMessage, messageNeedsDeploymentContinuation } from '../utils/deploymentContinuation'
import {
  getBetaChatPanelTransparency,
  getBetaChatSidebarTransparency,
  onBetaChatAppearanceChange,
  setBetaChatPanelTransparency,
  setBetaChatSidebarTransparency
} from '../services/betaChatAppearance'
import { streamCopilotChat } from '../services/copilotStream'
import { formatCopilotError, isChatAbortError, isProviderQuotaError } from '../utils/chatErrors'
import { generationStatusMeta, formatMessageGenerationStats } from '../utils/generationStatus'
import {
  CONFIG_ACCEPT,
  attachmentPreviewUrl,
  connectCopilotAppliance,
  fileToAttachment,
  getCopilotSettings,
  listCopilotAppliances,
  listCopilotRoles
} from '../services/copilot'
import { parseInputFormFromContent, resolveAssistantMessage } from '../utils/copilotForm'
import { estimateSessionContextUsage } from '../utils/contextUsage'
import {
  downloadArchitectDeliverable,
  createArchitectDeliverableAttachment,
  canSendDeliverableToOperator,
  architectDeliverableDownloadLabel,
  JPILOT_CHANGE_CONTROL_MARKER
} from '../utils/architectDeliverable'
import { JPILOT_DESIGN_MARKER } from '../utils/designDocument'
import { getBetaChatStore } from '../stores/betaChatConversations'
import {
  ARCHITECT_SESSION_ID,
  DESIGN_HANDOFF_MESSAGE,
  OPERATOR_SESSION_ID,
  consumeDesignHandoff,
  handoffState,
  queueDesignHandoff
} from '../stores/copilotHandoff'
import { clearSession, getSession } from '../stores/copilotSessions'
import {
  beginChatRun,
  endChatRun,
  isSessionLoading,
  setFocusedChatSession,
  stopChatRun
} from '../stores/copilotChatRuns'
import { notifyReplyReady } from '../services/chatNotifications'
import {
  CUSTOM_PERSONA_ACCENT,
  DEFAULT_JPILOT_ROLE,
  JPILOT_ROLES,
  capabilityForRole,
  getRoleById,
  normalizeRoleId,
  roleRequiresAppliance,
  writeLastUsedPersona
} from '../config/jpilotRoles'
import {
  appliancesForJpilotRole,
  isApplianceDisabledForRole
} from '../config/jpilotApplianceAccess'
import { isNetScalerVendor } from '../config/applianceVendors'
import { resolveCommandFilterVendor } from '../config/jpilotRecommendedActions'
import ChatRoleSwitchPrompt from './ChatRoleSwitchPrompt.vue'
import BetaChatBackground from './BetaChatBackground.vue'
import ArchitectDesignPanel from './ArchitectDesignPanel.vue'
import ArchitectDeliverableCard from './ArchitectDeliverableCard.vue'
import {
  applyDeliverableToSession,
  appendDiscoveryFormAnswers,
  beginDesignDocumentStreaming,
  isFormalDeliverableMarkdown,
  saveDesignPanelVisible,
  seedDesignDocumentFromAttachment
} from '../utils/architectDesignDocument'
import { buildRoleSwitchNotice, getRoleSwitchPrompt } from '../config/jpilotRoleInference'
import Tag from 'primevue/tag'
import {
  buildCalibrationFeedbackPayload,
  inferCalibrationCategory,
  inferUserGoal,
  shouldOfferCalibrationFeedback
} from '../utils/buildCalibrationFeedbackPayload'
import { sendCalibrationFeedback, getCalibrationFeedbackStatus } from '../services/calibrationFeedback'
import {
  CALIBRATION_FEEDBACK_CATEGORIES,
  CALIBRATION_SUGGESTED_SKILLS
} from '../config/calibrationStudio'

const props = defineProps({
  sessionId: { type: String, required: true },
  initialRole: { type: String, default: DEFAULT_JPILOT_ROLE },
  providers: { type: Array, default: () => [] },
  appliances: { type: Array, default: () => [] },
  defaultProviderId: { type: String, default: '' },
  webSearchAvailable: { type: Boolean, default: false },
  canClose: { type: Boolean, default: false },
  uiVariant: { type: String, default: 'classic' },
  /** Mobile beta chat: show button to open conversation list in parent. */
  showConversationSwitcher: { type: Boolean, default: false },
  /** Desktop beta chat: show button to collapse the conversation list sidebar. */
  showChatSidebarToggle: { type: Boolean, default: false },
  chatSidebarVisible: { type: Boolean, default: true },
  betaBackground: { type: String, default: 'constellation' },
  betaBackgrounds: { type: Array, default: () => [] },
  /** Isolates beta chat conversation storage (`main` vs experimental `lab`). */
  chatNamespace: { type: String, default: 'main' },
  /** Show experimental Chat Beta label in the chat header. */
  showBetaLabel: { type: Boolean, default: false }
})

const emit = defineEmits([
  'close',
  'open-conversations',
  'toggle-chat-sidebar',
  'update:betaBackground',
  'design-panel-visible-change'
])

const useDetachedDesignPanel = computed(
  () => props.uiVariant === 'beta' && !props.showConversationSwitcher
)

const openAppNav = inject('openMobileNav', () => {})

const router = useRouter()
const toast = useToast()

// Persistent per-pane state (survives unmount / pane switches / reload).
const session = getSession(props.sessionId, props.initialRole)

// Transient UI state — fine to reset on remount.
const connecting = ref(false)
const isGenerating = computed(() => isSessionLoading(props.sessionId))
const hasPendingRoleSwitch = computed(() => Boolean(session.pendingRoleSwitch))
const chatInputDisabled = computed(() => isGenerating.value || !ready.value || hasPendingRoleSwitch.value)
const sendDisabled = computed(
  () =>
    chatInputDisabled.value ||
    connecting.value ||
    (!session.input.trim() && !pendingAttachments.value.length)
)

function markPaneFocused() {
  setFocusedChatSession(props.sessionId)
}
const submittingFormIndex = ref(null)
const messagesEl = ref(null)
const pendingAttachments = ref([])
// The design panel stays closed until a design document actually exists — it
// opens when the model produces a deliverable, or when restoring a session that
// already has one (see onMounted). It is never auto-opened just by entering the role.
const designPanelVisible = ref(false)
const imageInputRef = ref(null)
const configInputRef = ref(null)
const attachMenu = ref(null)
const betaOptionsOp = ref(null)
const askInputRef = ref(null)
const commandMenuRef = ref(null)
const betaComposerRef = ref(null)
const generationStatus = ref({
  phase: 'thinking',
  label: 'Thinking…',
  elapsedMs: 0,
  tokensPerSec: null,
  round: 0
})
const liveDeploymentSubtasks = ref([])
const liveProgressTitle = ref('Operation progress')
let generationStartedAt = 0
let generationElapsedTimer = null
let lastGenerationStats = null

const calibrationDialogVisible = ref(false)
const calibrationSubmitting = ref(false)
const calibrationFeedbackReady = ref(true)
const calibrationForm = ref({
  userGoal: '',
  category: 'other',
  userComment: '',
  includeApplianceName: false
})

const calibrationCategoryOptions = CALIBRATION_FEEDBACK_CATEGORIES

const showCalibrationOffer = computed(
  () =>
    calibrationFeedbackReady.value &&
    shouldOfferCalibrationFeedback(session, { isGenerating: isGenerating.value })
)

const calibrationSuggestedSkillLabel = computed(() => {
  const payload = buildCalibrationFeedbackPayload({
    session,
    sessionId: props.sessionId,
    userGoal: calibrationForm.value.userGoal,
    category: calibrationForm.value.category
  })
  const id = payload.suggestedSkillId
  return id ? CALIBRATION_SUGGESTED_SKILLS[id] || id : ''
})

function resetCalibrationDialog() {
  calibrationForm.value = {
    userGoal: '',
    category: 'other',
    userComment: '',
    includeApplianceName: false
  }
}

function openCalibrationDialog() {
  calibrationForm.value = {
    userGoal: inferUserGoal(session.messages),
    category: inferCalibrationCategory(session),
    userComment: '',
    includeApplianceName: false
  }
  calibrationDialogVisible.value = true
}

async function submitCalibrationFeedback() {
  if (calibrationSubmitting.value) return
  calibrationSubmitting.value = true
  try {
    const payload = buildCalibrationFeedbackPayload({
      session,
      sessionId: props.sessionId,
      objectiveMet: false,
      userGoal: calibrationForm.value.userGoal,
      category: calibrationForm.value.category,
      userComment: calibrationForm.value.userComment,
      includeApplianceName: calibrationForm.value.includeApplianceName
    })
    const result = await sendCalibrationFeedback(payload)
    calibrationDialogVisible.value = false
    toast.add({
      severity: 'success',
      summary: 'Sent to Calibration Studio',
      detail: result.message || 'Session queued for SME review.',
      life: 6000
    })
  } catch (error) {
    toast.add({
      severity: 'warn',
      summary: 'Calibration send failed',
      detail: error.response?.data?.detail || error.message || 'Could not reach Calibration Studio.',
      life: 8000
    })
  } finally {
    calibrationSubmitting.value = false
  }
}

function resetGenerationStatus() {
  generationStatus.value = {
    phase: 'thinking',
    label: 'Thinking…',
    elapsedMs: 0,
    tokensPerSec: null,
    round: 0
  }
  liveDeploymentSubtasks.value = []
  liveProgressTitle.value = session.role === 'architect' ? 'Planning in progress' : 'Operation progress'
  lastGenerationStats = null
}

function startGenerationTimer() {
  generationStartedAt = Date.now()
  stopGenerationTimer()
  generationElapsedTimer = setInterval(() => {
    generationStatus.value = {
      ...generationStatus.value,
      elapsedMs: Date.now() - generationStartedAt
    }
  }, 250)
}

function stopGenerationTimer() {
  if (generationElapsedTimer) {
    clearInterval(generationElapsedTimer)
    generationElapsedTimer = null
  }
}

function onGenerationEvent(event) {
  if (event.type === 'subtasks') {
    liveDeploymentSubtasks.value = event.subtasks || []
    if (event.title) {
      liveProgressTitle.value = event.title
    }
  }
  if (event.type === 'llm_stats') {
    lastGenerationStats = {
      tokensPerSec: event.tokensPerSec,
      outputTokens: event.outputTokens,
      durationMs: event.durationMs,
      totalTokens: event.totalTokens
    }
  }
  if (event.type === 'status' || event.type === 'llm_stats') {
    generationStatus.value = {
      phase: event.phase || generationStatus.value.phase,
      label: event.label || generationStatus.value.label,
      elapsedMs: event.elapsedMs ?? generationStatus.value.elapsedMs,
      tokensPerSec: event.tokensPerSec ?? generationStatus.value.tokensPerSec,
      round: event.round ?? generationStatus.value.round
    }
  }
}

const configAccept = CONFIG_ACCEPT

// Installed custom personas fetched from the API (empty until loaded).
const installedPersonas = ref([])

const ready = computed(() => roleProviders.value.length > 0)

// Custom personas, cleaned for display in the role picker:
//  - drop personas whose id mirrors a built-in base role (architect/operator/analyst);
//    those are already shown in the base Role section and would collide on id.
//  - collapse duplicates: the same persona id (multiple installed versions) or the same
//    display label (distinct installs that present identically, e.g. two "Security Architect"
//    bundles) should appear only once.
const BASE_ROLE_IDS = new Set(JPILOT_ROLES.map((r) => r.id))
const BASE_ROLE_LABELS = new Set(JPILOT_ROLES.map((r) => r.label.trim().toLowerCase()))

const cleanedPersonas = computed(() => {
  const seenIds = new Set()
  const seenLabels = new Set()
  const result = []
  for (const p of installedPersonas.value) {
    const id = p.id
    if (!id || BASE_ROLE_IDS.has(id) || seenIds.has(id)) continue
    const labelKey = (p.label || '').trim().toLowerCase()
    if (BASE_ROLE_LABELS.has(labelKey) || (labelKey && seenLabels.has(labelKey))) continue
    seenIds.add(id)
    if (labelKey) seenLabels.add(labelKey)
    result.push(p)
  }
  return result
})

// Persona-first: one unified persona list for the picker. Built-in base-role personas
// (carrying icon/accent) plus installed custom personas, each with a capability badge.
const roleOptions = computed(() => {
  const baseRoles = JPILOT_ROLES.map((r) => ({
    ...r,
    isCustomPersona: false,
    kind: 'builtin',
    baseRole: r.id,
    capability: r.capability || capabilityForRole(r.id)
  }))
  const customs = cleanedPersonas.value.map((p) => ({
    id: p.id,
    label: p.label,
    description: p.description,
    requiresAppliance: p.requiresAppliance,
    suggestedPaneLabel: p.suggestedPaneLabel || p.label,
    handoffTarget: null,
    icon: 'pi pi-user',
    accent: CUSTOM_PERSONA_ACCENT,
    isCustomPersona: true,
    kind: 'custom',
    baseRole: p.baseRole,
    capability: p.capability || capabilityForRole(p.baseRole)
  }))
  return [...baseRoles, ...customs]
})

const baseRoleOptions = computed(() => roleOptions.value.filter((role) => !role.isCustomPersona))
const customPersonaOptions = computed(() => roleOptions.value.filter((role) => role.isCustomPersona))

const activeRole = computed(() => {
  const opts = roleOptions.value
  // A selected custom persona wins the title/identity over its base role.
  if (session.personaId) {
    const persona = opts.find((r) => r.isCustomPersona && r.id === session.personaId)
    if (persona) return persona
  }
  return opts.find((r) => !r.isCustomPersona && r.id === session.role) || getRoleById(session.role)
})

const roleNeedsAppliance = computed(() => {
  if (session.personaId) {
    const persona = installedPersonas.value.find((p) => p.id === session.personaId)
    if (persona) return persona.requiresAppliance
  }
  return roleRequiresAppliance(session.role)
})
const rolePlaceholder = computed(() => {
  if (activeRole.value.id === 'architect') {
    return 'Plan a deployment, change control window, new functionality, or ask architecture questions…'
  }
  if (activeRole.value.id === 'analyst') {
    return 'Describe the issue; attach logs or screenshots; connect an appliance for live checks…'
  }
  return 'Ask about your NetScalers, attach configs or images…'
})
const providerOptions = computed(() =>
  roleProviders.value.map((provider) => ({
    label: provider.model
      ? `${provider.providerName} · ${provider.model}`
      : provider.providerName,
    value: provider.id
  }))
)

const roleApplianceOptions = computed(() =>
  appliancesForJpilotRole(props.appliances, session.role)
)

const roleProviders = computed(() =>
  props.providers.filter((provider) => providerSupportsRole(provider, session.role))
)

const activeProvider = computed(() =>
  props.providers.find((provider) => provider.id === session.providerId) || roleProviders.value[0] || null
)

const contextUsage = computed(() =>
  estimateSessionContextUsage({
    messages: session.messages,
    draftInput: session.input,
    pendingAttachments: pendingAttachments.value,
    model: activeProvider.value?.model,
    providerType: activeProvider.value?.providerType
  })
)

const activeProviderName = computed(() => activeProvider.value?.providerName || '')

const activeProviderDisplayLabel = computed(() => {
  if (!activeProvider.value) return ''
  if (activeProvider.value.model) {
    return `${activeProvider.value.providerName} · ${activeProvider.value.model}`
  }
  return activeProvider.value.providerName
})

const activeProviderTooltip = computed(() =>
  activeProviderDisplayLabel.value
    ? `LLM for ${activeRole.value.label}: ${activeProviderDisplayLabel.value}`
    : ''
)

const selectedAppliance = computed(() =>
  roleApplianceOptions.value.find((appliance) => appliance.name === session.applianceChoice) ||
    props.appliances.find((appliance) => appliance.name === session.applianceChoice) ||
    null
)

/** Filter recommended actions once an appliance is chosen in this pane. */
const commandMenuVendor = computed(() =>
  session.applianceChoice ? resolveCommandFilterVendor(selectedAppliance.value) : null
)

const connectedApplianceTooltip = computed(() => {
  if (!selectedAppliance.value) return 'Connected'
  const vendor = selectedAppliance.value.vendor
  if (vendor === 'cisco' || vendor === 'f5' || vendor === 'sdx') return 'Connected via SSH'
  return 'Connected via Next-Gen API'
})

const betaStatusLine = computed(() => {
  if (isGenerating.value) return 'Generating a reply…'
  if (session.connectedAppliance && isApplianceConnected()) {
    return `Connected to ${session.connectedAppliance}`
  }
  if (session.applianceChoice && !roleNeedsAppliance.value) {
    return `Planning reference: ${session.applianceChoice}`
  }
  if (session.applianceChoice && roleNeedsAppliance.value) {
    return `${session.applianceChoice} — not connected`
  }
  if (activeProviderName.value) {
    return `Using ${activeProviderName.value}`
  }
  return activeRole.value.description
})

const mobileQuickPrompts = computed(() => {
  const role = session.role
  const byRole = {
    operator: [
      { id: 'ips', label: 'List IP addresses', text: 'List all IP addresses on the connected appliance with their types (NSIP, SNIP, VIP, etc.).' },
      { id: 'internet', label: 'Check internet access', text: 'Does the NetScaler have internet access?' },
      { id: 'vservers', label: 'List virtual servers', text: 'List all virtual servers on the connected appliance.' }
    ],
    analyst: [
      { id: 'health', label: 'System health', text: 'Show system health and high-level status on the connected appliance.' },
      { id: 'cpu', label: 'CPU & memory', text: 'Show CPU and memory utilization on the connected appliance.' },
      { id: 'ping', label: 'Test reachability', text: 'Can the appliance ping 8.8.8.8?' }
    ],
    architect: [
      { id: 'greenfield', label: 'Greenfield design', text: 'I am planning a new NetScaler deployment from scratch.' },
      { id: 'change', label: 'Change control', text: 'I need a change control record for a maintenance window.' },
      { id: 'gateway', label: 'Citrix Gateway', text: 'Help me plan a Citrix Gateway deployment.' }
    ]
  }
  return byRole[role] || byRole.operator
})

function onMobileQuickPrompt(text) {
  session.input = text
  sendMessage()
}

function formatMessageTime(msg) {
  const ts = msg.createdAt || msg.timestamp
  if (ts) {
    return new Date(ts).toTimeString().split(':').slice(0, 2).join(':')
  }
  return new Date().toTimeString().split(':').slice(0, 2).join(':')
}

// Masked-secret placeholder tokens (⟦secret:<fieldId>⟧) are embedded in a message's
// content in place of the real credential. Render them as a fixed mask so secrets never
// appear in plaintext in the transcript. History sent to the backend keeps the raw token;
// the backend substitutes it out-of-band only when calling the model.
const SECRET_PLACEHOLDER_RE = /⟦secret:[^⟧]*⟧/g

function maskSecretPlaceholders(text) {
  if (!text || typeof text !== 'string') return text
  return text.replace(SECRET_PLACEHOLDER_RE, '••••••••')
}

function displayContent(msg) {
  return maskSecretPlaceholders(msg?.content || '')
}

function chatApplianceName() {
  return session.applianceChoice || session.connectedAppliance || ''
}

function isApplianceConnected() {
  return Boolean(
    session.connectedAppliance &&
      session.applianceChoice &&
      session.connectedAppliance === session.applianceChoice
  )
}

function roleOptionTooltip(role) {
  return role.capability ? `${role.label} · ${role.capability}` : role.label
}

function providerSupportsRole(provider, roleId) {
  if (!provider) return false
  const roles = provider.roles
  if (!Array.isArray(roles) || !roles.length) return true
  // For custom persona ids, resolve to their base role for provider matching.
  const persona = installedPersonas.value.find((p) => p.id === roleId)
  const effectiveRoleId = persona ? persona.baseRole : roleId
  return roles.includes(effectiveRoleId)
}

function pickProviderForRole(force = false) {
  const options = providerOptions.value
  if (!options.length) {
    session.providerId = ''
    return
  }

  const currentValid = options.some((option) => option.value === session.providerId)
  if (!force && currentValid) return

  const roleDefault = options.find((option) => {
    const provider = props.providers.find((entry) => entry.id === option.value)
    return provider?.isDefault
  })
  session.providerId = roleDefault?.value || options[0]?.value || ''
}

function pickApplianceForRole(force = false) {
  const options = roleApplianceOptions.value
  if (!options.length) {
    session.applianceChoice = null
    session.connectedAppliance = ''
    return
  }

  const currentValid = options.some(
    (appliance) =>
      appliance.name === session.applianceChoice && !isApplianceDisabledForRole(appliance, session.role)
  )
  if (!force && currentValid) return

  const preferred =
    options.find((appliance) => isNetScalerVendor(appliance.vendor)) || options[0]
  session.applianceChoice = preferred.name
  if (roleNeedsAppliance.value) {
    session.connectedAppliance = ''
  }
}

// Persona-first: the picker value is always the selected persona id (built-in or custom).
const activeRolePickerId = computed(() => session.personaId || session.role)

function onRolePickerChange(newId) {
  // Every selection is a persona. Derive the internal capability role from its baseRole
  // (built-ins: baseRole === id) and remember it as the last-used default for new chats.
  const option = roleOptions.value.find((r) => r.id === newId)
  session.personaId = newId
  session.role = option?.baseRole || getRoleById(newId).id
  writeLastUsedPersona(newId)
  onRoleChange()
}

function onRoleChange() {
  pickProviderForRole(true)
  pickApplianceForRole(true)
}

watch(
  () => session.role,
  () => {
    onRoleChange()
  }
)

watch(
  () => props.providers,
  () => {
    pickProviderForRole(false)
  },
  { immediate: true, deep: true }
)

watch(
  () => props.appliances,
  () => {
    pickApplianceForRole(false)
  },
  { immediate: true, deep: true }
)

const attachMenuItems = computed(() => {
  const settings = getCopilotSettings()
  const items = []
  if (settings.allowImages) {
    items.push({ label: 'Attach image', icon: 'pi pi-image', command: () => imageInputRef.value?.click() })
  }
  if (settings.allowConfigFiles) {
    items.push({
      label: 'Attach config or Markdown',
      icon: 'pi pi-file',
      command: () => configInputRef.value?.click()
    })
  }
  if (!items.length) {
    items.push({ label: 'Attachments disabled — open Settings', icon: 'pi pi-cog', command: () => router.push('/settings') })
  }
  return items
})

function toggleAttachMenu(event) {
  attachMenu.value.toggle(event)
}

function toggleBetaOptions(event) {
  betaOptionsOp.value?.toggle(event)
}

function closeBetaOptions() {
  betaOptionsOp.value?.hide()
}

function chooseBetaBackground(id) {
  emit('update:betaBackground', id)
}

const chatPanelTransparency = ref(getBetaChatPanelTransparency(props.chatNamespace))
const chatSidebarTransparency = ref(getBetaChatSidebarTransparency(props.chatNamespace))

function syncChatTransparencyFromStorage() {
  chatPanelTransparency.value = getBetaChatPanelTransparency(props.chatNamespace)
  chatSidebarTransparency.value = getBetaChatSidebarTransparency(props.chatNamespace)
}

function onChatPanelTransparencyChange(value) {
  setBetaChatPanelTransparency(value, props.chatNamespace)
}

function onChatSidebarTransparencyChange(value) {
  setBetaChatSidebarTransparency(value, props.chatNamespace)
}

let chatAppearanceCleanup = null

function clearBetaConversation() {
  clearConversation()
}

function designDocumentHandoffContent() {
  const doc = session.designDocument
  if (!doc?.markdown) return ''
  const marker = doc.type === 'change_control' ? JPILOT_CHANGE_CONTROL_MARKER : JPILOT_DESIGN_MARKER
  return `${marker}\n${doc.markdown}`
}

function resolveDesignDocumentContext(runOptions = {}) {
  if (runOptions.designDocumentContext) {
    return runOptions.designDocumentContext
  }
  if (!isArchitectPane()) return undefined
  const doc = session.designDocument
  if (!doc?.markdown?.trim() || isFormalDeliverableMarkdown(doc.markdown)) {
    return undefined
  }
  return doc.markdown
}

function setDesignPanelVisible(visible) {
  designPanelVisible.value = visible
  saveDesignPanelVisible(visible)
}

function toggleDesignPanel() {
  setDesignPanelVisible(!designPanelVisible.value)
}

function openDesignPanel() {
  setDesignPanelVisible(true)
}

function closeDesignPanel() {
  setDesignPanelVisible(false)
}

function onDesignDocumentEdit(markdown) {
  if (!session.designDocument) return
  session.designDocument.markdown = markdown
  session.designDocument.dirty = true
  session.designDocument.updatedAt = new Date().toISOString()
}

function downloadDesignDocumentFromPanel() {
  const content = designDocumentHandoffContent()
  if (!content) return
  const filename = downloadArchitectDeliverable(content)
  const isChangeControl = architectDeliverableDownloadLabel(content).includes('change control')
  toast.add({
    severity: 'success',
    summary: isChangeControl ? 'Change control record downloaded' : 'Design document downloaded',
    detail: filename,
    life: 3000
  })
}

async function sendDesignDocumentRevision() {
  const doc = session.designDocument
  if (!doc?.markdown?.trim() || isGenerating.value) return
  const prompt =
    session.input.trim() ||
    'Revise the design document using my panel edits and your latest understanding from this conversation.'
  session.input = ''
  await sendMessage(prompt, null, {
    skipRoleInference: true,
    designDocumentContext: doc.markdown,
    includeDesignRevision: true
  })
  doc.dirty = false
}

function downloadArchitectDeliverableMessage(content) {
  const filename = downloadArchitectDeliverable(content)
  const isChangeControl = architectDeliverableDownloadLabel(content).includes('change control')
  toast.add({
    severity: 'success',
    summary: isChangeControl ? 'Change control record downloaded' : 'Design document downloaded',
    detail: filename,
    life: 3000
  })
}

function isArchitectPane() {
  if (props.uiVariant === 'beta' || props.sessionId.startsWith('beta-')) {
    return session.role === 'architect'
  }
  return props.sessionId === ARCHITECT_SESSION_ID || props.sessionId.endsWith('-pane-1')
}

function sendDesignToOperator(content) {
  if (!isArchitectPane() || session.role !== 'architect') {
    toast.add({
      severity: 'warn',
      summary: 'Architect pane only',
      detail: 'Send designs to Operator from the Architect chat pane.',
      life: 4000
    })
    return
  }
  const handoffContent = designDocumentHandoffContent() || content
  if (!handoffContent) {
    toast.add({
      severity: 'warn',
      summary: 'No design document',
      detail: 'Generate or attach a design document first.',
      life: 3500
    })
    return
  }
  try {
    const attachment = createArchitectDeliverableAttachment(handoffContent)
    const targetSessionId =
      props.uiVariant === 'beta' || props.sessionId.startsWith('beta-')
        ? getBetaChatStore(props.chatNamespace).resolveBetaHandoffTargetSessionId()
        : props.sessionId.replace(/pane-1$/, 'pane-2')
    queueDesignHandoff({
      content: handoffContent,
      sourceLabel: attachment.name,
      targetSessionId
    })
    toast.add({
      severity: 'info',
      summary: 'Sent to Operator',
      detail: 'Opening the Operator pane and starting implementation…',
      life: 3500
    })
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Handoff failed',
      detail: error.message || 'Could not send design to Operator.',
      life: 4000
    })
  }
}

async function acceptDesignHandoff(handoff) {
  if (isGenerating.value) {
    queueDesignHandoff(handoff)
    toast.add({
      severity: 'warn',
      summary: 'Operator is busy',
      detail: 'Stop the current reply, then send the design again from Architect.',
      life: 4000
    })
    return
  }

  setFocusedChatSession(props.sessionId)
  if (session.role !== 'operator') {
    session.role = 'operator'
  }

  let attachment
  try {
    attachment = createDesignDocumentAttachment(handoff.content, handoff.sourceLabel || undefined)
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Handoff failed',
      detail: error.message || 'Design document is too large to attach.',
      life: 4000
    })
    return
  }

  await sendMessage(DESIGN_HANDOFF_MESSAGE, [attachment], { skipRoleInference: true })
}

async function tryConsumeDesignHandoff() {
  const handoff = consumeDesignHandoff(props.sessionId)
  if (!handoff) return
  await acceptDesignHandoff(handoff)
}

function applyRoleForCommand(cmd) {
  if (!cmd?.role) return
  const nextRole = normalizeRoleId(cmd.role)
  if (nextRole !== session.role) {
    session.role = nextRole
  }
}

function resolvePendingRoleSwitchPrompt() {
  return [...session.messages].reverse().find((msg) => msg.roleSwitchPrompt && !msg.roleSwitchPrompt.resolved)
}

async function executePendingRoleSwitchChat(pending) {
  if (roleNeedsAppliance.value && !isApplianceConnected()) {
    session.pendingMessage = pending.content
    session.pendingAttachmentsSnapshot = pending.attachments
    await showAppliancePicker()
    return
  }
  await runChat(pending.content, pending.attachments, { skipRoleInference: true })
}

async function stayInCurrentRole() {
  if (!session.pendingRoleSwitch || isGenerating.value) return
  const pending = session.pendingRoleSwitch
  const promptMsg = resolvePendingRoleSwitchPrompt()
  if (promptMsg?.roleSwitchPrompt) {
    promptMsg.roleSwitchPrompt.resolved = true
  }
  session.pendingRoleSwitch = null
  await executePendingRoleSwitchChat(pending)
}

async function acceptRoleSwitch() {
  if (!session.pendingRoleSwitch || isGenerating.value) return
  const pending = session.pendingRoleSwitch
  const promptMsg = resolvePendingRoleSwitchPrompt()
  if (promptMsg?.roleSwitchPrompt) {
    promptMsg.roleSwitchPrompt.resolved = true
    const newRole = promptMsg.roleSwitchPrompt.suggestedRole
    if (newRole && newRole !== session.role) {
      session.role = newRole
      session.messages.push({
        role: 'assistant',
        content: '',
        roleSwitchNotice: buildRoleSwitchNotice(newRole, promptMsg.roleSwitchPrompt.reason),
        createdAt: Date.now()
      })
    }
  }
  session.pendingRoleSwitch = null
  await executePendingRoleSwitchChat(pending)
}

function onCommandPick(cmd) {
  if (cmd.type === 'link') {
    router.push(cmd.to)
    return
  }
  applyRoleForCommand(cmd)
  if (!ready.value) return
  sendMessage(cmd.text, null, { skipRoleInference: true })
}

function openCommandMenu() {
  commandMenuRef.value?.openMenu?.()
}

function focusComposer() {
  nextTick(() => {
    if (props.uiVariant === 'beta') {
      const el = betaComposerRef.value?.$el
      if (el?.focus) {
        el.focus()
      } else {
        el?.querySelector?.('input')?.focus()
      }
      return
    }
    askInputRef.value?.focus()
  })
}

function onSelectPersona(payload) {
  const roleId = typeof payload === 'string' ? payload : payload?.roleId
  const deferFocus = typeof payload === 'object' && payload?.deferFocus
  if (!roleId) return
  session.role = roleId
  if (!deferFocus) {
    focusComposer()
  }
}

async function onSelectSkill({ prompt, roleId, skillId, source }) {
  if (roleId && roleId !== session.role) {
    session.role = roleId
    pickProviderForRole(true)
  }
  const text = (prompt || '').trim()
  if (!text) {
    focusComposer()
    return
  }
  if (!ready.value || isGenerating.value || connecting.value) return
  // When the user explicitly invokes an installed blueprint ("Help me using the
  // installed <X> calibration blueprint…"), pin THAT blueprint for the turn so the
  // matcher cannot re-derive a different, keyword-overlapping blueprint from the
  // message text (e.g. the "Load Balancer" substring in a security-headers title).
  const activeBlueprintSkillId = source === 'blueprint' ? skillId : undefined
  await sendMessage(text, null, {
    skipRoleInference: true,
    ...(activeBlueprintSkillId ? { activeBlueprintSkillId } : {})
  })
}

function focusAskInput() {
  focusComposer()
}

async function addFiles(fileList) {
  const settings = getCopilotSettings()
  const files = Array.from(fileList || [])
  if (!files.length) return
  if (pendingAttachments.value.length + files.length > settings.maxAttachments) {
    toast.add({ severity: 'warn', summary: 'Too many attachments', detail: `Maximum ${settings.maxAttachments} attachments per message`, life: 3000 })
    return
  }
  for (const file of files) {
    try {
      const attachment = await fileToAttachment(file)
      if (attachment.kind === 'image' && !settings.allowImages) throw new Error('Image attachments are disabled in Settings')
      if (attachment.kind === 'config' && !settings.allowConfigFiles) throw new Error('Config file attachments are disabled in Settings')
      pendingAttachments.value.push(attachment)
      if (isArchitectPane() && attachment.kind === 'config' && seedDesignDocumentFromAttachment(session, attachment)) {
        openDesignPanel()
      }
    } catch (error) {
      toast.add({ severity: 'error', summary: 'Attachment failed', detail: error.message, life: 4000 })
    }
  }
}

function onImageSelected(event) {
  addFiles(event.target.files)
  event.target.value = ''
}

function onConfigSelected(event) {
  addFiles(event.target.files)
  event.target.value = ''
}

function removeAttachment(index) {
  pendingAttachments.value.splice(index, 1)
}

function clearConversation() {
  clearSession(props.sessionId)
  pendingAttachments.value = []
  // No document after a clear, so keep the design panel closed.
  closeDesignPanel()
}

const WEB_SEARCH_TOOLS = ['search_netscaler_nextgen_api', 'search_netscaler_cli_reference']

// Extract the external URLs that actually informed a reply (auditable provenance).
function extractWebSources(toolCalls) {
  const sources = []
  const seen = new Set()
  for (const tc of toolCalls || []) {
    if (!WEB_SEARCH_TOOLS.includes(tc.name)) continue
    let data
    try {
      data = JSON.parse(tc.result)
    } catch {
      continue
    }
    for (const r of data?.webResults?.results || []) {
      if (r.url && !seen.has(r.url)) {
        seen.add(r.url)
        sources.push({ title: r.title || r.url, url: r.url })
      }
    }
  }
  return sources
}

function assistantView(msg) {
  if (msg.role !== 'assistant') {
    return { content: msg.content, inputForm: null, formSubmitted: false }
  }
  return resolveAssistantMessage(msg)
}

function hostOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

async function scrollToBottom() {
  await nextTick()
  await nextTick()
  requestAnimationFrame(() => {
    if (messagesEl.value) {
      messagesEl.value.scrollTop = messagesEl.value.scrollHeight
    }
  })
}

function onApplianceChange() {
  session.connectedAppliance = ''
  if (!session.applianceChoice || !roleNeedsAppliance.value) return
  connectAppliance({ name: session.applianceChoice })
}

async function showAppliancePicker() {
  const pickerIndex = session.messages.length
  session.messages.push({ role: 'assistant', content: '', appliancePicker: true, appliances: [], pickerLoading: true })
  await scrollToBottom()
  try {
    const appliances = appliancesForJpilotRole(await listCopilotAppliances(), session.role)
    if (session.messages[pickerIndex]) {
      session.messages[pickerIndex].appliances = appliances
      session.messages[pickerIndex].pickerLoading = false
      session.messages[pickerIndex].content = appliances.length
        ? roleNeedsAppliance.value
          ? 'Choose a NetScaler from your inventory:'
          : 'Choose an appliance from your inventory (optional reference):'
        : roleNeedsAppliance.value
          ? 'No NetScaler appliances found. Add one in the inventory first.'
          : 'No appliances found. Add one in the inventory first.'
    }
  } catch (error) {
    if (session.messages[pickerIndex]) {
      session.messages[pickerIndex].pickerLoading = false
      session.messages[pickerIndex].content = error.response?.data?.detail || 'Failed to load NetScalers from inventory.'
    }
  }
  await scrollToBottom()
}

async function connectAppliance(appliance) {
  connecting.value = true
  try {
    const result = await connectCopilotAppliance(appliance.name)
    session.connectedAppliance = result.applianceName
    session.applianceChoice = result.applianceName
    const authLine =
      result.api === 'SSH'
        ? `Authenticated as **${result.authenticatedUser}** via SSH.`
        : `Authenticated as **${result.authenticatedUser}** via \`${result.loginEndpoint}\`.`
    session.messages.push({
      role: 'assistant',
      content: `${result.message}\n\n${authLine}`
    })
    const queued = session.pendingMessage
    const queuedAttachments = session.pendingAttachmentsSnapshot
    session.pendingMessage = null
    session.pendingAttachmentsSnapshot = []
    if (queued || queuedAttachments.length) {
      await runChat(queued, queuedAttachments, { skipRoleInference: true })
    }
  } catch (error) {
    session.connectedAppliance = ''
    session.messages.push({
      role: 'assistant',
      content: `Connection failed for **${appliance.name}**: ${error.response?.data?.detail || error.message}`
    })
  } finally {
    connecting.value = false
    await scrollToBottom()
  }
}

async function runChat(content, attachments, runOptions = {}) {
  // Blueprint stickiness for plain composer follow-ups: if a blueprint is pinned for
  // this session (established by an explicit invoke, a form submission, or an "applied"
  // suggestion) and the caller didn't override it, carry the pin so the matcher stays
  // on the same blueprint instead of re-deriving one from the follow-up text.
  if (!('activeBlueprintSkillId' in runOptions) && session.activeBlueprintSkillId) {
    runOptions = { ...runOptions, activeBlueprintSkillId: session.activeBlueprintSkillId }
  }
  stopChatRun(props.sessionId)
  const controller = new AbortController()
  beginChatRun(props.sessionId, controller)
  resetGenerationStatus()
  startGenerationTimer()
  if (isArchitectPane() && session.designDocument?.markdown) {
    beginDesignDocumentStreaming(session)
  }
  let wasError = false
  let userStopped = false
  await scrollToBottom()
  try {
    const conversational = session.messages.filter(
      (msg) =>
        (msg.role === 'user' || msg.role === 'assistant') &&
        msg.content &&
        !msg.appliancePicker &&
        !msg.roleSwitchNotice
    )
    let history = conversational.map((msg) => ({ role: msg.role, content: msg.content }))
    if (history.length && history[history.length - 1].role === 'user' && history[history.length - 1].content === content) {
      history = history.slice(0, -1)
    }
    const data = await streamCopilotChat(
      {
        message: content,
        history,
        attachments,
        settings: getCopilotSettings(),
        role: session.role || DEFAULT_JPILOT_ROLE,
        personaId: session.personaId || undefined,
        applianceName: chatApplianceName() || undefined,
        providerId: session.providerId || undefined,
        webSearch: session.webSearch !== false,
        deploymentContinuation: Boolean(runOptions.deploymentContinuation),
        longTaskApproved: Boolean(runOptions.longTaskApproved),
        designDocumentContext: resolveDesignDocumentContext(runOptions),
        includeDesignRevision: Boolean(runOptions.includeDesignRevision),
        ...(runOptions.skipBlueprintSkillId ? { skipBlueprintSkillId: runOptions.skipBlueprintSkillId } : {}),
        ...(runOptions.activeBlueprintSkillId ? { activeBlueprintSkillId: runOptions.activeBlueprintSkillId } : {}),
        ...(runOptions.secrets && Object.keys(runOptions.secrets).length ? { secrets: runOptions.secrets } : {})
      },
      {
        signal: controller.signal,
        onEvent: onGenerationEvent
      }
    )
    const parsed = parseInputFormFromContent(data.content || '')
    const rawContent = data.content || ''
    const deliverable = isArchitectPane()
      ? applyDeliverableToSession(session, rawContent, 'assistant')
      : { chatContent: parsed.content || rawContent, revision: null }
    const chatContent =
      deliverable.revision != null ? deliverable.chatContent : parsed.content || rawContent
    // Reveal the design panel once the model produces a deliverable or discovery notes exist.
    if (isArchitectPane() && (deliverable.revision != null || session.designDocument?.source === 'discovery')) {
      openDesignPanel()
    }
    session.messages.push({
      role: 'assistant',
      content: chatContent,
      createdAt: Date.now(),
      toolCalls: data.toolCalls,
      webSources: extractWebSources(data.toolCalls),
      inputForm: data.inputForm || parsed.inputForm,
      designDocRevision: deliverable.revision || undefined,
      generationStats: lastGenerationStats,
      deploymentContinuation: data.deploymentContinuation || null,
      deploymentSubtasks: data.deploymentContinuation?.subtasks || liveDeploymentSubtasks.value,
      progressTitle: liveProgressTitle.value,
      blueprintSuggestion: data.blueprintSuggestion || null,
      blueprintSuggestionDismissed: false
    })
    // Persist the session-level blueprint pin. An explicitly threaded pin wins; else,
    // when the backend reports a blueprint was actually applied this turn, remember it
    // so subsequent plain follow-ups stay on the same blueprint.
    if (runOptions.activeBlueprintSkillId) {
      session.activeBlueprintSkillId = runOptions.activeBlueprintSkillId
    } else if (data.blueprintSuggestion?.state === 'applied' && data.blueprintSuggestion.skillId) {
      session.activeBlueprintSkillId = data.blueprintSuggestion.skillId
    }
  } catch (error) {
    if (session.designDocument) {
      session.designDocument.streaming = false
    }
    if (isChatAbortError(error)) {
      userStopped = true
      session.messages.push({
        role: 'assistant',
        content: 'Stopped — generation was cancelled. No further tokens will be used for this reply.'
      })
      return
    }
    wasError = true
    const content = formatCopilotError(error)
    session.messages.push({
      role: 'assistant',
      content,
      isError: true,
      providerQuotaError: isProviderQuotaError(error)
    })
  } finally {
    stopGenerationTimer()
    endChatRun(props.sessionId)
    submittingFormIndex.value = null
    await scrollToBottom()
    if (!userStopped) {
      notifyReplyReady({
        toast,
        sessionId: props.sessionId,
        role: session.role,
        wasError
      })
    }
  }
}

function stopChat() {
  stopChatRun(props.sessionId)
}

async function submitConfigForm(values, messageIndex) {
  const msg = session.messages[messageIndex]
  const view = resolveAssistantMessage(msg)
  if (!view.inputForm || view.formSubmitted || isGenerating.value) return

  const isArchitect = session.role === 'architect'
  const prefix = isArchitect ? 'Planning inputs for:' : 'Configuration inputs for:'
  const lines = [`${prefix} ${view.inputForm.title}`]
  // Secret fields (type="password" or secret=true) are masked in the visible message /
  // transcript / history. Their real value is carried out-of-band via `secrets`, keyed by
  // a placeholder token that the backend substitutes only when calling the model.
  const secrets = {}
  for (const field of view.inputForm.fields) {
    const value = values[field.id]
    const isSecret = field.type === 'password' || field.secret === true
    if (isSecret) {
      const raw = String(value ?? '')
      if (raw.trim()) {
        const token = `⟦secret:${field.id}⟧`
        secrets[token] = raw
        // Visible line carries the placeholder token (not the secret). The user-facing
        // transcript renders it as a mask (see maskSecretPlaceholders in the display path).
        lines.push(`- ${field.label}: ${token}`)
      } else {
        lines.push(`- ${field.label}: (not provided)`)
      }
      continue
    }
    const rendered =
      field.type === 'boolean' ? (value ? 'yes' : 'no') : String(value ?? '').trim() || '(not provided)'
    lines.push(`- ${field.label}: ${rendered}`)
  }
  lines.push(
    '',
    isArchitect
      ? 'Continue design discovery or move to the next question.'
      : 'Proceed with the configuration on the connected appliance using these values. Do not ask the same questions in prose again.'
  )

  msg.formSubmitted = true
  if (isArchitect) {
    appendDiscoveryFormAnswers(session, {
      title: view.inputForm.title,
      fields: view.inputForm.fields,
      values
    })
    openDesignPanel()
  }
  // Pin this turn to the blueprint that presented the form, so the backend
  // doesn't re-match onto a different blueprint mid-flow (e.g. a discovery
  // form's answers getting matched against an unrelated blueprint).
  const activeBlueprintSkillId = msg.blueprintSuggestion?.skillId

  submittingFormIndex.value = messageIndex
  try {
    await sendMessage(lines.join('\n'), null, {
      ...(isArchitect ? { skipRoleInference: true } : {}),
      ...(activeBlueprintSkillId ? { activeBlueprintSkillId } : {}),
      ...(Object.keys(secrets).length ? { secrets } : {})
    })
  } finally {
    submittingFormIndex.value = null
  }
}

/**
 * Skip: find the original user message that triggered this assistant turn and
 * re-send it with skipBlueprintSkillId so the backend answers without that blueprint.
 * Dismiss the card immediately so it doesn't re-render on the old message.
 */
async function skipBlueprintSuggestion(msg) {
  if (isGenerating.value || !msg.blueprintSuggestion) return
  const skillId = msg.blueprintSuggestion.skillId
  msg.blueprintSuggestionDismissed = true
  // User is opting out of this blueprint — drop any session pin so the re-run (and
  // later turns) are not forced back onto it.
  if (session.activeBlueprintSkillId === skillId) {
    session.activeBlueprintSkillId = null
  }

  // Find the index of this assistant message in the messages array.
  const msgIndex = session.messages.indexOf(msg)
  if (msgIndex < 0) return

  // Walk backwards to find the immediately preceding user message.
  let originalUserMsg = null
  for (let i = msgIndex - 1; i >= 0; i--) {
    if (session.messages[i].role === 'user') {
      originalUserMsg = session.messages[i]
      break
    }
  }
  if (!originalUserMsg || !originalUserMsg.content) return

  // Re-send the original user message with skipBlueprintSkillId.
  const originalText = originalUserMsg.content
  const originalAttachments = originalUserMsg.attachments || []
  await sendMessage(originalText, originalAttachments, {
    skipRoleInference: true,
    skipBlueprintSkillId: skillId
  })
}

async function applyBlueprintSuggestion(msg) {
  if (isGenerating.value || !msg.blueprintSuggestion) return
  msg.blueprintSuggestionDismissed = true
  const prompt = msg.blueprintSuggestion.applyPrompt
  // User explicitly chose this blueprint — pin it so it can't be re-matched away.
  const skillId = msg.blueprintSuggestion.skillId
  await sendMessage(prompt, null, {
    skipRoleInference: true,
    ...(skillId ? { activeBlueprintSkillId: skillId } : {})
  })
}

async function resumeDeployment() {
  if (isGenerating.value) return
  const lastAssistant = [...session.messages].reverse().find((msg) => msg.role === 'assistant')
  if (lastAssistant?.deploymentContinuation) {
    lastAssistant.deploymentContinuation = {
      ...lastAssistant.deploymentContinuation,
      required: false
    }
  }
  await sendMessage('continue', null, {
    deploymentContinuation: true,
    longTaskApproved: true,
    skipRoleInference: true
  })
}

async function sendMessage(text, externalAttachments = null, options = {}) {
  const content = (text || session.input).trim()
  const sourceAttachments = externalAttachments ?? pendingAttachments.value
  const attachments = sourceAttachments.map((item) => ({
    name: item.name,
    kind: item.kind,
    mimeType: item.mimeType,
    data: item.data
  }))
  if ((!content && !attachments.length) || isGenerating.value || connecting.value) return

  if (session.pendingRoleSwitch && !options.skipRoleInference) {
    toast.add({
      severity: 'warn',
      summary: 'Choose a role first',
      detail: 'Stay in your current role or switch before sending another message.',
      life: 3500
    })
    return
  }

  if (!ready.value) return

  const attachmentNames = attachments.map((item) => item.name)
  const roleSwitch = options.skipRoleInference
    ? null
    : getRoleSwitchPrompt(content, {
        attachmentNames,
        currentRole: session.role
      })

  session.messages.push({
    role: 'user',
    content,
    createdAt: Date.now(),
    attachments: attachments.map((item) => ({ ...item }))
  })
  session.input = ''
  if (!externalAttachments) {
    pendingAttachments.value = []
  }
  await scrollToBottom()

  if (roleSwitch) {
    session.messages.push({
      role: 'assistant',
      content: roleSwitch.prompt.message,
      roleSwitchPrompt: { ...roleSwitch.prompt, resolved: false },
      createdAt: Date.now()
    })
    session.pendingRoleSwitch = {
      content,
      attachments
    }
    await scrollToBottom()
    return
  }

  const lastAssistant = [...session.messages].reverse().find((msg) => msg.role === 'assistant')
  const runOptions = { ...options }
  if (
    !runOptions.deploymentContinuation &&
    lastAssistant &&
    messageNeedsDeploymentContinuation(lastAssistant) &&
    isDeploymentContinueMessage(content)
  ) {
    runOptions.deploymentContinuation = true
    runOptions.longTaskApproved = true
    lastAssistant.deploymentContinuation = {
      ...lastAssistant.deploymentContinuation,
      required: false
    }
  }

  if (roleNeedsAppliance.value && !isApplianceConnected()) {
    session.pendingMessage = content
    session.pendingAttachmentsSnapshot = attachments
    await showAppliancePicker()
    return
  }
  await runChat(content, attachments, runOptions)
}

watch(
  () => [session.applianceChoice, session.connectedAppliance],
  () => {
    if (
      session.applianceChoice &&
      session.connectedAppliance &&
      session.applianceChoice !== session.connectedAppliance
    ) {
      session.connectedAppliance = ''
    }
  },
  { immediate: true }
)

watch(
  () => isArchitectPane() && designPanelVisible.value,
  (open) => {
    emit('design-panel-visible-change', open)
  }
)

watch(
  () => props.chatNamespace,
  () => {
    syncChatTransparencyFromStorage()
  }
)

onMounted(() => {
  syncChatTransparencyFromStorage()
  chatAppearanceCleanup = onBetaChatAppearanceChange(() => {
    syncChatTransparencyFromStorage()
  })
  markPaneFocused()
  scrollToBottom()
  tryConsumeDesignHandoff()
  if (isArchitectPane() && session.designDocument?.markdown) {
    openDesignPanel()
  }
  getCalibrationFeedbackStatus()
    .then((data) => {
      calibrationFeedbackReady.value = data?.status !== 'disabled'
    })
    .catch(() => {
      calibrationFeedbackReady.value = true
    })
  // Load installed custom personas from the API (non-blocking).
  loadInstalledPersonas()
  // A persona installed/uninstalled elsewhere (Calibration Studio, another tab,
  // background sync) should appear/disappear in the role selector without a full
  // reload — refresh the list when the chat regains focus/visibility.
  window.addEventListener('focus', refreshInstalledPersonasOnFocus)
  document.addEventListener('visibilitychange', refreshInstalledPersonasOnVisible)
})

// Load the installed custom personas that back the role selector. The backend
// lists only personas with bundles on disk and prunes orphan MongoDB index rows.
function loadInstalledPersonas() {
  return listCopilotRoles()
    .then((roles) => {
      installedPersonas.value = (roles || []).filter((r) => r.isCustomPersona)
      syncStalePersonaSelection()
    })
    .catch(() => {
      // Silently ignore — custom personas won't appear but base roles still work.
    })
}

function syncStalePersonaSelection() {
  if (!session.personaId) return
  // Built-in personas are always valid; keep the internal role in sync.
  if (BASE_ROLE_IDS.has(session.personaId)) {
    session.role = session.personaId
    return
  }
  const persona = installedPersonas.value.find((p) => p.id === session.personaId)
  if (persona) {
    // Reconcile the internal capability role to the persona's base role.
    session.role = persona.baseRole || session.role
    return
  }
  // Selected custom persona is gone (uninstalled / orphan-pruned): re-anchor to the
  // built-in of its last-known base role (or Operator) and update last-used — never null.
  const fallback = getRoleById(session.role).id
  session.personaId = fallback
  session.role = fallback
  writeLastUsedPersona(fallback)
}

function refreshInstalledPersonasOnFocus() {
  loadInstalledPersonas()
}

function refreshInstalledPersonasOnVisible() {
  if (document.visibilityState === 'visible') {
    loadInstalledPersonas()
  }
}

watch(
  () => handoffState.pending?.queuedAt,
  () => {
    tryConsumeDesignHandoff()
  }
)

onUnmounted(() => {
  chatAppearanceCleanup?.()
  stopGenerationTimer()
  window.removeEventListener('focus', refreshInstalledPersonasOnFocus)
  document.removeEventListener('visibilitychange', refreshInstalledPersonasOnVisible)
})
</script>

<style scoped>
.chat-pane.pane-generating {
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--p-primary-color) 35%, transparent);
}

.chat-pane {
  --glass-bg: rgba(255, 255, 255, 0.66);
  --glass-strong: rgba(255, 255, 255, 0.8);
  --glass-border: rgba(15, 23, 42, 0.1);
  --glass-text: var(--p-text-color);
  --glass-muted: var(--p-text-muted-color);
  --glass-field: rgba(15, 23, 42, 0.04);
  background: var(--glass-bg);
  border: 1px solid var(--glass-border);
  border-radius: 1rem;
  overflow: hidden;
  min-height: 0;
  backdrop-filter: blur(18px) saturate(140%);
  -webkit-backdrop-filter: blur(18px) saturate(140%);
  box-shadow: 0 12px 40px rgba(2, 6, 23, 0.12);
}

:global(.app-dark) .chat-pane {
  --glass-bg: rgba(17, 21, 32, 0.55);
  --glass-strong: rgba(24, 29, 43, 0.78);
  --glass-border: rgba(255, 255, 255, 0.12);
  --glass-field: rgba(255, 255, 255, 0.06);
  box-shadow: 0 12px 48px rgba(0, 0, 0, 0.45);
}

.pane-toolbar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 0.75rem;
  border-bottom: 1px solid var(--glass-border);
}

.pane-role-toggle :deep(.p-togglebutton) {
  padding: 0.45rem 0.65rem;
}

.role-toggle-option {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.role-toggle-option-labeled {
  gap: 0.35rem;
}

.pane-role-toggle :deep(.p-togglebutton .role-toggle-option i),
.beta-role-toggle :deep(.p-togglebutton .role-toggle-option i) {
  color: var(--role-option-accent);
  font-size: 1rem;
}

.pane-role-toggle :deep(.p-togglebutton:nth-child(4)),
.beta-role-toggle :deep(.p-togglebutton:nth-child(4)) {
  margin-left: 0.4rem;
  padding-left: 0.65rem;
  border-left: 2px solid #f59e0b;
}

.pane-select {
  min-width: 9rem;
}

.pane-select-appliance {
  min-width: 11rem;
}

.pane-select-appliance :deep(.appliance-name-label) {
  overflow: hidden;
}

.pane-select-appliance :deep(.appliance-name) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pane-select-llm {
  min-width: 9rem;
}

.pane-llm {
  display: flex;
  align-items: center;
  min-width: 0;
}

.pane-llm-name {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  max-width: 12rem;
  padding: 0.35rem 0.55rem;
  border-radius: 0.5rem;
  background: color-mix(in srgb, var(--p-primary-color) 10%, transparent);
  color: var(--p-text-color);
  font-size: 0.8125rem;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pane-llm-name i {
  flex-shrink: 0;
  color: var(--p-primary-color);
  font-size: 0.75rem;
}

.pane-spacer {
  flex: 1;
}

.pane-connected {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.8125rem;
  color: var(--p-primary-color);
  white-space: nowrap;
}

.pane-connected i {
  color: var(--p-green-500);
}

.pane-disconnected {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.8125rem;
  color: var(--p-orange-500);
  white-space: nowrap;
}

.pane-disconnected i {
  color: var(--p-orange-500);
}

.pane-appliance-ref {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  white-space: nowrap;
}

.pane-appliance-ref i {
  color: var(--p-primary-color);
}

/* ---------- Empty state: glass command menu ---------- */
.ask-hero {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  min-height: 0;
}

.glass-card {
  width: min(34rem, 100%);
  background: var(--glass-strong);
  border: 1px solid var(--glass-border);
  border-radius: 1rem;
  padding: 1.25rem;
  box-shadow: 0 18px 50px rgba(2, 6, 23, 0.18);
}

@media (min-width: 992px) {
  .glass-card {
    width: min(48rem, 100%);
    padding: 1.5rem 1.75rem;
  }
}

@media (min-width: 1400px) {
  .glass-card {
    width: min(56rem, 100%);
  }
}

.glass-head {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: var(--glass-text);
  margin-bottom: 0.9rem;
}

.glass-head i {
  color: var(--p-primary-color);
}

.glass-role-hint {
  margin: -0.35rem 0 0.85rem;
  font-size: 0.8125rem;
  color: var(--glass-muted);
  line-height: 1.45;
}

.glass-input {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 0.75rem;
  border: 1px solid var(--glass-border);
  border-radius: 0.75rem;
  background: var(--glass-field);
}

.glass-input-icon {
  color: var(--glass-muted);
}

.glass-input-field {
  flex: 1;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--glass-text);
  font-size: 0.95rem;
}

.glass-input-field::placeholder {
  color: var(--glass-muted);
}

.glass-attach {
  border: 0;
  background: transparent;
  color: var(--glass-muted);
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 0.4rem;
}

.glass-attach:hover:not(:disabled) {
  color: var(--glass-text);
}

.kbd {
  font-size: 0.75rem;
  color: var(--glass-muted);
  border: 1px solid var(--glass-border);
  border-radius: 0.4rem;
  padding: 0.05rem 0.4rem;
}

.glass-recommended {
  margin-top: 1rem;
  max-height: min(24rem, 42vh);
  overflow-y: auto;
  padding-right: 0.25rem;
}

.glass-recommended-intro {
  margin: 0 0 0.75rem;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--glass-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.glass-prompt-group + .glass-prompt-group {
  margin-top: 0.85rem;
}

.glass-prompt-group-title {
  margin-bottom: 0.35rem;
  padding: 0 0.7rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--glass-muted);
}

.glass-prompts {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.glass-prompt {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.55rem 0.7rem;
  border: 0;
  border-radius: 0.6rem;
  background: transparent;
  color: var(--glass-text);
  font-size: 0.875rem;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s ease;
}

.glass-prompt span {
  flex: 1;
}

.glass-prompt-link {
  font-size: 0.75rem;
  color: var(--glass-muted);
  margin-left: auto;
}

.glass-prompt:hover:not(:disabled) {
  background: var(--glass-field);
}

.glass-prompt:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.glass-prompt > i:first-child {
  color: var(--p-primary-color);
  flex-shrink: 0;
}

.glass-pending {
  margin-top: 0.75rem;
}

.glass-hint {
  margin: 0.9rem 0 0;
  font-size: 0.8125rem;
  color: var(--glass-muted);
}

.glass-llm-hint {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.glass-llm-hint i {
  color: var(--p-primary-color);
}

/* ---------- Active conversation ---------- */
.chat-messages {
  overflow-y: auto;
  padding: 1.25rem;
}

.chat-message {
  display: flex;
  margin-bottom: 1rem;
}

.chat-message-user {
  justify-content: flex-end;
}

.chat-message-assistant {
  justify-content: flex-start;
}

.chat-bubble {
  max-width: min(44rem, 92%);
  padding: 0.875rem 1rem;
  border-radius: 0.875rem;
  border: 1px solid var(--glass-border);
  background: var(--glass-strong);
  color: var(--glass-text);
}

.chat-message-user .chat-bubble {
  background: color-mix(in srgb, var(--p-primary-color) 16%, var(--glass-strong));
}

.chat-error-block {
  border-left: 3px solid var(--p-orange-500);
  padding-left: 0.75rem;
}

.design-doc-download {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--glass-border);
}

.chat-bubble-loading {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  color: var(--glass-muted);
}

.generation-status {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
}

.generation-label {
  font-size: 0.875rem;
  color: var(--glass-text);
}

.generation-meta {
  font-size: 0.75rem;
  color: var(--glass-muted);
  font-variant-numeric: tabular-nums;
}

.generation-stats-footer,
.beta-message-meta {
  font-size: 0.75rem;
  color: var(--glass-muted);
  font-variant-numeric: tabular-nums;
}

.generation-stats-footer {
  margin-top: 0.5rem;
}

.beta-message-meta-sep {
  margin: 0 0.35rem;
}

.chat-role {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--glass-muted);
  margin-bottom: 0.35rem;
}

.chat-content {
  white-space: pre-wrap;
  line-height: 1.6;
  font-size: 0.9375rem;
}

.web-sources {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
  margin-top: 0.6rem;
  padding-top: 0.5rem;
  border-top: 1px dashed var(--glass-border);
}

.web-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
  border: 1px solid color-mix(in srgb, var(--p-primary-color) 30%, transparent);
  border-radius: 999px;
  padding: 0.1rem 0.45rem;
}

.web-source-link {
  font-size: 0.75rem;
  color: var(--glass-muted);
  text-decoration: none;
  border: 1px solid var(--glass-border);
  border-radius: 0.4rem;
  padding: 0.1rem 0.4rem;
}

.web-source-link:hover {
  color: var(--p-primary-color);
  border-color: var(--p-primary-color);
}

.chat-attachments,
.pending-attachments {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.pending-attachments {
  padding: 0.75rem 1rem 0;
  border-top: 1px solid var(--glass-border);
}

.attachment-chip,
.pending-attachment {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.35rem 0.5rem;
  border-radius: 0.5rem;
  background: var(--glass-field);
  border: 1px solid var(--glass-border);
  font-size: 0.8125rem;
  color: var(--glass-text);
}

.attachment-thumb,
.pending-thumb {
  width: 2rem;
  height: 2rem;
  object-fit: cover;
  border-radius: 0.25rem;
}

.pending-name {
  max-width: 12rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chat-input-bar {
  display: flex;
  gap: 0.75rem;
  align-items: flex-end;
  padding: 1rem;
  border-top: 1px solid var(--glass-border);
}

.chat-input {
  resize: none;
  background: var(--glass-field);
}

/* ---------- Beta variant (Diamond ChatBox-style) ---------- */
.chat-pane-beta {
  --glass-bg: color-mix(in srgb, var(--p-content-background) 45%, transparent);
  --glass-strong: color-mix(in srgb, var(--p-content-background) 50%, transparent);
  --glass-border: color-mix(in srgb, var(--p-content-border-color) 55%, transparent);
  --glass-text: var(--p-text-color);
  --glass-muted: var(--p-text-muted-color);
  --glass-field: color-mix(in srgb, var(--p-surface-100) 58%, transparent);
  background: transparent;
  border-color: transparent;
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  box-shadow: none;
  height: 100%;
}

:global(.app-dark) .chat-pane-beta {
  --glass-field: color-mix(in srgb, var(--p-surface-800) 58%, transparent);
}

.beta-shell {
  min-height: 0;
}

.beta-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  gap: 0.65rem;
  padding: 0.65rem 0.75rem;
  border-bottom: 1px solid color-mix(in srgb, var(--p-content-border-color) 55%, transparent);
  background: color-mix(in srgb, var(--p-content-background) 48%, transparent);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  flex-shrink: 0;
  position: relative;
  z-index: 2;
}

.beta-header-start {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  min-width: 0;
}

.beta-header-chats {
  flex-shrink: 0;
}

.beta-header-center {
  display: flex;
  justify-content: center;
  flex-shrink: 0;
  min-width: 0;
}

.beta-header-center-stack {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.35rem;
  min-width: 0;
  max-width: 15rem;
}

.beta-header-model {
  width: 100%;
  min-width: 0;
}

.beta-header-model-select {
  width: 100%;
  min-width: 0;
}

.beta-header-model-select :deep(.p-select) {
  width: 100%;
}

.beta-header-model-select :deep(.p-select-label) {
  font-size: 0.75rem;
  padding: 0.28rem 0.55rem;
  color: var(--p-text-muted-color);
}

.beta-header-model-name {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  max-width: 100%;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chat-pane-lab .beta-header-model-select :deep(.p-select-label),
.chat-pane-lab .beta-header-model-name {
  font-size: 0.72rem;
}

@media (min-width: 992px) {
  .beta-header {
    gap: 1rem;
    padding: 1rem 3rem;
    padding-top: 1rem;
  }
}

.beta-header-identity {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  min-width: 0;
}

.chat-pane-lab .beta-header-identity {
  gap: 0.6rem;
}

.chat-pane-lab .beta-avatar {
  width: 2.5rem;
  height: 2.5rem;
  box-shadow: 0 4px 12px rgba(2, 6, 23, 0.08);
}

.chat-pane-lab .beta-status-dot {
  width: 0.6rem;
  height: 0.6rem;
}

.chat-pane-lab .beta-title {
  font-size: 0.95rem;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.chat-pane-lab .beta-title-brand {
  color: var(--p-text-muted-color);
}

.beta-title-role-cursor {
  display: inline;
  font-size: 1rem;
  color: var(--p-text-color);
  text-transform: capitalize;
  vertical-align: baseline;
}

.chat-pane-lab .beta-title-role-cursor {
  font-size: 0.95rem;
}

.chat-pane-lab .beta-subtitle {
  font-size: 0.78rem;
  color: color-mix(in srgb, var(--p-text-muted-color) 85%, transparent);
}

.chat-pane-lab .beta-lab-tag {
  padding: 0.1rem 0.4rem;
  font-size: 0.5625rem;
  background: color-mix(in srgb, var(--p-orange-500) 10%, transparent);
  border-color: color-mix(in srgb, var(--p-orange-500) 24%, transparent);
}

.beta-avatar-wrap {
  position: relative;
  flex-shrink: 0;
}

.beta-avatar {
  width: 4rem;
  height: 4rem;
  border-radius: 999px;
  box-shadow: 0 8px 24px rgba(2, 6, 23, 0.12);
}

.beta-avatar-role {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: color-mix(in srgb, var(--role-accent, var(--p-primary-color)) 16%, transparent);
  color: var(--role-accent, var(--p-primary-color));
  box-shadow: 0 4px 12px rgba(2, 6, 23, 0.08);
}

.beta-avatar-role i {
  font-size: 1.35rem;
}

.chat-pane-lab .beta-avatar-role i {
  font-size: 1rem;
}

.beta-status-dot {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 0.85rem;
  height: 0.85rem;
  border-radius: 999px;
  border: 2px solid var(--p-content-background);
  background: var(--p-surface-400);
}

.beta-status-active {
  background: var(--p-green-400);
}

.beta-status-busy {
  background: var(--p-yellow-400);
}

.beta-status-away {
  background: var(--p-orange-400);
}

.beta-header-copy {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
}

.beta-title {
  font-weight: 600;
  color: var(--p-text-color);
}

.beta-subtitle {
  font-size: 0.875rem;
  color: var(--p-text-muted-color);
}

.beta-lab-tag {
  display: inline-flex;
  align-self: flex-start;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  font-size: 0.625rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--p-orange-700);
  background: color-mix(in srgb, var(--p-orange-500) 14%, transparent);
  border: 1px solid color-mix(in srgb, var(--p-orange-500) 32%, transparent);
}

.beta-lab-tag-compact {
  margin-top: 0.1rem;
}

:global(.app-dark) .beta-lab-tag {
  color: var(--p-orange-300);
}

.beta-header-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.35rem;
  flex-wrap: nowrap;
  min-width: 0;
}

.beta-options-panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  width: min(22rem, 92vw);
  padding: 0.25rem;
}

.beta-options-group-roles {
  gap: 0.65rem;
}

.beta-role-picker-mobile {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.beta-role-picker-base {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.45rem;
}

.beta-role-picker-personas {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  padding-top: 0.65rem;
  border-top: 2px solid #f59e0b;
}

.beta-role-picker-personas-label {
  font-size: 0.6875rem;
  font-weight: 650;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #f59e0b;
}

.beta-role-picker-personas-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.45rem;
}

.beta-role-picker-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  min-height: 4.25rem;
  padding: 0.55rem 0.45rem;
  border-radius: 0.75rem;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
  color: var(--p-text-color);
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background 0.15s ease,
    box-shadow 0.15s ease;
}

.beta-role-picker-btn:hover:not(:disabled),
.beta-role-picker-btn:focus-visible {
  border-color: color-mix(in srgb, var(--role-option-accent) 45%, var(--p-content-border-color));
  outline: none;
}

.beta-role-picker-btn-active {
  border-color: var(--role-option-accent);
  background: color-mix(in srgb, var(--role-option-accent) 10%, var(--p-content-background));
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--role-option-accent) 35%, transparent) inset;
}

.beta-role-picker-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.beta-role-picker-btn .role-toggle-option i {
  color: var(--role-option-accent);
  font-size: 1rem;
}

.beta-role-picker-btn .beta-role-toggle-label {
  width: 100%;
  text-align: center;
  line-height: 1.25;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
}

.beta-role-picker-btn-persona .beta-role-toggle-label {
  color: var(--role-option-accent);
}

.beta-role-toggle-capability {
  display: block;
  width: 100%;
  text-align: center;
  font-size: 0.65rem;
  line-height: 1.2;
  opacity: 0.7;
  margin-top: 0.1rem;
}

@media (max-width: 380px) {
  .beta-role-picker-personas-grid {
    grid-template-columns: 1fr;
  }
}

.beta-options-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.35rem;
}

.beta-options-hint {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  line-height: 1.35;
}

.beta-bg-picker {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
}

.beta-bg-thumb {
  width: 100%;
  aspect-ratio: 3 / 2;
  border-radius: 0.5rem;
  border: 2px solid transparent;
  background-size: cover;
  background-position: center;
  cursor: pointer;
  color: var(--p-text-muted-color);
  font-size: 0.75rem;
}

.beta-bg-thumb-animated {
  position: relative;
  padding: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  align-items: stretch;
}

.beta-bg-thumb-theme {
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--p-content-border-color) 70%, transparent);
}

:global(.app-dark) .beta-bg-thumb-theme {
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.1);
}

.beta-bg-thumb-white {
  box-shadow: inset 0 0 0 1px rgba(15, 23, 42, 0.12);
}

.beta-bg-thumb-black {
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.14);
}

.beta-bg-thumb-label {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 0.2rem 0.25rem;
  font-size: 0.625rem;
  font-weight: 600;
  text-align: center;
  color: #fff;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.72));
  pointer-events: none;
}

.beta-bg-thumb-white .beta-bg-thumb-label {
  color: #0f172a;
  background: linear-gradient(transparent, rgba(255, 255, 255, 0.92));
}

.beta-bg-thumb-animated :deep(.beta-chat-bg) {
  border-radius: inherit;
}

.beta-bg-thumb-none {
  background: var(--p-surface-100);
  display: flex;
  align-items: center;
  justify-content: center;
}

.beta-bg-thumb-active {
  border-color: var(--p-primary-color);
}

.beta-options-group {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.beta-options-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--p-text-muted-color);
}

.beta-transparency-row {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.beta-transparency-slider {
  flex: 1;
  min-width: 0;
}

.beta-transparency-value {
  flex-shrink: 0;
  min-width: 2.5rem;
  font-size: 0.8125rem;
  font-variant-numeric: tabular-nums;
  color: var(--p-text-muted-color);
  text-align: right;
}

.beta-options-context {
  align-items: flex-start;
}

.beta-options-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  padding-top: 0.25rem;
  border-top: 1px solid var(--p-content-border-color);
}

.beta-role-toggle :deep(.p-togglebutton) {
  padding: 0.4rem 0.55rem;
}

.beta-select {
  min-width: 9rem;
}

.beta-select-appliance {
  min-width: 11rem;
}

.beta-messages,
.user-message-container {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem 0.75rem;
  margin-top: 0.25rem;
  min-height: 0;
}

.chat-pane-lab .beta-messages.user-message-container {
  display: flex;
  flex-direction: column;
}

.chat-pane-lab .beta-empty-welcome {
  flex: 1;
  height: 100%;
  display: flex;
  max-width: none;
  margin: 0;
  padding: 0;
}

.chat-pane-lab .beta-empty-welcome > * {
  width: 100%;
}

.chat-pane-lab.chat-pane-beta {
  background: transparent !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
}

.chat-pane-lab .beta-shell {
  background: transparent;
}

/* Liquid glass shell — transparent window, solid message cards */
.chat-pane-lab .beta-header {
  background: transparent;
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  border-bottom-color: color-mix(in srgb, var(--p-content-border-color) 32%, transparent);
}

.chat-pane-lab .beta-messages.user-message-container {
  background: transparent;
}

.chat-pane-lab .beta-bubble-assistant {
  background: var(--p-content-background);
  border-color: var(--p-content-border-color);
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  box-shadow: 0 4px 18px rgba(2, 6, 23, 0.08);
}

.chat-pane-lab .beta-bubble-user {
  background: var(--p-primary-100);
  border-color: color-mix(in srgb, var(--p-primary-color) 24%, var(--p-content-border-color));
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  box-shadow: 0 4px 18px rgba(2, 6, 23, 0.06);
}

:global(.app-dark) .chat-pane-lab .beta-bubble-assistant {
  background: var(--p-surface-800);
  border-color: var(--p-content-border-color);
  box-shadow: 0 4px 22px rgba(0, 0, 0, 0.3);
}

:global(.app-dark) .chat-pane-lab .beta-bubble-user {
  color: var(--p-primary-100);
  background: color-mix(in srgb, var(--p-primary-color) 30%, var(--p-surface-800));
  border-color: color-mix(in srgb, var(--p-primary-color) 38%, var(--p-content-border-color));
  box-shadow: 0 4px 22px rgba(0, 0, 0, 0.28);
}

.chat-pane-lab .beta-pending {
  background: transparent;
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  border-top-color: color-mix(in srgb, var(--p-content-border-color) 32%, transparent);
}

.chat-pane-lab .beta-footer {
  background: transparent;
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  border-top-color: color-mix(in srgb, var(--p-content-border-color) 32%, transparent);
}

.chat-pane-lab .beta-footer:not(.beta-footer-compact) .beta-composer-input :deep(input) {
  background: var(--p-content-background);
  border-color: var(--p-content-border-color);
  backdrop-filter: none;
  box-shadow: 0 2px 14px rgba(2, 6, 23, 0.07);
}

:global(.app-dark) .chat-pane-lab .beta-footer:not(.beta-footer-compact) .beta-composer-input :deep(input) {
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.28);
}

.chat-pane-lab .role-switch-notice {
  background: var(--p-content-background);
  border-color: var(--p-content-border-color);
}

@media (min-width: 768px) {
  .beta-messages,
  .user-message-container {
    padding: 0.625rem 1rem;
  }
}

@media (min-width: 992px) {
  .beta-messages,
  .user-message-container {
    padding: 0.75rem 1.5rem;
  }
}

@media (max-width: 991px) {
  .beta-messages,
  .user-message-container {
    padding: 0.35rem 0.5rem;
    margin-top: 0;
  }
}

.beta-empty {
  width: 100%;
  max-width: 100%;
  margin: 0 auto;
  padding: 1rem 0 2rem;
}

@media (min-width: 992px) {
  .beta-empty {
    max-width: min(48rem, 100%);
    padding: 1.5rem 0 2.5rem;
  }
}

@media (min-width: 1400px) {
  .beta-empty {
    max-width: min(56rem, 100%);
  }
}

.beta-empty-title {
  margin: 0 0 0.35rem;
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--p-text-color);
}

.beta-empty-hint {
  margin: 0 0 1rem;
  font-size: 0.875rem;
  color: var(--p-text-muted-color);
  line-height: 1.5;
}

.beta-empty-note {
  margin: 1rem 0 0;
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
}

.chat-support-note {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  flex-wrap: wrap;
  justify-content: center;
}

.chat-support-note a {
  color: var(--p-primary-color);
  text-decoration: none;
  font-weight: 500;
}

.chat-support-note a:hover {
  text-decoration: underline;
}

.beta-msg-grid {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.625rem;
  margin-bottom: 0.75rem;
}

.beta-msg-grid-user {
  grid-template-columns: 1fr;
}

.beta-msg-grid-user .beta-msg-content-col {
  margin-top: 0;
}

.beta-msg-avatar-col {
  margin-top: 0.125rem;
}

.beta-msg-content-col {
  margin-top: 0.125rem;
  min-width: 0;
}

.beta-msg-content-col :deep(.tool-trace-panel) {
  margin-top: 0.5rem;
}

.beta-msg-content-col :deep(.design-doc-download) {
  margin-top: 0.5rem;
  padding-top: 0.5rem;
}

.beta-msg-content-col :deep(.web-sources) {
  margin-top: 0.35rem;
  padding-top: 0.35rem;
}

.beta-attachments {
  margin-bottom: 0.35rem;
}

.beta-msg-content-user {
  text-align: right;
}

.beta-msg-avatar {
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 999px;
  box-shadow: 0 4px 12px rgba(2, 6, 23, 0.08);
}

.beta-msg-avatar-role {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: color-mix(in srgb, var(--role-accent, var(--p-primary-color)) 16%, transparent);
  color: var(--role-accent, var(--p-primary-color));
}

.beta-msg-avatar-role i {
  font-size: 1rem;
}

.beta-message-author {
  margin: 0 0 0.25rem;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--p-text-color);
}

.beta-bubble {
  display: inline-block;
  max-width: 80%;
  padding: 0.625rem 0.75rem;
  border-radius: var(--p-content-border-radius);
  border: 1px solid var(--p-content-border-color);
  font-weight: 500;
  line-height: 1.45;
  font-size: 0.875rem;
  word-break: break-word;
  white-space: pre-wrap;
  text-align: left;
}

.beta-bubble-assistant {
  color: var(--p-text-color);
  background: color-mix(in srgb, var(--p-content-background) 50%, transparent);
  border-color: color-mix(in srgb, var(--p-content-border-color) 55%, transparent);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  box-shadow: 0 2px 10px rgba(2, 6, 23, 0.05);
}

.beta-bubble-user {
  color: var(--p-primary-900);
  background: color-mix(in srgb, var(--p-primary-100) 55%, transparent);
  border-color: color-mix(in srgb, var(--p-primary-color) 28%, transparent);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  box-shadow: 0 2px 10px rgba(2, 6, 23, 0.04);
}

:global(.app-dark) .beta-bubble-assistant {
  background: color-mix(in srgb, var(--p-surface-900) 48%, transparent);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.18);
}

:global(.app-dark) .beta-bubble-user {
  color: var(--p-primary-100);
  background: color-mix(in srgb, var(--p-primary-color) 20%, transparent);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.18);
}

.beta-bubble-loading {
  display: inline-flex;
  align-items: center;
  gap: 0.65rem;
}

.beta-message-time {
  margin: 0.35rem 0 0;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}

.beta-check-icon {
  margin-left: 0.35rem;
  color: var(--p-green-400);
}

.beta-pending {
  border-top: 1px solid color-mix(in srgb, var(--p-content-border-color) 55%, transparent);
  padding: 0.75rem 1rem 0;
  background: color-mix(in srgb, var(--p-content-background) 45%, transparent);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}

.beta-footer {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 0.75rem;
  padding: 0.65rem 0.75rem;
  padding-bottom: calc(0.65rem + env(safe-area-inset-bottom, 0px));
  margin-top: auto;
  border-top: 1px solid color-mix(in srgb, var(--p-content-border-color) 55%, transparent);
  background: color-mix(in srgb, var(--p-content-background) 48%, transparent);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  flex-shrink: 0;
}

@media (min-width: 576px) {
  .beta-footer {
    flex-direction: row;
    align-items: center;
    gap: 1rem;
    padding: 1rem;
    padding-bottom: 1rem;
  }
}

@media (min-width: 992px) {
  .beta-footer {
    padding: 1rem 3rem;
  }
}

.beta-footer-actions {
  display: flex;
  width: 100%;
  gap: 1rem;
}

@media (min-width: 576px) {
  .beta-footer-actions {
    width: auto;
  }
}

.beta-footer-browse,
.beta-footer-attach {
  flex: 1;
}

@media (min-width: 576px) {
  .beta-footer-browse,
  .beta-footer-attach {
    flex: 0 0 auto;
  }
}

.beta-input {
  min-width: 0;
}

.role-switch-notice {
  display: flex;
  align-items: flex-start;
  gap: 0.55rem;
  margin: 0.35rem 0 0.75rem;
  padding: 0.55rem 0.75rem;
  border-radius: 0.65rem;
  border: 1px solid color-mix(in srgb, var(--p-primary-color) 28%, transparent);
  background: color-mix(in srgb, var(--p-primary-color) 8%, transparent);
  font-size: 0.8125rem;
  line-height: 1.45;
  color: var(--p-text-muted-color);
}

.role-switch-notice i {
  margin-top: 0.1rem;
  color: var(--p-primary-color);
  flex-shrink: 0;
}

.role-switch-notice strong {
  color: var(--p-text-color);
}

.role-switch-notice-architect {
  border-color: color-mix(in srgb, #7c3aed 35%, transparent);
  background: color-mix(in srgb, #7c3aed 10%, transparent);
}

.role-switch-notice-architect i {
  color: #7c3aed;
}

.role-switch-notice-operator {
  border-color: color-mix(in srgb, #059669 35%, transparent);
  background: color-mix(in srgb, #059669 10%, transparent);
}

.role-switch-notice-operator i {
  color: #059669;
}

.role-switch-notice-analyst {
  border-color: color-mix(in srgb, #d97706 35%, transparent);
  background: color-mix(in srgb, #d97706 10%, transparent);
}

.role-switch-notice-analyst i {
  color: #d97706;
}

.chat-messages .role-switch-notice {
  max-width: 42rem;
  margin-left: auto;
  margin-right: auto;
}

/* ---------- Beta mobile (SuperGrok-style) ---------- */
.beta-header-mobile-title {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  min-width: 0;
  text-align: center;
}

.beta-header-logo-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  line-height: 0;
}

.beta-header-trio-logo {
  color: var(--p-primary-color);
  transform: scale(calc(44 / 56));
  transform-origin: center center;
}

.beta-title-compact {
  font-size: 1rem;
  font-weight: 650;
  letter-spacing: -0.02em;
  color: var(--p-text-color);
}

/* Role chip shown to the right of the logo in the mobile header */
.beta-subtitle-compact {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
}

.beta-role-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  white-space: nowrap;
  color: var(--role-chip-accent, var(--p-text-muted-color));
  background: color-mix(in srgb, var(--role-chip-accent, var(--p-primary-color)) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--role-chip-accent, var(--p-primary-color)) 28%, transparent);
}

.beta-role-chip-label {
  font-size: 0.8125rem;
  text-transform: capitalize;
}

.beta-role-chip-icon {
  font-size: 0.625rem;
}

.beta-role-toggle-label {
  font-size: 0.8125rem;
  font-weight: 600;
}

.beta-mobile-prompts {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  width: 100%;
  max-width: 22rem;
  margin: 0.75rem auto 0;
}

.beta-mobile-prompt {
  width: 100%;
  padding: 0.85rem 1rem;
  border-radius: 1rem;
  border: 1px solid color-mix(in srgb, var(--p-content-border-color) 80%, transparent);
  background: color-mix(in srgb, var(--p-content-background) 88%, transparent);
  color: var(--p-text-color);
  font-size: 0.9375rem;
  font-weight: 500;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease;
}

.beta-mobile-prompt:hover:not(:disabled) {
  border-color: color-mix(in srgb, var(--p-primary-color) 35%, transparent);
  background: color-mix(in srgb, var(--p-primary-color) 8%, var(--p-content-background));
}

.beta-mobile-prompt:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.beta-composer {
  display: flex;
  flex: 1;
  align-items: center;
  gap: 0.15rem;
  min-width: 0;
}

.beta-footer:not(.beta-footer-compact) .beta-composer-icon,
.beta-footer:not(.beta-footer-compact) .beta-composer-send {
  display: none;
}

.beta-footer:not(.beta-footer-compact) .beta-composer-input :deep(input) {
  width: 100%;
  border: 1px solid color-mix(in srgb, var(--p-content-border-color) 55%, transparent);
  border-radius: 0.65rem;
  background: color-mix(in srgb, var(--p-content-background) 52%, transparent);
  color: var(--p-text-color);
  padding: 0.55rem 0.75rem;
}

.beta-footer:not(.beta-footer-compact) .beta-composer-input :deep(input:disabled) {
  opacity: 0.72;
  cursor: not-allowed;
}

.beta-footer-compact .beta-composer {
  display: flex;
  align-items: center;
  gap: 0.15rem;
  width: 100%;
  padding: 0.35rem 0.45rem 0.35rem 0.25rem;
  border-radius: 999px;
  border: 1px solid var(--beta-mobile-border, var(--p-content-border-color));
  background: var(--beta-mobile-composer-bg, var(--p-content-background));
}

.beta-composer-input :deep(input) {
  border: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
  padding-left: 0.25rem;
  padding-right: 0.25rem;
}

.beta-composer-input :deep(input:disabled) {
  opacity: 0.72;
  cursor: not-allowed;
}

.beta-footer-compact .beta-composer-input :deep(input:disabled) {
  color: var(--beta-mobile-muted, var(--p-text-muted-color));
}

.beta-composer-icon {
  flex-shrink: 0;
  width: 2.25rem;
  height: 2.25rem;
}

.beta-composer-send {
  flex-shrink: 0;
  width: 2.35rem !important;
  height: 2.35rem !important;
  padding: 0 !important;
}

.beta-footer-compact .beta-footer-actions {
  display: none;
}

@media (max-width: 767px), (max-width: 991px) and (max-height: 500px) {
  .beta-shell-compact {
    --beta-mobile-bg: #f8fafc;
    --beta-mobile-surface: #ffffff;
    --beta-mobile-ink: #0f172a;
    --beta-mobile-muted: #64748b;
    --beta-mobile-border: #e2e8f0;
    --beta-mobile-chip-bg: #ffffff;
    --beta-mobile-chip-hover: #f1f5f9;
    --beta-mobile-composer-bg: #ffffff;
    --beta-mobile-user-bubble: color-mix(in srgb, var(--p-primary-color) 10%, #ffffff);
    background: var(--beta-mobile-bg);
    color: var(--beta-mobile-ink);
  }

  :global(.app-dark) .beta-shell-compact {
    --beta-mobile-bg: #000000;
    --beta-mobile-surface: #000000;
    --beta-mobile-ink: #f5f5f5;
    --beta-mobile-muted: #a3a3a3;
    --beta-mobile-border: #262626;
    --beta-mobile-chip-bg: #141414;
    --beta-mobile-chip-hover: #1c1c1c;
    --beta-mobile-composer-bg: #141414;
    --beta-mobile-user-bubble: #1c1c1c;
    background: var(--beta-mobile-bg);
    color: var(--beta-mobile-ink);
  }

  :global(.app-dark) .beta-shell-compact .chat-pane-beta {
    background: var(--beta-mobile-bg);
    color: var(--beta-mobile-ink);
  }

  .beta-header-compact {
    display: grid;
    grid-template-columns: 2.75rem minmax(0, 1fr) auto;
    align-items: center;
    gap: 0.35rem;
    padding:
      calc(0.5rem + env(safe-area-inset-top, 0px))
      0.75rem
      0.5rem;
    border-bottom: 1px solid var(--beta-mobile-border);
    background: var(--beta-mobile-surface) !important;
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
    color: var(--beta-mobile-ink);
  }

  .beta-header-compact .beta-title-compact {
    color: var(--beta-mobile-ink);
  }

  .beta-header-compact .beta-subtitle-compact {
    color: var(--beta-mobile-muted);
  }

  .beta-header-compact .beta-header-start {
    grid-column: 1;
    min-width: 0;
  }

  .beta-header-compact .beta-header-mobile-title {
    grid-column: 2;
    justify-self: center;
  }

  .beta-header-compact .beta-header-actions {
    grid-column: 3;
    justify-self: end;
    display: inline-flex;
    align-items: center;
    gap: 0.1rem;
  }

  .beta-header-compact .beta-header-nav,
  .beta-header-compact .beta-header-actions :deep(.p-button) {
    color: var(--beta-mobile-ink);
  }

  .beta-messages.user-message-container {
    padding: 0.5rem 0.85rem 0.25rem;
    background: var(--beta-mobile-bg) !important;
    color: var(--beta-mobile-ink);
  }

  .beta-shell-compact .beta-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: min(42vh, 22rem);
    padding: 1.5rem 0.75rem 1rem;
    text-align: center;
  }

  .beta-shell-compact .beta-empty-title {
    font-size: 1.35rem;
    font-weight: 650;
    letter-spacing: -0.03em;
    margin-bottom: 0.5rem;
    color: var(--beta-mobile-ink);
  }

  .beta-shell-compact .beta-empty-hint {
    max-width: 18rem;
    margin-bottom: 0;
    font-size: 0.875rem;
    line-height: 1.45;
    color: var(--beta-mobile-muted);
  }

  .beta-shell-compact .beta-mobile-prompt {
    background: var(--beta-mobile-chip-bg);
    border: 1px solid var(--beta-mobile-border);
    color: var(--beta-mobile-ink);
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  }

  .beta-shell-compact .beta-mobile-prompt:hover:not(:disabled) {
    background: var(--beta-mobile-chip-hover);
    border-color: color-mix(in srgb, var(--p-primary-color) 30%, var(--beta-mobile-border));
  }

  .beta-shell-compact .beta-msg-grid-assistant {
    grid-template-columns: 1fr;
  }

  .beta-shell-compact .beta-msg-avatar-col,
  .beta-shell-compact .beta-message-author,
  .beta-shell-compact .beta-check-icon {
    display: none;
  }

  .beta-shell-compact .beta-bubble {
    max-width: 100%;
    padding: 0.75rem 0;
    border: 0;
    border-radius: 0;
    background: transparent !important;
    box-shadow: none !important;
    backdrop-filter: none !important;
    font-size: 0.9375rem;
    line-height: 1.55;
    color: var(--beta-mobile-ink);
  }

  .beta-shell-compact .beta-bubble :deep(.chat-markdown),
  .beta-shell-compact .beta-bubble :deep(.chat-markdown p),
  .beta-shell-compact .beta-bubble :deep(.chat-markdown li) {
    color: inherit;
  }

  .beta-shell-compact .beta-bubble-user {
    max-width: 88%;
    margin-left: auto;
    padding: 0.65rem 0.85rem;
    border-radius: 1.15rem 1.15rem 0.35rem 1.15rem;
    border: 1px solid var(--beta-mobile-border);
    background: var(--beta-mobile-user-bubble) !important;
    color: var(--beta-mobile-ink) !important;
  }

  .beta-shell-compact .beta-bubble-assistant.beta-bubble-loading {
    padding: 0.35rem 0;
  }

  .beta-shell-compact .beta-message-time {
    font-size: 0.6875rem;
    opacity: 0.72;
    color: var(--beta-mobile-muted);
  }

  .beta-footer-compact {
    border-top: 1px solid var(--beta-mobile-border);
    background: var(--beta-mobile-bg) !important;
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
    padding:
      0.5rem 0.75rem
      calc(0.65rem + env(safe-area-inset-bottom, 0px));
  }

  .beta-footer-compact .beta-composer {
    background: var(--beta-mobile-composer-bg);
    border-color: var(--beta-mobile-border);
  }

  .beta-footer-compact .beta-composer-input :deep(input) {
    color: var(--beta-mobile-ink);
  }

  .beta-footer-compact .beta-composer-input :deep(input::placeholder) {
    color: var(--beta-mobile-muted);
    opacity: 1;
  }

  .beta-footer-compact .beta-composer-icon :deep(.p-button) {
    color: var(--beta-mobile-muted);
  }

  .beta-footer-compact .beta-composer-send {
    background: var(--p-primary-color) !important;
    border-color: var(--p-primary-color) !important;
    color: var(--p-primary-contrast-color) !important;
  }

  .beta-shell-compact .beta-pending {
    border-top: 0;
    background: var(--beta-mobile-bg);
    padding: 0.35rem 0.85rem 0;
    color: var(--beta-mobile-ink);
  }

  :global(.app-dark) .beta-shell-compact :deep(.deployment-subtasks-title),
  :global(.app-dark) .beta-shell-compact :deep(.deployment-subtask--pending) {
    color: var(--beta-mobile-muted);
  }

  :global(.app-dark) .beta-shell-compact :deep(.role-switch-notice) {
    color: var(--beta-mobile-ink);
  }

  .chat-pane-beta:has(.beta-shell-compact) {
    --glass-text: #0f172a;
    --glass-muted: #64748b;
    background: #f8fafc;
  }

  :global(.app-dark) .chat-pane-beta:has(.beta-shell-compact) {
    --glass-text: #f5f5f5;
    --glass-muted: #a3a3a3;
    background: #000000;
  }

  /* ---- Mobile header: tighter actions, improved role-chip contrast ---- */
  .beta-header-compact .beta-role-chip {
    color: var(--role-chip-accent, var(--beta-mobile-muted));
    background: color-mix(in srgb, var(--role-chip-accent, currentColor) 10%, transparent);
    border-color: color-mix(in srgb, var(--role-chip-accent, currentColor) 22%, transparent);
  }

  .beta-header-compact .beta-header-actions {
    gap: 0.05rem;
  }

  /* Slightly smaller action buttons on narrow screens to prevent crowding */
  .beta-header-compact .beta-header-actions :deep(.p-button.p-button-rounded) {
    width: 2.1rem;
    height: 2.1rem;
    padding: 0;
  }

  /* ---- Mobile composer: stronger surface, more comfortable touch targets ---- */
  .beta-footer-compact {
    padding:
      0.6rem 0.75rem
      calc(0.75rem + env(safe-area-inset-bottom, 0px));
  }

  .beta-footer-compact .beta-composer {
    border-radius: 1.1rem;
    box-shadow:
      0 2px 8px rgba(2, 6, 23, 0.07),
      0 0 0 1px var(--beta-mobile-border);
    border-color: transparent;
    padding: 0.4rem 0.5rem 0.4rem 0.3rem;
  }

  :global(.app-dark) .beta-footer-compact .beta-composer {
    box-shadow:
      0 2px 14px rgba(0, 0, 0, 0.35),
      0 0 0 1px var(--beta-mobile-border);
  }

  /* Slightly larger send button for easier tap target */
  .beta-footer-compact .beta-composer-send {
    width: 2.5rem !important;
    height: 2.5rem !important;
    border-radius: 0.85rem !important;
    box-shadow: 0 2px 8px color-mix(in srgb, var(--p-primary-color) 35%, transparent);
  }

  /* Composer icons consistent size */
  .beta-footer-compact .beta-composer-icon {
    width: 2.25rem;
    height: 2.25rem;
  }

  /* Input text sizing */
  .beta-footer-compact .beta-composer-input :deep(input) {
    font-size: 1rem;
    padding-top: 0.45rem;
    padding-bottom: 0.45rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .beta-mobile-prompt {
    transition: none;
  }
}

.deployment-continue-actions {
  margin-top: 0.75rem;
}

.calibration-offer-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0.75rem 0;
}

.calibration-offer-hint {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}

.calibration-dialog-lead {
  font-size: 0.875rem;
  line-height: 1.5;
  color: var(--p-text-muted-color);
  margin-bottom: 1rem;
}

.calibration-dialog-fields {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.calibration-dialog-fields label {
  font-size: 0.8125rem;
  font-weight: 600;
}

.calibration-checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8125rem;
  font-weight: normal;
  margin-top: 0.25rem;
}

.calibration-suggested-skill {
  margin-top: 0.25rem;
}

.beta-footer-calibration {
  flex-shrink: 0;
}

.architect-design-rail-detached {
  position: relative;
  top: auto;
  right: auto;
  bottom: auto;
  width: 100%;
  height: 100%;
  flex: 1;
  min-height: 0;
  z-index: auto;
  box-shadow: none;
  border-left: none;
  border-radius: 0;
  overflow: hidden;
}

.chat-pane-architect.chat-pane-design-panel-open {
  position: relative;
}

@media (min-width: 992px) {
  .chat-pane-architect.chat-pane-design-panel-open {
    flex-direction: row;
    min-height: 0;
  }

  .chat-pane-architect.chat-pane-design-panel-open .beta-shell {
    flex: 0 0 72%;
    width: 72%;
    max-width: 72%;
    min-width: 0;
    margin-right: 0;
  }

  .chat-pane-architect.chat-pane-design-panel-open .architect-design-rail {
    position: relative;
    top: auto;
    right: auto;
    bottom: auto;
    flex: 0 0 23%;
    width: 23%;
    max-width: 23%;
    min-width: 0;
    height: 100%;
    box-shadow: none;
    border-left: 1px solid var(--p-content-border-color);
  }

  .chat-pane-architect.chat-pane-design-panel-open .pane-toolbar,
  .chat-pane-architect.chat-pane-design-panel-open .ask-hero,
  .chat-pane-architect.chat-pane-design-panel-open .messages-scroll,
  .chat-pane-architect.chat-pane-design-panel-open .chat-input-bar,
  .chat-pane-architect.chat-pane-design-panel-open .calibration-offer {
    margin-right: 23%;
  }
}

.architect-design-rail:not(.architect-design-rail-detached) {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 23%;
  z-index: 4;
  box-shadow: -8px 0 24px rgba(15, 23, 42, 0.08);
}

.chat-pane-architect.chat-pane-design-panel-open .pane-toolbar,
.chat-pane-architect.chat-pane-design-panel-open .ask-hero,
.chat-pane-architect.chat-pane-design-panel-open .messages-scroll,
.chat-pane-architect.chat-pane-design-panel-open .chat-input-bar,
.chat-pane-architect.chat-pane-design-panel-open .calibration-offer {
  margin-right: 23%;
}

.architect-summary-bubble {
  font-size: 0.875rem;
}

@media (max-width: 991px) {
  .chat-pane-architect.chat-pane-design-panel-open .beta-shell,
  .chat-pane-architect.chat-pane-design-panel-open .pane-toolbar,
  .chat-pane-architect.chat-pane-design-panel-open .ask-hero,
  .chat-pane-architect.chat-pane-design-panel-open .messages-scroll,
  .chat-pane-architect.chat-pane-design-panel-open .chat-input-bar,
  .chat-pane-architect.chat-pane-design-panel-open .calibration-offer {
    margin-right: 0;
  }

  /* Document Editor on mobile: stack it full-width below the chat and let it
     take the remaining height. The base rule pins it absolutely to the right
     at 23% width, which on a phone overlaps the header action buttons. Match
     that rule's specificity here (:not(.architect-design-rail-detached)) so
     the in-flow stacked layout actually wins. */
  .architect-design-rail:not(.architect-design-rail-detached) {
    position: relative;
    top: auto;
    right: auto;
    bottom: auto;
    width: 100%;
    max-width: 100%;
    height: auto;
    flex: 1 1 auto;
    min-height: 0;
    z-index: auto;
    box-shadow: none;
    border-top: 1px solid var(--p-content-border-color);
  }

  .chat-pane-architect.chat-pane-design-panel-open {
    display: flex;
    flex-direction: column;
    min-height: 0;
  }

  /* Keep the chat reachable above, but give the document the most room. */
  .chat-pane-architect.chat-pane-design-panel-open .beta-shell {
    flex: 0 0 auto;
    height: 40vh;
    min-height: 0;
  }
}
</style>
