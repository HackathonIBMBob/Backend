from __future__ import annotations

import json
from typing import Any, Dict, List

from ai_pipeline.agents.analyzer_agent import AnalyzerAgent


class RefactorAgent(AnalyzerAgent):
    MAX_DEP_FILE_CHARS = 8000

    def run(
        self,
        repo_files: List[dict],
        analysis: Dict[str, Any],
        dep_files: List[Dict[str, str]] | None = None,
    ) -> Dict[str, Any]:
        dep_context = self._dep_context(dep_files or [])
        prompt = f"""
You are Bob Refactor Agent, a senior software engineer specializing in legacy code modernization.

## Existing dependency manifests (pom.xml, package.json, etc.)
These are the ONLY libraries currently available in the project.
{dep_context}

## Static analysis results
{json.dumps(analysis, ensure_ascii=False, indent=2)}

## Repository source files
{self._repo_context(repo_files)}

## Your task
Produce a precise, actionable modernization plan following these strict rules:

RULE 1 — IMPORTS: Only suggest imports from libraries that already appear in the dependency
manifests above. Do NOT invent libraries that are not listed there.

RULE 2 — NEW DEPENDENCIES: If and only if a modernization step genuinely requires a library
that is NOT already in the manifests, add it to "dependency_updates" with the full updated
content of that manifest file (pom.xml or package.json). If no new deps are needed, leave
"dependency_updates" as an empty list.

RULE 3 — VARIABLE VALIDATION: Before referencing any variable or method in your suggestions,
confirm it is defined somewhere in the scanned source files. Report any suspicious undefined
references in "variable_warnings".

RULE 4 — CONSERVATISM: Prefer upgrading what already exists over rewriting from scratch.
Only propose a full rewrite when the existing code is beyond repair.

Return ONLY valid JSON with this exact shape:
{{
  "refactor_plan": ["ordered modernization step 1", "step 2"],
  "suggested_improvements": [
    {{
      "area": "module, class, or concern",
      "improvement": "concrete description of what to change and how",
      "priority": "high|medium|low",
      "requires_new_dep": false
    }}
  ],
  "dependency_updates": [
    {{
      "file": "pom.xml",
      "reason": "why this dependency is being added",
      "updated_content": "FULL updated file content including the new dependency"
    }}
  ],
  "new_project_structure": [
    {{"path": "target/path", "purpose": "why this file or folder exists"}}
  ],
  "migration_notes": ["practical note about applying this plan"],
  "variable_warnings": ["path/to/file.java:42 — variable X referenced but not found in scanned files"]
}}

Respond ONLY with a valid JSON object. No markdown, no explanation.
""".strip()
        return self._generate_json(prompt)

    def _dep_context(self, dep_files: List[Dict[str, str]]) -> str:
        if not dep_files:
            return "(no dependency manifests found in the repository)"
        parts = []
        for dep in dep_files:
            content = dep["content"]
            if len(content) > self.MAX_DEP_FILE_CHARS:
                content = content[: self.MAX_DEP_FILE_CHARS] + "\n... [truncated]"
            parts.append(f"### {dep['path']}\n{content}")
        return "\n\n".join(parts)
