import json
from typing import Any, Dict, List


class AnalyzerAgent:
    MAX_FILES_IN_CONTEXT = 40
    MAX_CHARS_PER_FILE = 6000

    def __init__(self, llm_client):
        self.llm = llm_client

    def run(self, repo_files: List[dict]) -> Dict[str, Any]:
        prompt = f"""
You are Bob Analyzer Agent, an expert software architect.

Analyze this repository and return structured JSON with architecture issues, potential bugs,
security risks, and a quality score.

Repository files:
{self._repo_context(repo_files)}

Return ONLY valid JSON with this exact shape:
{{
  "architecture_issues": [
    {{"file": "path or global", "issue": "description", "severity": "high|medium|low"}}
  ],
  "potential_bugs": [
    {{"file": "path", "bug": "description", "severity": "high|medium|low"}}
  ],
  "security_risks": [
    {{"file": "path", "risk": "description", "severity": "high|medium|low", "recommendation": "fix"}}
  ],
  "quality_score": 0,
  "summary": "short technical summary"
}}

Use a quality_score from 0 to 100. Respond only with JSON.
""".strip()
        return self._generate_json(prompt)

    def _repo_context(self, repo_files: List[dict], include_content: bool = True) -> str:
        snippets = []
        for file_info in repo_files[: self.MAX_FILES_IN_CONTEXT]:
            path = file_info.get("path", "unknown")
            language = file_info.get("language", "unknown")
            size_lines = file_info.get("size_lines", 0)
            header = f"File: {path}\nLanguage: {language}\nLines: {size_lines}"

            if not include_content:
                snippets.append(header)
                continue

            content = str(file_info.get("content", ""))
            if len(content) > self.MAX_CHARS_PER_FILE:
                content = content[: self.MAX_CHARS_PER_FILE] + "\n... [truncated]"
            snippets.append(f"{header}\nCode:\n{content}")

        if len(repo_files) > self.MAX_FILES_IN_CONTEXT:
            snippets.append(f"... [{len(repo_files) - self.MAX_FILES_IN_CONTEXT} more files omitted]")

        return "\n\n---\n\n".join(snippets)

    def _generate_json(self, prompt: str) -> Dict[str, Any]:
        if hasattr(self.llm, "generate_json"):
            return self.llm.generate_json(prompt)

        if hasattr(self.llm, "_generate_json"):
            return self.llm._generate_json(prompt)

        text = self._generate_text(prompt)
        return json.loads(self._strip_json_fences(text))

    def _generate_text(self, prompt: str) -> str:
        if hasattr(self.llm, "generate_text"):
            return self.llm.generate_text(prompt=prompt)

        if hasattr(self.llm, "generate"):
            response = self.llm.generate(prompt)
            return self._response_to_text(response)

        if hasattr(self.llm, "invoke"):
            response = self.llm.invoke(prompt)
            return self._response_to_text(response)

        if callable(self.llm):
            return self._response_to_text(self.llm(prompt))

        raise TypeError("llm_client must expose generate_json, _generate_json, generate_text, generate, invoke, or be callable")

    @staticmethod
    def _response_to_text(response: Any) -> str:
        if isinstance(response, str):
            return response
        if isinstance(response, dict):
            for key in ("text", "content", "output", "response"):
                if key in response:
                    return str(response[key])
        if hasattr(response, "content"):
            return str(response.content)
        return str(response)

    @staticmethod
    def _strip_json_fences(text: str) -> str:
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[len("```json") :].strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned[len("```") :].strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
        return cleaned
