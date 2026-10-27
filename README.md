# PLANORA — EDITH AI Assistant Backend (NVIDIA AI Catalog)

FastAPI backend that interfaces the **PLANORA** Android application with hosted models from the **NVIDIA API Catalog** (`https://integrate.api.nvidia.com/v1`) powered by the **EDITH** AI assistant.

---

## 1. Prerequisites

- Python 3.10+
- An NVIDIA NGC account and API key from [build.nvidia.com](https://build.nvidia.com)

---

## 2. Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Obtain your personal API key from [https://build.nvidia.com](https://build.nvidia.com) (free trial credits are provided upon registration).
3. Set your key in `.env`:
   ```bash
   NVIDIA_API_KEY=nvapi-your-actual-api-key
   ```
4. (Optional) Choose your model from the NVIDIA catalog. Default is:
   ```bash
   NVIDIA_MODEL=nvidia/nemotron-3.5-lightning-30b-a3b
   ```
   Other verified catalog options include:
   - `nvidia/nemotron-3.5-bolt-e4b`
   - `openai/gpt-oss-20b`
   - `nvidia/llama-3.1-nemotron-70b-instruct`

---

## 3. Running the Server

Install requirements:
```bash
pip install -r requirements.txt
```

Start the FastAPI server:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 4. API Endpoints

- `GET /health` — Health check, returns whether NVIDIA key is loaded.
- `GET /api/models` — Lists available candidate models.
- `POST /api/chat` — Accepts conversation history and returns assistant response with parsed task actions.

### Example Request
```json
POST /api/chat
Content-Type: application/json

{
  "messages": [
    {"role": "user", "content": "Break down my project launch into 3 tasks"}
  ]
}
```

### Example Response
```json
{
  "reply": "I've organized your project launch into 3 milestones.",
  "actions": [
    {
      "action_type": "BREAKDOWN",
      "title": "Project Launch",
      "priority": "HIGH",
      "subtasks": ["Finalize build", "Beta testing", "Publish release"]
    }
  ],
  "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
  "is_live_ai": true
}
```

---

## 5. Connecting from the Android App

- **Android Emulator**: Uses `http://10.0.2.2:8000/` (default mapped).
- **Physical Device**: Set your computer's local Wi-Fi IP (e.g. `http://192.168.1.50:8000/`) in the EDITH Settings screen.
- **Offline / Standalone**: If the backend is not running or no key is configured, EDITH automatically falls back to the deterministic local NLP engine with zero crashes.
