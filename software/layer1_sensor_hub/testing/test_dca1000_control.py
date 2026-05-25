from layer1_sensor_hub.mmwave_dca.dca1000_control import (
    Dca1000Command,
    Dca1000NativeClient,
    default_fpga_payload,
    default_packet_payload,
    network_from_config,
)


def test_dca1000_command_packet_frame() -> None:
    packet = Dca1000NativeClient._build_packet(Dca1000Command.RECORD_START, b"")
    assert packet == bytes.fromhex("5a a5 05 00 00 00 aa ee")


def test_network_from_ti_config() -> None:
    config = {
        "DCA1000Config": {
            "ethernetConfig": {
                "DCA1000IPAddress": "192.168.33.180",
                "DCA1000ConfigPort": 4096,
                "DCA1000DataPort": 4098,
            },
            "ethernetConfigUpdate": {"systemIPAddress": "192.168.33.30"},
        }
    }
    network = network_from_config(config)
    assert network.pc_ip == "192.168.33.30"
    assert network.dca_ip == "192.168.33.180"
    assert network.config_port == 4096
    assert network.data_port == 4098


def test_default_payloads_support_hex_override() -> None:
    config = {
        "DCA1000Config": {
            "packetDelay_us": 25,
            "nativeCommandPayloads": {
                "fpga": "01 02 03 04",
                "packet": "19 00",
            },
        }
    }
    assert default_fpga_payload(config) == bytes.fromhex("01 02 03 04")
    assert default_packet_payload(config) == bytes.fromhex("19 00")
