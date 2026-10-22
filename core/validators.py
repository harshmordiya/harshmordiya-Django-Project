import os
import io
import zipfile
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db.models.fields.files import FieldFile

MAX_NOTES_FILE_SIZE = getattr(settings, "MAX_NOTES_FILE_SIZE", 50 * 1024 * 1024)
ALLOWED_NOTES_EXTENSIONS = getattr(settings, "ALLOWED_NOTES_EXTENSIONS", [".pdf", ".docx", ".txt", ".pptx"])


def validate_course_notes_file(file):
    if not file:
        return file

    if isinstance(file, FieldFile) or (not isinstance(file, UploadedFile) and not hasattr(file, "file")):
        return file

    filename = getattr(file, "name", "")
    if not filename:
        raise ValidationError("Uploaded file must have a valid filename.")

    clean_name = os.path.basename(filename)
    if not clean_name or ".." in filename:
        raise ValidationError("Invalid filename detected.")

    ext = os.path.splitext(clean_name)[1].lower()
    if ext not in ALLOWED_NOTES_EXTENSIONS:
        allowed_display = ", ".join(e.upper().lstrip(".") for e in ALLOWED_NOTES_EXTENSIONS)
        raise ValidationError(
            f"Unsupported file format '{ext}'. Allowed formats: {allowed_display}."
        )

    file_size = getattr(file, "size", None)
    if file_size is not None and file_size > MAX_NOTES_FILE_SIZE:
        size_in_mb = round(file_size / (1024 * 1024), 1)
        raise ValidationError(
            f"File size ({size_in_mb} MB) exceeds the maximum allowed limit of 50 MB."
        )

    try:
        if ext == ".pdf":
            header = file.read(1024)
            file.seek(0)
            if not header or b"%PDF-" not in header[:1024] or header.startswith(b"MZ"):
                raise ValidationError(
                    "The uploaded file does not match a valid PDF document. Please upload a genuine PDF file."
                )

        elif ext == ".docx":
            header = file.read(4)
            file.seek(0)
            if header != b"PK\x03\x04":
                raise ValidationError(
                    "The uploaded file does not match a valid Word (.docx) document."
                )
            try:
                with zipfile.ZipFile(file) as zf:
                    namelist = zf.namelist()
                    if not any(name.startswith("word/") or name == "[Content_Types].xml" for name in namelist):
                        raise ValidationError(
                            "The uploaded file is not a valid Word (.docx) document."
                        )
            except (zipfile.BadZipFile, zipfile.LargeZipFile):
                raise ValidationError(
                    "The uploaded file is not a valid or readable Word (.docx) document."
                )
            finally:
                file.seek(0)

        elif ext == ".pptx":
            header = file.read(4)
            file.seek(0)
            if header != b"PK\x03\x04":
                raise ValidationError(
                    "The uploaded file does not match a valid PowerPoint (.pptx) presentation."
                )
            try:
                with zipfile.ZipFile(file) as zf:
                    namelist = zf.namelist()
                    if not any(name.startswith("ppt/") or name == "[Content_Types].xml" for name in namelist):
                        raise ValidationError(
                            "The uploaded file is not a valid PowerPoint (.pptx) presentation."
                        )
            except (zipfile.BadZipFile, zipfile.LargeZipFile):
                raise ValidationError(
                    "The uploaded file is not a valid or readable PowerPoint (.pptx) presentation."
                )
            finally:
                file.seek(0)

        elif ext == ".txt":
            chunk = file.read(4096)
            file.seek(0)
            if (
                chunk.startswith(b"MZ")
                or chunk.startswith(b"\x7fELF")
                or chunk.startswith(b"\xca\xfe\xba\xbe")
                or chunk.startswith(b"PK\x03\x04")
            ):
                raise ValidationError(
                    "Suspicious executable or binary content detected in text file."
                )
            if b"\x00" in chunk:
                raise ValidationError(
                    "Binary content detected. Only plain text (.txt) files are permitted."
                )
            try:
                chunk.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    chunk.decode("latin-1")
                except UnicodeDecodeError:
                    raise ValidationError(
                        "The uploaded file is not a valid text document."
                    )

    except ValidationError:
        file.seek(0)
        raise
    except Exception as e:
        file.seek(0)
        raise ValidationError(
            f"Failed to verify file integrity: {str(e)}"
        )
    finally:
        file.seek(0)

    return file
