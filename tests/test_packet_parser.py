import unittest

from fh6_tuning_sim.receiver.packet_parser import (
    FIELD_NAMES,
    FIELD_SPECS,
    PACKET_SIZE,
    PACKET_STRUCT,
    PacketLengthError,
    parse_packet,
)


class PacketParserTests(unittest.TestCase):
    def test_struct_size_matches_official_packet_size(self) -> None:
        self.assertEqual(PACKET_STRUCT.size, PACKET_SIZE)

    def test_parse_packet_returns_snake_case_fields(self) -> None:
        values = []
        for field in FIELD_SPECS:
            if field.type_code == "F32":
                values.append(0.0)
            elif field.type_code == "U32":
                values.append(123)
            else:
                values.append(0)

        speed_index = FIELD_NAMES.index("speed")
        rpm_index = FIELD_NAMES.index("current_engine_rpm")
        race_index = FIELD_NAMES.index("is_race_on")
        values[speed_index] = 42.5
        values[rpm_index] = 6500.0
        values[race_index] = 1

        packet = PACKET_STRUCT.pack(*values)
        parsed = parse_packet(packet)

        self.assertEqual(len(packet), PACKET_SIZE)
        self.assertEqual(parsed["is_race_on"], 1)
        self.assertAlmostEqual(parsed["speed"], 42.5)
        self.assertAlmostEqual(parsed["current_engine_rpm"], 6500.0)
        self.assertIn("tire_combined_slip_front_left", parsed)
        self.assertIn("normalized_ai_brake_difference", parsed)

    def test_invalid_packet_length_raises(self) -> None:
        with self.assertRaises(PacketLengthError):
            parse_packet(b"\x00" * (PACKET_SIZE - 1))


if __name__ == "__main__":
    unittest.main()
