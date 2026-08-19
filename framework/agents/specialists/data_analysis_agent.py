"""
Data Analysis Agent - Specialist for Data Analysis and Processing

Responsibilities:
- Data cleaning and preprocessing
- Statistical analysis
- Machine learning model development
- Data visualization
- Feature engineering
- Data pipeline design
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime


class DataTechnology(Enum):
    """Supported data technologies"""
    PANDAS = "pandas"
    NUMPY = "numpy"
    PYSPARK = "pyspark"
    DASK = "dask"
    POLARS = "polars"
    SQL = "sql"
    R = "r"
    JULIA = "julia"


class AnalysisType(Enum):
    """Types of data analysis"""
    DESCRIPTIVE = "descriptive"
    INFERENTIAL = "inferential"
    PREDICTIVE = "predictive"
    PRESCRIPTIVE = "prescriptive"
    DIAGNOSTIC = "diagnostic"
    EXPLORATORY = "exploratory"


class MLTask(Enum):
    """Machine learning task types"""
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    CLUSTERING = "clustering"
    DIMENSIONALITY_REDUCTION = "dimensionality_reduction"
    TIME_SERIES = "time_series"
    NLP = "nlp"
    COMPUTER_VISION = "computer_vision"
    RECOMMENDATION = "recommendation"


@dataclass
class DataSkill:
    """Represents a data analysis skill"""
    name: str
    description: str
    technology: DataTechnology
    difficulty: str  # "beginner", "intermediate", "advanced"
    dependencies: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.difficulty not in ["beginner", "intermediate", "advanced"]:
            raise ValueError("Difficulty must be beginner, intermediate, or advanced")


@dataclass
class Dataset:
    """Represents a dataset specification"""
    name: str
    description: str
    source: str  # "file", "database", "api", "stream"
    format: str  # "csv", "json", "parquet", "sql", etc.
    size: Optional[int] = None
    columns: List[Dict[str, Any]] = field(default_factory=list)
    shape: Optional[tuple] = None
    dtypes: Optional[Dict[str, str]] = None
    sample: Optional[List[Dict[str, Any]]] = None


@dataclass
class DataPipeline:
    """Represents a data processing pipeline"""
    name: str
    description: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)


@dataclass
class DataAnalysisAgent:
    """
    Data Analysis Specialist Agent
    
    This agent specializes in data analysis, processing, and machine learning.
    It can work with various data technologies and analysis methods.
    """
    
    agent_id: str = "data_analysis_agent_001"
    name: str = "Data Analysis Specialist"
    description: str = "Expert in data analysis, processing, and machine learning"
    version: str = "1.0.0"
    
    # Agent capabilities
    supported_technologies: List[DataTechnology] = field(default_factory=lambda: [
        DataTechnology.PANDAS,
        DataTechnology.NUMPY,
        DataTechnology.SQL,
        DataTechnology.PYSPARK,
    ])
    
    supported_analysis_types: List[AnalysisType] = field(default_factory=lambda: [
        AnalysisType.DESCRIPTIVE,
        AnalysisType.EXPLORATORY,
        AnalysisType.PREDICTIVE,
        AnalysisType.CLUSTERING,
    ])
    
    supported_ml_tasks: List[MLTask] = field(default_factory=lambda: [
        MLTask.CLASSIFICATION,
        MLTask.REGRESSION,
        MLTask.CLUSTERING,
        MLTask.TIME_SERIES,
        MLTask.NLP,
    ])
    
    # Agent skills
    skills: Dict[str, DataSkill] = field(default_factory=dict)
    
    # Current project state
    current_project: Optional[str] = None
    current_technology: Optional[DataTechnology] = None
    current_analysis_type: Optional[AnalysisType] = None
    
    # Datasets being processed
    datasets: Dict[str, Dataset] = field(default_factory=dict)
    
    # Data pipelines
    pipelines: Dict[str, DataPipeline] = field(default_factory=dict)
    
    # Analysis results
    analysis_results: Dict[str, Dict] = field(default_factory=dict)
    
    # ML models
    ml_models: Dict[str, Dict] = field(default_factory=dict)
    
    # Performance metrics
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize the agent with default skills"""
        self._initialize_skills()
    
    def _initialize_skills(self) -> None:
        """Initialize the agent's skill set"""
        self.skills = {
            "data_cleaning": DataSkill(
                name="Data Cleaning",
                description="Clean and preprocess data: handle missing values, outliers, duplicates",
                technology=DataTechnology.PANDAS,
                difficulty="intermediate",
                dependencies=["data_inspection", "statistical_analysis"]
            ),
            "exploratory_analysis": DataSkill(
                name="Exploratory Data Analysis",
                description="Perform EDA: summary statistics, distributions, correlations, visualizations",
                technology=DataTechnology.PANDAS,
                difficulty="intermediate",
                dependencies=["data_cleaning", "visualization"]
            ),
            "feature_engineering": DataSkill(
                name="Feature Engineering",
                description="Create and transform features: encoding, scaling, feature selection",
                technology=DataTechnology.PANDAS,
                difficulty="intermediate",
                dependencies=["data_understanding", "domain_knowledge"]
            ),
            "statistical_analysis": DataSkill(
                name="Statistical Analysis",
                description="Perform statistical tests and analysis: hypothesis testing, confidence intervals",
                technology=DataTechnology.PANDAS,
                difficulty="intermediate",
                dependencies=["statistics_basics", "probability"]
            ),
            "machine_learning": DataSkill(
                name="Machine Learning",
                description="Develop ML models: classification, regression, clustering, etc.",
                technology=DataTechnology.PANDAS,
                difficulty="advanced",
                dependencies=["feature_engineering", "model_evaluation"]
            ),
            "deep_learning": DataSkill(
                name="Deep Learning",
                description="Develop deep learning models: neural networks, CNNs, RNNs, transformers",
                technology=DataTechnology.PANDAS,
                difficulty="advanced",
                dependencies=["machine_learning", "gpu_computing"]
            ),
            "data_visualization": DataSkill(
                name="Data Visualization",
                description="Create visualizations: charts, graphs, dashboards using Matplotlib, Seaborn, Plotly",
                technology=DataTechnology.PANDAS,
                difficulty="intermediate",
                dependencies=["data_understanding", "design_principles"]
            ),
            "data_pipelines": DataSkill(
                name="Data Pipelines",
                description="Design and implement data processing pipelines: ETL, ELT, workflows",
                technology=DataTechnology.PYSPARK,
                difficulty="advanced",
                dependencies=["distributed_computing", "workflow_management"]
            ),
            "big_data_processing": DataSkill(
                name="Big Data Processing",
                description="Process large datasets: distributed computing, parallel processing",
                technology=DataTechnology.PYSPARK,
                difficulty="advanced",
                dependencies=["distributed_systems", "scalability"]
            ),
            "time_series_analysis": DataSkill(
                name="Time Series Analysis",
                description="Analyze time series data: forecasting, trend analysis, seasonality",
                technology=DataTechnology.PANDAS,
                difficulty="advanced",
                dependencies=["statistics", "time_series_models"]
            ),
        }
    
    async def load_dataset(self, dataset_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Load a dataset from various sources
        
        Args:
            dataset_spec: Dataset specification
            
        Returns:
            Dictionary with loaded dataset information
        """
        print(f"📊 {self.name}: Loading dataset {dataset_spec.get('name', 'Unnamed')}")
        
        dataset_name = dataset_spec.get("name", "unnamed_dataset")
        source = dataset_spec.get("source", "file")
        format_type = dataset_spec.get("format", "csv")
        
        # Create dataset object
        dataset = Dataset(
            name=dataset_name,
            description=dataset_spec.get("description", ""),
            source=source,
            format=format_type,
            size=dataset_spec.get("size"),
            columns=dataset_spec.get("columns", []),
        )
        
        # Simulate loading data
        if source == "file" and format_type == "csv":
            # Create sample data
            data = {
                "id": [1, 2, 3, 4, 5],
                "name": ["Alice", "Bob", "Charlie", "Diana", "Eve"],
                "age": [25, 30, 35, 28, 32],
                "score": [85.5, 90.2, 78.9, 92.1, 88.7],
                "timestamp": [
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                ]
            }
            
            df = pd.DataFrame(data)
            dataset.shape = df.shape
            dataset.dtypes = df.dtypes.to_dict()
            dataset.sample = df.head(3).to_dict("records")
            
        elif source == "database":
            # Simulate database query
            data = {
                "id": [1, 2, 3],
                "value": [100, 200, 300],
                "category": ["A", "B", "C"]
            }
            
            df = pd.DataFrame(data)
            dataset.shape = df.shape
            dataset.dtypes = df.dtypes.to_dict()
            dataset.sample = df.to_dict("records")
        
        self.datasets[dataset_name] = dataset
        
        result = {
            "dataset_name": dataset_name,
            "source": source,
            "format": format_type,
            "shape": dataset.shape,
            "dtypes": dataset.dtypes,
            "sample": dataset.sample,
            "status": "loaded"
        }
        
        print(f"✅ {self.name}: Dataset {dataset_name} loaded successfully")
        return result
    
    async def perform_eda(self, dataset_name: str, analysis_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform Exploratory Data Analysis on a dataset
        
        Args:
            dataset_name: Name of the dataset to analyze
            analysis_spec: EDA specification
            
        Returns:
            Dictionary with EDA results
        """
        print(f"🔍 {self.name}: Performing EDA on dataset {dataset_name}")
        
        if dataset_name not in self.datasets:
            raise ValueError(f"Dataset {dataset_name} not found")
        
        dataset = self.datasets[dataset_name]
        
        # Create sample data for analysis
        if dataset.sample:
            df = pd.DataFrame(dataset.sample)
        else:
            # Generate sample data
            df = pd.DataFrame({
                "id": [1, 2, 3, 4, 5],
                "value": [10, 20, 30, 40, 50],
                "category": ["A", "B", "A", "B", "A"]
            })
        
        # Perform EDA
        eda_results = {
            "dataset": dataset_name,
            "shape": df.shape,
            "dtypes": df.dtypes.to_dict(),
            "summary_statistics": {},
            "missing_values": {},
            "correlations": {},
            "distributions": {},
            "visualizations": []
        }
        
        # Summary statistics
        for col in df.select_dtypes(include=[np.number]).columns:
            eda_results["summary_statistics"][col] = {
                "mean": float(df[col].mean()),
                "median": float(df[col].median()),
                "std": float(df[col].std()),
                "min": float(df[col].min()),
                "max": float(df[col].max()),
                "quartiles": {
                    "q1": float(df[col].quantile(0.25)),
                    "q2": float(df[col].quantile(0.5)),
                    "q3": float(df[col].quantile(0.75))
                }
            }
        
        # Missing values
        missing = df.isnull().sum()
        for col, count in missing.items():
            if count > 0:
                eda_results["missing_values"][col] = {
                    "count": int(count),
                    "percentage": float((count / len(df)) * 100)
                }
        
        # Correlations
        if len(df.select_dtypes(include=[np.number]).columns) > 1:
            corr_matrix = df.corr()
            eda_results["correlations"] = corr_matrix.to_dict()
        
        # Distributions
        for col in df.columns:
            if df[col].dtype == "object":
                value_counts = df[col].value_counts().to_dict()
                eda_results["distributions"][col] = {
                    "type": "categorical",
                    "value_counts": value_counts,
                    "unique_values": int(df[col].nunique())
                }
            else:
                eda_results["distributions"][col] = {
                    "type": "numerical",
                    "histogram": self._create_histogram(df[col])
                }
        
        # Generate visualization suggestions
        eda_results["visualizations"] = [
            {
                "type": "histogram",
                "columns": list(df.select_dtypes(include=[np.number]).columns),
                "description": "Distribution of numerical columns"
            },
            {
                "type": "bar_chart",
                "columns": list(df.select_dtypes(include=["object"]).columns),
                "description": "Value counts for categorical columns"
            },
            {
                "type": "scatter_matrix",
                "columns": list(df.select_dtypes(include=[np.number]).columns),
                "description": "Relationships between numerical columns"
            }
        ]
        
        # Store results
        analysis_id = f"eda_{dataset_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.analysis_results[analysis_id] = eda_results
        
        print(f"✅ {self.name}: EDA completed for dataset {dataset_name}")
        return eda_results
    
    def _create_histogram(self, series: pd.Series) -> Dict[str, Any]:
        """Create histogram data for a series"""
        hist, bin_edges = np.histogram(series.dropna(), bins=10)
        return {
            "counts": hist.tolist(),
            "bin_edges": bin_edges.tolist(),
            "bin_centers": [(bin_edges[i] + bin_edges[i+1]) / 2 for i in range(len(bin_edges)-1)]
        }
    
    async def clean_data(self, dataset_name: str, cleaning_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean and preprocess data
        
        Args:
            dataset_name: Name of the dataset to clean
            cleaning_spec: Cleaning specification
            
        Returns:
            Dictionary with cleaning results
        """
        print(f"🧹 {self.name}: Cleaning dataset {dataset_name}")
        
        if dataset_name not in self.datasets:
            raise ValueError(f"Dataset {dataset_name} not found")
        
        dataset = self.datasets[dataset_name]
        
        # Create sample data for cleaning
        if dataset.sample:
            df = pd.DataFrame(dataset.sample)
        else:
            df = pd.DataFrame({
                "id": [1, 2, 3, None, 5],
                "value": [10, None, 30, 40, 50],
                "category": ["A", "B", None, "B", "A"]
            })
        
        cleaning_results = {
            "dataset": dataset_name,
            "original_shape": df.shape,
            "actions_performed": [],
            "summary": {}
        }
        
        # Handle missing values
        missing_strategy = cleaning_spec.get("missing_values", {}).get("strategy", "drop")
        
        if missing_strategy == "drop":
            original_count = len(df)
            df_clean = df.dropna()
            dropped_count = original_count - len(df_clean)
            cleaning_results["actions_performed"].append({
                "action": "drop_missing_values",
                "rows_dropped": dropped_count,
                "columns_affected": list(df.columns[df.isnull().any()])
            })
        elif missing_strategy == "fill":
            fill_values = cleaning_spec.get("missing_values", {}).get("fill_values", {})
            for col, fill_value in fill_values.items():
                if col in df.columns:
                    df[col] = df[col].fillna(fill_value)
                    cleaning_results["actions_performed"].append({
                        "action": "fill_missing_values",
                        "column": col,
                        "fill_value": fill_value,
                        "missing_count": int(df[col].isnull().sum())
                    })
        
        # Handle duplicates
        if cleaning_spec.get("remove_duplicates", True):
            original_count = len(df)
            df_clean = df.drop_duplicates()
            duplicate_count = original_count - len(df_clean)
            cleaning_results["actions_performed"].append({
                "action": "remove_duplicates",
                "duplicates_removed": duplicate_count
            })
        
        # Handle outliers
        if cleaning_spec.get("handle_outliers", False):
            numerical_cols = df.select_dtypes(include=[np.number]).columns
            for col in numerical_cols:
                method = cleaning_spec.get("outliers", {}).get("method", "iqr")
                if method == "iqr":
                    Q1 = df[col].quantile(0.25)
                    Q3 = df[col].quantile(0.75)
                    IQR = Q3 - Q1
                    lower_bound = Q1 - 1.5 * IQR
                    upper_bound = Q3 + 1.5 * IQR
                    
                    outliers_mask = (df[col] < lower_bound) | (df[col] > upper_bound)
                    outlier_count = outliers_mask.sum()
                    
                    # Cap outliers
                    df[col] = np.clip(df[col], lower_bound, upper_bound)
                    
                    cleaning_results["actions_performed"].append({
                        "action": "handle_outliers",
                        "column": col,
                        "method": "IQR capping",
                        "outliers_capped": int(outlier_count),
                        "lower_bound": float(lower_bound),
                        "upper_bound": float(upper_bound)
                    })
        
        # Update dataset
        dataset.shape = df.shape
        dataset.dtypes = df.dtypes.to_dict()
        dataset.sample = df.head(3).to_dict("records")
        
        cleaning_results["final_shape"] = df.shape
        cleaning_results["summary"] = {
            "original_rows": cleaning_results["original_shape"][0],
            "final_rows": df.shape[0],
            "rows_removed": cleaning_results["original_shape"][0] - df.shape[0],
            "columns": list(df.columns)
        }
        
        print(f"✅ {self.name}: Data cleaning completed for dataset {dataset_name}")
        return cleaning_results
    
    async def perform_feature_engineering(self, dataset_name: str, feature_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform feature engineering on a dataset
        
        Args:
            dataset_name: Name of the dataset
            feature_spec: Feature engineering specification
            
        Returns:
            Dictionary with feature engineering results
        """
        print(f"🎯 {self.name}: Performing feature engineering on dataset {dataset_name}")
        
        if dataset_name not in self.datasets:
            raise ValueError(f"Dataset {dataset_name} not found")
        
        dataset = self.datasets[dataset_name]
        
        # Create sample data
        if dataset.sample:
            df = pd.DataFrame(dataset.sample)
        else:
            df = pd.DataFrame({
                "age": [25, 30, 35, 28, 32],
                "income": [50000, 75000, 60000, 80000, 55000],
                "category": ["A", "B", "A", "B", "A"]
            })
        
        feature_results = {
            "dataset": dataset_name,
            "original_features": list(df.columns),
            "new_features": [],
            "transformations": [],
            "final_features": []
        }
        
        # Create new features
        new_features = feature_spec.get("new_features", [])
        for feature in new_features:
            feature_name = feature.get("name")
            feature_type = feature.get("type")
            
            if feature_type == "binning":
                col = feature.get("column")
                bins = feature.get("bins", 5)
                labels = feature.get("labels", None)
                
                if col in df.columns:
                    df[feature_name] = pd.cut(df[col], bins=bins, labels=labels)
                    feature_results["new_features"].append(feature_name)
                    feature_results["transformations"].append({
                        "type": "binning",
                        "column": col,
                        "new_feature": feature_name,
                        "bins": bins,
                        "labels": labels
                    })
            
            elif feature_type == "encoding":
                col = feature.get("column")
                method = feature.get("method", "one_hot")
                
                if col in df.columns and df[col].dtype == "object":
                    if method == "one_hot":
                        dummies = pd.get_dummies(df[col], prefix=feature_name)
                        for dummy_col in dummies.columns:
                            df[dummy_col] = dummies[dummy_col]
                            feature_results["new_features"].append(dummy_col)
                        feature_results["transformations"].append({
                            "type": "one_hot_encoding",
                            "column": col,
                            "new_features": list(dummies.columns),
                            "prefix": feature_name
                        })
                    elif method == "label":
                        from sklearn.preprocessing import LabelEncoder
                        le = LabelEncoder()
                        df[feature_name] = le.fit_transform(df[col])
                        feature_results["new_features"].append(feature_name)
                        feature_results["transformations"].append({
                            "type": "label_encoding",
                            "column": col,
                            "new_feature": feature_name
                        })
            
            elif feature_type == "scaling":
                col = feature.get("column")
                method = feature.get("method", "standard")
                
                if col in df.columns:
                    if method == "standard":
                        from sklearn.preprocessing import StandardScaler
                        scaler = StandardScaler()
                        df[feature_name] = scaler.fit_transform(df[[col]])
                    elif method == "minmax":
                        from sklearn.preprocessing import MinMaxScaler
                        scaler = MinMaxScaler()
                        df[feature_name] = scaler.fit_transform(df[[col]])
                    
                    feature_results["new_features"].append(feature_name)
                    feature_results["transformations"].append({
                        "type": "scaling",
                        "column": col,
                        "new_feature": feature_name,
                        "method": method
                    })
            
            elif feature_type == "polynomial":
                col = feature.get("column")
                degree = feature.get("degree", 2)
                
                if col in df.columns:
                    for d in range(2, degree + 1):
                        new_col = f"{col}_pow_{d}"
                        df[new_col] = df[col] ** d
                        feature_results["new_features"].append(new_col)
                    
                    feature_results["transformations"].append({
                        "type": "polynomial_features",
                        "column": col,
                        "new_features": [f"{col}_pow_{d}" for d in range(2, degree + 1)],
                        "degree": degree
                    })
        
        # Feature selection
        if feature_spec.get("feature_selection", False):
            method = feature_spec.get("feature_selection_method", "variance_threshold")
            
            if method == "variance_threshold":
                from sklearn.feature_selection import VarianceThreshold
                selector = VarianceThreshold(threshold=0.1)
                X = df.select_dtypes(include=[np.number])
                selector.fit(X)
                
                selected_features = X.columns[selector.get_support()].tolist()
                removed_features = X.columns[~selector.get_support()].tolist()
                
                feature_results["transformations"].append({
                    "type": "feature_selection",
                    "method": "variance_threshold",
                    "selected_features": selected_features,
                    "removed_features": removed_features,
                    "threshold": 0.1
                })
                
                # Update df to only include selected features
                df = df[selected_features + [col for col in df.columns if col not in X.columns]]
        
        feature_results["final_features"] = list(df.columns)
        
        # Update dataset
        dataset.shape = df.shape
        dataset.dtypes = df.dtypes.to_dict()
        dataset.sample = df.head(3).to_dict("records")
        
        print(f"✅ {self.name}: Feature engineering completed for dataset {dataset_name}")
        return feature_results
    
    async def train_ml_model(self, dataset_name: str, model_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Train a machine learning model
        
        Args:
            dataset_name: Name of the dataset
            model_spec: Model specification
            
        Returns:
            Dictionary with training results
        """
        print(f"🤖 {self.name}: Training ML model on dataset {dataset_name}")
        
        if dataset_name not in self.datasets:
            raise ValueError(f"Dataset {dataset_name} not found")
        
        dataset = self.datasets[dataset_name]
        
        # Create sample data
        if dataset.sample:
            df = pd.DataFrame(dataset.sample)
        else:
            # Generate sample classification data
            np.random.seed(42)
            X = np.random.randn(100, 5)
            y = np.random.randint(0, 2, 100)
            df = pd.DataFrame(X, columns=[f"feature_{i}" for i in range(5)])
            df["target"] = y
        
        # Extract features and target
        target_col = model_spec.get("target", "target")
        if target_col not in df.columns:
            raise ValueError(f"Target column {target_col} not found in dataset")
        
        X = df.drop(columns=[target_col])
        y = df[target_col]
        
        # Convert to numpy arrays
        X = X.select_dtypes(include=[np.number]).values
        y = y.values
        
        if len(X) == 0:
            raise ValueError("No numerical features found for training")
        
        # Determine task type
        task_type = model_spec.get("task_type", "classification")
        try:
            task = MLTask(task_type)
        except ValueError:
            task = MLTask.CLASSIFICATION
        
        # Train model based on task type
        training_results = {
            "dataset": dataset_name,
            "task_type": task.value,
            "model_type": model_spec.get("model_type", "default"),
            "features": list(X.columns) if hasattr(X, 'columns') else [f"feature_{i}" for i in range(X.shape[1])],
            "target": target_col,
            "training_metrics": {},
            "model_parameters": {}
        }
        
        if task == MLTask.CLASSIFICATION:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Train model
            model = RandomForestClassifier(
                n_estimators=model_spec.get("n_estimators", 100),
                max_depth=model_spec.get("max_depth", None),
                random_state=42
            )
            model.fit(X_train, y_train)
            
            # Predictions
            y_pred = model.predict(X_test)
            
            # Metrics
            training_results["training_metrics"] = {
                "accuracy": float(accuracy_score(y_test, y_pred)),
                "precision": float(precision_score(y_test, y_pred, average='weighted')),
                "recall": float(recall_score(y_test, y_pred, average='weighted')),
                "f1_score": float(f1_score(y_test, y_pred, average='weighted')),
                "train_samples": len(X_train),
                "test_samples": len(X_test)
            }
            
            training_results["model_parameters"] = {
                "n_estimators": model.n_estimators,
                "max_depth": model.max_depth,
                "n_features": model.n_features_in_
            }
            
        elif task == MLTask.REGRESSION:
            from sklearn.ensemble import RandomForestRegressor
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import mean_squared_error, r2_score
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Train model
            model = RandomForestRegressor(
                n_estimators=model_spec.get("n_estimators", 100),
                max_depth=model_spec.get("max_depth", None),
                random_state=42
            )
            model.fit(X_train, y_train)
            
            # Predictions
            y_pred = model.predict(X_test)
            
            # Metrics
            training_results["training_metrics"] = {
                "mse": float(mean_squared_error(y_test, y_pred)),
                "rmse": float(np.sqrt(mean_squared_error(y_test, y_pred))),
                "r2_score": float(r2_score(y_test, y_pred)),
                "train_samples": len(X_train),
                "test_samples": len(X_test)
            }
            
            training_results["model_parameters"] = {
                "n_estimators": model.n_estimators,
                "max_depth": model.max_depth,
                "n_features": model.n_features_in_
            }
        
        elif task == MLTask.CLUSTERING:
            from sklearn.cluster import KMeans
            from sklearn.metrics import silhouette_score
            
            # Train model
            n_clusters = model_spec.get("n_clusters", 3)
            model = KMeans(n_clusters=n_clusters, random_state=42)
            model.fit(X)
            
            # Predictions
            labels = model.predict(X)
            
            # Metrics
            if len(np.unique(labels)) > 1:
                silhouette = silhouette_score(X, labels)
            else:
                silhouette = 0.0
            
            training_results["training_metrics"] = {
                "silhouette_score": float(silhouette),
                "n_clusters": n_clusters,
                "samples": len(X)
            }
            
            training_results["model_parameters"] = {
                "n_clusters": n_clusters,
                "n_features": X.shape[1]
            }
        
        # Store model
        model_id = f"model_{dataset_name}_{task.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.ml_models[model_id] = {
            "model_type": task.value,
            "dataset": dataset_name,
            "parameters": training_results["model_parameters"],
            "metrics": training_results["training_metrics"],
            "timestamp": datetime.now().isoformat()
        }
        
        training_results["model_id"] = model_id
        training_results["status"] = "completed"
        
        print(f"✅ {self.name}: ML model training completed for dataset {dataset_name}")
        return training_results
    
    async def create_data_pipeline(self, pipeline_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a data processing pipeline
        
        Args:
            pipeline_spec: Pipeline specification
            
        Returns:
            Dictionary with pipeline information
        """
        print(f"🚀 {self.name}: Creating data pipeline {pipeline_spec.get('name', 'Unnamed')}")
        
        pipeline_name = pipeline_spec.get("name", "unnamed_pipeline")
        description = pipeline_spec.get("description", "")
        steps = pipeline_spec.get("steps", [])
        
        pipeline = DataPipeline(
            name=pipeline_name,
            description=description,
            steps=steps,
            inputs=pipeline_spec.get("inputs", []),
            outputs=pipeline_spec.get("outputs", [])
        )
        
        # Build dependencies
        for i, step in enumerate(steps):
            step_name = step.get("name", f"step_{i}")
            dependencies = step.get("dependencies", [])
            pipeline.dependencies[step_name] = dependencies
        
        self.pipelines[pipeline_name] = pipeline
        
        result = {
            "pipeline_name": pipeline_name,
            "description": description,
            "steps": [step.get("name", f"step_{i}") for i, step in enumerate(steps)],
            "inputs": pipeline.inputs,
            "outputs": pipeline.outputs,
            "dependencies": pipeline.dependencies,
            "status": "created"
        }
        
        print(f"✅ {self.name}: Data pipeline {pipeline_name} created with {len(steps)} steps")
        return result
    
    async def generate_visualization(self, dataset_name: str, viz_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate data visualizations
        
        Args:
            dataset_name: Name of the dataset
            viz_spec: Visualization specification
            
        Returns:
            Dictionary with visualization data
        """
        print(f"📊 {self.name}: Generating visualization for dataset {dataset_name}")
        
        if dataset_name not in self.datasets:
            raise ValueError(f"Dataset {dataset_name} not found")
        
        dataset = self.datasets[dataset_name]
        
        # Create sample data
        if dataset.sample:
            df = pd.DataFrame(dataset.sample)
        else:
            df = pd.DataFrame({
                "x": [1, 2, 3, 4, 5],
                "y": [10, 20, 15, 25, 30],
                "category": ["A", "B", "A", "B", "A"]
            })
        
        viz_type = viz_spec.get("type", "scatter")
        columns = viz_spec.get("columns", [])
        
        visualization = {
            "dataset": dataset_name,
            "type": viz_type,
            "data": {},
            "layout": {},
            "code": ""
        }
        
        if viz_type == "scatter":
            x_col = columns[0] if len(columns) > 0 else "x"
            y_col = columns[1] if len(columns) > 1 else "y"
            
            if x_col in df.columns and y_col in df.columns:
                visualization["data"] = {
                    "x": df[x_col].tolist(),
                    "y": df[y_col].tolist(),
                    "mode": "markers",
                    "type": "scatter"
                }
                visualization["layout"] = {
                    "xaxis": {"title": x_col},
                    "yaxis": {"title": y_col},
                    "title": f"{y_col} vs {x_col}"
                }
                
                # Generate Python code for the visualization
                visualization["code"] = f'''import matplotlib.pyplot as plt
import pandas as pd

# Sample data
data = {df.to_dict("records")}
df = pd.DataFrame(data)

# Create scatter plot
plt.figure(figsize=(10, 6))
plt.scatter(df["{x_col}"], df["{y_col}"])
plt.xlabel("{x_col}")
plt.ylabel("{y_col}")
plt.title("{y_col} vs {x_col}")
plt.grid(True)
plt.show()
'''
        
        elif viz_type == "histogram":
            col = columns[0] if len(columns) > 0 else "x"
            
            if col in df.columns:
                hist, bin_edges = np.histogram(df[col].dropna(), bins=10)
                
                visualization["data"] = [{
                    "x": bin_edges.tolist(),
                    "y": hist.tolist(),
                    "type": "bar",
                    "name": col
                }]
                visualization["layout"] = {
                    "xaxis": {"title": col},
                    "yaxis": {"title": "Frequency"},
                    "title": f"Distribution of {col}"
                }
                
                # Generate Python code
                visualization["code"] = f'''import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Sample data
data = {df.to_dict("records")}
df = pd.DataFrame(data)

# Create histogram
plt.figure(figsize=(10, 6))
plt.hist(df["{col}"], bins=10, alpha=0.7, color='blue', edgecolor='black')
plt.xlabel("{col}")
plt.ylabel("Frequency")
plt.title("Distribution of {col}")
plt.grid(True)
plt.show()
'''
        
        elif viz_type == "bar_chart":
            x_col = columns[0] if len(columns) > 0 else "category"
            y_col = columns[1] if len(columns) > 1 else "y"
            
            if x_col in df.columns and y_col in df.columns:
                grouped = df.groupby(x_col)[y_col].mean().reset_index()
                
                visualization["data"] = [{
                    "x": grouped[x_col].tolist(),
                    "y": grouped[y_col].tolist(),
                    "type": "bar",
                    "name": y_col
                }]
                visualization["layout"] = {
                    "xaxis": {"title": x_col},
                    "yaxis": {"title": f"Average {y_col}"},
                    "title": f"Average {y_col} by {x_col}"
                }
                
                # Generate Python code
                visualization["code"] = f'''import matplotlib.pyplot as plt
import pandas as pd

# Sample data
data = {df.to_dict("records")}
df = pd.DataFrame(data)

# Create bar chart
grouped = df.groupby("{x_col}")["{y_col}"].mean().reset_index()

plt.figure(figsize=(10, 6))
plt.bar(grouped["{x_col}"], grouped["{y_col}"])
plt.xlabel("{x_col}")
plt.ylabel("Average {y_col}")
plt.title("Average {y_col} by {x_col}")
plt.grid(True)
plt.show()
'''
        
        print(f"✅ {self.name}: Visualization generated for dataset {dataset_name}")
        return visualization
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "current_project": self.current_project,
            "current_technology": self.current_technology.value if self.current_technology else None,
            "current_analysis_type": self.current_analysis_type.value if self.current_analysis_type else None,
            "datasets_count": len(self.datasets),
            "pipelines_count": len(self.pipelines),
            "analysis_results_count": len(self.analysis_results),
            "ml_models_count": len(self.ml_models),
            "performance_metrics": self.performance_metrics,
            "skills": list(self.skills.keys())
        }
    
    def reset(self) -> None:
        """Reset agent state"""
        self.current_project = None
        self.current_technology = None
        self.current_analysis_type = None
        self.datasets.clear()
        self.pipelines.clear()
        self.analysis_results.clear()
        self.ml_models.clear()
        self.performance_metrics.clear()
        print(f"🔄 {self.name}: Agent state reset")
