"""CRM communications commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import JSON_OPTION, set_json_mode, should_skip_confirm
from ac_cli.commands.crm import _CRM, _api_request, _build_body
from ac_cli.formatting import print_detail, print_json, print_table

communications_app = typer.Typer(help="Communications / email operations")


@communications_app.command("list")
def communications_list(
    ctx: typer.Context,
    company_id: str | None = typer.Option(None, "--company-id", help="Filter by company"),
    contact_id: str | None = typer.Option(None, "--contact-id", help="Filter by contact"),
    deal_id: str | None = typer.Option(None, "--deal-id", help="Filter by deal"),
    comm_type: str | None = typer.Option(None, "--type", help="Filter by type (email, call, etc.)"),
    direction: str | None = typer.Option(None, help="Filter by direction (inbound, outbound)"),
    status: str | None = typer.Option(None, help="Filter by status"),
    sentiment: str | None = typer.Option(
        None,
        "--sentiment",
        help="Filter by sentiment: positive, neutral, or negative.",
    ),
    since: str | None = typer.Option(
        None,
        "--since",
        help="Include only communications on/after this ISO date (YYYY-MM-DD).",
    ),
    until: str | None = typer.Option(
        None,
        "--until",
        help="Include only communications on/before this ISO date (YYYY-MM-DD).",
    ),
    limit: int = typer.Option(20, help="Max results"),
    offset: int = typer.Option(0, help="Offset"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List communications."""
    set_json_mode(json_output)
    params: dict = {"limit": limit, "offset": offset}
    if company_id:
        params["company_id"] = company_id
    if contact_id:
        params["contact_id"] = contact_id
    if deal_id:
        params["deal_id"] = deal_id
    if comm_type:
        params["type"] = comm_type
    if direction:
        params["direction"] = direction
    if status:
        params["status"] = status
    if sentiment:
        params["sentiment"] = sentiment
    if since:
        params["since"] = since
    if until:
        params["until"] = until

    resp = _api_request("get", f"{_CRM}/communications", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("data", [])
    print_table(
        items,
        [
            ("direction", "Dir"),
            ("from_name", "From"),
            ("subject", "Subject"),
            ("status", "Status"),
            ("communication_date", "Date"),
            ("thread_id", "Thread"),
        ],
        title=f"Communications ({len(items)})",
    )


@communications_app.command("get")
def communications_get(
    ctx: typer.Context,
    communication_id: str = typer.Argument(..., help="Communication ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get a single communication by ID."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_CRM}/communications/{communication_id}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(data, [
        ("id", "ID"),
        ("direction", "Direction"),
        ("from_name", "From"),
        ("from_email", "From Email"),
        ("to_emails", "To"),
        ("subject", "Subject"),
        ("status", "Status"),
        ("sentiment", "Sentiment"),
        ("communication_date", "Date"),
        ("thread_id", "Thread"),
        ("company_id", "Company ID"),
        ("contact_id", "Contact ID"),
    ])
    rprint(f"\n[bold]Content[/bold]\n{data.get('content', '')}")


@communications_app.command("thread")
def communications_thread(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Show all messages in a thread."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_CRM}/communications/thread/{thread_id}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("data", [])
    if not items:
        rprint("[dim]No messages in this thread.[/dim]")
        return

    rprint(f"\n[bold]Thread: {items[0].get('subject', thread_id)}[/bold]")
    rprint(f"[dim]{'─' * 60}[/dim]")

    for msg in items:
        direction = msg.get("direction", "?")
        arrow = "[blue]→[/blue]" if direction == "outbound" else "[green]←[/green]"
        from_name = msg.get("from_name", msg.get("from_email", "?"))
        date = (msg.get("communication_date") or "")[:16].replace("T", " ")
        sentiment = msg.get("sentiment")
        sentiment_tag = f" [dim]({sentiment})[/dim]" if sentiment else ""

        rprint(f"\n{arrow} [bold]{from_name}[/bold]  {date}{sentiment_tag}")
        rprint(f"[dim]  To: {', '.join(msg.get('to_emails', []))}[/dim]")
        rprint(f"\n{msg.get('content', '')}")
        rprint(f"[dim]{'─' * 60}[/dim]")


@communications_app.command("unread")
def communications_unread(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """Show unread thread counts."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_CRM}/communications/unread-counts")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    counts = data.get("thread_counts", {})
    if not counts:
        rprint("[green]No unread threads![/green]")
        return

    total = sum(counts.values())
    rprint(f"\n[bold]Unread Messages ({total} total)[/bold]\n")
    for thread_id, count in counts.items():
        rprint(f"  {thread_id}: [yellow]{count}[/yellow] unread")


@communications_app.command("mark-read")
def communications_mark_read(
    thread_id: str = typer.Argument(..., help="Thread ID"),
) -> None:
    """Mark a thread as read."""
    _api_request("post", f"{_CRM}/communications/thread/{thread_id}/mark-read")

    rprint(f"[green]Marked thread {thread_id} as read[/green]")


@communications_app.command("delete")
def communications_delete(
    communication_id: str = typer.Argument(..., help="Communication ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a communication."""
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete communication {communication_id}?", abort=True)

    _api_request("delete", f"{_CRM}/communications/{communication_id}")

    rprint(f"[green]Deleted communication {communication_id}[/green]")


@communications_app.command("delete-thread")
def communications_delete_thread(
    thread_id: str = typer.Argument(..., help="Thread ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete an entire thread."""
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete thread {thread_id} and all its messages?", abort=True)

    _api_request("delete", f"{_CRM}/communications/thread/{thread_id}")

    rprint(f"[green]Deleted thread {thread_id}[/green]")


@communications_app.command("update")
def communications_update(
    ctx: typer.Context,
    communication_id: str = typer.Argument(..., help="Communication ID"),
    subject: str | None = typer.Option(None, help="Subject"),
    content: str | None = typer.Option(None, help="Content"),
    status: str | None = typer.Option(None, help="Status"),
    tags: str | None = typer.Option(None, help="Comma-separated tags"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update a communication."""
    set_json_mode(json_output)
    body = _build_body(subject=subject, content=content, status=status, tags=tags)

    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("patch", f"{_CRM}/communications/{communication_id}", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Updated communication {communication_id}[/green]")


@communications_app.command("archive")
def communications_archive(
    ctx: typer.Context,
    thread_id: str | None = typer.Option(None, "--thread-id", help="Thread ID to archive"),
    comm_id: str | None = typer.Option(None, "--comm-id", help="Communication ID to archive"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Archive a communication or thread."""
    set_json_mode(json_output)
    if not thread_id and not comm_id:
        rprint("[red]Must specify --thread-id or --comm-id[/red]")
        raise typer.Exit(code=1)

    body = _build_body(thread_id=thread_id, communication_id=comm_id)
    resp = _api_request("post", f"{_CRM}/communications/archive", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        target = thread_id or comm_id
        rprint(f"[green]Archived {target}[/green]")


@communications_app.command("unarchive")
def communications_unarchive(
    ctx: typer.Context,
    thread_id: str | None = typer.Option(None, "--thread-id", help="Thread ID to unarchive"),
    comm_id: str | None = typer.Option(None, "--comm-id", help="Communication ID to unarchive"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Unarchive a communication or thread."""
    set_json_mode(json_output)
    if not thread_id and not comm_id:
        rprint("[red]Must specify --thread-id or --comm-id[/red]")
        raise typer.Exit(code=1)

    body = _build_body(thread_id=thread_id, communication_id=comm_id)
    resp = _api_request("post", f"{_CRM}/communications/unarchive", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        target = thread_id or comm_id
        rprint(f"[green]Unarchived {target}[/green]")


@communications_app.command("contact-by-email")
def communications_contact_by_email(
    ctx: typer.Context,
    email: str = typer.Argument(..., help="Email address to look up"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Look up a contact by email address."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_CRM}/communications/contact-by-email", params={"email": email})

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(data, [
        ("id", "ID"),
        ("full_name", "Name"),
        ("email", "Email"),
        ("job_title", "Job Title"),
        ("company_id", "Company ID"),
    ])


@communications_app.command("resolve-contact")
def communications_resolve_contact(
    ctx: typer.Context,
    email: str = typer.Argument(..., help="Email address to resolve"),
    name: str | None = typer.Option(None, help="Contact name"),
    job_title: str | None = typer.Option(None, "--job-title", help="Job title"),
    company_id: str | None = typer.Option(None, "--company-id", help="Company ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Resolve or create a contact from an email address."""
    set_json_mode(json_output)
    body = _build_body(email=email, name=name, job_title=job_title, company_id=company_id)
    resp = _api_request("post", f"{_CRM}/communications/resolve-contact", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Resolved contact:[/green] {data.get('full_name', data.get('email', email))} ({data.get('id', '')})")


@communications_app.command("draft-email")
def communications_draft_email(
    ctx: typer.Context,
    contact_id: str = typer.Option(..., "--contact-id", help="Contact ID"),
    subject: str = typer.Option(..., help="Email subject"),
    content: str = typer.Option(..., help="Email content"),
    company_id: str | None = typer.Option(None, "--company-id", help="Company ID"),
    deal_id: str | None = typer.Option(None, "--deal-id", help="Deal ID"),
    to_emails: str | None = typer.Option(None, "--to-emails", help="Comma-separated recipient emails"),
    from_email: str | None = typer.Option(None, "--from-email", help="Sender email"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create an email draft."""
    set_json_mode(json_output)
    body = _build_body(
        contact_id=contact_id, subject=subject, content=content,
        company_id=company_id, deal_id=deal_id, from_email=from_email,
    )
    if to_emails:
        body["to_emails"] = [e.strip() for e in to_emails.split(",")]

    resp = _api_request("post", f"{_CRM}/communications/draft-email", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Draft created:[/green] {data.get('subject', '')} ({data.get('id', '')})")


@communications_app.command("generate-draft")
def communications_generate_draft(
    ctx: typer.Context,
    mode: str = typer.Option(..., help="compose or reply"),
    recipient_name: str = typer.Option(..., "--recipient-name", help="Recipient name"),
    recipient_email: str | None = typer.Option(None, "--recipient-email", help="Recipient email"),
    recipient_title: str | None = typer.Option(None, "--recipient-title", help="Recipient job title"),
    company_name: str | None = typer.Option(None, "--company-name", help="Company name"),
    sender_name: str | None = typer.Option(None, "--sender-name", help="Sender name"),
    sender_signature: str | None = typer.Option(None, "--sender-signature", help="Sender email signature"),
    original_subject: str | None = typer.Option(None, "--original-subject", help="Original subject (for replies)"),
    user_draft_subject: str | None = typer.Option(None, "--user-draft-subject", help="Draft subject to refine"),
    user_draft_body: str | None = typer.Option(None, "--user-draft-body", help="Draft body to refine"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Generate an AI-drafted email."""
    set_json_mode(json_output)
    body = _build_body(
        mode=mode, recipient_name=recipient_name, recipient_email=recipient_email,
        recipient_title=recipient_title, company_name=company_name,
        sender_name=sender_name, sender_signature=sender_signature,
        original_subject=original_subject,
        user_draft_subject=user_draft_subject, user_draft_body=user_draft_body,
    )

    resp = _api_request("post", f"{_CRM}/communications/generate-draft", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[bold]Generated Draft[/bold]\n")
        rprint(f"[bold]Subject:[/bold] {data.get('subject', '')}")
        rprint(f"\n{data.get('body', data.get('content', ''))}")


@communications_app.command("unread-thread-ids")
def communications_unread_thread_ids(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """Get list of unread thread IDs."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_CRM}/communications/unread-thread-ids")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    thread_ids = data if isinstance(data, list) else data.get("thread_ids", [])
    if not thread_ids:
        rprint("[green]No unread threads![/green]")
        return

    rprint(f"\n[bold]Unread Threads ({len(thread_ids)})[/bold]\n")
    for tid in thread_ids:
        rprint(f"  {tid}")
