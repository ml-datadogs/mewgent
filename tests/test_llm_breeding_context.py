"""Breeding context shipped to the LLM advisor."""

from src.llm import advisor


def test_load_breeding_context_includes_strategy_marker() -> None:
    text = advisor._load_breeding_context()
    assert "MewgentBreedingStrategyContext" in text
    assert "Strategy A" in text and "Strategy B" in text
