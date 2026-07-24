"""Pipeline stage definitions."""
from enum import Enum


class Stage(str, Enum):
    INGEST = "ingest"
    ABM = "abm"
    SCORE = "score"
    TRAIN = "train"
    PREDICT = "predict"
