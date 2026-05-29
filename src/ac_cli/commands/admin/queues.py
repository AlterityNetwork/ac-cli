"""Admin queue management commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import JSON_OPTION, _api_request, set_json_mode
from ac_cli.commands.admin import _ADMIN
from ac_cli.formatting import print_json

queues_app = typer.Typer(help="Queue management")


@queues_app.command("health")
def queues_health(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """Check queue health status."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_ADMIN}/queues/health")

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(data)


@queues_app.command("stats")
def queues_stats(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """Show queue statistics."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_ADMIN}/queues/stats")

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(data)


@queues_app.command("queue-stats")
def queues_queue_stats(
    ctx: typer.Context,
    queue_name: str = typer.Argument(..., help="Queue name"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Show statistics for a specific queue."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_ADMIN}/queues/{queue_name}/stats")

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(data)


@queues_app.command("metrics")
def queues_metrics(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """Show queue metrics."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_ADMIN}/queues/metrics")

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(data)


@queues_app.command("send-to-sentry")
def queues_send_to_sentry() -> None:
    """Send queue metrics to Sentry."""
    _api_request("post", f"{_ADMIN}/queues/metrics/send-to-sentry")

    rprint("[green]Metrics sent to Sentry[/green]")


@queues_app.command("job-performance")
def queues_job_performance(
    ctx: typer.Context,
    job_id: str = typer.Argument(..., help="Job ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Show performance metrics for a specific job."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_ADMIN}/queues/jobs/{job_id}/performance")

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(data)
