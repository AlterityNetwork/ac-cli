"""Tests for formatting helpers."""

import json

from ac_cli.formatting import print_detail, print_json, print_table


def test_print_table_renders_rows(capsys):
    data = [
        {"name": "Acme", "industry": "SaaS"},
        {"name": "Globex", "industry": "Manufacturing"},
    ]
    print_table(data, [("name", "Name"), ("industry", "Industry")], title="Companies")
    output = capsys.readouterr().out
    assert "Acme" in output
    assert "Globex" in output
    assert "Companies" in output


def test_print_table_empty(capsys):
    print_table([], [("name", "Name")], title="Empty")
    output = capsys.readouterr().out
    assert "Empty" in output


def test_print_detail_renders_fields(capsys):
    data = {"id": "abc", "name": "Acme", "website": "https://acme.com"}
    print_detail(data, [("id", "ID"), ("name", "Name"), ("website", "Website")])
    output = capsys.readouterr().out
    assert "abc" in output
    assert "Acme" in output
    assert "https://acme.com" in output


def test_print_json_outputs_valid_json(capsys):
    data = {"items": [1, 2, 3], "total": 3}
    print_json(data)
    output = capsys.readouterr().out
    parsed = json.loads(output)
    assert parsed == data


def test_print_detail_missing_key(capsys):
    data = {"name": "Acme"}
    print_detail(data, [("name", "Name"), ("missing", "Missing Field")])
    output = capsys.readouterr().out
    assert "Acme" in output
    assert "Missing Field" in output


# -- rich markup in text the CLI did not write ---------------------------------
#
# Every cell, title and value passes through a markup-enabled console. A close
# tag raises MarkupError, and the command then exits 1 with no output. An open
# tag renders as nothing, so the reader reads a value the row does not hold.


def test_print_table_renders_a_close_tag_in_a_cell(capsys):
    """A close tag raised MarkupError, and the whole page printed nothing."""
    print_table([{"name": "Acme [/beta] Ltd"}], [("name", "Name")])
    assert "[/beta]" in capsys.readouterr().out


def test_print_table_keeps_a_bracketed_word_in_a_cell(capsys):
    """An open tag dropped the bracketed text and the reader saw "Acme  Ltd"."""
    print_table([{"name": "Acme [formerly Beta] Ltd"}], [("name", "Name")])
    assert "[formerly Beta]" in capsys.readouterr().out


def test_print_table_renders_a_close_tag_in_the_title(capsys):
    """One title interpolates a command argument, so it takes the same escape."""
    print_table([], [("name", "Name")], title="Configs for acme[/x]")
    assert "[/x]" in capsys.readouterr().out


def test_print_table_renders_a_non_string_cell(capsys):
    """A cell can hold a list of tags, and escape() rejects a non-string."""
    print_table([{"tags": ["a [/x]", "b"]}], [("tags", "Tags")])
    assert "[/x]" in capsys.readouterr().out


def test_print_detail_renders_a_close_tag_in_a_value(capsys):
    print_detail({"name": "Acme [/beta] Ltd"}, [("name", "Name")])
    assert "[/beta]" in capsys.readouterr().out


def test_print_detail_keeps_a_bracketed_word_in_a_value(capsys):
    print_detail({"name": "Acme [formerly Beta] Ltd"}, [("name", "Name")])
    assert "[formerly Beta]" in capsys.readouterr().out


def test_print_detail_renders_a_non_string_value(capsys):
    print_detail({"tags": ["a [/x]"]}, [("tags", "Tags")])
    assert "[/x]" in capsys.readouterr().out
