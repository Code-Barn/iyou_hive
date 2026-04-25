from django import forms
from .models import ArchiveDocument


class ArchiveDocumentForm(forms.ModelForm):
    """Form for uploading documents to the archive."""
    
    class Meta:
        model = ArchiveDocument
        fields = ['title', 'file', 'file_type', 'category', 'description', 'tags']
        widgets = {
            'file_type': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.TextInput(attrs={'class': 'form-input'}),
            'title': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'tags': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'comma,separated,tags'
            }),
        }
        help_texts = {
            'tags': 'Enter comma-separated tags for easier filtering',
        }
    
    def clean_tags(self):
        """Parse comma-separated tags into a list."""
        tags = self.cleaned_data.get('tags', '')
        if tags:
            return [tag.strip() for tag in tags.split(',') if tag.strip()]
        return []
    
    def save(self, commit=True):
        """Save the document with metadata."""
        document = super().save(commit=False)
        
        # Auto-detect file type if not specified
        if not document.file_type and document.file:
            extension = document.get_file_extension()
            if extension == 'pdf':
                document.file_type = 'pdf'
            elif extension in ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg']:
                document.file_type = 'image'
            elif extension in ['doc', 'docx']:
                document.file_type = 'word'
            else:
                document.file_type = 'other'
        
        if commit:
            document.save()
        
        return document
