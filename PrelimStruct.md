# AI-Assisted Preliminary Structural Platform: Implementation Roadmap
**Version:** 2.1 (Added Intermediate Debug Phase)  
**Date:** January 2026  
**Objective:** To build a robust, Python-powered preliminary structural design platform with rigorous HK Code compliance, integrated lateral stability checks, and a "Magazine-Style" automated report.

---

## Phase 1: The Engineering Core (Python Migration & Upgrade)
*Goal: Port legacy logic to Python and "tighten" engineering rules for professional reliability.*

### 1.1 Data Structure & Inputs
* **Action:** Create a `ProjectData` class in Python to centralize all inputs.
* **Attributes:**
    * **Geometry:** `BayX`, `BayY`, `Floors`, `StoryHeight`.
    * **Loads:** `LiveLoad` (mapped from Code Table 3.1/3.2), `DeadLoad` (Superimposed).
    * **Materials:** `fcu_slab`, `fcu_beam`, `fcu_col` (Grades 35-60), `fy` (500), `fyv` (250).
    * **Logic Port:** Convert the Javascript `subDivisions` object (Live Load lookup) into a Python dictionary.

### 1.2 Gravity Engine (The "Rigorous" Upgrade)
* **Slabs (HK Code Cl 7.3.1.2):**
    * Replace simple span/depth constants.
    * Implement **Modification Factors** ($M_{tension}$) based on service stress ($f_s \approx \frac{2}{3}f_y$).
    * Output: Required effective depth ($d_{req}$) accounting for deflection control.
* **Beams (HK Code Cl 6.1):**
    * **Pattern Loading:** Apply a **1.1x magnification factor** to static moments ($M_{design} = 1.1 \times \frac{wL^2}{8}$) to simulate alternate span loading.
    * **Shear "Hard Stop":** Explicitly calculate shear stress $v = \frac{V}{bd}$.
        * **Check:** If $v > v_{max}$ (approx. $0.8\sqrt{f_{cu}}$ or 7MPa), trigger a "Resize Needed" flag immediately. (Do not propose links for over-stressed concrete).
    * **Deep Beam Filter:** If $Span/Depth < 2.0$, output "Deep Beam (STM Required)" and invalidate beam theory results.
* **Columns:**
    * **Load Accumulation:** $N = Area \times Floors \times (1.4G_k + 1.6Q_k)$.
    * **Eccentricity Toggle:**
        * *Interior:* Axial focus.
        * *Edge/Corner:* Add nominal moment $M_{min} = N \times 0.05h$ (or reaction eccentricity).

### 1.3 Lateral Stability Module (HK Wind Code 2019)
* **Action:** Implement `calculate_wind_hk2019(height, width, depth, terrain_type)`.
* **Physics:**
    * Determine **Reference Wind Pressure ($q_{ref}$)**.
    * Apply **Topography ($S_a$)** and **Exposure ($S_d$)** factors based on height.
    * **Output:** Total Base Shear ($V_{wind}$) and Overturning Moment ($M_{wind}$) using the Static Method.

### 1.4 Core Wall Module
* **Action:** Implement `check_core_wall(core_dim_x, core_dim_y, thickness, M_wind)`.
* **Physics:** Treat the core as a hollow cantilever tube.
* **Checks:**
    * **Max Compression:** $\frac{P}{A} + \frac{M_{wind}y}{I} < 0.45f_{cu}$.
    * **Tension Uplift:** Check if $\frac{P}{A} - \frac{M_{wind}y}{I} < 0$ (Requires tension piles).
    * **Shear:** Simplified stress check $\frac{1.5V}{A_{shear}} < 0.8\sqrt{f_{cu}}$.

---

## Phase 2: The Interface (Streamlit Dashboard)
*Goal: A modern, responsive dashboard replacing the static HTML form.*

### 2.1 Layout & Controls
* **Framework:** Streamlit (Python).
* **Sidebar:** Grouped inputs (Geometry, Loading, Materials).
* **Main Stage:**
    * **Real-time Badges:** "Pill" indicators for Slab, Beam, Column, Core status (Green=Pass, Red=Fail).
    * **Carbon Estimator:** Live display of $kgCO_2e/m^2$ based on volume and concrete grade.

### 2.2 Interactive Visualization
* **Library:** `streamlit-drawable-canvas` or `Plotly`.
* **Features:**
    * Draw the framing grid dynamically.
    * **Reactive Colors:** Elements turn Red instantly if utilization > 1.0.
    * **Core Representation:** Blue box indicating core position relative to the grid.

---

## Phase 3: The "Magazine" Report (HTML/CSS Generation)
*Goal: High-design, brochure-style output (No "default report" look).*

### 3.1 The Template Strategy
* **Tech Stack:** **Jinja2** (Python templating) + **CSS Grid**.
* **Typography:** Embed **Aileron** font (Base64 encoded) for modern, clean headers.
* **Assets:** SVG Icons for concrete, steel, wind, warning, and checkmarks (Color palette: Slate Blue, Vibrant Teal, Alert Red).
* **Formatting:** Clean numbers (no citation markers), absolute positioning for visual hierarchy.

### 3.2 Report Pages
* **Page 1 (Gravity Scheme):**
    * **Hero Section:** Project Title & Key Metrics (Concrete Volume, Carbon).
    * **Framing Plan:** SVG export of the grid.
    * **Element Table:** Clean rows with status badges for Beam/Slab/Column.
* **Page 2 (Stability & Summary):**
    * **Lateral Diagram:** Visualization of Wind Load vs. Core Wall.
    * **AI Design Review Placeholder:** Empty quote block ready for Phase 5.

---

## Phase 4: Intermediate Debug & Integration Testing
*Goal: Stabilize the platform logic and visuals BEFORE adding AI complexity.*

### 4.1 Data Pipeline Verification
* **Objective:** Ensure inputs flow correctly from Streamlit $\to$ Python Logic $\to$ HTML Report.
* **Tasks:**
    * Trace a specific value (e.g., "Live Load = 5kPa") through the entire chain to ensure no floating-point errors or rounding issues.
    * Verify that changing a "Material Grade" slider updates the "Carbon Estimate" instantly.

### 4.2 Engineering Logic Stress Test
* **Objective:** Verify "Hard Stops" and Error Handling.
* **Tasks:**
    * **Input Impossible Geometry:** Set Beam Width > Column Width. Ensure the UI flags a warning.
    * **Force Failures:** Input 20m spans with 300mm depth. Ensure the code returns a clear "Section Too Small" error, not a crash or infinite loop.
    * **Lateral Stability Check:** Input a 0m core thickness. Ensure the "Tension Uplift" warning triggers correctly.

### 4.3 Visual Regression Testing
* **Objective:** Ensure the "Magazine Look" renders correctly across environments.
* **Tasks:**
    * Check HTML Report layout on standard A4 PDF export settings.
    * Verify that the CSS Grid does not break when data strings are long (e.g., "1200x1200mm" fitting in the column width).
    * Check SVG Icon alignment and font rendering (Aileron) in Chrome and Edge.

---

## Phase 5: The AI Design Director
*Goal: Intelligent, automated commentary to validate the scheme.*

### 5.1 The Prompt Engineering
* **Trigger:** Executed only upon "Generate Report" click.
* **System Prompt:**
    > "Act as a Senior Structural Engineer in Hong Kong. Review the following preliminary metrics: [JSON Data].
    > 1. Critique structural efficiency (e.g., 'Spans > 10m, consider PT').
    > 2. Flag constructability risks (e.g., 'Beam width > Column width').
    > 3. Suggest one sustainability improvement.
    > Keep tone professional. Max 150 words."

### 5.2 Integration
* **API:** Connect to **OpenAI (GPT-4o)** or **DeepSeek API**.
* **Output:** Inject text response into the "Design Review" quote block in the HTML report (verified in Phase 3).

---

## Phase 6: Final Validation & QA
*Goal: Final polish and "Sanity Check" before deployment.*

### 6.1 Benchmark Comparisons
* **Action:** Run 3 standard textbook cases (Short span, Long span, High-rise) through the platform.
* **Verify:** Compare results against manual calculations to certify accuracy.

### 6.2 Deliverable
* **Final Output:** A standalone Python application (locally hosted or deployed) generating PDF-ready HTML reports.