# Copyright (C) 2026 Byers Brands, LLC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

from celery import shared_task
from .models import ArchiveDocument
from pathlib import Path
from .utils import convert_pdf_to_markdown as process_pdf_to_markdown
from apps.core.tasks import load_document_text

@shared_task
def convert_pdf_to_markdown(document_id):
    """
    Celery task to convert a PDF to Markdown and extract text.
    """
    document = ArchiveDocument.objects.get(id=document_id)
    try:
        document.conversion_status = 'PROCESSING'
        document.text_extraction_status = 'PROCESSING'
        document.save()

        # Get the absolute path to the file
        file_path = Path(document.file.path)

        # First, extract text content
        try:
            extracted_text = load_document_text(document)
            document.extracted_text = extracted_text
            document.text_extraction_status = 'SUCCESS'
        except Exception as text_extract_error:
            document.extracted_text = f"Text extraction error: {str(text_extract_error)}"
            document.text_extraction_status = 'FAILED'

        # Process the PDF to Markdown
        try:
            markdown_path = process_pdf_to_markdown(file_path)
            document.conversion_status = 'SUCCESS'
            document.markdown_path = str(markdown_path)
        except Exception as convert_error:
            document.conversion_status = 'FAILED'
            document.conversion_error = str(convert_error)

        document.save()

    except Exception as e:
        # Handle conversion failure
        document.conversion_status = 'FAILED'
        document.text_extraction_status = 'FAILED'
        document.conversion_error = str(e)
        document.save()
