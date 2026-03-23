# Layer 1 - 60 GHz Presence Radar

This module provides acquisition and lightweight processing for the Infineon XENSIV 60 GHz presence radar path built around the `BGT60LTR11AIP` sensor and `DEMOBGT60LTR11AIPTOBO1` development kit.

Main API: `PresenceSource`, `PresenceSample`, `MockPresenceProvider`, `BGT60LTR11AIPSerialProvider`, and `PresenceProcessor`.

For live hardware reads, pass the serial port explicitly. Autodetection is intentionally not used in the current workflow.
