# -*- coding: utf-8 -*-
"""
Created on Mon Jun 19 22:56:25 2023

@author: blgnm
"""

from abc import ABC, abstractmethod
import pandas as pd

class Model(ABC):
    """
    Generic abstract class defining the structure of any model class (e.g. ParsnipModel).
    """
    
    @abstractmethod
    def load_model(self) -> None:
        pass
    
    @abstractmethod
    def load_classifier(self) -> None:
        pass
    
    @abstractmethod
    def classify(self) -> pd.DataFrame:
        pass
    
    @abstractmethod
    def predict_light_curve(self) -> pd.DataFrame:
        pass
    
    @abstractmethod
    def format_lc_and_meta(self) -> None:
        pass
    
    @abstractmethod
    def preprocess_dataset(self) ->None:
        pass