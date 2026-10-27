import json
import re
import asyncio
from typing import List, Tuple, Optional, Union
import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.core.logging import get_logger, mask_secret
from app.schemas.chat import ChatMessage, TaskAction, ActionType

logger = get_logger("nvidia_service")

EDITH_SYSTEM_PROMPT = """You are EDITH, an elite, highly capable AI assistant embedded in PLANORA, a personal checklist, schedule, and productivity application.
Your goal is to help the user plan their day, prioritize tasks, break down complex projects into actionable milestones, and manage checklists with speed and precision.

Key Behavior:
1. Be concise, direct, supportive, and organized.
2. Provide structured, actionable advice.
3. CRITICAL: When the user asks to create, schedule, prioritize, complete, delete, or break down tasks, you MUST:
   a. Write a brief natural language reply FIRST explaining what you are doing (e.g., "I'll schedule your meeting for tomorrow at 6:00 PM.").
   b. Append a structured JSON action block at the very end of your response inside a ```json ... ``` code block.

The action block must strictly follow this JSON schema:
```json
{
  "actions": [
    {
      "action_type": "CREATE_TASK" | "EDIT_TASK" | "COMPLETE_TASK" | "DELETE_TASK" | "BREAKDOWN",
      "title": "Clear concise task title",
      "description": "Optional details or context",
      "priority": "NONE" | "LOW" | "MEDIUM" | "HIGH" | "URGENT",
      "due_date": null,
      "subtasks": ["Milestone 1", "Milestone 2"]
    }
  ]
}
```

Rules for Task Extraction:
- Clean titles: The title must be the actual task (e.g., "Meeting", "Math Assignment", "Grocery Shopping"). Do not prefix titles with "I have a" or "Add a".
- Dates & Times: Put specific schedule information into description or due_date.
- Conversational Queries: If no task modifications are needed (e.g. conversational questions, tips, greetings, general advice), do NOT include a JSON action block.
"""

class NvidiaAiService:
    def __init__(self):
        self.base_url = settings.NVIDIA_BASE_URL.rstrip("/")
        self.default_model = settings.NVIDIA_MODEL
        self.timeout = settings.TIMEOUT_SECONDS
        self.max_retries = settings.MAX_RETRIES

    def is_configured(self) -> bool:
        return bool(settings.NVIDIA_API_KEY and settings.NVIDIA_API_KEY.strip())

    async def generate_chat_response(
        self,
        messages: List[ChatMessage],
        model: str = None,
        task_context: str = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> Tuple[str, List[TaskAction], str]:
        if not self.is_configured():
            logger.warning("NVIDIA_API_KEY is not configured.")
            raise HTTPException(
                status_code=401,
                detail="NVIDIA_API_KEY is not configured on the backend server. Please configure it in .env or environment variables."
            )

        active_model = model or self.default_model
        endpoint = f"{self.base_url}/chat/completions"

        # Format conversation payload, ensuring system prompt is prepended with task context
        system_content = EDITH_SYSTEM_PROMPT
        if task_context and task_context.strip():
            system_content += f"\n\nCURRENT USER CHECKLIST (PLANORA):\n{task_context.strip()}\nUse this live context to give accurate, personalized answers regarding the user's tasks, schedule, and daily priorities."

        formatted_messages = [{"role": "system", "content": system_content}]
        for msg in messages:
            role_str = msg.role.value if hasattr(msg.role, "value") else str(msg.role)
            if role_str != "system":
                formatted_messages.append({"role": role_str, "content": msg.content})

        payload = {
            "model": active_model,
            "messages": formatted_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "chat_template_kwargs": {"enable_thinking": False},
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.NVIDIA_API_KEY}",
        }

        logger.info(f"Dispatching chat request to NVIDIA catalog. Model: {active_model}, Key: {mask_secret(settings.NVIDIA_API_KEY)}")

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(endpoint, json=payload, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    message_obj = data["choices"][0]["message"]
                    raw_content = message_obj.get("content")
                    if not raw_content and message_obj.get("reasoning_content"):
                        raw_content = message_obj["reasoning_content"]
                    if not raw_content:
                        raw_content = "I have processed your request."
                    clean_reply, actions = self._extract_actions(raw_content)
                    return clean_reply, actions, active_model

                elif response.status_code == 429:
                    logger.warning(f"Rate limited by NVIDIA API (429). Attempt {attempt + 1}/{self.max_retries + 1}")
                    if attempt < self.max_retries:
                        await asyncio.sleep(2.0 * (attempt + 1))
                        continue
                    raise HTTPException(
                        status_code=429,
                        detail="NVIDIA API rate limit reached. Please wait a moment before trying again."
                    )

                elif response.status_code == 401 or response.status_code == 403:
                    logger.error("Authentication failed with NVIDIA API.")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail="Invalid or unauthorized NVIDIA API key. Please check your credentials in .env."
                    )

                elif response.status_code == 404:
                    logger.error(f"Requested model '{active_model}' not found or endpoint unavailable.")
                    raise HTTPException(
                        status_code=404,
                        detail=f"Model '{active_model}' was not found in the NVIDIA catalog."
                    )

                else:
                    logger.error(f"NVIDIA API error: HTTP {response.status_code} - {response.text}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"NVIDIA API returned error HTTP {response.status_code}."
                    )

            except httpx.TimeoutException:
                logger.error("Request to NVIDIA API timed out.")
                if attempt < self.max_retries:
                    await asyncio.sleep(1.0)
                    continue
                raise HTTPException(
                    status_code=504,
                    detail="NVIDIA API timed out while generating a response."
                )

            except httpx.RequestError as e:
                logger.error(f"Network error connecting to NVIDIA API: {str(e)}")
                if attempt < self.max_retries:
                    await asyncio.sleep(1.0)
                    continue
                raise HTTPException(
                    status_code=502,
                    detail=f"Network error connecting to NVIDIA API: {str(e)}"
                )

        raise HTTPException(
            status_code=500,
            detail="Failed to communicate with NVIDIA API after retries."
        )

    def _extract_actions(self, content: str) -> Tuple[str, List[TaskAction]]:
        """
        Parses structured task actions out of the raw response text,
        validates them against the TaskAction schema, and strips all JSON
        blocks completely from the user-facing text.
        Guarantees that raw JSON is never returned in user-facing reply.
        """
        actions: List[TaskAction] = []
        clean_text = content

        # Search for ```json ... ``` blocks or raw {"actions": ...}
        json_blocks = re.findall(r"```(?:json)?\s*(\{\s*\"actions\"[\s\S]*?\})\s*```", content, re.IGNORECASE)
        if not json_blocks:
            json_blocks = re.findall(r"(\{\s*\"actions\"\s*:\s*\[[\s\S]*?\]\s*\})", content)

        for json_str in json_blocks:
            try:
                parsed = json.loads(json_str)
                raw_actions = parsed.get("actions", [])
                for act in raw_actions:
                    try:
                        raw_action_type = str(act.get("action_type", "CREATE_TASK")).upper()
                        try:
                            action_type = ActionType(raw_action_type)
                        except ValueError:
                            action_type = ActionType.CREATE_TASK

                        priority = str(act.get("priority", "MEDIUM")).upper()
                        if priority not in ["NONE", "LOW", "MEDIUM", "HIGH", "URGENT"]:
                            priority = "MEDIUM"

                        title = str(act.get("title", "")).strip()
                        # Reject empty or single-character noise
                        if not title or len(title) < 2:
                            continue

                        due_date_raw = act.get("due_date")
                        due_date_val = None
                        if isinstance(due_date_raw, (int, float)):
                            due_date_val = int(due_date_raw)
                        elif isinstance(due_date_raw, str) and due_date_raw.isdigit():
                            due_date_val = int(due_date_raw)

                        task_action = TaskAction(
                            action_type=action_type,
                            title=title,
                            description=str(act.get("description", "") or "").strip(),
                            priority=priority,
                            due_date=due_date_val,
                            subtasks=[str(s).strip() for s in act.get("subtasks", []) if str(s).strip()],
                        )
                        actions.append(task_action)
                    except Exception as parse_ex:
                        logger.warning(f"Skipping malformed action item: {parse_ex}")
            except json.JSONDecodeError:
                logger.warning("Found action block candidate but failed to parse JSON.")

        # Completely strip any ```json ... ``` code blocks from displayed text
        clean_text = re.sub(r"```(?:json)?\s*\{\s*\"actions\"[\s\S]*?\}\s*```", "", content, flags=re.IGNORECASE)
        # Also strip any bare JSON action blocks
        clean_text = re.sub(r"\{\s*\"actions\"\s*:\s*\[[\s\S]*?\]\s*\}", "", clean_text)
        # Clean up any leftover empty code block markers or excess whitespace
        clean_text = re.sub(r"```\s*```", "", clean_text)
        clean_text = clean_text.strip()

        # If clean_text is empty because the model only emitted JSON, synthesize a natural explanation
        if not clean_text and actions:
            action_phrases = []
            for act in actions:
                if act.action_type == ActionType.CREATE_TASK:
                    action_phrases.append(f"I'll add '{act.title}' to your checklist")
                elif act.action_type == ActionType.COMPLETE_TASK:
                    action_phrases.append(f"I'll mark '{act.title}' as completed")
                elif act.action_type == ActionType.DELETE_TASK:
                    action_phrases.append(f"I'll remove '{act.title}' from your checklist")
                elif act.action_type == ActionType.BREAKDOWN:
                    action_phrases.append(f"I'll break down '{act.title}' into subtasks")
                elif act.action_type == ActionType.EDIT_TASK:
                    action_phrases.append(f"I'll update '{act.title}'")
            clean_text = ". ".join(action_phrases) + "."
        elif not clean_text:
            clean_text = "I have processed your request."

        return clean_text, actions

nvidia_service = NvidiaAiService()
