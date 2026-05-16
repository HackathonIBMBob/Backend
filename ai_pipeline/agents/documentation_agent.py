import json
from typing import Any, Dict, List

from ai_pipeline.agents.analyzer_agent import AnalyzerAgent


class DocumentationAgent(AnalyzerAgent):
    def run(
        self,
        repo_files: List[dict],
        analysis: Dict[str, Any],
        refactor_plan: Dict[str, Any],
    ) -> Dict[str, Any]:
        prompt = f"""
You are Bob Documentation Agent, a technical writer for software engineering teams.

Generate technical documentation for this system based on the analysis and refactor plan.

Analysis JSON:
{json.dumps(analysis, ensure_ascii=False, indent=2)}

Refactor plan JSON:
{json.dumps(refactor_plan, ensure_ascii=False, indent=2)}

Repository files:
{self._repo_context(repo_files, include_content=False)}

Return ONLY valid JSON with this exact shape:
{{
  "technical_readme": "README content in markdown",
  "system_explanation": "clear explanation of the system architecture and flow",
  "endpoints_or_modules": [
    {{"name": "endpoint or module", "description": "what it does"}}
  ],
  "runbook": ["setup or operational note"]
}}

Respond only with JSON.
""".strip()
        return self._generate_json(prompt)
