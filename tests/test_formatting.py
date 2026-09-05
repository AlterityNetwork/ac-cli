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


def test_print_table_folds_a_value_that_holds_no_space(monkeypatch, capsys, table_column):
    """A tool id, a run id and a UUID hold no space, so the column folds them.

    Rich divides a line on a space. A cell of that shape is one word, so it
    overflows its column and the default `ellipsis` cuts it. The reader then
    cannot copy the value into the next command. No terminal is wide enough to
    close the fault for every id the CLI prints.
    """
    monkeypatch.setenv("COLUMNS", "24")
    tool_id = "mcp.acme_zendesk_production.send_message"

    print_table([{"name": tool_id}], [("name", "Tool ID")])

    output = capsys.readouterr().out
    assert "…" not in output
    assert table_column(output, 0) == tool_id


def test_print_table_folds_the_long_word_only(monkeypatch, capsys):
    """A fold divides one word that is wider than its column. It keeps the rest.

    The cell holds one long id and three short words. The id divides, and no
    short word does. A fix that cut every cell at the column edge would break
    a short word too.
    """
    monkeypatch.setenv("COLUMNS", "24")
    cell = "sent to mcp.acme_zendesk_production.send_message today"

    print_table([{"d": cell}], [("d", "Detail")])

    output = capsys.readouterr().out
    assert "…" not in output
    for word in ("sent", "to", "today"):
        assert word in output


def test_print_table_rules_off_each_row(monkeypatch, capsys, table_column):
    """A rule separates two rows, because a folded row is more than one line.

    Two folded ids make six body lines. The reader needs the rule to see which
    three lines belong to the first row.
    """
    monkeypatch.setenv("COLUMNS", "24")
    first = "0f3a9c21-8b4e-4d7a-9c15-2e6f8a1b3d47"
    second = "7d2b1e60-3f9a-4c8b-a1d2-5b7e9c0f4a13"

    print_table([{"id": first}, {"id": second}], [("id", "Run ID")])

    output = capsys.readouterr().out
    assert "├" in output
    assert table_column(output, 0) == first + second


# -- control bytes in text the CLI did not write --------------------------------
#
# A markup escape does not stop a control byte. A value that holds `\x1b[41m`
# reaches the terminal unchanged under a str, under an escape and under a bare
# Text. The terminal then repaints from an API value, and a `\r` rewrites the
# line the CLI already wrote. Print what the value holds instead: each control
# byte renders as its own escape, so the reader sees it and the terminal does
# not act on it.


def test_as_text_shows_an_escape_byte(monkeypatch):
    import ac_cli.formatting as fmt

    text = fmt.as_text("red \x1b[41m now")
    assert "\x1b" not in text.plain
    assert "\\x1b" in text.plain


def test_as_text_shows_a_carriage_return(monkeypatch):
    """A `\\r` rewrites the line the CLI already wrote, so it is not a newline."""
    import ac_cli.formatting as fmt

    text = fmt.as_text("first\rsecond")
    assert "\r" not in text.plain
    assert "\\x0d" in text.plain


def test_as_text_keeps_a_newline_and_a_tab(monkeypatch):
    """A mail body holds both, and neither repaints the terminal."""
    import ac_cli.formatting as fmt

    assert fmt.as_text("a\nb\tc").plain == "a\nb\tc"


def test_as_text_shows_a_c1_byte(monkeypatch):
    """U+009B is the one-character CSI, so it opens a sequence on its own."""
    import ac_cli.formatting as fmt

    text = fmt.as_text("x\u009b41m")
    assert "\u009b" not in text.plain
    assert "\\x9b" in text.plain


def test_print_table_shows_an_escape_byte_in_a_cell(capsys):
    print_table([{"name": "Acme \x1b[41m Ltd"}], [("name", "Name")])
    output = capsys.readouterr().out
    assert "\x1b[41m" not in output
    assert "\\x1b" in output


def test_print_detail_shows_an_escape_byte_in_a_value(capsys):
    print_detail({"name": "Acme \x1b[41m Ltd"}, [("name", "Name")])
    output = capsys.readouterr().out
    assert "\x1b[41m" not in output
    assert "\\x1b" in output


# -- styled: one markup template, and values that are not markup ----------------
#
# A call site writes the markup and the API writes the values. `styled` keeps
# that boundary: the template parses, and each value prints as it is.


def test_styled_keeps_the_template_markup(monkeypatch):
    import ac_cli.formatting as fmt

    text = fmt.styled("[green]Created:[/green] {}", "Acme")
    assert text.plain == "Created: Acme"
    assert "green" in [span.style for span in text.spans]


def test_styled_renders_a_close_tag_in_a_value(monkeypatch):
    """This is the reported fault: `create` exited 1 and printed nothing."""
    import ac_cli.formatting as fmt

    assert fmt.styled("[green]Created:[/green] {}", "Acme [/beta] Ltd").plain == (
        "Created: Acme [/beta] Ltd"
    )


def test_styled_keeps_a_bracketed_word_in_a_value(monkeypatch):
    import ac_cli.formatting as fmt

    assert fmt.styled("{}", "see the [urgent] note").plain == "see the [urgent] note"


def test_styled_keeps_a_trailing_backslash(monkeypatch):
    import ac_cli.formatting as fmt

    assert fmt.styled("{}", "C:\\share\\").plain == "C:\\share\\"


def test_styled_styles_the_value_the_template_wraps(monkeypatch):
    """A value inside a tag keeps that tag. The old f-string styled it too."""
    import ac_cli.formatting as fmt

    text = fmt.styled("[bold]{}[/bold] after", "Acme")
    bold = [span for span in text.spans if span.style == "bold"]
    assert len(bold) == 1
    assert text.plain[bold[0].start : bold[0].end] == "Acme"


def test_styled_places_each_value_in_order(monkeypatch):
    import ac_cli.formatting as fmt

    assert fmt.styled("{} and {} and {}", 1, 2, 3).plain == "1 and 2 and 3"


def test_styled_highlights_a_value(monkeypatch):
    """A value keeps the colour the console gave it before this change."""
    import ac_cli.formatting as fmt

    text = fmt.styled("id {}", "https://acme.com")
    assert "repr.url" in [span.style for span in text.spans]


def test_styled_shows_a_control_byte_in_a_value(monkeypatch):
    import ac_cli.formatting as fmt

    assert "\x1b" not in fmt.styled("{}", "red \x1b[41m").plain


def test_styled_keeps_a_brace_in_the_template(monkeypatch):
    """The template is not a format string, so a lone brace is a brace."""
    import ac_cli.formatting as fmt

    assert fmt.styled("{ {} }", "x").plain == "{ x }"


def test_styled_refuses_a_value_count_that_does_not_match(monkeypatch):
    """A wrong count drops a value in silence, so raise instead."""
    import pytest

    import ac_cli.formatting as fmt

    with pytest.raises(ValueError):
        fmt.styled("{} and {}", "one")


def test_styled_with_no_value_renders_the_template(monkeypatch):
    """A call site holds markup in a variable. `styled` renders it."""
    import ac_cli.formatting as fmt

    assert fmt.styled("[blue]-> [/blue]").plain == "-> "


def test_no_docstring_in_the_module_holds_a_control_byte():
    """A `\\x1b` in a plain docstring is the escape byte, not four characters.

    The module that strips control bytes must not carry one. `python -c
    "help(...)"` prints every docstring, and an ESC there repaints the
    terminal. Mark a docstring that names an escape as a raw string.
    """
    import inspect

    import ac_cli.formatting as fmt

    for name, member in vars(fmt).items():
        doc = inspect.getdoc(member) if callable(member) else None
        if not doc:
            continue
        found = [hex(ord(c)) for c in doc if ord(c) < 0x20 and c not in "\n\t"]
        assert found == [], f"{name} docstring holds {found}"
