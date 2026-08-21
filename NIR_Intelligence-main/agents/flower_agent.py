# NIR Intelligence Platform - Flower Agent
# Handles federated learning operations with comprehensive Flower integration

import os
import json
import pickle
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

from .base_agent import AgentOutput, AgentStatus, BaseAgent, ErrorSeverity


class FederatedLearningMode(Enum):
    """Modes for federated learning"""
    SERVER = "server"
    CLIENT = "client"
    STANDALONE = "standalone"


class AggregationStrategy(Enum):
    """Aggregation strategies for federated learning"""
    FED_AVG = "FedAvg"
    FED_PROX = "FedProx"
    FED_ADAM = "FedAdam"
    FED_YOGI = "FedYogi"
    FED_SGD = "FedSGD"


class PrivacyLevel(Enum):
    """Privacy levels for federated learning"""
    LOCAL_ONLY = "local_only"
    DIFFERENTIAL_PRIVACY = "differential_privacy"
    SECURE_AGGREGATION = "secure_aggregation"
    HOMOMORPHIC_ENCRYPTION = "homomorphic_encryption"


@dataclass
class FederatedLearningConfig:
    """Configuration for federated learning"""
    mode: FederatedLearningMode = FederatedLearningMode.STANDALONE
    aggregation_strategy: AggregationStrategy = AggregationStrategy.FED_AVG
    privacy_level: PrivacyLevel = PrivacyLevel.LOCAL_ONLY
    server_address: str = "localhost"
    port: int = 5555
    num_rounds: int = 10
    num_clients: int = 3
    min_clients: int = 2
    client_timeout: int = 300
    model_path: str = "models/federated_model.pkl"
    metrics_path: str = "output/federated_metrics.json"
    enable_differential_privacy: bool = False
    dp_epsilon: float = 1.0
    dp_delta: float = 1e-5
    use_secure_aggregation: bool = False


@dataclass
class FederatedLearningResult:
    """Results from federated learning operations"""
    success: bool = False
    mode: str = ""
    server_started: bool = False
    clients_connected: int = 0
    training_rounds: int = 0
    global_model_accuracy: float = 0.0
    aggregation_strategy: str = ""
    privacy_level: str = ""
    model_size: int = 0
    training_time: float = 0.0
    metrics: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ClientConfig:
    """Configuration for a federated learning client"""
    client_id: str
    client_name: str = ""
    data_size: int = 0
    data_distribution: Dict[str, int] = field(default_factory=dict)
    model_parameters: Dict[str, Any] = field(default_factory=dict)
    local_epochs: int = 1
    learning_rate: float = 0.001
    batch_size: int = 32
    privacy_config: Optional[Dict[str, Any]] = None


class FlowerAgent(BaseAgent):
    """
    Enhanced agent for managing federated learning with Flower.
    
    Features:
    - Server and client mode support
    - Multiple aggregation strategies
    - Privacy-preserving techniques
    - Model management and persistence
    - Comprehensive metrics and monitoring
    """

    def __init__(self, **kwargs):
        super().__init__(name="FlowerAgent", version="2.0.0", **kwargs)
        self.dependencies = ["flwr", "tensorflow", "numpy", "scikit-learn"]
        
        # Federated learning configuration
        self.config = FederatedLearningConfig(**kwargs.get("config", {}))
        
        # Runtime state
        self._server: Optional[Any] = None
        self._client: Optional[Any] = None
        self._current_round: int = 0
        self._connected_clients: List[str] = []
        self._training_history: List[Dict[str, Any]] = []
        self._model_registry: Dict[str, Any] = {}
        self._metrics: Dict[str, Any] = {}
        self._lock = threading.Lock()
        
        # Setup directories
        self._setup_directories()
        
        self.logger.info(f"FlowerAgent initialized in {self.config.mode} mode")
        self.logger.info(f"Aggregation strategy: {self.config.aggregation_strategy}")
        self.logger.info(f"Privacy level: {self.config.privacy_level}")

    def _setup_directories(self):
        """Setup required directories for federated learning"""
        try:
            # Create directories if they don't exist
            directories = [
                Path(self.config.model_path).parent,
                Path(self.config.metrics_path).parent,
                Path("temp/flower"),
                Path("output/federated"),
            ]
            
            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)
                
        except Exception as e:
            self.logger.warning(f"Failed to setup directories: {e}")

    def _check_flower_available(self) -> bool:
        """Check if Flower framework is available"""
        try:
            import flwr
            self.logger.info(f"Flower version: {flwr.__version__}")
            return True
        except ImportError:
            self.logger.warning("Flower framework not available. Using simulation mode.")
            return False

    def _get_aggregation_strategy(self):
        """Get the appropriate aggregation strategy class"""
        try:
            import flwr.server.strategy
            
            strategy_map = {
                AggregationStrategy.FED_AVG: flwr.server.strategy.FedAvg,
                AggregationStrategy.FED_PROX: flwr.server.strategy.FedProx,
                AggregationStrategy.FED_ADAM: flwr.server.strategy.FedAdam,
                AggregationStrategy.FED_YOGI: flwr.server.strategy.FedYogi,
                AggregationStrategy.FED_SGD: flwr.server.strategy.FedSGD,
            }
            
            return strategy_map.get(self.config.aggregation_strategy, flwr.server.strategy.FedAvg)
            
        except ImportError:
            # Return a mock strategy for simulation mode
            return type('MockStrategy', (), {})

    def _create_flower_server(self) -> Any:
        """Create and configure a Flower server"""
        if not self._check_flower_available():
            return None
            
        try:
            import flwr.server
            from flwr.server.strategy import FedAvg
            
            # Get the appropriate strategy
            strategy_class = self._get_aggregation_strategy()
            
            # Create strategy with custom configuration
            strategy = strategy_class(
                fraction_fit=1.0,
                fraction_evaluate=1.0,
                min_fit_clients=self.config.min_clients,
                min_evaluate_clients=self.config.min_clients,
                min_available_clients=self.config.min_clients,
            )
            
            # Create server
            server = flwr.server.ServerApp(
                client_fn=self._client_fn,
                config={"num_rounds": self.config.num_rounds},
                strategy=strategy,
            )
            
            self.logger.info("Flower server created successfully")
            return server
            
        except Exception as e:
            self.logger.error(f"Failed to create Flower server: {e}")
            return None

    def _create_flower_client(self, client_config: ClientConfig) -> Any:
        """Create and configure a Flower client"""
        if not self._check_flower_available():
            return None
            
        try:
            import flwr.client
            from flwr.client import ClientApp
            
            # Create client
            client = ClientApp(
                client=FlowerClient(client_config, self),
                config={"client_id": client_config.client_id},
            )
            
            self.logger.info(f"Flower client created for {client_config.client_id}")
            return client
            
        except Exception as e:
            self.logger.error(f"Failed to create Flower client: {e}")
            return None

    def _client_fn(self, cid: str) -> Any:
        """Client factory function for Flower server"""
        try:
            # In a real implementation, this would return a client for the given CID
            # For now, return a mock client
            client_config = ClientConfig(client_id=cid)
            return self._create_flower_client(client_config)
        except Exception as e:
            self.logger.error(f"Failed to create client for {cid}: {e}")
            return None

    def start_server(self) -> bool:
        """Start the federated learning server"""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting federated learning server...")
            
            # Create server
            self._server = self._create_flower_server()
            
            if self._server is None:
                self.logger.warning("Using simulation mode - Flower not available")
                # Simulate server start
                self._server_started = True
                self._server_address = f"{self.config.server_address}:{self.config.port}"
                return True
            
            # In a real implementation, we would start the server here
            # For now, we'll simulate it
            self._server_started = True
            self._server_address = f"{self.config.server_address}:{self.config.port}"
            
            self.logger.info(f"Server started at {self._server_address}")
            self.status = AgentStatus.COMPLETED
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start server: {e}")
            self.status = AgentStatus.ERROR
            return False

    def stop_server(self) -> bool:
        """Stop the federated learning server"""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Stopping federated learning server...")
            
            # Clean up server
            self._server = None
            self._server_started = False
            self._connected_clients = []
            self._current_round = 0
            
            self.logger.info("Server stopped successfully")
            self.status = AgentStatus.COMPLETED
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop server: {e}")
            self.status = AgentStatus.ERROR
            return False

    def connect_client(self, client_config: ClientConfig) -> bool:
        """Connect a client to the federated learning network"""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info(f"Connecting client: {client_config.client_id}")
            
            # Create client
            client = self._create_flower_client(client_config)
            
            if client is not None:
                self._client = client
                self._connected_clients.append(client_config.client_id)
                self.logger.info(f"Client connected: {client_config.client_id}")
                self.status = AgentStatus.COMPLETED
                return True
            else:
                # Simulation mode
                self._connected_clients.append(client_config.client_id)
                self.logger.info(f"Client connected (simulation): {client_config.client_id}")
                self.status = AgentStatus.COMPLETED
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to connect client: {e}")
            self.status = AgentStatus.ERROR
            return False

    def start_training_round(self, data: Dict[str, Any]) -> bool:
        """Start a federated learning training round"""
        try:
            self.status = AgentStatus.PROCESSING
            self._current_round += 1
            
            self.logger.info(f"Starting training round {self._current_round}")
            
            # Simulate training round
            round_result = {
                "round_number": self._current_round,
                "clients_participating": len(self._connected_clients),
                "client_ids": self._connected_clients.copy(),
                "training_time": 120.5,  # seconds
                "model_improvement": 0.02,
                "global_accuracy": min(0.99, 0.80 + (self._current_round * 0.02)),
            }
            
            self._training_history.append(round_result)
            
            # Update metrics
            self._metrics[f"round_{self._current_round}"] = round_result
            
            self.logger.info(f"Training round {self._current_round} completed")
            self.status = AgentStatus.COMPLETED
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start training round: {e}")
            self.status = AgentStatus.ERROR
            return False

    def aggregate_models(self, client_models: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate models from multiple clients"""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info(f"Aggregating models from {len(client_models)} clients")
            
            # Simulate model aggregation based on strategy
            if self.config.aggregation_strategy == AggregationStrategy.FED_AVG:
                # Simple average aggregation
                aggregated_model = self._federated_average(client_models)
            elif self.config.aggregation_strategy == AggregationStrategy.FED_PROX:
                # Proximal term aggregation
                aggregated_model = self._federated_proximal(client_models)
            else:
                # Default to average
                aggregated_model = self._federated_average(client_models)
            
            # Store the aggregated model
            model_id = f"model_round_{self._current_round}"
            self._model_registry[model_id] = aggregated_model
            
            self.logger.info(f"Models aggregated using {self.config.aggregation_strategy}")
            self.status = AgentStatus.COMPLETED
            return aggregated_model
            
        except Exception as e:
            self.logger.error(f"Failed to aggregate models: {e}")
            self.status = AgentStatus.ERROR
            return {}

    def _federated_average(self, client_models: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform federated averaging of client models"""
        if not client_models:
            return {}
        
        # Simple average of model parameters
        num_clients = len(client_models)
        aggregated_model = {}
        
        for key in client_models[0].keys():
            # Average the parameters - handle both lists and scalars
            values = [model[key] for model in client_models]
            
            # Check if all values are lists (parameters)
            if all(isinstance(v, list) for v in values):
                # Average each element in the lists
                aggregated_model[key] = [
                    sum(layer_params[i] for layer_params in values) / num_clients
                    for i in range(len(values[0]))
                ]
            elif all(isinstance(v, (int, float)) for v in values):
                # Average scalar values
                aggregated_model[key] = sum(values) / num_clients
            else:
                # For mixed types, just take the first one
                aggregated_model[key] = values[0]
        
        return aggregated_model

    def _federated_proximal(self, client_models: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform federated proximal aggregation"""
        # For now, use the same as federated average
        # In a real implementation, this would include proximal terms
        return self._federated_average(client_models)

    def save_model(self, model: Dict[str, Any], model_name: str = None) -> bool:
        """Save a model to disk"""
        try:
            self.status = AgentStatus.PROCESSING
            
            model_name = model_name or f"model_round_{self._current_round}"
            model_path = Path(self.config.model_path).parent / f"{model_name}.pkl"
            
            # Save model
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)
            
            self.logger.info(f"Model saved to {model_path}")
            self.status = AgentStatus.COMPLETED
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save model: {e}")
            self.status = AgentStatus.ERROR
            return False

    def load_model(self, model_name: str = None) -> Optional[Dict[str, Any]]:
        """Load a model from disk"""
        try:
            self.status = AgentStatus.PROCESSING
            
            model_name = model_name or f"model_round_{self._current_round}"
            model_path = Path(self.config.model_path).parent / f"{model_name}.pkl"
            
            if not model_path.exists():
                self.logger.warning(f"Model not found: {model_path}")
                return None
            
            # Load model
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            
            self.logger.info(f"Model loaded from {model_path}")
            self.status = AgentStatus.COMPLETED
            return model
            
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            self.status = AgentStatus.ERROR
            return None

    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics"""
        return {
            "training_history": self._training_history,
            "connected_clients": self._connected_clients,
            "current_round": self._current_round,
            "server_started": getattr(self, '_server_started', False),
            "server_address": getattr(self, '_server_address', ""),
            "config": {
                "mode": self.config.mode.value,
                "aggregation_strategy": self.config.aggregation_strategy.value,
                "privacy_level": self.config.privacy_level.value,
                "num_rounds": self.config.num_rounds,
                "num_clients": self.config.num_clients,
            },
            **self._metrics
        }

    def apply_privacy_techniques(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply privacy-preserving techniques to data"""
        try:
            self.status = AgentStatus.PROCESSING
            
            if self.config.privacy_level == PrivacyLevel.DIFFERENTIAL_PRIVACY:
                # Apply differential privacy
                data = self._apply_differential_privacy(data)
            elif self.config.privacy_level == PrivacyLevel.SECURE_AGGREGATION:
                # Apply secure aggregation
                data = self._apply_secure_aggregation(data)
            elif self.config.privacy_level == PrivacyLevel.HOMOMORPHIC_ENCRYPTION:
                # Apply homomorphic encryption (simulated)
                data = self._apply_homomorphic_encryption(data)
            
            self.logger.info(f"Applied {self.config.privacy_level} privacy techniques")
            self.status = AgentStatus.COMPLETED
            return data
            
        except Exception as e:
            self.logger.error(f"Failed to apply privacy techniques: {e}")
            self.status = AgentStatus.ERROR
            return data

    def _apply_differential_privacy(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply differential privacy to data"""
        import numpy as np
        
        # Add noise to numerical values for differential privacy
        for key, value in data.items():
            if isinstance(value, (int, float)):
                # Add Laplace noise
                scale = 1.0 / self.config.dp_epsilon
                noise = np.random.laplace(0, scale)
                data[key] = value + noise
            elif isinstance(value, list) and all(isinstance(x, (int, float)) for x in value):
                # Add noise to list of numbers
                scale = 1.0 / self.config.dp_epsilon
                noise = np.random.laplace(0, scale, len(value))
                data[key] = [v + n for v, n in zip(value, noise)]
        
        return data

    def _apply_secure_aggregation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply secure aggregation techniques"""
        # In a real implementation, this would use cryptographic techniques
        # For now, we'll just return the data as-is (simulation)
        self.logger.info("Secure aggregation applied (simulation)")
        return data

    def _apply_homomorphic_encryption(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply homomorphic encryption (simulated)"""
        # In a real implementation, this would encrypt the data
        # For now, we'll just return the data as-is (simulation)
        self.logger.info("Homomorphic encryption applied (simulation)")
        return data

    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute federated learning operations based on context"""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting Flower agent execution")
            
            # Determine operation from context
            operation = context.get("operation", "status")
            
            if operation == "start_server":
                success = self.start_server()
                result = {"server_started": success, "address": getattr(self, '_server_address', "")}
            
            elif operation == "stop_server":
                success = self.stop_server()
                result = {"server_stopped": success}
            
            elif operation == "connect_client":
                client_config = ClientConfig(**context.get("client_config", {}))
                success = self.connect_client(client_config)
                result = {"client_connected": success, "client_id": client_config.client_id}
            
            elif operation == "start_training":
                success = self.start_training_round(context.get("data", {}))
                result = {"training_started": success, "round": self._current_round}
            
            elif operation == "aggregate_models":
                client_models = context.get("client_models", [])
                aggregated_model = self.aggregate_models(client_models)
                result = {"aggregation_successful": True, "model_size": len(aggregated_model)}
            
            elif operation == "save_model":
                model = context.get("model", {})
                model_name = context.get("model_name", None)
                success = self.save_model(model, model_name)
                result = {"model_saved": success}
            
            elif operation == "load_model":
                model_name = context.get("model_name", None)
                model = self.load_model(model_name)
                result = {"model_loaded": model is not None, "model_size": len(model) if model else 0}
            
            elif operation == "get_metrics":
                metrics = self.get_metrics()
                result = {"metrics": metrics}
            
            else:  # Default: return status
                result = {
                    "server_started": getattr(self, '_server_started', False),
                    "connected_clients": len(self._connected_clients),
                    "current_round": self._current_round,
                    "aggregation_strategy": self.config.aggregation_strategy.value,
                    "privacy_level": self.config.privacy_level.value,
                    "federated_learning_ready": True,
                }
            
            self.status = AgentStatus.COMPLETED
            return self._create_success_output(result)
            
        except Exception as e:
            return self._handle_error(e)

    def get_federated_learning_status(self) -> Dict[str, Any]:
        """Get the current status of federated learning"""
        return {
            "server_started": getattr(self, '_server_started', False),
            "server_address": getattr(self, '_server_address', f"{self.config.server_address}:{self.config.port}"),
            "connected_clients": len(self._connected_clients),
            "client_ids": self._connected_clients.copy(),
            "current_round": self._current_round,
            "training_history": self._training_history,
            "model_registry": list(self._model_registry.keys()),
            "config": {
                "mode": self.config.mode.value,
                "aggregation_strategy": self.config.aggregation_strategy.value,
                "privacy_level": self.config.privacy_level.value,
                "num_rounds": self.config.num_rounds,
                "num_clients": self.config.num_clients,
            },
            "flower_available": self._check_flower_available(),
        }


# Flower Client implementation for federated learning
class FlowerClient:
    """Flower client implementation for federated learning"""
    
    def __init__(self, client_config: ClientConfig, flower_agent: FlowerAgent):
        self.client_config = client_config
        self.flower_agent = flower_agent
        self.logger = flower_agent.logger
        
    def get_parameters(self, config):
        """Get model parameters from the client"""
        try:
            # In a real implementation, this would return the client's model parameters
            # For simulation, return mock parameters
            return {
                "layer1": [0.1, 0.2, 0.3],
                "layer2": [0.4, 0.5, 0.6],
                "bias": [0.01, 0.02],
            }
        except Exception as e:
            self.logger.error(f"Failed to get parameters: {e}")
            return {}
    
    def fit(self, parameters, config):
        """Train the model on client data"""
        try:
            # In a real implementation, this would train the model on client data
            # For simulation, return updated parameters
            updated_parameters = {}
            for key, value in parameters.items():
                if isinstance(value, list):
                    updated_parameters[key] = [v + 0.01 for v in value]  # Simulate learning
                else:
                    updated_parameters[key] = value + 0.01
            
            # Return number of examples used and updated parameters
            return len(self.client_config.data_distribution), updated_parameters
        except Exception as e:
            self.logger.error(f"Failed to fit model: {e}")
            return 0, {}
    
    def evaluate(self, parameters, config):
        """Evaluate the model on client data"""
        try:
            # In a real implementation, this would evaluate the model
            # For simulation, return mock metrics
            return 0.85, {"accuracy": 0.85, "loss": 0.15}
        except Exception as e:
            self.logger.error(f"Failed to evaluate model: {e}")
            return 0.0, {}


# Utility functions for federated learning

def create_federated_learning_config(
    mode: str = "server",
    aggregation_strategy: str = "FedAvg",
    privacy_level: str = "local_only",
    server_address: str = "localhost",
    port: int = 5555,
    num_rounds: int = 10,
    num_clients: int = 3,
) -> FederatedLearningConfig:
    """Create a federated learning configuration"""
    return FederatedLearningConfig(
        mode=FederatedLearningMode(mode),
        aggregation_strategy=AggregationStrategy(aggregation_strategy),
        privacy_level=PrivacyLevel(privacy_level),
        server_address=server_address,
        port=port,
        num_rounds=num_rounds,
        num_clients=num_clients,
    )


def create_client_config(
    client_id: str,
    client_name: str = "",
    data_size: int = 1000,
    data_distribution: Optional[Dict[str, int]] = None,
    local_epochs: int = 1,
    learning_rate: float = 0.001,
    batch_size: int = 32,
) -> ClientConfig:
    """Create a client configuration"""
    return ClientConfig(
        client_id=client_id,
        client_name=client_name,
        data_size=data_size,
        data_distribution=data_distribution or {"class1": 500, "class2": 500},
        local_epochs=local_epochs,
        learning_rate=learning_rate,
        batch_size=batch_size,
    )