"""
Engineering Constants for HK Code 2013 Structural Design
"""

# Material Densities
CONCRETE_DENSITY = 24.5  # kN/m³

# Steel Yield Strengths (MPa)
STEEL_YIELD_STRENGTH = 500  # Grade 500 reinforcement (fy)
LINK_YIELD_STRENGTH = 250   # Grade 250 links (fyv)

# Partial Safety Factors (HK Code 2013)
GAMMA_C = 1.5   # Concrete material factor
GAMMA_S = 1.15  # Steel material factor (main bars)
GAMMA_SV = 1.15 # Steel material factor (shear links)

# Load Factors (ULS)
GAMMA_G = 1.4   # Dead load factor
GAMMA_Q = 1.6   # Live load factor
GAMMA_W = 1.4   # Wind load factor

# Serviceability Load Factors
GAMMA_G_SLS = 1.0
GAMMA_Q_SLS = 1.0

# Design Constants
PATTERN_LOAD_FACTOR = 1.1  # Magnification for alternate span loading

# Span/Depth Ratios (HK Code Table 7.4)
SPAN_DEPTH_RATIOS = {
    "cantilever": 7,
    "simply_supported": 20,
    "continuous": 26,
    "one_way_slab": 26,
    "two_way_slab": 30,
    "beam": 18,
}

# Minimum Element Dimensions (mm)
MIN_SLAB_THICKNESS = 125
MIN_BEAM_WIDTH = 250
MIN_BEAM_DEPTH = 300
MIN_COLUMN_SIZE = 200

# Maximum Practical Dimensions (mm)
MAX_BEAM_DEPTH = 1500  # Increased to accommodate larger spans
MAX_BEAM_WIDTH = 800   # Increased to accommodate heavier loads

# Deep Beam Threshold
DEEP_BEAM_RATIO = 2.0  # L/d < 2.0 triggers deep beam warning

# Reinforcement Limits (%)
MIN_SLAB_REINFORCEMENT = 0.13
MAX_SLAB_REINFORCEMENT = 4.0
MIN_BEAM_REINFORCEMENT = 0.13
MAX_BEAM_REINFORCEMENT = 4.0
MIN_COLUMN_REINFORCEMENT = 0.8
MAX_COLUMN_REINFORCEMENT = 6.0

# Shear Constants
SHEAR_STRESS_MAX_FACTOR = 0.8  # v_max = 0.8 * sqrt(fcu) or 7 MPa
SHEAR_STRESS_MAX_LIMIT = 7.0   # MPa absolute limit

# Deflection Limits
DRIFT_LIMIT = 1/500  # Building sway index limit

# Carbon Emission Factors (kgCO2e per m³ of concrete)
CARBON_FACTORS = {
    25: 280,
    30: 300,
    35: 320,
    40: 340,
    45: 365,
    50: 390,
    55: 420,
    60: 450,
}
