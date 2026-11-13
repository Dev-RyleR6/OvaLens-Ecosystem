"""
Foundation University soft desktop palette for the native operator interface.
Light neutral surfaces keep controls readable; the camera retains its dark well.
"""

class FUTheme:
    # Foundation University Institutional Brand
    PRIMARY_MAROON = "#800000"
    DARK_MAROON = "#5C0000"
    LIGHT_MAROON = "#991B1B"
    HOVER_MAROON = "#6B0000"
    PRIMARY_MAROON_BG = "#FAEEEE"
    PRIMARY_MAROON_BORDER = "#800000" # Institutional maroon border

    # Semantic results use readable text on quiet tinted surfaces.
    FERTILE_GREEN = "#357a38"         # Foundation University Agri-Green
    FERTILE_GREEN_HOVER = "#28642D"
    FERTILE_GREEN_BG = "#E5F2E7"
    FERTILE_GREEN_CARD = "#F1F8F3"
    FERTILE_GREEN_BORDER = "#C7DFCC"
    FERTILE_GREEN_TEXT = "#28642D"

    INFERTILE_AMBER = "#875A12"
    INFERTILE_AMBER_HOVER = "#70490C"
    INFERTILE_AMBER_BG = "#FBF0D9"
    INFERTILE_AMBER_CARD = "#FFFAF0"
    INFERTILE_AMBER_BORDER = "#EBDAB3"
    INFERTILE_AMBER_TEXT = "#80530C"

    REJECT_RED = "#DC2626"
    REJECT_RED_HOVER = "#B91C1C"
    REJECT_RED_BG = "#FDECEC"
    REJECT_RED_CARD = "#FFF5F5"
    REJECT_RED_BORDER = "#F2CACA"
    REJECT_RED_TEXT = "#A92020"

    # Native desktop surfaces follow the FU light theme.
    BG_LIGHT = "#F8FAFC"
    PANEL_LIGHT = "#FFFFFF"
    PANEL_LIGHT_ALT = "#F1F5F9"
    PANEL_ACCENT = "#E8EDF3"
    BORDER = "#E2E8F0"
    BORDER_DARK = "#CBD5E1"
    DARKROOM_VIEWPORT = "#111317"     # Studio Viewport for Candling Stream

    # Separate light-workspace text from the dark camera well.
    TEXT_PRIMARY = "#1E293B"
    TEXT_SECONDARY = "#475569"
    TEXT_MUTED = "#5B6B80"
    TEXT_DIM = "#5B6B80"
    VIEWPORT_TEXT = "#F1F5F9"
    VIEWPORT_MUTED = "#CBD5E1"
    TEXT_WHITE = "#FFFFFF"            # Pure White for dark buttons
    TEXT_ACCENT = "#875A12"

    # Standard Typography
    # Native Windows face: available offline, with real regular/bold weights.
    FONT_FAMILY = "Segoe UI"
    FONT_BODY = 14
    FONT_LABEL = 12
    FONT_HEADING = 20
    FONT_METRIC = 24


def fit_caption(text, measure, width):
    """Keep long batch codes and staff names within their native header control."""
    if measure(text) <= width:
        return text
    low, high = 0, len(text)
    while low < high:
        middle = (low + high + 1) // 2
        if measure(text[:middle] + "…") <= width:
            low = middle
        else:
            high = middle - 1
    return text[:low] + "…"
