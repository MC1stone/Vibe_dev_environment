"""
Forms for NIR_Mistral Authentication
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from core.models import User
from django.core.exceptions import ValidationError


class CustomAuthenticationForm(AuthenticationForm):
    """Custom authentication form that accepts both username and email"""
    
    username = forms.CharField(
        label="Username or Email",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your username or email',
            'autofocus': True
        })
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your password'
        })
    )
    remember = forms.BooleanField(
        required=False,
        label="Remember me",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    def clean_username(self):
        """Allow login with both username and email"""
        username = self.cleaned_data.get('username')
        
        # Check if it's an email
        if '@' in username:
            try:
                user = User.objects.get(email=username)
                return user.username  # Return the actual username for authentication
            except User.DoesNotExist:
                pass
        
        # Return as-is (could be username)
        return username
    
    def confirm_login_allowed(self, user):
        """Check if user is active"""
        if not user.is_active:
            raise ValidationError("This account is inactive.")


class CustomUserCreationForm(UserCreationForm):
    """Custom user registration form with additional fields"""
    
    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your email address',
            'required': True
        })
    )
    first_name = forms.CharField(
        label="First Name",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your first name',
            'required': True
        })
    )
    last_name = forms.CharField(
        label="Last Name",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your last name',
            'required': True
        })
    )
    username = forms.CharField(
        label="Username",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Choose a username',
            'required': True
        })
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Create a strong password',
            'required': True
        })
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm your password',
            'required': True
        })
    )
    institution = forms.CharField(
        label="Institution (Optional)",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Your institution or organization'
        })
    )
    accept_terms = forms.BooleanField(
        required=True,
        label="I accept the Terms and Conditions and Privacy Policy",
        error_messages={
            'required': 'You must accept the terms and conditions to register.'
        }
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2', 'institution']
    
    def clean_email(self):
        """Validate email uniqueness"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email
    
    def clean_username(self):
        """Validate username uniqueness"""
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError("A user with this username already exists.")
        return username
    
    def clean_password2(self):
        """Validate password confirmation"""
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError("The two password fields didn't match.")
        
        # Check password strength
        if password2 and len(password2) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        
        return password2
    
    def save(self, commit=True):
        """Save the user with additional fields"""
        user = super().save(commit=False)
        
        # Set additional fields
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.institution = self.cleaned_data.get('institution', '')
        
        if commit:
            user.save()
        
        return user


class UserPreferenceForm(forms.ModelForm):
    """Form for updating user preferences including integration settings"""
    
    class Meta:
        from core.models import UserPreference
        model = UserPreference
        fields = [
            'theme', 'language', 'timezone',
            'email_notifications', 'job_completion_notifications', 'error_notifications',
            'auto_process_uploads', 'max_storage_usage', 'auto_cleanup_old_files', 'retention_days',
            'flowerai_enabled', 'federated_learning_enabled', 'share_spectra_data',
            'share_metadata', 'share_analysis_results', 'data_visibility',
            'ilias_enabled', 'ilias_sync_enabled'
        ]
        widgets = {
            'theme': forms.Select(attrs={'class': 'form-input'}),
            'language': forms.Select(attrs={'class': 'form-input'}),
            'timezone': forms.Select(attrs={'class': 'form-input'}),
            'email_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'job_completion_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'error_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'auto_process_uploads': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'max_storage_usage': forms.NumberInput(attrs={'class': 'form-input'}),
            'auto_cleanup_old_files': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'retention_days': forms.NumberInput(attrs={'class': 'form-input'}),
            'flowerai_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'federated_learning_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'share_spectra_data': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'share_metadata': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'share_analysis_results': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'data_visibility': forms.Select(attrs={'class': 'form-input'}),
            'ilias_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ilias_sync_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
