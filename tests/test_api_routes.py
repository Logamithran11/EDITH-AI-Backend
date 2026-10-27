from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "service" in data

def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "EDITH AI Backend"
    assert "nvidia_configured" in data
    assert "default_model" in data

def test_models_endpoint():
    response = client.get("/api/models")
    assert response.status_code == 200
    data = response.json()
    assert "default_model" in data
    assert "available_candidates" in data
    assert len(data["available_candidates"]) > 0

def test_chat_empty_messages_validation():
    response = client.post("/api/chat", json={"messages": []})
    assert response.status_code == 400
    assert "At least one message is required" in response.json()["detail"]

def test_chat_unconfigured_api_key(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "NVIDIA_API_KEY", "")
    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "Plan my day"}]}
    )
    assert response.status_code == 401
    assert "NVIDIA_API_KEY is not configured" in response.json()["detail"]

def test_chat_mocked_successful_ai_response(monkeypatch):
    from unittest.mock import AsyncMock
    from app.services.nvidia_service import nvidia_service
    from app.schemas.chat import TaskAction, ActionType

    async def mock_generate_chat_response(messages, model=None, task_context=None, temperature=0.5, max_tokens=1024):
        return (
            "Hello! Here is your daily plan based on your tasks.",
            [
                TaskAction(
                    action_type=ActionType.CREATE_TASK,
                    title="Finish Q3 audit",
                    priority="HIGH",
                    description="From assistant",
                )
            ],
            "nvidia/nemotron-3.5-lightning-30b-a3b",
        )

    monkeypatch.setattr(nvidia_service, "generate_chat_response", mock_generate_chat_response)

    response = client.post(
        "/api/chat",
        json={
            "messages": [
                {"role": "user", "content": "Hello, plan my day"}
            ],
            "task_context": "- [HIGH] Finish Q3 audit",
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["reply"] == "Hello! Here is your daily plan based on your tasks."
    assert data["model"] == "nvidia/nemotron-3.5-lightning-30b-a3b"
    assert data["is_live_ai"] is True
    assert len(data["actions"]) == 1
    assert data["actions"][0]["title"] == "Finish Q3 audit"
    assert data["actions"][0]["priority"] == "HIGH"
    assert data["actions"][0]["action_type"] == "CREATE_TASK"

def test_chat_mocked_nvidia_timeout(monkeypatch):
    from fastapi import HTTPException
    from app.services.nvidia_service import nvidia_service

    async def mock_timeout(messages, model=None, task_context=None, temperature=0.5, max_tokens=1024):
        raise HTTPException(status_code=504, detail="NVIDIA API timed out while generating a response.")

    monkeypatch.setattr(nvidia_service, "generate_chat_response", mock_timeout)

    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "What is my highest priority?"}]}
    )
    assert response.status_code == 504
    assert "timed out" in response.json()["detail"]
