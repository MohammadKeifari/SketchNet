from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import MinimumLengthValidator

User = get_user_model()


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
