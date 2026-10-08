"""Validated, atomic JPEG evidence storage, preserving bytes across retries."""
import hashlib
import io
import os
from pathlib import Path
import tempfile
import warnings

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError


def store_scan_image(scan_id, upload, directory, max_bytes):
    data = upload.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(413, "Scan photo exceeds the upload size limit.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if image.format != "JPEG" or image.width * image.height > 25_000_000:
                    raise ValueError("A JPEG of at most 25 megapixels is required")
                image.load()
    except (UnidentifiedImageError, OSError, ValueError,
            Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(422, "Upload must be a complete JPEG of at most 25 megapixels.")

    digest = hashlib.sha256(data).hexdigest()
    target = Path(directory) / f"{scan_id}.jpg"
    temporary = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        # The endpoint holds the scan row lock throughout this operation.
        if target.exists():
            with target.open("rb") as stream:
                existing_digest = hashlib.file_digest(stream, "sha256").hexdigest()
            if existing_digest != digest:
                raise HTTPException(409, "This scan already has a different evidence photo.")
        else:
            fd, temporary = tempfile.mkstemp(dir=target.parent, suffix=".tmp")
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
    except OSError:
        raise HTTPException(503, "Photo storage is unavailable; retry this upload.")
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
    return {"status": "success", "scan_id": str(scan_id),
            "image_url": f"/storage/{scan_id}.jpg", "sha256": digest, "size_bytes": len(data)}
