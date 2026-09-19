from models.graph import Graph
from dataclasses import dataclass, field
from simulation.drone import Drone, DroneStatus
from simulation.movement import Movement, MovementStatus


@dataclass(slots=True)
class SimulationState:
    graph: Graph
    drones: dict[int, Drone]
    turn_number: int = 0
    active_movements: dict[int, Movement] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate the initial state."""
        if self.turn_number < 0:
            raise ValueError("turn_number cannot be negative.")

        if not self.drones:
            raise ValueError("At least one drone is required.")

        for drone_id, drone in self.drones.items():
            if drone_id != drone.drone_id:
                raise ValueError(
                    "Drone dictionary key must match drone_id."
                )

            if drone.current_zone not in self.graph.zones:
                raise ValueError(
                    f"Unknown current zone '{drone.current_zone}'."
                )

    @property
    def delivered_count(self) -> int:
        """Return the number of delivered drones."""
        return sum(
            drone.is_delivered
            for drone in self.drones.values()
        )

    @property
    def all_delivered(self) -> bool:
        return self.delivered_count == len(self.drones)

    @property
    def active_movement_count(self) -> int:
        return len(self.active_movements)

    def get_drone(self, drone_id) -> Drone:
        try:
            return self.drones[drone_id]
        except KeyError as e:
            raise KeyError(
                f"Unknown drone ID: {drone_id}"
            ) from e

    def drones_in_zone(self, zone_name: str) -> list[Drone]:
        self._validate_zone_name(zone_name)

        return [
            drone
            for drone in self.drones.values()
            if drone.current_zone == zone_name
            and drone.status is not DroneStatus.IN_TRANSIT
            and drone.status is not DroneStatus.DELIVERED
        ]

    def zone_occupancy(self, zone_name: str) -> int:
        return len(self.drones_in_zone(zone_name))

    def connection_occupancy(self, source: str,
                             destination: str,) -> int:
        connection_key = frozenset((source, destination))

        return sum(
            movement.connection_key == connection_key
            and movement.status is MovementStatus.IN_PROGRESS
            for movement in self.active_movements.values()
        )

    def can_enter_zone(self, zone_name: str, reserved_departures: int = 0,
                       reserved_entries: int = 0
                       ) -> bool:
        self._validate_zone_name(zone_name)

        if reserved_entries < 0:
            raise ValueError("reserved_entries cannot be negative.")

        if reserved_departures < 0:
            raise ValueError("reserved_departures cannot be negative.")

        if zone_name in {self.graph.start_name, self.graph.end_name}:
            return True

        zone = self.graph.zones[zone_name]
        occupancy = self.zone_occupancy(zone_name)
        active_reservations = self.destination_reservations(zone_name)

        projected_occupancy = (
            occupancy - reserved_departures
            + active_reservations + reserved_entries
        )

        return projected_occupancy < zone.max_drones

    def can_use_connection(
        self,
        source: str,
        destination: str,
        reserved_uses: int = 0,
         ) -> bool:
        """Return whether another drone may use a connection."""
        if reserved_uses < 0:
            raise ValueError(
                "reserved_uses cannot be negative."
            )

        connection = self.graph.get_connection(
            source,
            destination,
        )

        occupancy = self.connection_occupancy(
            source,
            destination,
        )

        return (
            occupancy + reserved_uses
            < connection.max_capacity
        )

    def register_movement(self, movement: Movement) -> None:
        drone = self.get_drone(movement.drone_id)
        if movement.drone_id in self.active_movements:
            raise RuntimeError(
                f"{movement.identifier} already has an active movement."
                )
        if drone.status is DroneStatus.DELIVERED:
            raise (
                f"'{movement.identifier}' is alresdy deliverd."
            )
        if drone.current_zone != movement.source:
            raise ValueError(
                f"'{movement.identifier}' is not in '{movement.source}'"
            )
        if drone.next_zone != movement.destination:
            raise ValueError(
                f"'{movement.identifier}' cannot move to"
                f" '{movement.destination}'."
            )
        if movement.status is MovementStatus.PLANNED:
            movement.start()
        if movement.status is not MovementStatus.IN_PROGRESS:
            raise ValueError(
                "Only an active movment can be registered."
            )
        if movement.duration > 1:
            drone.start_transit(
                destination=movement.destination,
                duration=movement.duration
            )
        self.active_movements[movement.drone_id] = movement

    def complete_movement(self, drone_id: int) -> Movement:
        try:
            movement = self.active_movements[drone_id]
        except KeyError as e:
            raise KeyError(
                f"Drone D{drone_id} has no active movemeent."
            ) from e

        if movement.status is not MovementStatus.COMPLETED:
            raise RuntimeError(
                "Movement must be completed first."
            )

        drone = self.get_drone(drone_id)
        drone.enter_zone(movement.destination)

        del self.active_movements[drone_id]
        return movement

    def advance_active_movements(self) -> list[Movement]:
        completed: list[Movement] = []

        for movement in list(self.active_movements.values()):
            drone = self.get_drone(movement.drone_id)

            movement_completed = movement.advance()
            if drone.status is DroneStatus.IN_TRANSIT:
                drone_completed = drone.advance_transit()
                if drone_completed != movement_completed:
                    raise RuntimeError(
                        "Drone and movement transit states are out of sync."
                    )
            if movement_completed:
                completed.append(movement)
        return completed

    def increment_turn(self) -> None:
        self.turn_number += 1
        for drone in self.drones.values():
            drone.begin_turn()

    def _validate_zone_name(self, zone_name: str) -> None:
        if zone_name not in self.graph.zones:
            raise KeyError(f"Unknown zone : '{zone_name}'.")

    def destination_reservations(self, zone_name: str) -> int:
        """Count active movements reserving a destination zone."""
        self._validate_zone_name(zone_name)

        return sum(
            movement.destination == zone_name
            and movement.status is MovementStatus.IN_PROGRESS
            for movement in self.active_movements.values()
        )
