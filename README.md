# PrelimStruct

AI-Assisted Preliminary Structural Design Platform for Hong Kong Code compliance.

A Python-powered structural engineering tool featuring rigorous HK Code 2013 compliance, integrated lateral stability checks (HK Wind Code 2019), and professional "Magazine-Style" HTML report generation.

## Features

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

1. **Quick Presets**: Pre-configured building types (Residential, Office, Retail, Car Park, Plant Room)
2. **Geometry**: Bay dimensions, number of floors, story height
3. **Loading**: Live load class selection from HK Code Table 3.1/3.2
4. **Materials**: Concrete grades for slabs, beams, and columns
5. **Lateral System**: Terrain category, core wall dimensions and location
6. **Load Combinations**: Toggle between ULS Gravity, ULS Wind, and SLS

### Main Dashboard

- **Status Badges**: Real-time pass/warn/fail indicators for each element
- **Key Metrics**: Live load, design load, concrete volume, carbon intensity
- **Framing Plan**: Interactive Plotly visualization with reactive colors
- **Lateral Diagram**: Wind load visualization with drift indicator
- **Detailed Results**: Tabbed view for Slab, Beams, Columns, and Lateral analysis

### Generating Reports

1. Scroll to the "Generate Report" section
2. Enter project metadata (name, number, engineer)
3. Optionally add AI design review commentary
4. Click "Generate HTML Report"
5. Download or preview the magazine-style report

## Running Tests

Execute the test suite with pytest:

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_feature5.py -v

# Run with coverage report
pytest tests/ -v --cov=src
```

## Project Structure

```
PrelimStruct/
├── app.py                    # Streamlit dashboard entry point
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── PrelimStruct.md           # Implementation roadmap
├── progress.txt              # Development progress tracker
├── src/
│   ├── core/
│   │   ├── constants.py      # Engineering constants
│   │   ├── data_models.py    # Data classes and project structure
│   │   └── load_tables.py    # HK Code load tables
│   ├── engines/
│   │   ├── slab_engine.py    # Slab design calculations
│   │   ├── beam_engine.py    # Beam design calculations
│   │   ├── column_engine.py  # Column design calculations
│   │   ├── wind_engine.py    # Wind load and lateral analysis
│   │   └── punching_shear.py # Punching shear checks
│   └── report/
│       └── report_generator.py  # Magazine-style HTML report
└── tests/
    ├── test_feature1.py      # Engineering core tests
    ├── test_feature2.py      # Lateral stability tests
    ├── test_dashboard.py     # Dashboard integration tests
    ├── test_moment_frame.py  # Moment frame system tests
    ├── test_report_generator.py  # Report generation tests
    └── test_feature5.py      # Debug & integration tests
```

## Code Standards

### HK Code 2013 Compliance
- Deflection control per Cl 7.3.1.2
- Pattern loading factor 1.1x for beams
- Shear stress hard stops (v_max = 0.8*sqrt(fcu) or 7 MPa)
- Deep beam detection (L/d < 2.0)

### HK Wind Code 2019
- Reference wind pressure (q_ref) = 0.7 kPa
- Terrain categories: Open Sea, Open Country, Urban, City Centre
- Topography and exposure factors
- Drift limit: H/500

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| streamlit | >=1.30.0 | Web dashboard |
| plotly | >=5.18.0 | Interactive visualizations |
| numpy | >=1.24.0 | Numerical calculations |
| pandas | >=2.0.0 | Data processing |
| jinja2 | >=3.1.0 | Report templating |
| pytest | >=7.4.0 | Testing framework |

## Version History

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

**PrelimStruct v2.1** | HK Code 2013 + Wind Code 2019 | For preliminary design only
