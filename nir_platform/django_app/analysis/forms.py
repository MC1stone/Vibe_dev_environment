"""
Forms for the Analysis app in NIR Intelligence Platform.
"""

from django import forms
from django.core.validators import FileExtensionValidator
from .models import SpectralData, AnalysisProject, ChatSession
from django.conf import settings


class UploadFileForm(forms.Form):
    """Form for uploading spectral data files."""
    
    file = forms.FileField(
        label='Spectral Data File',
        help_text='Upload a file containing spectral data',
        validators=[
            FileExtensionValidator(allowed_extensions=['.csv', '.txt', '.xlsx', '.json', '.spc', '.jdx', '.zip'])
        ]
    )
    
    spectrometer_type = forms.ChoiceField(
        label='Spectrometer Type',
        choices=[
            ('', 'Auto-detect'),
            ('ocean_optics', 'Ocean Optics'),
            ('asd_fieldspec', 'ASD FieldSpec'),
            ('bruker', 'Bruker'),
            ('diy_raspberry', 'DIY Raspberry Pi'),
            ('diy_arduino', 'DIY Arduino'),
            ('other', 'Other')
        ],
        required=False,
        help_text='Select your spectrometer type or leave blank for auto-detection'
    )
    
    metadata = forms.CharField(
        label='Additional Metadata',
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'Enter metadata as JSON...'}),
        required=False,
        help_text='Optional: Additional metadata in JSON format'
    )


class AnalysisForm(forms.Form):
    """Form for analysis parameters."""
    
    analysis_type = forms.ChoiceField(
        label='Analysis Type',
        choices=[
            ('full', 'Full Analysis'),
            ('spectral', 'Spectral Analysis Only'),
            ('metadata', 'Metadata Quality Only'),
            ('calibration', 'Calibration Only')
        ],
        initial='full',
        help_text='Select the type of analysis to perform'
    )
    
    include_calibration = forms.BooleanField(
        label='Include Calibration',
        initial=True,
        required=False,
        help_text='Whether to perform calibration as part of the analysis'
    )
    
    include_metadata_quality = forms.BooleanField(
        label='Include Metadata Quality Assessment',
        initial=True,
        required=False,
        help_text='Whether to assess metadata quality'
    )
    
    generate_report = forms.BooleanField(
        label='Generate Report',
        initial=True,
        required=False,
        help_text='Whether to generate a comprehensive report'
    )
    
    report_format = forms.ChoiceField(
        label='Report Format',
        choices=[
            ('html', 'HTML'),
            ('pdf', 'PDF'),
            ('both', 'Both')
        ],
        initial='html',
        required=False,
        help_text='Format for the generated report'
    )


class ChatForm(forms.ModelForm):
    """Form for chat messages."""
    
    message = forms.CharField(
        label='',
        widget=forms.TextInput(attrs={
            'placeholder': 'Type your message here...',
            'class': 'form-control',
            'autofocus': True
        }),
        help_text='Enter your message to chat with the AI agent'
    )
    
    class Meta:
        model = ChatSession
        fields = ['message']


class ProjectForm(forms.ModelForm):
    """Form for creating analysis projects."""
    
    name = forms.CharField(
        label='Project Name',
        max_length=255,
        help_text='Enter a name for your analysis project'
    )
    
    description = forms.CharField(
        label='Description',
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        help_text='Describe your project'
    )
    
    project_type = forms.ChoiceField(
        label='Project Type',
        choices=[
            ('research', 'Research'),
            ('education', 'Education'),
            ('quality_control', 'Quality Control'),
            ('other', 'Other')
        ],
        initial='research',
        required=False,
        help_text='Select the type of project'
    )
    
    tags = forms.CharField(
        label='Tags',
        required=False,
        help_text='Comma-separated list of tags'
    )
    
    class Meta:
        model = AnalysisProject
        fields = ['name', 'description', 'project_type', 'tags']


class FederatedLearningForm(forms.Form):
    """Form for federated learning consent."""
    
    consent = forms.BooleanField(
        label='I consent to share my data with the federated learning network',
        required=True,
        help_text='By checking this box, you agree to share your anonymized spectral data with the federated learning network to improve models for all users.'
    )
    
    share_metadata = forms.BooleanField(
        label='Share metadata',
        initial=True,
        required=False,
        help_text='Include metadata in the federated learning data'
    )
    
    share_spectra = forms.BooleanField(
        label='Share spectral data',
        initial=True,
        required=False,
        help_text='Include spectral data in the federated learning data'
    )
    
    anonymize_data = forms.BooleanField(
        label='Anonymize my data',
        initial=True,
        required=False,
        help_text='Remove all personally identifiable information from shared data'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        consent = cleaned_data.get('consent')
        
        if not consent:
            # If no consent, disable all sharing
            cleaned_data['share_metadata'] = False
            cleaned_data['share_spectra'] = False
        
        return cleaned_data
