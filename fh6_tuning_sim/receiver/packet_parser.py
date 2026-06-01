from __future__ import annotations

from dataclasses import dataclass
import re
import struct
from typing import Any, Iterable


PACKET_SIZE = 324
OFFICIAL_DOC_URL = (
    "https://support.forza.net/hc/en-us/articles/"
    "51744149102611-Forza-Horizon-6-Data-Out-Documentation"
)


def camel_to_snake(value: str) -> str:
    value = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return value.lower()


@dataclass(frozen=True)
class FieldSpec:
    official_name: str
    type_code: str

    @property
    def name(self) -> str:
        return camel_to_snake(self.official_name)

    @property
    def struct_code(self) -> str:
        return {
            "S32": "i",
            "U32": "I",
            "F32": "f",
            "U16": "H",
            "U8": "B",
            "S8": "b",
        }[self.type_code]

    @property
    def size(self) -> int:
        return {
            "S32": 4,
            "U32": 4,
            "F32": 4,
            "U16": 2,
            "U8": 1,
            "S8": 1,
        }[self.type_code]


FIELD_SPECS: tuple[FieldSpec, ...] = (
    FieldSpec("IsRaceOn", "S32"),
    FieldSpec("TimestampMS", "U32"),
    FieldSpec("EngineMaxRpm", "F32"),
    FieldSpec("EngineIdleRpm", "F32"),
    FieldSpec("CurrentEngineRpm", "F32"),
    FieldSpec("AccelerationX", "F32"),
    FieldSpec("AccelerationY", "F32"),
    FieldSpec("AccelerationZ", "F32"),
    FieldSpec("VelocityX", "F32"),
    FieldSpec("VelocityY", "F32"),
    FieldSpec("VelocityZ", "F32"),
    FieldSpec("AngularVelocityX", "F32"),
    FieldSpec("AngularVelocityY", "F32"),
    FieldSpec("AngularVelocityZ", "F32"),
    FieldSpec("Yaw", "F32"),
    FieldSpec("Pitch", "F32"),
    FieldSpec("Roll", "F32"),
    FieldSpec("NormalizedSuspensionTravelFrontLeft", "F32"),
    FieldSpec("NormalizedSuspensionTravelFrontRight", "F32"),
    FieldSpec("NormalizedSuspensionTravelRearLeft", "F32"),
    FieldSpec("NormalizedSuspensionTravelRearRight", "F32"),
    FieldSpec("TireSlipRatioFrontLeft", "F32"),
    FieldSpec("TireSlipRatioFrontRight", "F32"),
    FieldSpec("TireSlipRatioRearLeft", "F32"),
    FieldSpec("TireSlipRatioRearRight", "F32"),
    FieldSpec("WheelRotationSpeedFrontLeft", "F32"),
    FieldSpec("WheelRotationSpeedFrontRight", "F32"),
    FieldSpec("WheelRotationSpeedRearLeft", "F32"),
    FieldSpec("WheelRotationSpeedRearRight", "F32"),
    FieldSpec("WheelOnRumbleStripFrontLeft", "S32"),
    FieldSpec("WheelOnRumbleStripFrontRight", "S32"),
    FieldSpec("WheelOnRumbleStripRearLeft", "S32"),
    FieldSpec("WheelOnRumbleStripRearRight", "S32"),
    FieldSpec("WheelInPuddleFrontLeft", "S32"),
    FieldSpec("WheelInPuddleFrontRight", "S32"),
    FieldSpec("WheelInPuddleRearLeft", "S32"),
    FieldSpec("WheelInPuddleRearRight", "S32"),
    FieldSpec("SurfaceRumbleFrontLeft", "F32"),
    FieldSpec("SurfaceRumbleFrontRight", "F32"),
    FieldSpec("SurfaceRumbleRearLeft", "F32"),
    FieldSpec("SurfaceRumbleRearRight", "F32"),
    FieldSpec("TireSlipAngleFrontLeft", "F32"),
    FieldSpec("TireSlipAngleFrontRight", "F32"),
    FieldSpec("TireSlipAngleRearLeft", "F32"),
    FieldSpec("TireSlipAngleRearRight", "F32"),
    FieldSpec("TireCombinedSlipFrontLeft", "F32"),
    FieldSpec("TireCombinedSlipFrontRight", "F32"),
    FieldSpec("TireCombinedSlipRearLeft", "F32"),
    FieldSpec("TireCombinedSlipRearRight", "F32"),
    FieldSpec("SuspensionTravelMetersFrontLeft", "F32"),
    FieldSpec("SuspensionTravelMetersFrontRight", "F32"),
    FieldSpec("SuspensionTravelMetersRearLeft", "F32"),
    FieldSpec("SuspensionTravelMetersRearRight", "F32"),
    FieldSpec("CarOrdinal", "S32"),
    FieldSpec("CarClass", "S32"),
    FieldSpec("CarPerformanceIndex", "S32"),
    FieldSpec("DrivetrainType", "S32"),
    FieldSpec("NumCylinders", "S32"),
    FieldSpec("CarGroup", "U32"),
    FieldSpec("SmashableVelDiff", "F32"),
    FieldSpec("SmashableMass", "F32"),
    FieldSpec("PositionX", "F32"),
    FieldSpec("PositionY", "F32"),
    FieldSpec("PositionZ", "F32"),
    FieldSpec("Speed", "F32"),
    FieldSpec("Power", "F32"),
    FieldSpec("Torque", "F32"),
    FieldSpec("TireTempFrontLeft", "F32"),
    FieldSpec("TireTempFrontRight", "F32"),
    FieldSpec("TireTempRearLeft", "F32"),
    FieldSpec("TireTempRearRight", "F32"),
    FieldSpec("Boost", "F32"),
    FieldSpec("Fuel", "F32"),
    FieldSpec("DistanceTraveled", "F32"),
    FieldSpec("BestLap", "F32"),
    FieldSpec("LastLap", "F32"),
    FieldSpec("CurrentLap", "F32"),
    FieldSpec("CurrentRaceTime", "F32"),
    FieldSpec("LapNumber", "U16"),
    FieldSpec("RacePosition", "U8"),
    FieldSpec("Accel", "U8"),
    FieldSpec("Brake", "U8"),
    FieldSpec("Clutch", "U8"),
    FieldSpec("HandBrake", "U8"),
    FieldSpec("Gear", "U8"),
    FieldSpec("Steer", "S8"),
    FieldSpec("NormalizedDrivingLine", "S8"),
    FieldSpec("NormalizedAIBrakeDifference", "S8"),
)

FIELD_NAMES = tuple(field.name for field in FIELD_SPECS)

# The official field list accounts for 323 named bytes, while the documented packet
# size is 324 bytes. Treat the final byte as alignment padding and keep validation
# strict at the documented size.
PACKET_STRUCT = struct.Struct(
    "<" + "".join(field.struct_code for field in FIELD_SPECS) + "x"
)


class PacketLengthError(ValueError):
    pass


def iter_field_offsets() -> Iterable[tuple[str, str, int, int]]:
    offset = 0
    for field in FIELD_SPECS:
        yield field.name, field.type_code, offset, field.size
        offset += field.size


def parse_packet(packet: bytes, *, strict_size: bool = True) -> dict[str, Any]:
    if strict_size and len(packet) != PACKET_SIZE:
        raise PacketLengthError(
            f"Expected {PACKET_SIZE} bytes, got {len(packet)} bytes"
        )
    if len(packet) < PACKET_SIZE:
        raise PacketLengthError(
            f"Expected at least {PACKET_SIZE} bytes, got {len(packet)} bytes"
        )

    values = PACKET_STRUCT.unpack_from(packet[:PACKET_SIZE])
    return dict(zip(FIELD_NAMES, values, strict=True))


def packet_schema() -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "type": type_code,
            "offset": offset,
            "size": size,
        }
        for name, type_code, offset, size in iter_field_offsets()
    ]


def validate_schema_size() -> None:
    if PACKET_STRUCT.size != PACKET_SIZE:
        raise AssertionError(
            f"Parser struct is {PACKET_STRUCT.size} bytes, expected {PACKET_SIZE}"
        )


validate_schema_size()
