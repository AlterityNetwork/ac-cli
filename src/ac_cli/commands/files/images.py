"""Image file commands: upload, delete."""

from __future__ import annotations

import mimetypes
from enum import Enum
from pathlib import Path

import typer
from rich import print as rprint

from ac_cli.commands._helpers import should_skip_confirm

from ac_cli.commands._helpers import _api_request
from ac_cli.commands.files import _FILES
from ac_cli.formatting import print_detail, print_json

images_app = typer.Typer(help="Image file operations")

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".avif"}
MAX_SIZE_BYTES = 1_048_576  # 1 MB


class ImageCategory(str, Enum):
    avatars = "avatars"
    organization_logos = "organization_logos"
    crm_company_logos = "crm_company_logos"
    general_images = "general_images"
    apps_assets = "apps_assets"


@images_app.command("upload")
def images_upload(
    ctx: typer.Context,
    file_path: Path = typer.Argument(..., help="Path to the image file"),
    category: ImageCategory = typer.Option(..., "--category", "-c", help="Image category"),
) -> None:
    """Upload an image file."""
    if not file_path.exists():
        rprint(f"[red]Error:[/red] File not found: {file_path}")
        raise typer.Exit(code=1)

    suffix = file_path.suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        rprint(f"[red]Error:[/red] Unsupported file type: {suffix}")
        raise typer.Exit(code=1)

    size = file_path.stat().st_size
    if size > MAX_SIZE_BYTES:
        rprint(f"[red]Error:[/red] File too large ({size} bytes, max {MAX_SIZE_BYTES})")
        raise typer.Exit(code=1)

    content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"

    with open(file_path, "rb") as f:
        resp = _api_request(
            "post",
            f"{_FILES}/images/upload",
            files={"file": (file_path.name, f, content_type)},
            data={"category": category.value},
        )

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        print_detail(data, [
            ("key", "Key"),
            ("public_url", "URL"),
            ("filename", "Filename"),
            ("content_type", "Content-Type"),
            ("size", "Size"),
            ("category", "Category"),
        ])


@images_app.command("delete")
def images_delete(
    ctx: typer.Context,
    key: str = typer.Argument(..., help="R2 object key of the image"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete an image by its R2 object key."""
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete image {key}?", abort=True)

    resp = _api_request("delete", f"{_FILES}/images/{key}")

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(f"[green]Deleted image:[/green] {key}")
