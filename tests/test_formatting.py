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


# -- a null field ---------------------------------------------------------------
#
# A JSON null and an absent key say the same thing: the record carries no value
# there. One record read two ways is one record, so a table and a detail view
# must answer alike. `str(None)` printed `None`, which reads as a value.


def test_print_table_renders_a_null_cell_blank(capsys):
    print_table([{"name": "Acme", "ended_at": None}], [("name", "Name"), ("ended_at", "Ended")])
    output = capsys.readouterr().out
    assert "Acme" in output
    assert "None" not in output


def test_print_detail_renders_a_null_field_blank(capsys):
    print_detail({"name": "Acme", "ended_at": None}, [("name", "Name"), ("ended_at", "Ended")])
    output = capsys.readouterr().out
    assert "Acme" in output
    assert "None" not in output


def test_a_falsy_value_is_not_a_null(capsys):
    """The test is `is None`, so a zero and a False keep their value.

    A truth test would blank both, and `Children: 0` is a fact a reader needs.
    """
    print_detail(
        {"child_count": 0, "cancelled": False},
        [("child_count", "Children"), ("cancelled", "Cancelled")],
    )
    output = capsys.readouterr().out
    assert "0" in output
    assert "False" in output


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


def test_print_table_keeps_a_trailing_backslash(capsys):
    """rich.markup.escape appends a second backslash, and nothing removes it."""
    print_table([{"path": "C:\\share\\"}], [("path", "Path")])
    out = capsys.readouterr().out
    assert "C:\\share\\" in out
    assert "C:\\share\\\\" not in out


def test_print_detail_keeps_a_trailing_backslash(capsys):
    print_detail({"path": "C:\\share\\"}, [("path", "Path")])
    assert capsys.readouterr().out.rstrip("\n").endswith("C:\\share\\")


def _coloured_console():
    """A console that emits styles, which capsys and a pipe do not."""
    import io

    from rich.console import Console

    return Console(file=io.StringIO(), width=60, force_terminal=True, color_system="truecolor")


def test_print_table_keeps_the_title_style(monkeypatch):
    """Table styles a str title only, so a Text title must name the style."""
    import ac_cli.formatting as fmt

    console = _coloured_console()
    monkeypatch.setattr(fmt, "console", console)
    # The title wraps to the table width, so the row must be wider than it.
    fmt.print_table([{"name": "Acme Corporation Ltd"}], [("name", "Name")], title="Companies")

    import re

    from rich.default_styles import DEFAULT_STYLES

    title_line = console.file.getvalue().splitlines()[0]
    plain = re.sub(r"\x1b\[[0-9;]*m", "", title_line)
    assert "Companies" in plain
    assert title_line == DEFAULT_STYLES["table.title"].render(plain)


def test_print_detail_keeps_the_value_highlighting(monkeypatch):
    """The console highlights a str but not a Text, so the helper highlights."""
    import ac_cli.formatting as fmt

    console = _coloured_console()
    monkeypatch.setattr(fmt, "console", console)
    fmt.print_detail({"n": 250, "url": "https://acme.com"}, [("n", "N"), ("url", "URL")])

    from rich.default_styles import DEFAULT_STYLES

    out = console.file.getvalue()
    assert DEFAULT_STYLES["repr.number"].render("250") in out
    assert DEFAULT_STYLES["repr.url"].render("https://acme.com") in out


def test_as_text_keeps_markup_literal_and_keeps_the_highlighting(monkeypatch):
    """as_text carries both rules: no markup parsing, and the old colours."""
    import ac_cli.formatting as fmt

    console = _coloured_console()
    monkeypatch.setattr(fmt, "console", console)
    source = "id 250 is [/beta] at https://acme.com"
    # The highlighter colours each bracket on its own, so the styled stream
    # holds no contiguous "[/beta]". Read the literal text off `plain`.
    assert fmt.as_text(source).plain == source

    # Name the styles, not their bytes. A rich release may repaint a theme.
    styles = [span.style for span in fmt.as_text(source).spans]
    assert "repr.number" in styles
    assert "repr.url" in styles


def test_as_text_keeps_a_trailing_backslash(monkeypatch):
    import ac_cli.formatting as fmt

    console = _coloured_console()
    monkeypatch.setattr(fmt, "console", console)
    console.print(fmt.as_text("C:\\share\\"))

    out = console.file.getvalue()
    assert "C:\\share\\" in out
    assert "C:\\share\\\\" not in out
