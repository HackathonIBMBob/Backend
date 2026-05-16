import json
from typing import Any, Dict, List

from ai_pipeline.agents.analyzer_agent import AnalyzerAgent


class RefactorAgent(AnalyzerAgent):
    def run(self, repo_files: List[dict], analysis: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""
You are Bob Refactor Agent, a senior software engineer.

Based on this repository and analysis, propose a modern refactoring plan.

Analysis JSON:
{json.dumps(analysis, ensure_ascii=False, indent=2)}

Repository files:
{self._repo_context(repo_files)}

Return ONLY valid JSON with this exact shape:
{{
  "refactor_plan": ["ordered step"],
  "suggested_improvements": [
    {{"area": "module or concern", "improvement": "description", "priority": "high|medium|low"}}
  ],
  "new_project_structure": [
    {{"path": "target/path", "purpose": "why this file or folder exists"}}
  ],
  "migration_notes": ["practical implementation note"]
}}

Respond only with JSON.
""".strip()
        return self._generate_json(prompt)
