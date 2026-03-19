"""Tests for file image commands."""

import json


SAMPLE_UPLOAD_RESPONSE = {
    "key": "org-456/avatars/photo.png",
    "public_url": "https://cdn.example.com/org-456/avatars/photo.png",
    "filename": "photo.png",
    "content_type": "image/png",
    "size": 1024,
    "category": "avatars",
}

SAMPLE_DELETE_RESPONSE = {
    "key": "org-456/avatars/photo.png",
    "deleted": True,
}


def _create_image(tmp_path, name="photo.png", size=1024):
    """Create a temporary image file for testing."""
    f = tmp_path / name
    f.write_bytes(b"\x89PNG" + b"\x00" * (size - 4))
    return f


def test_images_upload(invoke, mock_api, tmp_path):
    img = _create_image(tmp_path)
    mock_api.post("/api/v1/files/images/upload").respond(200, json=SAMPLE_UPLOAD_RESPONSE)
    result = invoke(["files", "images", "upload", str(img), "--category", "avatars"])
    assert result.exit_code == 0
    assert "photo.png" in result.output


def test_images_upload_json(invoke, mock_api, tmp_path):
    img = _create_image(tmp_path)
    mock_api.post("/api/v1/files/images/upload").respond(200, json=SAMPLE_UPLOAD_RESPONSE)
    result = invoke(["files", "--json", "images", "upload", str(img), "--category", "avatars"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["key"] == "org-456/avatars/photo.png"
    assert parsed["category"] == "avatars"


def test_images_upload_file_not_found(invoke, mock_api):
    result = invoke(["files", "images", "upload", "/nonexistent/photo.png", "--category", "avatars"])
    assert result.exit_code == 1
    assert "File not found" in result.output


def test_images_upload_unsupported_extension(invoke, mock_api, tmp_path):
    f = tmp_path / "doc.txt"
    f.write_text("not an image")
    result = invoke(["files", "images", "upload", str(f), "--category", "avatars"])
    assert result.exit_code == 1
    assert "Unsupported file type" in result.output


def test_images_upload_too_large(invoke, mock_api, tmp_path):
    img = _create_image(tmp_path, size=1_048_577)  # 1 byte over limit
    result = invoke(["files", "images", "upload", str(img), "--category", "avatars"])
    assert result.exit_code == 1
    assert "too large" in result.output


def test_images_upload_invalid_category(invoke, mock_api, tmp_path):
    img = _create_image(tmp_path)
    result = invoke(["files", "images", "upload", str(img), "--category", "bogus"])
    assert result.exit_code != 0


def test_images_upload_api_error(invoke, mock_api, tmp_path):
    img = _create_image(tmp_path)
    mock_api.post("/api/v1/files/images/upload").respond(400, json={"detail": "Invalid image"})
    result = invoke(["files", "images", "upload", str(img), "--category", "avatars"])
    assert result.exit_code == 1
    assert "Invalid image" in result.output


def test_images_upload_all_categories(invoke, mock_api, tmp_path):
    categories = [
        "avatars",
        "organization_logos",
        "crm_company_logos",
        "general_images",
        "apps_assets",
    ]
    for cat in categories:
        img = _create_image(tmp_path, name=f"{cat}.png")
        resp = {**SAMPLE_UPLOAD_RESPONSE, "category": cat}
        mock_api.post("/api/v1/files/images/upload").respond(200, json=resp)
        result = invoke(["files", "images", "upload", str(img), "--category", cat])
        assert result.exit_code == 0, f"Failed for category {cat}"


def test_images_upload_jpeg(invoke, mock_api, tmp_path):
    img = _create_image(tmp_path, name="photo.jpg")
    resp = {**SAMPLE_UPLOAD_RESPONSE, "filename": "photo.jpg", "content_type": "image/jpeg"}
    mock_api.post("/api/v1/files/images/upload").respond(200, json=resp)
    result = invoke(["files", "images", "upload", str(img), "--category", "avatars"])
    assert result.exit_code == 0
    assert "photo.jpg" in result.output


def test_images_delete_with_yes(invoke, mock_api):
    mock_api.delete("/api/v1/files/images/org-456/avatars/photo.png").respond(
        200, json=SAMPLE_DELETE_RESPONSE,
    )
    result = invoke(["files", "images", "delete", "org-456/avatars/photo.png", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_images_delete_json(invoke, mock_api):
    mock_api.delete("/api/v1/files/images/org-456/avatars/photo.png").respond(
        200, json=SAMPLE_DELETE_RESPONSE,
    )
    result = invoke(["files", "--json", "images", "delete", "org-456/avatars/photo.png", "--yes"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["deleted"] is True


def test_images_delete_aborted(invoke, mock_api):
    result = invoke(["files", "images", "delete", "org-456/avatars/photo.png"], input="n\n")
    assert result.exit_code == 1


def test_images_delete_not_found(invoke, mock_api):
    mock_api.delete("/api/v1/files/images/org-456/avatars/photo.png").respond(
        404, json={"detail": "Image not found"},
    )
    result = invoke(["files", "images", "delete", "org-456/avatars/photo.png", "--yes"])
    assert result.exit_code == 1
    assert "Image not found" in result.output


def test_images_delete_forbidden(invoke, mock_api):
    mock_api.delete("/api/v1/files/images/org-456/avatars/photo.png").respond(
        403, json={"detail": "Forbidden"},
    )
    result = invoke(["files", "images", "delete", "org-456/avatars/photo.png", "--yes"])
    assert result.exit_code == 1
    assert "Forbidden" in result.output
