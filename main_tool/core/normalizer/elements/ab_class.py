"""
Abstract base class for normalizers.
"""
from abc import ABC, abstractmethod
from typing import Any

class Normalizer(ABC):
    """
    Abstract interface for all normalizers.
    """

    @abstractmethod
    def normalize(self, value: Any) -> str:
        """
        Main function for normalizers to implement
        """
        raise NotImplementedError