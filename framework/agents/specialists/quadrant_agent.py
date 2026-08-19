"""
Quadrant Agent - Specialist for Quadrant Data Visualization

Responsibilities:
- Dashboard design and creation
- Data source configuration
- Visualization setup
- Layout management
- Interactive features
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import asyncio


class QuadrantComponent(Enum):
    """Quadrant component types"""
    DASHBOARD = "dashboard"
    PAGE = "page"
    VISUALIZATION = "visualization"
    DATA_SOURCE = "data_source"
    LAYOUT = "layout"
    FILTER = "filter"
    PARAMETER = "parameter"


class QuadrantVisualizationType(Enum):
    """Quadrant visualization types"""
    TABLE = "table"
    CHART = "chart"
    GRAPH = "graph"
    MAP = "map"
    GAUGE = "gauge"
    CARD = "card"
    TEXT = "text"
    IMAGE = "image"
    PIVOT_TABLE = "pivot_table"
    HEATMAP = "heatmap"


class QuadrantChartType(Enum):
    """Quadrant chart types"""
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    SCATTER = "scatter"
    AREA = "area"
    COLUMN = "column"
    DONUT = "donut"
    RADAR = "radar"
    BUBBLE = "bubble"
    BOX_PLOT = "box_plot"


@dataclass
class QuadrantDataSource:
    """Represents a Quadrant data source"""
    name: str
    source_type: str  # "database", "api", "file", "custom"
    connection_string: Optional[str] = None
    query: Optional[str] = None
    file_path: Optional[str] = None
    file_format: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    refresh_interval: Optional[int] = None


@dataclass
class QuadrantVisualization:
    """Represents a Quadrant visualization"""
    viz_id: str
    name: str
    viz_type: QuadrantVisualizationType
    chart_type: Optional[QuadrantChartType] = None
    data_source: Optional[str] = None
    x_axis: Optional[str] = None
    y_axis: Optional[str] = None
    series: List[str] = field(default_factory=list)
    filters: Dict[str, Any] = field(default_factory=dict)
    settings: Dict[str, Any] = field(default_factory=dict)
    position: Dict[str, Any] = field(default_factory=dict)
    size: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QuadrantPage:
    """Represents a Quadrant dashboard page"""
    page_id: str
    name: str
    layout: str = "grid"  # "grid", "freeform", "tabs"
    visualizations: List[str] = field(default_factory=list)
    filters: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QuadrantDashboard:
    """Represents a Quadrant dashboard"""
    dashboard_id: str
    name: str
    description: str = ""
    pages: Dict[str, QuadrantPage] = field(default_factory=dict)
    data_sources: Dict[str, QuadrantDataSource] = field(default_factory=dict)
    visualizations: Dict[str, QuadrantVisualization] = field(default_factory=dict)
    theme: Dict[str, Any] = field(default_factory=dict)
    settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QuadrantAgent:
    """
    Quadrant Specialist Agent
    
    This agent specializes in Quadrant data visualization and dashboard creation.
    It can design and implement interactive dashboards with various visualizations.
    """
    
    agent_id: str = "quadrant_agent_001"
    name: str = "Quadrant Specialist"
    description: str = "Expert in Quadrant data visualization and dashboard creation"
    version: str = "1.0.0"
    
    # Agent capabilities
    supported_viz_types: List[QuadrantVisualizationType] = field(default_factory=lambda: [
        QuadrantVisualizationType.TABLE,
        QuadrantVisualizationType.CHART,
        QuadrantVisualizationType.GRAPH,
        QuadrantVisualizationType.MAP,
        QuadrantVisualizationType.GAUGE,
        QuadrantVisualizationType.CARD,
        QuadrantVisualizationType.TEXT,
        QuadrantVisualizationType.PIVOT_TABLE,
        QuadrantVisualizationType.HEATMAP,
    ])
    
    supported_chart_types: List[QuadrantChartType] = field(default_factory=lambda: [
        QuadrantChartType.BAR,
        QuadrantChartType.LINE,
        QuadrantChartType.PIE,
        QuadrantChartType.SCATTER,
        QuadrantChartType.AREA,
        QuadrantChartType.COLUMN,
        QuadrantChartType.DONUT,
        QuadrantChartType.RADAR,
        QuadrantChartType.BUBBLE,
        QuadrantChartType.BOX_PLOT,
    ])
    
    # Agent skills
    skills: Dict[str, str] = field(default_factory=dict)
    
    # Current project state
    current_project: Optional[str] = None
    current_dashboard: Optional[str] = None
    
    # Dashboards being developed
    dashboards: Dict[str, QuadrantDashboard] = field(default_factory=dict)
    
    # Data sources
    data_sources: Dict[str, QuadrantDataSource] = field(default_factory=dict)
    
    # Visualizations
    visualizations: Dict[str, QuadrantVisualization] = field(default_factory=dict)
    
    # Performance metrics
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize the agent with default skills"""
        self._initialize_skills()
    
    def _initialize_skills(self) -> None:
        """Initialize the agent's skill set"""
        self.skills = {
            "dashboard_design": "Design effective dashboards with proper layout and organization",
            "data_source_configuration": "Configure data sources for various data providers",
            "visualization_creation": "Create various types of visualizations for data representation",
            "layout_management": "Manage dashboard layouts and component positioning",
            "interactivity": "Implement interactive features and user controls",
            "filtering": "Set up filters and parameters for data exploration",
            "theming": "Apply consistent theming and styling across dashboards",
            "performance_optimization": "Optimize dashboard performance and loading times",
            "responsive_design": "Design dashboards that work well on different screen sizes",
            "testing": "Test dashboards and validate their functionality",
            "documentation": "Document dashboards and their components",
            "deployment": "Deploy dashboards to production environments"
        }
    
    async def create_dashboard(self, dashboard_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new Quadrant dashboard
        
        Args:
            dashboard_spec: Dashboard specification
            
        Returns:
            Dictionary with dashboard configuration
        """
        print(f"🚀 {self.name}: Creating dashboard {dashboard_spec.get('name', 'Unnamed')}")
        
        dashboard_id = dashboard_spec.get("dashboard_id", f"dashboard_{len(self.dashboards) + 1}")
        dashboard_name = dashboard_spec.get("name", "Unnamed Dashboard")
        description = dashboard_spec.get("description", "")
        theme = dashboard_spec.get("theme", {"primary_color": "#007bff", "background": "#ffffff"})
        settings = dashboard_spec.get("settings", {})
        
        # Create dashboard
        dashboard = QuadrantDashboard(
            dashboard_id=dashboard_id,
            name=dashboard_name,
            description=description,
            theme=theme,
            settings=settings
        )
        
        self.dashboards[dashboard_id] = dashboard
        self.current_dashboard = dashboard_id
        
        # Generate dashboard configuration
        dashboard_config = self._generate_dashboard_config(dashboard)
        
        result = {
            "dashboard_id": dashboard_id,
            "name": dashboard_name,
            "description": description,
            "theme": theme,
            "settings": settings,
            "config": dashboard_config,
            "status": "created"
        }
        
        print(f"✅ {self.name}: Dashboard {dashboard_name} created with ID {dashboard_id}")
        return result
    
    def _generate_dashboard_config(self, dashboard: QuadrantDashboard) -> Dict[str, Any]:
        """Generate dashboard configuration"""
        config = {
            "name": dashboard.name,
            "description": dashboard.description,
            "theme": dashboard.theme,
            "settings": dashboard.settings,
            "pages": [],
            "data_sources": [],
            "visualizations": []
        }
        
        # Add pages
        for page_id, page in dashboard.pages.items():
            page_config = {
                "page_id": page.page_id,
                "name": page.name,
                "layout": page.layout,
                "visualizations": page.visualizations,
                "filters": page.filters,
                "parameters": page.parameters
            }
            config["pages"].append(page_config)
        
        # Add data sources
        for ds_id, ds in dashboard.data_sources.items():
            ds_config = {
                "name": ds.name,
                "source_type": ds.source_type,
                "connection_string": ds.connection_string,
                "query": ds.query,
                "file_path": ds.file_path,
                "file_format": ds.file_format,
                "parameters": ds.parameters,
                "refresh_interval": ds.refresh_interval
            }
            config["data_sources"].append(ds_config)
        
        # Add visualizations
        for viz_id, viz in dashboard.visualizations.items():
            viz_config = {
                "viz_id": viz.viz_id,
                "name": viz.name,
                "viz_type": viz.viz_type.value,
                "chart_type": viz.chart_type.value if viz.chart_type else None,
                "data_source": viz.data_source,
                "x_axis": viz.x_axis,
                "y_axis": viz.y_axis,
                "series": viz.series,
                "filters": viz.filters,
                "settings": viz.settings,
                "position": viz.position,
                "size": viz.size
            }
            config["visualizations"].append(viz_config)
        
        return config
    
    async def add_data_source(self, dashboard_id: str, data_source_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a data source to a dashboard
        
        Args:
            dashboard_id: ID of the dashboard
            data_source_spec: Data source specification
            
        Returns:
            Dictionary with data source configuration
        """
        print(f"📊 {self.name}: Adding data source to dashboard {dashboard_id}")
        
        if dashboard_id not in self.dashboards:
            raise ValueError(f"Dashboard {dashboard_id} not found")
        
        dashboard = self.dashboards[dashboard_id]
        
        ds_id = data_source_spec.get("ds_id", f"ds_{len(dashboard.data_sources) + 1}")
        ds_name = data_source_spec.get("name", "Unnamed Data Source")
        source_type = data_source_spec.get("source_type", "database")
        connection_string = data_source_spec.get("connection_string")
        query = data_source_spec.get("query")
        file_path = data_source_spec.get("file_path")
        file_format = data_source_spec.get("file_format")
        parameters = data_source_spec.get("parameters", {})
        refresh_interval = data_source_spec.get("refresh_interval")
        
        # Create data source
        data_source = QuadrantDataSource(
            name=ds_name,
            source_type=source_type,
            connection_string=connection_string,
            query=query,
            file_path=file_path,
            file_format=file_format,
            parameters=parameters,
            refresh_interval=refresh_interval
        )
        
        dashboard.data_sources[ds_id] = data_source
        self.data_sources[ds_id] = data_source
        
        # Generate data source configuration
        ds_config = self._generate_data_source_config(data_source)
        
        result = {
            "dashboard_id": dashboard_id,
            "ds_id": ds_id,
            "name": ds_name,
            "source_type": source_type,
            "config": ds_config,
            "status": "added"
        }
        
        print(f"✅ {self.name}: Data source {ds_name} added to dashboard {dashboard_id}")
        return result
    
    def _generate_data_source_config(self, data_source: QuadrantDataSource) -> Dict[str, Any]:
        """Generate data source configuration"""
        config = {
            "name": data_source.name,
            "type": data_source.source_type,
            "parameters": data_source.parameters
        }
        
        if data_source.source_type == "database":
            config["connection_string"] = data_source.connection_string
            config["query"] = data_source.query
        elif data_source.source_type == "api":
            config["url"] = data_source.connection_string
            config["method"] = data_source.parameters.get("method", "GET")
            config["headers"] = data_source.parameters.get("headers", {})
        elif data_source.source_type == "file":
            config["path"] = data_source.file_path
            config["format"] = data_source.file_format
        
        if data_source.refresh_interval:
            config["refresh_interval"] = data_source.refresh_interval
        
        return config
    
    async def add_page(self, dashboard_id: str, page_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a page to a dashboard
        
        Args:
            dashboard_id: ID of the dashboard
            page_spec: Page specification
            
        Returns:
            Dictionary with page configuration
        """
        print(f"📄 {self.name}: Adding page to dashboard {dashboard_id}")
        
        if dashboard_id not in self.dashboards:
            raise ValueError(f"Dashboard {dashboard_id} not found")
        
        dashboard = self.dashboards[dashboard_id]
        
        page_id = page_spec.get("page_id", f"page_{len(dashboard.pages) + 1}")
        page_name = page_spec.get("name", "Unnamed Page")
        layout = page_spec.get("layout", "grid")
        visualizations = page_spec.get("visualizations", [])
        filters = page_spec.get("filters", {})
        parameters = page_spec.get("parameters", {})
        
        # Create page
        page = QuadrantPage(
            page_id=page_id,
            name=page_name,
            layout=layout,
            visualizations=visualizations,
            filters=filters,
            parameters=parameters
        )
        
        dashboard.pages[page_id] = page
        
        # Generate page configuration
        page_config = self._generate_page_config(page)
        
        result = {
            "dashboard_id": dashboard_id,
            "page_id": page_id,
            "name": page_name,
            "layout": layout,
            "visualizations": visualizations,
            "config": page_config,
            "status": "added"
        }
        
        print(f"✅ {self.name}: Page {page_name} added to dashboard {dashboard_id}")
        return result
    
    def _generate_page_config(self, page: QuadrantPage) -> Dict[str, Any]:
        """Generate page configuration"""
        config = {
            "page_id": page.page_id,
            "name": page.name,
            "layout": page.layout,
            "visualizations": page.visualizations,
            "filters": page.filters,
            "parameters": page.parameters
        }
        
        if page.layout == "grid":
            config["grid_settings"] = {
                "columns": 12,
                "gap": "16px",
                "responsive": True
            }
        elif page.layout == "freeform":
            config["freeform_settings"] = {
                "snap_to_grid": True,
                "grid_size": "8px"
            }
        elif page.layout == "tabs":
            config["tab_settings"] = {
                "tab_position": "top",
                "tab_style": "default"
            }
        
        return config
    
    async def add_visualization(self, dashboard_id: str, viz_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a visualization to a dashboard
        
        Args:
            dashboard_id: ID of the dashboard
            viz_spec: Visualization specification
            
        Returns:
            Dictionary with visualization configuration
        """
        print(f"📊 {self.name}: Adding visualization to dashboard {dashboard_id}")
        
        if dashboard_id not in self.dashboards:
            raise ValueError(f"Dashboard {dashboard_id} not found")
        
        dashboard = self.dashboards[dashboard_id]
        
        viz_id = viz_spec.get("viz_id", f"viz_{len(dashboard.visualizations) + 1}")
        viz_name = viz_spec.get("name", "Unnamed Visualization")
        viz_type_str = viz_spec.get("viz_type", "chart")
        chart_type_str = viz_spec.get("chart_type", "bar")
        data_source = viz_spec.get("data_source")
        x_axis = viz_spec.get("x_axis")
        y_axis = viz_spec.get("y_axis")
        series = viz_spec.get("series", [])
        filters = viz_spec.get("filters", {})
        settings = viz_spec.get("settings", {})
        position = viz_spec.get("position", {"x": 0, "y": 0})
        size = viz_spec.get("size", {"width": 400, "height": 300})
        
        # Validate visualization type
        try:
            viz_type = QuadrantVisualizationType(viz_type_str)
        except ValueError:
            viz_type = QuadrantVisualizationType.CHART
            print(f"⚠️  Visualization type {viz_type_str} not supported, defaulting to Chart")
        
        # Validate chart type
        chart_type = None
        if viz_type == QuadrantVisualizationType.CHART:
            try:
                chart_type = QuadrantChartType(chart_type_str)
            except ValueError:
                chart_type = QuadrantChartType.BAR
                print(f"⚠️  Chart type {chart_type_str} not supported, defaulting to Bar")
        
        # Create visualization
        visualization = QuadrantVisualization(
            viz_id=viz_id,
            name=viz_name,
            viz_type=viz_type,
            chart_type=chart_type,
            data_source=data_source,
            x_axis=x_axis,
            y_axis=y_axis,
            series=series,
            filters=filters,
            settings=settings,
            position=position,
            size=size
        )
        
        dashboard.visualizations[viz_id] = visualization
        self.visualizations[viz_id] = visualization
        
        # Generate visualization code
        viz_code = self._generate_visualization_code(visualization)
        
        result = {
            "dashboard_id": dashboard_id,
            "viz_id": viz_id,
            "name": viz_name,
            "viz_type": viz_type.value,
            "chart_type": chart_type.value if chart_type else None,
            "data_source": data_source,
            "x_axis": x_axis,
            "y_axis": y_axis,
            "series": series,
            "code": viz_code,
            "status": "added"
        }
        
        print(f"✅ {self.name}: Visualization {viz_name} ({viz_type.value}) added to dashboard {dashboard_id}")
        return result
    
    def _generate_visualization_code(self, visualization: QuadrantVisualization) -> str:
        """Generate visualization configuration code"""
        if visualization.viz_type == QuadrantVisualizationType.TABLE:
            code = f'''
// Table Visualization: {visualization.name}
{{
    "type": "table",
    "name": "{visualization.name}",
    "data_source": "{visualization.data_source}",
    "columns": {json.dumps(visualization.series, indent=4)},
    "settings": {json.dumps(visualization.settings, indent=4)},
    "position": {json.dumps(visualization.position)},
    "size": {json.dumps(visualization.size)},
    "filters": {json.dumps(visualization.filters, indent=4)}
}}
'''
        elif visualization.viz_type == QuadrantVisualizationType.CHART and visualization.chart_type:
            code = f'''
// Chart Visualization: {visualization.name}
{{
    "type": "chart",
    "chart_type": "{visualization.chart_type.value}",
    "name": "{visualization.name}",
    "data_source": "{visualization.data_source}",
    "x_axis": "{visualization.x_axis}",
    "y_axis": "{visualization.y_axis}",
    "series": {json.dumps(visualization.series, indent=4)},
    "settings": {json.dumps(visualization.settings, indent=4)},
    "position": {json.dumps(visualization.position)},
    "size": {json.dumps(visualization.size)},
    "filters": {json.dumps(visualization.filters, indent=4)}
}}
'''
        elif visualization.viz_type == QuadrantVisualizationType.GAUGE:
            code = f'''
// Gauge Visualization: {visualization.name}
{{
    "type": "gauge",
    "name": "{visualization.name}",
    "data_source": "{visualization.data_source}",
    "value_field": "{visualization.x_axis}",
    "min": {visualization.settings.get("min", 0)},
    "max": {visualization.settings.get("max", 100)},
    "thresholds": {json.dumps(visualization.settings.get("thresholds", []))},
    "position": {json.dumps(visualization.position)},
    "size": {json.dumps(visualization.size)}
}}
'''
        elif visualization.viz_type == QuadrantVisualizationType.CARD:
            code = f'''
// Card Visualization: {visualization.name}
{{
    "type": "card",
    "name": "{visualization.name}",
    "data_source": "{visualization.data_source}",
    "value_field": "{visualization.x_axis}",
    "title": "{visualization.settings.get("title", visualization.name)}",
    "subtitle": "{visualization.settings.get("subtitle", "")}",
    "format": "{visualization.settings.get("format", "number")}",
    "position": {json.dumps(visualization.position)},
    "size": {json.dumps(visualization.size)}
}}
'''
        else:
            code = f'''
// Generic Visualization: {visualization.name}
{{
    "type": "{visualization.viz_type.value}",
    "name": "{visualization.name}",
    "data_source": "{visualization.data_source}",
    "settings": {json.dumps(visualization.settings, indent=4)},
    "position": {json.dumps(visualization.position)},
    "size": {json.dumps(visualization.size)},
    "filters": {json.dumps(visualization.filters, indent=4)}
}}
'''
        
        return code
    
    async def validate_dashboard(self, dashboard_id: str) -> Dict[str, Any]:
        """
        Validate a dashboard configuration
        
        Args:
            dashboard_id: ID of the dashboard to validate
            
        Returns:
            Dictionary with validation results
        """
        print(f"✅ {self.name}: Validating dashboard {dashboard_id}")
        
        if dashboard_id not in self.dashboards:
            raise ValueError(f"Dashboard {dashboard_id} not found")
        
        dashboard = self.dashboards[dashboard_id]
        
        validation = {
            "dashboard": dashboard_id,
            "valid": True,
            "warnings": [],
            "errors": [],
            "recommendations": []
        }
        
        # Check dashboard name
        if not dashboard.name:
            validation["valid"] = False
            validation["errors"].append("Dashboard name is required")
        
        # Check for pages
        if not dashboard.pages:
            validation["warnings"].append("Dashboard has no pages")
        else:
            # Check each page
            for page_id, page in dashboard.pages.items():
                if not page.name:
                    validation["warnings"].append(f"Page {page_id} has no name")
                
                if not page.visualizations:
                    validation["warnings"].append(f"Page {page.name} has no visualizations")
        
        # Check for data sources
        if not dashboard.data_sources:
            validation["warnings"].append("Dashboard has no data sources")
        else:
            # Check each data source
            for ds_id, ds in dashboard.data_sources.items():
                if not ds.name:
                    validation["warnings"].append(f"Data source {ds_id} has no name")
                
                if not ds.source_type:
                    validation["errors"].append(f"Data source {ds.name} has no source type")
        
        # Check for visualizations
        if not dashboard.visualizations:
            validation["warnings"].append("Dashboard has no visualizations")
        else:
            # Check each visualization
            for viz_id, viz in dashboard.visualizations.items():
                if not viz.name:
                    validation["warnings"].append(f"Visualization {viz_id} has no name")
                
                if not viz.data_source:
                    validation["warnings"].append(f"Visualization {viz.name} has no data source")
                
                if viz.viz_type == QuadrantVisualizationType.CHART and not viz.chart_type:
                    validation["warnings"].append(f"Chart visualization {viz.name} has no chart type")
        
        # Generate recommendations
        if len(dashboard.pages) > 5:
            validation["recommendations"].append("Consider breaking down large dashboards into multiple focused dashboards")
        
        if len(dashboard.visualizations) > 20:
            validation["recommendations"].append("Consider organizing visualizations across multiple pages for better usability")
        
        if not dashboard.theme:
            validation["recommendations"].append("Consider adding a theme for consistent styling")
        
        print(f"✅ {self.name}: Dashboard {dashboard_id} validation completed")
        return validation
    
    async def generate_dashboard_documentation(self, dashboard_id: str) -> Dict[str, Any]:
        """
        Generate documentation for a dashboard
        
        Args:
            dashboard_id: ID of the dashboard
            
        Returns:
            Dictionary with documentation
        """
        print(f"📚 {self.name}: Generating documentation for dashboard {dashboard_id}")
        
        if dashboard_id not in self.dashboards:
            raise ValueError(f"Dashboard {dashboard_id} not found")
        
        dashboard = self.dashboards[dashboard_id]
        
        documentation = {
            "dashboard": {
                "id": dashboard.dashboard_id,
                "name": dashboard.name,
                "description": dashboard.description,
                "theme": dashboard.theme,
                "settings": dashboard.settings
            },
            "pages": [],
            "data_sources": [],
            "visualizations": [],
            "usage": {}
        }
        
        # Document pages
        for page_id, page in dashboard.pages.items():
            page_doc = {
                "page_id": page.page_id,
                "name": page.name,
                "layout": page.layout,
                "visualizations": page.visualizations,
                "filters": page.filters,
                "parameters": page.parameters
            }
            documentation["pages"].append(page_doc)
        
        # Document data sources
        for ds_id, ds in dashboard.data_sources.items():
            ds_doc = {
                "ds_id": ds_id,
                "name": ds.name,
                "source_type": ds.source_type,
                "connection_string": ds.connection_string,
                "query": ds.query,
                "file_path": ds.file_path,
                "file_format": ds.file_format,
                "parameters": ds.parameters,
                "refresh_interval": ds.refresh_interval
            }
            documentation["data_sources"].append(ds_doc)
        
        # Document visualizations
        for viz_id, viz in dashboard.visualizations.items():
            viz_doc = {
                "viz_id": viz.viz_id,
                "name": viz.name,
                "viz_type": viz.viz_type.value,
                "chart_type": viz.chart_type.value if viz.chart_type else None,
                "data_source": viz.data_source,
                "x_axis": viz.x_axis,
                "y_axis": viz.y_axis,
                "series": viz.series,
                "filters": viz.filters,
                "settings": viz.settings,
                "position": viz.position,
                "size": viz.size
            }
            documentation["visualizations"].append(viz_doc)
        
        # Generate usage examples
        dashboard_config = self._generate_dashboard_config(dashboard)
        documentation["usage"] = {
            "import": f'''
# Import dashboard configuration

```json
{json.dumps(dashboard_config, indent=2)}
```

# Usage instructions:
1. Open Quadrant editor
2. Click "Import" button
3. Paste the JSON configuration above
4. Click "Import" to create the dashboard
''',
            "customization": f'''
# Customizing the {dashboard.name} Dashboard

## Adding New Visualizations

1. Click "Add Visualization" button
2. Select visualization type
3. Configure data source and settings
4. Position and size the visualization

## Modifying Data Sources

1. Click "Data Sources" tab
2. Select the data source to modify
3. Update connection details or query
4. Save changes

## Sharing the Dashboard

1. Click "Share" button
2. Configure access permissions
3. Copy the shareable link
4. Send to team members
''',
            "best_practices": """
# Dashboard Design Best Practices

## Layout
- Use grid layout for structured dashboards
- Use freeform layout for creative designs
- Keep important visualizations at the top
- Group related visualizations together

## Data Sources
- Use parameterized queries for flexibility
- Set appropriate refresh intervals
- Handle errors gracefully
- Cache data when possible

## Visualizations
- Choose the right visualization type for your data
- Use consistent styling and colors
- Add clear titles and labels
- Limit the number of visualizations per page

## Performance
- Limit the amount of data loaded at once
- Use pagination for large datasets
- Optimize queries for speed
- Consider using cached data for static dashboards
"""
        }
        
        print(f"✅ {self.name}: Documentation generated for dashboard {dashboard_id}")
        return documentation
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "current_project": self.current_project,
            "current_dashboard": self.current_dashboard,
            "dashboards_count": len(self.dashboards),
            "data_sources_count": len(self.data_sources),
            "visualizations_count": len(self.visualizations),
            "performance_metrics": self.performance_metrics,
            "skills": list(self.skills.keys())
        }
    
    def reset(self) -> None:
        """Reset agent state"""
        self.current_project = None
        self.current_dashboard = None
        self.dashboards.clear()
        self.data_sources.clear()
        self.visualizations.clear()
        self.performance_metrics.clear()
        print(f"🔄 {self.name}: Agent state reset")
