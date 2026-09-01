"""Regression tests for removed legacy chat command surfaces."""


def test_legacy_chat_commands_are_not_registered(invoke):
    root = invoke(["--help"])
    admin = invoke(["admin", "--help"])
    chat = invoke(["chat", "--help"])
    chat_escalations = invoke(["admin", "chat-escalations", "--help"])

    assert root.exit_code == 0
    assert admin.exit_code == 0
    assert " chat " not in root.output
    assert " chat-escalations " not in admin.output
    assert chat.exit_code == 2
    assert chat_escalations.exit_code == 2
