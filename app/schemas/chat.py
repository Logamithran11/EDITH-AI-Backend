from enum import Enum
from typing import List, Optional, Union
from pydantic import BaseModel, Field

class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class ActionType(str, Enum):
    CREATE_TASK = "CREATE_TASK"
    EDIT_TASK = "EDIT_TASK"
    COMPLETE_TASK = "COMPLETE_TASK"
    DELETE_TASK = "DELETE_TASK"
    BREAKDOWN = "BREAKDOWN"

class TaskAction(BaseModel):
    action_type: ActionType
    title: str
    description: Optional[str] = ""
    priority: str = "MEDIUM"  # NONE, LOW, MEDIUM, HIGH, URGENT
    due_date: Optional[Union[int, str]] = None
    estimated_minutes: Optional[int] = None
    subtasks: List[str] = Field(default_factory=list)

class ChatMessage(BaseModel):
    role: MessageRole
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    task_context: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = 0.5
    max_tokens: Optional[int] = 1024

class ChatResponse(BaseModel):
    reply: str
    actions: List[TaskAction] = Field(default_factory=list)
    model: str
    is_live_ai: bool = True
