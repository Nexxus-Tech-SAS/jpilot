import base64
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Blueprint suggestion card — surfaced when a strict match missed but a
# relaxed/secondary match found a plausible candidate.
# ---------------------------------------------------------------------------

ChatRole = Literal["architect", "operator", "analyst"]


class CopilotSettings(BaseModel):
    allowImages: bool = True
    allowConfigFiles: bool = True
    maxAttachments: int = Field(default=5, ge=1, le=10)


class ChatAttachment(BaseModel):
    name: str
    kind: Literal["image", "config"]
    mimeType: str
    data: str


class ChatMessage(BaseModel):
    role: str
    content: str


class CopilotRoleResponse(BaseModel):
    id: str
    label: str
    description: str
    requiresAppliance: bool
    suggestedPaneLabel: str
    handoffTarget: str | None = None
    baseRole: str | None = None
    isCustomPersona: bool = False
    # Persona-first model: every entry is a persona. `kind` discriminates the three
    # built-in base-role personas from installed/custom ones; `capability` is the
    # user-facing label derived from baseRole (Plan-only / Read-only / Full control).
    kind: Literal["builtin", "custom"] = "builtin"
    capability: str = ""


class DeploymentSubtask(BaseModel):
    id: str
    label: str
    status: Literal["pending", "in_progress", "completed", "failed"] = "pending"


class DeploymentContinuation(BaseModel):
    required: bool = False
    reason: Literal["long_task", "tool_limit"] = "long_task"
    message: str = ""
    subtasks: list[DeploymentSubtask] = []


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    attachments: list[ChatAttachment] = []
    settings: CopilotSettings | None = None
    role: ChatRole = "operator"
    personaId: str | None = None
    applianceName: str | None = None
    providerId: str | None = None
    webSearch: bool = True
    deploymentContinuation: bool = False
    longTaskApproved: bool = False
    designDocumentContext: str | None = None
    includeDesignRevision: bool = False
    skipBlueprintSkillId: str | None = None


class CopilotApplianceItem(BaseModel):
    id: str
    name: str
    environment: str
    enabled: bool
    notes: str = ""
    vendor: str = "netscaler"
    productId: str | None = None
    copilotEligible: bool = True
    platformEnabled: bool = True
    chatAvailable: bool = False


class CopilotConnectRequest(BaseModel):
    applianceName: str


class CopilotConnectResponse(BaseModel):
    success: bool
    applianceName: str
    environment: str = ""
    message: str
    api: str = "NetScaler Next-Gen API"
    apiPath: str = "/mgmt/api/nextgen/v1"
    loginEndpoint: str = "/mgmt/api/nextgen/v1/login"
    authenticatedUser: str = ""


class ToolCallTrace(BaseModel):
    name: str
    arguments: dict
    result: str


class InputFormField(BaseModel):
    id: str
    label: str
    type: str = "text"
    required: bool = False
    placeholder: str = ""
    hint: str = ""
    default: str | bool | int | float | None = None
    options: list[dict[str, str]] = []


class InputForm(BaseModel):
    title: str
    description: str = ""
    submitLabel: str = "Submit"
    fields: list[InputFormField] = []


class BlueprintSuggestion(BaseModel):
    """Surfaced on every turn where a blueprint is relevant.

    state="applied"   — strict match hit; blueprint injected silently this turn.
    state="suggested" — strict miss, relaxed candidate found; user can apply or skip.
    """

    skillId: str
    label: str
    summary: str = ""
    confidence: int = 0
    action: Literal["apply", "install"] = "apply"
    applyPrompt: str
    state: Literal["applied", "suggested"] = "suggested"


class ChatResponse(BaseModel):
    role: str = "assistant"
    content: str
    providerName: str
    providerType: str
    model: str
    toolCalls: list[ToolCallTrace] = []
    inputForm: InputForm | None = None
    deploymentContinuation: DeploymentContinuation | None = None
    blueprintSuggestion: BlueprintSuggestion | None = None


class CopilotStatusResponse(BaseModel):
    ready: bool
    providerName: str | None = None
    providerType: str | None = None
    model: str | None = None
    message: str = ""
    settings: CopilotSettings = CopilotSettings()
