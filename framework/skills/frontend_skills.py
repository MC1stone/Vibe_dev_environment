"""
Frontend Skills Module

Specialized skills for frontend development agents.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json


class FrontendSkillType(Enum):
    """Frontend skill types"""
    UI_DESIGN = "ui_design"
    RESPONSIVE_DESIGN = "responsive_design"
    STATE_MANAGEMENT = "state_management"
    PERFORMANCE = "performance"
    ACCESSIBILITY = "accessibility"
    STYLING = "styling"
    ANIMATION = "animation"
    TESTING = "testing"
    INTERNATIONALIZATION = "internationalization"
    FRAMEWORKS = "frameworks"


@dataclass
class FrontendSkill:
    """Represents a frontend development skill"""
    skill_id: str
    name: str
    skill_type: FrontendSkillType
    description: str
    difficulty: str  # "beginner", "intermediate", "advanced"
    technologies: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    best_practices: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.difficulty not in ["beginner", "intermediate", "advanced"]:
            raise ValueError("Difficulty must be beginner, intermediate, or advanced")


class FrontendSkills:
    """
    Frontend Skills Collection
    
    This class contains all specialized skills for frontend development.
    """
    
    def __init__(self):
        self.skills: Dict[str, FrontendSkill] = {}
        self._initialize_skills()
    
    def _initialize_skills(self) -> None:
        """Initialize all frontend skills"""
        
        # UI Design Skills
        self.skills["ui_design_principles"] = FrontendSkill(
            skill_id="ui_design_principles",
            name="UI Design Principles",
            skill_type=FrontendSkillType.UI_DESIGN,
            description="Apply fundamental UI design principles and best practices",
            difficulty="intermediate",
            technologies=["Figma", "Sketch", "Adobe XD", "Design Systems"],
            dependencies=["user_research", "design_thinking"],
            examples=[
                "Design a user-friendly dashboard interface",
                "Create a consistent design system",
                "Apply Fitts's Law and Hick's Law in UI design"
            ],
            best_practices=[
                "Keep the interface simple and intuitive",
                "Use consistent design patterns",
                "Prioritize user needs and goals",
                "Maintain visual hierarchy",
                "Use appropriate whitespace",
                "Ensure visual consistency",
                "Design for accessibility"
            ]
        )
        
        self.skills["design_systems"] = FrontendSkill(
            skill_id="design_systems",
            name="Design Systems",
            skill_type=FrontendSkillType.UI_DESIGN,
            description="Create and maintain design systems for consistent UI",
            difficulty="advanced",
            technologies=["Storybook", "Styleguidist", "Figma", "Sketch"],
            dependencies=["ui_design_principles", "component_architecture"],
            examples=[
                "Create a design system with reusable components",
                "Document design tokens and guidelines",
                "Implement a living style guide"
            ],
            best_practices=[
                "Create a comprehensive component library",
                "Define clear design tokens (colors, typography, spacing)",
                "Document usage guidelines",
                "Implement design system in code",
                "Keep design system up-to-date",
                "Test design system components"
            ]
        )
        
        # Responsive Design Skills
        self.skills["responsive_layouts"] = FrontendSkill(
            skill_id="responsive_layouts",
            name="Responsive Layouts",
            skill_type=FrontendSkillType.RESPONSIVE_DESIGN,
            description="Create layouts that work on all device sizes",
            difficulty="intermediate",
            technologies=["CSS Flexbox", "CSS Grid", "Media Queries", "Bootstrap", "Tailwind"],
            dependencies=["css_basics", "html_structure"],
            examples=[
                "Create a responsive grid layout",
                "Implement mobile-first design",
                "Design adaptive layouts for different screen sizes"
            ],
            best_practices=[
                "Use mobile-first approach",
                "Use relative units (%, em, rem) instead of fixed units",
                "Implement proper viewport meta tag",
                "Use media queries for breakpoints",
                "Test on multiple device sizes",
                "Consider touch targets for mobile",
                "Use flexible images and media"
            ]
        )
        
        self.skills["mobile_first_design"] = FrontendSkill(
            skill_id="mobile_first_design",
            name="Mobile-First Design",
            skill_type=FrontendSkillType.RESPONSIVE_DESIGN,
            description="Design applications starting from mobile and scaling up",
            difficulty="intermediate",
            technologies=["CSS", "Responsive Design", "Progressive Enhancement"],
            dependencies=["responsive_layouts"],
            examples=[
                "Design a mobile-first web application",
                "Implement progressive enhancement",
                "Optimize performance for mobile devices"
            ],
            best_practices=[
                "Start with mobile layout and scale up",
                "Prioritize content for mobile users",
                "Optimize images and assets for mobile",
                "Use appropriate font sizes for readability",
                "Design for touch interactions",
                "Test on real mobile devices"
            ]
        )
        
        # State Management Skills
        self.skills["react_state_management"] = FrontendSkill(
            skill_id="react_state_management",
            name="React State Management",
            skill_type=FrontendSkillType.STATE_MANAGEMENT,
            description="Manage application state in React applications",
            difficulty="intermediate",
            technologies=["React", "useState", "useReducer", "Context API", "Redux", "Zustand"],
            dependencies=["react_basics", "javascript_es6"],
            examples=[
                "Implement local state with useState",
                "Create a global state with Context API",
                "Set up Redux for complex state management"
            ],
            best_practices=[
                "Use local state for component-specific data",
                "Lift state up when multiple components need it",
                "Use Context API for theme and user preferences",
                "Consider Redux for complex application state",
                "Avoid prop drilling with state management libraries",
                "Keep state updates immutable",
                "Use selectors for derived state"
            ]
        )
        
        self.skills["vue_state_management"] = FrontendSkill(
            skill_id="vue_state_management",
            name="Vue State Management",
            skill_type=FrontendSkillType.STATE_MANAGEMENT,
            description="Manage application state in Vue applications",
            difficulty="intermediate",
            technologies=["Vue", "Vuex", "Pinia", "Composition API"],
            dependencies=["vue_basics", "javascript_es6"],
            examples=[
                "Implement reactive data with ref and reactive",
                "Create a Vuex store for global state",
                "Use Pinia for modular state management"
            ],
            best_practices=[
                "Use ref for primitive values and reactive for objects",
                "Use computed properties for derived state",
                "Use Vuex for complex state management",
                "Consider Pinia for better TypeScript support",
                "Avoid mutating state directly",
                "Use actions for async state updates"
            ]
        )
        
        # Performance Skills
        self.skills["performance_optimization"] = FrontendSkill(
            skill_id="performance_optimization",
            name="Performance Optimization",
            skill_type=FrontendSkillType.PERFORMANCE,
            description="Optimize frontend performance for faster loading and smoother user experience",
            difficulty="advanced",
            technologies=["Lighthouse", "WebPageTest", "Chrome DevTools", "Webpack"],
            dependencies=["javascript_basics", "browser_api"],
            examples=[
                "Optimize bundle size with code splitting",
                "Implement lazy loading for components",
                "Optimize images and assets"
            ],
            best_practices=[
                "Minimize and bundle CSS and JavaScript",
                "Use code splitting for large applications",
                "Lazy load non-critical resources",
                "Optimize images (compression, modern formats)",
                "Use browser caching effectively",
                "Minimize DOM manipulations",
                "Use efficient data structures and algorithms"
            ]
        )
        
        self.skills["bundle_optimization"] = FrontendSkill(
            skill_id="bundle_optimization",
            name="Bundle Optimization",
            skill_type=FrontendSkillType.PERFORMANCE,
            description="Optimize frontend bundles for faster loading",
            difficulty="advanced",
            technologies=["Webpack", "Rollup", "Vite", "Parcel"],
            dependencies=["javascript_modules", "build_tools"],
            examples=[
                "Configure Webpack for production builds",
                "Implement tree shaking to remove unused code",
                "Optimize bundle splitting strategy"
            ],
            best_practices=[
                "Use production mode for builds",
                "Enable minification and compression",
                "Use tree shaking to remove unused code",
                "Split bundles by route or feature",
                "Use dynamic imports for lazy loading",
                "Optimize source maps for production",
                "Use content hashing for cache busting"
            ]
        )
        
        # Accessibility Skills
        self.skills["wcag_compliance"] = FrontendSkill(
            skill_id="wcag_compliance",
            name="WCAG Compliance",
            skill_type=FrontendSkillType.ACCESSIBILITY,
            description="Ensure applications meet WCAG accessibility standards",
            difficulty="intermediate",
            technologies=["WAVE", "axe", "Lighthouse", "NVDA", "VoiceOver"],
            dependencies=["html_semantics", "aria_standards"],
            examples=[
                "Audit application for WCAG compliance",
                "Implement proper ARIA attributes",
                "Ensure keyboard navigation support"
            ],
            best_practices=[
                "Use semantic HTML elements",
                "Provide appropriate ARIA attributes",
                "Ensure keyboard accessibility",
                "Use sufficient color contrast",
                "Provide text alternatives for non-text content",
                "Make content adaptable and distinguishable",
                "Test with screen readers"
            ]
        )
        
        self.skills["keyboard_accessibility"] = FrontendSkill(
            skill_id="keyboard_accessibility",
            name="Keyboard Accessibility",
            skill_type=FrontendSkillType.ACCESSIBILITY,
            description="Ensure applications are fully accessible via keyboard",
            difficulty="intermediate",
            technologies=["HTML", "CSS", "JavaScript", "WAI-ARIA"],
            dependencies=["wcag_compliance"],
            examples=[
                "Implement keyboard navigation for a complex UI",
                "Create accessible dropdown menus",
                "Ensure all interactive elements are keyboard accessible"
            ],
            best_practices=[
                "Ensure all interactive elements are keyboard focusable",
                "Provide visible focus indicators",
                "Use proper tab order",
                "Implement keyboard shortcuts where appropriate",
                "Test with keyboard-only navigation",
                "Avoid keyboard traps"
            ]
        )
        
        # Styling Skills
        self.skills["css_methodologies"] = FrontendSkill(
            skill_id="css_methodologies",
            name="CSS Methodologies",
            skill_type=FrontendSkillType.STYLING,
            description="Use CSS methodologies for maintainable and scalable styles",
            difficulty="intermediate",
            technologies=["BEM", "SMACSS", "OOCSS", "ITCSS", "Tailwind CSS"],
            dependencies=["css_basics", "html_structure"],
            examples=[
                "Implement BEM methodology for component styling",
                "Create a scalable CSS architecture",
                "Use utility-first CSS with Tailwind"
            ],
            best_practices=[
                "Use consistent naming conventions",
                "Keep CSS modular and reusable",
                "Avoid deep nesting in selectors",
                "Use meaningful class names",
                "Keep specificity low",
                "Document CSS conventions",
                "Use CSS variables for theming"
            ]
        )
        
        self.skills["css_preprocessors"] = FrontendSkill(
            skill_id="css_preprocessors",
            name="CSS Preprocessors",
            skill_type=FrontendSkillType.STYLING,
            description="Use CSS preprocessors for enhanced styling capabilities",
            difficulty="intermediate",
            technologies=["Sass", "Less", "Stylus", "PostCSS"],
            dependencies=["css_basics"],
            examples=[
                "Create mixins for reusable styles",
                "Use variables for consistent theming",
                "Implement nested selectors"
            ],
            best_practices=[
                "Use variables for colors, fonts, and spacing",
                "Create reusable mixins",
                "Use nesting judiciously",
                "Keep partials organized",
                "Use functions for complex calculations",
                "Avoid over-nesting"
            ]
        )
        
        # Animation Skills
        self.skills["css_animations"] = FrontendSkill(
            skill_id="css_animations",
            name="CSS Animations",
            skill_type=FrontendSkillType.ANIMATION,
            description="Create smooth and performant animations with CSS",
            difficulty="intermediate",
            technologies=["CSS Animations", "CSS Transitions", "Keyframes"],
            dependencies=["css_basics"],
            examples=[
                "Create a smooth hover animation",
                "Implement a loading spinner with CSS",
                "Create complex keyframe animations"
            ],
            best_practices=[
                "Use CSS animations for simple animations",
                "Prefer transforms over animating width/height",
                "Use will-change for performance hints",
                "Avoid animating properties that trigger layout",
                "Use appropriate timing functions",
                "Keep animations short and subtle",
                "Test animations on different devices"
            ]
        )
        
        self.skills["javascript_animations"] = FrontendSkill(
            skill_id="javascript_animations",
            name="JavaScript Animations",
            skill_type=FrontendSkillType.ANIMATION,
            description="Create complex animations with JavaScript",
            difficulty="advanced",
            technologies=["GSAP", "Anime.js", "Framer Motion", "React Spring"],
            dependencies=["javascript_basics", "animation_principles"],
            examples=[
                "Create a complex animation sequence",
                "Implement scroll-based animations",
                "Create interactive animations"
            ],
            best_practices=[
                "Use requestAnimationFrame for smooth animations",
                "Use libraries like GSAP for complex animations",
                "Optimize animation performance",
                "Use hardware acceleration when possible",
                "Clean up animations to avoid memory leaks",
                "Test animations on different devices"
            ]
        )
        
        # Testing Skills
        self.skills["frontend_unit_testing"] = FrontendSkill(
            skill_id="frontend_unit_testing",
            name="Frontend Unit Testing",
            skill_type=FrontendSkillType.TESTING,
            description="Write unit tests for frontend components and functions",
            difficulty="intermediate",
            technologies=["Jest", "React Testing Library", "Vue Test Utils", "Enzyme"],
            dependencies=["testing_basics", "javascript_basics"],
            examples=[
                "Test a React component with Jest",
                "Write unit tests for utility functions",
                "Mock dependencies in frontend tests"
            ],
            best_practices=[
                "Test component rendering",
                "Test user interactions",
                "Mock external dependencies",
                "Use descriptive test names",
                "Keep tests fast and isolated",
                "Test both happy paths and error cases"
            ]
        )
        
        self.skills["e2e_testing"] = FrontendSkill(
            skill_id="e2e_testing",
            name="End-to-End Testing",
            skill_type=FrontendSkillType.TESTING,
            description="Test complete user flows with end-to-end tests",
            difficulty="intermediate",
            technologies=["Cypress", "Playwright", "Selenium", "Puppeteer"],
            dependencies=["frontend_unit_testing", "testing_basics"],
            examples=[
                "Test a complete user registration flow",
                "Create end-to-end tests for a checkout process",
                "Test cross-page navigation"
            ],
            best_practices=[
                "Test real user flows",
                "Use page objects for maintainability",
                "Wait for elements to be ready",
                "Clean up test data after execution",
                "Use realistic test data",
                "Test on multiple browsers"
            ]
        )
        
        # Internationalization Skills
        self.skills["i18n_implementation"] = FrontendSkill(
            skill_id="i18n_implementation",
            name="Internationalization (i18n)",
            skill_type=FrontendSkillType.INTERNATIONALIZATION,
            description="Implement multi-language support in applications",
            difficulty="intermediate",
            technologies=["i18next", "react-i18next", "vue-i18n", "FormatJS"],
            dependencies=["javascript_basics"],
            examples=[
                "Add multi-language support to a React app",
                "Implement language switching",
                "Format dates and numbers for different locales"
            ],
            best_practices=[
                "Extract all user-facing text",
                "Use appropriate data formats for each locale",
                "Implement language detection",
                "Provide fallback languages",
                "Use proper pluralization and grammar rules",
                "Test with right-to-left languages"
            ]
        )
        
        self.skills["localization"] = FrontendSkill(
            skill_id="localization",
            name="Localization",
            skill_type=FrontendSkillType.INTERNATIONALIZATION,
            description="Adapt applications for different locales and regions",
            difficulty="intermediate",
            technologies=["i18next", "react-i18next", "vue-i18n", "FormatJS"],
            dependencies=["i18n_implementation"],
            examples=[
                "Adapt date and time formats for different regions",
                "Implement locale-specific formatting",
                "Handle currency and number formatting"
            ],
            best_practices=[
                "Use locale-appropriate date and time formats",
                "Format numbers and currencies correctly",
                "Handle text direction (RTL vs LTR)",
                "Use appropriate units of measurement",
                "Consider cultural differences in UI",
                "Test with different locales"
            ]
        )
        
        # Framework Skills
        self.skills["react_development"] = FrontendSkill(
            skill_id="react_development",
            name="React Development",
            skill_type=FrontendSkillType.FRAMEWORKS,
            description="Develop applications using React framework",
            difficulty="intermediate",
            technologies=["React", "React Hooks", "React Router", "Next.js"],
            dependencies=["javascript_es6", "jsx_basics"],
            examples=[
                "Create a React functional component",
                "Implement client-side routing with React Router",
                "Build a full-stack application with Next.js"
            ],
            best_practices=[
                "Use functional components with hooks",
                "Keep components small and focused",
                "Use props for component communication",
                "Manage state appropriately",
                "Use React.memo for performance optimization",
                "Follow React naming conventions"
            ]
        )
        
        self.skills["vue_development"] = FrontendSkill(
            skill_id="vue_development",
            name="Vue Development",
            skill_type=FrontendSkillType.FRAMEWORKS,
            description="Develop applications using Vue framework",
            difficulty="intermediate",
            technologies=["Vue", "Vue Router", "Vuex", "Pinia", "Nuxt.js"],
            dependencies=["javascript_es6", "html_basics"],
            examples=[
                "Create a Vue single-file component",
                "Implement state management with Vuex",
                "Build a server-side rendered app with Nuxt.js"
            ],
            best_practices=[
                "Use single-file components",
                "Keep components focused and reusable",
                "Use props for parent-child communication",
                "Use events for child-parent communication",
                "Use Vuex for global state management",
                "Follow Vue style guide"
            ]
        )
    
    def get_skill(self, skill_id: str) -> Optional[FrontendSkill]:
        """Get a specific skill by ID"""
        return self.skills.get(skill_id)
    
    def get_skills_by_type(self, skill_type: FrontendSkillType) -> List[FrontendSkill]:
        """Get all skills of a specific type"""
        return [skill for skill in self.skills.values() if skill.skill_type == skill_type]
    
    def get_skills_by_technology(self, technology: str) -> List[FrontendSkill]:
        """Get all skills that use a specific technology"""
        return [skill for skill in self.skills.values() if technology in skill.technologies]
    
    def get_skills_by_difficulty(self, difficulty: str) -> List[FrontendSkill]:
        """Get all skills of a specific difficulty level"""
        return [skill for skill in self.skills.values() if skill.difficulty == difficulty]
    
    def search_skills(self, query: str) -> List[FrontendSkill]:
        """Search skills by name or description"""
        query_lower = query.lower()
        return [
            skill for skill in self.skills.values()
            if query_lower in skill.name.lower() or query_lower in skill.description.lower()
        ]
    
    def list_all_skills(self) -> List[Dict[str, Any]]:
        """List all available skills"""
        return [
            {
                "skill_id": skill.skill_id,
                "name": skill.name,
                "type": skill.skill_type.value,
                "description": skill.description,
                "difficulty": skill.difficulty,
                "technologies": skill.technologies
            }
            for skill in self.skills.values()
        ]
    
    def get_skill_statistics(self) -> Dict[str, Any]:
        """Get statistics about available skills"""
        statistics = {
            "total_skills": len(self.skills),
            "by_type": {},
            "by_difficulty": {},
            "by_technology": {}
        }
        
        # Count by type
        for skill_type in FrontendSkillType:
            count = len(self.get_skills_by_type(skill_type))
            if count > 0:
                statistics["by_type"][skill_type.value] = count
        
        # Count by difficulty
        for difficulty in ["beginner", "intermediate", "advanced"]:
            count = len(self.get_skills_by_difficulty(difficulty))
            if count > 0:
                statistics["by_difficulty"][difficulty] = count
        
        # Count by technology
        all_technologies = set()
        for skill in self.skills.values():
            for tech in skill.technologies:
                all_technologies.add(tech)
        
        for tech in all_technologies:
            count = len(self.get_skills_by_technology(tech))
            statistics["by_technology"][tech] = count
        
        return statistics
