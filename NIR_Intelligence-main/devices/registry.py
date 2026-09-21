# NIR Intelligence Platform - Spectrometer adapter registry
# New spectrometer models are integrated by registering an adapter here;
# the platform core resolves devices by MODEL_ID and never needs changes.

from typing import Dict, List, Optional, Type

from .base_spectrometer import SpectrometerAdapter


class SpectrometerRegistry:
    """Registry of all available spectrometer adapters"""

    def __init__(self):
        self._adapters: Dict[str, Type[SpectrometerAdapter]] = {}

    def register(self, adapter_class: Type[SpectrometerAdapter]) -> Type[SpectrometerAdapter]:
        """Register an adapter class under its MODEL_ID"""
        model_id = getattr(adapter_class, "MODEL_ID", None)
        if not model_id or model_id == "unknown":
            raise ValueError(f"Adapter {adapter_class.__name__} must define a unique MODEL_ID")
        self._adapters[model_id] = adapter_class
        return adapter_class

    def get(self, model_id: str) -> Optional[Type[SpectrometerAdapter]]:
        """Look up an adapter class by model id"""
        return self._adapters.get(model_id)

    def create(self, model_id: str, config: Optional[dict] = None) -> Optional[SpectrometerAdapter]:
        """Instantiate a registered adapter with optional device config"""
        adapter_class = self._adapters.get(model_id)
        if adapter_class is None:
            return None
        return adapter_class(config=config)

    def list_models(self) -> List[str]:
        """Return all registered model ids"""
        return sorted(self._adapters.keys())

    def is_registered(self, model_id: str) -> bool:
        return model_id in self._adapters


_REGISTRY = SpectrometerRegistry()


def get_registry() -> SpectrometerRegistry:
    """Return the global spectrometer adapter registry"""
    return _REGISTRY


def register_adapter(adapter_class: Type[SpectrometerAdapter]) -> Type[SpectrometerAdapter]:
    """Convenience decorator/function to register an adapter in the global registry"""
    return _REGISTRY.register(adapter_class)
