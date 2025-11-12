"""
Abstract base class for the loader classes.
"""
from abc import ABC, abstractmethod
from pandas import DataFrame

class DataLoader(ABC):
    """
    ABC for all loaders returning a normalized long Dataframe.
    """

    @abstractmethod
    def load(self, path: str) -> DataFrame:
        """
        ABC for loaders
        """
        raise NotImplementedError