# +--------------------------------------------------------------------------+
# | Admin Intelligence — CLI commands (superadmin only)                      |
# +--------------------------------------------------------------------------+
# | Role                                                                     |
# | Sub-app wiring + shared helpers for the global intel_companies /         |
# | intel_people / intel_signals tables and their intel_sources provenance.  |
# | Mirrors the /admin/intelligence API one-to-one (API<->CLI parity).       |
# | One command module per entity; this file holds only what they share.     |
# +--------------------------------------------------------------------------+

from __future__ import annotations

import typer

from ac_cli.commands.admin import _ADMIN

intelligence_app = typer.Typer(
    help="Intelligence data viewer (companies, people, signals, sources)"
)

companies_app = typer.Typer(help="Intel companies")
people_app = typer.Typer(help="Intel people")
signals_app = typer.Typer(help="Intel signals (append-only)")
sources_app = typer.Typer(help="Intel provenance sources")

_INTEL = f"{_ADMIN}/intelligence"


def _list_params(query, sort, order, limit, offset, **filters) -> dict:
    params: dict = {"limit": limit, "offset": offset}
    if query:
        params["q"] = query
    if sort:
        params["sort"] = sort
    if order:
        params["order"] = order
    # Fold any non-empty field filters (industry, country, ...) into the params.
    for key, value in filters.items():
        if value:
            params[key] = value
    return params


def _write_body(**fields) -> dict:
    """Build a request body from the provided (non-None) option values."""
    return {k: v for k, v in fields.items() if v is not None}


# -- Register sub-command groups from submodules ------------------------------
# Imported last: each submodule imports the app + helpers defined above.

from ac_cli.commands.admin.intelligence import (  # noqa: E402
    companies,  # noqa: F401
    people,  # noqa: F401
    signals,  # noqa: F401
    sources,  # noqa: F401
)

intelligence_app.add_typer(companies_app, name="companies")
intelligence_app.add_typer(people_app, name="people")
intelligence_app.add_typer(signals_app, name="signals")
intelligence_app.add_typer(sources_app, name="sources")
