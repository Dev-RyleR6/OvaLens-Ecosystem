"""
Foundation University low-glare desktop palette for the native operator interface.
Dim slate surfaces, distinct controls and high-contrast text support candling work.
"""

class FUTheme:
    # Foundation University Institutional Brand
    PRIMARY_MAROON = "#800000"
    DARK_MAROON = "#5C0000"
    LIGHT_MAROON = "#991B1B"
    HOVER_MAROON = "#6B0000"
    PRIMARY_MAROON_BG = "#382532"
    PRIMARY_MAROON_BORDER = "#D99AA6" # Institutional maroon border

    # Semantic results use readable text on quiet tinted surfaces.
    FERTILE_GREEN = "#357a38"         # Foundation University Agri-Green
    FERTILE_GREEN_HOVER = "#28642D"
    FERTILE_GREEN_BG = "#214A36"
    FERTILE_GREEN_CARD = "#18382C"
    FERTILE_GREEN_BORDER = "#4F8A63"
    FERTILE_GREEN_TEXT = "#A7E3B1"

    INFERTILE_AMBER = "#875A12"
    INFERTILE_AMBER_HOVER = "#70490C"
    INFERTILE_AMBER_BG = "#4C3820"
    INFERTILE_AMBER_CARD = "#332A20"
    INFERTILE_AMBER_BORDER = "#A48244"
    INFERTILE_AMBER_TEXT = "#F3CE85"

    REJECT_RED = "#DC2626"
    REJECT_RED_HOVER = "#B91C1C"
    REJECT_RED_BG = "#492732"
    REJECT_RED_CARD = "#38232D"
    REJECT_RED_BORDER = "#B5707E"
    REJECT_RED_TEXT = "#FFBAC2"

    # Legacy LIGHT names remain aliases for consumers; this station uses dim slate.
    BG_LIGHT = "#0F172A"
    PANEL_LIGHT = "#1E293B"
    PANEL_LIGHT_ALT = "#29384D"
    PANEL_ACCENT = "#374B65"
    BORDER = "#475569"
    BORDER_CONTROL = "#94A3B8"
    SELECTION_BG = "#41546F"
    SELECTION_HOVER = "#3B506C"
    INPUT_BG = "#111D2E"
    FOCUS = "#F4B2BF"
    BRAND_TEXT = "#F4B2BF"
    BORDER_DARK = BORDER_CONTROL
    DARKROOM_VIEWPORT = "#111317"     # Studio Viewport for Candling Stream

    # Separate light-workspace text from the dark camera well.
    TEXT_PRIMARY = "#F1F5F9"
    TEXT_SECONDARY = "#D5DEE9"
    TEXT_MUTED = "#C3CFDF"
    TEXT_DIM = TEXT_MUTED
    VIEWPORT_TEXT = "#F1F5F9"
    VIEWPORT_MUTED = "#CBD5E1"
    TEXT_WHITE = "#FFFFFF"            # Pure White for dark buttons
    TEXT_DISABLED_ON_ACCENT = "#D4BABA"
    TEXT_ACCENT = "#F3CE85"

    # Standard Typography
    # configure_desktop selects the shipped Inter face before Tk starts.
    FONT_PREFERRED = "Inter"
    FONT_FAMILY = "Segoe UI"
    FONT_BODY = 14
    FONT_LABEL = 13
    FONT_CAPTION = 13
    FONT_CONTROL = 14
    FONT_HEADING = 20
    FONT_METRIC = 24


DIM_PALETTE = {key: value for key, value in vars(FUTheme).items()
               if isinstance(value, str) and value.startswith('#')}
LIGHT_PALETTE = dict(DIM_PALETTE, **{
    'BG_LIGHT': '#EDF0F3', 'PANEL_LIGHT': '#F7F8FA',
    'PANEL_LIGHT_ALT': '#E2E7ED', 'PANEL_ACCENT': '#D2DAE4',
    'BORDER': '#A5AFBD', 'BORDER_CONTROL': '#657386', 'BORDER_DARK': '#657386',
    'INPUT_BG': '#FAFBFC', 'SELECTION_BG': '#CFD8E4', 'SELECTION_HOVER': '#C2CDDC',
    'TEXT_PRIMARY': '#182333', 'TEXT_SECONDARY': '#344256',
    'TEXT_MUTED': '#465469', 'TEXT_DIM': '#465469',
    'FOCUS': '#800000', 'BRAND_TEXT': '#800000',
    'PRIMARY_MAROON_BG': '#F1DFE3', 'PRIMARY_MAROON_BORDER': '#800000',
    'FERTILE_GREEN_BG': '#DEECE0', 'FERTILE_GREEN_CARD': '#E7F0E8',
    'FERTILE_GREEN_BORDER': '#357a38', 'FERTILE_GREEN_TEXT': '#245C2A',
    'INFERTILE_AMBER_BG': '#F3E8D4', 'INFERTILE_AMBER_CARD': '#F5EDDF',
    'INFERTILE_AMBER_BORDER': '#875A12', 'INFERTILE_AMBER_TEXT': '#70490C',
    'REJECT_RED_BG': '#F6E1E4', 'REJECT_RED_CARD': '#F8EAEC',
    'REJECT_RED_BORDER': '#B91C1C', 'REJECT_RED_TEXT': '#9F1828',
    'TEXT_ACCENT': '#70490C',
})
FUTheme.appearance = 'dim'


def set_palette(appearance):
    """Select visual tokens only; station and camera settings are untouched."""
    palette = LIGHT_PALETTE if appearance == 'light' else DIM_PALETTE
    for key, value in palette.items():
        setattr(FUTheme, key, value)
    FUTheme.appearance = 'light' if appearance == 'light' else 'dim'


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
