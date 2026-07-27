"""Pipeline stage definitions."""
from enum import Enum


class Stage(str, Enum):
    INGEST = "ingest"
    ABM = "abm"
    SCORING = "scoring"
    TRAINING = "training"
    PREDICTION = "prediction"
