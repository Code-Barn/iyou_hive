from celery import shared_task
from .models import ArchiveDocument
from pathlib import Path
from apps.core.document_processing import convert_pdf_to_markdown as process_pdf_to_markdown

@shared_task
def convert_pdf_to_markdown(document_id):
    """
    Celery task to convert a PDF to Markdown.
    """
    document = ArchiveDocument.objects.get(id=document_id)
    try:
        document.conversion_status = 'PROCESSING'
        document.save()

        # Get the absolute path to the file
        file_path = Path(document.file.path)

        # Process the PDF
        markdown_path = process_pdf_to_markdown(file_path)

        # Update the document record
        document.conversion_status = 'SUCCESS'
        document.markdown_path = str(markdown_path)
        document.save()

    except Exception as e:
        # Handle conversion failure
        document.conversion_status = 'FAILED'
        document.conversion_error = str(e)
        document.save()
