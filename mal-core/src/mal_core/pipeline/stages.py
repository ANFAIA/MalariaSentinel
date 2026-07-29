"""Pipeline stage definitions."""
from enum import Enum


class Stage(str, Enum):
    DOWNLOAD = "download"
    INGEST = "ingest"
    BUILD_HOSTS = "build_hosts"
    BUILD_MOBILITY = "build_mobility"
    ABM = "abm"
    SCORING = "scoring"
    TRAINING = "training"
    PREDICTION = "prediction"
