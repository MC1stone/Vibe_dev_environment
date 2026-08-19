"""
Faiss Agent - Specialist for Facebook AI Similarity Search (Faiss)

Responsibilities:
- Vector database design and implementation
- Index creation and optimization
- Similarity search
- Embedding management
- Performance tuning
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import asyncio
import numpy as np


class FaissIndexType(Enum):
    """Faiss index types"""
    FLAT_L2 = "Flat_L2"
    FLAT_IP = "Flat_IP"
    IVF_FLAT = "IVF_Flat"
    IVF_PQ = "IVF_PQ"
    HNSW_FLAT = "HNSW_Flat"
    HNSW_PQ = "HNSW_PQ"
    PQ = "PQ"
    LSH = "LSH"


class FaissMetricType(Enum):
    """Faiss metric types"""
    L2 = "L2"  # Euclidean distance
    INNER_PRODUCT = "INNER_PRODUCT"  # Inner product (cosine similarity)


class FaissQuantizer(Enum):
    """Faiss quantization types"""
    NONE = "none"
    FP16 = "fp16"
    INT8 = "int8"
    INT8_UNIFORM = "int8_uniform"


@dataclass
class FaissIndex:
    """Represents a Faiss index"""
    index_id: str
    name: str
    dimension: int
    index_type: FaissIndexType
    metric_type: FaissMetricType = FaissMetricType.L2
    nlist: int = 100  # Number of clusters for IVF
    nprobe: int = 10  # Number of clusters to search for IVF
    m: int = 8  # Number of sub-vectors for PQ
    nbits: int = 8  # Number of bits per sub-vector for PQ
    quantizer: FaissQuantizer = FaissQuantizer.NONE
    trained: bool = False
    size: int = 0


@dataclass
class FaissEmbedding:
    """Represents an embedding vector"""
    embedding_id: str
    vector: np.ndarray
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[str] = None


@dataclass
class FaissSearchResult:
    """Represents a similarity search result"""
    query_id: str
    results: List[Dict[str, Any]] = field(default_factory=list)
    distances: List[float] = field(default_factory=list)
    indices: List[int] = field(default_factory=list)
    execution_time: float = 0.0


@dataclass
class FaissAgent:
    """
    Faiss Specialist Agent
    
    This agent specializes in Faiss vector database implementation and similarity search.
    It can create, optimize, and query vector indexes for various applications.
    """
    
    agent_id: str = "faiss_agent_001"
    name: str = "Faiss Specialist"
    description: str = "Expert in Faiss vector database and similarity search"
    version: str = "1.0.0"
    
    # Agent capabilities
    supported_index_types: List[FaissIndexType] = field(default_factory=lambda: [
        FaissIndexType.FLAT_L2,
        FaissIndexType.FLAT_IP,
        FaissIndexType.IVF_FLAT,
        FaissIndexType.IVF_PQ,
        FaissIndexType.HNSW_FLAT,
        FaissIndexType.HNSW_PQ,
    ])
    
    supported_metric_types: List[FaissMetricType] = field(default_factory=lambda: [
        FaissMetricType.L2,
        FaissMetricType.INNER_PRODUCT,
    ])
    
    # Agent skills
    skills: Dict[str, str] = field(default_factory=dict)
    
    # Current project state
    current_project: Optional[str] = None
    current_index: Optional[str] = None
    
    # Indexes being managed
    indexes: Dict[str, FaissIndex] = field(default_factory=dict)
    
    # Embeddings stored
    embeddings: Dict[str, FaissEmbedding] = field(default_factory=dict)
    
    # Search results
    search_results: Dict[str, FaissSearchResult] = field(default_factory=dict)
    
    # Performance metrics
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize the agent with default skills"""
        self._initialize_skills()
    
    def _initialize_skills(self) -> None:
        """Initialize the agent's skill set"""
        self.skills = {
            "index_design": "Design optimal Faiss indexes for specific use cases and data distributions",
            "index_creation": "Create and configure Faiss indexes with appropriate parameters",
            "index_optimization": "Optimize index parameters for performance and accuracy",
            "similarity_search": "Perform efficient similarity search with various metrics",
            "embedding_management": "Manage embeddings and their metadata",
            "quantization": "Apply quantization techniques to reduce memory usage",
            "performance_tuning": "Tune Faiss parameters for optimal performance",
            "batch_processing": "Process embeddings in batches for efficiency",
            "gpu_acceleration": "Utilize GPU acceleration for faster operations",
            "index_persistence": "Save and load indexes for persistent storage",
            "testing": "Test index performance and validate results",
            "documentation": "Document index configurations and usage"
        }
    
    async def create_index(self, index_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new Faiss index
        
        Args:
            index_spec: Index specification
            
        Returns:
            Dictionary with index configuration
        """
        print(f"🚀 {self.name}: Creating Faiss index {index_spec.get('name', 'Unnamed')}")
        
        index_id = index_spec.get("index_id", f"index_{len(self.indexes) + 1}")
        index_name = index_spec.get("name", "Unnamed Index")
        dimension = index_spec.get("dimension", 128)
        index_type_str = index_spec.get("index_type", "Flat_L2")
        metric_type_str = index_spec.get("metric_type", "L2")
        
        # Validate index type
        try:
            index_type = FaissIndexType(index_type_str)
        except ValueError:
            index_type = FaissIndexType.FLAT_L2
            print(f"⚠️  Index type {index_type_str} not supported, defaulting to Flat_L2")
        
        # Validate metric type
        try:
            metric_type = FaissMetricType(metric_type_str)
        except ValueError:
            metric_type = FaissMetricType.L2
            print(f"⚠️  Metric type {metric_type_str} not supported, defaulting to L2")
        
        # Get additional parameters
        nlist = index_spec.get("nlist", 100)
        nprobe = index_spec.get("nprobe", 10)
        m = index_spec.get("m", 8)
        nbits = index_spec.get("nbits", 8)
        quantizer_str = index_spec.get("quantizer", "none")
        
        try:
            quantizer = FaissQuantizer(quantizer_str)
        except ValueError:
            quantizer = FaissQuantizer.NONE
            print(f"⚠️  Quantizer {quantizer_str} not supported, defaulting to none")
        
        # Create index
        index = FaissIndex(
            index_id=index_id,
            name=index_name,
            dimension=dimension,
            index_type=index_type,
            metric_type=metric_type,
            nlist=nlist,
            nprobe=nprobe,
            m=m,
            nbits=nbits,
            quantizer=quantizer
        )
        
        self.indexes[index_id] = index
        self.current_index = index_id
        
        # Generate index creation code
        index_code = self._generate_index_code(index)
        
        result = {
            "index_id": index_id,
            "name": index_name,
            "dimension": dimension,
            "index_type": index_type.value,
            "metric_type": metric_type.value,
            "nlist": nlist,
            "nprobe": nprobe,
            "m": m,
            "nbits": nbits,
            "quantizer": quantizer.value,
            "code": index_code,
            "status": "created"
        }
        
        print(f"✅ {self.name}: Faiss index {index_name} created with ID {index_id}")
        return result
    
    def _generate_index_code(self, index: FaissIndex) -> str:
        """Generate Faiss index creation code"""
        code = f'''
import faiss
import numpy as np

# Index parameters
DIMENSION = {index.dimension}
INDEX_TYPE = "{index.index_type.value}"
METRIC_TYPE = faiss.METRIC_{index.metric_type.value}

# Create index based on type
if INDEX_TYPE == "Flat_L2":
    index = faiss.IndexFlatL2(DIMENSION)
elif INDEX_TYPE == "Flat_IP":
    index = faiss.IndexFlatIP(DIMENSION)
elif INDEX_TYPE == "IVF_Flat":
    nlist = {index.nlist}
    quantizer = faiss.IndexFlatL2(DIMENSION)
    index = faiss.IndexIVFFlat(quantizer, DIMENSION, nlist, METRIC_TYPE)
elif INDEX_TYPE == "IVF_PQ":
    nlist = {index.nlist}
    m = {index.m}
    nbits = {index.nbits}
    quantizer = faiss.IndexFlatL2(DIMENSION)
    index = faiss.IndexIVFPQ(quantizer, DIMENSION, nlist, m, nbits)
elif INDEX_TYPE == "HNSW_Flat":
    m = {index.m}
    index = faiss.IndexHNSWFlat(DIMENSION, m, METRIC_TYPE)
elif INDEX_TYPE == "HNSW_PQ":
    m = {index.m}
    nbits = {index.nbits}
    index = faiss.IndexHNSWFlat(DIMENSION, m, METRIC_TYPE)
else:
    # Default to Flat L2
    index = faiss.IndexFlatL2(DIMENSION)

# Train index if needed
if hasattr(index, "train"):
    # Generate random training data
    nb = 10000  # Number of training vectors
    xb = np.random.random((nb, DIMENSION)).astype('float32')
    index.train(xb)
    print(f"Index trained with {{nb}} vectors")

# Index information
print(f"Index created: {{index.is_trained}}")
print(f"Index type: {{INDEX_TYPE}}")
print(f"Dimension: {{DIMENSION}}")
print(f"Metric: {{METRIC_TYPE}}")

# Save index (optional)
# faiss.write_index(index, "{index.index_id}.faiss")
'''
        return code
    
    async def add_embeddings(self, index_id: str, embeddings_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add embeddings to an index
        
        Args:
            index_id: ID of the index
            embeddings_spec: Embeddings specification
            
        Returns:
            Dictionary with embedding addition results
        """
        print(f"📊 {self.name}: Adding embeddings to index {index_id}")
        
        if index_id not in self.indexes:
            raise ValueError(f"Index {index_id} not found")
        
        index = self.indexes[index_id]
        
        # Get embeddings data
        vectors = embeddings_spec.get("vectors", [])
        metadata_list = embeddings_spec.get("metadata", [])
        batch_size = embeddings_spec.get("batch_size", 1000)
        
        # Generate sample embeddings if none provided
        if not vectors:
            num_embeddings = embeddings_spec.get("num_embeddings", 100)
            vectors = [np.random.random(index.dimension).tolist() for _ in range(num_embeddings)]
            metadata_list = [{"id": f"emb_{i}", "source": f"source_{i % 10}"} for i in range(num_embeddings)]
        
        # Convert to numpy array
        vectors_array = np.array(vectors, dtype=np.float32)
        
        # Validate dimension
        if vectors_array.shape[1] != index.dimension:
            raise ValueError(f"Embedding dimension {vectors_array.shape[1]} doesn't match index dimension {index.dimension}")
        
        # Add embeddings in batches
        num_batches = int(np.ceil(len(vectors_array) / batch_size))
        added_count = 0
        
        for i in range(num_batches):
            start_idx = i * batch_size
            end_idx = min((i + 1) * batch_size, len(vectors_array))
            batch = vectors_array[start_idx:end_idx]
            
            # Store embeddings
            for j, vector in enumerate(batch):
                embedding_id = f"{index_id}_emb_{added_count + j}"
                metadata = metadata_list[added_count + j] if (added_count + j) < len(metadata_list) else {}
                
                embedding = FaissEmbedding(
                    embedding_id=embedding_id,
                    vector=vector,
                    metadata=metadata
                )
                self.embeddings[embedding_id] = embedding
            
            added_count += len(batch)
        
        # Update index size
        index.size += len(vectors_array)
        index.trained = True
        
        result = {
            "index_id": index_id,
            "embeddings_added": len(vectors_array),
            "total_embeddings": index.size,
            "batch_size": batch_size,
            "num_batches": num_batches,
            "dimension": index.dimension,
            "status": "completed"
        }
        
        print(f"✅ {self.name}: Added {len(vectors_array)} embeddings to index {index_id}")
        return result
    
    async def search_similar(self, index_id: str, search_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform similarity search on an index
        
        Args:
            index_id: ID of the index to search
            search_spec: Search specification
            
        Returns:
            Dictionary with search results
        """
        print(f"🔍 {self.name}: Performing similarity search on index {index_id}")
        
        if index_id not in self.indexes:
            raise ValueError(f"Index {index_id} not found")
        
        index = self.indexes[index_id]
        
        # Get query vectors
        query_vectors = search_spec.get("query_vectors", [])
        k = search_spec.get("k", 5)  # Number of nearest neighbors
        
        # Generate sample query if none provided
        if not query_vectors:
            num_queries = search_spec.get("num_queries", 1)
            query_vectors = [np.random.random(index.dimension).tolist() for _ in range(num_queries)]
        
        query_array = np.array(query_vectors, dtype=np.float32)
        
        # Validate dimension
        if query_array.shape[1] != index.dimension:
            raise ValueError(f"Query dimension {query_array.shape[1]} doesn't match index dimension {index.dimension}")
        
        # Perform search (simulated)
        search_results = []
        distances = []
        indices = []
        
        for i, query_vector in enumerate(query_array):
            # Simulate search results
            # In a real implementation, this would use the actual Faiss index
            result_indices = np.random.randint(0, index.size, size=k).tolist()
            result_distances = np.random.random(k).tolist()
            
            indices.append(result_indices)
            distances.append(result_distances)
            
            # Get result metadata
            result_items = []
            for idx, distance in zip(result_indices, result_distances):
                embedding_id = f"{index_id}_emb_{idx}"
                if embedding_id in self.embeddings:
                    embedding = self.embeddings[embedding_id]
                    result_items.append({
                        "embedding_id": embedding_id,
                        "distance": distance,
                        "metadata": embedding.metadata,
                        "vector": embedding.vector.tolist()
                    })
            
            search_results.append(result_items)
        
        # Create search result
        query_id = f"search_{index_id}_{len(self.search_results) + 1}"
        search_result = FaissSearchResult(
            query_id=query_id,
            results=search_results,
            distances=distances,
            indices=indices,
            execution_time=0.01  # Simulated execution time
        )
        
        self.search_results[query_id] = search_result
        
        result = {
            "query_id": query_id,
            "index_id": index_id,
            "num_queries": len(query_vectors),
            "k": k,
            "results": search_results,
            "distances": distances,
            "indices": indices,
            "execution_time": search_result.execution_time,
            "status": "completed"
        }
        
        print(f"✅ {self.name}: Similarity search completed for index {index_id}")
        return result
    
    async def optimize_index(self, index_id: str, optimization_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize an existing index
        
        Args:
            index_id: ID of the index to optimize
            optimization_spec: Optimization specification
            
        Returns:
            Dictionary with optimization results
        """
        print(f"⚡ {self.name}: Optimizing index {index_id}")
        
        if index_id not in self.indexes:
            raise ValueError(f"Index {index_id} not found")
        
        index = self.indexes[index_id]
        
        # Get optimization parameters
        target_speed = optimization_spec.get("target_speed", "balanced")  # "fast", "balanced", "accurate"
        memory_constraint = optimization_spec.get("memory_constraint", None)  # in MB
        accuracy_constraint = optimization_spec.get("accuracy_constraint", None)  # 0-1
        
        # Generate optimization recommendations
        recommendations = []
        
        # Check if we can use a more efficient index type
        if index.index_type == FaissIndexType.FLAT_L2 and index.size > 100000:
            recommendations.append({
                "action": "change_index_type",
                "current": index.index_type.value,
                "recommended": "IVF_Flat",
                "reason": "IVF indexes are more efficient for large datasets",
                "expected_improvement": "10x faster search"
            })
        
        # Check nprobe for IVF indexes
        if index.index_type in [FaissIndexType.IVF_FLAT, FaissIndexType.IVF_PQ]:
            if index.nprobe > index.nlist:
                recommendations.append({
                    "action": "adjust_nprobe",
                    "current": index.nprobe,
                    "recommended": min(index.nprobe, index.nlist),
                    "reason": "nprobe should not exceed nlist",
                    "expected_improvement": "better accuracy"
                })
            elif index.nprobe < 10:
                recommendations.append({
                    "action": "increase_nprobe",
                    "current": index.nprobe,
                    "recommended": 10,
                    "reason": "Higher nprobe improves recall",
                    "expected_improvement": "better accuracy"
                })
        
        # Check quantization
        if index.quantizer == FaissQuantizer.NONE and memory_constraint:
            if index.size * index.dimension * 4 / (1024 * 1024) > memory_constraint:  # 4 bytes per float32
                recommendations.append({
                    "action": "apply_quantization",
                    "current": "none",
                    "recommended": "int8",
                    "reason": f"Memory usage exceeds {memory_constraint}MB",
                    "expected_improvement": "4x memory reduction"
                })
        
        # Apply optimizations
        optimized = False
        if recommendations:
            # Update index parameters based on recommendations
            for rec in recommendations:
                if rec["action"] == "change_index_type":
                    try:
                        new_type = FaissIndexType(rec["recommended"])
                        index.index_type = new_type
                        optimized = True
                    except ValueError:
                        pass
                elif rec["action"] == "adjust_nprobe":
                    index.nprobe = rec["recommended"]
                    optimized = True
                elif rec["action"] == "increase_nprobe":
                    index.nprobe = rec["recommended"]
                    optimized = True
                elif rec["action"] == "apply_quantization":
                    try:
                        new_quantizer = FaissQuantizer(rec["recommended"])
                        index.quantizer = new_quantizer
                        optimized = True
                    except ValueError:
                        pass
        
        result = {
            "index_id": index_id,
            "optimized": optimized,
            "recommendations": recommendations,
            "current_config": {
                "index_type": index.index_type.value,
                "nlist": index.nlist,
                "nprobe": index.nprobe,
                "quantizer": index.quantizer.value,
                "size": index.size
            },
            "status": "completed"
        }
        
        print(f"✅ {self.name}: Index {index_id} optimization completed with {len(recommendations)} recommendations")
        return result
    
    async def evaluate_performance(self, index_id: str, evaluation_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate index performance
        
        Args:
            index_id: ID of the index to evaluate
            evaluation_spec: Evaluation specification
            
        Returns:
            Dictionary with performance evaluation
        """
        print(f"📈 {self.name}: Evaluating performance of index {index_id}")
        
        if index_id not in self.indexes:
            raise ValueError(f"Index {index_id} not found")
        
        index = self.indexes[index_id]
        
        # Generate performance metrics
        metrics = {
            "index_id": index_id,
            "index_type": index.index_type.value,
            "size": index.size,
            "dimension": index.dimension,
            "memory_usage": index.size * index.dimension * 4 / (1024 * 1024),  # MB
            "search_speed": 0.0,  # queries per second
            "accuracy": 0.0,  # recall@k
            "build_time": 0.0,  # seconds
            "recommendations": []
        }
        
        # Estimate memory usage
        if index.index_type == FaissIndexType.FLAT_L2:
            metrics["memory_usage"] = index.size * index.dimension * 4 / (1024 * 1024)
        elif index.index_type in [FaissIndexType.IVF_FLAT, FaissIndexType.IVF_PQ]:
            metrics["memory_usage"] = (index.size * index.dimension * 4 + index.nlist * index.dimension * 4) / (1024 * 1024)
        elif index.index_type in [FaissIndexType.HNSW_FLAT, FaissIndexType.HNSW_PQ]:
            metrics["memory_usage"] = index.size * index.dimension * 4 * 1.5 / (1024 * 1024)  # HNSW uses more memory
        
        # Estimate search speed
        if index.index_type == FaissIndexType.FLAT_L2:
            metrics["search_speed"] = 1000.0  # queries per second
        elif index.index_type in [FaissIndexType.IVF_FLAT, FaissIndexType.IVF_PQ]:
            metrics["search_speed"] = 10000.0 * (index.nlist / index.nprobe)
        elif index.index_type in [FaissIndexType.HNSW_FLAT, FaissIndexType.HNSW_PQ]:
            metrics["search_speed"] = 5000.0
        
        # Estimate accuracy
        if index.index_type == FaissIndexType.FLAT_L2:
            metrics["accuracy"] = 1.0  # Exact search
        elif index.index_type in [FaissIndexType.IVF_FLAT, FaissIndexType.IVF_PQ]:
            metrics["accuracy"] = 0.95 * (index.nprobe / index.nlist)
        elif index.index_type in [FaissIndexType.HNSW_FLAT, FaissIndexType.HNSW_PQ]:
            metrics["accuracy"] = 0.98
        
        # Generate recommendations
        if metrics["memory_usage"] > 1000:  # > 1GB
            metrics["recommendations"].append({
                "type": "memory",
                "issue": f"High memory usage: {metrics['memory_usage']:.2f} MB",
                "suggestion": "Consider using IVF or PQ indexes to reduce memory usage"
            })
        
        if metrics["search_speed"] < 1000:
            metrics["recommendations"].append({
                "type": "performance",
                "issue": f"Low search speed: {metrics['search_speed']:.2f} queries/sec",
                "suggestion": "Consider using IVF or HNSW indexes for faster search"
            })
        
        if metrics["accuracy"] < 0.9:
            metrics["recommendations"].append({
                "type": "accuracy",
                "issue": f"Low accuracy: {metrics['accuracy']:.2f}",
                "suggestion": "Consider increasing nprobe or using a more accurate index type"
            })
        
        self.performance_metrics[index_id] = metrics["search_speed"]
        
        print(f"✅ {self.name}: Performance evaluation completed for index {index_id}")
        return metrics
    
    async def generate_index_documentation(self, index_id: str) -> Dict[str, Any]:
        """
        Generate documentation for an index
        
        Args:
            index_id: ID of the index
            
        Returns:
            Dictionary with documentation
        """
        print(f"📚 {self.name}: Generating documentation for index {index_id}")
        
        if index_id not in self.indexes:
            raise ValueError(f"Index {index_id} not found")
        
        index = self.indexes[index_id]
        
        documentation = {
            "index": {
                "id": index.index_id,
                "name": index.name,
                "dimension": index.dimension,
                "index_type": index.index_type.value,
                "metric_type": index.metric_type.value,
                "nlist": index.nlist,
                "nprobe": index.nprobe,
                "m": index.m,
                "nbits": index.nbits,
                "quantizer": index.quantizer.value,
                "trained": index.trained,
                "size": index.size
            },
            "configuration": {},
            "usage": {},
            "best_practices": {}
        }
        
        # Generate configuration code
        config_code = self._generate_index_code(index)
        documentation["configuration"] = {
            "python_code": config_code,
            "parameters": {
                "dimension": index.dimension,
                "index_type": index.index_type.value,
                "metric_type": index.metric_type.value,
                "nlist": index.nlist,
                "nprobe": index.nprobe,
                "m": index.m,
                "nbits": index.nbits
            }
        }
        
        # Generate usage examples
        documentation["usage"] = {
            "adding_embeddings": f'''
# Adding embeddings to {index.name}

```python
import faiss
import numpy as np

# Load index
index = faiss.read_index("{index.index_id}.faiss")

# Generate embeddings
embeddings = np.random.random((1000, {index.dimension})).astype('float32')

# Add to index
index.add(embeddings)

# Save updated index
faiss.write_index(index, "{index.index_id}.faiss")
```
''',
            "searching": f'''
# Searching in {index.name}

```python
import faiss
import numpy as np

# Load index
index = faiss.read_index("{index.index_id}.faiss")

# Query vector
query = np.random.random({index.dimension}).astype('float32').reshape(1, -1)

# Search
k = 5  # Number of nearest neighbors
D, I = index.search(query, k)

# Results
print(f"Nearest neighbors: {{I}}")
print(f"Distances: {{D}}")
```
''',
            "saving_loading": f'''
# Saving and loading {index.name}

```python
import faiss

# Save index
faiss.write_index(index, "{index.index_id}.faiss")

# Load index
index = faiss.read_index("{index.index_id}.faiss")
```
'''
        }
        
        # Generate best practices
        documentation["best_practices"] = {
            "index_selection": f'''
# Index Selection Guide for {index.index_type.value}

## When to use {index.index_type.value}:

{self._get_index_usage_guide(index.index_type)}

## Performance characteristics:
- **Memory usage**: {self._get_memory_characteristics(index.index_type)}
- **Search speed**: {self._get_speed_characteristics(index.index_type)}
- **Accuracy**: {self._get_accuracy_characteristics(index.index_type)}
- **Training required**: {self._get_training_requirement(index.index_type)}
''',
            "parameter_tuning": f'''
# Parameter Tuning for {index.index_type.value}

## Key parameters:

{self._get_parameter_guide(index.index_type)}
'''
        }
        
        print(f"✅ {self.name}: Documentation generated for index {index_id}")
        return documentation
    
    def _get_index_usage_guide(self, index_type: FaissIndexType) -> str:
        """Get usage guide for index type"""
        guides = {
            FaissIndexType.FLAT_L2: "Use for small datasets (< 1M vectors) or when exact search is required. Fast for small datasets but doesn't scale well.",
            FaissIndexType.FLAT_IP: "Use for cosine similarity search on small datasets. Similar to Flat_L2 but uses inner product.",
            FaissIndexType.IVF_FLAT: "Use for medium to large datasets (1M-100M vectors). Provides good balance between speed and accuracy.",
            FaissIndexType.IVF_PQ: "Use for very large datasets (> 10M vectors) when memory is constrained. Uses product quantization for compression.",
            FaissIndexType.HNSW_FLAT: "Use for dynamic datasets with frequent updates. Good for approximate nearest neighbor search.",
            FaissIndexType.HNSW_PQ: "Use for very large dynamic datasets. Combines HNSW with product quantization."
        }
        return guides.get(index_type, "General purpose index for various use cases.")
    
    def _get_memory_characteristics(self, index_type: FaissIndexType) -> str:
        """Get memory characteristics for index type"""
        characteristics = {
            FaissIndexType.FLAT_L2: "High - stores all vectors in memory",
            FaissIndexType.FLAT_IP: "High - stores all vectors in memory",
            FaissIndexType.IVF_FLAT: "Medium - stores cluster centers and vectors",
            FaissIndexType.IVF_PQ: "Low - uses compression with product quantization",
            FaissIndexType.HNSW_FLAT: "High - stores graph structure and vectors",
            FaissIndexType.HNSW_PQ: "Medium - uses compression with product quantization"
        }
        return characteristics.get(index_type, "Medium")
    
    def _get_speed_characteristics(self, index_type: FaissIndexType) -> str:
        """Get speed characteristics for index type"""
        characteristics = {
            FaissIndexType.FLAT_L2: "Fast for small datasets, slow for large datasets",
            FaissIndexType.FLAT_IP: "Fast for small datasets, slow for large datasets",
            FaissIndexType.IVF_FLAT: "Very fast - searches only a subset of clusters",
            FaissIndexType.IVF_PQ: "Very fast - searches compressed vectors",
            FaissIndexType.HNSW_FLAT: "Fast - uses graph traversal for approximate search",
            FaissIndexType.HNSW_PQ: "Fast - uses graph traversal with compressed vectors"
        }
        return characteristics.get(index_type, "Moderate")
    
    def _get_accuracy_characteristics(self, index_type: FaissIndexType) -> str:
        """Get accuracy characteristics for index type"""
        characteristics = {
            FaissIndexType.FLAT_L2: "Exact - returns true nearest neighbors",
            FaissIndexType.FLAT_IP: "Exact - returns true nearest neighbors",
            FaissIndexType.IVF_FLAT: "Approximate - depends on nprobe parameter",
            FaissIndexType.IVF_PQ: "Approximate - depends on nprobe and quantization",
            FaissIndexType.HNSW_FLAT: "Approximate - depends on graph construction",
            FaissIndexType.HNSW_PQ: "Approximate - depends on graph construction and quantization"
        }
        return characteristics.get(index_type, "Moderate")
    
    def _get_training_requirement(self, index_type: FaissIndexType) -> str:
        """Get training requirement for index type"""
        requirements = {
            FaissIndexType.FLAT_L2: "No - ready to use immediately",
            FaissIndexType.FLAT_IP: "No - ready to use immediately",
            FaissIndexType.IVF_FLAT: "Yes - requires training data for clustering",
            FaissIndexType.IVF_PQ: "Yes - requires training data for clustering and quantization",
            FaissIndexType.HNSW_FLAT: "No - builds incrementally",
            FaissIndexType.HNSW_PQ: "No - builds incrementally"
        }
        return requirements.get(index_type, "Depends on configuration")
    
    def _get_parameter_guide(self, index_type: FaissIndexType) -> str:
        """Get parameter tuning guide for index type"""
        guides = {
            FaissIndexType.FLAT_L2: "No tunable parameters - simple brute-force search.",
            FaissIndexType.FLAT_IP: "No tunable parameters - simple brute-force search.",
            FaissIndexType.IVF_FLAT: f"""
- **nlist**: Number of cluster centers (default: {self.indexes.get(self.current_index, type('obj', (lambda: None, {'index_type': index_type}))()).nlist})
  - Higher values: better accuracy, more memory, slower search
  - Lower values: faster search, less memory, lower accuracy
  - Recommended: 100-1000 depending on dataset size

- **nprobe**: Number of clusters to search (default: {self.indexes.get(self.current_index, type('obj', (lambda: None, {'index_type': index_type}))()).nprobe})
  - Higher values: better accuracy, slower search
  - Lower values: faster search, lower accuracy
  - Recommended: 1-20, typically nprobe <= sqrt(nlist)
""",
            FaissIndexType.IVF_PQ: """
- **nlist**: Number of cluster centers
- **nprobe**: Number of clusters to search
- **m**: Number of sub-vectors for product quantization
  - Higher values: better accuracy, more memory
  - Lower values: less memory, lower accuracy
  - Recommended: 4-16
- **nbits**: Number of bits per sub-vector
  - Higher values: better accuracy, more memory
  - Lower values: less memory, lower accuracy
  - Recommended: 8 (standard)
""",
            FaissIndexType.HNSW_FLAT: """
- **m**: Number of bidirectional links per node
  - Higher values: better accuracy, more memory, slower construction
  - Lower values: less memory, faster construction, lower accuracy
  - Recommended: 4-32
""",
            FaissIndexType.HNSW_PQ: """
- **m**: Number of bidirectional links per node
- **nbits**: Number of bits per sub-vector for quantization
"""
        }
        return guides.get(index_type, "No specific parameters for this index type.")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "current_project": self.current_project,
            "current_index": self.current_index,
            "indexes_count": len(self.indexes),
            "embeddings_count": len(self.embeddings),
            "search_results_count": len(self.search_results),
            "performance_metrics": self.performance_metrics,
            "skills": list(self.skills.keys())
        }
    
    def reset(self) -> None:
        """Reset agent state"""
        self.current_project = None
        self.current_index = None
        self.indexes.clear()
        self.embeddings.clear()
        self.search_results.clear()
        self.performance_metrics.clear()
        print(f"🔄 {self.name}: Agent state reset")
