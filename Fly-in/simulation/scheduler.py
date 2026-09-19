"""Turn-based scheduler for drone movements."""

from dataclasses import dataclass

from models.zone import ZoneType
from simulation.drone import Drone, DroneStatus
from simulation.movement import Movement
from simulation.simulation_state import SimulationState


@dataclass(slots=True)
class TurnResult:
    """Result of one simulated turn."""

    turn_number: int
    started_movements: list[Movement]
    completed_movements: list[Movement]
    waiting_drone_ids: list[int]


class Scheduler:
    """Plan and execute valid drone movements turn by turn."""

    def run_turn(self, state: SimulationState) -> TurnResult:
        """Execute one complete simulation turn."""
        state.increment_turn()

        completed = state.advance_active_movements()

        for movement in completed:
            state.complete_movement(movement.drone_id)
        completed_drone_ids = {
            movement.drone_id
            for movement in completed
            }

        planned: list[Movement] = []
        waiting: list[int] = []

        reserved_entries: dict[str, int] = {}
        reserved_departures: dict[str, int] = {}
        reserved_connections: dict[frozenset[str], int] = {}

        candidates = [
            drone
            for drone in self._movement_candidates(state)
            if drone.drone_id not in completed_drone_ids
        ]

        # Phase 1: Plan all movements without modifying the sate.
        for drone in candidates:
            destination = drone.next_zone

            if destination is None:
                continue

            source = drone.current_zone
            connection_key = frozenset((source, destination))

            destination_entries = reserved_entries.get(destination, 0,)
            destination_departures = reserved_departures.get(destination, 0,)

            connection_uses = reserved_connections.get(connection_key, 0,)

            if not state.can_enter_zone(
                destination,
                reserved_entries=destination_entries,
                reserved_departures=destination_departures
                                        ):
                drone.wait()
                waiting.append(drone.drone_id)
                continue

            if not state.can_use_connection(
                source, destination, reserved_uses=connection_uses
                                            ):
                drone.wait()
                waiting.append(drone.drone_id)
                continue

            duration = self._movement_duration(state, destination,)

            movement = Movement(
                drone_id=drone.drone_id,
                source=source,
                destination=destination,
                duration=duration,
                remaining_turns=duration,
            )

            planned.append(movement)

            reserved_departures[source] = (
                reserved_departures.get(source, 0) + 1
            )
            reserved_entries[destination] = (
                destination_entries + 1
            )
            reserved_connections[connection_key] = (
                connection_uses + 1
            )

        # Phase 2: Start all accepted movements.
        started: list[Movement] = []

        for movement in planned:
            state.register_movement(movement)
            started.append(movement)

        # Phase 3: Apply the first movment step in this turn

        newly_completed: list[Movement] = []

        for movement in started:
            drone = state.get_drone(movement.drone_id)
            movement_completed = movement.advance()

            if drone.status is DroneStatus.IN_TRANSIT:
                drone_completed = drone.advance_transit()

                if drone_completed != movement_completed:
                    raise RuntimeError(
                        "Drone and movement transit states are out of sync."
                        )

            if movement_completed:
                state.complete_movement(movement.drone_id)
                newly_completed.append(movement)

        completed.extend(newly_completed)

        return TurnResult(
            turn_number=state.turn_number,
            started_movements=started,
            completed_movements=completed,
            waiting_drone_ids=waiting,
        )

    def run_until_complete(
        self,
        state: SimulationState,
        max_turns: int = 10_000,
    ) -> list[TurnResult]:
        """Run turns until all drones are delivered."""
        if max_turns <= 0:
            raise ValueError("max_turns must be positive.")

        results: list[TurnResult] = []

        while not state.all_delivered:
            if len(results) >= max_turns:
                raise RuntimeError(
                    "Simulation exceeded the maximum number of turns."
                )

            result = self.run_turn(state)
            results.append(result)

            if self._is_deadlocked(state, result):
                raise RuntimeError(
                    "Simulation deadlock detected."
                )

        return results

    @staticmethod
    def _movement_candidates(
        state: SimulationState,
    ) -> list[Drone]:
        """Return stationary, undelivered drones in priority order."""
        candidates = [
            drone
            for drone in state.drones.values()
            if drone.status is not DroneStatus.IN_TRANSIT
            and drone.status is not DroneStatus.DELIVERED
            and drone.drone_id not in state.active_movements
            and drone.next_zone is not None
        ]

        return sorted(
            candidates,
            key=lambda drone: (
                -drone.path_index,
                -drone.waiting_turns,
                drone.drone_id,
            ),
        )

    @staticmethod
    def _movement_duration(
        state: SimulationState,
        destination: str,
         ) -> int:
        """Return the travel duration for entering a zone."""
        zone = state.graph.zones[destination]

        if zone.zone_type is ZoneType.RESTRICTED:
            return 2

        return 1

    @staticmethod
    def _is_deadlocked(
        state: SimulationState,
        result: TurnResult,
    ) -> bool:
        """Return whether no further progress is possible."""
        return (
            not state.all_delivered
            and not result.started_movements
            and not result.completed_movements
            and not state.active_movements
        )
