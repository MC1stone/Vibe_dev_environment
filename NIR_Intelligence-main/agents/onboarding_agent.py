#!/usr/bin/env python3
"""
NIR Intelligence Platform - OnboardingAgent
Agent for user onboarding, tutorial system, and contextual help
"""

import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
from .base_agent import BaseAgent, AgentOutput, AgentStatus, ErrorSeverity, AgentError


@dataclass
class OnboardingStep:
    """Represents a single onboarding step"""
    id: str
    title: str
    description: str
    target_element: Optional[str] = None
    position: str = "bottom"  # top, bottom, left, right
    completed: bool = False
    required: bool = True
    order: int = 0


@dataclass
class HelpTopic:
    """Represents a help topic"""
    id: str
    title: str
    content: str
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    related_features: List[str] = field(default_factory=list)


@dataclass
class Tooltip:
    """Represents a contextual tooltip"""
    id: str
    element_selector: str
    content: str
    position: str = "top"
    trigger: str = "hover"  # hover, click, focus
    delay: int = 300


@dataclass
class ProgressIndicator:
    """Represents user progress through onboarding"""
    user_id: str
    current_step: str
    completed_steps: List[str] = field(default_factory=list)
    started_at: str = ""
    last_activity: str = ""
    completion_percentage: float = 0.0


class OnboardingAgent(BaseAgent):
    """
    Agent for user onboarding, tutorial system, and contextual help
    
    Features:
    - Interactive onboarding tutorials
    - Contextual help system
    - Progress tracking
    - Tooltip management
    - User guidance and assistance
    """
    
    def __init__(self, **kwargs):
        super().__init__(name="OnboardingAgent", version="2.0.0", **kwargs)
        self.dependencies = ['jinja2']
        self.logger = logging.getLogger(f"Agent.OnboardingAgent")
        
        # Configuration
        self.onboarding_data_file = kwargs.get('onboarding_data_file', 'data/onboarding.json')
        self.help_data_file = kwargs.get('help_data_file', 'data/help_topics.json')
        self.tooltip_data_file = kwargs.get('tooltip_data_file', 'data/tooltips.json')
        self.output_dir = kwargs.get('output_dir', 'static/onboarding')
        self.template_dir = kwargs.get('template_dir', 'templates/onboarding')
        
        # Initialize agent-specific attributes
        self._initialize_attributes()
    
    def _initialize_attributes(self):
        """Initialize agent-specific attributes"""
        self.onboarding_steps: Dict[str, OnboardingStep] = {}
        self.help_topics: Dict[str, HelpTopic] = {}
        self.tooltips: Dict[str, Tooltip] = {}
        self.user_progress: Dict[str, ProgressIndicator] = {}
        self.stats = {
            'onboarding_steps_created': 0,
            'help_topics_created': 0,
            'tooltips_created': 0,
            'users_onboarded': 0,
            'errors': 0
        }
        
        # Load existing data
        self._load_onboarding_data()
        self._load_help_data()
        self._load_tooltip_data()
    
    def _load_onboarding_data(self):
        """Load onboarding data from file"""
        try:
            data_path = Path(self.onboarding_data_file)
            if data_path.exists():
                with open(data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for step_data in data.get('steps', []):
                        step = OnboardingStep(
                            id=step_data.get('id', ''),
                            title=step_data.get('title', ''),
                            description=step_data.get('description', ''),
                            target_element=step_data.get('target_element'),
                            position=step_data.get('position', 'bottom'),
                            completed=step_data.get('completed', False),
                            required=step_data.get('required', True),
                            order=step_data.get('order', 0)
                        )
                        self.onboarding_steps[step.id] = step
                        self.stats['onboarding_steps_created'] += 1
        except Exception as e:
            self.logger.warning(f"Could not load onboarding data: {str(e)}")
    
    def _load_help_data(self):
        """Load help topics from file"""
        try:
            data_path = Path(self.help_data_file)
            if data_path.exists():
                with open(data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for topic_data in data.get('topics', []):
                        topic = HelpTopic(
                            id=topic_data.get('id', ''),
                            title=topic_data.get('title', ''),
                            content=topic_data.get('content', ''),
                            category=topic_data.get('category', 'general'),
                            tags=topic_data.get('tags', []),
                            related_features=topic_data.get('related_features', [])
                        )
                        self.help_topics[topic.id] = topic
                        self.stats['help_topics_created'] += 1
        except Exception as e:
            self.logger.warning(f"Could not load help data: {str(e)}")
    
    def _load_tooltip_data(self):
        """Load tooltip data from file"""
        try:
            data_path = Path(self.tooltip_data_file)
            if data_path.exists():
                with open(data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for tooltip_data in data.get('tooltips', []):
                        tooltip = Tooltip(
                            id=tooltip_data.get('id', ''),
                            element_selector=tooltip_data.get('element_selector', ''),
                            content=tooltip_data.get('content', ''),
                            position=tooltip_data.get('position', 'top'),
                            trigger=tooltip_data.get('trigger', 'hover'),
                            delay=tooltip_data.get('delay', 300)
                        )
                        self.tooltips[tooltip.id] = tooltip
                        self.stats['tooltips_created'] += 1
        except Exception as e:
            self.logger.warning(f"Could not load tooltip data: {str(e)}")
    
    def create_default_onboarding_steps(self) -> List[OnboardingStep]:
        """Create default onboarding steps for NIR Intelligence Platform"""
        steps = [
            OnboardingStep(
                id="welcome",
                title="Welcome to NIR Intelligence",
                description="Thank you for choosing NIR Intelligence! This platform helps you analyze spectral data from any spectrometer. Let's get started with a quick tour.",
                target_element="#welcome-modal",
                position="center",
                required=True,
                order=0
            ),
            OnboardingStep(
                id="upload_spectra",
                title="Upload Your Spectra",
                description="Start by uploading your spectral data files. We support various formats including WAV, MP3, PNG, JPG, and more.",
                target_element="#upload-button",
                position="bottom",
                required=True,
                order=1
            ),
            OnboardingStep(
                id="select_analysis",
                title="Select Analysis Type",
                description="Choose the type of analysis you want to perform. Options include spectral analysis, metadata quality assessment, and spectrometer calibration.",
                target_element="#analysis-selector",
                position="right",
                required=True,
                order=2
            ),
            OnboardingStep(
                id="view_results",
                title="View Analysis Results",
                description="After analysis, you'll see detailed results including spectral data, metadata quality scores, and recommendations for improvement.",
                target_element="#results-section",
                position="top",
                required=True,
                order=3
            ),
            OnboardingStep(
                id="federated_learning",
                title="Join Federated Learning",
                description="Contribute your data to the federated learning system to help improve models across the community. Your privacy is always protected.",
                target_element="#federated-section",
                position="left",
                required=False,
                order=4
            ),
            OnboardingStep(
                id="ilias_integration",
                title="ILIAS Integration",
                description="Connect with your ILIAS learning platform to access courses, forums, and collaborate with other researchers.",
                target_element="#ilias-section",
                position="right",
                required=False,
                order=5
            ),
            OnboardingStep(
                id="completion",
                title="Onboarding Complete!",
                description="You've completed the basic onboarding. You're now ready to start analyzing your spectral data. Don't hesitate to use the help system if you need assistance.",
                target_element="#completion-modal",
                position="center",
                required=True,
                order=6
            )
        ]
        
        return steps
    
    def create_default_help_topics(self) -> List[HelpTopic]:
        """Create default help topics"""
        topics = [
            HelpTopic(
                id="getting_started",
                title="Getting Started",
                content="""
                <h3>Welcome to NIR Intelligence!</h3>
                <p>This platform is designed to help researchers and scientists analyze spectral data from any type of spectrometer, including DIY devices.</p>
                
                <h4>Quick Start Guide:</h4>
                <ol>
                    <li><strong>Upload Data:</strong> Start by uploading your spectral data files in the Upload section.</li>
                    <li><strong>Select Analysis:</strong> Choose the type of analysis you want to perform.</li>
                    <li><strong>View Results:</strong> Review your analysis results and recommendations.</li>
                    <li><strong>Save & Share:</strong> Save your results and optionally share them with the federated learning community.</li>
                </ol>
                
                <p>For more detailed information, explore the help topics below or use the contextual help (?) icons throughout the application.</p>
                """,
                category="getting_started",
                tags=["beginner", "start", "overview"],
                related_features=["upload", "analysis", "results"]
            ),
            HelpTopic(
                id="file_formats",
                title="Supported File Formats",
                content="""
                <h3>Supported File Formats</h3>
                <p>NIR Intelligence supports a wide range of file formats for spectral data analysis:</p>
                
                <h4>Audio Formats:</h4>
                <ul>
                    <li><strong>WAV:</strong> Standard audio format, commonly used for spectral data from audio-based spectrometers</li>
                    <li><strong>MP3:</strong> Compressed audio format, supported for compatibility</li>
                    <li><strong>FLAC:</strong> Lossless audio format, recommended for high-quality spectral data</li>
                </ul>
                
                <h4>Image Formats:</h4>
                <ul>
                    <li><strong>PNG:</strong> Lossless image format, ideal for spectral charts and graphs</li>
                    <li><strong>JPG/JPEG:</strong> Compressed image format, supported for compatibility</li>
                    <li><strong>TIFF:</strong> High-quality image format, recommended for scientific data</li>
                    <li><strong>BMP:</strong> Standard bitmap format</li>
                </ul>
                
                <h4>Spectral Data Formats:</h4>
                <ul>
                    <li><strong>CSV:</strong> Comma-separated values, commonly used for spectral data export</li>
                    <li><strong>JSON:</strong> JavaScript Object Notation, used for structured spectral data</li>
                    <li><strong>XML:</strong> eXtensible Markup Language, supported for compatibility</li>
                    <li><strong>TXT:</strong> Plain text format, for simple spectral data</li>
                </ul>
                
                <p><strong>Note:</strong> For best results, use uncompressed formats like WAV, FLAC, PNG, or TIFF when possible.</p>
                """,
                category="data_formats",
                tags=["formats", "files", "upload", "data"],
                related_features=["upload", "data_processing"]
            ),
            HelpTopic(
                id="metadata_quality",
                title="Metadata Quality Analysis",
                content="""
                <h3>Metadata Quality Analysis</h3>
                <p>Our metadata quality assessment system evaluates your spectral data metadata against established standards to ensure completeness and accuracy.</p>
                
                <h4>Quality Criteria:</h4>
                <ul>
                    <li><strong>Completeness:</strong> All required metadata fields are present</li>
                    <li><strong>Accuracy:</strong> Metadata values are valid and consistent</li>
                    <li><strong>Standards Compliance:</strong> Metadata follows recognized standards (Dublin Core, ISO, etc.)</li>
                    <li><strong>Consistency:</strong> Metadata is consistent across related datasets</li>
                    <li><strong>Timeliness:</strong> Metadata is up-to-date and relevant</li>
                </ul>
                
                <h4>Quality Score:</h4>
                <p>The quality score is calculated on a scale from 0 to 100, where:</p>
                <ul>
                    <li><strong>90-100:</strong> Excellent - Metadata meets all standards and best practices</li>
                    <li><strong>80-89:</strong> Good - Metadata is mostly complete with minor issues</li>
                    <li><strong>70-79:</strong> Fair - Metadata has several issues that need attention</li>
                    <li><strong>60-69:</strong> Poor - Metadata has significant gaps and errors</li>
                    <li><strong>Below 60:</strong> Incomplete - Major metadata is missing or invalid</li>
                </ul>
                
                <h4>Improvement Recommendations:</h4>
                <p>Based on the analysis, we provide specific recommendations to improve your metadata quality, including:</p>
                <ul>
                    <li>Missing fields that should be added</li>
                    <li>Invalid values that need correction</li>
                    <li>Inconsistencies that should be resolved</li>
                    <li>Standards that should be followed</li>
                </ul>
                """,
                category="analysis",
                tags=["metadata", "quality", "standards", "analysis"],
                related_features=["metadata_analysis", "quality_scoring"]
            ),
            HelpTopic(
                id="spectrometer_analysis",
                title="Spectrometer Analysis and Calibration",
                content="""
                <h3>Spectrometer Analysis and Calibration</h3>
                <p>Our system analyzes your spectral data for potential spectrometer issues and provides recommendations for optimal parameter setup.</p>
                
                <h4>Detected Issues:</h4>
                <ul>
                    <li><strong>Wavelength Shift:</strong> Detection of shifts in wavelength calibration that may affect measurement accuracy</li>
                    <li><strong>Intensity Drift:</strong> Identification of intensity variations that may indicate sensor issues</li>
                    <li><strong>Noise Levels:</strong> Analysis of signal-to-noise ratio and noise characteristics</li>
                    <li><strong>Resolution Issues:</strong> Assessment of spectral resolution and potential limitations</li>
                    <li><strong>Baseline Problems:</strong> Detection of baseline shifts or curvature that may affect data quality</li>
                </ul>
                
                <h4>Parameter Recommendations:</h4>
                <p>Based on the analysis of your spectrometer and data, we provide specific parameter recommendations:</p>
                <ul>
                    <li><strong>Integration Time:</strong> Optimal exposure time for your measurements</li>
                    <li><strong>Wavelength Range:</strong> Recommended spectral range for your application</li>
                    <li><strong>Resolution:</strong> Suggested spectral resolution settings</li>
                    <li><strong>Averaging:</strong> Recommended number of scans to average for improved signal-to-noise ratio</li>
                    <li><strong>Dark Correction:</strong> Advice on dark current correction and background subtraction</li>
                </ul>
                
                <h4>DIY Spectrometer Support:</h4>
                <p>We provide special support for DIY spectrometers, including:</p>
                <ul>
                    <li>Custom calibration profiles for popular DIY designs</li>
                    <li>Compensation for common DIY spectrometer limitations</li>
                    <li>Recommendations for hardware improvements</li>
                    <li>Community-shared calibration data</li>
                </ul>
                """,
                category="analysis",
                tags=["spectrometer", "calibration", "parameters", "DIY"],
                related_features=["spectrometer_analysis", "calibration"]
            ),
            HelpTopic(
                id="federated_learning",
                title="Federated Learning System",
                content="""
                <h3>Federated Learning System</h3>
                <p>The federated learning system allows you to contribute to and benefit from a collaborative model improvement process while maintaining data privacy.</p>
                
                <h4>How It Works:</h4>
                <ol>
                    <li><strong>Local Training:</strong> Your data is analyzed locally on your system</li>
                    <li><strong>Model Updates:</strong> Only model improvements (not your data) are shared with the central server</li>
                    <li><strong>Aggregation:</strong> The central server aggregates updates from multiple participants</li>
                    <li><strong>Improved Models:</strong> Enhanced models are distributed back to all participants</li>
                </ol>
                
                <h4>Privacy Protection:</h4>
                <ul>
                    <li><strong>Data Never Leaves Your System:</strong> Your raw data and metadata stay on your local machine</li>
                    <li><strong>Secure Communication:</strong> All communications are encrypted using industry-standard protocols</li>
                    <li><strong>Anonymized Contributions:</strong> Model updates are anonymized and cannot be traced back to individual users</li>
                    <li><strong>Selective Participation:</strong> You control exactly what data is used for federated learning</li>
                </ul>
                
                <h4>Participation Options:</h4>
                <ul>
                    <li><strong>Full Participation:</strong> Share all analysis results for maximum community benefit</li>
                    <li><strong>Partial Participation:</strong> Share only specific types of data or results</li>
                    <li><strong>Anonymous Participation:</strong> Contribute without associating data with your account</li>
                    <li><strong>Opt-Out:</strong> Choose not to participate in federated learning at all</li>
                </ul>
                
                <h4>Benefits:</h4>
                <ul>
                    <li><strong>Improved Accuracy:</strong> Benefit from models trained on diverse datasets from the community</li>
                    <li><strong>Faster Analysis:</strong> Access to pre-trained models reduces local processing time</li>
                    <li><strong>Community Insights:</strong> Learn from patterns and insights discovered across the user base</li>
                    <li><strong>Continuous Improvement:</strong> Models improve over time as more users participate</li>
                </ul>
                
                <p><strong>Note:</strong> Federated learning is completely optional. You can use all features of NIR Intelligence without participating.</p>
                """,
                category="federated",
                tags=["federated", "learning", "privacy", "collaboration"],
                related_features=["federated_learning", "privacy"]
            ),
            HelpTopic(
                id="ilias_integration",
                title="ILIAS Learning Platform Integration",
                content="""
                <h3>ILIAS Learning Platform Integration</h3>
                <p>Our integration with the ILIAS e-learning platform provides seamless access to courses, resources, and collaboration tools.</p>
                
                <h4>Features:</h4>
                <ul>
                    <li><strong>Single Sign-On (SSO):</strong> Log in once to access both NIR Intelligence and ILIAS with the same credentials</li>
                    <li><strong>Course Synchronization:</strong> Access your ILIAS courses directly from NIR Intelligence</li>
                    <li><strong>Resource Sharing:</strong> Share analysis results and reports with your ILIAS courses</li>
                    <li><strong>Communication:</strong> Discuss spectral analysis with classmates and instructors through ILIAS forums</li>
                    <li><strong>Assignment Integration:</strong> Submit spectral analysis assignments directly through ILIAS</li>
                    <li><strong>Grade Tracking:</strong> View grades and feedback for spectral analysis assignments</li>
                </ul>
                
                <h4>Getting Started:</h4>
                <ol>
                    <li><strong>Connect Your Account:</strong> Link your NIR Intelligence account with your ILIAS account in the settings</li>
                    <li><strong>Select Courses:</strong> Choose which ILIAS courses to integrate with NIR Intelligence</li>
                    <li><strong>Configure Permissions:</strong> Set what information is shared between the platforms</li>
                    <li><strong>Start Using:</strong> Access ILIAS features directly from the NIR Intelligence interface</li>
                </ol>
                
                <h4>User Groups and Collaboration:</h4>
                <p>Through ILIAS integration, you can:</p>
                <ul>
                    <li><strong>Join Research Groups:</strong> Collaborate with other researchers on spectral analysis projects</li>
                    <li><strong>Share Data:</strong> Securely share spectral data and analysis results with group members</li>
                    <li><strong>Discuss Results:</strong> Use ILIAS forums to discuss analysis findings and get feedback</li>
                    <li><strong>Access Shared Resources:</strong> Benefit from calibration data and analysis methods shared by the community</li>
                </ul>
                
                <h4>Privacy and Security:</h4>
                <ul>
                    <li><strong>Data Control:</strong> You control what data is shared with ILIAS and other users</li>
                    <li><strong>Institutional Compliance:</strong> Integration complies with your institution's data protection policies</li>
                    <li><strong>Selective Sharing:</strong> Choose which courses and groups can access your shared data</li>
                    <li><strong>Audit Trail:</strong> All data sharing activities are logged for transparency</li>
                </ul>
                
                <p><strong>Note:</strong> ILIAS integration is only available for registered users with valid ILIAS accounts.</p>
                """,
                category="integration",
                tags=["ilias", "integration", "collaboration", "education"],
                related_features=["ilias_integration", "collaboration"]
            )
        ]
        
        return topics
    
    def create_default_tooltips(self) -> List[Tooltip]:
        """Create default contextual tooltips"""
        tooltips = [
            Tooltip(
                id="upload_help",
                element_selector="#upload-button",
                content="Upload your spectral data files here. Supported formats include WAV, MP3, PNG, JPG, CSV, and more.",
                position="bottom",
                trigger="hover",
                delay=300
            ),
            Tooltip(
                id="analysis_type_help",
                element_selector="#analysis-type-select",
                content="Choose the type of analysis to perform. Options include spectral analysis, metadata quality assessment, and spectrometer calibration.",
                position="right",
                trigger="hover",
                delay=300
            ),
            Tooltip(
                id="metadata_quality_help",
                element_selector="#metadata-quality-score",
                content="This score represents the quality of your metadata based on completeness, accuracy, and standards compliance. Click for detailed breakdown.",
                position="top",
                trigger="hover",
                delay=300
            ),
            Tooltip(
                id="spectral_shift_help",
                element_selector="#spectral-shift-indicator",
                content="This indicator shows detected wavelength shifts in your spectral data. Red indicates significant shifts that may affect accuracy.",
                position="left",
                trigger="hover",
                delay=300
            ),
            Tooltip(
                id="parameter_recommendation_help",
                element_selector="#parameter-recommendations",
                content="These are optimized parameter suggestions based on your spectrometer type and the data being analyzed.",
                position="right",
                trigger="hover",
                delay=300
            ),
            Tooltip(
                id="federated_toggle_help",
                element_selector="#federated-toggle",
                content="Toggle this switch to enable or disable participation in the federated learning system. Your data remains private regardless of this setting.",
                position="bottom",
                trigger="hover",
                delay=300
            ),
            Tooltip(
                id="ilias_connect_help",
                element_selector="#ilias-connect-button",
                content="Connect your ILIAS account to access courses, share results, and collaborate with other researchers.",
                position="top",
                trigger="hover",
                delay=300
            ),
            Tooltip(
                id="save_analysis_help",
                element_selector="#save-analysis-button",
                content="Save your current analysis session. You can return to it later or share it with others.",
                position="bottom",
                trigger="hover",
                delay=300
            ),
            Tooltip(
                id="export_results_help",
                element_selector="#export-results-button",
                content="Export your analysis results in various formats including PDF, CSV, JSON, and Quarto reports.",
                position="bottom",
                trigger="hover",
                delay=300
            ),
            Tooltip(
                id="progress_indicator_help",
                element_selector="#onboarding-progress",
                content="This shows your progress through the onboarding tutorial. Click to resume or restart the tutorial.",
                position="right",
                trigger="hover",
                delay=300
            )
        ]
        
        return tooltips
    
    def generate_onboarding_tutorial(self) -> Dict[str, Any]:
        """Generate a complete onboarding tutorial structure"""
        tutorial = {
            "id": "nir_intelligence_onboarding",
            "title": "NIR Intelligence Platform Onboarding",
            "description": "Complete onboarding tutorial for new users of the NIR Intelligence Platform",
            "estimated_duration": "15-20 minutes",
            "steps": [],
            "completion_reward": "Access to advanced features and community recognition",
            "prerequisites": [],
            "learning_objectives": [
                "Understand the platform's main features and capabilities",
                "Learn how to upload and analyze spectral data",
                "Discover the federated learning system and privacy features",
                "Explore ILIAS integration for collaboration and learning",
                "Gain confidence in using the platform independently"
            ]
        }
        
        # Add steps from our onboarding steps
        for step_id, step in sorted(self.onboarding_steps.items(), key=lambda x: x[1].order):
            tutorial["steps"].append({
                "id": step.id,
                "title": step.title,
                "description": step.description,
                "target_element": step.target_element,
                "position": step.position,
                "required": step.required,
                "order": step.order,
                "estimated_time": "2-3 minutes",
                "interactive": True,
                "completion_criteria": "User performs the described action or clicks 'Next'"
            })
        
        return tutorial
    
    def generate_help_system(self) -> Dict[str, Any]:
        """Generate a complete help system structure"""
        help_system = {
            "id": "nir_intelligence_help",
            "title": "NIR Intelligence Help System",
            "description": "Comprehensive help system for the NIR Intelligence Platform",
            "categories": {},
            "search_enabled": True,
            "contextual_help": True,
            "feedback_enabled": True
        }
        
        # Organize help topics by category
        for topic_id, topic in self.help_topics.items():
            if topic.category not in help_system["categories"]:
                help_system["categories"][topic.category] = {
                    "id": topic.category,
                    "title": topic.category.replace("_", " ").title(),
                    "description": f"Help topics related to {topic.category}",
                    "topics": []
                }
            
            help_system["categories"][topic.category]["topics"].append({
                "id": topic.id,
                "title": topic.title,
                "content": topic.content,
                "tags": topic.tags,
                "related_features": topic.related_features
            })
        
        # Add quick start guide
        help_system["quick_start"] = {
            "title": "Quick Start Guide",
            "steps": [
                {
                    "step": 1,
                    "title": "Upload Your Data",
                    "description": "Start by uploading your spectral data files. We support WAV, MP3, PNG, JPG, CSV, and more.",
                    "action": "Click the 'Upload' button and select your files",
                    "time_estimate": "2 minutes"
                },
                {
                    "step": 2,
                    "title": "Select Analysis Type",
                    "description": "Choose what kind of analysis you want to perform on your data.",
                    "action": "Select from the available analysis options",
                    "time_estimate": "1 minute"
                },
                {
                    "step": 3,
                    "title": "Review Results",
                    "description": "Examine the analysis results, including spectral data, metadata quality, and recommendations.",
                    "action": "Scroll through the results and explore the visualizations",
                    "time_estimate": "5-10 minutes"
                },
                {
                    "step": 4,
                    "title": "Save and Share",
                    "description": "Save your analysis and optionally share it with the community or your ILIAS courses.",
                    "action": "Click 'Save' and choose your sharing preferences",
                    "time_estimate": "2 minutes"
                }
            ]
        }
        
        # Add FAQ section
        help_system["faq"] = {
            "title": "Frequently Asked Questions",
            "questions": [
                {
                    "question": "What file formats are supported?",
                    "answer": "We support a wide range of formats including WAV, MP3, FLAC (audio), PNG, JPG, TIFF, BMP (images), CSV, JSON, XML, TXT (data). For best results, use uncompressed formats like WAV, FLAC, PNG, or TIFF.",
                    "category": "data_formats",
                    "tags": ["formats", "upload", "files"]
                },
                {
                    "question": "Is my data private and secure?",
                    "answer": "Yes, your data privacy is our top priority. All data processing happens locally on your system. When you choose to participate in federated learning, only model improvements (not your raw data) are shared, and all communications are encrypted.",
                    "category": "privacy",
                    "tags": ["privacy", "security", "data"]
                },
                {
                    "question": "Do I need special equipment?",
                    "answer": "No, you can use any type of spectrometer, including DIY devices. Our system is designed to work with data from professional spectrometers as well as affordable DIY solutions. We provide special calibration profiles for popular DIY designs.",
                    "category": "equipment",
                    "tags": ["spectrometer", "DIY", "equipment"]
                },
                {
                    "question": "How accurate are the analysis results?",
                    "answer": "Our analysis algorithms are continuously improved through federated learning. The accuracy depends on the quality of your input data and the type of analysis. We provide confidence scores with all results to help you assess reliability.",
                    "category": "analysis",
                    "tags": ["accuracy", "results", "analysis"]
                },
                {
                    "question": "Can I use this for commercial purposes?",
                    "answer": "NIR Intelligence is designed for open science and educational purposes. For commercial use, please contact us to discuss licensing options. The platform is free for academic and non-commercial research use.",
                    "category": "licensing",
                    "tags": ["commercial", "license", "usage"]
                }
            ]
        }
        
        return help_system
    
    def generate_tooltip_system(self) -> Dict[str, Any]:
        """Generate a complete tooltip system structure"""
        tooltip_system = {
            "id": "nir_intelligence_tooltips",
            "title": "Contextual Tooltip System",
            "description": "Context-sensitive help tooltips for the NIR Intelligence Platform",
            "tooltips": [],
            "settings": {
                "default_position": "top",
                "default_trigger": "hover",
                "default_delay": 300,
                "animation": "fade",
                "show_arrows": True,
                "max_width": "300px",
                "theme": "dark"
            }
        }
        
        # Add tooltips
        for tooltip_id, tooltip in self.tooltips.items():
            tooltip_system["tooltips"].append({
                "id": tooltip.id,
                "element_selector": tooltip.element_selector,
                "content": tooltip.content,
                "position": tooltip.position,
                "trigger": tooltip.trigger,
                "delay": tooltip.delay
            })
        
        return tooltip_system
    
    def generate_javascript_files(self) -> Dict[str, str]:
        """Generate JavaScript files for onboarding and help functionality"""
        files = {}
        
        # Onboarding JavaScript
        files['onboarding.js'] = '''// NIR Intelligence Onboarding System
class OnboardingTutorial {
    constructor(options = {}) {
        this.steps = options.steps || [];
        this.currentStep = 0;
        this.completedSteps = new Set();
        this.isActive = false;
        this.overlay = null;
        this.highlightElement = null;
        
        this.settings = {
            overlayColor: 'rgba(0, 0, 0, 0.7)',
            highlightColor: '#006699',
            highlightOpacity: 0.3,
            stepPadding: 20,
            animationDuration: 300,
            ...options.settings
        };
        
        this.init();
    }
    
    init() {
        // Create overlay element
        this.overlay = document.createElement('div');
        this.overlay.className = 'onboarding-overlay';
        this.overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: ${this.settings.overlayColor};
            z-index: 9999;
            display: none;
        `;
        document.body.appendChild(this.overlay);
        
        // Create step container
        this.stepContainer = document.createElement('div');
        this.stepContainer.className = 'onboarding-step-container';
        this.stepContainer.style.cssText = `
            position: fixed;
            background: white;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            padding: 20px;
            max-width: 400px;
            z-index: 10000;
            display: none;
        `;
        document.body.appendChild(this.stepContainer);
        
        // Add step navigation
        this.stepContainer.innerHTML = `
            <div class="onboarding-step-header">
                <h3 class="onboarding-step-title"></h3>
                <button class="onboarding-close" onclick="onboarding.close()">&times;</button>
            </div>
            <div class="onboarding-step-content"></div>
            <div class="onboarding-step-footer">
                <span class="onboarding-step-counter"></span>
                <div class="onboarding-step-buttons">
                    <button class="onboarding-prev" onclick="onboarding.prev()">Back</button>
                    <button class="onboarding-next" onclick="onboarding.next()">Next</button>
                    <button class="onboarding-skip" onclick="onboarding.skip()">Skip</button>
                </div>
            </div>
        `;
        
        // Style the elements
        this.styleElements();
        
        // Add event listeners
        document.addEventListener('keydown', (e) => {
            if (!this.isActive) return;
            
            if (e.key === 'Escape') {
                this.close();
            } else if (e.key === 'ArrowLeft') {
                this.prev();
            } else if (e.key === 'ArrowRight') {
                this.next();
            }
        });
    }
    
    styleElements() {
        const style = document.createElement('style');
        style.textContent = `
            .onboarding-overlay {
                transition: opacity ${this.settings.animationDuration}ms ease;
            }
            .onboarding-overlay.active {
                display: block;
                opacity: 1;
            }
            .onboarding-step-container {
                transition: all ${this.settings.animationDuration}ms ease;
            }
            .onboarding-step-container.active {
                display: block;
            }
            .onboarding-step-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
            }
            .onboarding-step-title {
                margin: 0;
                color: #006699;
                font-size: 1.2rem;
            }
            .onboarding-close {
                background: none;
                border: none;
                font-size: 1.5rem;
                cursor: pointer;
                color: #666;
            }
            .onboarding-close:hover {
                color: #000;
            }
            .onboarding-step-content {
                margin-bottom: 20px;
                line-height: 1.6;
            }
            .onboarding-step-footer {
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .onboarding-step-counter {
                color: #666;
                font-size: 0.9rem;
            }
            .onboarding-step-buttons button {
                margin-left: 10px;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 0.9rem;
            }
            .onboarding-prev {
                background-color: #f0f0f0;
            }
            .onboarding-next {
                background-color: #006699;
                color: white;
            }
            .onboarding-skip {
                background-color: #ccc;
                color: #333;
            }
            .onboarding-highlight {
                position: relative;
                z-index: 10001;
            }
            .onboarding-highlight::after {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background-color: ${this.settings.highlightColor};
                opacity: ${this.settings.highlightOpacity};
                border-radius: 4px;
                pointer-events: none;
                animation: onboardingPulse 2s infinite;
            }
            @keyframes onboardingPulse {
                0%, 100% { opacity: ${this.settings.highlightOpacity}; }
                50% { opacity: ${this.settings.highlightOpacity * 1.5}; }
            }
        `;
        document.head.appendChild(style);
    }
    
    start() {
        if (this.steps.length === 0) {
            console.warn('No onboarding steps defined');
            return;
        }
        
        this.isActive = true;
        this.currentStep = 0;
        this.completedSteps.clear();
        
        this.showCurrentStep();
        this.overlay.classList.add('active');
        
        // Trigger start event
        document.dispatchEvent(new CustomEvent('onboarding:start'));
    }
    
    showCurrentStep() {
        const step = this.steps[this.currentStep];
        if (!step) return;
        
        // Update step content
        this.stepContainer.querySelector('.onboarding-step-title').textContent = step.title;
        this.stepContainer.querySelector('.onboarding-step-content').innerHTML = step.description;
        this.stepContainer.querySelector('.onboarding-step-counter').textContent = 
            `${this.currentStep + 1} of ${this.steps.length}`;
        
        // Position the step container
        this.positionStepContainer(step);
        
        // Highlight target element
        this.highlightTargetElement(step);
        
        // Show container
        this.stepContainer.classList.add('active');
        
        // Update buttons
        this.updateButtons();
        
        // Trigger step show event
        document.dispatchEvent(new CustomEvent('onboarding:stepShow', {
            detail: { step: step, stepIndex: this.currentStep }
        }));
    }
    
    positionStepContainer(step) {
        if (!step.target_element) {
            // Center if no target element
            this.stepContainer.style.top = '50%';
            this.stepContainer.style.left = '50%';
            this.stepContainer.style.transform = 'translate(-50%, -50%)';
            return;
        }
        
        const target = document.querySelector(step.target_element);
        if (!target) {
            this.stepContainer.style.top = '50%';
            this.stepContainer.style.left = '50%';
            this.stepContainer.style.transform = 'translate(-50%, -50%)';
            return;
        }
        
        const rect = target.getBoundingClientRect();
        const containerHeight = this.stepContainer.offsetHeight || 200;
        
        let top, left;
        
        switch (step.position) {
            case 'top':
                top = rect.top - containerHeight - this.settings.stepPadding;
                left = rect.left + (rect.width / 2) - (this.stepContainer.offsetWidth / 2);
                break;
            case 'bottom':
                top = rect.bottom + this.settings.stepPadding;
                left = rect.left + (rect.width / 2) - (this.stepContainer.offsetWidth / 2);
                break;
            case 'left':
                top = rect.top + (rect.height / 2) - (containerHeight / 2);
                left = rect.left - this.stepContainer.offsetWidth - this.settings.stepPadding;
                break;
            case 'right':
                top = rect.top + (rect.height / 2) - (containerHeight / 2);
                left = rect.right + this.settings.stepPadding;
                break;
            default:
                top = '50%';
                left = '50%';
                this.stepContainer.style.transform = 'translate(-50%, -50%)';
        }
        
        // Ensure the container stays within viewport
        const viewportHeight = window.innerHeight;
        const viewportWidth = window.innerWidth;
        
        if (top < 0) top = this.settings.stepPadding;
        if (left < 0) left = this.settings.stepPadding;
        if (top + containerHeight > viewportHeight) 
            top = viewportHeight - containerHeight - this.settings.stepPadding;
        if (left + this.stepContainer.offsetWidth > viewportWidth) 
            left = viewportWidth - this.stepContainer.offsetWidth - this.settings.stepPadding;
        
        this.stepContainer.style.top = `${top}px`;
        this.stepContainer.style.left = `${left}px`;
        this.stepContainer.style.transform = 'none';
    }
    
    highlightTargetElement(step) {
        // Remove previous highlights
        const existingHighlights = document.querySelectorAll('.onboarding-highlight');
        existingHighlights.forEach(el => el.classList.remove('onboarding-highlight'));
        
        if (!step.target_element) return;
        
        const target = document.querySelector(step.target_element);
        if (target) {
            target.classList.add('onboarding-highlight');
            this.highlightElement = target;
        }
    }
    
    updateButtons() {
        const prevBtn = this.stepContainer.querySelector('.onboarding-prev');
        const nextBtn = this.stepContainer.querySelector('.onboarding-next');
        
        prevBtn.disabled = this.currentStep === 0;
        nextBtn.textContent = this.currentStep === this.steps.length - 1 ? 'Finish' : 'Next';
    }
    
    next() {
        if (this.currentStep < this.steps.length - 1) {
            this.currentStep++;
            this.completedSteps.add(this.currentStep - 1);
            this.showCurrentStep();
        } else {
            this.complete();
        }
    }
    
    prev() {
        if (this.currentStep > 0) {
            this.currentStep--;
            this.showCurrentStep();
        }
    }
    
    skip() {
        this.completedSteps.add(this.currentStep);
        this.next();
    }
    
    complete() {
        this.completedSteps.add(this.currentStep);
        this.close();
        
        // Trigger completion event
        document.dispatchEvent(new CustomEvent('onboarding:complete', {
            detail: { completedSteps: Array.from(this.completedSteps) }
        }));
    }
    
    close() {
        this.isActive = false;
        this.overlay.classList.remove('active');
        this.stepContainer.classList.remove('active');
        
        // Remove highlight
        if (this.highlightElement) {
            this.highlightElement.classList.remove('onboarding-highlight');
            this.highlightElement = null;
        }
        
        // Trigger close event
        document.dispatchEvent(new CustomEvent('onboarding:close'));
    }
    
    addSteps(steps) {
        this.steps = [...this.steps, ...steps];
        this.steps.sort((a, b) => a.order - b.order);
    }
    
    setSteps(steps) {
        this.steps = steps.sort((a, b) => a.order - b.order);
    }
}

// Initialize onboarding
let onboarding = new OnboardingTutorial({
    steps: [] // Steps will be added dynamically
});

// Function to start onboarding
action startOnboarding = function(steps) {
    onboarding.setSteps(steps);
    onboarding.start();
};

// Function to check onboarding status
action checkOnboardingStatus = function() {
    return {
        isActive: onboarding.isActive,
        currentStep: onboarding.currentStep,
        completedSteps: Array.from(onboarding.completedSteps),
        totalSteps: onboarding.steps.length
    };
};

// Function to resume onboarding
action resumeOnboarding = function() {
    if (onboarding.completedSteps.size > 0) {
        // Start from the first incomplete step
        const firstIncomplete = Array.from({ length: onboarding.steps.length }, (_, i) => i)
            .find(i => !onboarding.completedSteps.has(i)) || 0;
        onboarding.currentStep = firstIncomplete;
        onboarding.start();
    } else {
        onboarding.start();
    }
};

// Listen for DOM content loaded
document.addEventListener('DOMContentLoaded', function() {
    // Check if we should auto-start onboarding
    if (window.location.search.includes('onboarding=true')) {
        // Fetch steps from server
        fetch('/api/onboarding/steps/')
            .then(response => response.json())
            .then(steps => {
                startOnboarding(steps);
            })
            .catch(error => {
                console.error('Failed to load onboarding steps:', error);
            });
    }
});
'''
        
        # Help system JavaScript
        files['help.js'] = '''// NIR Intelligence Help System
class HelpSystem {
    constructor(options = {}) {
        this.helpTopics = options.topics || [];
        this.categories = options.categories || {};
        this.searchIndex = [];
        this.helpModal = null;
        this.searchResults = [];
        
        this.settings = {
            modalId: 'help-modal',
            triggerClass: 'help-trigger',
            searchMinLength: 2,
            resultsPerPage: 10,
            ...options.settings
        };
        
        this.init();
    }
    
    init() {
        // Create help modal
        this.createHelpModal();
        
        // Index help topics for search
        this.buildSearchIndex();
        
        // Setup event listeners
        this.setupEventListeners();
    }
    
    createHelpModal() {
        this.helpModal = document.createElement('div');
        this.helpModal.id = this.settings.modalId;
        this.helpModal.className = 'help-modal';
        this.helpModal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: rgba(0, 0, 0, 0.5);
            z-index: 10000;
            display: none;
            overflow-y: auto;
        `;
        
        this.helpModal.innerHTML = `
            <div class="help-modal-content" style="
                background: white;
                max-width: 800px;
                margin: 50px auto;
                border-radius: 8px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
                padding: 20px;
            ">
                <div class="help-modal-header" style="
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 20px;
                    border-bottom: 1px solid #eee;
                    padding-bottom: 15px;
                ">
                    <h2 style="margin: 0; color: #006699;">Help Center</h2>
                    <button class="help-close" onclick="helpSystem.close()" style="
                        background: none;
                        border: none;
                        font-size: 1.5rem;
                        cursor: pointer;
                    ">&times;</button>
                </div>
                
                <div class="help-search" style="margin-bottom: 20px;">
                    <input type="text" id="help-search-input" placeholder="Search help topics..." style="
                        width: 100%;
                        padding: 10px;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        font-size: 1rem;
                    ">
                    <div id="help-search-results" style="margin-top: 10px;"></div>
                </div>
                
                <div class="help-content">
                    <div class="help-categories" id="help-categories" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px;"></div>
                    <div class="help-topics" id="help-topics"></div>
                </div>
                
                <div class="help-quick-start" style="margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 4px;">
                    <h3 style="margin-top: 0; color: #006699;">Quick Start Guide</h3>
                    <div id="help-quick-start-steps"></div>
                </div>
            </div>
        `;
        
        document.body.appendChild(this.helpModal);
        
        // Add styles
        this.addStyles();
    }
    
    addStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .help-modal.active {
                display: block;
            }
            .help-category-card {
                background: white;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 15px;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            .help-category-card:hover {
                background: #f8f9fa;
                border-color: #006699;
            }
            .help-category-card h4 {
                margin: 0 0 10px 0;
                color: #006699;
            }
            .help-topic {
                background: white;
                border: 1px solid #eee;
                border-radius: 4px;
                padding: 15px;
                margin-bottom: 10px;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            .help-topic:hover {
                background: #f8f9fa;
                border-color: #006699;
            }
            .help-topic h4 {
                margin: 0 0 10px 0;
                color: #006699;
            }
            .help-topic-content {
                display: none;
                margin-top: 15px;
                padding-top: 15px;
                border-top: 1px solid #eee;
            }
            .help-topic.active .help-topic-content {
                display: block;
            }
            .help-quick-start-step {
                margin-bottom: 15px;
                padding: 10px;
                background: white;
                border-radius: 4px;
                border-left: 4px solid #006699;
            }
            .help-quick-start-step:last-child {
                margin-bottom: 0;
            }
            .help-search-result {
                padding: 10px;
                border-bottom: 1px solid #eee;
                cursor: pointer;
            }
            .help-search-result:hover {
                background: #f8f9fa;
            }
            .help-search-result:last-child {
                border-bottom: none;
            }
        `;
        document.head.appendChild(style);
    }
    
    buildSearchIndex() {
        this.searchIndex = [];
        
        // Index topics
        this.helpTopics.forEach(topic => {
            const words = [
                ...topic.title.toLowerCase().split(/\\s+/),
                ...topic.content.toLowerCase().split(/\\s+/),
                ...topic.tags.map(tag => tag.toLowerCase())
            ];
            
            words.forEach(word => {
                if (word.length >= this.settings.searchMinLength) {
                    this.searchIndex.push({
                        word: word,
                        topicId: topic.id,
                        title: topic.title,
                        category: topic.category
                    });
                }
            });
        });
        
        // Index categories
        Object.values(this.categories).forEach(category => {
            const words = category.title.toLowerCase().split(/\\s+/);
            words.forEach(word => {
                if (word.length >= this.settings.searchMinLength) {
                    this.searchIndex.push({
                        word: word,
                        categoryId: category.id,
                        title: category.title,
                        type: 'category'
                    });
                }
            });
        });
    }
    
    setupEventListeners() {
        // Search input
        const searchInput = document.getElementById('help-search-input');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.performSearch(e.target.value);
            });
        }
        
        // Contextual help triggers
        document.querySelectorAll(`.${this.settings.triggerClass}`).forEach(trigger => {
            trigger.addEventListener('click', (e) => {
                e.preventDefault();
                const topicId = trigger.getAttribute('data-help-topic');
                if (topicId) {
                    this.showTopic(topicId);
                } else {
                    this.open();
                }
            });
        });
    }
    
    open() {
        this.helpModal.classList.add('active');
        this.renderCategories();
        this.renderQuickStart();
        
        // Trigger open event
        document.dispatchEvent(new CustomEvent('help:open'));
    }
    
    close() {
        this.helpModal.classList.remove('active');
        
        // Clear search
        const searchInput = document.getElementById('help-search-input');
        if (searchInput) {
            searchInput.value = '';
        }
        document.getElementById('help-search-results').innerHTML = '';
        
        // Trigger close event
        document.dispatchEvent(new CustomEvent('help:close'));
    }
    
    renderCategories() {
        const container = document.getElementById('help-categories');
        if (!container) return;
        
        container.innerHTML = '';
        
        Object.values(this.categories).forEach(category => {
            const card = document.createElement('div');
            card.className = 'help-category-card';
            card.innerHTML = `
                <h4>${category.title}</h4>
                <p style="margin: 0; color: #666; font-size: 0.9rem;">${category.topics.length} topics</p>
            `;
            card.addEventListener('click', () => this.showCategory(category.id));
            container.appendChild(card);
        });
    }
    
    showCategory(categoryId) {
        const category = this.categories[categoryId];
        if (!category) return;
        
        const container = document.getElementById('help-topics');
        if (!container) return;
        
        container.innerHTML = `
            <h3 style="margin-bottom: 15px;">${category.title}</h3>
            <p style="color: #666; margin-bottom: 20px;">${category.description}</p>
        `;
        
        category.topics.forEach(topic => {
            const topicElement = document.createElement('div');
            topicElement.className = 'help-topic';
            topicElement.innerHTML = `
                <h4>${topic.title}</h4>
                <p style="color: #666; font-size: 0.9rem; margin: 0;">
                    ${topic.tags.join(', ')}
                </p>
                <div class="help-topic-content">
                    <div style="padding: 10px; background: #f8f9fa; border-radius: 4px;">
                        ${topic.content}
                    </div>
                    ${topic.related_features.length > 0 ? `
                        <div style="margin-top: 10px;">
                            <strong>Related Features:</strong> ${topic.related_features.join(', ')}
                        </div>
                    ` : ''}
                </div>
            `;
            topicElement.addEventListener('click', () => {
                topicElement.classList.toggle('active');
            });
            container.appendChild(topicElement);
        });
    }
    
    showTopic(topicId) {
        const topic = this.helpTopics.find(t => t.id === topicId);
        if (!topic) return;
        
        const container = document.getElementById('help-topics');
        if (!container) return;
        
        container.innerHTML = `
            <div class="help-topic active">
                <h2 style="margin-bottom: 15px;">${topic.title}</h2>
                <div class="help-topic-content" style="display: block;">
                    <div style="padding: 15px; background: #f8f9fa; border-radius: 4px; margin-bottom: 15px;">
                        ${topic.content}
                    </div>
                    ${topic.tags.length > 0 ? `
                        <div style="margin-bottom: 15px;">
                            <strong>Tags:</strong> ${topic.tags.join(', ')}
                        </div>
                    ` : ''}
                    ${topic.related_features.length > 0 ? `
                        <div style="margin-bottom: 15px;">
                            <strong>Related Features:</strong> ${topic.related_features.join(', ')}
                        </div>
                    ` : ''}
                    <button onclick="helpSystem.backToCategories()" style="
                        padding: 8px 16px;
                        background: #006699;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                    ">Back to Categories</button>
                </div>
            </div>
        `;
    }
    
    backToCategories() {
        this.renderCategories();
        document.getElementById('help-topics').innerHTML = '';
    }
    
    renderQuickStart() {
        const container = document.getElementById('help-quick-start-steps');
        if (!container) return;
        
        // This would be populated with actual quick start steps
        container.innerHTML = '<p>Complete the onboarding tutorial for a guided tour, or explore the help topics above.</p>';
    }
    
    performSearch(query) {
        if (query.length < this.settings.searchMinLength) {
            document.getElementById('help-search-results').innerHTML = '';
            return;
        }
        
        const resultsContainer = document.getElementById('help-search-results');
        if (!resultsContainer) return;
        
        const queryLower = query.toLowerCase();
        
        // Search in index
        const matches = this.searchIndex.filter(item => 
            item.word.includes(queryLower) || 
            item.title.toLowerCase().includes(queryLower)
        );
        
        // Get unique results
        const uniqueResults = [];
        const seen = new Set();
        
        matches.forEach(match => {
            const key = match.topicId || match.categoryId;
            if (!seen.has(key)) {
                seen.add(key);
                uniqueResults.push(match);
            }
        });
        
        // Display results
        if (uniqueResults.length === 0) {
            resultsContainer.innerHTML = '<div class="help-search-result">No results found</div>';
            return;
        }
        
        resultsContainer.innerHTML = '';
        uniqueResults.slice(0, this.settings.resultsPerPage).forEach(result => {
            const resultElement = document.createElement('div');
            resultElement.className = 'help-search-result';
            resultElement.innerHTML = `
                <strong>${result.title}</strong>
                <span style="color: #666; font-size: 0.9rem; margin-left: 10px;">
                    ${result.category || result.type || ''}
                </span>
            `;
            resultElement.addEventListener('click', () => {
                if (result.topicId) {
                    this.showTopic(result.topicId);
                } else if (result.categoryId) {
                    this.showCategory(result.categoryId);
                }
                resultsContainer.innerHTML = '';
                document.getElementById('help-search-input').value = '';
            });
            resultsContainer.appendChild(resultElement);
        });
    }
    
    setHelpData(data) {
        this.helpTopics = data.topics || this.helpTopics;
        this.categories = data.categories || this.categories;
        this.buildSearchIndex();
    }
}

// Initialize help system
let helpSystem = new HelpSystem({
    topics: [], // Will be populated from server
    categories: {},
    settings: {
        modalId: 'nir-help-modal',
        triggerClass: 'help-trigger'
    }
});

// Function to open help
action openHelp = function(topicId = null) {
    if (topicId) {
        helpSystem.open();
        helpSystem.showTopic(topicId);
    } else {
        helpSystem.open();
    }
};

// Function to search help
action searchHelp = function(query) {
    helpSystem.performSearch(query);
};

// Function to load help data from server
action loadHelpData = function() {
    fetch('/api/help/topics/')
        .then(response => response.json())
        .then(data => {
            helpSystem.setHelpData(data);
        })
        .catch(error => {
            console.error('Failed to load help data:', error);
        });
};

// Load help data when DOM is ready
document.addEventListener('DOMContentLoaded', loadHelpData);
'''
        
        # Tooltip JavaScript
        files['tooltips.js'] = '''// NIR Intelligence Tooltip System
class TooltipSystem {
    constructor(options = {}) {
        this.tooltips = options.tooltips || [];
        this.tooltipElements = new Map();
        this.activeTooltips = new Set();
        
        this.settings = {
            defaultPosition: 'top',
            defaultTrigger: 'hover',
            defaultDelay: 300,
            animationDuration: 200,
            maxWidth: '300px',
            theme: 'dark',
            ...options.settings
        };
        
        this.init();
    }
    
    init() {
        // Create tooltip container
        this.tooltipContainer = document.createElement('div');
        this.tooltipContainer.className = 'tooltip-system-container';
        this.tooltipContainer.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            pointer-events: none;
            z-index: 9999;
        `;
        document.body.appendChild(this.tooltipContainer);
        
        // Add styles
        this.addStyles();
        
        // Initialize tooltips
        this.initializeTooltips();
    }
    
    addStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .tooltip-system-tooltip {
                position: absolute;
                background: ${this.settings.theme === 'dark' ? '#333' : '#fff'};
                color: ${this.settings.theme === 'dark' ? '#fff' : '#333'};
                padding: 8px 12px;
                border-radius: 4px;
                font-size: 0.85rem;
                line-height: 1.4;
                max-width: ${this.settings.maxWidth};
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
                opacity: 0;
                transition: opacity ${this.settings.animationDuration}ms ease;
                pointer-events: auto;
                z-index: 10000;
            }
            
            .tooltip-system-tooltip::after {
                content: '';
                position: absolute;
                width: 8px;
                height: 8px;
                background: ${this.settings.theme === 'dark' ? '#333' : '#fff'};
                transform: rotate(45deg);
            }
            
            .tooltip-system-tooltip.active {
                opacity: 1;
            }
            
            .tooltip-system-tooltip.top {
                transform: translateY(-8px);
            }
            .tooltip-system-tooltip.top::after {
                top: 100%;
                left: 50%;
                margin-left: -4px;
            }
            
            .tooltip-system-tooltip.bottom {
                transform: translateY(8px);
            }
            .tooltip-system-tooltip.bottom::after {
                bottom: 100%;
                left: 50%;
                margin-left: -4px;
            }
            
            .tooltip-system-tooltip.left {
                transform: translateX(-8px);
            }
            .tooltip-system-tooltip.left::after {
                left: 100%;
                top: 50%;
                margin-top: -4px;
            }
            
            .tooltip-system-tooltip.right {
                transform: translateX(8px);
            }
            .tooltip-system-tooltip.right::after {
                right: 100%;
                top: 50%;
                margin-top: -4px;
            }
        `;
        document.head.appendChild(style);
    }
    
    initializeTooltips() {
        this.tooltips.forEach(tooltip => {
            this.createTooltip(tooltip);
        });
    }
    
    createTooltip(tooltip) {
        const elements = document.querySelectorAll(tooltip.element_selector);
        
        elements.forEach(element => {
            const tooltipElement = document.createElement('div');
            tooltipElement.className = 'tooltip-system-tooltip';
            tooltipElement.textContent = tooltip.content;
            tooltipElement.style.display = 'none';
            
            // Store reference
            this.tooltipElements.set(element, tooltipElement);
            
            // Set position
            tooltipElement.classList.add(tooltip.position || this.settings.defaultPosition);
            
            // Add to container
            this.tooltipContainer.appendChild(tooltipElement);
            
            // Setup trigger
            this.setupTrigger(element, tooltipElement, tooltip.trigger || this.settings.defaultTrigger, tooltip.delay || this.settings.defaultDelay);
        });
    }
    
    setupTrigger(element, tooltipElement, trigger, delay) {
        let timeoutId = null;
        
        switch (trigger) {
            case 'hover':
                element.addEventListener('mouseenter', () => {
                    timeoutId = setTimeout(() => this.showTooltip(element, tooltipElement), delay);
                });
                element.addEventListener('mouseleave', () => {
                    clearTimeout(timeoutId);
                    this.hideTooltip(element, tooltipElement);
                });
                break;
                
            case 'click':
                element.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    if (this.activeTooltips.has(element)) {
                        this.hideTooltip(element, tooltipElement);
                    } else {
                        this.showTooltip(element, tooltipElement);
                    }
                });
                break;
                
            case 'focus':
                element.addEventListener('focus', () => {
                    this.showTooltip(element, tooltipElement);
                });
                element.addEventListener('blur', () => {
                    this.hideTooltip(element, tooltipElement);
                });
                break;
        }
        
        // Hide on scroll
        window.addEventListener('scroll', () => {
            this.hideTooltip(element, tooltipElement);
        });
    }
    
    showTooltip(element, tooltipElement) {
        if (this.activeTooltips.has(element)) return;
        
        this.activeTooltips.add(element);
        tooltipElement.style.display = 'block';
        
        // Position the tooltip
        this.positionTooltip(element, tooltipElement);
        
        // Add active class after a small delay to allow positioning
        setTimeout(() => {
            tooltipElement.classList.add('active');
        }, 10);
    }
    
    hideTooltip(element, tooltipElement) {
        if (!this.activeTooltips.has(element)) return;
        
        this.activeTooltips.delete(element);
        tooltipElement.classList.remove('active');
        
        // Hide after transition completes
        setTimeout(() => {
            if (!this.activeTooltips.has(element)) {
                tooltipElement.style.display = 'none';
            }
        }, this.settings.animationDuration);
    }
    
    positionTooltip(element, tooltipElement) {
        const rect = element.getBoundingClientRect();
        const tooltipRect = tooltipElement.getBoundingClientRect();
        const position = Array.from(tooltipElement.classList).find(cls => 
            ['top', 'bottom', 'left', 'right'].includes(cls)
        ) || this.settings.defaultPosition;
        
        let top, left;
        
        switch (position) {
            case 'top':
                top = rect.top - tooltipRect.height - 8;
                left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
                break;
            case 'bottom':
                top = rect.bottom + 8;
                left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
                break;
            case 'left':
                top = rect.top + (rect.height / 2) - (tooltipRect.height / 2);
                left = rect.left - tooltipRect.width - 8;
                break;
            case 'right':
                top = rect.top + (rect.height / 2) - (tooltipRect.height / 2);
                left = rect.right + 8;
                break;
        }
        
        // Ensure tooltip stays within viewport
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        
        if (left < 0) left = 4;
        if (top < 0) top = 4;
        if (left + tooltipRect.width > viewportWidth) 
            left = viewportWidth - tooltipRect.width - 4;
        if (top + tooltipRect.height > viewportHeight) 
            top = viewportHeight - tooltipRect.height - 4;
        
        tooltipElement.style.top = `${top}px`;
        tooltipElement.style.left = `${left}px`;
    }
    
    addTooltip(tooltip) {
        this.tooltips.push(tooltip);
        this.createTooltip(tooltip);
    }
    
    removeTooltip(elementSelector) {
        // Remove from tooltips array
        this.tooltips = this.tooltips.filter(t => t.element_selector !== elementSelector);
        
        // Remove from DOM
        const elements = document.querySelectorAll(elementSelector);
        elements.forEach(element => {
            const tooltipElement = this.tooltipElements.get(element);
            if (tooltipElement) {
                this.tooltipContainer.removeChild(tooltipElement);
                this.tooltipElements.delete(element);
            }
        });
    }
    
    setTooltips(tooltips) {
        // Clear existing tooltips
        this.tooltipContainer.innerHTML = '';
        this.tooltipElements.clear();
        this.activeTooltips.clear();
        this.tooltips = [];
        
        // Add new tooltips
        this.tooltips = tooltips;
        this.initializeTooltips();
    }
}

// Initialize tooltip system
let tooltipSystem = new TooltipSystem({
    tooltips: [], // Will be populated from server
    settings: {
        defaultPosition: 'top',
        defaultTrigger: 'hover',
        defaultDelay: 300,
        theme: 'dark'
    }
});

// Function to load tooltips from server
action loadTooltips = function() {
    fetch('/api/tooltips/')
        .then(response => response.json())
        .then(data => {
            tooltipSystem.setTooltips(data.tooltips || []);
        })
        .catch(error => {
            console.error('Failed to load tooltips:', error);
        });
};

// Function to add a tooltip dynamically
action addTooltip = function(tooltip) {
    tooltipSystem.addTooltip(tooltip);
};

// Load tooltips when DOM is ready
document.addEventListener('DOMContentLoaded', loadTooltips);
'''
        
        return files
    
    def generate_progress_indicators(self) -> Dict[str, str]:
        """Generate HTML/CSS for progress indicators"""
        indicators = {}
        
        # Onboarding progress bar
        indicators['onboarding_progress.html'] = '''<!-- Onboarding Progress Indicator -->
<div id="onboarding-progress" class="onboarding-progress" style="
    position: fixed;
    bottom: 20px;
    right: 20px;
    z-index: 1000;
">
    <div class="progress-container" style="
        display: flex;
        align-items: center;
        gap: 10px;
        background: white;
        padding: 10px 15px;
        border-radius: 25px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
    ">
        <div class="progress-icon" style="
            width: 30px;
            height: 30px;
            background: #006699;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        ">i</div>
        <div class="progress-info">
            <div class="progress-text" style="font-size: 0.85rem; color: #666;">Onboarding Progress</div>
            <div class="progress-bar-container" style="width: 150px; height: 6px; background: #eee; border-radius: 3px; margin-top: 4px;">
                <div id="onboarding-progress-bar" class="progress-bar" style="
                    height: 100%;
                    background: #006699;
                    border-radius: 3px;
                    width: 0%;
                    transition: width 0.3s ease;
                "></div>
            </div>
        </div>
        <button onclick="resumeOnboarding()" class="progress-resume" style="
            background: none;
            border: none;
            color: #006699;
            cursor: pointer;
            font-size: 0.85rem;
            font-weight: 500;
        ">Resume</button>
    </div>
</div>

<style>
    .onboarding-progress:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }
    
    .progress-resume:hover {
        text-decoration: underline;
    }
</style>

<script>
    // Update progress based on user's onboarding status
    function updateOnboardingProgress() {
        fetch('/api/onboarding/progress/')
            .then(response => response.json())
            .then(data => {
                const progressBar = document.getElementById('onboarding-progress-bar');
                if (progressBar) {
                    progressBar.style.width = `${data.completion_percentage}%`;
                }
                
                // Update progress container visibility
                const progressContainer = document.querySelector('.progress-container');
                if (data.completion_percentage < 100) {
                    progressContainer.style.display = 'flex';
                } else {
                    progressContainer.style.display = 'none';
                }
            })
            .catch(error => {
                console.error('Failed to update onboarding progress:', error);
            });
    }
    
    // Check progress on page load
    document.addEventListener('DOMContentLoaded', updateOnboardingProgress);
    
    // Periodically check progress
    setInterval(updateOnboardingProgress, 30000);
</script>'''
        
        # Analysis progress indicator
        indicators['analysis_progress.html'] = '''<!-- Analysis Progress Indicator -->
<div id="analysis-progress" class="analysis-progress" style="
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    z-index: 10000;
    display: none;
">
    <div class="progress-overlay" style="
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(255, 255, 255, 0.8);
    "></div>
    <div class="progress-modal" style="
        background: white;
        padding: 30px;
        border-radius: 8px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        text-align: center;
        max-width: 400px;
        width: 90%;
    ">
        <h3 style="margin-top: 0; color: #006699;">Analyzing Your Data</h3>
        <p style="color: #666; margin-bottom: 20px;">Please wait while we process your spectral data...</p>
        
        <div class="progress-steps" style="display: flex; justify-content: space-between; margin-bottom: 20px;">
            <div class="progress-step active" style="text-align: center;">
                <div class="step-circle" style="width: 30px; height: 30px; border-radius: 50%; background: #006699; color: white; display: flex; align-items: center; justify-content: center; margin: 0 auto 5px;">1</div>
                <div class="step-label" style="font-size: 0.75rem; color: #666;">Uploading</div>
            </div>
            <div class="progress-step" style="text-align: center;">
                <div class="step-circle" style="width: 30px; height: 30px; border-radius: 50%; background: #eee; color: #666; display: flex; align-items: center; justify-content: center; margin: 0 auto 5px;">2</div>
                <div class="step-label" style="font-size: 0.75rem; color: #666;">Processing</div>
            </div>
            <div class="progress-step" style="text-align: center;">
                <div class="step-circle" style="width: 30px; height: 30px; border-radius: 50%; background: #eee; color: #666; display: flex; align-items: center; justify-content: center; margin: 0 auto 5px;">3</div>
                <div class="step-label" style="font-size: 0.75rem; color: #666;">Analyzing</div>
            </div>
            <div class="progress-step" style="text-align: center;">
                <div class="step-circle" style="width: 30px; height: 30px; border-radius: 50%; background: #eee; color: #666; display: flex; align-items: center; justify-content: center; margin: 0 auto 5px;">4</div>
                <div class="step-label" style="font-size: 0.75rem; color: #666;">Complete</div>
            </div>
        </div>
        
        <div class="progress-bar-container" style="width: 100%; height: 6px; background: #eee; border-radius: 3px; margin-bottom: 15px;">
            <div id="analysis-progress-bar" class="progress-bar" style="
                height: 100%;
                background: #006699;
                border-radius: 3px;
                width: 25%;
                transition: width 0.3s ease;
            "></div>
        </div>
        
        <div class="progress-percentage" id="analysis-progress-percentage" style="color: #666; font-size: 0.9rem;">25%</div>
        
        <div class="progress-message" id="analysis-progress-message" style="color: #666; font-size: 0.85rem; margin-top: 10px;">
            Uploading files...
        </div>
        
        <button onclick="cancelAnalysis()" class="progress-cancel" style="
            background: none;
            border: none;
            color: #666;
            cursor: pointer;
            font-size: 0.85rem;
            margin-top: 15px;
        ">Cancel</button>
    </div>
</div>

<style>
    .analysis-progress.active {
        display: block;
    }
    
    .progress-step.active .step-circle {
        background: #006699;
        color: white;
    }
    
    .progress-step.active .step-label {
        color: #006699;
        font-weight: 500;
    }
    
    .progress-step.completed .step-circle {
        background: #28A745;
        color: white;
    }
    
    .progress-cancel:hover {
        color: #dc3545;
        text-decoration: underline;
    }
</style>

<script>
    // Show progress indicator
    function showAnalysisProgress() {
        document.getElementById('analysis-progress').classList.add('active');
    }
    
    // Hide progress indicator
    function hideAnalysisProgress() {
        document.getElementById('analysis-progress').classList.remove('active');
    }
    
    // Update progress
    function updateAnalysisProgress(step, percentage, message) {
        const progressBar = document.getElementById('analysis-progress-bar');
        const percentageElement = document.getElementById('analysis-progress-percentage');
        const messageElement = document.getElementById('analysis-progress-message');
        
        if (progressBar) {
            progressBar.style.width = `${percentage}%`;
        }
        if (percentageElement) {
            percentageElement.textContent = `${percentage}%`;
        }
        if (messageElement) {
            messageElement.textContent = message;
        }
        
        // Update step indicators
        const steps = document.querySelectorAll('.progress-step');
        steps.forEach((stepElement, index) => {
            stepElement.classList.remove('active', 'completed');
            if (index < step - 1) {
                stepElement.classList.add('completed');
            } else if (index === step - 1) {
                stepElement.classList.add('active');
            }
        });
    }
    
    // Cancel analysis
    function cancelAnalysis() {
        if (confirm('Are you sure you want to cancel the analysis?')) {
            // Send cancel request to server
            fetch('/api/analysis/cancel/', { method: 'POST' })
                .then(() => {
                    hideAnalysisProgress();
                })
                .catch(error => {
                    console.error('Failed to cancel analysis:', error);
                });
        }
    }
    
    // Example usage:
    // showAnalysisProgress();
    // updateAnalysisProgress(2, 50, 'Processing spectral data...');
    // updateAnalysisProgress(3, 75, 'Analyzing metadata...');
    // updateAnalysisProgress(4, 100, 'Finalizing results...');
    // hideAnalysisProgress();
</script>'''
        
        return indicators
    
    def create_output_directory(self) -> bool:
        """Create the output directory structure"""
        try:
            base_dir = Path(self.output_dir)
            base_dir.mkdir(parents=True, exist_ok=True)
            
            # Create subdirectories
            (base_dir / "js").mkdir(parents=True, exist_ok=True)
            (base_dir / "css").mkdir(parents=True, exist_ok=True)
            (base_dir / "templates").mkdir(parents=True, exist_ok=True)
            
            return True
        except Exception as e:
            self.logger.error(f"Error creating output directory: {str(e)}")
            return False
    
    def save_javascript_files(self, js_files: Dict[str, str]) -> List[str]:
        """Save JavaScript files to the output directory"""
        saved_files = []
        try:
            base_dir = Path(self.output_dir) / "js"
            base_dir.mkdir(parents=True, exist_ok=True)
            
            for filename, content in js_files.items():
                file_path = base_dir / filename
                with open(file_path, 'w') as f:
                    f.write(content)
                saved_files.append(str(file_path))
                self.logger.info(f"Saved JavaScript file: {file_path}")
            
            return saved_files
            
        except Exception as e:
            self.logger.error(f"Error saving JavaScript files: {str(e)}")
            self.stats['errors'] += 1
            return saved_files
    
    def save_template_files(self, template_files: Dict[str, str]) -> List[str]:
        """Save template files to the output directory"""
        saved_files = []
        try:
            base_dir = Path(self.output_dir) / "templates"
            base_dir.mkdir(parents=True, exist_ok=True)
            
            for filename, content in template_files.items():
                file_path = base_dir / filename
                with open(file_path, 'w') as f:
                    f.write(content)
                saved_files.append(str(file_path))
                self.logger.info(f"Saved template file: {file_path}")
            
            return saved_files
            
        except Exception as e:
            self.logger.error(f"Error saving template files: {str(e)}")
            self.stats['errors'] += 1
            return saved_files
    
    def save_onboarding_data(self):
        """Save onboarding data to files"""
        try:
            # Save onboarding steps
            steps_data = {
                "steps": [
                    {
                        "id": step.id,
                        "title": step.title,
                        "description": step.description,
                        "target_element": step.target_element,
                        "position": step.position,
                        "completed": step.completed,
                        "required": step.required,
                        "order": step.order
                    }
                    for step in self.onboarding_steps.values()
                ]
            }
            
            with open(self.onboarding_data_file, 'w') as f:
                json.dump(steps_data, f, indent=2)
            
            # Save help topics
            help_data = {
                "topics": [
                    {
                        "id": topic.id,
                        "title": topic.title,
                        "content": topic.content,
                        "category": topic.category,
                        "tags": topic.tags,
                        "related_features": topic.related_features
                    }
                    for topic in self.help_topics.values()
                ]
            }
            
            with open(self.help_data_file, 'w') as f:
                json.dump(help_data, f, indent=2)
            
            # Save tooltips
            tooltip_data = {
                "tooltips": [
                    {
                        "id": tooltip.id,
                        "element_selector": tooltip.element_selector,
                        "content": tooltip.content,
                        "position": tooltip.position,
                        "trigger": tooltip.trigger,
                        "delay": tooltip.delay
                    }
                    for tooltip in self.tooltips.values()
                ]
            }
            
            with open(self.tooltip_data_file, 'w') as f:
                json.dump(tooltip_data, f, indent=2)
            
            self.logger.info("Saved onboarding data files")
            
        except Exception as e:
            self.logger.error(f"Error saving onboarding data: {str(e)}")
            self.stats['errors'] += 1
    
    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute the agent's primary function"""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting OnboardingAgent execution")
            
            action = context.get('action', 'generate_all')
            
            if action == 'generate_all':
                # Create output directory
                if not self.create_output_directory():
                    return self._create_error_output("Failed to create output directory")
                
                # Create default data if not exists
                if not self.onboarding_steps:
                    steps = self.create_default_onboarding_steps()
                    for step in steps:
                        self.onboarding_steps[step.id] = step
                
                if not self.help_topics:
                    topics = self.create_default_help_topics()
                    for topic in topics:
                        self.help_topics[topic.id] = topic
                
                if not self.tooltips:
                    tooltips = self.create_default_tooltips()
                    for tooltip in tooltips:
                        self.tooltips[tooltip.id] = tooltip
                
                # Generate JavaScript files
                js_files = self.generate_javascript_files()
                saved_js = self.save_javascript_files(js_files)
                
                # Generate template files
                template_files = self.generate_progress_indicators()
                saved_templates = self.save_template_files(template_files)
                
                # Save data files
                self.save_onboarding_data()
                
                # Generate complete structures
                tutorial = self.generate_onboarding_tutorial()
                help_system = self.generate_help_system()
                tooltip_system = self.generate_tooltip_system()
                
                output = {
                    "status": "completed",
                    "message": "Onboarding system generation completed successfully",
                    "statistics": self.stats,
                    "generated_files": {
                        "javascript_files": saved_js,
                        "template_files": saved_templates,
                        "data_files": [self.onboarding_data_file, self.help_data_file, self.tooltip_data_file]
                    },
                    "onboarding_tutorial": tutorial,
                    "help_system": help_system,
                    "tooltip_system": tooltip_system,
                    "step_count": len(self.onboarding_steps),
                    "help_topic_count": len(self.help_topics),
                    "tooltip_count": len(self.tooltips)
                }
                
            elif action == 'generate_onboarding':
                tutorial = self.generate_onboarding_tutorial()
                output = {
                    "status": "completed",
                    "onboarding_tutorial": tutorial,
                    "step_count": len(tutorial["steps"])
                }
                
            elif action == 'generate_help':
                help_system = self.generate_help_system()
                output = {
                    "status": "completed",
                    "help_system": help_system,
                    "topic_count": len(self.help_topics),
                    "category_count": len(help_system["categories"])
                }
                
            elif action == 'generate_tooltips':
                tooltip_system = self.generate_tooltip_system()
                output = {
                    "status": "completed",
                    "tooltip_system": tooltip_system,
                    "tooltip_count": len(self.tooltips)
                }
                
            elif action == 'generate_javascript':
                js_files = self.generate_javascript_files()
                saved_files = self.save_javascript_files(js_files)
                output = {
                    "status": "completed",
                    "javascript_files": list(js_files.keys()),
                    "saved_files": saved_files,
                    "file_count": len(js_files)
                }
                
            elif action == 'generate_templates':
                template_files = self.generate_progress_indicators()
                saved_files = self.save_template_files(template_files)
                output = {
                    "status": "completed",
                    "template_files": list(template_files.keys()),
                    "saved_files": saved_files,
                    "file_count": len(template_files)
                }
                
            elif action == 'add_onboarding_step':
                step_data = context.get('step', {})
                step = OnboardingStep(
                    id=step_data.get('id', f"step_{len(self.onboarding_steps) + 1}"),
                    title=step_data.get('title', ''),
                    description=step_data.get('description', ''),
                    target_element=step_data.get('target_element'),
                    position=step_data.get('position', 'bottom'),
                    completed=step_data.get('completed', False),
                    required=step_data.get('required', True),
                    order=step_data.get('order', len(self.onboarding_steps))
                )
                self.onboarding_steps[step.id] = step
                self.stats['onboarding_steps_created'] += 1
                
                output = {
                    "status": "completed",
                    "step_id": step.id,
                    "total_steps": len(self.onboarding_steps)
                }
                
            elif action == 'add_help_topic':
                topic_data = context.get('topic', {})
                topic = HelpTopic(
                    id=topic_data.get('id', f"topic_{len(self.help_topics) + 1}"),
                    title=topic_data.get('title', ''),
                    content=topic_data.get('content', ''),
                    category=topic_data.get('category', 'general'),
                    tags=topic_data.get('tags', []),
                    related_features=topic_data.get('related_features', [])
                )
                self.help_topics[topic.id] = topic
                self.stats['help_topics_created'] += 1
                
                output = {
                    "status": "completed",
                    "topic_id": topic.id,
                    "total_topics": len(self.help_topics)
                }
                
            elif action == 'add_tooltip':
                tooltip_data = context.get('tooltip', {})
                tooltip = Tooltip(
                    id=tooltip_data.get('id', f"tooltip_{len(self.tooltips) + 1}"),
                    element_selector=tooltip_data.get('element_selector', ''),
                    content=tooltip_data.get('content', ''),
                    position=tooltip_data.get('position', 'top'),
                    trigger=tooltip_data.get('trigger', 'hover'),
                    delay=tooltip_data.get('delay', 300)
                )
                self.tooltips[tooltip.id] = tooltip
                self.stats['tooltips_created'] += 1
                
                output = {
                    "status": "completed",
                    "tooltip_id": tooltip.id,
                    "total_tooltips": len(self.tooltips)
                }
                
            else:
                output = {"status": "error", "message": f"Unknown action: {action}"}
            
            self.status = AgentStatus.COMPLETED
            return self._create_success_output(output)
            
        except Exception as e:
            return self._handle_error(e)
    
    def validate(self) -> List[AgentError]:
        """Validate agent configuration and state"""
        errors = super().validate()
        
        # Check if output directory is writable
        try:
            test_path = Path(self.output_dir)
            if test_path.exists():
                test_file = test_path / ".write_test"
                with open(test_file, 'w') as f:
                    f.write("test")
                test_file.unlink()
            else:
                # Try to create the directory
                test_path.mkdir(parents=True, exist_ok=True)
                test_path.rmdir()
        except Exception as e:
            errors.append(AgentError(
                agent_name=self.name,
                error_type="permission_error",
                message=f"Output directory is not writable: {self.output_dir}",
                severity=ErrorSeverity.MEDIUM,
                context={"output_dir": self.output_dir},
                solution=f"Ensure directory {self.output_dir} exists and is writable"
            ))
        
        return errors


if __name__ == "__main__":
    # Allow direct execution for testing
    agent = OnboardingAgent()
    output = agent.initialize()
    print(f"OnboardingAgent initialized: {output.status.name}")
