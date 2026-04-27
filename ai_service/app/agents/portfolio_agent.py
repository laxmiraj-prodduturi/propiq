from __future__ import annotations

from .base import run_specialist
from ..services.agent_tools import PORTFOLIO_TOOLS

_SYSTEM_PROMPT = """\
You are a Portfolio Analyst Agent for a residential property management platform.
Your job is to analyze the property portfolio and provide clear insights on:
- Occupancy rates and vacancy status
- Portfolio-wide rent collection summary
- Overall maintenance burden
- Portfolio health and key metrics

Use your tools to fetch real data. Be concise and cite actual figures.
Do not speculate — base all answers on tool results."""


def run(query: str) -> str:
    return run_specialist(
        name="PortfolioAgent",
        system_prompt=_SYSTEM_PROMPT,
        tools=PORTFOLIO_TOOLS,
        query=query,
    )
