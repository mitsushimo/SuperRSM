"""
Thread-safe, introspectable model registry for SuperRSM regression models.
"""

import logging
import threading
from typing import Any, Callable, Dict, List, Optional, Type, Union

from super_rsm.common.config import ModelMetadata
from super_rsm.common.exceptions import RegistryError
from super_rsm.models.base import BaseRSMModel

logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    Central thread-safe registry managing registered regression models.
    Supports class-level metadata introspection without instantiation.
    """

    _lock: threading.RLock = threading.RLock()
    _models: Dict[str, Type[BaseRSMModel]] = {}

    @classmethod
    def register(cls, model_class: Type[BaseRSMModel]) -> Type[BaseRSMModel]:
        """Register a BaseRSMModel subclass using its class-level metadata."""
        if not isinstance(model_class, type) or not issubclass(model_class, BaseRSMModel):
            raise RegistryError(f"Class {getattr(model_class, '__name__', str(model_class))} must subclass BaseRSMModel.")

        metadata = model_class.get_metadata()
        name = metadata.name

        with cls._lock:
            if name in cls._models:
                logger.warning(f"Overwriting previously registered model '{name}'.")
            cls._models[name] = model_class

        return model_class

    @classmethod
    def get(cls, name: str) -> Type[BaseRSMModel]:
        """Retrieve registered model class by unique identifier name."""
        with cls._lock:
            if name not in cls._models:
                raise RegistryError(f"Unknown regression model '{name}'. Available: {cls.list_names()}")
            return cls._models[name]

    @classmethod
    def create(cls, name: str, **hyperparameters: Any) -> BaseRSMModel:
        """Factory method instantiating a registered model with hyperparameters."""
        model_cls = cls.get(name)
        return model_cls(**hyperparameters)

    @classmethod
    def list_names(cls) -> List[str]:
        """Return list of all registered model names."""
        with cls._lock:
            return sorted(list(cls._models.keys()))

    @classmethod
    def get_metadata(cls, name: str) -> ModelMetadata:
        """Retrieve metadata for a model without instantiating it."""
        return cls.get(name).get_metadata()

    @classmethod
    def get_all_metadata(cls) -> Dict[str, ModelMetadata]:
        """Retrieve metadata mapping for all registered models for dynamic GUI forms."""
        with cls._lock:
            return {name: model_cls.get_metadata() for name, model_cls in cls._models.items()}

    @classmethod
    def contains(cls, name: str) -> bool:
        """Check whether a model name is registered."""
        with cls._lock:
            return name in cls._models

    @classmethod
    def unregister(cls, name: str) -> None:
        """Remove a model from the registry."""
        with cls._lock:
            cls._models.pop(name, None)

    @classmethod
    def clear(cls) -> None:
        """Clear all registered models (primarily for test fixture isolation)."""
        with cls._lock:
            cls._models.clear()


def register_model(
    cls_or_none: Optional[Type[BaseRSMModel]] = None,
) -> Union[Type[BaseRSMModel], Callable[[Type[BaseRSMModel]], Type[BaseRSMModel]]]:
    """Decorator for registering BaseRSMModel subclasses."""
    def decorator(subclass: Type[BaseRSMModel]) -> Type[BaseRSMModel]:
        ModelRegistry.register(subclass)
        return subclass

    if cls_or_none is not None:
        return decorator(cls_or_none)
    return decorator


# Convenient alias for decorator
register_rsm_model = register_model


def get_supported_methods() -> List[str]:
    """Return list of all registered model names."""
    return ModelRegistry.list_names()


def get_metadata(name: str) -> ModelMetadata:
    """Convenience accessor for model metadata."""
    return ModelRegistry.get_metadata(name)
