"""Admin queue management commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import _api_request
from ac_cli.commands.admin import _ADMIN
from ac_cli.formatting import print_json, print_table

queues_app = typer.Typer(help="Queue management")


@queues_app.command("health")
def queues_health(
    ctx: typer.Context,
) -> None:
    """Check queue health status."""
    resp = _api_request("get", f"{_ADMIN}/queues/health")

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(data)


@queues_app.command("stats")
def queues_stats(
    ctx: typer.Context,
) -> None:
    """Show queue statistics."""
    resp = _api_request("get", f"{_ADMIN}/queues/stats")

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(data)


@queues_app.command("queue-stats")
def queues_queue_stats(
    ctx: typer.Context,
    queue_name: str = typer.Argument(..., help="Queue name"),
) -> None:
    """Show statistics for a specific queue."""
    resp = _api_request("get", f"{_ADMIN}/queues/{queue_name}/stats")

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(data)


@queues_app.command("metrics")
def queues_metrics(
    ctx: typer.Context,
) -> None:
    """Show queue metrics."""
    resp = _api_request("get", f"{_ADMIN}/queues/metrics")

    data = resp.json()
    if ctx.obj["json"]:
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
) -> None:
    """Show performance metrics for a specific job."""
    resp = _api_request("get", f"{_ADMIN}/queues/jobs/{job_id}/performance")

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(data)


@queues_app.command("failed")
def queues_failed(
    ctx: typer.Context,
    queue_name: str = typer.Argument(..., help="Queue name"),
    limit: int = typer.Option(50, help="Max results"),
) -> None:
    """List failed jobs in a queue."""
    resp = _api_request("get", f"{_ADMIN}/queues/{queue_name}/failed", params={"limit": limit})

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("data", [])
    print_table(
        items,
        [
            ("job_id", "Job ID"),
            ("error", "Error"),
            ("failed_at", "Failed At"),
        ],
        title=f"Failed Jobs ({len(items)})",
    )


@queues_app.command("retry-all")
def queues_retry_all(
    queue_name: str = typer.Argument(..., help="Queue name"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Retry all failed jobs in a queue."""
    if not yes:
        typer.confirm(f"Retry all failed jobs in queue {queue_name}?", abort=True)

    _api_request("post", f"{_ADMIN}/queues/{queue_name}/failed/retry")

    rprint(f"[green]Retrying all failed jobs in queue {queue_name}[/green]")


@queues_app.command("retry-job")
def queues_retry_job(
    job_id: str = typer.Argument(..., help="Job ID"),
) -> None:
    """Retry a specific failed job."""
    _api_request("post", f"{_ADMIN}/queues/jobs/{job_id}/retry")

    rprint(f"[green]Retrying job {job_id}[/green]")


@queues_app.command("clear-failed")
def queues_clear_failed(
    queue_name: str = typer.Argument(..., help="Queue name"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Clear all failed jobs in a queue."""
    if not yes:
        typer.confirm(f"Clear all failed jobs in queue {queue_name}?", abort=True)

    _api_request("delete", f"{_ADMIN}/queues/{queue_name}/failed")

    rprint(f"[green]Cleared failed jobs in queue {queue_name}[/green]")
