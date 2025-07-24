from io import BytesIO
import mimetypes
import barcode
from barcode.writer import ImageWriter
from fastapi import Request, UploadFile
from datetime import datetime, timedelta, timezone
from slugify import slugify
from starlette.datastructures import UploadFile as StarletteUploadFile
import qrcode

from app.helpers.s3 import upload_file_to_s3

class SimpleUploadFile:
    def __init__(self, filename: str, file: BytesIO, content_type: str):
        self.filename = filename
        self.file = file
        self.content_type = content_type

def get_lang_from_request(request: Request):
    return request.headers.get("Accept-Language", "en")

def parse_date_to_utc_start(date_str):
    """Parse 'YYYY-MM-DD' to UTC datetime at start of day."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except Exception:
        return None

def parse_date_to_utc_end(date_str):
    """Parse 'YYYY-MM-DD' to UTC datetime at start of next day (exclusive)."""
    try:
        return (datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)).replace(tzinfo=timezone.utc)
    except Exception:
        return None

def apply_operator(column, operator, value, field_type=None):
    """
    Apply the correct SQLAlchemy filter based on operator and field type.
    """
    # Boolean fields (stored as text, e.g., "true"/"false")
    if field_type == "boolean":
        if isinstance(value, bool):
            value = "true" if value else "false"
        value = str(value).lower()
        if operator == "equal":
            return column == value
        elif operator == "notequal":
            return column != value

    # Date fields (value should be a date/datetime object or string in ISO format)
    elif field_type == "date":
        # You may want to parse the value to a datetime object before calling this function
        if operator == "equal":
            return column == value
        elif operator == "notequal":
            return column != value
        elif operator == "greater":
            return column > value
        elif operator == "lesser":
            return column < value

    # Dropdown fields (multi-select)
    elif field_type == "dropdown":
        # value is expected to be a list
        if operator == "in":
            return column.in_(value)
        elif operator == "notin":
            return ~column.in_(value)

    # Number fields
    elif field_type == "number":
        # Convert value to int or float as needed
        try:
            num_value = int(value)
        except (ValueError, TypeError):
            num_value = float(value)
        if operator == "equal":
            return column == num_value
        elif operator == "notequal":
            return column != num_value

    # Text fields
    elif field_type == "text":
        if operator == "like":
            return column.ilike(f"%{value}%")

    # Default fallback (treat as string)
    if operator == "equal":
        return column == str(value)
    elif operator == "notequal":
        return column != str(value)
    elif operator == "greater":
        return column > value
    elif operator == "lesser":
        return column < value
    elif operator == "like":
        return column.ilike(f"%{value}%")
    elif operator == "in":
        return column.in_(value)
    elif operator == "notin":
        return ~column.in_(value)

    raise ValueError(f"Unsupported operator '{operator}' for field type '{field_type}'")

def create_upload_file(file_bytes: BytesIO, filename: str) -> 'SimpleUploadFile':
    file_bytes.seek(0)
    content_type, _ = mimetypes.guess_type(filename)
    if content_type is None:
        content_type = 'application/octet-stream'

    return SimpleUploadFile(filename, file_bytes, content_type)

def generate_qr_code(data: str) -> str:
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")

    upload_file = create_upload_file(buffer, f"{slugify(data)}.png")
    return upload_file_to_s3(upload_file, folder="qr_codes")

def generate_barcode(data: str) -> str:
    buffer = BytesIO()
    code128 = barcode.get("code128", data, writer=ImageWriter())
    code128.write(buffer, options={"write_text": False})

    upload_file = create_upload_file(buffer, f"{slugify(data)}.png")
    return upload_file_to_s3(upload_file, folder="barcodes")