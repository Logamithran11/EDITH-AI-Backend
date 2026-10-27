from app.schemas.chat import (
    ChatMessage,
    MessageRole,
    TaskAction,
    ActionType,
    ChatRequest,
    ChatResponse,
)

def test_chat_message_creation():
    msg = ChatMessage(role=MessageRole.USER, content="Plan my day")
    assert msg.role == MessageRole.USER
    assert msg.content == "Plan my day"

def test_task_action_defaults():
    action = TaskAction(
        action_type=ActionType.CREATE_TASK,
        title="Review PR",
    )
    assert action.action_type == ActionType.CREATE_TASK
    assert action.title == "Review PR"
    assert action.priority == "MEDIUM"
    assert action.subtasks == []

def test_chat_request_validation():
    req = ChatRequest(
        messages=[ChatMessage(role=MessageRole.USER, content="Hello")],
        model="nvidia/nemotron-3.5-lightning-30b-a3b",
    )
    assert len(req.messages) == 1
    assert req.model == "nvidia/nemotron-3.5-lightning-30b-a3b"
