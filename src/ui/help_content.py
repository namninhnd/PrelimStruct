"""
Centralized help content for PrelimStruct Help System

All help topics, tooltips, and documentation organized by context.
"""

from src.ui.help_system import HelpTopic

# =============================================================================
# HELP TOPICS DATABASE
# =============================================================================

HELP_TOPICS = [
    # --- GEOMETRY SECTION ---
    HelpTopic(
        id="geo_01_building_dims",
        title="Building Dimensions",
        content="""
        **Building dimensions** define the overall footprint and height of the structure.

        - **Width (X)**: Building dimension in X-direction (meters)
        - **Depth (Y)**: Building dimension in Y-direction (meters)
        - **Total Height**: Sum of all floor heights (auto-calculated)

        These dimensions are used to:
        - Generate structural grid
        - Position core walls
        - Calculate wind loads
        - Determine lateral load distribution
        """,
        context="geometry",
        references=["HK Code 2013 Cl 2.1 - Loads and Load Combinations"]
    ),

    HelpTopic(
        id="geo_02_core_wall",
        title="Core Wall Configuration",
        content="""
        **Core walls** provide lateral resistance and house lift shafts, stairs, and services.

        **Available Configurations:**
        - **I-Section**: Two parallel walls with coupling beams
        - **C-Shaped (Facing)**: Two C-sections facing each other
        - **C-Shaped (Back-to-Back)**: Two C-sections positioned back-to-back
        - **Tube (Center Opening)**: Box-shaped with central door opening
        - **Tube (Side Opening)**: Box-shaped with side door opening

        **Design Considerations:**
        - Core wall provides torsional rigidity
        - Coupling beams transfer shear between walls
        - Opening sizes affect stiffness and capacity
        """,
        context="geometry",
        references=[
            "HK Code 2013 Cl 6.7 - Deep Beams (Coupling Beams)",
            "HK Code 2013 Cl 9.8 - Walls"
        ]
    ),

    HelpTopic(
        id="geo_03_floor_heights",
        title="Floor Heights",
        content="""
        **Floor heights** define vertical spacing between structural levels.

        - **Typical Floor**: Height for repeated floors (usually 3.0-4.0m for residential)
        - **Ground Floor**: Often taller to accommodate lobby/retail (3.5-5.0m)
        - **Roof Level**: May differ if mechanical floor or rooftop amenities

        **Impact on Design:**
        - Column slenderness ratios
        - Beam spans and moments
        - Drift limits (lateral displacement)
        - P-Delta effects (tall buildings)
        """,
        context="geometry",
        references=["HK Code 2013 Cl 7.3.2 - Deflection and Serviceability Limits"]
    ),

    # --- LOADS SECTION ---
    HelpTopic(
        id="load_01_occupancy",
        title="Occupancy Type & Live Loads",
        content="""
        **Occupancy type** determines imposed loads per HK Code Table 2.

        **Common Types:**
        - **Residential**: 2.0 kPa (habitable rooms), 1.5 kPa (balconies)
        - **Office**: 2.5-4.0 kPa (general office areas)
        - **Retail**: 4.0-5.0 kPa (shops, restaurants)
        - **Car Park**: 2.5 kPa (light vehicles), 5.0 kPa (heavy vehicles)

        **Pattern Loading Factor:**
        - Applied to account for non-uniform live load distribution
        - Typically 0.5-0.7 (reduces total imposed load in combination)
        """,
        context="loads",
        references=[
            "HK Code 2013 Cl 2.1 Table 2 - Imposed Loads",
            "HK Code 2013 Cl 2.4.2.2 - Pattern Loading"
        ]
    ),

    HelpTopic(
        id="load_02_wind",
        title="Wind Loads",
        content="""
        **Wind loads** are calculated per HK Code of Practice on Wind Effects 2019.

        **Key Parameters:**
        - **Wind Speed**: Basic wind speed for Hong Kong (typically 50-70 m/s)
        - **Terrain Category**: Urban, suburban, or open terrain
        - **Exposure**: Windward, leeward, or corner effects

        **Load Cases:**
        - 24 directional cases (0°, 15°, 30°, ..., 345°)
        - 48 combinations including torsion (±5% eccentricity)

        **Design Checks:**
        - Lateral drift < H/500 (serviceability)
        - Member forces for ULS design
        - Overturning and stability
        """,
        context="loads",
        references=[
            "COP Wind Effects HK 2019",
            "HK Code 2013 Cl 2.4.3 - Partial Safety Factors"
        ]
    ),

    HelpTopic(
        id="load_03_combinations",
        title="Load Combinations",
        content="""
        **Load combinations** per HK Code Cl 2.4.3:

        **Ultimate Limit State (ULS):**
        - 1.4 DL + 1.6 LL
        - 1.4 DL + 1.4 WL
        - 1.2 DL + 1.2 LL + 1.2 WL

        **Serviceability Limit State (SLS):**
        - 1.0 DL + 1.0 LL
        - 1.0 DL + 1.0 WL

        **Pattern Loading:**
        - Pattern factor applied to LL (typically 0.5-0.7)
        - Accounts for non-simultaneous loading of all floors
        """,
        context="loads",
        references=["HK Code 2013 Cl 2.4.3 - Load Combinations and Partial Factors"]
    ),

    # --- MATERIALS SECTION ---
    HelpTopic(
        id="mat_01_concrete",
        title="Concrete Grades",
        content="""
        **Concrete characteristic strength (fcu)** per HK Code:

        **Common Grades:**
        - **C30**: fcu = 30 MPa (low-rise, non-structural)
        - **C35**: fcu = 35 MPa (typical slabs, beams)
        - **C40**: fcu = 40 MPa (typical columns, < 20 stories)
        - **C45**: fcu = 45 MPa (columns, 20-30 stories)
        - **C50**: fcu = 50 MPa (high-rise columns, > 30 stories)
        - **C60**: fcu = 60 MPa (very high-rise, core walls)

        **Properties:**
        - Ec = 22 × (fcu/20)^0.3 (kN/mm²) [Cl 3.1.7]
        - fcr = 0.37 √fcu (flexural tensile strength) [Cl 3.1.6.3]
        """,
        context="materials",
        references=[
            "HK Code 2013 Cl 3.1.7 - Modulus of Elasticity",
            "HK Code 2013 Cl 3.1.6.3 - Flexural Tensile Strength"
        ]
    ),

    HelpTopic(
        id="mat_02_steel",
        title="Reinforcement",
        content="""
        **Reinforcement characteristic strength (fy):**

        **Grades:**
        - **Grade 460**: fy = 460 MPa (older standard)
        - **Grade 500**: fy = 500 MPa (current standard)

        **Properties:**
        - Es = 200 GPa (modulus of elasticity)
        - Ductility Class: B or C (typical)

        **Minimum Cover:**
        - Depends on exposure class (XC1-XC4, XD1-XS3)
        - Mild: 25-30mm
        - Moderate: 35-40mm
        - Severe: 45-50mm
        """,
        context="materials",
        references=[
            "HK Code 2013 Cl 3.2 - Reinforcement",
            "HK Code 2013 Table 4.2 - Nominal Cover"
        ]
    ),

    HelpTopic(
        id="mat_03_exposure",
        title="Exposure Classes",
        content="""
        **Exposure classes** determine durability requirements and concrete cover.

        **Classes (per HK Code Table 4.1):**
        - **XC1**: Dry or permanently wet (interior, low humidity)
        - **XC2**: Wet, rarely dry (long-term water contact)
        - **XC3/XC4**: Moderate/high humidity (exterior, exposed)
        - **XD1**: Moderate humidity (chloride exposure)
        - **XS1-XS3**: Marine exposure (airborne salt, seawater)

        **Effects:**
        - Higher exposure → greater cover required
        - Affects concrete grade requirements
        - Impacts carbonation resistance
        """,
        context="materials",
        references=["HK Code 2013 Cl 4.2 - Durability and Cover"]
    ),

    # --- FEM SECTION ---
    HelpTopic(
        id="fem_01_model_builder",
        title="FEM Model Builder",
        content="""
        **Finite Element Model** built using OpenSeesPy:

        **Elements:**
        - **Beam Elements**: ElasticBeamColumn (frame members)
        - **Shell Elements**: ShellMITC4 with PlateFiber section (walls, slabs)
        - **Rigid Diaphragm**: Floor slabs act as rigid in-plane

        **Node Numbering:**
        - Floor-based: Floor × 10000 + Node ID
        - Example: Node 20015 = Floor 2, Node 15

        **Boundary Conditions:**
        - Fixed base (all DOFs restrained at foundation)
        - Rigid diaphragm constraint at each floor
        """,
        context="fem",
        references=[
            "OpenSeesPy Documentation",
            "ShellMITC4 Element: https://openseespydoc.readthedocs.io/"
        ]
    ),

    HelpTopic(
        id="fem_02_analysis",
        title="FEM Analysis Procedure",
        content="""
        **Analysis Steps:**

        1. **Build Model**: Nodes, elements, materials, constraints
        2. **Apply Loads**: Gravity (DL + LL), lateral (wind)
        3. **Run Analysis**: Static linear or nonlinear
        4. **Extract Results**: Displacements, forces, reactions

        **Solver:**
        - Linear static (small displacements)
        - Supports multiple load cases
        - Superposition for load combinations

        **Output:**
        - Node displacements (Δx, Δy, Δz, θx, θy, θz)
        - Element forces (N, Vy, Vz, T, My, Mz)
        - Support reactions (for foundation design)
        """,
        context="fem",
        references=["OpenSeesPy Analysis Commands"]
    ),

    HelpTopic(
        id="fem_03_visualization",
        title="FEM Visualization",
        content="""
        **Available Views:**

        - **Plan View**: Top-down view of floor layout with element numbers
        - **Elevation View**: Side view (X-Z or Y-Z) showing vertical structure
        - **3D View**: Interactive 3D model with deformed shape

        **Display Options:**
        - **Deformed Shape**: Exaggerated displacement (scale factor)
        - **Force Diagrams**: Axial, shear, moment (color-coded)
        - **Utilization Ratios**: Demand/capacity by element

        **Interaction:**
        - Zoom, pan, rotate (3D)
        - Click elements for detailed forces
        - Toggle layers (beams, columns, walls, slabs)
        """,
        context="fem",
        references=["opsvis Documentation"]
    ),

    # --- DESIGN SECTION ---
    HelpTopic(
        id="design_01_slab",
        title="Slab Design",
        content="""
        **Slab design** per HK Code Cl 6.1 (Flexure) and Cl 7.3 (Deflection):

        **Checks:**
        1. **Flexure**: M / (bd²) ≤ K' (balanced design)
        2. **Shear**: v ≤ vc + vr (concrete + reinforcement)
        3. **Deflection**: Span/effective depth ≤ basic ratio × factors
        4. **Minimum Reinforcement**: As,min = 0.13% bh (Cl 9.2.1.1)

        **Design Moments:**
        - Continuous slabs: -ve at supports, +ve at midspan
        - FEM moments used (not simplified coefficients)

        **Output:**
        - Required steel area (mm²/m)
        - Bar spacing and diameter
        - Utilization ratio
        """,
        context="design",
        references=[
            "HK Code 2013 Cl 6.1 - Beams (applies to slabs)",
            "HK Code 2013 Cl 7.3 - Deflection",
            "HK Code 2013 Cl 9.2.1.1 - Minimum Reinforcement"
        ]
    ),

    HelpTopic(
        id="design_02_beam",
        title="Beam Design",
        content="""
        **Beam design** per HK Code Cl 6.1 (Flexure) and Cl 6.2 (Shear):

        **Flexural Design:**
        - K = M / (fcu × bd²)
        - If K ≤ K': singly reinforced
        - If K > K': compression steel required

        **Shear Design:**
        - v = V / (bd)
        - vc = design concrete shear strength (Table 6.3)
        - vr = Asv × fyv / (sv × b)

        **Deep Beams (Cl 6.7):**
        - Applies when span/depth < 2.0
        - Different shear and flexure provisions
        - Coupling beams typically deep beams
        """,
        context="design",
        references=[
            "HK Code 2013 Cl 6.1 - Flexural Design",
            "HK Code 2013 Cl 6.2 - Shear",
            "HK Code 2013 Cl 6.7 - Deep Beams"
        ]
    ),

    HelpTopic(
        id="design_03_column",
        title="Column Design",
        content="""
        **Column design** per HK Code Cl 6.2 (Axial + Bending):

        **Short Columns (le/h < 15):**
        - Interaction diagram (N-M curve)
        - Check (N, M) point within capacity envelope

        **Slender Columns (le/h ≥ 15):**
        - Additional moment from slenderness
        - Madd = N × au
        - au = additional deflection per Cl 6.2.5.1

        **Biaxial Bending:**
        - Interaction surface (N-Mx-My)
        - Simplified check: (Mx/Mux)^αn + (My/Muy)^αn ≤ 1.0

        **Output:**
        - Required reinforcement (total As, mm²)
        - Utilization ratio
        - Link/tie requirements
        """,
        context="design",
        references=[
            "HK Code 2013 Cl 6.2 - Columns",
            "HK Code 2013 Cl 6.2.5 - Slenderness"
        ]
    ),

    HelpTopic(
        id="design_04_punching",
        title="Punching Shear",
        content="""
        **Punching shear** at slab-column connections (Cl 6.4):

        **Checks:**
        1. **Face of Column**: v ≤ 0.8 √fcu or 5 MPa
        2. **Critical Perimeter (1.5d)**: v ≤ vc (from Table 6.3)
        3. **Shear Reinforcement Zone**: If v > vc, provide shear studs/links

        **Critical Perimeter:**
        - u = perimeter at distance 1.5d from column face
        - For internal columns: rectangular perimeter
        - For edge/corner columns: reduced perimeter

        **Design Shear Stress:**
        - v = V / (u × d)
        - V = total reaction force from FEM
        """,
        context="design",
        references=["HK Code 2013 Cl 6.4 - Punching Shear"]
    ),

    # --- RESULTS SECTION ---
    HelpTopic(
        id="result_01_utilization",
        title="Utilization Ratios",
        content="""
        **Utilization ratio** = Demand / Capacity:

        - **< 0.85**: OK (green) - adequate capacity
        - **0.85-1.00**: WARNING (yellow) - near capacity
        - **> 1.00**: FAIL (red) - insufficient capacity

        **Calculation:**
        - Demand = FEM forces (M, V, N)
        - Capacity = HK Code design strength

        **Interpretation:**
        - High ratios → increase member size or reinforcement
        - Very low ratios → may be over-designed (optimize)
        """,
        context="results"
    ),

    HelpTopic(
        id="result_02_drift",
        title="Lateral Drift Limits",
        content="""
        **Drift limits** per HK Code Cl 7.3.2:

        **Serviceability Limit:**
        - Inter-story drift: Δ / h ≤ 1/500 (typical)
        - Some codes use 1/300 or 1/400

        **Calculation:**
        - Δ = horizontal displacement at floor i+1 - floor i
        - h = floor height

        **Actions if Exceeded:**
        - Increase core wall thickness
        - Add shear walls or braced frames
        - Increase column/beam stiffness
        - Check P-Delta effects (tall buildings)
        """,
        context="results",
        references=["HK Code 2013 Cl 7.3.2 - Horizontal Deflection"]
    ),

    HelpTopic(
        id="result_03_reactions",
        title="Support Reactions",
        content="""
        **Support reactions** at foundation level:

        **Uses:**
        - Foundation design (pile capacity, raft sizing)
        - Soil bearing pressure checks
        - Overturning stability

        **Components:**
        - Fx, Fy, Fz: Reaction forces (kN)
        - Mx, My, Mz: Reaction moments (kNm)

        **Export:**
        - View reaction table (all nodes, all load cases)
        - Export to CSV for foundation design
        - Compare to geotechnical capacity
        """,
        context="results"
    ),
]


# =============================================================================
# TECHNICAL TERM TOOLTIPS
# =============================================================================

TOOLTIPS = {
    # Geometry
    "fcu": "Characteristic compressive cube strength of concrete at 28 days (MPa)",
    "fy": "Characteristic yield strength of reinforcement steel (MPa)",
    "effective_depth": "Distance from compression face to centroid of tension steel (d = h - cover - φ/2)",
    "span_depth_ratio": "Ratio of span length to effective depth (used for deflection checks)",
    "slenderness_ratio": "Effective length / radius of gyration (λ = le/i)",

    # Loads
    "DL": "Dead Load - permanent gravity loads (self-weight, finishes, MEP)",
    "LL": "Live Load / Imposed Load - variable gravity loads (occupancy, furniture)",
    "WL": "Wind Load - lateral loads from wind pressure",
    "pattern_loading": "Reduction factor for non-simultaneous loading of multiple floors",

    # Analysis
    "ULS": "Ultimate Limit State - strength design with partial safety factors (1.4 DL + 1.6 LL)",
    "SLS": "Serviceability Limit State - deflection/crack control with unfactored loads",
    "rigid_diaphragm": "Assumption that floor slabs are infinitely stiff in-plane (distributes lateral loads)",

    # Design
    "K_value": "Dimensionless moment coefficient K = M / (fcu × b × d²)",
    "K_prime": "Balanced design limit (0.156 for Grade 500 steel)",
    "shear_stress": "Applied shear force divided by effective area v = V / (b × d)",
    "vc": "Design concrete shear stress capacity without shear reinforcement",

    # Materials
    "Ec": "Modulus of elasticity of concrete (kN/mm²)",
    "Es": "Modulus of elasticity of steel reinforcement (200 GPa)",
    "cover": "Concrete cover to reinforcement (mm) - for durability and fire resistance",

    # FEM
    "ShellMITC4": "4-node shell element with Mindlin-Reissner plate theory (OpenSeesPy)",
    "PlateFiber": "Section type for shell elements using fiber discretization",
    "rigid_link": "Constraint connecting nodes to maintain relative positions",
}


# =============================================================================
# QUICK REFERENCE DATA
# =============================================================================

HK_CODE_CLAUSES = {
    "2.1": "Loads and Load Arrangements",
    "2.4.2.2": "Pattern Loading",
    "2.4.3": "Partial Safety Factors for Loads",
    "3.1.6.3": "Flexural Tensile Strength",
    "3.1.7": "Modulus of Elasticity",
    "3.2": "Reinforcement",
    "4.2": "Durability and Concrete Cover",
    "6.1": "Beams - Flexural Design",
    "6.2": "Columns - Axial Load and Bending",
    "6.4": "Punching Shear",
    "6.7": "Deep Beams",
    "7.3.1.2": "Deflection of Beams and Slabs",
    "7.3.2": "Lateral Deflection",
    "9.2.1.1": "Minimum Reinforcement in Beams",
    "9.8": "Walls",
}
