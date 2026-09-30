import pygame
import random

from .beat import (
    Note,
    LANES,
    LANE_KEYS,
    LANE_LABELS,
    LANE_COLORS
)


# =========================================================
# GAME SETTINGS
# =========================================================

WIDTH = 480
HEIGHT = 640
FPS = 60

HIT_Y = HEIGHT - 80
HIT_WINDOW = 30

# =========================================================
# BPM SETTINGS
# =========================================================

# Slower BPM so the game is easier to play
BPM = 80

# 60000 ms = 1 minute
# 60000 / 80 = 750 ms between beats
BEAT_INTERVAL_MS = 60000 / BPM


# =========================================================
# HOLD NOTE SETTINGS
# =========================================================

# Around 20% of notes will be hold notes
HOLD_CHANCE = 0.20

# Player must hold the key for 1 second
HOLD_DURATION_MS = 1000


# =========================================================
# GAME OVER
# =========================================================

MAX_MISSES = 15


class GameEngine:

    def __init__(self):

        pygame.init()

        # Initialize audio
        try:
            pygame.mixer.init()
        except pygame.error:
            pass

        # Create game window
        self.screen = pygame.display.set_mode(
            (WIDTH, HEIGHT)
        )

        pygame.display.set_caption(
            "Rhythm Tap"
        )

        self.clock = pygame.time.Clock()

        # =================================================
        # FONTS
        # =================================================

        self.font = pygame.font.Font(
            None,
            32
        )

        self.small_font = pygame.font.Font(
            None,
            24
        )

        self.big_font = pygame.font.Font(
            None,
            52
        )

        # =================================================
        # SOUND EFFECTS
        # =================================================

        self.sounds = {}

        try:

            self.sounds["PERFECT"] = pygame.mixer.Sound(
                "assets/perfect.wav"
            )

            self.sounds["GREAT"] = pygame.mixer.Sound(
                "assets/great.wav"
            )

            self.sounds["OK"] = pygame.mixer.Sound(
                "assets/ok.wav"
            )

        except pygame.error:

            print(
                "Warning: Could not load sound effects."
            )

        # Start game
        self.reset()


    # =========================================================
    # RESET GAME
    # =========================================================

    def reset(self):

        # Notes currently on screen
        self.notes = []

        # Score
        self.score = 0

        # Current combo
        self.combo = 0

        # Highest combo
        self.max_combo = 0

        # Misses used for game-over
        self.misses = 0

        # =====================================================
        # GRADE COUNTERS
        # =====================================================

        self.perfect_count = 0
        self.great_count = 0
        self.ok_count = 0

        # Separate grade MISS counter
        self.grade_miss_count = 0

        # =====================================================
        # BPM TIMER
        # =====================================================

        current_time = pygame.time.get_ticks()

        # First note appears after one beat
        self.next_beat_time = (
            current_time + BEAT_INTERVAL_MS
        )

        # Note movement speed
        self.speed = 5

        self.frame = 0

        # Feedback shown on screen
        self.feedback = ""

        self.feedback_timer = 0

        # Game-over state
        self.game_over = False


    # =========================================================
    # PLAY SOUND
    # =========================================================

    def play_grade_sound(self, grade):

        sound = self.sounds.get(
            grade
        )

        if sound:

            sound.play()


    # =========================================================
    # SPAWN NOTE
    # =========================================================

    def spawn_note(self):

        # Random lane
        lane = random.randrange(
            LANES
        )

        # Decide if note is hold note
        is_hold = (
            random.random()
            < HOLD_CHANCE
        )

        # Create note
        note = Note(
            lane=lane,
            y=-30,
            speed=self.speed
        )

        # Set hold status
        note.is_hold = is_hold

        if is_hold:

            note.hold_duration = (
                HOLD_DURATION_MS
            )

        # Add note to game
        self.notes.append(
            note
        )


    # =========================================================
    # HANDLE EVENTS
    # =========================================================

    def handle_events(self):

        for event in pygame.event.get():

            # Close window
            if event.type == pygame.QUIT:

                return False


            if event.type == pygame.KEYDOWN:

                # -----------------------------------------
                # RESTART
                # -----------------------------------------

                if event.key == pygame.K_r:

                    if self.game_over:

                        self.reset()

                    continue


                # -----------------------------------------
                # LANE KEY
                # -----------------------------------------

                if event.key in LANE_KEYS:

                    lane = LANE_KEYS.index(
                        event.key
                    )

                    self.process_tap(
                        lane
                    )

        return True


    # =========================================================
    # PROCESS TAP
    # =========================================================

    def process_tap(self, lane):

        # Don't accept input after game over
        if self.game_over:

            return

        best_note = None

        best_distance = float(
            "inf"
        )

        # Find closest note in selected lane
        for note in self.notes:

            if note.hit or note.missed:

                continue

            if note.lane != lane:

                continue

            distance = abs(
                note.y - HIT_Y
            )

            if distance < best_distance:

                best_distance = distance

                best_note = note


        # =====================================================
        # NO NOTE / WRONG TAP
        # =====================================================

        if (
            best_note is None
            or best_distance > HIT_WINDOW
        ):

            self.combo = 0

            self.feedback = "MISS"

            self.feedback_timer = 30

            self.grade_miss_count += 1

            return


        # =====================================================
        # HOLD NOTE
        # =====================================================

        if best_note.is_hold:

            # Start holding the note
            best_note.holding = True

            best_note.hold_start_time = (
                pygame.time.get_ticks()
            )

            self.feedback = "HOLD!"

            self.feedback_timer = 20

            return


        # =====================================================
        # NORMAL NOTE GRADING
        # =====================================================

        if best_distance <= 10:

            grade = "PERFECT"

            points = 100

            self.perfect_count += 1


        elif best_distance <= 20:

            grade = "GREAT"

            points = 70

            self.great_count += 1


        else:

            grade = "OK"

            points = 40

            self.ok_count += 1


        # Mark note as hit
        best_note.hit = True

        # Add score
        self.score += points

        # Increase combo
        self.combo += 1

        self.max_combo = max(
            self.max_combo,
            self.combo
        )

        # Feedback
        self.feedback = grade

        self.feedback_timer = 30

        # Play sound
        self.play_grade_sound(
            grade
        )


    # =========================================================
    # UPDATE HOLD NOTES
    # =========================================================

    def update_hold_notes(self):

        current_time = pygame.time.get_ticks()

        # Get currently pressed keys
        keys = pygame.key.get_pressed()


        for note in self.notes:

            # Ignore normal notes
            if not note.is_hold:

                continue

            # Ignore hold notes that aren't being held
            if not note.holding:

                continue


            # Key required for this lane
            lane_key = LANE_KEYS[
                note.lane
            ]


            # =================================================
            # PLAYER RELEASED TOO EARLY
            # =================================================

            if not keys[lane_key]:

                note.holding = False

                note.missed = True

                self.combo = 0

                self.misses += 1

                self.grade_miss_count += 1

                self.feedback = "MISS"

                self.feedback_timer = 30

                continue


            # =================================================
            # CHECK HOLD DURATION
            # =================================================

            held_time = (
                current_time
                - note.hold_start_time
            )


            if held_time >= note.hold_duration:

                # Hold completed
                note.holding = False

                note.hit = True

                # Give points
                self.score += 100

                # Combo
                self.combo += 1

                self.max_combo = max(
                    self.max_combo,
                    self.combo
                )

                # Count successful hold
                self.perfect_count += 1

                # Feedback
                self.feedback = "PERFECT"

                self.feedback_timer = 30

                # Sound
                self.play_grade_sound(
                    "PERFECT"
                )


    # =========================================================
    # BPM NOTE SPAWNING
    # =========================================================

    def update_beat_spawning(self):

        current_time = pygame.time.get_ticks()


        # Spawn exactly according to BPM
        while (
            current_time
            >= self.next_beat_time
        ):

            self.spawn_note()

            # Schedule next beat
            self.next_beat_time += (
                BEAT_INTERVAL_MS
            )


    # =========================================================
    # UPDATE GAME
    # =========================================================

    def update(self):

        # Stop updates after game over
        if self.game_over:

            return


        self.frame += 1


        # =====================================================
        # BPM SPAWNING
        # =====================================================

        self.update_beat_spawning()


        # =====================================================
        # MOVE NOTES
        # =====================================================

        for note in self.notes:

            if note.hit or note.missed:

                continue

            # Move note
            note.update()


            # =================================================
            # NOTE MISSED
            # =================================================

            if note.y > HEIGHT:

                note.missed = True

                self.combo = 0

                self.misses += 1

                self.grade_miss_count += 1

                self.feedback = "MISS"

                self.feedback_timer = 30


        # =====================================================
        # HOLD NOTE PROCESSING
        # =====================================================

        self.update_hold_notes()


        # =====================================================
        # REMOVE OLD NOTES
        # =====================================================

        self.notes = [

            note

            for note in self.notes

            if not note.hit
            and not note.missed

        ]


        # =====================================================
        # FEEDBACK TIMER
        # =====================================================

        if self.feedback_timer > 0:

            self.feedback_timer -= 1

        else:

            self.feedback = ""


        # =====================================================
        # GAME OVER
        # =====================================================

        if self.misses >= MAX_MISSES:

            self.game_over = True


    # =========================================================
    # CALCULATE ACCURACY
    # =========================================================

    def get_accuracy(self):

        total_judged = (

            self.perfect_count
            + self.great_count
            + self.ok_count
            + self.grade_miss_count

        )


        if total_judged == 0:

            return 0.0


        successful = (

            self.perfect_count
            + self.great_count
            + self.ok_count

        )


        return (
            successful
            / total_judged
        ) * 100


    # =========================================================
    # DRAW GAME
    # =========================================================

    def draw(self):

        # Background
        self.screen.fill(
            (20, 20, 30)
        )


        # =====================================================
        # LANES
        # =====================================================

        lane_width = WIDTH // LANES


        for i in range(LANES):

            x = i * lane_width


            # Lane background
            pygame.draw.rect(

                self.screen,

                (30, 30, 45),

                (
                    x,
                    0,
                    lane_width,
                    HEIGHT
                )

            )


            # Lane divider
            pygame.draw.line(

                self.screen,

                (70, 70, 90),

                (
                    x,
                    0
                ),

                (
                    x,
                    HEIGHT
                ),

                2

            )


        # =====================================================
        # HIT LINE
        # =====================================================

        pygame.draw.line(

            self.screen,

            (255, 255, 255),

            (
                0,
                HIT_Y
            ),

            (
                WIDTH,
                HIT_Y
            ),

            3

        )


        # =====================================================
        # DRAW NOTES
        # =====================================================

        for note in self.notes:

            # Never draw already completed/missed notes
            if note.hit or note.missed:

                continue


            lane_x = (

                note.lane
                * lane_width
                + lane_width // 2

            )


            # =================================================
            # HOLD NOTE TAIL
            # =================================================

            if note.is_hold:

                tail_rect = (
                    note.get_hold_tail_rect(
                        lane_x
                    )
                )


                # Grey hold bar
                pygame.draw.rect(

                    self.screen,

                    (150, 150, 150),

                    tail_rect

                )


                # White outline
                pygame.draw.rect(

                    self.screen,

                    (255, 255, 255),

                    tail_rect,

                    2

                )


            # =================================================
            # NOTE HEAD
            # =================================================

            rect = note.get_rect(
                lane_x
            )


            if note.is_hold:

                # ---------------------------------------------
                # HOLD NOTE
                # ---------------------------------------------

                # White background
                pygame.draw.rect(

                    self.screen,

                    (255, 255, 255),

                    rect

                )


                # Lane-colored outline
                pygame.draw.rect(

                    self.screen,

                    LANE_COLORS[
                        note.lane
                    ],

                    rect,

                    3

                )


                # HOLD text
                hold_text = (
                    self.small_font.render(

                        "HOLD",

                        True,

                        (0, 0, 0)

                    )
                )


                hold_text_rect = (
                    hold_text.get_rect(

                        center=rect.center

                    )
                )


                self.screen.blit(

                    hold_text,

                    hold_text_rect

                )


            else:

                # ---------------------------------------------
                # NORMAL NOTE
                # ---------------------------------------------

                pygame.draw.rect(

                    self.screen,

                    LANE_COLORS[
                        note.lane
                    ],

                    rect

                )


        # =====================================================
        # HOLD PROGRESS
        # =====================================================

        for note in self.notes:

            if not note.is_hold:

                continue

            if not note.holding:

                continue

            if note.hit or note.missed:

                continue


            current_time = (
                pygame.time.get_ticks()
            )


            held_time = (

                current_time
                - note.hold_start_time

            )


            progress = min(

                held_time
                / note.hold_duration,

                1.0

            )


            rect = note.get_rect(

                note.lane
                * lane_width
                + lane_width // 2

            )


            progress_width = int(

                note.WIDTH
                * progress

            )


            # White progress indicator
            pygame.draw.rect(

                self.screen,

                (255, 255, 255),

                (

                    rect.x,

                    rect.y,

                    progress_width,

                    5

                )

            )


        # =====================================================
        # LANE LABELS
        # =====================================================

        for i in range(LANES):

            lane_x = (

                i * lane_width
                + lane_width // 2

            )


            label = (
                self.small_font.render(

                    LANE_LABELS[i],

                    True,

                    (255, 255, 255)

                )
            )


            label_rect = (
                label.get_rect(

                    center=(

                        lane_x,

                        HIT_Y + 35

                    )

                )
            )


            self.screen.blit(

                label,

                label_rect

            )


        # =====================================================
        # HUD
        # =====================================================

        score_text = (
            self.font.render(

                f"Score: {self.score}",

                True,

                (255, 255, 255)

            )
        )


        combo_text = (
            self.font.render(

                f"Combo: {self.combo}",

                True,

                (255, 255, 255)

            )
        )


        miss_text = (
            self.font.render(

                f"Misses: {self.misses}/{MAX_MISSES}",

                True,

                (255, 255, 255)

            )
        )


        bpm_text = (
            self.small_font.render(

                f"BPM: {BPM}",

                True,

                (200, 200, 200)

            )
        )


        self.screen.blit(

            score_text,

            (10, 10)

        )


        self.screen.blit(

            combo_text,

            (10, 45)

        )


        self.screen.blit(

            miss_text,

            (WIDTH - 150, 10)

        )


        self.screen.blit(

            bpm_text,

            (WIDTH - 100, 40)

        )


        # =====================================================
        # FEEDBACK
        # =====================================================

        if self.feedback:

            feedback = (
                self.big_font.render(

                    self.feedback,

                    True,

                    (255, 255, 255)

                )
            )


            feedback_rect = (
                feedback.get_rect(

                    center=(

                        WIDTH // 2,

                        HIT_Y - 60

                    )

                )
            )


            self.screen.blit(

                feedback,

                feedback_rect

            )


        # =====================================================
        # GAME OVER SCREEN
        # =====================================================

        if self.game_over:

            # Dark transparent overlay
            overlay = pygame.Surface(

                (
                    WIDTH,
                    HEIGHT
                ),

                pygame.SRCALPHA

            )


            overlay.fill(

                (
                    0,
                    0,
                    0,
                    200
                )

            )


            self.screen.blit(

                overlay,

                (0, 0)

            )


            # ---------------------------------------------
            # GAME OVER TITLE
            # ---------------------------------------------

            title = (
                self.big_font.render(

                    "GAME OVER",

                    True,

                    (255, 255, 255)

                )
            )


            title_rect = (
                title.get_rect(

                    center=(

                        WIDTH // 2,

                        100

                    )

                )
            )


            self.screen.blit(

                title,

                title_rect

            )


            # ---------------------------------------------
            # SCORE
            # ---------------------------------------------

            score = (
                self.font.render(

                    f"Score: {self.score}",

                    True,

                    (255, 255, 255)

                )
            )


            score_rect = (
                score.get_rect(

                    center=(

                        WIDTH // 2,

                        155

                    )

                )
            )


            self.screen.blit(

                score,

                score_rect

            )


            # ---------------------------------------------
            # GRADE SUMMARY
            # ---------------------------------------------

            perfect = (
                self.font.render(

                    f"PERFECT: {self.perfect_count}",

                    True,

                    (255, 255, 255)

                )
            )


            great = (
                self.font.render(

                    f"GREAT: {self.great_count}",

                    True,

                    (255, 255, 255)

                )
            )


            ok = (
                self.font.render(

                    f"OK: {self.ok_count}",

                    True,

                    (255, 255, 255)

                )
            )


            miss = (
                self.font.render(

                    f"MISS: {self.grade_miss_count}",

                    True,

                    (255, 255, 255)

                )
            )


            self.screen.blit(

                perfect,

                (150, 210)

            )


            self.screen.blit(

                great,

                (150, 245)

            )


            self.screen.blit(

                ok,

                (150, 280)

            )


            self.screen.blit(

                miss,

                (150, 315)

            )


            # ---------------------------------------------
            # ACCURACY
            # ---------------------------------------------

            accuracy = (
                self.get_accuracy()
            )


            accuracy_text = (
                self.font.render(

                    f"Accuracy: {accuracy:.1f}%",

                    True,

                    (255, 255, 255)

                )
            )


            accuracy_rect = (
                accuracy_text.get_rect(

                    center=(

                        WIDTH // 2,

                        375

                    )

                )
            )


            self.screen.blit(

                accuracy_text,

                accuracy_rect

            )


            # ---------------------------------------------
            # RESTART
            # ---------------------------------------------

            restart = (
                self.small_font.render(

                    "Press R to restart",

                    True,

                    (200, 200, 200)

                )
            )


            restart_rect = (
                restart.get_rect(

                    center=(

                        WIDTH // 2,

                        430

                    )

                )
            )


            self.screen.blit(

                restart,

                restart_rect

            )


        # Update display
        pygame.display.flip()


    # =========================================================
    # MAIN GAME LOOP
    # =========================================================

    def run(self):

        running = True


        while running:

            running = self.handle_events()

            self.update()

            self.draw()

            self.clock.tick(
                FPS
            )


        pygame.quit()