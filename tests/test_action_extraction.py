from app.services.nvidia_service import nvidia_service
from app.schemas.chat import ActionType

def test_extract_actions_single_task():
    raw_response = """Here is your plan for today:
1. Finish the report

```json
{
  "actions": [
    {
      "action_type": "CREATE_TASK",
      "title": "Finish quarterly report",
      "description": "Complete sections 3 and 4",
      "priority": "HIGH"
    }
  ]
}
```
Let me know if you need any adjustments!"""

    clean_text, actions = nvidia_service._extract_actions(raw_response)
    assert len(actions) == 1
    assert actions[0].action_type == ActionType.CREATE_TASK
    assert actions[0].title == "Finish quarterly report"
    assert actions[0].priority == "HIGH"
    assert "```json" not in clean_text
    assert "Here is your plan for today:" in clean_text
    assert "Let me know if you need any adjustments!" in clean_text

def test_extract_actions_breakdown():
    raw_response = """I have broken down your mobile app launch:
```json
{
  "actions": [
    {
      "action_type": "BREAKDOWN",
      "title": "Mobile App Launch",
      "priority": "URGENT",
      "subtasks": [
        "Finalize APK release build",
        "Prepare screenshots",
        "Submit to Play Store"
      ]
    }
  ]
}
```"""

    clean_text, actions = nvidia_service._extract_actions(raw_response)
    assert len(actions) == 1
    assert actions[0].action_type == ActionType.BREAKDOWN
    assert len(actions[0].subtasks) == 3
    assert actions[0].subtasks[0] == "Finalize APK release build"
    assert actions[0].priority == "URGENT"

def test_extract_actions_none():
    raw_response = "You should prioritize your highest priority task first, then take a 5-minute break."
    clean_text, actions = nvidia_service._extract_actions(raw_response)
    assert len(actions) == 0
    assert clean_text == raw_response

def test_extract_actions_only_json_synthesizes_natural_reply():
    raw_response = """```json
{
  "actions": [
    {
      "action_type": "CREATE_TASK",
      "title": "Team Standup",
      "description": "Tomorrow at 10 AM",
      "priority": "MEDIUM"
    }
  ]
}
```"""
    clean_text, actions = nvidia_service._extract_actions(raw_response)
    assert len(actions) == 1
    assert actions[0].title == "Team Standup"
    assert "Team Standup" in clean_text
    assert "{" not in clean_text
    assert "actions" not in clean_text
    assert "```" not in clean_text

def test_extract_actions_rejects_single_character_noise():
    raw_response = """I noticed some noise.
```json
{
  "actions": [
    {
      "action_type": "CREATE_TASK",
      "title": "n",
      "priority": "NONE"
    },
    {
      "action_type": "CREATE_TASK",
      "title": "Valid Planning Session",
      "priority": "HIGH"
    }
  ]
}
```"""
    clean_text, actions = nvidia_service._extract_actions(raw_response)
    assert len(actions) == 1
    assert actions[0].title == "Valid Planning Session"

def test_extract_actions_malformed_json_fallback():
    raw_response = """Here is the task:
```json
{ "actions": [ { broken json
```
Hope that helps!"""
    clean_text, actions = nvidia_service._extract_actions(raw_response)
    assert len(actions) == 0
    assert "Here is the task:" in clean_text
    assert "Hope that helps!" in clean_text
