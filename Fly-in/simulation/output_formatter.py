from simulation.movement import Movement
from simulation.scheduler import TurnResult


class OutputFormatter:

    def format_turn(self, result: TurnResult) -> str:
        complited_ids = {
            movement.drone_id
            for movement in result.completed_movements
        }

        tokens: dict[int, str] = {}

        for movement in result.started_movements:
            if movement.drone_id in complited_ids:
                continue

            if movement.duration > 1:
                tokens[movement.drone_id] = (
                    f"D{movement.drone_id}-"
                    f"{self._connection_name(movement)}"
                )

        for movement in result.completed_movements:
            tokens[movement.drone_id] = (
                f"D{movement.drone_id}-"
                f"{movement.destination}"
            )

        return " ".join(
            tokens[drone_id]
            for drone_id in sorted(tokens)
        )

    def format_simulation(self, results: list[TurnResult]) -> str:

        lines = [
            self.format_turn(result)
            for result in results
        ]

        return "\n".join(
            line
            for line in lines
            if line
        )

    @staticmethod
    def _connection_name(movement: Movement) -> str:
        return f"{movement.source}-{movement.destination}"
