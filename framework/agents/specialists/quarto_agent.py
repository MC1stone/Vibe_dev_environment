"""
Quarto Agent - Specialist for Quarto Document Publishing

Responsibilities:
- Document creation and formatting
- Code execution and output rendering
- Multi-language support
- Publication and sharing
- Template management
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import asyncio


class QuartoDocumentType(Enum):
    """Quarto document types"""
    WEBSITE = "website"
    REPORT = "report"
    PRESENTATION = "presentation"
    BOOK = "book"
    BLOG = "blog"
    DASHBOARD = "dashboard"


class QuartoFormat(Enum):
    """Quarto output formats"""
    HTML = "html"
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    EPUB = "epub"
    MARKDOWN = "markdown"
    JUPYTER = "jupyter"


class QuartoEngine(Enum):
    """Quarto rendering engines"""
    KNITR = "knitr"
    JUPYTER = "jupyter"
    OBSIDIAN = "obsidian"
    MARKDOWN = "markdown"


class QuartoLanguage(Enum):
    """Quarto supported languages"""
    R = "r"
    PYTHON = "python"
    JULIA = "julia"
    OBSIDIAN = "obsidian"
    MARKDOWN = "markdown"
    SQL = "sql"
    BASH = "bash"


@dataclass
class QuartoCodeCell:
    """Represents a Quarto code cell"""
    cell_id: str
    code: str
    language: QuartoLanguage
    echo: bool = True
    eval: bool = True
    output: Optional[str] = None
    error: Optional[str] = None
    execution_time: float = 0.0


@dataclass
class QuartoMarkdownCell:
    """Represents a Quarto markdown cell"""
    cell_id: str
    content: str
    format: str = "markdown"  # "markdown", "html", "text"


@dataclass
class QuartoDocument:
    """Represents a Quarto document"""
    document_id: str
    title: str
    document_type: QuartoDocumentType = QuartoDocumentType.REPORT
    formats: List[QuartoFormat] = field(default_factory=list)
    engine: QuartoEngine = QuartoEngine.KNITR
    language: QuartoLanguage = QuartoLanguage.PYTHON
    cells: List[Any] = field(default_factory=list)  # Mix of code and markdown cells
    metadata: Dict[str, Any] = field(default_factory=dict)
    bibliography: Optional[str] = None
    citations: List[str] = field(default_factory=list)


@dataclass
class QuartoProject:
    """Represents a Quarto project"""
    project_id: str
    name: str
    description: str = ""
    documents: List[str] = field(default_factory=list)
    configuration: Dict[str, Any] = field(default_factory=dict)
    dependencies: Dict[str, str] = field(default_factory=dict)


@dataclass
class QuartoAgent:
    """
    Quarto Specialist Agent
    
    This agent specializes in Quarto document publishing, code execution, and multi-format output.
    It can create and manage Quarto documents and projects for various publishing needs.
    """
    
    agent_id: str = "quarto_agent_001"
    name: str = "Quarto Specialist"
    description: str = "Expert in Quarto document publishing and code execution"
    version: str = "1.0.0"
    
    # Agent capabilities
    supported_document_types: List[QuartoDocumentType] = field(default_factory=lambda: [
        QuartoDocumentType.WEBSITE,
        QuartoDocumentType.REPORT,
        QuartoDocumentType.PRESENTATION,
        QuartoDocumentType.BOOK,
        QuartoDocumentType.BLOG,
    ])
    
    supported_formats: List[QuartoFormat] = field(default_factory=lambda: [
        QuartoFormat.HTML,
        QuartoFormat.PDF,
        QuartoFormat.DOCX,
        QuartoFormat.PPTX,
        QuartoFormat.MARKDOWN,
        QuartoFormat.JUPYTER,
    ])
    
    supported_engines: List[QuartoEngine] = field(default_factory=lambda: [
        QuartoEngine.KNITR,
        QuartoEngine.JUPYTER,
        QuartoEngine.MARKDOWN,
    ])
    
    supported_languages: List[QuartoLanguage] = field(default_factory=lambda: [
        QuartoLanguage.R,
        QuartoLanguage.PYTHON,
        QuartoLanguage.JULIA,
        QuartoLanguage.MARKDOWN,
        QuartoLanguage.SQL,
        QuartoLanguage.BASH,
    ])
    
    # Agent skills
    skills: Dict[str, str] = field(default_factory=dict)
    
    # Current project state
    current_project: Optional[str] = None
    current_document: Optional[str] = None
    
    # Projects being managed
    projects: Dict[str, QuartoProject] = field(default_factory=dict)
    
    # Documents being created
    documents: Dict[str, QuartoDocument] = field(default_factory=dict)
    
    # Performance metrics
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize the agent with default skills"""
        self._initialize_skills()
    
    def _initialize_skills(self) -> None:
        """Initialize the agent's skill set"""
        self.skills = {
            "document_creation": "Create Quarto documents with proper structure and formatting",
            "code_execution": "Execute code in various languages and capture outputs",
            "multi_format_publishing": "Publish documents in multiple formats (HTML, PDF, etc.)",
            "template_management": "Create and manage document templates for consistency",
            "citation_management": "Manage bibliographies and citations in documents",
            "cross_referencing": "Create cross-references and links within documents",
            "interactive_documents": "Create interactive documents with widgets and controls",
            "collaboration": "Set up collaborative document editing workflows",
            "version_control": "Integrate with version control systems for document management",
            "testing": "Test documents and validate their rendering",
            "documentation": "Document Quarto projects and their components",
            "deployment": "Deploy Quarto documents to various platforms"
        }
    
    async def create_project(self, project_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new Quarto project
        
        Args:
            project_spec: Project specification
            
        Returns:
            Dictionary with project configuration
        """
        print(f"🚀 {self.name}: Creating Quarto project {project_spec.get('name', 'Unnamed')}")
        
        project_id = project_spec.get("project_id", f"project_{len(self.projects) + 1}")
        project_name = project_spec.get("name", "Unnamed Project")
        description = project_spec.get("description", "")
        configuration = project_spec.get("configuration", {})
        dependencies = project_spec.get("dependencies", {})
        
        # Create project
        project = QuartoProject(
            project_id=project_id,
            name=project_name,
            description=description,
            configuration=configuration,
            dependencies=dependencies
        )
        
        self.projects[project_id] = project
        self.current_project = project_id
        
        # Generate project structure
        project_structure = self._generate_project_structure(project)
        
        result = {
            "project_id": project_id,
            "name": project_name,
            "description": description,
            "configuration": configuration,
            "dependencies": dependencies,
            "structure": project_structure,
            "status": "created"
        }
        
        print(f"✅ {self.name}: Quarto project {project_name} created with ID {project_id}")
        return result
    
    def _generate_project_structure(self, project: QuartoProject) -> Dict[str, Any]:
        """Generate project directory structure"""
        structure = {
            "name": project.name,
            "type": "quarto_project",
            "files": [],
            "directories": []
        }
        
        # Add configuration files
        structure["files"].append({
            "name": "_quarto.yml",
            "type": "configuration",
            "content": self._generate_quarto_config(project.configuration)
        })
        
        # Add dependency files
        if project.dependencies:
            structure["files"].append({
                "name": "requirements.txt",
                "type": "dependencies",
                "content": self._generate_requirements_file(project.dependencies)
            })
        
        # Add README
        structure["files"].append({
            "name": "README.md",
            "type": "documentation",
            "content": f"# {project.name}\n\n{project.description}\n\n## Project Structure\n\n- `_quarto.yml`: Quarto configuration\n- `docs/`: Project documents\n- `output/`: Rendered output\n"
        })
        
        # Add directories
        structure["directories"].append({
            "name": "docs",
            "type": "documents",
            "description": "Quarto documents"
        })
        
        structure["directories"].append({
            "name": "output",
            "type": "output",
            "description": "Rendered output files"
        })
        
        return structure
    
    def _generate_quarto_config(self, configuration: Dict[str, Any]) -> str:
        """Generate _quarto.yml configuration"""
        config = {
            "project": {
                "type": configuration.get("type", "website"),
                "output-dir": configuration.get("output_dir", "output")
            },
            "website": {
                "title": configuration.get("title", "My Quarto Project"),
                "navbar": {
                    "left": [
                        {"href": "index.qmd", "text": "Home"}
                    ]
                }
            } if configuration.get("type") == "website" else {},
            "format": {
                "html": {
                    "theme": configuration.get("theme", "cosmo"),
                    "toc": True,
                    "toc-depth": 3
                },
                "pdf": {
                    "documentclass": "article",
                    "papersize": "a4"
                }
            }
        }
        
        return """# Quarto Configuration
# This file configures the Quarto project

```yaml
""" + f"{yaml.dump(config, default_flow_style=False, sort_keys=False)}" + """
```

## Usage

- **Render documents**: `quarto render`
- **Preview website**: `quarto preview`
- **Publish**: `quarto publish`
"""
    
    def _generate_requirements_file(self, dependencies: Dict[str, str]) -> str:
        """Generate requirements.txt file"""
        lines = []
        
        # Add Quarto dependencies
        lines.append("quarto")
        
        # Add Python dependencies
        if "python" in dependencies:
            lines.append(f"# Python dependencies")
            for pkg, version in dependencies["python"].items():
                lines.append(f"{pkg}=={version}")
        
        # Add R dependencies
        if "r" in dependencies:
            lines.append(f"# R dependencies")
            for pkg, version in dependencies["r"].items():
                lines.append(f"# install.packages('{pkg}', version='{version}')")
        
        return "\n".join(lines)
    
    async def create_document(self, project_id: str, document_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new Quarto document
        
        Args:
            project_id: ID of the project
            document_spec: Document specification
            
        Returns:
            Dictionary with document configuration
        """
        print(f"📄 {self.name}: Creating document for project {project_id}")
        
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")
        
        project = self.projects[project_id]
        
        document_id = document_spec.get("document_id", f"doc_{len(self.documents) + 1}")
        title = document_spec.get("title", "Untitled Document")
        document_type_str = document_spec.get("document_type", "report")
        formats_str = document_spec.get("formats", ["html"])
        engine_str = document_spec.get("engine", "knitr")
        language_str = document_spec.get("language", "python")
        
        # Validate document type
        try:
            document_type = QuartoDocumentType(document_type_str)
        except ValueError:
            document_type = QuartoDocumentType.REPORT
            print(f"⚠️  Document type {document_type_str} not supported, defaulting to Report")
        
        # Validate formats
        formats = []
        for fmt_str in formats_str:
            try:
                formats.append(QuartoFormat(fmt_str))
            except ValueError:
                print(f"⚠️  Format {fmt_str} not supported")
        
        if not formats:
            formats = [QuartoFormat.HTML]
        
        # Validate engine
        try:
            engine = QuartoEngine(engine_str)
        except ValueError:
            engine = QuartoEngine.KNITR
            print(f"⚠️  Engine {engine_str} not supported, defaulting to Knitr")
        
        # Validate language
        try:
            language = QuartoLanguage(language_str)
        except ValueError:
            language = QuartoLanguage.PYTHON
            print(f"⚠️  Language {language_str} not supported, defaulting to Python")
        
        # Create document
        document = QuartoDocument(
            document_id=document_id,
            title=title,
            document_type=document_type,
            formats=formats,
            engine=engine,
            language=language,
            metadata=document_spec.get("metadata", {}),
            bibliography=document_spec.get("bibliography"),
            citations=document_spec.get("citations", [])
        )
        
        self.documents[document_id] = document
        project.documents.append(document_id)
        self.current_document = document_id
        
        # Generate document content
        document_content = self._generate_document_content(document)
        
        result = {
            "project_id": project_id,
            "document_id": document_id,
            "title": title,
            "document_type": document_type.value,
            "formats": [fmt.value for fmt in formats],
            "engine": engine.value,
            "language": language.value,
            "content": document_content,
            "status": "created"
        }
        
        print(f"✅ {self.name}: Document {title} created with ID {document_id}")
        return result
    
    def _generate_document_content(self, document: QuartoDocument) -> str:
        """Generate Quarto document content"""
        if document.document_type == QuartoDocumentType.WEBSITE:
            content = self._generate_website_document(document)
        elif document.document_type == QuartoDocumentType.REPORT:
            content = self._generate_report_document(document)
        elif document.document_type == QuartoDocumentType.PRESENTATION:
            content = self._generate_presentation_document(document)
        elif document.document_type == QuartoDocumentType.BOOK:
            content = self._generate_book_document(document)
        elif document.document_type == QuartoDocumentType.BLOG:
            content = self._generate_blog_document(document)
        else:
            content = self._generate_generic_document(document)
        
        return content
    
    def _generate_website_document(self, document: QuartoDocument) -> str:
        """Generate website document"""
        content = f"""---
title: "{document.title}"
format: html
---

# {document.title}

## Overview

This is a Quarto website document.

## Features

- **Interactive**: Supports interactive components
- **Multi-format**: Can be rendered as HTML, PDF, etc.
- **Code execution**: Supports {document.language.value} code execution

## Usage

```{{{document.language.value}}}
# Example code
print("Hello from {document.language.value}!")
```

## Sections

### Introduction

### Methods

### Results

### Discussion

### References
"""
        return content
    
    def _generate_report_document(self, document: QuartoDocument) -> str:
        """Generate report document"""
        content = f"""---
title: "{document.title}"
author: "Author Name"
date: "`r Sys.Date()`"
format:
  html:
    toc: true
    toc-depth: 3
  pdf:
    documentclass: article
---

# {document.title}

## Abstract

This report demonstrates the use of Quarto for creating reproducible documents.

## Introduction

Quarto is an open-source scientific and technical publishing system built on Pandoc.

## Methods

### Data Collection

### Analysis

```{{{document.language.value}}}
# Analysis code
import pandas as pd
import numpy as np

# Example analysis
data = pd.DataFrame({{
    'x': np.random.randn(100),
    'y': np.random.randn(100)
}})

print(data.head())
```

## Results

### Summary Statistics

```{{{document.language.value}}}
# Summary statistics
print(data.describe())
```

## Discussion

The results show...

## References
"""
        return content
    
    def _generate_presentation_document(self, document: QuartoDocument) -> str:
        """Generate presentation document"""
        content = f"""---
title: "{document.title}"
author: "Author Name"
format:
  revealjs:
    theme: white
    transition: slide
---

# {document.title}

## Introduction

- Overview of the presentation
- Key objectives

## Methods

- Data collection
- Analysis approach

## Results

### Key Findings

```{{{document.language.value}}}
# Live code demonstration
import matplotlib.pyplot as plt
import numpy as np

# Generate data
x = np.linspace(0, 10, 100)
y = np.sin(x)

# Plot
plt.figure(figsize=(8, 4))
plt.plot(x, y)
plt.title("Sine Wave")
plt.show()
```

## Discussion

- Interpretation of results
- Implications

## Conclusion

- Summary
- Next steps

## Thank You!

Questions?
"""
        return content
    
    def _generate_book_document(self, document: QuartoDocument) -> str:
        """Generate book document"""
        content = f"""---
title: "{document.title}"
author: "Author Name"
date: "`r Sys.Date()`"
format:
  html:
    toc: true
    toc-depth: 2
  pdf:
    documentclass: book
---

# {document.title}

## Preface

This book is created using Quarto.

## Chapter 1: Introduction

### Overview

### Background

## Chapter 2: Methods

### Data Collection

### Analysis

## Chapter 3: Results

### Findings

## Chapter 4: Discussion

### Interpretation

## References
"""
        return content
    
    def _generate_blog_document(self, document: QuartoDocument) -> str:
        """Generate blog document"""
        content = f"""---
title: "{document.title}"
author: "Author Name"
date: "`r Sys.Date()`"
categories: [blog, quarto]
tags: [quarto, publishing]
format: html
---

# {document.title}

This is a blog post created with Quarto.

## Introduction

## Main Content

### Section 1

### Section 2

## Code Example

```{{{document.language.value}}}
# Example code
print("Hello from Quarto!")
```

## Conclusion

## Comments
"""
        return content
    
    def _generate_generic_document(self, document: QuartoDocument) -> str:
        """Generate generic document"""
        content = f"""---
title: "{document.title}"
format: {document.formats[0].value if document.formats else 'html'}
---

# {document.title}

This is a Quarto document.

## Content

Add your content here.

## Code

```{{{document.language.value}}}
# Code example
print("Hello from {document.language.value}!")
```
"""
        return content
    
    async def add_code_cell(self, document_id: str, cell_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a code cell to a document
        
        Args:
            document_id: ID of the document
            cell_spec: Code cell specification
            
        Returns:
            Dictionary with code cell configuration
        """
        print(f"💻 {self.name}: Adding code cell to document {document_id}")
        
        if document_id not in self.documents:
            raise ValueError(f"Document {document_id} not found")
        
        document = self.documents[document_id]
        
        cell_id = cell_spec.get("cell_id", f"cell_{len(document.cells) + 1}")
        code = cell_spec.get("code", "")
        language_str = cell_spec.get("language", document.language.value)
        echo = cell_spec.get("echo", True)
        eval = cell_spec.get("eval", True)
        
        # Validate language
        try:
            language = QuartoLanguage(language_str)
        except ValueError:
            language = document.language
            print(f"⚠️  Language {language_str} not supported, using document language: {document.language.value}")
        
        # Create code cell
        code_cell = QuadrantCodeCell(
            cell_id=cell_id,
            code=code,
            language=language,
            echo=echo,
            eval=eval
        )
        
        document.cells.append(code_cell)
        
        # Generate cell code
        cell_code = self._generate_code_cell_code(code_cell, document)
        
        result = {
            "document_id": document_id,
            "cell_id": cell_id,
            "code": code,
            "language": language.value,
            "echo": echo,
            "eval": eval,
            "cell_code": cell_code,
            "status": "added"
        }
        
        print(f"✅ {self.name}: Code cell {cell_id} added to document {document_id}")
        return result
    
    def _generate_code_cell_code(self, cell: QuartoCodeCell, document: QuartoDocument) -> str:
        """Generate code cell content"""
        echo_str = "echo=true" if cell.echo else "echo=false"
        eval_str = "eval=true" if cell.eval else "eval=false"
        
        code = f"""```{{{cell.language.value} {echo_str} {eval_str}}}
# Code cell: {cell.cell_id}
{cell.code}
```

---
"""
        return code
    
    async def add_markdown_cell(self, document_id: str, cell_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a markdown cell to a document
        
        Args:
            document_id: ID of the document
            cell_spec: Markdown cell specification
            
        Returns:
            Dictionary with markdown cell configuration
        """
        print(f"📝 {self.name}: Adding markdown cell to document {document_id}")
        
        if document_id not in self.documents:
            raise ValueError(f"Document {document_id} not found")
        
        document = self.documents[document_id]
        
        cell_id = cell_spec.get("cell_id", f"cell_{len(document.cells) + 1}")
        content = cell_spec.get("content", "")
        format_type = cell_spec.get("format", "markdown")
        
        # Create markdown cell
        markdown_cell = QuartoMarkdownCell(
            cell_id=cell_id,
            content=content,
            format=format_type
        )
        
        document.cells.append(markdown_cell)
        
        # Generate cell code
        cell_code = self._generate_markdown_cell_code(markdown_cell)
        
        result = {
            "document_id": document_id,
            "cell_id": cell_id,
            "content": content,
            "format": format_type,
            "cell_code": cell_code,
            "status": "added"
        }
        
        print(f"✅ {self.name}: Markdown cell {cell_id} added to document {document_id}")
        return result
    
    def _generate_markdown_cell_code(self, cell: QuartoMarkdownCell) -> str:
        """Generate markdown cell content"""
        if cell.format == "markdown":
            code = f"""## Markdown Cell: {cell.cell_id}

{cell.content}

---
"""
        elif cell.format == "html":
            code = f"""## HTML Cell: {cell.cell_id}

::: {{html}}
{cell.content}
:::

---
"""
        else:
            code = f"""## Text Cell: {cell.cell_id}

```
{cell.content}
```

---
"""
        
        return code
    
    async def render_document(self, document_id: str, render_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Render a Quarto document
        
        Args:
            document_id: ID of the document to render
            render_spec: Render specification
            
        Returns:
            Dictionary with render results
        """
        print(f"🎨 {self.name}: Rendering document {document_id}")
        
        if document_id not in self.documents:
            raise ValueError(f"Document {document_id} not found")
        
        document = self.documents[document_id]
        
        # Get render formats
        formats_str = render_spec.get("formats", [fmt.value for fmt in document.formats])
        output_dir = render_spec.get("output_dir", "output")
        
        # Validate formats
        formats = []
        for fmt_str in formats_str:
            try:
                formats.append(QuartoFormat(fmt_str))
            except ValueError:
                print(f"⚠️  Format {fmt_str} not supported")
        
        if not formats:
            formats = document.formats
        
        # Simulate rendering
        render_results = {
            "document_id": document_id,
            "title": document.title,
            "formats": [fmt.value for fmt in formats],
            "output_dir": output_dir,
            "files_generated": [],
            "warnings": [],
            "errors": [],
            "execution_time": 0.0,
            "status": "completed"
        }
        
        # Generate output files
        for fmt in formats:
            if fmt == QuartoFormat.HTML:
                render_results["files_generated"].append(f"{output_dir}/{document.document_id}.html")
            elif fmt == QuartoFormat.PDF:
                render_results["files_generated"].append(f"{output_dir}/{document.document_id}.pdf")
            elif fmt == QuartoFormat.DOCX:
                render_results["files_generated"].append(f"{output_dir}/{document.document_id}.docx")
            elif fmt == QuartoFormat.PPTX:
                render_results["files_generated"].append(f"{output_dir}/{document.document_id}.pptx")
            elif fmt == QuartoFormat.MARKDOWN:
                render_results["files_generated"].append(f"{output_dir}/{document.document_id}.md")
            elif fmt == QuartoFormat.JUPYTER:
                render_results["files_generated"].append(f"{output_dir}/{document.document_id}.ipynb")
        
        # Generate render command
        render_command = self._generate_render_command(document, formats, output_dir)
        render_results["command"] = render_command
        
        print(f"✅ {self.name}: Document {document_id} rendered to {len(formats)} formats")
        return render_results
    
    def _generate_render_command(self, document: QuartoDocument, formats: List[QuartoFormat], output_dir: str) -> str:
        """Generate Quarto render command"""
        format_args = ", ".join([fmt.value for fmt in formats])
        
        command = f"quarto render {document.document_id}.qmd --to {format_args} --output-dir {output_dir}"
        
        # Add engine-specific options
        if document.engine == QuartoEngine.JUPYTER:
            command += " --execute"
        
        return command
    
    async def validate_document(self, document_id: str) -> Dict[str, Any]:
        """
        Validate a Quarto document
        
        Args:
            document_id: ID of the document to validate
            
        Returns:
            Dictionary with validation results
        """
        print(f"✅ {self.name}: Validating document {document_id}")
        
        if document_id not in self.documents:
            raise ValueError(f"Document {document_id} not found")
        
        document = self.documents[document_id]
        
        validation = {
            "document": document_id,
            "title": document.title,
            "valid": True,
            "warnings": [],
            "errors": [],
            "recommendations": []
        }
        
        # Check document title
        if not document.title:
            validation["valid"] = False
            validation["errors"].append("Document title is required")
        
        # Check for cells
        if not document.cells:
            validation["warnings"].append("Document has no cells")
        else:
            # Check each cell
            code_cell_count = 0
            for cell in document.cells:
                if isinstance(cell, QuartoCodeCell):
                    code_cell_count += 1
                    if not cell.code.strip():
                        validation["warnings"].append(f"Code cell {cell.cell_id} is empty")
                elif isinstance(cell, QuartoMarkdownCell):
                    if not cell.content.strip():
                        validation["warnings"].append(f"Markdown cell {cell.cell_id} is empty")
            
            if code_cell_count == 0:
                validation["recommendations"].append("Consider adding code cells for executable content")
        
        # Check formats
        if not document.formats:
            validation["warnings"].append("No output formats specified")
        
        # Check metadata
        if not document.metadata:
            validation["recommendations"].append("Consider adding metadata for better document organization")
        
        # Check for bibliography if citations exist
        if document.citations and not document.bibliography:
            validation["warnings"].append("Document has citations but no bibliography file specified")
        
        print(f"✅ {self.name}: Document {document_id} validation completed")
        return validation
    
    async def generate_document_documentation(self, document_id: str) -> Dict[str, Any]:
        """
        Generate documentation for a document
        
        Args:
            document_id: ID of the document
            
        Returns:
            Dictionary with documentation
        """
        print(f"📚 {self.name}: Generating documentation for document {document_id}")
        
        if document_id not in self.documents:
            raise ValueError(f"Document {document_id} not found")
        
        document = self.documents[document_id]
        
        documentation = {
            "document": {
                "id": document.document_id,
                "title": document.title,
                "type": document.document_type.value,
                "formats": [fmt.value for fmt in document.formats],
                "engine": document.engine.value,
                "language": document.language.value,
                "metadata": document.metadata,
                "bibliography": document.bibliography,
                "citations": document.citations
            },
            "cells": [],
            "structure": {},
            "usage": {}
        }
        
        # Document cells
        for cell in document.cells:
            if isinstance(cell, QuartoCodeCell):
                cell_doc = {
                    "cell_id": cell.cell_id,
                    "type": "code",
                    "language": cell.language.value,
                    "code": cell.code,
                    "echo": cell.echo,
                    "eval": cell.eval,
                    "output": cell.output,
                    "error": cell.error,
                    "execution_time": cell.execution_time
                }
                documentation["cells"].append(cell_doc)
            elif isinstance(cell, QuartoMarkdownCell):
                cell_doc = {
                    "cell_id": cell.cell_id,
                    "type": "markdown",
                    "format": cell.format,
                    "content": cell.content
                }
                documentation["cells"].append(cell_doc)
        
        # Generate structure
        documentation["structure"] = {
            "code_cells": len([c for c in document.cells if isinstance(c, QuartoCodeCell)]),
            "markdown_cells": len([c for c in document.cells if isinstance(c, QuartoMarkdownCell)]),
            "total_cells": len(document.cells),
            "languages": list(set([c.language.value for c in document.cells if isinstance(c, QuartoCodeCell)])),
            "formats": [fmt.value for fmt in document.formats]
        }
        
        # Generate usage examples
        document_content = self._generate_document_content(document)
        render_command = self._generate_render_command(document, document.formats, "output")
        
        documentation["usage"] = {
            "content": document_content,
            "render_command": render_command,
            "instructions": f'''
# Working with {document.title}

## Rendering the Document

1. Save the document content to `{document.document_id}.qmd`
2. Run the render command:

```bash
{render_command}
```

3. Check the output directory for rendered files

## Editing the Document

1. Open `{document.document_id}.qmd` in your preferred editor
2. Add or modify cells as needed
3. Re-render to see changes

## Adding Code Cells

```markdown
```{{{document.language.value}}}
# Your code here
print("Hello from {document.language.value}!")
```
```

## Adding Markdown Cells

```markdown
## Section Title

Your content here.
```
'''
        }
        
        print(f"✅ {self.name}: Documentation generated for document {document_id}")
        return documentation
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "current_project": self.current_project,
            "current_document": self.current_document,
            "projects_count": len(self.projects),
            "documents_count": len(self.documents),
            "performance_metrics": self.performance_metrics,
            "skills": list(self.skills.keys())
        }
    
    def reset(self) -> None:
        """Reset agent state"""
        self.current_project = None
        self.current_document = None
        self.projects.clear()
        self.documents.clear()
        self.performance_metrics.clear()
        print(f"🔄 {self.name}: Agent state reset")
