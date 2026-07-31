"""Tests for ask_user tool — human-in-the-loop mid-execution."""
from __future__ import annotations

import json
from unittest.mock import patch
import pytest

from agents_janus.tools.ask_user_tool import ask_user


class TestAskUser:
    def test_free_text(self, monkeypatch):
        """User types a free-form answer."""
        monkeypatch.setattr("builtins.input", lambda _: "my custom answer")
        result = ask_user(question="What is your preference?")
        data = json.loads(result)
        assert data["question"] == "What is your preference?"
        assert data["answer"] == "my custom answer"
        assert data["options"] is None

    def test_multi_choice_by_number(self, monkeypatch):
        """User picks by number."""
        monkeypatch.setattr("builtins.input", lambda _: "2")
        result = ask_user(
            question="Which approach?",
            options=["Approach A", "Approach B", "Approach C"],
        )
        data = json.loads(result)
        assert data["answer"] == "Approach B"

    def test_multi_choice_by_text(self, monkeypatch):
        """User types the option text directly."""
        monkeypatch.setattr("builtins.input", lambda _: "Approach C")
        result = ask_user(
            question="Which approach?",
            options=["Approach A", "Approach B", "Approach C"],
        )
        data = json.loads(result)
        assert data["answer"] == "Approach C"

    def test_default_used_on_empty(self, monkeypatch):
        """Default is used when user presses Enter."""
        monkeypatch.setattr("builtins.input", lambda _: "")
        result = ask_user(
            question="Confirm?",
            options=["yes", "no"],
            default="yes",
        )
        data = json.loads(result)
        assert data["answer"] == "yes"

    def test_eof_uses_default(self, monkeypatch):
        """EOF (Ctrl+D) uses the default."""
        def raise_eof(_):
            raise EOFError
        monkeypatch.setattr("builtins.input", raise_eof)
        result = ask_user(question="Q?", default="fallback")
        data = json.loads(result)
        assert data["answer"] == "fallback"

    def test_keyboard_interrupt_uses_default(self, monkeypatch):
        """KeyboardInterrupt (Ctrl+C) uses the default."""
        def raise_kbi(_):
            raise KeyboardInterrupt
        monkeypatch.setattr("builtins.input", raise_kbi)
        result = ask_user(question="Q?", default="abort")
        data = json.loads(result)
        assert data["answer"] == "abort"

    def test_custom_answer_in_multi_choice(self, monkeypatch):
        """User types something not in options — returned as-is."""
        monkeypatch.setattr("builtins.input", lambda _: "my own idea")
        result = ask_user(
            question="Which?",
            options=["A", "B"],
        )
        data = json.loads(result)
        assert data["answer"] == "my own idea"

    def test_out_of_range_number_falls_back_to_text(self, monkeypatch):
        """Out-of-range number → returned as text (LLM can detect it's invalid)."""
        monkeypatch.setattr("builtins.input", lambda _: "99")
        result = ask_user(
            question="Which?",
            options=["A", "B"],
        )
        data = json.loads(result)
        assert data["answer"] == "99"  # raw text preserved