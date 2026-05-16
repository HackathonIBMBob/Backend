import json
import os
from typing import List

from dotenv import load_dotenv


load_dotenv()

MODEL_ID = "ibm/granite-34b-code-instruct"


def _credential_error() -> str | None:
    api_key = os.getenv("WATSONX_APIKEY")
    project_id = os.getenv("WATSONX_PROJECT_ID")
    if not api_key or api_key == "your_api_key_here":
        return "WATSONX_APIKEY is not configured in .env"
    if not project_id or project_id == "your_project_id_here":
        return "WATSONX_PROJECT_ID is not configured in .env"
    return None


def _strip_json_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[len("```json") :].strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned[len("```") :].strip()
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()
    return cleaned


def _model():
    credential_error = _credential_error()
    if credential_error:
        raise RuntimeError(credential_error)

    from ibm_watsonx_ai import APIClient, Credentials
    from ibm_watsonx_ai.foundation_models import ModelInference

    credentials = Credentials(
        url=os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com"),
        api_key=os.getenv("WATSONX_APIKEY"),
    )
    client = APIClient(credentials)
    return ModelInference(
        model_id=MODEL_ID,
        api_client=client,
        project_id=os.getenv("WATSONX_PROJECT_ID"),
        params={
            "decoding_method": "greedy",
            "max_new_tokens": 4096,
            "temperature": 0,
        },
    )


def _generate_json(prompt: str) -> dict:
    response = _model().generate_text(prompt=prompt)
    return json.loads(_strip_json_fences(response))


def analyze_architecture(files: List[dict]) -> dict:
    try:
        summaries = []
        for file_info in files:
            first_lines = "\n".join(file_info.get("content", "").splitlines()[:20])
            summaries.append(f"File: {file_info.get('path')}\nLanguage: {file_info.get('language')}\n{first_lines}")

        prompt = f"""
You are an expert software architect analyzing a legacy codebase.

Codebase files:
{chr(10).join(summaries)}

Return ONLY valid JSON with this exact shape:
{{
  "architecture_summary": "string describing overall architecture",
  "detected_languages": ["list of languages found"],
  "risk_zones": [
    {{"file": "filename", "issue": "description", "severity": "high|medium|low"}}
  ],
  "modernization_plan": ["step 1", "step 2", "step 3"]
}}

Respond ONLY with a valid JSON object. No markdown fences, no explanation, no preamble.
""".strip()
        return _generate_json(prompt)
    except Exception as exc:
        print(f"Bob architecture analysis error: {exc}")
        return {"error": str(exc)}


def modernize_file(filename: str, code: str, language: str, plan: str) -> dict:
    try:
        prompt = f"""
You are an expert {language} developer modernizing legacy code.

Filename: {filename}
Modernization plan context:
{plan}

Full code:
{code}

Return ONLY valid JSON with this exact shape:
{{
  "modernized_code": "the full modernized code as string",
  "changes_summary": "bullet list of what changed",
  "documentation": "docstring/comments explaining the modernized code"
}}

Respond ONLY with a valid JSON object. No markdown fences, no explanation, no extra text.
""".strip()
        result = _generate_json(prompt)
        result.setdefault("modernized_code", code)
        result.setdefault("changes_summary", "")
        result.setdefault("documentation", "")
        return result
    except Exception as exc:
        print(f"Bob file modernization error for {filename}: {exc}")
        return {"error": str(exc)}
