"""
LED Face Patterns for 8x8 Matrix (64 LEDs)
Displays animated faces that react to Nova's state
"""

# 8x8 LED matrix mapping (row-major order, 0-63)
# The matrix is laid out as:
# 0  1  2  3  4  5  6  7
# 8  9  10 11 12 13 14 15
# ... and so on

# Colors
OFF = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (0, 100, 255)
CYAN = (0, 255, 255)
GREEN = (0, 255, 100)
YELLOW = (255, 200, 0)
ORANGE = (255, 100, 0)
PURPLE = (150, 0, 255)
PINK = (255, 100, 150)


def create_pattern(rows, color=WHITE):
    """Convert 8x8 binary pattern to LED colors"""
    pixels = [OFF] * 64
    for row_idx, row in enumerate(rows):
        for col_idx in range(8):
            if row & (1 << (7 - col_idx)):
                pixels[row_idx * 8 + col_idx] = color
    return pixels


# ========== FACE PATTERNS ==========

# Happy face :)
HAPPY_FACE = [
    0b00000000,
    0b01100110,
    0b01100110,
    0b00000000,
    0b00000000,
    0b10000001,
    0b01000010,
    0b00111100,
]

# Sad face :(
SAD_FACE = [
    0b00000000,
    0b01100110,
    0b01100110,
    0b00000000,
    0b00000000,
    0b00111100,
    0b01000010,
    0b10000001,
]

# Neutral face :|
NEUTRAL_FACE = [
    0b00000000,
    0b01100110,
    0b01100110,
    0b00000000,
    0b00000000,
    0b00000000,
    0b01111110,
    0b00000000,
]

# Listening face (eyes open wide) O_O
LISTENING_FACE = [
    0b00000000,
    0b01111110,
    0b01111110,
    0b01100110,
    0b00000000,
    0b00000000,
    0b00011000,
    0b00000000,
]

# Speaking face (mouth open) :O
SPEAKING_OPEN = [
    0b00000000,
    0b01100110,
    0b01100110,
    0b00000000,
    0b00011000,
    0b00100100,
    0b00100100,
    0b00011000,
]

# Speaking face (mouth closed) :-
SPEAKING_CLOSED = [
    0b00000000,
    0b01100110,
    0b01100110,
    0b00000000,
    0b00000000,
    0b00000000,
    0b00111100,
    0b00000000,
]

# Thinking face (one eye squinting) -_o
THINKING_FACE = [
    0b00000000,
    0b00000110,
    0b01111110,
    0b00000110,
    0b00000000,
    0b00000000,
    0b00111100,
    0b00000000,
]

# Wink face ;)
WINK_FACE = [
    0b00000000,
    0b01100000,
    0b01100110,
    0b00000110,
    0b00000000,
    0b10000001,
    0b01000010,
    0b00111100,
]

# Surprised face :O
SURPRISED_FACE = [
    0b00000000,
    0b01100110,
    0b01100110,
    0b00000000,
    0b00011000,
    0b00111100,
    0b00111100,
    0b00011000,
]

# Heart
HEART = [
    0b00000000,
    0b01100110,
    0b11111111,
    0b11111111,
    0b11111111,
    0b01111110,
    0b00111100,
    0b00011000,
]

# Sleeping face z_z
SLEEPING_FACE = [
    0b00000000,
    0b00000000,
    0b01111110,
    0b00000000,
    0b00000000,
    0b00000000,
    0b00111100,
    0b00000000,
]


# ========== ANIMATION FRAMES ==========

def get_listening_animation():
    """Pulsing eyes animation while listening"""
    return [
        (create_pattern(LISTENING_FACE, CYAN), 0.3),
        (create_pattern(LISTENING_FACE, BLUE), 0.3),
    ]


def get_speaking_animation():
    """Mouth opening/closing while speaking"""
    return [
        (create_pattern(SPEAKING_OPEN, GREEN), 0.15),
        (create_pattern(SPEAKING_CLOSED, GREEN), 0.15),
    ]


def get_thinking_animation():
    """Blinking animation while thinking"""
    return [
        (create_pattern(THINKING_FACE, PURPLE), 0.4),
        (create_pattern(NEUTRAL_FACE, PURPLE), 0.2),
    ]


def get_idle_animation():
    """Gentle breathing animation when idle"""
    return [
        (create_pattern(HAPPY_FACE, (50, 50, 50)), 1.0),
        (create_pattern(HAPPY_FACE, (100, 100, 100)), 1.0),
        (create_pattern(HAPPY_FACE, (50, 50, 50)), 1.0),
    ]


def get_wake_animation():
    """Wake up animation sequence"""
    return [
        (create_pattern(SLEEPING_FACE, (30, 30, 30)), 0.3),
        (create_pattern(NEUTRAL_FACE, (100, 100, 100)), 0.3),
        (create_pattern(SURPRISED_FACE, YELLOW), 0.3),
        (create_pattern(HAPPY_FACE, WHITE), 0.5),
    ]


def get_happy_animation():
    """Happy celebration animation"""
    return [
        (create_pattern(HAPPY_FACE, YELLOW), 0.2),
        (create_pattern(WINK_FACE, ORANGE), 0.2),
        (create_pattern(HAPPY_FACE, PINK), 0.2),
    ]


# ========== STATE FACES ==========

FACE_PATTERNS = {
    "idle": create_pattern(HAPPY_FACE, (80, 80, 80)),
    "listening": create_pattern(LISTENING_FACE, CYAN),
    "speaking": create_pattern(SPEAKING_OPEN, GREEN),
    "thinking": create_pattern(THINKING_FACE, PURPLE),
    "happy": create_pattern(HAPPY_FACE, YELLOW),
    "sad": create_pattern(SAD_FACE, BLUE),
    "surprised": create_pattern(SURPRISED_FACE, ORANGE),
    "wink": create_pattern(WINK_FACE, PINK),
    "heart": create_pattern(HEART, (255, 0, 50)),
    "sleeping": create_pattern(SLEEPING_FACE, (30, 30, 50)),
}


def get_face(state: str):
    """Get a static face pattern by state name"""
    return FACE_PATTERNS.get(state, FACE_PATTERNS["idle"])
