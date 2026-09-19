"""High-resolution Arcade visualization for Fly-in simulations."""

from __future__ import annotations

from math import atan2, degrees
from typing import TYPE_CHECKING

import arcade

from models.zone import ZoneRole, ZoneType

if TYPE_CHECKING:
    from simulation.movement import Movement
    from simulation.simulation import SimulationResult


# High-resolution window.
WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080
WINDOW_TITLE = "Fly-in Visualizer"

# A larger logical world creates more distance between zones.
WORLD_WIDTH = 3200
WORLD_HEIGHT = 2000
MAP_PADDING = 280

TURN_DURATION = 0.80

# Smaller drones than in the previous version.
SHIP_SCALE = 0.24

# Camera configuration.
INITIAL_ZOOM = 0.78
MIN_ZOOM = 0.25
MAX_ZOOM = 5.00
ZOOM_STEP = 1.15

# Replay speed configuration.
DEFAULT_SPEED = 1.0
MIN_SPEED = 0.25
MAX_SPEED = 4.0
SPEED_STEP = 0.25

BACKGROUND_COLOR = (12, 15, 22)
CONNECTION_COLOR = (94, 108, 136)
CONNECTION_GLOW_COLOR = (42, 50, 70)
CONNECTION_TEXT_COLOR = (180, 190, 210)
TEXT_COLOR = (240, 243, 250)
ZONE_OUTLINE_COLOR = (250, 250, 250)
ZONE_SHADOW_COLOR = (6, 8, 12, 170)
HUD_BACKGROUND_COLOR = (8, 10, 16, 225)
CONTROL_BACKGROUND_COLOR = (35, 42, 58, 245)
CONTROL_OUTLINE_COLOR = (150, 165, 195)

SHIP_TEXTURES = (
    ":resources:/images/space_shooter/playerShip1_blue.png",
    ":resources:/images/space_shooter/playerShip1_green.png",
    ":resources:/images/space_shooter/playerShip1_orange.png",
    ":resources:/images/space_shooter/playerShip2_orange.png",
    ":resources:/images/space_shooter/playerShip3_orange.png",
)

ZONE_COLORS = {
    ZoneType.NORMAL: (68, 112, 195),
    ZoneType.PRIORITY: (65, 198, 116),
    ZoneType.RESTRICTED: (242, 164, 49),
    ZoneType.BLOCKED: (186, 57, 71),
}

AnimationAction = tuple[float, float, float, float]


class ReplayWindow(arcade.Window):
    """Animate an already calculated Fly-in simulation."""

    def __init__(self, result: SimulationResult) -> None:
        """Create the high-resolution replay window."""
        super().__init__(
            WINDOW_WIDTH,
            WINDOW_HEIGHT,
            WINDOW_TITLE,
            resizable=True,
        )

        self.result = result
        self.graph = result.plan.graph
        self.turns = result.turns

        self.background_color = BACKGROUND_COLOR

        self.world_camera = arcade.Camera2D()
        self.gui_camera = arcade.Camera2D()
        self.world_camera.match_window(position=True)
        self.gui_camera.match_window(position=True)

        self.playing = False
        self.speed = DEFAULT_SPEED
        self.turn_index = 0
        self.elapsed = 0.0

        self.zone_positions = self._build_zone_positions()

        # Center the camera on the larger logical map.
        self.world_camera.position = (
            WORLD_WIDTH / 2,
            WORLD_HEIGHT / 2,
        )
        self.world_camera.zoom = INITIAL_ZOOM

        self.initial_camera_position = tuple(
            self.world_camera.position
        )
        self.initial_zoom = self.world_camera.zoom

        self.sprites: dict[int, arcade.Sprite] = {}
        self.sprite_list = arcade.SpriteList()
        self.actions: dict[int, AnimationAction] = {}

        # Rotation is animated separately from position.
        self.rotation_starts: dict[int, float] = {}
        self.rotation_targets: dict[int, float] = {}

        self._create_sprites()
        self._prepare_turn()

    def _build_zone_positions(
        self,
    ) -> dict[str, tuple[float, float]]:
        """Scale map coordinates into a spacious logical world."""
        zones = list(self.graph.zones.values())

        if not zones:
            raise ValueError("The graph contains no zones.")

        xs = [zone.x for zone in zones]
        ys = [zone.y for zone in zones]

        min_x = min(xs)
        max_x = max(xs)
        min_y = min(ys)
        max_y = max(ys)

        x_span = max(max_x - min_x, 1)
        y_span = max(max_y - min_y, 1)

        usable_width = WORLD_WIDTH - 2 * MAP_PADDING
        usable_height = WORLD_HEIGHT - 2 * MAP_PADDING

        positions: dict[str, tuple[float, float]] = {}

        for zone in zones:
            world_x = (
                MAP_PADDING
                + ((zone.x - min_x) / x_span) * usable_width
            )
            world_y = (
                MAP_PADDING
                + ((zone.y - min_y) / y_span) * usable_height
            )
            positions[zone.name] = (world_x, world_y)

        return positions

    def _create_sprites(self) -> None:
        """Create one small built-in ship sprite per drone."""
        start_x, start_y = self.zone_positions[
            self.graph.start_name
        ]

        for drone_id in sorted(self.result.plan.state.drones):
            texture_path = SHIP_TEXTURES[
                (drone_id - 1) % len(SHIP_TEXTURES)
            ]
            sprite = arcade.Sprite(
                texture_path,
                scale=SHIP_SCALE,
            )

            offset_x, offset_y = self._drone_offset(drone_id)
            sprite.center_x = start_x + offset_x
            sprite.center_y = start_y + offset_y
            sprite.angle = 0.0

            self.sprites[drone_id] = sprite
            self.sprite_list.append(sprite)

    @staticmethod
    def _drone_offset(drone_id: int) -> tuple[float, float]:
        """Return a compact offset for drones sharing one zone."""
        column = (drone_id - 1) % 6
        row = ((drone_id - 1) // 6) % 6

        return (
            (column - 2.5) * 10.0,
            (row - 2.5) * 8.0,
        )

    def _position_for_zone(
        self,
        zone_name: str,
        drone_id: int,
    ) -> tuple[float, float]:
        """Return a zone position including the drone offset."""
        x, y = self.zone_positions[zone_name]
        offset_x, offset_y = self._drone_offset(drone_id)

        return x + offset_x, y + offset_y

    def _midpoint_for(
        self,
        movement: Movement,
        drone_id: int,
    ) -> tuple[float, float]:
        """Return the visual midpoint of a connection."""
        source_x, source_y = self._position_for_zone(
            movement.source,
            drone_id,
        )
        destination_x, destination_y = self._position_for_zone(
            movement.destination,
            drone_id,
        )

        return (
            (source_x + destination_x) / 2,
            (source_y + destination_y) / 2,
        )

    @staticmethod
    def _target_ship_angle(
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
    ) -> float:
        """Return the angle required to face the movement direction."""
        delta_x = end_x - start_x
        delta_y = end_y - start_y

        if delta_x == 0 and delta_y == 0:
            return 0.0

        movement_angle = degrees(
            atan2(delta_y, delta_x)
        )

        # Built-in player ships point upward at angle 0.
        return 90.0 - movement_angle

    @staticmethod
    def _shortest_angle_delta(
        start_angle: float,
        target_angle: float,
    ) -> float:
        """Return the shortest signed rotation between two angles."""
        return (
            (target_angle - start_angle + 180.0) % 360.0
        ) - 180.0

    def _prepare_turn(self) -> None:
        """Prepare position and rotation animations for one turn."""
        self.actions.clear()
        self.rotation_starts.clear()
        self.rotation_targets.clear()

        if self.turn_index >= len(self.turns):
            self.playing = False
            return

        turn = self.turns[self.turn_index]

        started = {
            movement.drone_id: movement
            for movement in turn.started_movements
        }
        completed = {
            movement.drone_id: movement
            for movement in turn.completed_movements
        }

        drone_ids = sorted(set(started) | set(completed))

        for drone_id in drone_ids:
            sprite = self.sprites[drone_id]
            start_x = sprite.center_x
            start_y = sprite.center_y

            started_movement = started.get(drone_id)
            completed_movement = completed.get(drone_id)

            if (
                started_movement is not None
                and completed_movement is not None
            ):
                end_x, end_y = self._position_for_zone(
                    completed_movement.destination,
                    drone_id,
                )
            elif started_movement is not None:
                end_x, end_y = self._midpoint_for(
                    started_movement,
                    drone_id,
                )
            elif completed_movement is not None:
                end_x, end_y = self._position_for_zone(
                    completed_movement.destination,
                    drone_id,
                )
            else:
                continue

            target_angle = self._target_ship_angle(
                start_x,
                start_y,
                end_x,
                end_y,
            )

            self.rotation_starts[drone_id] = sprite.angle
            self.rotation_targets[drone_id] = target_angle

            self.actions[drone_id] = (
                start_x,
                start_y,
                end_x,
                end_y,
            )

    def _finish_turn(self) -> None:
        """Finish the current animation and prepare the next turn."""
        if self.turn_index >= len(self.turns):
            return

        for drone_id, action in self.actions.items():
            _, _, end_x, end_y = action
            sprite = self.sprites[drone_id]
            sprite.center_x = end_x
            sprite.center_y = end_y
            sprite.angle = self.rotation_targets.get(
                drone_id,
                sprite.angle,
            )

        self.turn_index += 1
        self.elapsed = 0.0
        self._prepare_turn()

    def _reset_replay(self) -> None:
        """Reset all ships and playback state."""
        self.playing = False
        self.turn_index = 0
        self.elapsed = 0.0
        self.actions.clear()
        self.rotation_starts.clear()
        self.rotation_targets.clear()
        self.sprites.clear()
        self.sprite_list = arcade.SpriteList()

        self._create_sprites()
        self._prepare_turn()

    def _reset_camera(self) -> None:
        """Reset pan and zoom."""
        self.world_camera.position = self.initial_camera_position
        self.world_camera.zoom = self.initial_zoom

    def on_update(self, delta_time: float) -> None:
        """Advance movement and rotation animations."""
        if not self.playing:
            return

        if self.turn_index >= len(self.turns):
            self.playing = False
            return

        self.elapsed += delta_time * self.speed
        progress = min(self.elapsed / TURN_DURATION, 1.0)

        # Smoothstep produces softer motion at both ends.
        eased_progress = progress * progress * (
            3.0 - 2.0 * progress
        )

        for drone_id, action in self.actions.items():
            start_x, start_y, end_x, end_y = action
            sprite = self.sprites[drone_id]

            sprite.center_x = (
                start_x
                + (end_x - start_x) * eased_progress
            )
            sprite.center_y = (
                start_y
                + (end_y - start_y) * eased_progress
            )

            start_angle = self.rotation_starts.get(
                drone_id,
                sprite.angle,
            )
            target_angle = self.rotation_targets.get(
                drone_id,
                start_angle,
            )
            angle_delta = self._shortest_angle_delta(
                start_angle,
                target_angle,
            )
            sprite.angle = (
                start_angle
                + angle_delta * eased_progress
            )

        if progress >= 1.0:
            self._finish_turn()

    def on_draw(self) -> None:
        """Draw the high-resolution world and fixed interface."""
        self.clear()

        self.world_camera.use()
        self._draw_connections()
        self._draw_zones()
        self.sprite_list.draw()
        self._draw_drone_ids()

        self.gui_camera.use()
        self._draw_hud()

    def _draw_connections(self) -> None:
        """Draw high-contrast graph connections."""
        for connection in self.graph.connections:
            start_x, start_y = self.zone_positions[
                connection.zone_a
            ]
            end_x, end_y = self.zone_positions[
                connection.zone_b
            ]

            # Soft shadow/glow behind the main line.
            arcade.draw_line(
                start_x,
                start_y,
                end_x,
                end_y,
                CONNECTION_GLOW_COLOR,
                10,
            )
            arcade.draw_line(
                start_x,
                start_y,
                end_x,
                end_y,
                CONNECTION_COLOR,
                4,
            )

            label_x = (start_x + end_x) / 2
            label_y = (start_y + end_y) / 2

            arcade.draw_text(
                str(connection.max_capacity),
                label_x,
                label_y + 12,
                CONNECTION_TEXT_COLOR,
                14,
                anchor_x="center",
            )

    def _draw_zones(self) -> None:
        """Draw larger high-resolution zones and labels."""
        for zone in self.graph.zones.values():
            x, y = self.zone_positions[zone.name]
            color = ZONE_COLORS[zone.zone_type]

            if zone.role in {
                ZoneRole.START,
                ZoneRole.END,
            }:
                radius = 42
            else:
                radius = 32

            arcade.draw_circle_filled(
                x + 6,
                y - 7,
                radius + 3,
                ZONE_SHADOW_COLOR,
            )
            arcade.draw_circle_filled(
                x,
                y,
                radius,
                color,
            )
            arcade.draw_circle_outline(
                x,
                y,
                radius,
                ZONE_OUTLINE_COLOR,
                3,
            )

            arcade.draw_text(
                zone.name,
                x,
                y + radius + 14,
                TEXT_COLOR,
                16,
                anchor_x="center",
            )

            if zone.role not in {
                ZoneRole.START,
                ZoneRole.END,
            }:
                arcade.draw_text(
                    f"cap {zone.max_drones}",
                    x,
                    y - radius - 25,
                    CONNECTION_TEXT_COLOR,
                    13,
                    anchor_x="center",
                )

    def _draw_drone_ids(self) -> None:
        """Draw a crisp identifier below every drone."""
        for drone_id, sprite in self.sprites.items():
            arcade.draw_text(
                f"D{drone_id}",
                sprite.center_x,
                sprite.center_y - 23,
                TEXT_COLOR,
                11,
                anchor_x="center",
            )

    def _draw_hud(self) -> None:
        """Draw high-resolution controls and status text."""
        arcade.draw_lrbt_rectangle_filled(
            0,
            self.width,
            0,
            96,
            HUD_BACKGROUND_COLOR,
        )
        arcade.draw_lrbt_rectangle_filled(
            0,
            self.width,
            self.height - 64,
            self.height,
            HUD_BACKGROUND_COLOR,
        )

        shown_turn = min(
            self.turn_index + 1,
            len(self.turns),
        )
        status = "PLAY" if self.playing else "PAUSE"

        arcade.draw_text(
            (
                f"Turn {shown_turn}/{len(self.turns)}"
                f"  |  {status}"
                f"  |  Speed {self.speed:.2f}x"
                f"  |  Zoom {self.world_camera.zoom:.2f}x"
            ),
            28,
            self.height - 44,
            TEXT_COLOR,
            22,
        )

        arcade.draw_text(
            (
                "SPACE Start/Pause   RIGHT Next turn   "
                "R Replay reset   C Camera reset   "
                "UP/DOWN or W/S Speed   X Speed reset"
            ),
            28,
            56,
            TEXT_COLOR,
            16,
        )

        arcade.draw_text(
            (
                "Mouse: hold LEFT and drag to move   "
                "Mouse wheel to zoom   ESC Close"
            ),
            28,
            24,
            CONNECTION_TEXT_COLOR,
            15,
        )

        self._draw_speed_controls()

    def _speed_control_bounds(
        self,
    ) -> dict[str, tuple[float, float, float, float]]:
        """Return GUI-space bounds for the speed buttons."""
        button_width = 58.0
        button_height = 38.0
        gap = 8.0
        bottom = self.height - 51.0

        plus_left = self.width - 24.0 - button_width
        reset_left = plus_left - gap - 92.0
        minus_left = reset_left - gap - button_width

        return {
            "decrease": (
                minus_left,
                bottom,
                button_width,
                button_height,
            ),
            "reset": (
                reset_left,
                bottom,
                92.0,
                button_height,
            ),
            "increase": (
                plus_left,
                bottom,
                button_width,
                button_height,
            ),
        }

    @staticmethod
    def _point_inside(
        x: float,
        y: float,
        bounds: tuple[float, float, float, float],
    ) -> bool:
        """Return whether a point lies inside LBWH bounds."""
        left, bottom, width, height = bounds

        return (
            left <= x <= left + width
            and bottom <= y <= bottom + height
        )

    def _draw_speed_controls(self) -> None:
        """Draw clickable replay-speed controls."""
        bounds = self._speed_control_bounds()
        labels = {
            "decrease": "-",
            "reset": f"{self.speed:.2f}x",
            "increase": "+",
        }

        for name, button_bounds in bounds.items():
            left, bottom, width, height = button_bounds

            arcade.draw_lbwh_rectangle_filled(
                left,
                bottom,
                width,
                height,
                CONTROL_BACKGROUND_COLOR,
            )
            arcade.draw_lbwh_rectangle_outline(
                left,
                bottom,
                width,
                height,
                CONTROL_OUTLINE_COLOR,
                2,
            )
            arcade.draw_text(
                labels[name],
                left + width / 2,
                bottom + height / 2,
                TEXT_COLOR,
                16,
                anchor_x="center",
                anchor_y="center",
            )

    def _increase_speed(self) -> None:
        """Increase replay speed by one step."""
        self.speed = min(
            MAX_SPEED,
            round(self.speed + SPEED_STEP, 2),
        )

    def _decrease_speed(self) -> None:
        """Decrease replay speed by one step."""
        self.speed = max(
            MIN_SPEED,
            round(self.speed - SPEED_STEP, 2),
        )

    def _reset_speed(self) -> None:
        """Reset replay speed to its default value."""
        self.speed = DEFAULT_SPEED

    def on_key_press(
        self,
        symbol: int,
        modifiers: int,
    ) -> None:
        """Handle replay and camera controls."""
        del modifiers

        if symbol == arcade.key.SPACE:
            self.playing = not self.playing

        elif symbol == arcade.key.RIGHT:
            self._finish_turn()

        elif symbol == arcade.key.R:
            self._reset_replay()

        elif symbol in {
            arcade.key.C,
            arcade.key.HOME,
        }:
            self._reset_camera()

        elif symbol in {
            arcade.key.UP,
            arcade.key.W,
        }:
            self._increase_speed()

        elif symbol in {
            arcade.key.DOWN,
            arcade.key.S,
        }:
            self._decrease_speed()

        elif symbol == arcade.key.X:
            self._reset_speed()

        elif symbol == arcade.key.ESCAPE:
            self.close()

    def on_text(self, text: str) -> None:
        """Handle layout-independent plus and minus characters."""
        if text == "+":
            self._increase_speed()
        elif text == "-":
            self._decrease_speed()

    def on_mouse_press(
        self,
        x: int,
        y: int,
        button: int,
        modifiers: int,
    ) -> None:
        """Handle clicks on the speed controls."""
        del modifiers

        if button != arcade.MOUSE_BUTTON_LEFT:
            return

        bounds = self._speed_control_bounds()

        if self._point_inside(x, y, bounds["decrease"]):
            self._decrease_speed()
        elif self._point_inside(x, y, bounds["reset"]):
            self._reset_speed()
        elif self._point_inside(x, y, bounds["increase"]):
            self._increase_speed()

    def on_mouse_drag(
        self,
        x: int,
        y: int,
        dx: int,
        dy: int,
        buttons: int,
        modifiers: int,
    ) -> None:
        """Pan the world while the left mouse button is held."""
        del x, y, modifiers

        if not buttons & arcade.MOUSE_BUTTON_LEFT:
            return

        camera_x, camera_y = self.world_camera.position
        zoom = self.world_camera.zoom

        self.world_camera.position = (
            camera_x - dx / zoom,
            camera_y - dy / zoom,
        )

    def on_mouse_scroll(
        self,
        x: int,
        y: int,
        scroll_x: float,
        scroll_y: float,
    ) -> None:
        """Zoom toward the current mouse position."""
        del scroll_x

        if scroll_y == 0:
            return

        before_x, before_y, _ = self.world_camera.unproject(
            (x, y)
        )

        requested_zoom = (
            self.world_camera.zoom
            * (ZOOM_STEP ** scroll_y)
        )
        new_zoom = max(
            MIN_ZOOM,
            min(MAX_ZOOM, requested_zoom),
        )

        if new_zoom == self.world_camera.zoom:
            return

        self.world_camera.zoom = new_zoom

        after_x, after_y, _ = self.world_camera.unproject(
            (x, y)
        )
        camera_x, camera_y = self.world_camera.position

        self.world_camera.position = (
            camera_x + before_x - after_x,
            camera_y + before_y - after_y,
        )

    def on_resize(
        self,
        width: int,
        height: int,
    ) -> None:
        """Update both camera viewports after resizing."""
        del width, height

        self.world_camera.match_window(
            position=False,
        )
        self.gui_camera.match_window(
            position=True,
        )


def run_visualization(result: SimulationResult) -> None:
    """Open the Arcade replay window."""
    ReplayWindow(result)
    arcade.run()
