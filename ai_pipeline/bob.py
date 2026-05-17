from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from ai_pipeline.agents import AnalyzerAgent, DocumentationAgent, RefactorAgent


class BobOrchestrator:
    """Async multi-agent LLM pipeline for repository modernization."""

    def __init__(self, llm_client):
        self.llm = llm_client
        self.analyzer = AnalyzerAgent(llm_client)
        self.refactor_agent = RefactorAgent(llm_client)
        self.documentation_agent = DocumentationAgent(llm_client)

    async def run(self, repo_files: List[dict]) -> Dict[str, Any]:
        analysis = await self.analyze(repo_files)
        refactor = await self.refactor(repo_files, analysis)
        docs = await self.document(repo_files, analysis, refactor)

        return {
            "analysis": analysis,
            "refactor": refactor,
            "documentation": docs,
        }

    async def analyze(self, repo_files: List[dict]) -> Dict[str, Any]:
        return await asyncio.to_thread(self.analyzer.run, repo_files)

    async def refactor(
        self,
        repo_files: List[dict],
        analysis: Dict[str, Any],
        dep_files: List[dict] | None = None,
    ) -> Dict[str, Any]:
        return await asyncio.to_thread(self.refactor_agent.run, repo_files, analysis, dep_files or [])

    async def document(
        self,
        repo_files: List[dict],
        analysis: Dict[str, Any],
        refactor_plan: Dict[str, Any],
    ) -> Dict[str, Any]:
        return await asyncio.to_thread(
            self.documentation_agent.run,
            repo_files,
            analysis,
            refactor_plan,
        )
