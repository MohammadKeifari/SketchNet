from django import forms
from .models import Dataset
from .services import validate_file_size, FORMAT_EXTENSIONS


class DatasetForm(forms.ModelForm):
    class Meta:
        model = Dataset
        fields = [
            "name",
            "description",
            "format",
            "file",
            "cover_image",
            "is_private",
            "user_shape",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Dataset name",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-input",
                    "rows": 3,
                    "placeholder": "Describe your dataset...",
                }
            ),
            "format": forms.Select(attrs={"class": "form-input"}),
            "file": forms.FileInput(attrs={"class": "form-input-file"}),
            "cover_image": forms.FileInput(attrs={"class": "form-input-file"}),
            "user_shape": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "e.g., (1000, 28, 28)"}
            ),
        }

    def clean_file(self):
        file = self.cleaned_data.get("file")
        if file:
            validate_file_size(file)
        return file

    def clean_cover_image(self):
        image = self.cleaned_data.get("cover_image")
        if image and image.size > 5 * 1024 * 1024:  # 5MB max for cover
            raise forms.ValidationError("Cover image must be under 5MB.")
        return image


class DatasetEditForm(DatasetForm):
    """Same as create but file is optional during edit"""

    file = forms.FileField(
        required=False, widget=forms.FileInput(attrs={"class": "form-input-file"})
    )


class PrivateAccessForm(forms.Form):
    """Search and add users to private dataset"""

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "Search by name or email...",
            }
        ),
    )
