"""
Multi-Agent Framework for Cancer Genomics Pipeline

This module implements a multi-agent architecture for parallel cancer biomarker
analysis. Each agent specializes in specific genes or biomarkers, coordinated by
a supervisor agent.

Architecture:
    SupervisorAgent: Orchestrates workflow, distributes tasks, aggregates results
    GeneAgent: Base class for gene-specific analysis agents
    Specialized Agents: BRCA, EGFR, TP53, etc. with domain expertise

Usage:
    >>> from src.agents import SupervisorAgent, BRCAAgent, EGFRAgent
    >>> supervisor = SupervisorAgent()
    >>> supervisor.register_agent(BRCAAgent())
    >>> supervisor.register_agent(EGFRAgent())
    >>> results = supervisor.analyze_cancer_panel(vcf_file)
"""

from .base_agent import BaseAgent, AgentResult, AgentStatus
from .supervisor_agent import SupervisorAgent
from .specialized_agents import BRCAAgent, EGFRAgent, TP53Agent, TMBAgent

__all__ = [
    "BaseAgent",
    "AgentResult",
    "AgentStatus",
    "SupervisorAgent",
    "BRCAAgent",
    "EGFRAgent",
    "TP53Agent",
    "TMBAgent",
]
