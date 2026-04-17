#import library
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path       

import pygame
#define game values, rule
SCREEN_WIDTH, SCREEN_HEIGHT = 900, 700
FPS = 60
WINDOW_TITLE = "Dont Touch The Button"

BACKGROUND_COLOR = (18, 18, 24)
BUTTON_COLOR = (235, 70, 70)
BUTTON_OUTLINE_COLOR = (255, 210, 210)
SHIELD_COLOR = (70, 170, 255)
NORMAL_NOTE_COLOR = (255, 225, 90)
HOLD_NOTE_COLOR = (80, 230, 255)
FAKE_NOTE_COLOR = (255, 60, 60)
TEXT_COLOR = (245, 245, 245)
GAME_OVER_COLOR = (255, 90, 90)
PERFECT_COLOR = (110, 255, 140)
GOOD_COLOR = (255, 220, 100)

BUTTON_RADIUS = 34.0
SHIELD_RADIUS = 30.0
SHIELD_ORBIT_DISTANCE = 90.0
NOTE_RADIUS = 22.0
PERFECT_WINDOW = 14.0
GOOD_WINDOW = 30.0
HOLD_NOTE_DURATION = 0.9

INITIAL_SPAWN_INTERVAL = 0.75
MIN_SPAWN_INTERVAL = 0.28

DIFFICULTY_INTERVAL = 12.0
MAX_DIFFICULTY_LEVEL = 6
SONG_BPM = 125
BEATS_PER_SPAWN = 0.7
BASE_TRAVEL_BEATS = 2.5
FAKE_NOTE_SPAWN_CHANCE = 0.3
BASE_DIR = Path(__file__).resolve().parent
ASSET_DIR = BASE_DIR / "assets"
MUSIC_PATH = ASSET_DIR / "music" / "game.ogg"
MENU_UI_PATH = ASSET_DIR / "ui" / "menu_ui.png"
GAME_BG_PATH = ASSET_DIR / "ui" / "game_bg.png"

# add enums for direction, note types, hit results, and game states

class Direction(Enum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()


class NoteType(Enum):
    NORMAL = auto()
    HOLD = auto()
    FAKE = auto()


class HitResult(Enum):
    PERFECT = auto()
    GOOD = auto()
    BLOCKED = auto()
    HOLD_START = auto()
    HOLD_SUCCESS = auto()
    HOLD_FAIL = auto()
    FAKE_BLOCK = auto()
    BUTTON_HIT = auto()
    NONE = auto()


class GameState(Enum):
    MENU = auto()
    PLAYING = auto()
    GAME_OVER = auto()
# implement Vector2 utility class for position and distance calculation
# implement CircleHitbox for collision detection

@dataclass(frozen=True)
class Vector2:
    x: float
    y: float

    def distance_to(self, other: "Vector2") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def to_int_tuple(self) -> tuple[int, int]:
        return int(self.x), int(self.y)


@dataclass
class CircleHitbox:
    center: Vector2
    radius: float

    def overlaps(self, other: "CircleHitbox") -> bool:
        return self.center.distance_to(other.center) <= self.radius + other.radius
# create Button and Shield classes with hitbox and positioning logic
@dataclass
class Button:
    center: Vector2
    radius: float = BUTTON_RADIUS

    @property
    def hitbox(self) -> CircleHitbox:
        return CircleHitbox(self.center, self.radius)


@dataclass
class Shield:
    center: Vector2
    orbit_distance: float = SHIELD_ORBIT_DISTANCE
    radius: float = SHIELD_RADIUS
    direction: Direction = Direction.UP

    def set_direction(self, direction: Direction) -> None:
        self.direction = direction

    @property
    def position(self) -> Vector2:
        offsets = {
            Direction.UP: (0, -self.orbit_distance),
            Direction.DOWN: (0, self.orbit_distance),
            Direction.LEFT: (-self.orbit_distance, 0),
            Direction.RIGHT: (self.orbit_distance, 0),
        }
        dx, dy = offsets[self.direction]
        return Vector2(self.center.x + dx, self.center.y + dy)

    @property
    def hitbox(self) -> CircleHitbox:
        return CircleHitbox(self.position, self.radius)
# implement ArrowNote class with movement, hold mechanics, and hitbox
@dataclass
class ArrowNote:
    direction: Direction
    position: Vector2
    note_type: NoteType = NoteType.NORMAL
    speed: float = 0.0
    radius: float = NOTE_RADIUS
    is_active: bool = True
    hold_duration: float = 0.0
    hold_progress: float = 0.0
    is_being_held: bool = False

    def update(self, dt: float) -> None:
        if not self.is_active or (self.note_type == NoteType.HOLD and self.is_being_held):
            return
        moves = {
            Direction.UP: (0, self.speed * dt),
            Direction.DOWN: (0, -self.speed * dt),
            Direction.LEFT: (self.speed * dt, 0),
            Direction.RIGHT: (-self.speed * dt, 0),
        }
        dx, dy = moves[self.direction]
        self.position = Vector2(self.position.x + dx, self.position.y + dy)

    @property
    def hitbox(self) -> CircleHitbox:
        return CircleHitbox(self.position, self.radius)

# add ScoreManager to track score, combo, and performance stats
@dataclass
class ScoreManager:
    score: int = 0
    combo: int = 0
    max_combo: int = 0
    perfect_count: int = 0
    good_count: int = 0
    blocked_count: int = 0
    hold_success_count: int = 0
    fake_penalty_count: int = 0
    miss_count: int = 0

    def register_result(self, result: HitResult) -> None:
        if result == HitResult.PERFECT:
            self.score += 100
            self.combo += 1
            self.perfect_count += 1
        elif result == HitResult.GOOD:
            self.score += 60
            self.combo += 1
            self.good_count += 1
        elif result == HitResult.BLOCKED:
            self.score += 30
            self.combo += 1
            self.blocked_count += 1
        elif result == HitResult.HOLD_START:
            self.score += 20
        elif result == HitResult.HOLD_SUCCESS:
            self.score += 150
            self.combo += 1
            self.hold_success_count += 1
        elif result == HitResult.HOLD_FAIL:
            self.combo = 0
            self.miss_count += 1
        elif result == HitResult.FAKE_BLOCK:
            self.score = max(0, self.score - 80)
            self.combo = 0
            self.fake_penalty_count += 1
        elif result == HitResult.BUTTON_HIT:
            self.combo = 0
            self.miss_count += 1
        self.max_combo = max(self.max_combo, self.combo)

# implement HitJudge system for normal, hold, and fake note logic
class HitJudge:
    def __init__(self, perfect_window: float = PERFECT_WINDOW, good_window: float = GOOD_WINDOW) -> None:
        self.perfect_window = perfect_window
        self.good_window = good_window

    def judge(self, note: ArrowNote, shield: Shield, button: Button, dt: float) -> HitResult:
        if not note.is_active:
            return HitResult.NONE
        if note.note_type == NoteType.HOLD:
            return self._judge_hold(note, shield, button, dt)
        if note.note_type == NoteType.FAKE:
            return self._judge_fake(note, shield, button)
        return self._judge_normal(note, shield, button)

    def _judge_normal(self, note: ArrowNote, shield: Shield, button: Button) -> HitResult:
        if note.direction == shield.direction and note.hitbox.overlaps(shield.hitbox):
            note.is_active = False
            dist = note.position.distance_to(shield.position)
            if dist <= self.perfect_window:
                return HitResult.PERFECT
            if dist <= self.good_window:
                return HitResult.GOOD
            return HitResult.BLOCKED
        if note.hitbox.overlaps(button.hitbox):
            note.is_active = False
            return HitResult.BUTTON_HIT
        return HitResult.NONE

    def _judge_hold(self, note: ArrowNote, shield: Shield, button: Button, dt: float) -> HitResult:
        if not note.is_being_held:
            if note.direction == shield.direction and note.hitbox.overlaps(shield.hitbox):
                note.is_being_held = True
                note.hold_progress = 0.0
                return HitResult.HOLD_START
            if note.hitbox.overlaps(button.hitbox):
                note.is_active = False
                return HitResult.BUTTON_HIT
            return HitResult.NONE
        if shield.direction != note.direction:
            note.is_active = False
            note.is_being_held = False
            return HitResult.HOLD_FAIL
        note.hold_progress += dt
        if note.hold_progress >= note.hold_duration:
            note.is_active = False
            note.is_being_held = False
            return HitResult.HOLD_SUCCESS
        return HitResult.NONE

    def _judge_fake(self, note: ArrowNote, shield: Shield, button: Button) -> HitResult:
        if note.direction == shield.direction and note.hitbox.overlaps(shield.hitbox):
            note.is_active = False
            return HitResult.FAKE_BLOCK
        if note.hitbox.overlaps(button.hitbox):
            note.is_active = False
        return HitResult.NONE

# implement BeatSpawner with patterns, randomness, and difficulty scaling
class BeatSpawner:
    def __init__(self) -> None:
        self.timer = 0.0
        self.beat_interval = 60.0 / SONG_BPM
        self.spawn_interval = self.beat_interval * BEATS_PER_SPAWN
        self.patterns = [
            [
                (Direction.UP, NoteType.NORMAL),
                (Direction.LEFT, NoteType.NORMAL),
                (Direction.DOWN, NoteType.HOLD),
                (Direction.RIGHT, NoteType.NORMAL),
                (Direction.UP, NoteType.FAKE),
            ],
            [
                (Direction.RIGHT, NoteType.NORMAL),
                (Direction.DOWN, NoteType.NORMAL),
                (Direction.LEFT, NoteType.FAKE),
                (Direction.UP, NoteType.NORMAL),
                (Direction.RIGHT, NoteType.HOLD),
            ],
            [
                (Direction.LEFT, NoteType.NORMAL),
                (Direction.UP, NoteType.NORMAL),
                (Direction.RIGHT, NoteType.NORMAL),
                (Direction.DOWN, NoteType.FAKE),
                (Direction.LEFT, NoteType.HOLD),
            ],
            [
                (Direction.DOWN, NoteType.NORMAL),
                (Direction.RIGHT, NoteType.FAKE),
                (Direction.UP, NoteType.NORMAL),
                (Direction.LEFT, NoteType.NORMAL),
                (Direction.DOWN, NoteType.HOLD),
            ],
            [
                (Direction.UP, NoteType.NORMAL),
                (Direction.RIGHT, NoteType.NORMAL),
                (Direction.DOWN, NoteType.NORMAL),
                (Direction.LEFT, NoteType.NORMAL),
                (Direction.UP, NoteType.FAKE),
            ],
            [
                (Direction.LEFT, NoteType.FAKE),
                (Direction.DOWN, NoteType.NORMAL),
                (Direction.UP, NoteType.HOLD),
                (Direction.RIGHT, NoteType.NORMAL),
                (Direction.LEFT, NoteType.NORMAL),
            ],
        ]
        self.fake_pattern = [Direction.UP, Direction.RIGHT, Direction.LEFT, Direction.DOWN]
        self.current_pattern = random.choice(self.patterns)
        self.pattern_index = 0
        self.fake_pattern_index = 0
        self.last_direction: Direction | None = None
        self.same_direction_count = 0

    def reset(self) -> None:
        self.timer = 0.0
        self.beat_interval = 60.0 / SONG_BPM
        self.spawn_interval = self.beat_interval * BEATS_PER_SPAWN
        self.current_pattern = random.choice(self.patterns)
        self.pattern_index = 0
        self.fake_pattern_index = 0
        self.last_direction = None
        self.same_direction_count = 0

    def _pick_new_pattern(self) -> None:
        candidates = [p for p in self.patterns if p is not self.current_pattern]
        self.current_pattern = random.choice(candidates or self.patterns)
        self.pattern_index = 0

    def _prevent_repetitive_direction(self, note_data: tuple[Direction, NoteType]) -> tuple[Direction, NoteType]:
        direction, note_type = note_data
        self.same_direction_count = self.same_direction_count + 1 if self.last_direction == direction else 1
        if self.same_direction_count >= 3:
            alternatives = [d for d in Direction if d != direction]
            direction = random.choice(alternatives)
            self.same_direction_count = 1
        self.last_direction = direction
        return direction, note_type

    def update(
        self,
        dt: float,
        hold_note_active: bool = False,
        difficulty_level: int = 0,
        blocked_fake_directions: set[Direction] | None = None,
    ) -> list[tuple[Direction, NoteType]]:
        self.timer += dt
        factor = min(difficulty_level, MAX_DIFFICULTY_LEVEL)
        beat_multiplier = 1.0 if factor <= 1 else 0.5 if factor <= 3 else 0.25
        self.beat_interval = 60.0 / SONG_BPM
        self.spawn_interval = max(MIN_SPAWN_INTERVAL, self.beat_interval * BEATS_PER_SPAWN * beat_multiplier)
        blocked_fake_directions = blocked_fake_directions or set()
        spawned: list[tuple[Direction, NoteType]] = []

        while self.timer >= self.spawn_interval:
            self.timer -= self.spawn_interval

            if hold_note_active:
                if self.fake_pattern_index % 2 == 0:
                    allowed = [d for d in self.fake_pattern if d not in blocked_fake_directions]
                    if allowed and random.random() < FAKE_NOTE_SPAWN_CHANCE:
                        spawned.append((random.choice(allowed), NoteType.FAKE))
                self.fake_pattern_index += 1
                continue

            if self.pattern_index >= len(self.current_pattern):
                self._pick_new_pattern()

            note_data = self._prevent_repetitive_direction(self.current_pattern[self.pattern_index])
            self.pattern_index += 1

            if note_data[1] == NoteType.FAKE and random.random() >= FAKE_NOTE_SPAWN_CHANCE:
                continue

            spawned.append(note_data)

        return spawned

# create main game class DontTouchTheButtonGame with initialization
class DontTouchTheButtonGame:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(WINDOW_TITLE)
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()

        self.title_font = pygame.font.SysFont("arial", 42, bold=True)
        self.ui_font = pygame.font.SysFont("arial", 28)
        self.small_font = pygame.font.SysFont("arial", 22)

        self.center = Vector2(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
        self.button = Button(self.center)
        self.shield = Shield(self.center)
        self.score_manager = ScoreManager()
        self.hit_judge = HitJudge()
        self.spawner = BeatSpawner()
        self.notes: list[ArrowNote] = []

        self.state = GameState.MENU
        self.is_running = True
        self.last_result_text = ""
        self.last_result_color = TEXT_COLOR
        self.last_result_timer = 0.0
        self.survival_time = 0.0
        self.difficulty_level = 0

        self._try_load_music()
        self.menu_ui_image = self._load_scaled_image(MENU_UI_PATH)
        self.game_bg_image = self._load_scaled_image(GAME_BG_PATH)

# add asset loading system for images and music
    def _load_scaled_image(self, path: Path) -> pygame.Surface | None:
        if not path.exists():
            return None
        try:
            return pygame.transform.smoothscale(
                pygame.image.load(str(path)).convert_alpha(),
                (SCREEN_WIDTH, SCREEN_HEIGHT),
            )
        except pygame.error:
            return None

    def _try_load_music(self) -> None:
        if MUSIC_PATH.exists():
            try:
                pygame.mixer.init()
                pygame.mixer.music.load(str(MUSIC_PATH))
            except pygame.error:
                pass
# implement music control (load, play, stop)
    def _start_music(self) -> None:
        if pygame.mixer.get_init():
            try:
                pygame.mixer.music.play(-1)
            except pygame.error:
                pass

    def _stop_music(self) -> None:
        if pygame.mixer.get_init():
            try:
                pygame.mixer.music.stop()
            except pygame.error:
                pass
# implement game reset and state management system
    def reset_game(self) -> None:
        self.notes.clear()
        self.score_manager = ScoreManager()
        self.hit_judge = HitJudge()
        self.spawner.reset()
        self.shield = Shield(self.center)
        self.last_result_text = ""
        self.last_result_color = TEXT_COLOR
        self.last_result_timer = 0.0
        self.survival_time = 0.0
        self.difficulty_level = 0
        self.state = GameState.PLAYING
        self._start_music()
# implement note creation with dynamic speed and travel calculation
    def create_note(self, direction: Direction, note_type: NoteType) -> ArrowNote:
        margin = 60.0
        if direction == Direction.UP:
            position = Vector2(self.center.x, -margin)
            travel_distance = (self.center.y - SHIELD_ORBIT_DISTANCE) - position.y
        elif direction == Direction.DOWN:
            position = Vector2(self.center.x, SCREEN_HEIGHT + margin)
            travel_distance = position.y - (self.center.y + SHIELD_ORBIT_DISTANCE)
        elif direction == Direction.LEFT:
            position = Vector2(-margin, self.center.y)
            travel_distance = (self.center.x - SHIELD_ORBIT_DISTANCE) - position.x
        else:
            position = Vector2(SCREEN_WIDTH + margin, self.center.y)
            travel_distance = position.x - (self.center.x + SHIELD_ORBIT_DISTANCE)

        beat_duration = 60.0 / SONG_BPM
        travel_beats = BASE_TRAVEL_BEATS if self.difficulty_level <= 1 else max(2.5, BASE_TRAVEL_BEATS - 0.75) if self.difficulty_level <= 3 else max(2.0, BASE_TRAVEL_BEATS - 1.25)
        note_speed = max(120.0, travel_distance / (beat_duration * travel_beats))
        hold_duration = HOLD_NOTE_DURATION if note_type == NoteType.HOLD else 0.0

        return ArrowNote(direction, position, note_type, note_speed, hold_duration=hold_duration)

    def spawn_note(self, direction: Direction, note_type: NoteType) -> None:
        self.notes.append(self.create_note(direction, note_type))

    def _has_active_hold_note(self) -> bool:
        return any(note.is_active and note.note_type == NoteType.HOLD for note in self.notes)

    def _get_active_hold_directions(self) -> set[Direction]:
        return {note.direction for note in self.notes if note.is_active and note.note_type == NoteType.HOLD}
# implement event handling for menu, gameplay, and game over states
    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_running = False
            elif event.type == pygame.KEYDOWN:
                if self.state == GameState.MENU and event.key == pygame.K_SPACE:
                    self.reset_game()
                elif self.state == GameState.PLAYING:
                    key_map = {
                        pygame.K_UP: Direction.UP,
                        pygame.K_DOWN: Direction.DOWN,
                        pygame.K_LEFT: Direction.LEFT,
                        pygame.K_RIGHT: Direction.RIGHT,
                    }
                    if event.key in key_map:
                        self.shield.set_direction(key_map[event.key])
                elif self.state == GameState.GAME_OVER:
                    if event.key == pygame.K_r:
                        self.reset_game()
                    elif event.key == pygame.K_ESCAPE:
                        self.state = GameState.MENU
                        self._stop_music()
# implement main update loop including difficulty scaling and spawning
    def update(self, dt: float) -> None:
        if self.state != GameState.PLAYING:
            return

        self.survival_time += dt
        self.difficulty_level = min(int(self.survival_time // DIFFICULTY_INTERVAL), MAX_DIFFICULTY_LEVEL)

        if self.last_result_timer > 0:
            self.last_result_timer -= dt
            if self.last_result_timer <= 0:
                self.last_result_text = ""

        for note in self.notes:
            note.update(dt)
            result = self.hit_judge.judge(note, self.shield, self.button, dt)
            if result != HitResult.NONE:
                self.score_manager.register_result(result)
                self._set_feedback_text(result)
            if result == HitResult.BUTTON_HIT:
                self.state = GameState.GAME_OVER
                self._stop_music()

        self.notes = [note for note in self.notes if note.is_active]

        for direction, note_type in self.spawner.update(
            dt,
            hold_note_active=self._has_active_hold_note(),
            difficulty_level=self.difficulty_level,
            blocked_fake_directions=self._get_active_hold_directions(),
        ):
            self.spawn_note(direction, note_type)
# implement hit feedback system with visual text indicators
    def _set_feedback_text(self, result: HitResult) -> None:
        texts = {
            HitResult.PERFECT: ("PERFECT", PERFECT_COLOR),
            HitResult.GOOD: ("GOOD", GOOD_COLOR),
            HitResult.BLOCKED: ("BLOCK", TEXT_COLOR),
            HitResult.HOLD_START: ("HOLD", HOLD_NOTE_COLOR),
            HitResult.HOLD_SUCCESS: ("HOLD OK", PERFECT_COLOR),
            HitResult.HOLD_FAIL: ("HOLD FAIL", GAME_OVER_COLOR),
            HitResult.FAKE_BLOCK: ("FAKE!", FAKE_NOTE_COLOR),
            HitResult.BUTTON_HIT: ("MISS", GAME_OVER_COLOR),
        }
        self.last_result_text, self.last_result_color = texts.get(result, ("", TEXT_COLOR))
        self.last_result_timer = 0.45
# implement drawing functions for arrows, fake notes, and shield
    def _draw_fnf_arrow(
        self,
        cx: int,
        cy: int,
        direction: Direction,
        size: int,
        color: tuple[int, int, int],
        outline_color: tuple[int, int, int] = (255, 255, 255),
        outline_width: int = 3,
    ) -> None:
        head = size
        neck = int(size * 0.48)
        stem_len = int(size * 1.25)
        half_stem = int(size * 0.42)

        if direction == Direction.UP:
            points = [(cx, cy + head * 1.45), (cx - head, cy + neck), (cx - half_stem, cy + neck), (cx - half_stem, cy - stem_len), (cx + half_stem, cy - stem_len), (cx + half_stem, cy + neck), (cx + head, cy + neck)]
        elif direction == Direction.DOWN:
            points = [(cx, cy - head * 1.45), (cx - head, cy - neck), (cx - half_stem, cy - neck), (cx - half_stem, cy + stem_len), (cx + half_stem, cy + stem_len), (cx + half_stem, cy - neck), (cx + head, cy - neck)]
        elif direction == Direction.LEFT:
            points = [(cx + head * 1.45, cy), (cx + neck, cy - head), (cx + neck, cy - half_stem), (cx - stem_len, cy - half_stem), (cx - stem_len, cy + half_stem), (cx + neck, cy + half_stem), (cx + neck, cy + head)]
        else:
            points = [(cx - head * 1.45, cy), (cx - neck, cy - head), (cx - neck, cy - half_stem), (cx + stem_len, cy - half_stem), (cx + stem_len, cy + half_stem), (cx - neck, cy + half_stem), (cx - neck, cy + head)]

        pygame.draw.polygon(self.screen, color, points)
        pygame.draw.polygon(self.screen, outline_color, points, width=outline_width)
        shine = tuple(min(255, c + 28) for c in color)
        inner = [(cx + int((px - cx) * 0.8), cy + int((py - cy) * 0.8)) for px, py in points]
        pygame.draw.polygon(self.screen, shine, inner)

    def _draw_fake_x(self, cx: int, cy: int, size: int, color: tuple[int, int, int]) -> None:
        pygame.draw.line(self.screen, color, (cx - size, cy - size), (cx + size, cy + size), 10)
        pygame.draw.line(self.screen, color, (cx - size, cy + size), (cx + size, cy - size), 10)
        pygame.draw.line(self.screen, (255, 220, 220), (cx - size + 2, cy - size + 2), (cx + size - 2, cy + size - 2), 4)
        pygame.draw.line(self.screen, (255, 220, 220), (cx - size + 2, cy + size - 2), (cx + size - 2, cy - size + 2), 4)

    def _draw_shield_piece(self, cx: int, cy: int, direction: Direction, color: tuple[int, int, int]) -> None:
        long_half, short_half, thickness = 34, 8, 12
        if direction == Direction.UP:
            points = [(cx - long_half, cy - short_half), (cx - long_half + 10, cy - short_half - thickness), (cx + long_half - 10, cy - short_half - thickness), (cx + long_half, cy - short_half), (cx + long_half - 10, cy + short_half), (cx - long_half + 10, cy + short_half)]
        elif direction == Direction.DOWN:
            points = [(cx - long_half, cy + short_half), (cx - long_half + 10, cy + short_half + thickness), (cx + long_half - 10, cy + short_half + thickness), (cx + long_half, cy + short_half), (cx + long_half - 10, cy - short_half), (cx - long_half + 10, cy - short_half)]
        elif direction == Direction.LEFT:
            points = [(cx - short_half, cy - long_half), (cx - short_half - thickness, cy - long_half + 10), (cx - short_half - thickness, cy + long_half - 10), (cx - short_half, cy + long_half), (cx + short_half, cy + long_half - 10), (cx + short_half, cy - long_half + 10)]
        else:
            points = [(cx + short_half, cy - long_half), (cx + short_half + thickness, cy - long_half + 10), (cx + short_half + thickness, cy + long_half - 10), (cx + short_half, cy + long_half), (cx - short_half, cy + long_half - 10), (cx - short_half, cy - long_half + 10)]

        pygame.draw.polygon(self.screen, color, points)
        pygame.draw.polygon(self.screen, (235, 245, 255), points, width=3)
        inner = [(cx + int((px - cx) * 0.78), cy + int((py - cy) * 0.78)) for px, py in points]
        pygame.draw.polygon(self.screen, (120, 210, 255), inner)
# implement rendering system for menu, gameplay, and game over screens
    def draw(self) -> None:
        if self.state == GameState.MENU and self.menu_ui_image is not None:
            self.screen.blit(self.menu_ui_image, (0, 0))
        elif self.state in (GameState.PLAYING, GameState.GAME_OVER) and self.game_bg_image is not None:
            self.screen.blit(self.game_bg_image, (0, 0))
        else:
            self.screen.fill(BACKGROUND_COLOR)

        if self.state == GameState.PLAYING:
            self._draw_playing()
        elif self.state == GameState.GAME_OVER:
            self._draw_playing()
            self._draw_game_over()

        pygame.display.flip()

    def _draw_playing(self) -> None:
        pygame.draw.circle(self.screen, (55, 55, 75), self.center.to_int_tuple(), int(SHIELD_ORBIT_DISTANCE), width=2)
        self._draw_button()
        self._draw_shield()
        self._draw_notes()
        self._draw_hud()

    def _draw_game_over(self) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 155))
        self.screen.blit(overlay, (0, 0))
        self._draw_centered_text("GAME OVER", self.title_font, GAME_OVER_COLOR, 220)
        self._draw_centered_text(f"Final Score: {self.score_manager.score}", self.ui_font, TEXT_COLOR, 300)
        self._draw_centered_text(f"Max Combo: {self.score_manager.max_combo}", self.ui_font, TEXT_COLOR, 340)
        self._draw_centered_text("Press R to retry or ESC for menu", self.ui_font, TEXT_COLOR, 420)

    def _draw_button(self) -> None:
        center = self.button.center.to_int_tuple()
        pygame.draw.circle(self.screen, BUTTON_COLOR, center, int(self.button.radius))
        pygame.draw.circle(self.screen, BUTTON_OUTLINE_COLOR, center, int(self.button.radius), width=4)
        pygame.draw.circle(self.screen, (255, 235, 235), center, int(self.button.radius * 0.42))

    def _draw_shield(self) -> None:
        p = self.shield.position
        self._draw_shield_piece(int(p.x), int(p.y), self.shield.direction, SHIELD_COLOR)

    def _draw_notes(self) -> None:
        for note in self.notes:
            x, y = int(note.position.x), int(note.position.y)
            if note.note_type == NoteType.FAKE:
                self._draw_fake_x(x, y, 16, FAKE_NOTE_COLOR)
                continue

            self._draw_fnf_arrow(x, y, note.direction, 18, NORMAL_NOTE_COLOR if note.note_type == NoteType.NORMAL else HOLD_NOTE_COLOR)

            if note.note_type == NoteType.HOLD:
                ratio = min(1.0, note.hold_progress / note.hold_duration) if note.hold_duration > 0 else 0.0
                bar_x, bar_y = int(note.position.x - 23), int(note.position.y + 28)
                pygame.draw.rect(self.screen, (55, 55, 75), (bar_x, bar_y, 46, 7), border_radius=3)
                pygame.draw.rect(self.screen, HOLD_NOTE_COLOR, (bar_x, bar_y, int(46 * ratio), 7), border_radius=3)
# implement HUD displaying score, combo, stats, and time
    def _draw_hud(self) -> None:
        items = [
            (self.ui_font, f"Score: {self.score_manager.score}", TEXT_COLOR, (24, 20)),
            (self.ui_font, f"Combo: {self.score_manager.combo}", SHIELD_COLOR, (24, 56)),
            (self.small_font, f"Perfect: {self.score_manager.perfect_count}", PERFECT_COLOR, (24, 104)),
            (self.small_font, f"Good: {self.score_manager.good_count}", GOOD_COLOR, (24, 134)),
            (self.small_font, f"Hold OK: {self.score_manager.hold_success_count}", HOLD_NOTE_COLOR, (24, 164)),
            (self.small_font, f"Fake Penalty: {self.score_manager.fake_penalty_count}", FAKE_NOTE_COLOR, (24, 194)),
            (self.small_font, f"Difficulty Level: {self.difficulty_level}", GOOD_COLOR, (24, 224)),
            (self.small_font, f"Time: {self.survival_time:.1f}s", TEXT_COLOR, (24, 254)),
        ]
        for font, text, color, pos in items:
            self.screen.blit(font.render(text, True, color), pos)

        if self.last_result_text:
            surf = self.title_font.render(self.last_result_text, True, self.last_result_color)
            self.screen.blit(surf, surf.get_rect(center=(SCREEN_WIDTH // 2, 95)))

    def _draw_centered_text(self, text: str, font: pygame.font.Font, color: tuple[int, int, int], y: int) -> None:
        surf = font.render(text, True, color)
        self.screen.blit(surf, surf.get_rect(center=(SCREEN_WIDTH // 2, y)))
# implement game loop with FPS control and rendering cycle
    def run(self) -> None:
        while self.is_running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
        self._stop_music()
        pygame.quit()

# add main entry point to run the game
def main() -> None:
    DontTouchTheButtonGame().run()


if __name__ == "__main__":
    main()