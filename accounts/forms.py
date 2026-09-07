from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import MinimumLengthValidator
from django.core.validators import FileExtensionValidator

User = get_user_model()

AVATAR_MAX_BYTES = 2 * 1024 * 1024
AVATAR_EXTENSIONS = ("jpeg", "jpg", "png", "webp")


class CustomSignupForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={"class": "form-input", "placeholder": "Password"}
        ),
        validators=[MinimumLengthValidator(8).validate],  # Add this
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(
            attrs={"class": "form-input", "placeholder": "Confirm password"}
        ),
    )

    class Meta:
        model = User
        fields = ["username", "email"]
        widgets = {
            "username": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Username"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-input", "placeholder": "Email address"}
            ),
        }

    def clean_password2(self):
        """Ensure both password fields match."""
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match")
        return password2

    def save(self, commit=True):
        """Create the user with the hashed password from the form."""
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    """Edit bio and profile photo on the My Profile page."""

    remove_avatar = forms.BooleanField(required=False)

    class Meta:
        model = User
        fields = ["bio", "avatar"]
        widgets = {
            "bio": forms.Textarea(
                attrs={
                    "class": "form-input",
                    "rows": 3,
                    "maxlength": 280,
                    "placeholder": "A short bio…",
                }
            ),
            "avatar": forms.FileInput(
                attrs={
                    "class": "profile-file-input",
                    "accept": "image/jpeg,image/png,image/webp",
                    "aria-labelledby": "avatar-field-label",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["avatar"].required = False
        self.fields["avatar"].validators.append(
            FileExtensionValidator(AVATAR_EXTENSIONS)
        )
        self.fields["bio"].required = False

    def clean_avatar(self):
        """Reject oversized or disallowed profile photos."""
        image = self.cleaned_data.get("avatar")
        if not image:
            return image
        if getattr(image, "size", 0) > AVATAR_MAX_BYTES:
            raise forms.ValidationError("Profile photo must be under 2MB.")
        name = getattr(image, "name", "") or ""
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext not in AVATAR_EXTENSIONS:
            raise forms.ValidationError("Use a JPEG, PNG, or WebP image.")
        return image

    def save(self, commit=True):
        """Persist bio/avatar, honoring the remove-photo checkbox."""
        user = super().save(commit=False)
        uploaded = self.files.get("avatar")
        if self.cleaned_data.get("remove_avatar") and not uploaded:
            if user.avatar:
                user.avatar.delete(save=False)
            user.avatar = None
        if commit:
            user.save()
        return user
