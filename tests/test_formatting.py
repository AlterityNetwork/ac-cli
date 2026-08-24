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

    title_line = console.file.getvalue().splitlines()[0]
    assert "Companies" in title_line
    assert title_line.startswith("\x1b[3m") and title_line.endswith("\x1b[0m")


def test_print_detail_keeps_the_value_highlighting(monkeypatch):
    """The console highlights a str but not a Text, so the helper highlights."""
    import ac_cli.formatting as fmt

    console = _coloured_console()
    monkeypatch.setattr(fmt, "console", console)
    fmt.print_detail({"n": 250, "url": "https://acme.com"}, [("n", "N"), ("url", "URL")])

    out = console.file.getvalue()
    assert "\x1b[1;36m250\x1b[0m" in out
    assert "\x1b[4;94mhttps://acme.com\x1b[0m" in out


def test_as_text_keeps_markup_literal_and_keeps_the_highlighting(monkeypatch):
    """as_text carries both rules: no markup parsing, and the old colours."""
    import ac_cli.formatting as fmt

    console = _coloured_console()
    monkeypatch.setattr(fmt, "console", console)
    source = "id 250 is [/beta] at https://acme.com"
    # The highlighter colours each bracket on its own, so the styled stream
    # holds no contiguous "[/beta]". Read the literal text off `plain`.
    assert fmt.as_text(source).plain == source

    console.print(fmt.as_text(source))
    out = console.file.getvalue()
    assert "\x1b[1;36m250\x1b[0m" in out
    assert "\x1b[4;94mhttps://acme.com\x1b[0m" in out


def test_as_text_keeps_a_trailing_backslash(monkeypatch):
    import ac_cli.formatting as fmt

    console = _coloured_console()
    monkeypatch.setattr(fmt, "console", console)
    console.print(fmt.as_text("C:\\share\\"))

    assert "C:\\share\\\\" not in console.file.getvalue()
