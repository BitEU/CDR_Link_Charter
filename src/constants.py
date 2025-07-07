# constants.py
"""
Constants and configuration for the People Connection Visualizer
"""

COMRADE_VERSION = "0.6.6"

# Modern color scheme
COLORS = {
    'primary': '#2563eb',      # Modern blue
    'primary_light': '#60a5fa',
    'primary_dark': '#1d4ed8',
    'secondary': '#10b981',    # Modern green
    'secondary_light': '#34d399',
    'accent': '#f59e0b',       # Amber
    'background': '#f8fafc',   # Light gray
    'surface': '#ffffff',      # White
    'surface_bright': '#f0f0f0',  # Light gray for highlighting
    'text_primary': '#1e293b', # Dark slate
    'text_secondary': '#64748b', # Slate
    'border': '#e2e8f0',       # Light border
    'hover': '#f1f5f9',        # Light hover
    'danger': '#ef4444',       # Red
    'success': '#22c55e'       # Green
}

# Card color options - 8 distinct colors
CARD_COLORS = [
    '#2563eb',  # Blue (default)
    '#dc2626',  # Red
    '#16a34a',  # Green
    '#ca8a04',  # Yellow
    '#9333ea',  # Purple
    '#ea580c',  # Orange
    '#0891b2',  # Cyan
    '#be185d'   # Pink
]

# Application settings
APP_TITLE = "🔗 People Connection Visualizer"
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900

# Canvas settings
GRID_SIZE = 40
DEFAULT_CARD_MIN_WIDTH = 200
DEFAULT_CARD_MIN_HEIGHT = 120

# Layout settings
BOX_LAYOUT_COLS = 2
BOX_LAYOUT_COL_WIDTH = 400
BOX_LAYOUT_ROW_HEIGHT = 200
BOX_LAYOUT_START_X = 200
BOX_LAYOUT_START_Y = 120