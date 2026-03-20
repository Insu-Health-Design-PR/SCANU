"""Layer 1 60 GHz presence radar module."""

from .port_resolver import Presence60GPortResolver
from .presence_models import (
    BGT60LTR11AIP_SENSOR_MODEL,
    DEMOBGT60LTR11AIPTOBO1_BOARD_KIT,
    PresenceFeatures,
    PresenceFrame,
    PresenceSample,
)
from .presence_processor import PresenceProcessor
from .presence_source import (
    BGT60LTR11AIPSerialConfig,
    BGT60LTR11AIPSerialProvider,
    MockPresenceProvider,
    PresenceSource,
)

__all__ = [
    "BGT60LTR11AIP_SENSOR_MODEL",
    "BGT60LTR11AIPSerialConfig",
    "BGT60LTR11AIPSerialProvider",
    "DEMOBGT60LTR11AIPTOBO1_BOARD_KIT",
    "MockPresenceProvider",
    "Presence60GPortResolver",
    "PresenceFeatures",
    "PresenceFrame",
    "PresenceProcessor",
    "PresenceSample",
    "PresenceSource",
]
