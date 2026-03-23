from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
import os
from datetime import datetime
from io import BytesIO
from datetime import datetime
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import uuid
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

OUTPUT_DIR = "storage/pdfs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def add_header_footer(canvas, doc):
    # Header
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(40, 800, "⚡ TranscodeCloud PDF Generator")

    # Footer
    canvas.setFont("Helvetica", 9)
    canvas.drawString(40, 20, f"Page {doc.page}")

import boto3
from io import BytesIO
import uuid

def generate_styled_pdf(data):
    filename = f"{uuid.uuid4()}.pdf"
    s3_key = f"pdfs/{filename}"

    buffer = BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()

    elements = []

    if "title" in data:
        elements.append(Paragraph(data["title"], styles["Title"]))
        elements.append(Spacer(1, 20))

    table_data = []

    for key, value in data.items():
        if key == "title":
            continue

        if isinstance(value, list):
            value = ", ".join(map(str, value))

        table_data.append([
            Paragraph(f"<b>{key}</b>", styles["BodyText"]),
            Paragraph(str(value), styles["BodyText"])
        ])

    table = Table(table_data, colWidths=[150, 300])

    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
    ]))

    elements.append(table)

    doc.build(
        elements,
        onFirstPage=add_header_footer,
        onLaterPages=add_header_footer
    )

    # ✅ reset buffer
    buffer.seek(0)

    # ✅ Upload to S3 (same as your video logic)
    s3_client = boto3.client("s3", region_name="us-east-1")

    bucket_name = "pdfgeneratorbucket23"

    s3_client.upload_fileobj(
        buffer,
        bucket_name,
        s3_key,
        ExtraArgs={
            "ContentType": "application/pdf"
        }
    )

    file_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"

    return file_url, filename