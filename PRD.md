# PrelimStruct V3.5 - Product Requirements Document

> **Version:** 3.5
> **Status:** Planning
> **Target Users:** Structural Engineers (Hong Kong market)
> **Last Updated:** 2026-01-24

---

## Executive Summary

PrelimStruct V3.5 is a major upgrade that transforms the platform from a hybrid simplified/FEM approach to a **pure FEM-based analysis platform**. This upgrade addresses critical modeling deficiencies identified in V3.0, implements proper shell elements for walls and slabs, expands wind load cases per HK COP, and introduces an AI-assisted model builder via chat interface.

---

## Problem Statement

V3.0 introduced FEM capabilities but retained the simplified method, creating confusion and inconsistent results. Key issues include:
1. **Wall Modeling**: Walls not modeled as shell elements, limiting accuracy
2. **Coupling Beams**: Error when generating coupling beams (NoneType division)
3. **Secondary Beams**: Not appearing in FEM preview
4. **Slab Modeling**: Missing shell element representation
5. **Wind Loads**: Only 3 load combinations visible; HK COP requires 24 wind cases
6. **User Experience**: Mixed UI for simplified vs FEM creates confusion

---

## Target Audience

### Primary: Structural Engineers
- **Location**: Hong Kong
- **Experience**: 3-15 years in building design
- **Goal**: Quick preliminary checks on tall building assumptions
- **Pain Point**: Manual calculations are time-consuming and error-prone

### Secondary: Design Consultancy Firms
- **Goal**: Standardize preliminary design workflow
- **Pain Point**: Inconsistent approaches across team members

---

## Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| FEM Analysis Accuracy | >95% match with ETABS benchmark | Compare results for 5 test buildings |
| Analysis Time | <30 seconds for 30-story building | Performance benchmark |
| HK Code Compliance | 100% clause coverage | Audit against HK2013 checklist |
| User Satisfaction | >4.2/5 rating | Post-release survey |

---

## Out of Scope (V3.5)

- Seismic analysis beyond Eurocode 8 reference
- Non-linear analysis (pushover, time-history)
- Foundation design
- Connection design details
- Multi-building analysis

---

# Features Breakdown

## FEATURE 16: FEM-Only Architecture Refactor
**Priority:** P0 (MUST)
**Status:** Not Started
**Estimated Effort:** Large

### Problem
V3.0 maintains both simplified and FEM methods, creating confusion and maintenance burden. Users don't know which results to trust.

### Solution
Remove simplified method entirely. All structural analysis goes through OpenSeesPy FEM engine.

### User Stories
1. **US-16.1**: As a structural engineer, I want a single consistent analysis method so that I can trust the results without confusion.
2. **US-16.2**: As a user, I want the UI to focus on FEM workflow so that I can work efficiently without navigating deprecated features.

### Tasks

#### Task 16.1: Remove Simplified Method Code
**Priority:** P0 | **Agent:** backend-specialist

##### Sub-tasks:
- [ ] 16.1.1: Audit `src/engines/` for simplified calculation code
- [ ] 16.1.2: Remove simplified beam/column/slab calculation paths
- [ ] 16.1.3: Update `SlabEngine`, `BeamEngine`, `ColumnEngine` to use FEM results only
- [ ] 16.1.4: Remove `StructuralLayout` simplified calculation references
- [ ] 16.1.5: Update `data_models.py` to remove simplified-only fields
- [ ] 16.1.6: Update unit tests to reflect FEM-only approach

**Verification:**
- All tests pass after removal
- No references to "simplified" in calculation paths
- App runs without errors

#### Task 16.2: Update Dashboard for FEM-Only Flow
**Priority:** P0 | **Agent:** frontend-specialist

##### Sub-tasks:
- [ ] 16.2.1: Remove "Simplified Method" UI sections from `app.py`
- [ ] 16.2.2: Update sidebar to focus on FEM model inputs
- [ ] 16.2.3: Remove comparison views (FEM vs Simplified)
- [ ] 16.2.4: Update KEY METRICS to show FEM results only
- [ ] 16.2.5: Update status badges to reflect FEM analysis state

**Verification:**
- No "simplified" options visible in UI
- Dashboard shows FEM-only workflow
- Status badges update correctly after FEM analysis

#### Task 16.3: Reorganize Model Flow (OpenSees Building Pattern)
**Priority:** P1 | **Agent:** backend-specialist

##### Sub-tasks:
- [ ] 16.3.1: Study OpenSees BuildingTcl pattern from reference
- [ ] 16.3.2: Restructure `model_builder.py` to follow OpenSees conventions
- [ ] 16.3.3: Separate model definition, loads, and analysis into distinct phases
- [ ] 16.3.4: Implement proper node numbering scheme (floor-based)
- [ ] 16.3.5: Add model validation before analysis
- [ ] 16.3.6: Document new model structure in code comments

**Verification:**
- Model builds following OpenSees conventions
- Node/element numbering is consistent and floor-based
- Model passes validation checks

---

## FEATURE 17: Advanced Wall Modeling (ShellMITC4 + Plate Fiber Section)
**Priority:** P0 (MUST)
**Status:** Not Started
**Estimated Effort:** Large

### Problem
Current walls use simplified beam elements. Tall building core walls require proper shell behavior for accurate stress distribution and coupled wall effects.

### Solution
Implement ShellMITC4 shell elements with Plate Fiber Section and NDMaterial for walls per OpenSees documentation.

### References
- https://openseespydoc.readthedocs.io/en/latest/src/ShellMITC4.html
- https://opensees.berkeley.edu/wiki/index.php/Shell_Element
- https://opensees.berkeley.edu/wiki/index.php?title=Plate_Fiber_Section
- https://opensees.berkeley.edu/wiki/index.php?title=NDMaterial_Command

### User Stories
1. **US-17.1**: As a structural engineer, I want walls modeled as shell elements so that stress distribution is accurate.
2. **US-17.2**: As a user, I want to specify exact core wall centroid location so that I can model irregular building cores.
3. **US-17.3**: As a user, I want columns near core walls auto-detected and omitted so that model geometry is correct.

### Tasks

#### Task 17.1: Implement ShellMITC4 Wall Elements with Plate Fiber Section
**Priority:** P0 | **Agent:** backend-specialist

##### Sub-tasks:
- [ ] 17.1.1: Study ShellMITC4 element and Plate Fiber Section documentation
- [ ] 17.1.2: Create `WallElement` class in `src/fem/wall_element.py`
- [ ] 17.1.3: Implement NDMaterial for concrete (PlaneStressUserMaterial or similar)
- [ ] 17.1.4: Implement Plate Fiber Section with fiber layers (cover + core concrete, steel)
- [ ] 17.1.5: Create wall mesh with ShellMITC4 quad elements
- [ ] 17.1.6: Add wall-to-beam connection logic (rigid links at floor levels)
- [ ] 17.1.7: Integrate wall elements into `model_builder.py`
- [ ] 17.1.8: Add unit tests for wall element creation
- [ ] 17.1.9: Validate against reference solutions

**Verification:**
- Wall shell elements created in OpenSeesPy model
- Plate fiber section properly defines through-thickness behavior
- Stress distribution matches expected behavior
- Unit tests pass with >90% coverage

#### Task 17.2: Custom Core Wall Location Input
**Priority:** P1 | **Agent:** frontend-specialist

##### Sub-tasks:
- [ ] 17.2.1: Add "Custom" option to core wall location dropdown
- [ ] 17.2.2: Create input fields for centroid X, Y coordinates (m)
- [ ] 17.2.3: Validate centroid is within building footprint
- [ ] 17.2.4: Update `LateralInput` model with custom centroid fields
- [ ] 17.2.5: Update framing plan visualization to show custom location
- [ ] 17.2.6: Add tooltip explaining coordinate system

**Acceptance Criteria:**
```gherkin
Given I select "Custom" for core wall location
When I enter centroid X=10.0m and Y=8.0m
Then the core wall appears at that location in the framing plan
And the FEM model places the wall at those coordinates
```

**Verification:**
- Custom location option appears in dropdown
- Validation prevents invalid coordinates
- Visualization updates in real-time

#### Task 17.3: Auto-Omit Columns Near Core Walls
**Priority:** P1 | **Agent:** backend-specialist

##### Sub-tasks:
- [ ] 17.3.1: Implement proximity detection algorithm (1m threshold)
- [ ] 17.3.2: Create `detect_columns_near_core()` function in `model_builder.py`
- [ ] 17.3.3: Automatically exclude flagged columns from FEM model
- [ ] 17.3.4: Add visual indicator in framing plan for omitted columns
- [ ] 17.3.5: Allow user override to force-include columns
- [ ] 17.3.6: Log omitted columns in analysis summary

**Verification:**
- Columns within 1m of core walls are auto-omitted
- Visual indicator shows omitted columns (greyed out)
- User can override via checkbox

#### Task 17.4: Fix Coupling Beam Generation Error
**Priority:** P0 | **Agent:** debugger

##### Sub-tasks:
- [ ] 17.4.1: Reproduce NoneType division error in test case
- [ ] 17.4.2: Trace error to source in `coupling_beam.py`
- [ ] 17.4.3: Add null checks for wall geometry parameters
- [ ] 17.4.4: Fix calculation when opening dimensions are None
- [ ] 17.4.5: Add unit tests for edge cases (no openings, zero dimensions)
- [ ] 17.4.6: Verify coupling beam appears in visualization

**Verification:**
- No error when generating coupling beams
- Coupling beams display correctly for all core wall types
- Unit tests cover edge cases

---

## FEATURE 18: Secondary Beam Modeling Fix
**Priority:** P0 (MUST)
**Status:** Not Started
**Estimated Effort:** Medium

### Problem
Secondary beams not appearing in FEM preview, indicating they're not modeled.

### Solution
Fix beam generation to include secondary beams in the FEM model.

### User Stories
1. **US-18.1**: As a structural engineer, I want all beams visible in the model so that I can verify the framing layout.

### Tasks

#### Task 18.1: Debug Secondary Beam Generation
**Priority:** P0 | **Agent:** debugger

##### Sub-tasks:
- [ ] 18.1.1: Trace secondary beam creation in `model_builder.py`
- [ ] 18.1.2: Identify why secondary beams are skipped
- [ ] 18.1.3: Fix beam generation logic for Y-direction spans
- [ ] 18.1.4: Ensure secondary beams connect to primary beams
- [ ] 18.1.5: Add secondary beams to visualization

**Verification:**
- Secondary beams appear in plan view
- Secondary beams connect properly to primary beams
- Model statistics show correct beam count

#### Task 18.2: Update Beam Visualization
**Priority:** P1 | **Agent:** frontend-specialist

##### Sub-tasks:
- [ ] 18.2.1: Differentiate primary vs secondary beams in visualization (color/style)
- [ ] 18.2.2: Add legend entry for secondary beams
- [ ] 18.2.3: Show beam type in hover tooltip

**Verification:**
- Primary and secondary beams visually distinct
- Legend shows both beam types
- Tooltip displays beam type

---

## FEATURE 19: Shell Element Slab Modeling
**Priority:** P0 (MUST)
**Status:** Not Started
**Estimated Effort:** Large

### Problem
Slabs not modeled as shell elements. Need proper membrane/plate behavior for accurate load distribution.

### Solution
Implement ShellMITC4 elements with Elastic Membrane Plate Section per OpenSees documentation.

### References
- https://openseespydoc.readthedocs.io/en/latest/src/ShellMITC4.html
- https://opensees.berkeley.edu/wiki/index.php/Shell_Element
- https://opensees.berkeley.edu/wiki/index.php/Elastic_Membrane_Plate_Section

### User Stories
1. **US-19.1**: As a structural engineer, I want slabs modeled as shell elements so that load distribution is accurate.
2. **US-19.2**: As a user, I want slab boundaries defined by surrounding beams so that geometry is correct.

### Tasks

#### Task 19.1: Implement ShellMITC4 Slab Elements
**Priority:** P0 | **Agent:** backend-specialist

##### Sub-tasks:
- [ ] 19.1.1: Study ShellMITC4 element documentation
- [ ] 19.1.2: Create `SlabElement` class in `src/fem/slab_element.py`
- [ ] 19.1.3: Implement Elastic Membrane Plate Section material
- [ ] 19.1.4: Create slab mesh generation (quad elements)
- [ ] 19.1.5: Ensure slab nodes align with beam nodes (connectivity)
- [ ] 19.1.6: Integrate slab elements into `model_builder.py`
- [ ] 19.1.7: Add unit tests for slab element creation

**Verification:**
- Slab shell elements created in OpenSeesPy model
- Nodes shared between slabs and beams
- Mesh quality meets standards (aspect ratio < 5)

#### Task 19.2: Slab Panel Detection from Beams
**Priority:** P0 | **Agent:** backend-specialist

##### Sub-tasks:
- [ ] 19.2.1: Create algorithm to detect slab panels bounded by beams
- [ ] 19.2.2: Handle irregular panel shapes (L-shaped, openings)
- [ ] 19.2.3: Generate mesh for each panel independently
- [ ] 19.2.4: Handle slab openings (stairs, elevators)
- [ ] 19.2.5: Ensure continuity across panel boundaries

**Verification:**
- Slab panels correctly detected from beam layout
- Mesh generated for each panel
- No gaps or overlaps between panels

#### Task 19.3: Slab Visualization Update
**Priority:** P1 | **Agent:** frontend-specialist

##### Sub-tasks:
- [ ] 19.3.1: Add slab mesh visualization in plan view
- [ ] 19.3.2: Show slab stress contours after analysis
- [ ] 19.3.3: Add toggle to show/hide slab elements
- [ ] 19.3.4: Display slab thickness in hover tooltip

**Verification:**
- Slab mesh visible in plan view
- Stress contours display after analysis
- Toggle works correctly

---

## FEATURE 20: Enhanced Load Combination System
**Priority:** P0 (MUST)
**Status:** Not Started
**Estimated Effort:** Large

### Problem
Only 3 load combinations visible. HK COP Wind Effects requires 24 wind cases (48 combinations with +/-). UI needs improvement for managing many combinations.

### Solution
Expand load case system per HK COP with improved UI for selection and management.

### User Stories
1. **US-20.1**: As a structural engineer, I want all HK COP wind load cases so that code compliance is complete.
2. **US-20.2**: As a user, I want to easily select/deselect load combinations so that I can focus on relevant cases.
3. **US-20.3**: As a user, I want custom live load input for Class 9 "Other" so that I can handle special loading.

### Tasks

#### Task 20.1: Implement Full HK COP Wind Load Cases
**Priority:** P0 | **Agent:** backend-specialist

##### Sub-tasks:
- [ ] 20.1.1: Define all 24 HK COP wind directions/cases
- [ ] 20.1.2: Create `WindLoadCase` enum with all cases (W1-W24)
- [ ] 20.1.3: Calculate wind forces for each direction
- [ ] 20.1.4: Generate +/- combinations (48 total wind combinations)
- [ ] 20.1.5: Update `load_combinations.py` with new cases
- [ ] 20.1.6: Cite HK COP Wind Effects clause numbers

**Verification:**
- 24 wind cases defined
- 48 wind combinations generated
- Forces correct for each direction

#### Task 20.2: Define Well-Structured Load Cases
**Priority:** P0 | **Agent:** backend-specialist

##### Sub-tasks:
- [ ] 20.2.1: Create clear load case naming: DL, SDL, LL, W1-W24, E1-E3
- [ ] 20.2.2: Define Eurocode 8 seismic cases (E1, E2, E3)
- [ ] 20.2.3: Implement load case categories (GRAVITY, WIND, SEISMIC)
- [ ] 20.2.4: Generate ULS/SLS combinations per HK Code
- [ ] 20.2.5: Add combination factors per Table 2.1

**Verification:**
- All load cases properly named
- Categories correctly assigned
- Factors match HK Code Table 2.1

#### Task 20.3: Load Combination UI Overhaul
**Priority:** P0 | **Agent:** frontend-specialist

##### Sub-tasks:
- [ ] 20.3.1: Create scrollable list for load combinations
- [ ] 20.3.2: Add checkbox for each combination
- [ ] 20.3.3: Implement "Select All" and "Select None" buttons
- [ ] 20.3.4: Group combinations by category (GRAVITY/WIND/SEISMIC)
- [ ] 20.3.5: Add collapsible sections for each category
- [ ] 20.3.6: Show combination count (selected/total)
- [ ] 20.3.7: Store selection in session state

**Acceptance Criteria:**
```gherkin
Given I am on the Load Combinations section
When I click "Select All" for WIND category
Then all 48 wind combinations are selected
And the count shows "48/48 selected"
```

**Verification:**
- All combinations visible in scrollable list
- Select All/None works per category
- Selection persists in session

#### Task 20.4: Custom Live Load Input (Class 9)
**Priority:** P1 | **Agent:** frontend-specialist

##### Sub-tasks:
- [ ] 20.4.1: Add "Other" option to Live Load Class dropdown
- [ ] 20.4.2: Show kPa input field when "Other" selected
- [ ] 20.4.3: Validate input range (0.5 - 20.0 kPa)
- [ ] 20.4.4: Update `LoadInput` model with custom LL field
- [ ] 20.4.5: Apply custom LL to slab loading

**Verification:**
- "Other" option available in dropdown
- Custom kPa input appears and validates
- Custom load applied to model

#### Task 20.5: Surface Load on Slabs
**Priority:** P0 | **Agent:** backend-specialist

##### Sub-tasks:
- [ ] 20.5.1: Implement OpenSees SurfaceLoad element
- [ ] 20.5.2: Apply distributed load to slab shell elements
- [ ] 20.5.3: Display load as kPa (kN/m2) in UI
- [ ] 20.5.4: Remove nodal load approach from slabs
- [ ] 20.5.5: Verify load distribution is correct

**Reference:** https://opensees.berkeley.edu/wiki/index.php/SurfaceLoad_Element

**Verification:**
- Surface loads applied to slab elements
- Load displayed in kPa units
- Total load equals expected value

#### Task 20.6: Remove Analysis Load Pattern
**Priority:** P1 | **Agent:** backend-specialist

##### Sub-tasks:
- [ ] 20.6.1: Remove "Analysis" load pattern from model
- [ ] 20.6.2: Add "Loading Pattern Factor" input for LL scaling
- [ ] 20.6.3: Apply factor to live load in combinations
- [ ] 20.6.4: Update documentation for factor usage

**Verification:**
- No "Analysis" pattern in model
- Factor input works and scales LL correctly

---

## FEATURE 21: UI/UX Enhancement
**Priority:** P1 (SHOULD)
**Status:** Not Started
**Estimated Effort:** Large

### Problem
Current UI has mixed layouts, visualization controls above views, and limited display options. Need cleaner workflow for FEM-focused analysis.

### User Stories
1. **US-21.1**: As a user, I want FEM views prominently displayed so that I can see results immediately.
2. **US-21.2**: As a user, I want to control what's displayed (loads, deformation, reactions) so that I can focus on specific results.
3. **US-21.3**: As a user, I want to adjust view scales independently so that I can see details clearly.
4. **US-21.4**: As a structural engineer, I want to view and export reaction forces for all base nodes and load cases so that I can verify foundation design loads.

### Tasks

#### Task 21.1: Relocate FEM Views Section
**Priority:** P1 | **Agent:** frontend-specialist

##### Sub-tasks:
- [ ] 21.1.1: Move FEM Views section below KEY METRICS
- [ ] 21.1.2: Move visualization legends to bottom of views
- [ ] 21.1.3: Arrange view buttons: Plan (Left), Elevation (Center), 3D (Right)
- [ ] 21.1.4: Add floor selection dropdown next to Plan View button
- [ ] 21.1.5: Format floor labels as "G/F (+0.00)", "1/F (+4.00)", etc.

**Verification:**
- FEM Views below KEY METRICS
- Legends at bottom
- Floor selector properly formatted

#### Task 21.2: Conditional Utilization Display
**Priority:** P1 | **Agent:** frontend-specialist

##### Sub-tasks:
- [ ] 21.2.1: Hide utilization bars until FEM analysis complete
- [ ] 21.2.2: Hide element colors until analysis complete
- [ ] 21.2.3: Reduce utilization bar height to 50% of current
- [ ] 21.2.4: Add "Run Analysis" prompt when results not available

**Verification:**
- No utilization shown before analysis
- Bars appear after analysis completes
- Bar height is thinner

#### Task 21.3: Independent Axis Scale Controls
**Priority:** P1 | **Agent:** frontend-specialist

##### Sub-tasks:
- [ ] 21.3.1: Add X-axis scale slider (0.5x - 2.0x)
- [ ] 21.3.2: Add Y-axis scale slider (0.5x - 2.0x)
- [ ] 21.3.3: Update Plotly figure with scaled axes
- [ ] 21.3.4: Maintain aspect ratio option (checkbox)

**Verification:**
- X and Y scales adjustable independently
- View updates in real-time
- Aspect ratio lock works

#### Task 21.4: Calculation Tables Toggle
**Priority:** P1 | **Agent:** frontend-specialist

##### Sub-tasks:
- [ ] 21.4.1: Create collapsible "Calculations" section
- [ ] 21.4.2: Show element capacity checks (HKConcreteProperties)
- [ ] 21.4.3: Organize tables by floor
- [ ] 21.4.4: Include columns: Element, Demand, Capacity, Utilization, Status
- [ ] 21.4.5: Add export to CSV option

**Verification:**
- Calculation tables toggle open/closed
- Tables organized by floor
- Export works correctly

#### Task 21.5: Switch to opsvis from vfo
**Priority:** P1 | **Agent:** backend-specialist

##### Sub-tasks:
- [ ] 21.5.1: Remove vfo imports and usage
- [ ] 21.5.2: Implement opsvis data extraction
- [ ] 21.5.3: Update visualization functions to use opsvis format
- [ ] 21.5.4: Update requirements.txt (remove vfo, ensure opsvis)

**Reference:** https://opsvis.readthedocs.io/

**Verification:**
- vfo completely removed
- opsvis provides visualization data
- All views work correctly

#### Task 21.6: Display Options Panel
**Priority:** P1 | **Agent:** frontend-specialist

##### Sub-tasks:
- [ ] 21.6.1: Create display options panel BELOW FEM views
- [ ] 21.6.2: Add toggle: Show Loads (with opsvis plot_load)
- [ ] 21.6.3: Add toggle: Show Deformed Shape (plot_defo)
- [ ] 21.6.4: Add toggle: Show Reactions (plot_reactions)
- [ ] 21.6.5: Add force diagram dropdown: N, Vy, Vz, My, Mz, T
- [ ] 21.6.6: Add scale factor slider for deformed shape

**References:**
- https://opsvis.readthedocs.io/en/stable/plot_load.html
- https://opsvis.readthedocs.io/en/stable/plot_defo.html
- https://opsvis.readthedocs.io/en/stable/plot_reactions.html
- https://opsvis.readthedocs.io/en/stable/section_force_diagram_3d.html

**Verification:**
- All toggles work correctly
- Force diagrams display selected type
- Scale factor adjusts deformed shape

#### Task 21.7: Reaction Table View and Export
**Priority:** P0 | **Agent:** frontend-specialist

##### Sub-tasks:
- [ ] 21.7.1: Create Reaction Table section in results area
- [ ] 21.7.2: Extract reaction forces from all support nodes at base
- [ ] 21.7.3: Display reactions per node (Fx, Fy, Fz, Mx, My, Mz)
- [ ] 21.7.4: Show reactions for all individual load cases (DL, SDL, LL, W1-W24, E1-E3)
- [ ] 21.7.5: Show reactions for all load combinations (ULS, SLS)
- [ ] 21.7.6: Add load case/combination selector dropdown
- [ ] 21.7.7: Calculate total reactions (sum of all nodes) per load case
- [ ] 21.7.8: Implement export to CSV functionality
- [ ] 21.7.9: Implement export to Excel functionality (.xlsx)
- [ ] 21.7.10: Add "Copy to Clipboard" button for quick data sharing

**Acceptance Criteria:**
```gherkin
Given the FEM analysis is complete
When I select "ULS_GRAVITY_1" from the load combination dropdown
Then I see a table with all base node reactions
And each row shows Node ID, Fx, Fy, Fz, Mx, My, Mz
And I can export the table to CSV or Excel
```

**Verification:**
- Reaction table displays all base nodes
- All load cases and combinations selectable
- CSV/Excel export produces correct data
- Total reactions calculated correctly

---

## FEATURE 22: AI Chat Assistant for Model Building
**Priority:** P1 (SHOULD)
**Status:** Not Started
**Estimated Effort:** Large

### Problem
Users must manually configure all model parameters. AI could guide and automate model setup from natural language.

### Solution
Add AI chat interface above Project Settings that helps users build models through conversation.

### User Stories
1. **US-22.1**: As a user, I want to describe my building in natural language so that AI can configure the model.
2. **US-22.2**: As a user, I want AI to suggest optimal configurations so that I can learn best practices.

### Tasks

#### Task 22.1: AI Chat Interface Component
**Priority:** P1 | **Agent:** frontend-specialist

##### Sub-tasks:
- [ ] 22.1.1: Create chat container above Project Settings
- [ ] 22.1.2: Implement message history display
- [ ] 22.1.3: Add text input with send button
- [ ] 22.1.4: Style chat bubbles (user vs AI)
- [ ] 22.1.5: Add typing indicator during AI response
- [ ] 22.1.6: Implement auto-scroll to latest message

**Verification:**
- Chat container appears above Project Settings
- Messages display correctly
- Send button triggers AI response

#### Task 22.2: AI Model Builder Backend
**Priority:** P1 | **Agent:** backend-specialist

##### Sub-tasks:
- [ ] 22.2.1: Create `ModelBuilderAssistant` class in `src/ai/`
- [ ] 22.2.2: Design prompts for building parameter extraction
- [ ] 22.2.3: Implement intent detection (describe building, ask question, modify parameter)
- [ ] 22.2.4: Create parameter validation and suggestion logic
- [ ] 22.2.5: Generate configuration from conversation
- [ ] 22.2.6: Integrate with existing `AIService`

**Verification:**
- AI extracts parameters from natural language
- Suggestions are valid and code-compliant
- Configuration generates correctly

#### Task 22.3: Model Configuration from Chat
**Priority:** P1 | **Agent:** backend-specialist

##### Sub-tasks:
- [ ] 22.3.1: Map extracted parameters to `ProjectData` fields
- [ ] 22.3.2: Apply configuration to UI inputs
- [ ] 22.3.3: Preview configuration before applying
- [ ] 22.3.4: Allow user confirmation/modification
- [ ] 22.3.5: Handle partial configurations (fill defaults)

**Verification:**
- AI configuration populates UI fields
- User can preview and confirm
- Partial configs handled gracefully

---

## FEATURE 23: Testing & Quality Assurance
**Priority:** P0 (MUST)
**Status:** Not Started
**Estimated Effort:** Medium

### Problem
New features need comprehensive testing to ensure reliability and code compliance.

### Tasks

#### Task 23.1: Unit Tests for New Features
**Priority:** P0 | **Agent:** test-engineer

##### Sub-tasks:
- [ ] 23.1.1: Tests for SFI-MVLEM-3D wall elements
- [ ] 23.1.2: Tests for ShellMITC4 slab elements
- [ ] 23.1.3: Tests for wind load case generation (24 cases)
- [ ] 23.1.4: Tests for load combination UI logic
- [ ] 23.1.5: Tests for AI model builder

**Verification:**
- All new modules have >80% test coverage
- All tests pass

#### Task 23.2: Integration Tests
**Priority:** P0 | **Agent:** test-engineer

##### Sub-tasks:
- [ ] 23.2.1: End-to-end model building test
- [ ] 23.2.2: Analysis workflow test (build -> analyze -> results)
- [ ] 23.2.3: Report generation with new features
- [ ] 23.2.4: AI chat integration test

**Verification:**
- Integration tests pass
- Full workflow completes without errors

#### Task 23.3: Benchmark Validation
**Priority:** P1 | **Agent:** test-engineer

##### Sub-tasks:
- [ ] 23.3.1: Create benchmark models (3 test buildings)
- [ ] 23.3.2: Compare results with ETABS/SAP2000
- [ ] 23.3.3: Document discrepancies and acceptable tolerances
- [ ] 23.3.4: Create validation report

**Verification:**
- Results within 5% of benchmark for displacements
- Results within 10% for member forces

---

# Implementation Phases

## Phase 1: Core Fixes (Features 16-18)
**Duration:** 2 weeks
**Focus:** Remove simplified method, fix critical bugs

| Week | Tasks |
|------|-------|
| 1 | Task 16.1, 16.2, 17.4, 18.1 |
| 2 | Task 16.3, 17.3, 18.2 |

**Milestone:** FEM-only architecture working with all beams visible

## Phase 2: Shell Elements (Features 17, 19)
**Duration:** 3 weeks
**Focus:** Implement proper wall and slab modeling

| Week | Tasks |
|------|-------|
| 3 | Task 17.1, 17.2 |
| 4 | Task 19.1, 19.2 |
| 5 | Task 19.3 |

**Milestone:** Walls and slabs as shell elements

## Phase 3: Load System (Feature 20)
**Duration:** 2 weeks
**Focus:** Full HK COP load combinations

| Week | Tasks |
|------|-------|
| 6 | Task 20.1, 20.2, 20.5 |
| 7 | Task 20.3, 20.4, 20.6 |

**Milestone:** Complete load combination system

## Phase 4: UI/UX & AI (Features 21-22)
**Duration:** 3 weeks
**Focus:** Enhanced user experience

| Week | Tasks |
|------|-------|
| 8 | Task 21.1, 21.2, 21.3 |
| 9 | Task 21.4, 21.5, 21.6 |
| 10 | Task 22.1, 22.2, 22.3 |

**Milestone:** Complete UI overhaul with AI chat

## Phase 5: Testing (Feature 23)
**Duration:** 1 week
**Focus:** Quality assurance

| Week | Tasks |
|------|-------|
| 11 | Task 23.1, 23.2, 23.3 |

**Milestone:** All tests pass, validation complete

---

# Agent Assignments

| Feature | Primary Agent | Supporting Agents |
|---------|---------------|-------------------|
| F16: FEM-Only Refactor | backend-specialist | frontend-specialist |
| F17: Wall Modeling | backend-specialist | debugger, frontend-specialist |
| F18: Secondary Beams | debugger | frontend-specialist |
| F19: Slab Modeling | backend-specialist | frontend-specialist |
| F20: Load Combinations | backend-specialist | frontend-specialist |
| F21: UI/UX Enhancement | frontend-specialist | backend-specialist |
| F22: AI Chat | backend-specialist | frontend-specialist |
| F23: Testing | test-engineer | - |

---

# Appendix

## A. HK Code References

| Feature | HK Code Clause |
|---------|----------------|
| Load Combinations | Table 2.1, Cl 2.3 |
| Wind Loads | Code of Practice on Wind Effects in Hong Kong 2019 |
| Material Properties | Cl 3.1, 3.2 |
| Stress-Strain | Cl 6.1.2.4 |
| Deflection Limits | Cl 7.3.1.2 |
| Drift Limits | Cl 7.3.2 |

## B. OpenSees Element References

| Element/Section | Documentation |
|-----------------|---------------|
| ShellMITC4 | https://openseespydoc.readthedocs.io/en/latest/src/ShellMITC4.html |
| Shell Element (wiki) | https://opensees.berkeley.edu/wiki/index.php/Shell_Element |
| Plate Fiber Section | https://opensees.berkeley.edu/wiki/index.php?title=Plate_Fiber_Section |
| NDMaterial Command | https://opensees.berkeley.edu/wiki/index.php?title=NDMaterial_Command |
| SurfaceLoad | https://opensees.berkeley.edu/wiki/index.php/SurfaceLoad_Element |

## C. Task Count Summary

| Feature | Tasks | Sub-tasks | Total Work Items |
|---------|-------|-----------|------------------|
| F16 | 3 | 17 | 20 |
| F17 | 4 | 23 | 27 |
| F18 | 2 | 8 | 10 |
| F19 | 3 | 14 | 17 |
| F20 | 6 | 24 | 30 |
| F21 | 7 | 36 | 43 |
| F22 | 3 | 16 | 19 |
| F23 | 3 | 12 | 15 |
| **TOTAL** | **31** | **150** | **181** |

---

*Document generated by Product Manager & Project Planner agents*
*PrelimStruct V3.5 Planning - 2026-01-24*
