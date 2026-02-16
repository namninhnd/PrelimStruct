# PrelimStruct

AI-Assisted Preliminary Structural Design Platform for Hong Kong Code compliance.

A Python-powered structural engineering tool featuring rigorous HK Code 2013 compliance, integrated FEM analysis using OpenSeesPy, AI-assisted design optimization, and professional "Magazine-Style" HTML report generation.

## What's New in v3.5

- **Gemini AI Provider**: Google AI Studio (Gemini 3 Flash) as primary LLM with 1M context and built-in thinking
- **FEM Design Checks**: HK Code 2013 element-level checks — flexural, shear, ductility, rebar sizing
- **Design Checks Panel**: Top-3 governing elements per type (beams, slabs, columns, walls, coupling beams)
- **AI Chat UX**: Natural conversation with parameter extraction, spinner feedback, follow-up suggestions
- **I-Section Core Walls**: Node deduplication, collinear trim, polygonal slab support
- **Triangular Mesh**: Tri/quad shell mesh toggle for slab and wall elements
- **Performance**: Structure reuse across load cases, optimized benchmarks
- **Report Redesign**: Page 2 replaced with FEM Design Checks summary (replaces hand-calc steps)

## Features

### v3.5 - Design Checks + AI Chat (Phases 12-16)
- **FEM Design Checks**: Element-level HK Code 2013 compliance (flexural, shear, ductility)
- **Governing Element Selection**: Multi-factor scoring to surface Top-3 critical elements
- **Design Checks Panel**: Per-type tables for beams, slab strips, columns, walls, coupling beams
- **AI Chat Assistant**: Natural language building description with regex + LLM parameter extraction
- **Gemini Integration**: Google AI Studio primary provider with DeepSeek/Grok/OpenRouter fallback
- **I-Section Core Walls**: Proper node merge, collinear segment trimming
- **Tri Shell Mesh**: Toggle between triangular and quadrilateral shell elements
- **Report Page 2**: FEM design check results replace step-by-step hand calculations

### v3.0 - FEM + AI Features
- **OpenSeesPy Integration**: Linear static FEM analysis with beam-column elements
- **Core Wall System**: 5 configuration types with automatic section property calculation
- **Coupling Beam Design**: Deep beam provisions per HK Code 2013 Cl 6.7
- **Beam Trimming**: Automatic beam shortening at core wall boundaries
- **AI Design Optimization**: Gradient-based optimization with AI suggestions
- **AI Results Interpretation**: FEM vs hand-calc comparison with recommendations
- **FEM Visualization**: Interactive Plan/Elevation/3D views with Plotly

### v2.1 - Core Features
- **Gravity Design Engine**: Slab, beam, and column design with HK Code 2013 compliance
- **Lateral Stability Module**: HK Wind Code 2019 with core wall and moment frame systems
- **Interactive Dashboard**: Real-time Streamlit interface with live status badges
- **Carbon Estimator**: Embodied carbon calculation based on concrete grades
- **Magazine-Style Reports**: Professional HTML reports with Jinja2 templating

## Quick Start

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/namninhnd/PrelimStruct.git
cd PrelimStruct
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. (Optional) Configure AI Assistant:
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your API key
# Default provider: Gemini (free at https://aistudio.google.com/apikey)
# Backup providers: DeepSeek, Grok, OpenRouter
```

### Launching the Streamlit Dashboard

To start the interactive design platform:

```bash
streamlit run app.py
```

This will:
- Start a local web server (typically at `http://localhost:8501`)
- Open the dashboard automatically in your default browser
- Enable real-time structural calculations as you adjust inputs

**Alternative launch methods:**

```bash
# Specify a custom port
streamlit run app.py --server.port 8080

# Run in headless mode (no auto-open browser)
streamlit run app.py --server.headless true

# Run with specific address binding
streamlit run app.py --server.address 0.0.0.0
```

## Using the Dashboard

### Sidebar Controls

The left sidebar contains all input controls organized into sections:

1. **AI Assistant**: Natural language building description with parameter extraction
2. **Quick Presets**: Pre-configured building types (Residential, Office, Retail, Car Park, Plant Room)
3. **Geometry**: Bay dimensions, number of floors, story height
4. **Loading**: Live load class selection from HK Code Table 3.1/3.2
5. **Materials**: Concrete grades for slabs, beams, and columns
6. **Core Wall Configuration**: 5 configuration types with dimension inputs
7. **Lateral System**: Terrain category, core wall location
8. **Load Combinations**: Toggle between ULS Gravity, ULS Wind, and SLS

### Core Wall Configurations

| Configuration | Description | Use Case |
|---------------|-------------|----------|
| I_SECTION | Two walls blended into I-shape | Efficient for regular cores |
| TWO_C_FACING | Two C-walls facing each other | Corridor cores with central opening |
| TWO_C_BACK_TO_BACK | Two C-walls back to back | Cores with openings on both sides |
| TUBE_CENTER_OPENING | Box core with center door | Elevator/stair cores |
| TUBE_SIDE_OPENING | Box core with side door | Asymmetric cores |

### Main Dashboard

- **Status Badges**: Real-time pass/warn/fail indicators for each element
- **Key Metrics**: Live load, design load, concrete volume, carbon intensity
- **Framing Plan**: Interactive Plotly visualization with core wall outline
- **Lateral Diagram**: Wind load visualization with drift indicator
- **Detailed Results**: Tabbed view for Slab, Beams, Columns, and Lateral analysis

### FEM Analysis Section

1. **Model Preview Options**:
   - Show/hide nodes, supports, loads, labels
   - Include wind loads toggle
   - Floor elevation selector

2. **Run FEM Analysis**:
   - Click "Run FEM Analysis" to execute OpenSeesPy solver
   - View deflected shape and reactions overlay
   - Compare FEM results with hand calculations

3. **Visualization Tabs**:
   - **Plan View**: Top-down view with utilization coloring
   - **Elevation View**: Side view with deflected shape
   - **3D View**: Isometric view with all elements
   - **FEM vs Hand-Calc**: Comparison table

4. **Design Checks Panel** (v3.5):
   - Top-3 governing elements per structural type
   - Flexural check with rebar suggestions
   - Shear stress check with link sizing
   - Ductility and reinforcement ratio validation

5. **Export**: Download visualization as PNG/SVG/PDF

### AI Chat Assistant

The AI Assistant in the sidebar helps you describe buildings in natural language:

1. Type "30-storey office building with 8m x 10m bays"
2. Parameters are extracted automatically (floors, bay size, type)
3. Review the configuration preview
4. Click "Apply Extracted Parameters" to update model inputs
5. The assistant suggests what else to specify (concrete grade, bay count, etc.)

### Generating Reports

1. Scroll to the "Generate Report" section
2. Enter project metadata (name, number, engineer)
3. Optionally add AI design review commentary
4. Click "Generate HTML Report"
5. Download or preview the magazine-style report

## AI Assistant Configuration

The AI Assistant supports four providers with automatic fallback:

### Gemini 3 Flash (Default — 1M context, thinking)
```bash
# .env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-api-key-here
```
Get a free API key at [Google AI Studio](https://aistudio.google.com/apikey). Uses the native `google-genai` SDK with built-in thinking/reasoning.

### DeepSeek (Backup for Hong Kong)
```bash
# .env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your-api-key-here
```

### Grok (Backup — 2M context window)
```bash
# .env
LLM_PROVIDER=grok
GROK_API_KEY=your-api-key-here
```

### OpenRouter (Fallback — 300+ models)
```bash
# .env
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your-api-key-here
```

### Cost Tracking
```bash
# Enable cost tracking
LLM_TRACK_COSTS=true
LLM_MONTHLY_BUDGET=5.00  # USD
```

## Running Tests

Execute the test suite with pytest:

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_fem_engine.py -v

# Run with coverage report
pytest tests/ -v --cov=src

# Skip slow tests
pytest tests/ -v -m "not slow"

# Run design check tests
pytest tests/test_fem_design_checks.py tests/test_element_checks.py -v
```

## Project Structure

```
PrelimStruct/
├── app.py                    # Streamlit dashboard entry point
├── requirements.txt          # Python dependencies
├── .env.example              # Environment template
├── pytest.ini                # Pytest configuration
├── README.md                 # This file
├── src/
│   ├── core/
│   │   ├── constants.py      # Engineering constants + HK Code rebar data
│   │   ├── data_models.py    # Data classes and project structure
│   │   └── load_tables.py    # HK Code load tables
│   ├── engines/
│   │   ├── slab_engine.py    # Slab design calculations
│   │   ├── beam_engine.py    # Beam design calculations
│   │   ├── column_engine.py  # Column design calculations
│   │   ├── wind_engine.py    # Wind load and lateral analysis
│   │   ├── punching_shear.py # Punching shear checks
│   │   └── coupling_beam_engine.py  # Coupling beam design
│   ├── fem/
│   │   ├── fem_engine.py     # FEMModel class (OpenSeesPy wrapper)
│   │   ├── model_builder.py  # ProjectData → FEM model conversion
│   │   ├── solver.py         # Linear static solver
│   │   ├── visualization.py  # Plan/Elevation/3D views
│   │   ├── core_wall_geometry.py  # Core wall section generators
│   │   ├── coupling_beam.py  # Coupling beam geometry
│   │   ├── beam_trimmer.py   # Beam-core wall intersection
│   │   ├── load_combinations.py  # HK Code 2013 load combinations
│   │   ├── sls_checks.py     # Serviceability checks
│   │   ├── design_checks.py  # Element-level HK Code 2013 checks
│   │   ├── design_check_summary.py  # Top-N governing element aggregator
│   │   ├── analysis_summary.py  # FEM vs hand-calc comparison
│   │   └── design_codes/
│   │       └── hk2013.py     # HK Code 2013 ConcreteProperties extension
│   ├── ai/
│   │   ├── providers.py      # LLM providers (Gemini, DeepSeek, Grok, OpenRouter)
│   │   ├── config.py         # AI configuration management
│   │   ├── prompts.py        # System prompts and templates
│   │   ├── llm_service.py    # AIService high-level interface
│   │   ├── model_builder_assistant.py  # AI chat parameter extraction
│   │   ├── response_parser.py # Structured response parsing
│   │   ├── mesh_generator.py # Rule-based mesh generation
│   │   ├── auto_setup.py     # Smart model setup
│   │   ├── optimizer.py      # Gradient-based design optimization
│   │   └── results_interpreter.py  # FEM results interpretation
│   ├── ui/
│   │   ├── sidebar.py        # Sidebar input controls
│   │   ├── help_system.py    # Help tooltip system
│   │   ├── help_content.py   # Help text content
│   │   └── views/
│   │       └── fem_views.py  # FEM visualization + design checks panel
│   └── report/
│       └── report_generator.py  # Magazine-style HTML report
└── tests/
    ├── test_fem_engine.py    # FEM engine tests
    ├── test_model_builder.py # Model builder tests
    ├── test_ai_model_builder.py  # AI chat extraction tests
    ├── test_ai_chat_apply_flow.py  # Chat → apply flow tests
    ├── test_fem_design_checks.py  # Design check classification tests
    ├── test_element_checks.py  # Element-level check tests
    ├── test_design_checks_requires_element_forces.py  # Missing-data tests
    ├── test_fem_views_design_checks.py  # Design checks panel tests
    ├── test_coupling_beam_inputs.py  # Coupling beam dimension tests
    ├── test_ui_integration_smoke.py  # Smoke tests for UI gates
    └── ...
```

## Code Standards

### HK Code 2013 Compliance
- Deflection control per Cl 7.3.1.2
- Pattern loading factor 1.1x for beams
- Shear stress hard stops (v_max = 0.8*sqrt(fcu) or 7 MPa)
- Deep beam detection (L/d < 2.0)
- Coupling beam design per Cl 6.7
- Reinforcement ratio limits: rho_min 0.3% (beams/slabs), 0.25% (walls), 0.8% (columns)

### HK Wind Code 2019
- Reference wind pressure (q_ref) = 0.7 kPa
- Terrain categories: Open Sea, Open Country, Urban, City Centre
- Topography and exposure factors
- Drift limit: H/500

### SLS Checks (HK Code 2013 Cl 7)
- Span/depth ratio checks (Table 7.3, Cl 7.3.4)
- Deflection checks (Cl 7.3.2-7.3.3)
- Crack width checks (Cl 7.2)

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| streamlit | >=1.30.0 | Web dashboard |
| plotly | >=5.18.0 | Interactive visualizations |
| numpy | >=1.24.0 | Numerical calculations |
| pandas | >=2.0.0 | Data processing |
| jinja2 | >=3.1.0 | Report templating |
| pytest | >=7.4.0 | Testing framework |
| openseespy | >=3.5.0 | FEM solver |
| concreteproperties | >=0.5.0 | Section analysis |
| google-genai | >=1.0.0 | Gemini AI provider (primary) |
| httpx | >=0.27.0 | AI API client (backup providers) |
| python-dotenv | >=1.0.0 | Environment management |

## Version History

- **v3.5** - FEM design checks, Gemini integration, AI chat, tri mesh, I-section walls
- **v3.0** - FEM Analysis + AI Assistant (OpenSeesPy, DeepSeek, visualization)
- **v2.1** - Added moment frame system, comprehensive testing, debug phase
- **v2.0** - Lateral stability module with core wall and drift checks
- **v1.0** - Initial Python migration with gravity design engine

## License

For preliminary design purposes only. Professional engineering judgment required.

## Contributing

1. Create a feature branch
2. Add tests for new functionality
3. Ensure all tests pass (`pytest tests/ -v`)
4. Submit a pull request

---

**PrelimStruct v3.5** | FEM Design Checks + AI Chat | HK Code 2013 + Wind Code 2019
