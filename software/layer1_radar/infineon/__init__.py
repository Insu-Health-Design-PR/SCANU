"""Infineon sensor integrations (BGT60* etc.)."""

from .ifx_cdc_transport import IfxCdcReply, IfxCdcTransport, crc16_ccitt_false
from .ifx_ltr11_provider import IfxLtr11PresenceProvider, IfxLtr11ProviderConfig
from .presence_models import PresenceFeatures, PresenceFrame
from .presence_processor import PresenceProcessor
from .presence_source import MockPresenceProvider, PresenceProvider, PresenceSource
from .port_resolver import Presence60GPortResolver

__all__ = [
    "IfxCdcReply",
    "IfxCdcTransport",
    "crc16_ccitt_false",
    "IfxLtr11PresenceProvider",
    "IfxLtr11ProviderConfig",
    "PresenceProvider",
    "MockPresenceProvider",
    "PresenceSource",
    "PresenceProcessor",
    "PresenceFrame",
    "PresenceFeatures",
    "Presence60GPortResolver",
]

