"""Agent-importable SDK for programmatic access to ac-cli commands."""

from ac_cli.sdk.registry import build_registry, get_command_schema

__all__ = ["build_registry", "get_command_schema"]
