"""
Abstract base class for the loader classes.
"""
from abc import ABC, abstractmethod
from pandas import DataFrame

class DataLoader(ABC):
    """
    Abstract interface for all loaders.
    """

    @abstractmethod
    def load(self, path: str) -> DataFrame:
        """
        Main function for loaders to implement.
        """
        raise NotImplementedError
