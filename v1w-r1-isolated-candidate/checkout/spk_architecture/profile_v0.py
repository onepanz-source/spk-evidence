"""SPK Architecture Profile v0.

Abstract architectural capacities.
Independent of simulator implementation.
"""

from dataclasses import dataclass, fields


@dataclass(frozen=True, slots=True)
class ProcessingElementV0:
    pe_id: str

    program_slots: int
    state_slots: int
    event_slots: int
    output_slots: int
    observation_slots: int

    accesses_per_service_tick: int

    def __post_init__(self):
        if (
            type(self.pe_id) is not str
            or not self.pe_id
            or self.pe_id.strip() != self.pe_id
        ):
            raise ValueError("invalid PE identifier")

        for field in fields(self):
            if field.name == "pe_id":
                continue

            value = getattr(self, field.name)

            minimum = (
                1
                if field.name == "accesses_per_service_tick"
                else 0
            )

            if type(value) is not int or value < minimum:
                raise ValueError(
                    f"invalid PE capacity: {field.name}"
                )


@dataclass(frozen=True, slots=True)
class ArchitectureProfileV0:
    profile_id: str
    pes: tuple[ProcessingElementV0, ...]

    def __post_init__(self):
        if (
            type(self.profile_id) is not str
            or not self.profile_id
        ):
            raise ValueError("invalid architecture profile_id")

        if type(self.pes) is not tuple or not self.pes:
            raise ValueError("architecture requires PE tuple")

        if any(
            type(pe) is not ProcessingElementV0
            for pe in self.pes
        ):
            raise ValueError("invalid processing element")

        ids = [pe.pe_id for pe in self.pes]

        if len(ids) != len(set(ids)):
            raise ValueError("duplicate PE identifier")

        # Architecture v0 supports homogeneous PEs.
        capacity_names = tuple(
            field.name
            for field in fields(ProcessingElementV0)
            if field.name != "pe_id"
        )

        def signature(pe):
            return tuple(
                getattr(pe, name)
                for name in capacity_names
            )

        reference = signature(self.pes[0])

        if any(
            signature(pe) != reference
            for pe in self.pes[1:]
        ):
            raise ValueError(
                "Architecture v0 requires homogeneous PEs"
            )
