"""
Magazine-Style Report Generator for PrelimStruct

Generates professional HTML reports with:
- CSS Grid layout for magazine-style presentation
- SVG icons for visual elements
- Embedded fonts for consistent typography
- Multi-page structure (Gravity, Stability, Assumptions, FEM Analysis)
- FEM results integration with AI interpretation
"""

import base64
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from jinja2 import Environment, BaseLoader, select_autoescape

# Import project data models
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.data_models import ProjectData, LoadCombination
from src.core.constants import (
    GAMMA_G, GAMMA_Q, GAMMA_W, DRIFT_LIMIT,
    CARBON_FACTORS, CONCRETE_DENSITY
)

# Import AI results interpreter (for FEM integration)
try:
    from src.ai.results_interpreter import (
        ResultsInterpretation,
        FEMResultsSummary,
        SimplifiedResultsSummary,
    )
    HAS_AI_INTERPRETER = True
except ImportError:
    HAS_AI_INTERPRETER = False


# =============================================================================
# SVG ICONS (Embedded)
# =============================================================================

SVG_ICONS = {
    'concrete': '''<svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
        <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V5h14v14z"/>
        <path d="M7 7h4v4H7zM13 7h4v4h-4zM7 13h4v4H7zM13 13h4v4h-4z" opacity="0.5"/>
    </svg>''',

    'steel': '''<svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
        <path d="M12 2L2 7v10l10 5 10-5V7L12 2zm0 2.18l6.9 3.45L12 11.09 5.1 7.64 12 4.18zM4 8.82l7 3.5v7.36l-7-3.5V8.82zm9 10.86v-7.36l7-3.5v7.36l-7 3.5z"/>
    </svg>''',

    'wind': '''<svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
        <path d="M14.5 17c0 1.65-1.35 3-3 3s-3-1.35-3-3h2c0 .55.45 1 1 1s1-.45 1-1-.45-1-1-1H2v-2h9.5c1.65 0 3 1.35 3 3z"/>
        <path d="M19 6.5C19 4.57 17.43 3 15.5 3S12 4.57 12 6.5h2c0-.83.67-1.5 1.5-1.5s1.5.67 1.5 1.5S16.33 8 15.5 8H2v2h13.5c1.93 0 3.5-1.57 3.5-3.5z"/>
        <path d="M18.5 11H2v2h16.5c.83 0 1.5.67 1.5 1.5s-.67 1.5-1.5 1.5v2c1.93 0 3.5-1.57 3.5-3.5s-1.57-3.5-3.5-3.5z"/>
    </svg>''',

    'check': '''<svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
    </svg>''',

    'warning': '''<svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
        <path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/>
    </svg>''',

    'error': '''<svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
    </svg>''',

    'building': '''<svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
        <path d="M15 11V5l-3-3-3 3v2H3v14h18V11h-6zm-8 8H5v-2h2v2zm0-4H5v-2h2v2zm0-4H5V9h2v2zm6 8h-2v-2h2v2zm0-4h-2v-2h2v2zm0-4h-2V9h2v2zm0-4h-2V5h2v2zm6 12h-2v-2h2v2zm0-4h-2v-2h2v2z"/>
    </svg>''',

    'carbon': '''<svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
    </svg>''',

    'ruler': '''<svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
        <path d="M21 6H3c-1.1 0-2 .9-2 2v8c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm0 10H3V8h2v4h2V8h2v4h2V8h2v4h2V8h2v4h2V8h2v8z"/>
    </svg>''',

    'core': '''<svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
        <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V5h14v14z"/>
        <rect x="8" y="8" width="8" height="8" fill="currentColor" opacity="0.3"/>
    </svg>'''
}


# =============================================================================
# CSS STYLES (Magazine-Style)
# =============================================================================

CSS_STYLES = '''
/* ============================================
   PrelimStruct Magazine-Style Report
   ============================================ */

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

:root {
    /* Color Palette */
    --primary: #1a365d;
    --primary-light: #2c5282;
    --secondary: #2d3748;
    --accent: #3182ce;
    --success: #38a169;
    --warning: #d69e2e;
    --danger: #e53e3e;
    --light: #f7fafc;
    --dark: #1a202c;
    --gray-100: #f7fafc;
    --gray-200: #edf2f7;
    --gray-300: #e2e8f0;
    --gray-400: #cbd5e0;
    --gray-500: #a0aec0;
    --gray-600: #718096;
    --gray-700: #4a5568;
    --gray-800: #2d3748;

    /* Typography */
    --font-primary: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    --font-mono: 'SF Mono', 'Fira Code', monospace;

    /* Spacing */
    --spacing-xs: 0.25rem;
    --spacing-sm: 0.5rem;
    --spacing-md: 1rem;
    --spacing-lg: 1.5rem;
    --spacing-xl: 2rem;
    --spacing-2xl: 3rem;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: var(--font-primary);
    font-size: 11pt;
    line-height: 1.6;
    color: var(--dark);
    background: white;
}

/* Page Layout for Print */
@page {
    size: A4;
    margin: 15mm;
}

.page {
    width: 100%;
    max-width: 210mm;
    margin: 0 auto;
    padding: var(--spacing-xl);
    page-break-after: always;
    background: white;
}

.page:last-child {
    page-break-after: avoid;
}

/* ============================================
   HEADER & HERO SECTION
   ============================================ */

.report-header {
    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
    color: white;
    padding: var(--spacing-2xl);
    border-radius: 8px;
    margin-bottom: var(--spacing-xl);
    position: relative;
    overflow: hidden;
}

.report-header::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -20%;
    width: 60%;
    height: 200%;
    background: rgba(255,255,255,0.05);
    transform: rotate(15deg);
}

.report-header h1 {
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: var(--spacing-sm);
    position: relative;
}

.report-header .subtitle {
    font-size: 1.1rem;
    font-weight: 300;
    opacity: 0.9;
    margin-bottom: var(--spacing-lg);
}

.header-meta {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: var(--spacing-md);
    margin-top: var(--spacing-lg);
    padding-top: var(--spacing-lg);
    border-top: 1px solid rgba(255,255,255,0.2);
}

.header-meta-item {
    text-align: center;
}

.header-meta-item .label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    opacity: 0.7;
    margin-bottom: var(--spacing-xs);
}

.header-meta-item .value {
    font-size: 1rem;
    font-weight: 600;
}

/* ============================================
   STATUS BADGES
   ============================================ */

.status-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: var(--spacing-md);
    margin-bottom: var(--spacing-xl);
}

.status-card {
    background: var(--gray-100);
    border-radius: 8px;
    padding: var(--spacing-md);
    text-align: center;
    border: 2px solid transparent;
    transition: all 0.2s ease;
}

.status-card.pass {
    border-color: var(--success);
    background: #f0fff4;
}

.status-card.warn {
    border-color: var(--warning);
    background: #fffff0;
}

.status-card.fail {
    border-color: var(--danger);
    background: #fff5f5;
}

.status-card .icon {
    width: 32px;
    height: 32px;
    margin: 0 auto var(--spacing-sm);
}

.status-card.pass .icon { color: var(--success); }
.status-card.warn .icon { color: var(--warning); }
.status-card.fail .icon { color: var(--danger); }

.status-card .element-name {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--gray-700);
    margin-bottom: var(--spacing-xs);
}

.status-card .utilization {
    font-size: 1.25rem;
    font-weight: 700;
}

.status-card.pass .utilization { color: var(--success); }
.status-card.warn .utilization { color: var(--warning); }
.status-card.fail .utilization { color: var(--danger); }

/* ============================================
   KEY METRICS SECTION
   ============================================ */

.metrics-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: var(--spacing-lg);
    margin-bottom: var(--spacing-xl);
}

.metric-card {
    background: white;
    border: 1px solid var(--gray-300);
    border-radius: 8px;
    padding: var(--spacing-lg);
    position: relative;
}

.metric-card .icon {
    position: absolute;
    top: var(--spacing-md);
    right: var(--spacing-md);
    width: 24px;
    height: 24px;
    color: var(--gray-400);
}

.metric-card .label {
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--gray-600);
    margin-bottom: var(--spacing-xs);
}

.metric-card .value {
    font-size: 1.75rem;
    font-weight: 700;
    color: var(--primary);
}

.metric-card .unit {
    font-size: 0.9rem;
    font-weight: 400;
    color: var(--gray-500);
    margin-left: var(--spacing-xs);
}

/* ============================================
   ELEMENT TABLES
   ============================================ */

.section-title {
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--primary);
    margin-bottom: var(--spacing-md);
    padding-bottom: var(--spacing-sm);
    border-bottom: 2px solid var(--accent);
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
}

.section-title .icon {
    width: 24px;
    height: 24px;
    color: var(--accent);
}

.element-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: var(--spacing-xl);
    font-size: 0.9rem;
}

.element-table th {
    background: var(--gray-100);
    padding: var(--spacing-sm) var(--spacing-md);
    text-align: left;
    font-weight: 600;
    color: var(--gray-700);
    border-bottom: 2px solid var(--gray-300);
}

.element-table td {
    padding: var(--spacing-sm) var(--spacing-md);
    border-bottom: 1px solid var(--gray-200);
}

.element-table tr:hover {
    background: var(--gray-100);
}

.element-table .number {
    font-family: var(--font-mono);
    text-align: right;
}

.element-table .status-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
}

.status-badge.pass {
    background: #c6f6d5;
    color: #276749;
}

.status-badge.warn {
    background: #fefcbf;
    color: #975a16;
}

.status-badge.fail {
    background: #fed7d7;
    color: #c53030;
}

/* ============================================
   FRAMING DIAGRAM
   ============================================ */

.diagram-container {
    background: var(--gray-100);
    border-radius: 8px;
    padding: var(--spacing-lg);
    margin-bottom: var(--spacing-xl);
}

.diagram-container svg {
    width: 100%;
    max-height: 300px;
}

.diagram-title {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--gray-600);
    text-align: center;
    margin-bottom: var(--spacing-md);
}

/* ============================================
   LATERAL SYSTEM SECTION
   ============================================ */

.lateral-summary {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--spacing-xl);
    margin-bottom: var(--spacing-xl);
}

.lateral-card {
    background: white;
    border: 1px solid var(--gray-300);
    border-radius: 8px;
    padding: var(--spacing-lg);
}

.lateral-card h3 {
    font-size: 1rem;
    font-weight: 600;
    color: var(--primary);
    margin-bottom: var(--spacing-md);
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
}

.lateral-card h3 .icon {
    width: 20px;
    height: 20px;
    color: var(--accent);
}

.lateral-stats {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--spacing-md);
}

.lateral-stat {
    text-align: center;
    padding: var(--spacing-sm);
    background: var(--gray-100);
    border-radius: 4px;
}

.lateral-stat .label {
    font-size: 0.75rem;
    color: var(--gray-600);
    margin-bottom: var(--spacing-xs);
}

.lateral-stat .value {
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--primary);
}

/* ============================================
   AI REVIEW PLACEHOLDER
   ============================================ */

.ai-review-section {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 8px;
    padding: var(--spacing-xl);
    color: white;
    margin-bottom: var(--spacing-xl);
}

.ai-review-section h3 {
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: var(--spacing-md);
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
}

.ai-review-content {
    background: rgba(255,255,255,0.1);
    border-radius: 6px;
    padding: var(--spacing-lg);
    font-style: italic;
    line-height: 1.8;
}

.ai-review-placeholder {
    opacity: 0.8;
}

/* ============================================
   ASSUMPTIONS PAGE
   ============================================ */

.assumptions-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--spacing-xl);
}

.assumption-card {
    background: var(--gray-100);
    border-radius: 8px;
    padding: var(--spacing-lg);
}

.assumption-card h4 {
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--primary);
    margin-bottom: var(--spacing-md);
    padding-bottom: var(--spacing-sm);
    border-bottom: 1px solid var(--gray-300);
}

.assumption-list {
    list-style: none;
}

.assumption-list li {
    padding: var(--spacing-sm) 0;
    border-bottom: 1px solid var(--gray-200);
    display: flex;
    justify-content: space-between;
    font-size: 0.85rem;
}

.assumption-list li:last-child {
    border-bottom: none;
}

.assumption-list .item-label {
    color: var(--gray-600);
}

.assumption-list .item-value {
    font-weight: 600;
    color: var(--dark);
    font-family: var(--font-mono);
}

/* ============================================
   CARBON DASHBOARD
   ============================================ */

.carbon-dashboard {
    background: linear-gradient(135deg, #38a169 0%, #2f855a 100%);
    border-radius: 8px;
    padding: var(--spacing-xl);
    color: white;
    margin-bottom: var(--spacing-xl);
}

.carbon-dashboard h3 {
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: var(--spacing-lg);
}

.carbon-metrics {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: var(--spacing-lg);
}

.carbon-metric {
    text-align: center;
    padding: var(--spacing-md);
    background: rgba(255,255,255,0.1);
    border-radius: 6px;
}

.carbon-metric .value {
    font-size: 1.5rem;
    font-weight: 700;
    margin-bottom: var(--spacing-xs);
}

.carbon-metric .label {
    font-size: 0.8rem;
    opacity: 0.9;
}

/* ============================================
   FOOTER
   ============================================ */

.report-footer {
    margin-top: var(--spacing-2xl);
    padding-top: var(--spacing-lg);
    border-top: 1px solid var(--gray-300);
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.8rem;
    color: var(--gray-500);
}

.footer-logo {
    font-weight: 700;
    color: var(--primary);
}

/* ============================================
   CALCULATION STEPS
   ============================================ */

.calc-section {
    background: var(--gray-100);
    border-radius: 8px;
    padding: var(--spacing-lg);
    margin-bottom: var(--spacing-lg);
}

.calc-section h3 {
    font-size: 1rem;
    font-weight: 700;
    color: var(--primary);
    margin-bottom: var(--spacing-md);
    padding-bottom: var(--spacing-sm);
    border-bottom: 1px solid var(--gray-300);
}

.calc-step {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: var(--spacing-sm) var(--spacing-md);
    margin-bottom: var(--spacing-sm);
    padding: var(--spacing-sm);
    background: white;
    border-radius: 4px;
    border-left: 3px solid var(--accent);
}

.calc-step .step-num {
    font-weight: 700;
    color: var(--accent);
    font-size: 0.85rem;
}

.calc-step .step-desc {
    font-size: 0.85rem;
    color: var(--gray-700);
}

.calc-step .step-formula {
    grid-column: 2;
    font-family: var(--font-mono);
    font-size: 0.8rem;
    color: var(--primary);
    background: var(--gray-100);
    padding: var(--spacing-xs) var(--spacing-sm);
    border-radius: 4px;
}

.calc-result {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-md);
    background: white;
    border-radius: 4px;
    margin-top: var(--spacing-md);
    border: 2px solid var(--accent);
}

.calc-result .label {
    font-weight: 600;
    color: var(--gray-700);
}

.calc-result .value {
    font-family: var(--font-mono);
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--primary);
}

.calc-result.pass { border-color: var(--success); }
.calc-result.pass .value { color: var(--success); }
.calc-result.warn { border-color: var(--warning); }
.calc-result.warn .value { color: var(--warning); }
.calc-result.fail { border-color: var(--danger); }
.calc-result.fail .value { color: var(--danger); }

/* ============================================
   FEM RESULTS SECTION (Feature 14)
   ============================================ */

.fem-results-section {
    background: var(--gray-100);
    border-radius: 8px;
    padding: var(--spacing-lg);
    margin-bottom: var(--spacing-xl);
}

.fem-comparison-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: var(--spacing-lg);
    margin-bottom: var(--spacing-xl);
}

.fem-card {
    background: white;
    border: 1px solid var(--gray-300);
    border-radius: 8px;
    padding: var(--spacing-lg);
}

.fem-card h4 {
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--primary);
    margin-bottom: var(--spacing-md);
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
}

.fem-card h4 .icon {
    width: 20px;
    height: 20px;
    color: var(--accent);
}

.fem-value-row {
    display: flex;
    justify-content: space-between;
    padding: var(--spacing-sm) 0;
    border-bottom: 1px solid var(--gray-200);
}

.fem-value-row:last-child {
    border-bottom: none;
}

.fem-value-row .label {
    color: var(--gray-600);
    font-size: 0.85rem;
}

.fem-value-row .value {
    font-weight: 600;
    font-family: var(--font-mono);
}

.discrepancy-indicator {
    display: inline-block;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.75rem;
    margin-left: var(--spacing-xs);
}

.discrepancy-indicator.high {
    background: #fed7d7;
    color: #c53030;
}

.discrepancy-indicator.medium {
    background: #fefcbf;
    color: #975a16;
}

.discrepancy-indicator.low {
    background: #c6f6d5;
    color: #276749;
}

.critical-elements-list {
    list-style: none;
    padding: 0;
}

.critical-element-item {
    padding: var(--spacing-md);
    background: white;
    border-radius: 6px;
    margin-bottom: var(--spacing-sm);
    border-left: 4px solid var(--accent);
}

.critical-element-item.critical {
    border-left-color: var(--danger);
    background: #fff5f5;
}

.critical-element-item.high {
    border-left-color: var(--warning);
    background: #fffff0;
}

.critical-element-item.medium {
    border-left-color: var(--accent);
}

.critical-element-item .element-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: var(--spacing-xs);
}

.critical-element-item .element-type {
    font-weight: 600;
    color: var(--primary);
}

.critical-element-item .criticality-badge {
    font-size: 0.75rem;
    padding: 2px 8px;
    border-radius: 12px;
    text-transform: uppercase;
}

.criticality-badge.critical {
    background: var(--danger);
    color: white;
}

.criticality-badge.high {
    background: var(--warning);
    color: white;
}

.criticality-badge.medium {
    background: var(--accent);
    color: white;
}

.critical-element-item .element-issue {
    font-size: 0.85rem;
    color: var(--gray-700);
    margin-bottom: var(--spacing-xs);
}

.critical-element-item .element-recommendation {
    font-size: 0.8rem;
    color: var(--gray-600);
    font-style: italic;
}

.ai-interpretation {
    background: linear-gradient(135deg, #4c51bf 0%, #667eea 100%);
    border-radius: 8px;
    padding: var(--spacing-xl);
    color: white;
    margin-bottom: var(--spacing-xl);
}

.ai-interpretation h3 {
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: var(--spacing-md);
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
}

.ai-interpretation .summary-text {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    padding: var(--spacing-lg);
    margin-bottom: var(--spacing-md);
    line-height: 1.8;
}

.ai-interpretation .confidence-score {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    font-size: 0.85rem;
    opacity: 0.9;
}

.recommendations-list {
    background: var(--gray-100);
    border-radius: 8px;
    padding: var(--spacing-lg);
}

.recommendations-list h4 {
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--primary);
    margin-bottom: var(--spacing-md);
}

.recommendations-list ol {
    margin: 0;
    padding-left: var(--spacing-lg);
}

.recommendations-list li {
    padding: var(--spacing-sm) 0;
    border-bottom: 1px solid var(--gray-200);
    font-size: 0.9rem;
}

.recommendations-list li:last-child {
    border-bottom: none;
}

.code-compliance-summary {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: var(--spacing-md);
    margin-bottom: var(--spacing-xl);
}

.compliance-card {
    background: white;
    border-radius: 8px;
    padding: var(--spacing-md);
    text-align: center;
    border: 2px solid var(--gray-300);
}

.compliance-card.pass {
    border-color: var(--success);
}

.compliance-card.fail {
    border-color: var(--danger);
}

.compliance-card.warning {
    border-color: var(--warning);
}

.compliance-card .check-name {
    font-weight: 600;
    color: var(--primary);
    font-size: 0.85rem;
    margin-bottom: var(--spacing-xs);
}

.compliance-card .check-status {
    font-size: 1.25rem;
    font-weight: 700;
}

.compliance-card.pass .check-status {
    color: var(--success);
}

.compliance-card.fail .check-status {
    color: var(--danger);
}

.compliance-card.warning .check-status {
    color: var(--warning);
}

.compliance-card .check-value {
    font-size: 0.8rem;
    color: var(--gray-600);
    font-family: var(--font-mono);
}

/* ============================================
   PRINT STYLES
   ============================================ */

@media print {
    body {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }

    .page {
        padding: 0;
        margin: 0;
    }

    .report-header,
    .ai-review-section,
    .carbon-dashboard,
    .calc-section,
    .ai-interpretation,
    .fem-results-section {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }
}
'''


# =============================================================================
# JINJA2 HTML TEMPLATE
# =============================================================================

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ project.project_name }} - Structural Design Report</title>
    <style>
{{ css_styles }}
    </style>
</head>
<body>

<!-- ============================================
     PAGE 1: GRAVITY SCHEME
     ============================================ -->
<div class="page" id="page-gravity">

    <!-- Hero Header -->
    <header class="report-header">
        <h1>{{ project.project_name }}</h1>
        <p class="subtitle">Preliminary Structural Design Report</p>
        <div class="header-meta">
            <div class="header-meta-item">
                <div class="label">Project No.</div>
                <div class="value">{{ project.project_number }}</div>
            </div>
            <div class="header-meta-item">
                <div class="label">Engineer</div>
                <div class="value">{{ project.engineer }}</div>
            </div>
            <div class="header-meta-item">
                <div class="label">Date</div>
                <div class="value">{{ project.date }}</div>
            </div>
            <div class="header-meta-item">
                <div class="label">Status</div>
                <div class="value">{{ overall_status }}</div>
            </div>
        </div>
    </header>

    <!-- Status Overview -->
    <div class="status-grid">
        {% for element in status_elements %}
        <div class="status-card {{ element.status_class }}">
            <div class="icon">{{ element.icon | safe }}</div>
            <div class="element-name">{{ element.name }}</div>
            <div class="utilization">{{ element.utilization }}</div>
        </div>
        {% endfor %}
    </div>

    <!-- Key Metrics -->
    <div class="metrics-grid">
        <div class="metric-card">
            <div class="icon">{{ icons.building | safe }}</div>
            <div class="label">Total Height</div>
            <div class="value">{{ metrics.total_height }}<span class="unit">m</span></div>
        </div>
        <div class="metric-card">
            <div class="icon">{{ icons.ruler | safe }}</div>
            <div class="label">Floor Area</div>
            <div class="value">{{ metrics.floor_area }}<span class="unit">m²</span></div>
        </div>
        <div class="metric-card">
            <div class="icon">{{ icons.carbon | safe }}</div>
            <div class="label">Carbon Intensity</div>
            <div class="value">{{ metrics.carbon_intensity }}<span class="unit">kgCO₂e/m²</span></div>
        </div>
    </div>

    <!-- Element Design Summary Table -->
    <h2 class="section-title">
        <span class="icon">{{ icons.concrete | safe }}</span>
        Structural Element Summary
    </h2>

    <table class="element-table">
        <thead>
            <tr>
                <th>Element</th>
                <th>Size</th>
                <th>Grade</th>
                <th class="number">Utilization</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            {% for element in element_summary %}
            <tr>
                <td><strong>{{ element.name }}</strong></td>
                <td>{{ element.size }}</td>
                <td>C{{ element.grade }}</td>
                <td class="number">{{ element.utilization }}%</td>
                <td><span class="status-badge {{ element.status_class }}">{{ element.status }}</span></td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <!-- Framing Grid Diagram -->
    <div class="diagram-container">
        <div class="diagram-title">Structural Framing Plan</div>
        {{ framing_svg | safe }}
    </div>

    <footer class="report-footer">
        <span class="footer-logo">PrelimStruct</span>
        <span>Page 1 of {{ total_pages }} | Generated {{ generation_date }}</span>
    </footer>
</div>

<!-- ============================================
     PAGE 2: STEP-BY-STEP DESIGN CALCULATIONS
     ============================================ -->
<div class="page" id="page-calculations">

    <h2 class="section-title">
        <span class="icon">{{ icons.ruler | safe }}</span>
        Step-by-Step Design Calculations
    </h2>

    <!-- Slab Design Calculations -->
    <div class="calc-section">
        <h3>{{ icons.concrete | safe }} Slab Design (HK Code Cl 7.3.1.2)</h3>

        <div class="calc-step">
            <span class="step-num">1</span>
            <span class="step-desc">Determine slab span and support conditions</span>
            <div class="step-formula">Span = {{ calc.slab.span }} m | Type: {{ calc.slab.slab_type }}</div>
        </div>

        <div class="calc-step">
            <span class="step-num">2</span>
            <span class="step-desc">Calculate total factored load (ULS)</span>
            <div class="step-formula">w = γ<sub>G</sub>×Gk + γ<sub>Q</sub>×Qk = {{ calc.slab.load_calc }}</div>
        </div>

        <div class="calc-step">
            <span class="step-num">3</span>
            <span class="step-desc">Apply span/depth ratio from HK Code Table 7.4</span>
            <div class="step-formula">Basic ratio = {{ calc.slab.basic_ratio }} ({{ calc.slab.slab_type }})</div>
        </div>

        <div class="calc-step">
            <span class="step-num">4</span>
            <span class="step-desc">Calculate modification factor for service stress</span>
            <div class="step-formula">MF = {{ calc.slab.mod_factor }} → Modified ratio = {{ calc.slab.modified_ratio }}</div>
        </div>

        <div class="calc-step">
            <span class="step-num">5</span>
            <span class="step-desc">Calculate required effective depth</span>
            <div class="step-formula">d = Span / Modified ratio = {{ calc.slab.span }}m / {{ calc.slab.modified_ratio }} = {{ calc.slab.eff_depth }} mm</div>
        </div>

        <div class="calc-step">
            <span class="step-num">6</span>
            <span class="step-desc">Add cover and bar diameter to get total thickness</span>
            <div class="step-formula">h = d + cover + φ/2 = {{ calc.slab.eff_depth }} + 25 + 6 = {{ calc.slab.thickness }} mm</div>
        </div>

        <div class="calc-result {{ calc.slab.status_class }}">
            <span class="label">Slab Thickness Adopted</span>
            <span class="value">{{ calc.slab.thickness }} mm (Utilization: {{ calc.slab.utilization }}%)</span>
        </div>
    </div>

    <!-- Primary Beam Design Calculations -->
    <div class="calc-section">
        <h3>{{ icons.steel | safe }} Primary Beam Design (HK Code)</h3>

        <div class="calc-step">
            <span class="step-num">1</span>
            <span class="step-desc">Determine beam span and tributary width</span>
            <div class="step-formula">Span = {{ calc.pri_beam.span }} m | Tributary width = {{ calc.pri_beam.trib_width }} m</div>
        </div>

        <div class="calc-step">
            <span class="step-num">2</span>
            <span class="step-desc">Calculate uniformly distributed load on beam</span>
            <div class="step-formula">w = {{ calc.pri_beam.load_calc }}</div>
        </div>

        <div class="calc-step">
            <span class="step-num">3</span>
            <span class="step-desc">Calculate design moment (with pattern loading factor)</span>
            <div class="step-formula">M = {{ calc.pri_beam.moment_calc }}</div>
        </div>

        <div class="calc-step">
            <span class="step-num">4</span>
            <span class="step-desc">Calculate design shear</span>
            <div class="step-formula">V = {{ calc.pri_beam.shear_calc }}</div>
        </div>

        <div class="calc-step">
            <span class="step-num">5</span>
            <span class="step-desc">Size beam for flexure and check shear stress</span>
            <div class="step-formula">b × d = {{ calc.pri_beam.width }} × {{ calc.pri_beam.depth }} mm | v = V/(bd) = {{ calc.pri_beam.shear_stress }} MPa</div>
        </div>

        <div class="calc-step">
            <span class="step-num">6</span>
            <span class="step-desc">Check deep beam (L/d > 2.0) and shear capacity</span>
            <div class="step-formula">L/d = {{ calc.pri_beam.span_depth_ratio }} | v<sub>max</sub> = 0.8√f<sub>cu</sub> = {{ calc.pri_beam.v_max }} MPa</div>
        </div>

        <div class="calc-result {{ calc.pri_beam.status_class }}">
            <span class="label">Primary Beam Size Adopted</span>
            <span class="value">{{ calc.pri_beam.width }} × {{ calc.pri_beam.depth }} mm (Utilization: {{ calc.pri_beam.utilization }}%)</span>
        </div>
    </div>

    <!-- Secondary Beam Design Calculations -->
    <div class="calc-section">
        <h3>{{ icons.steel | safe }} Secondary Beam Design (HK Code)</h3>

        <div class="calc-step">
            <span class="step-num">1</span>
            <span class="step-desc">Determine beam span and tributary width</span>
            <div class="step-formula">Span = {{ calc.sec_beam.span }} m | Tributary width = {{ calc.sec_beam.trib_width }} m</div>
        </div>

        <div class="calc-step">
            <span class="step-num">2</span>
            <span class="step-desc">Calculate uniformly distributed load on beam</span>
            <div class="step-formula">w = {{ calc.sec_beam.load_calc }}</div>
        </div>

        <div class="calc-step">
            <span class="step-num">3</span>
            <span class="step-desc">Calculate design moment (with pattern loading factor)</span>
            <div class="step-formula">M = {{ calc.sec_beam.moment_calc }}</div>
        </div>

        <div class="calc-step">
            <span class="step-num">4</span>
            <span class="step-desc">Calculate design shear</span>
            <div class="step-formula">V = {{ calc.sec_beam.shear_calc }}</div>
        </div>

        <div class="calc-step">
            <span class="step-num">5</span>
            <span class="step-desc">Size beam for flexure and check shear stress</span>
            <div class="step-formula">b × d = {{ calc.sec_beam.width }} × {{ calc.sec_beam.depth }} mm | v = V/(bd) = {{ calc.sec_beam.shear_stress }} MPa</div>
        </div>

        <div class="calc-result {{ calc.sec_beam.status_class }}">
            <span class="label">Secondary Beam Size Adopted</span>
            <span class="value">{{ calc.sec_beam.width }} × {{ calc.sec_beam.depth }} mm (Utilization: {{ calc.sec_beam.utilization }}%)</span>
        </div>
    </div>

    <!-- Column Design Calculations -->
    <div class="calc-section">
        <h3>{{ icons.building | safe }} Column Design (HK Code)</h3>

        <div class="calc-step">
            <span class="step-num">1</span>
            <span class="step-desc">Calculate tributary area and number of floors</span>
            <div class="step-formula">A<sub>trib</sub> = {{ calc.column.trib_area }} m² | Floors = {{ calc.column.floors }}</div>
        </div>

        <div class="calc-step">
            <span class="step-num">2</span>
            <span class="step-desc">Calculate total factored axial load</span>
            <div class="step-formula">N = {{ calc.column.load_calc }}</div>
        </div>

        <div class="calc-step">
            <span class="step-num">3</span>
            <span class="step-desc">Check eccentricity for edge/corner columns</span>
            <div class="step-formula">{{ calc.column.ecc_check }}</div>
        </div>

        <div class="calc-step">
            <span class="step-num">4</span>
            <span class="step-desc">Size column section (assuming 2% reinforcement)</span>
            <div class="step-formula">N = 0.35×f<sub>cu</sub>×A<sub>c</sub> + 0.67×f<sub>y</sub>×A<sub>s</sub> → {{ calc.column.size_calc }}</div>
        </div>

        <div class="calc-step">
            <span class="step-num">5</span>
            <span class="step-desc">Check slenderness ratio</span>
            <div class="step-formula">λ = L<sub>e</sub>/b = {{ calc.column.slenderness_calc }}</div>
        </div>

        <div class="calc-result {{ calc.column.status_class }}">
            <span class="label">Column Size Adopted</span>
            <span class="value">{{ calc.column.size }} mm (Utilization: {{ calc.column.utilization }}%)</span>
        </div>
    </div>

    <footer class="report-footer">
        <span class="footer-logo">PrelimStruct</span>
        <span>Page 2 of {{ total_pages }} | Generated {{ generation_date }}</span>
    </footer>
</div>

<!-- ============================================
     PAGE 3: STABILITY & SUMMARY
     ============================================ -->
<div class="page" id="page-stability">

    <h2 class="section-title">
        <span class="icon">{{ icons.wind | safe }}</span>
        Lateral Stability Analysis
    </h2>

    <!-- Lateral System Summary -->
    <div class="lateral-summary">
        <div class="lateral-card">
            <h3><span class="icon">{{ icons.wind | safe }}</span>Wind Loading (HK Wind Code 2019)</h3>
            <div class="lateral-stats">
                <div class="lateral-stat">
                    <div class="label">Base Shear</div>
                    <div class="value">{{ lateral.base_shear }} kN</div>
                </div>
                <div class="lateral-stat">
                    <div class="label">OTM</div>
                    <div class="value">{{ lateral.overturning_moment }} kNm</div>
                </div>
                <div class="lateral-stat">
                    <div class="label">Ref. Pressure</div>
                    <div class="value">{{ lateral.reference_pressure }} kPa</div>
                </div>
                <div class="lateral-stat">
                    <div class="label">Terrain</div>
                    <div class="value">{{ lateral.terrain }}</div>
                </div>
            </div>
        </div>

        <div class="lateral-card">
            <h3><span class="icon">{{ icons.core | safe }}</span>{{ lateral.system_type }}</h3>
            <div class="lateral-stats">
                {% if lateral.has_core %}
                <div class="lateral-stat">
                    <div class="label">Core Size</div>
                    <div class="value">{{ lateral.core_size }}</div>
                </div>
                <div class="lateral-stat">
                    <div class="label">Location</div>
                    <div class="value">{{ lateral.core_location }}</div>
                </div>
                <div class="lateral-stat">
                    <div class="label">Compression</div>
                    <div class="value">{{ lateral.compression_util }}%</div>
                </div>
                <div class="lateral-stat">
                    <div class="label">Shear</div>
                    <div class="value">{{ lateral.shear_util }}%</div>
                </div>
                {% else %}
                <div class="lateral-stat">
                    <div class="label">System</div>
                    <div class="value">Moment Frame</div>
                </div>
                <div class="lateral-stat">
                    <div class="label">Columns</div>
                    <div class="value">All participating</div>
                </div>
                {% endif %}
            </div>
        </div>
    </div>

    <!-- Drift Check -->
    <h2 class="section-title">
        <span class="icon">{{ icons.ruler | safe }}</span>
        Serviceability - Drift Check
    </h2>

    <table class="element-table">
        <thead>
            <tr>
                <th>Parameter</th>
                <th>Value</th>
                <th>Limit</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Total Drift</td>
                <td class="number">{{ drift.drift_mm }} mm</td>
                <td class="number">{{ drift.limit_mm }} mm</td>
                <td><span class="status-badge {{ drift.status_class }}">{{ drift.status }}</span></td>
            </tr>
            <tr>
                <td>Drift Index (Δ/H)</td>
                <td class="number">1/{{ drift.drift_ratio }}</td>
                <td class="number">1/500</td>
                <td><span class="status-badge {{ drift.status_class }}">{{ drift.status }}</span></td>
            </tr>
        </tbody>
    </table>

    <!-- AI Design Review -->
    <div class="ai-review-section">
        <h3>
            <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
                <path d="M21 11.5a8.38 8.38 0 01-.9 3.8 8.5 8.5 0 01-7.6 4.7 8.38 8.38 0 01-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 01-.9-3.8 8.5 8.5 0 014.7-7.6 8.38 8.38 0 013.8-.9h.5a8.48 8.48 0 018 8v.5z"/>
            </svg>
            AI Design Review
        </h3>
        <div class="ai-review-content">
            {% if ai_review %}
            {{ ai_review }}
            {% else %}
            <p class="ai-review-placeholder">
                AI design review commentary will be generated here. This feature analyzes the structural
                scheme for efficiency, constructability, and sustainability considerations, providing
                senior engineer-level critique and recommendations.
            </p>
            {% endif %}
        </div>
    </div>

    <!-- Carbon Dashboard -->
    <div class="carbon-dashboard">
        <h3>
            {{ icons.carbon | safe }}
            Embodied Carbon Summary
        </h3>
        <div class="carbon-metrics">
            <div class="carbon-metric">
                <div class="value">{{ carbon.volume }}</div>
                <div class="label">Concrete Volume (m³)</div>
            </div>
            <div class="carbon-metric">
                <div class="value">{{ carbon.emission }}</div>
                <div class="label">Total Emission (tCO₂e)</div>
            </div>
            <div class="carbon-metric">
                <div class="value">{{ carbon.intensity }}</div>
                <div class="label">Intensity (kgCO₂e/m²)</div>
            </div>
        </div>
    </div>

    <footer class="report-footer">
        <span class="footer-logo">PrelimStruct</span>
        <span>Page 3 of {{ total_pages }} | Generated {{ generation_date }}</span>
    </footer>
</div>

<!-- ============================================
     PAGE 3: ASSUMPTIONS & BASIS OF DESIGN
     ============================================ -->
<div class="page" id="page-assumptions">

    <h2 class="section-title">
        <span class="icon">{{ icons.check | safe }}</span>
        Basis of Design & Assumptions
    </h2>

    <div class="assumptions-grid">

        <!-- Code References -->
        <div class="assumption-card">
            <h4>Code References</h4>
            <ul class="assumption-list">
                <li>
                    <span class="item-label">Concrete Design</span>
                    <span class="item-value">HK Code 2013</span>
                </li>
                <li>
                    <span class="item-label">Wind Loading</span>
                    <span class="item-value">HK Wind Code 2019</span>
                </li>
                <li>
                    <span class="item-label">Live Loads</span>
                    <span class="item-value">Table 3.1/3.2</span>
                </li>
                <li>
                    <span class="item-label">Deflection Control</span>
                    <span class="item-value">Cl 7.3.1.2</span>
                </li>
            </ul>
        </div>

        <!-- Material Properties -->
        <div class="assumption-card">
            <h4>Material Properties</h4>
            <ul class="assumption-list">
                <li>
                    <span class="item-label">Slab Grade</span>
                    <span class="item-value">C{{ materials.fcu_slab }}</span>
                </li>
                <li>
                    <span class="item-label">Beam Grade</span>
                    <span class="item-value">C{{ materials.fcu_beam }}</span>
                </li>
                <li>
                    <span class="item-label">Column Grade</span>
                    <span class="item-value">C{{ materials.fcu_column }}</span>
                </li>
                <li>
                    <span class="item-label">Reinforcement</span>
                    <span class="item-value">Grade 500</span>
                </li>
            </ul>
        </div>

        <!-- Partial Safety Factors -->
        <div class="assumption-card">
            <h4>Partial Safety Factors</h4>
            <ul class="assumption-list">
                <li>
                    <span class="item-label">γ<sub>c</sub> (Concrete)</span>
                    <span class="item-value">1.50</span>
                </li>
                <li>
                    <span class="item-label">γ<sub>s</sub> (Steel)</span>
                    <span class="item-value">1.15</span>
                </li>
                <li>
                    <span class="item-label">γ<sub>G</sub> (Dead Load)</span>
                    <span class="item-value">{{ load_factors.gamma_g }}</span>
                </li>
                <li>
                    <span class="item-label">γ<sub>Q</sub> (Live Load)</span>
                    <span class="item-value">{{ load_factors.gamma_q }}</span>
                </li>
            </ul>
        </div>

        <!-- Load Combinations -->
        <div class="assumption-card">
            <h4>Load Combinations Applied</h4>
            <ul class="assumption-list">
                <li>
                    <span class="item-label">ULS Gravity</span>
                    <span class="item-value">1.4Gk + 1.6Qk</span>
                </li>
                <li>
                    <span class="item-label">ULS Wind</span>
                    <span class="item-value">1.0Gk + 1.4Wk</span>
                </li>
                <li>
                    <span class="item-label">SLS Deflection</span>
                    <span class="item-value">1.0Gk + 1.0Qk</span>
                </li>
                <li>
                    <span class="item-label">Active Combination</span>
                    <span class="item-value">{{ load_factors.active_combination }}</span>
                </li>
            </ul>
        </div>

    </div>

    <!-- Geometry Summary -->
    <h2 class="section-title" style="margin-top: var(--spacing-xl);">
        <span class="icon">{{ icons.building | safe }}</span>
        Building Geometry
    </h2>

    <table class="element-table">
        <thead>
            <tr>
                <th>Parameter</th>
                <th>Value</th>
                <th>Unit</th>
                <th>Notes</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Bay Width (X-direction)</td>
                <td class="number">{{ geometry.bay_x }}</td>
                <td>m</td>
                <td>Primary span direction</td>
            </tr>
            <tr>
                <td>Bay Width (Y-direction)</td>
                <td class="number">{{ geometry.bay_y }}</td>
                <td>m</td>
                <td>Secondary span direction</td>
            </tr>
            <tr>
                <td>Number of Floors</td>
                <td class="number">{{ geometry.floors }}</td>
                <td>-</td>
                <td>Above ground level</td>
            </tr>
            <tr>
                <td>Typical Story Height</td>
                <td class="number">{{ geometry.story_height }}</td>
                <td>m</td>
                <td>Floor-to-floor</td>
            </tr>
            <tr>
                <td>Total Building Height</td>
                <td class="number">{{ geometry.total_height }}</td>
                <td>m</td>
                <td>To roof level</td>
            </tr>
            <tr>
                <td>Tributary Area</td>
                <td class="number">{{ geometry.tributary_area }}</td>
                <td>m²</td>
                <td>Single bay</td>
            </tr>
        </tbody>
    </table>

    <!-- Design Loads -->
    <h2 class="section-title">
        <span class="icon">{{ icons.concrete | safe }}</span>
        Design Loads
    </h2>

    <table class="element-table">
        <thead>
            <tr>
                <th>Load Type</th>
                <th>Value</th>
                <th>Unit</th>
                <th>Reference</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Live Load (Imposed)</td>
                <td class="number">{{ loads.live_load }}</td>
                <td>kPa</td>
                <td>{{ loads.live_load_ref }}</td>
            </tr>
            <tr>
                <td>Superimposed Dead Load</td>
                <td class="number">{{ loads.dead_load }}</td>
                <td>kPa</td>
                <td>Finishes + Services</td>
            </tr>
            <tr>
                <td>Slab Self-Weight</td>
                <td class="number">{{ loads.slab_self_weight }}</td>
                <td>kPa</td>
                <td>24.5 kN/m³ × thickness</td>
            </tr>
            <tr>
                <td>Total Dead Load (Gk)</td>
                <td class="number">{{ loads.total_dead }}</td>
                <td>kPa</td>
                <td>SDL + Self-weight</td>
            </tr>
            <tr>
                <td>Factored Design Load</td>
                <td class="number">{{ loads.design_load }}</td>
                <td>kPa</td>
                <td>{{ load_factors.active_combination }}</td>
            </tr>
        </tbody>
    </table>

    <footer class="report-footer">
        <span class="footer-logo">PrelimStruct</span>
        <span>Page 4 of {{ total_pages }} | Generated {{ generation_date }}</span>
    </footer>
</div>

{% if has_fem_results %}
<!-- ============================================
     PAGE 5: FEM ANALYSIS RESULTS (Feature 14)
     ============================================ -->
<div class="page" id="page-fem">

    <h2 class="section-title">
        <span class="icon">{{ icons.building | safe }}</span>
        FEM Analysis Results
    </h2>

    <!-- Code Compliance Summary -->
    <div class="code-compliance-summary">
        {% for check in fem_data.code_compliance %}
        <div class="compliance-card {{ check.status }}">
            <div class="check-name">{{ check.check_name }}</div>
            <div class="check-status">
                {% if check.status == 'pass' %}OK{% elif check.status == 'fail' %}FAIL{% else %}WARN{% endif %}
            </div>
            <div class="check-value">{{ check.actual_value }} / {{ check.limit_value }}</div>
        </div>
        {% endfor %}
    </div>

    <!-- FEM vs Simplified Comparison -->
    <h3 class="section-title" style="font-size: 1rem;">
        <span class="icon">{{ icons.ruler | safe }}</span>
        FEM vs Simplified Design Comparison
    </h3>

    <div class="fem-comparison-grid">
        <div class="fem-card">
            <h4><span class="icon">{{ icons.steel | safe }}</span>Beam Forces</h4>
            <div class="fem-value-row">
                <span class="label">Max Moment (FEM)</span>
                <span class="value">{{ fem_data.max_beam_moment }} kNm</span>
            </div>
            <div class="fem-value-row">
                <span class="label">Max Moment (Simplified)</span>
                <span class="value">{{ fem_data.simplified_beam_moment }} kNm
                    {% if fem_data.moment_discrepancy > 15 %}
                    <span class="discrepancy-indicator high">+{{ fem_data.moment_discrepancy }}%</span>
                    {% elif fem_data.moment_discrepancy > 5 %}
                    <span class="discrepancy-indicator medium">+{{ fem_data.moment_discrepancy }}%</span>
                    {% else %}
                    <span class="discrepancy-indicator low">{{ fem_data.moment_discrepancy }}%</span>
                    {% endif %}
                </span>
            </div>
            <div class="fem-value-row">
                <span class="label">Max Shear (FEM)</span>
                <span class="value">{{ fem_data.max_beam_shear }} kN</span>
            </div>
            <div class="fem-value-row">
                <span class="label">Location</span>
                <span class="value">{{ fem_data.beam_moment_location }}</span>
            </div>
        </div>

        <div class="fem-card">
            <h4><span class="icon">{{ icons.concrete | safe }}</span>Column Forces</h4>
            <div class="fem-value-row">
                <span class="label">Max Axial (FEM)</span>
                <span class="value">{{ fem_data.max_column_axial }} kN</span>
            </div>
            <div class="fem-value-row">
                <span class="label">Max Axial (Simplified)</span>
                <span class="value">{{ fem_data.simplified_column_axial }} kN
                    {% if fem_data.axial_discrepancy > 15 %}
                    <span class="discrepancy-indicator high">+{{ fem_data.axial_discrepancy }}%</span>
                    {% elif fem_data.axial_discrepancy > 5 %}
                    <span class="discrepancy-indicator medium">+{{ fem_data.axial_discrepancy }}%</span>
                    {% else %}
                    <span class="discrepancy-indicator low">{{ fem_data.axial_discrepancy }}%</span>
                    {% endif %}
                </span>
            </div>
            <div class="fem-value-row">
                <span class="label">Max Column Moment</span>
                <span class="value">{{ fem_data.max_column_moment }} kNm</span>
            </div>
            <div class="fem-value-row">
                <span class="label">Location</span>
                <span class="value">{{ fem_data.column_axial_location }}</span>
            </div>
        </div>

        <div class="fem-card">
            <h4><span class="icon">{{ icons.wind | safe }}</span>Drift & Deflection</h4>
            <div class="fem-value-row">
                <span class="label">Max Drift (FEM)</span>
                <span class="value">{{ fem_data.max_drift }} mm (H/{{ fem_data.drift_ratio }})</span>
            </div>
            <div class="fem-value-row">
                <span class="label">Drift (Simplified)</span>
                <span class="value">{{ fem_data.simplified_drift }} mm</span>
            </div>
            <div class="fem-value-row">
                <span class="label">Max Deflection</span>
                <span class="value">{{ fem_data.max_deflection }} mm</span>
            </div>
            <div class="fem-value-row">
                <span class="label">Governing Load Case</span>
                <span class="value">{{ fem_data.critical_load_case }}</span>
            </div>
        </div>

        <div class="fem-card">
            <h4><span class="icon">{{ icons.check | safe }}</span>Model Summary</h4>
            <div class="fem-value-row">
                <span class="label">Element Count</span>
                <span class="value">{{ fem_data.element_count }}</span>
            </div>
            <div class="fem-value-row">
                <span class="label">Node Count</span>
                <span class="value">{{ fem_data.node_count }}</span>
            </div>
            <div class="fem-value-row">
                <span class="label">Max Stress</span>
                <span class="value">{{ fem_data.max_stress }} MPa</span>
            </div>
            <div class="fem-value-row">
                <span class="label">Stress Location</span>
                <span class="value">{{ fem_data.stress_location }}</span>
            </div>
        </div>
    </div>

    <!-- Critical Elements (if any) -->
    {% if fem_data.critical_elements %}
    <h3 class="section-title" style="font-size: 1rem; margin-top: var(--spacing-xl);">
        <span class="icon">{{ icons.warning | safe }}</span>
        Critical Elements Requiring Attention
    </h3>

    <ul class="critical-elements-list">
        {% for element in fem_data.critical_elements %}
        <li class="critical-element-item {{ element.criticality }}">
            <div class="element-header">
                <span class="element-type">{{ element.element_type }} - {{ element.location }}</span>
                <span class="criticality-badge {{ element.criticality }}">{{ element.criticality }}</span>
            </div>
            <div class="element-issue">{{ element.issue }}</div>
            {% if element.recommendation %}
            <div class="element-recommendation">Recommendation: {{ element.recommendation }}</div>
            {% endif %}
        </li>
        {% endfor %}
    </ul>
    {% endif %}

    <!-- AI Interpretation -->
    {% if fem_data.ai_interpretation %}
    <div class="ai-interpretation">
        <h3>
            <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
                <path d="M21 11.5a8.38 8.38 0 01-.9 3.8 8.5 8.5 0 01-7.6 4.7 8.38 8.38 0 01-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 01-.9-3.8 8.5 8.5 0 014.7-7.6 8.38 8.38 0 013.8-.9h.5a8.48 8.48 0 018 8v.5z"/>
            </svg>
            AI-Powered FEM Results Interpretation
        </h3>
        <div class="summary-text">
            {{ fem_data.ai_interpretation.summary | safe }}
        </div>
        <div class="confidence-score">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
            </svg>
            Confidence Score: {{ fem_data.ai_interpretation.confidence_score }}%
        </div>
    </div>
    {% endif %}

    <!-- Recommendations -->
    {% if fem_data.recommendations %}
    <div class="recommendations-list">
        <h4>Prioritized Recommendations</h4>
        <ol>
            {% for rec in fem_data.recommendations %}
            <li>{{ rec }}</li>
            {% endfor %}
        </ol>
    </div>
    {% endif %}

    <footer class="report-footer">
        <span class="footer-logo">PrelimStruct</span>
        <span>Page 5 of {{ total_pages }} | Generated {{ generation_date }}</span>
    </footer>
</div>
{% endif %}

</body>
</html>
'''


# =============================================================================
# FRAMING DIAGRAM SVG GENERATOR
# =============================================================================

def generate_framing_svg(project: ProjectData) -> str:
    """Generate an SVG framing plan diagram."""

    # Dimensions
    bay_x = project.geometry.bay_x
    bay_y = project.geometry.bay_y

    # SVG canvas settings
    margin = 40
    scale = 30  # pixels per meter
    width = bay_x * scale + 2 * margin
    height = bay_y * scale + 2 * margin

    # Colors based on status
    def get_color(utilization: float) -> str:
        if utilization > 1.0:
            return "#e53e3e"  # Red - fail
        elif utilization > 0.85:
            return "#d69e2e"  # Amber - warning
        return "#38a169"  # Green - pass

    # Get utilizations
    slab_util = project.slab_result.utilization if project.slab_result else 0.5
    beam_util = max(
        project.primary_beam_result.utilization if project.primary_beam_result else 0.5,
        project.secondary_beam_result.utilization if project.secondary_beam_result else 0.5
    )
    col_util = project.column_result.utilization if project.column_result else 0.5

    # Build SVG
    svg = f'''<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
    <!-- Background -->
    <rect width="{width}" height="{height}" fill="#f7fafc"/>

    <!-- Grid lines -->
    <g stroke="#e2e8f0" stroke-width="1" stroke-dasharray="4,4">
        <line x1="{margin}" y1="{margin}" x2="{margin + bay_x * scale}" y2="{margin}"/>
        <line x1="{margin}" y1="{margin + bay_y * scale}" x2="{margin + bay_x * scale}" y2="{margin + bay_y * scale}"/>
        <line x1="{margin}" y1="{margin}" x2="{margin}" y2="{margin + bay_y * scale}"/>
        <line x1="{margin + bay_x * scale}" y1="{margin}" x2="{margin + bay_x * scale}" y2="{margin + bay_y * scale}"/>
    </g>

    <!-- Slab (filled area) -->
    <rect x="{margin + 5}" y="{margin + 5}"
          width="{bay_x * scale - 10}" height="{bay_y * scale - 10}"
          fill="{get_color(slab_util)}" fill-opacity="0.15"
          stroke="{get_color(slab_util)}" stroke-width="1"/>

    <!-- Beams (lines) -->
    <g stroke="{get_color(beam_util)}" stroke-width="4" stroke-linecap="round">
        <!-- Primary beams (horizontal) -->
        <line x1="{margin}" y1="{margin}" x2="{margin + bay_x * scale}" y2="{margin}"/>
        <line x1="{margin}" y1="{margin + bay_y * scale}" x2="{margin + bay_x * scale}" y2="{margin + bay_y * scale}"/>
        <!-- Secondary beams (vertical) -->
        <line x1="{margin}" y1="{margin}" x2="{margin}" y2="{margin + bay_y * scale}"/>
        <line x1="{margin + bay_x * scale}" y1="{margin}" x2="{margin + bay_x * scale}" y2="{margin + bay_y * scale}"/>
    </g>

    <!-- Columns (corner squares) -->
    <g fill="{get_color(col_util)}" stroke="{get_color(col_util)}" stroke-width="1">
        <rect x="{margin - 8}" y="{margin - 8}" width="16" height="16" rx="2"/>
        <rect x="{margin + bay_x * scale - 8}" y="{margin - 8}" width="16" height="16" rx="2"/>
        <rect x="{margin - 8}" y="{margin + bay_y * scale - 8}" width="16" height="16" rx="2"/>
        <rect x="{margin + bay_x * scale - 8}" y="{margin + bay_y * scale - 8}" width="16" height="16" rx="2"/>
    </g>

    <!-- Dimension labels -->
    <g font-family="Inter, sans-serif" font-size="11" fill="#4a5568" text-anchor="middle">
        <text x="{margin + bay_x * scale / 2}" y="{height - 10}">{bay_x}m</text>
        <text x="15" y="{margin + bay_y * scale / 2}" transform="rotate(-90, 15, {margin + bay_y * scale / 2})">{bay_y}m</text>
    </g>

    <!-- Core wall (if present) -->'''

    # Add core wall if present
    core_geometry = project.lateral.core_geometry if project.lateral else None
    if core_geometry and core_geometry.length_x and core_geometry.length_y:
        core_x = core_geometry.length_x / 1000.0
        core_y = core_geometry.length_y / 1000.0
        core_scale_x = core_x * scale * 0.8
        core_scale_y = core_y * scale * 0.8

        # Position based on legacy core_location if present, else default to center
        raw_location = getattr(project.lateral, "core_location", "center")
        if hasattr(raw_location, "name"):
            location = raw_location.name.lower()
        else:
            location = str(raw_location).lower()

        if location == "side":
            cx = margin + bay_x * scale - core_scale_x - 10
            cy = margin + bay_y * scale / 2 - core_scale_y / 2
        elif location == "corner":
            cx = margin + bay_x * scale - core_scale_x - 10
            cy = margin + 10
        else:
            cx = margin + bay_x * scale / 2 - core_scale_x / 2
            cy = margin + bay_y * scale / 2 - core_scale_y / 2

        svg += f'''
    <rect x="{cx}" y="{cy}" width="{core_scale_x}" height="{core_scale_y}"
          fill="#3182ce" fill-opacity="0.3" stroke="#3182ce" stroke-width="2"/>
    <text x="{cx + core_scale_x/2}" y="{cy + core_scale_y/2 + 4}"
          font-family="Inter, sans-serif" font-size="10" fill="#3182ce" text-anchor="middle">CORE</text>'''

    svg += '''

    <!-- Legend -->
    <g transform="translate(10, 10)" font-family="Inter, sans-serif" font-size="9" fill="#718096">
        <rect x="0" y="0" width="8" height="8" fill="#38a169"/>
        <text x="12" y="7">Pass</text>
        <rect x="40" y="0" width="8" height="8" fill="#d69e2e"/>
        <text x="52" y="7">Warn</text>
        <rect x="80" y="0" width="8" height="8" fill="#e53e3e"/>
        <text x="92" y="7">Fail</text>
    </g>
</svg>'''

    return svg


# =============================================================================
# REPORT GENERATOR CLASS
# =============================================================================

class ReportGenerator:
    """
    Magazine-Style HTML Report Generator for PrelimStruct.

    Generates professional, print-ready HTML reports with:
    - Page 1: Gravity Scheme (hero, status badges, element table, framing diagram)
    - Page 2: Stability & Summary (lateral analysis, drift check, AI review placeholder)
    - Page 3: Assumptions (basis of design, code refs, load factors)
    """

    def __init__(self, project: ProjectData):
        """Initialize with project data."""
        self.project = project
        self.env = Environment(
            loader=BaseLoader(),
            autoescape=select_autoescape(['html', 'xml'])
        )
        self.template = self.env.from_string(HTML_TEMPLATE)

    def _get_status_class(self, utilization: float) -> str:
        """Return CSS class based on utilization ratio."""
        if utilization > 1.0:
            return "fail"
        elif utilization > 0.85:
            return "warn"
        return "pass"

    def _get_status_text(self, utilization: float) -> str:
        """Return status text based on utilization."""
        if utilization > 1.0:
            return "FAIL"
        elif utilization > 0.85:
            return "WARN"
        return "OK"

    def _format_utilization(self, utilization: float) -> str:
        """Format utilization as percentage string."""
        return f"{utilization * 100:.0f}%"

    def _get_overall_status(self) -> str:
        """Determine overall project status."""
        utils = []
        if self.project.slab_result:
            utils.append(self.project.slab_result.utilization)
        if self.project.primary_beam_result:
            utils.append(self.project.primary_beam_result.utilization)
        if self.project.column_result:
            utils.append(self.project.column_result.utilization)
        if self.project.wind_result and not self.project.wind_result.drift_ok:
            utils.append(1.5)  # Force fail if drift exceeds limit

        if not utils:
            return "PENDING"

        max_util = max(utils)
        if max_util > 1.0:
            return "REQUIRES REVIEW"
        elif max_util > 0.85:
            return "ACCEPTABLE"
        return "SATISFACTORY"

    def _build_status_elements(self) -> list:
        """Build status card data for each structural element."""
        elements = []

        # Slab
        if self.project.slab_result:
            util = self.project.slab_result.utilization
            elements.append({
                'name': 'Slab',
                'icon': SVG_ICONS['concrete'],
                'utilization': self._format_utilization(util),
                'status_class': self._get_status_class(util)
            })

        # Primary Beam
        if self.project.primary_beam_result:
            util = self.project.primary_beam_result.utilization
            elements.append({
                'name': 'Primary Beam',
                'icon': SVG_ICONS['steel'],
                'utilization': self._format_utilization(util),
                'status_class': self._get_status_class(util)
            })

        # Secondary Beam
        if self.project.secondary_beam_result:
            util = self.project.secondary_beam_result.utilization
            elements.append({
                'name': 'Secondary Beam',
                'icon': SVG_ICONS['steel'],
                'utilization': self._format_utilization(util),
                'status_class': self._get_status_class(util)
            })

        # Column
        if self.project.column_result:
            util = self.project.column_result.utilization
            elements.append({
                'name': 'Column',
                'icon': SVG_ICONS['concrete'],
                'utilization': self._format_utilization(util),
                'status_class': self._get_status_class(util)
            })

        # Drift
        if self.project.wind_result:
            drift_ok = self.project.wind_result.drift_ok
            elements.append({
                'name': 'Drift',
                'icon': SVG_ICONS['wind'],
                'utilization': 'OK' if drift_ok else 'FAIL',
                'status_class': 'pass' if drift_ok else 'fail'
            })

        return elements

    def _build_element_summary(self) -> list:
        """Build element summary table data."""
        elements = []

        # Slab
        if self.project.slab_result:
            r = self.project.slab_result
            elements.append({
                'name': 'Slab',
                'size': f'{r.thickness:.0f}mm thick',
                'grade': self.project.materials.fcu_slab,
                'utilization': f'{r.utilization * 100:.0f}',
                'status': self._get_status_text(r.utilization),
                'status_class': self._get_status_class(r.utilization)
            })

        # Primary Beam
        if self.project.primary_beam_result:
            r = self.project.primary_beam_result
            elements.append({
                'name': 'Primary Beam',
                'size': f'{r.width:.0f} × {r.depth:.0f}mm',
                'grade': self.project.materials.fcu_beam,
                'utilization': f'{r.utilization * 100:.0f}',
                'status': self._get_status_text(r.utilization),
                'status_class': self._get_status_class(r.utilization)
            })

        # Secondary Beam
        if self.project.secondary_beam_result:
            r = self.project.secondary_beam_result
            elements.append({
                'name': 'Secondary Beam',
                'size': f'{r.width:.0f} × {r.depth:.0f}mm',
                'grade': self.project.materials.fcu_beam,
                'utilization': f'{r.utilization * 100:.0f}',
                'status': self._get_status_text(r.utilization),
                'status_class': self._get_status_class(r.utilization)
            })

        # Column
        if self.project.column_result:
            r = self.project.column_result
            elements.append({
                'name': 'Column',
                'size': f'{r.dimension:.0f} × {r.dimension:.0f}mm',
                'grade': self.project.materials.fcu_column,
                'utilization': f'{r.utilization * 100:.0f}',
                'status': self._get_status_text(r.utilization),
                'status_class': self._get_status_class(r.utilization)
            })

        return elements

    def _build_lateral_data(self) -> dict:
        """Build lateral system data for template."""
        data = {
            'base_shear': '—',
            'overturning_moment': '—',
            'reference_pressure': '—',
            'terrain': '—',
            'system_type': 'Lateral System',
            'has_core': False,
            'core_size': '—',
            'core_location': '—',
            'compression_util': '—',
            'shear_util': '—'
        }

        if self.project.wind_result:
            wr = self.project.wind_result
            data['base_shear'] = f'{wr.base_shear:.0f}'
            data['overturning_moment'] = f'{wr.overturning_moment:.0f}'
            data['reference_pressure'] = f'{wr.reference_pressure:.2f}'

        if self.project.lateral:
            data['terrain'] = self.project.lateral.terrain.name

            core_geometry = self.project.lateral.core_geometry
            if core_geometry and core_geometry.length_x and core_geometry.length_y:
                data['system_type'] = 'Core Wall System'
                data['has_core'] = True
                core_x = core_geometry.length_x / 1000.0
                core_y = core_geometry.length_y / 1000.0
                data['core_size'] = f'{core_x:.1f} × {core_y:.1f}m'

                raw_location = getattr(self.project.lateral, "core_location", "CENTER")
                if hasattr(raw_location, "name"):
                    data['core_location'] = raw_location.name
                else:
                    data['core_location'] = str(raw_location).upper()

                if self.project.core_wall_result:
                    cwr = self.project.core_wall_result
                    data['compression_util'] = f'{cwr.compression_check * 100:.0f}'
                    data['shear_util'] = f'{cwr.shear_check * 100:.0f}'
            else:
                data['system_type'] = 'Moment Frame System'

        return data

    def _build_drift_data(self) -> dict:
        """Build drift check data for template."""
        data = {
            'drift_mm': '—',
            'limit_mm': '—',
            'drift_ratio': '—',
            'status': '—',
            'status_class': 'pass'
        }

        if self.project.wind_result:
            wr = self.project.wind_result
            total_height = self.project.geometry.floors * self.project.geometry.story_height * 1000  # mm
            limit_mm = total_height / 500

            data['drift_mm'] = f'{wr.drift_mm:.1f}'
            data['limit_mm'] = f'{limit_mm:.1f}'

            if wr.drift_index > 0:
                data['drift_ratio'] = f'{1/wr.drift_index:.0f}'
            else:
                data['drift_ratio'] = '∞'

            data['status'] = 'OK' if wr.drift_ok else 'FAIL'
            data['status_class'] = 'pass' if wr.drift_ok else 'fail'

        return data

    def _build_carbon_data(self) -> dict:
        """Build carbon emission data for template."""
        total_area = (self.project.geometry.bay_x *
                      self.project.geometry.bay_y *
                      self.project.geometry.floors)

        volume = self.project.concrete_volume
        emission = self.project.carbon_emission / 1000  # Convert to tonnes
        intensity = self.project.carbon_emission / total_area if total_area > 0 else 0

        return {
            'volume': f'{volume:.1f}',
            'emission': f'{emission:.1f}',
            'intensity': f'{intensity:.0f}'
        }

    def _get_load_combination_name(self) -> str:
        """Get human-readable load combination name."""
        combo = self.project.load_combination
        # Map load combinations to human-readable names
        combo_names = {
            LoadCombination.ULS_GRAVITY_1: "ULS Gravity (1.4Gk + 1.6Qk)",
            LoadCombination.ULS_GRAVITY_2: "ULS Gravity Min (1.0Gk + 1.6Qk)",
            LoadCombination.ULS_WIND_1: "ULS Wind (1.4Gk + 1.4Wk)",
            LoadCombination.ULS_WIND_2: "ULS Wind Min (1.0Gk + 1.4Wk)",
            LoadCombination.ULS_WIND_3: "ULS Combined (1.2Gk + 1.2Qk + 1.2Wk)",
            LoadCombination.ULS_WIND_4: "ULS Wind Reversal (1.2Gk + 1.2Qk - 1.2Wk)",
            LoadCombination.SLS_CHARACTERISTIC: "SLS Characteristic (1.0Gk + 1.0Qk)",
            LoadCombination.SLS_FREQUENT: "SLS Frequent (1.0Gk + 0.5Qk)",
            LoadCombination.SLS_QUASI_PERMANENT: "SLS Quasi-Permanent (1.0Gk + 0.3Qk)",
        }
        return combo_names.get(combo, "ULS Gravity (1.4Gk + 1.6Qk)")

    def _build_fem_data(
        self,
        fem_results: Optional[Any] = None,
        simplified_results: Optional[Any] = None,
        ai_interpretation: Optional[Any] = None,
    ) -> dict:
        """Build FEM results data for template.

        Args:
            fem_results: Optional FEMResultsSummary from analysis
            simplified_results: Optional SimplifiedResultsSummary for comparison
            ai_interpretation: Optional ResultsInterpretation from AI

        Returns:
            Dictionary with FEM data for template rendering
        """
        data = {
            'max_beam_moment': '—',
            'max_beam_shear': '—',
            'max_column_axial': '—',
            'max_column_moment': '—',
            'max_drift': '—',
            'drift_ratio': '—',
            'max_deflection': '—',
            'max_stress': '—',
            'stress_location': '—',
            'beam_moment_location': '—',
            'column_axial_location': '—',
            'critical_load_case': '—',
            'element_count': 0,
            'node_count': 0,
            'simplified_beam_moment': '—',
            'simplified_column_axial': '—',
            'simplified_drift': '—',
            'moment_discrepancy': 0,
            'axial_discrepancy': 0,
            'code_compliance': [],
            'critical_elements': [],
            'recommendations': [],
            'ai_interpretation': None,
        }

        if fem_results:
            # Extract FEM values
            data['max_beam_moment'] = f'{fem_results.max_beam_moment[0]:.1f}'
            data['beam_moment_location'] = fem_results.max_beam_moment[1] or 'N/A'
            data['max_beam_shear'] = f'{fem_results.max_beam_shear[0]:.1f}'
            data['max_column_axial'] = f'{fem_results.max_column_axial[0]:.1f}'
            data['column_axial_location'] = fem_results.max_column_axial[1] or 'N/A'
            data['max_column_moment'] = f'{fem_results.max_column_moment[0]:.1f}'
            data['max_drift'] = f'{fem_results.max_drift[0]:.1f}'
            data['drift_ratio'] = f'{fem_results.max_drift[1]:.0f}' if fem_results.max_drift[1] > 0 else '500+'
            data['max_deflection'] = f'{fem_results.max_deflection[0]:.1f}'
            data['max_stress'] = f'{fem_results.max_stress[0]:.1f}'
            data['stress_location'] = fem_results.max_stress[1] or 'N/A'
            data['critical_load_case'] = fem_results.critical_load_case or 'ULS1'
            data['element_count'] = fem_results.element_count
            data['node_count'] = fem_results.node_count

        if simplified_results:
            data['simplified_beam_moment'] = f'{simplified_results.beam_moment:.1f}'
            data['simplified_column_axial'] = f'{simplified_results.column_axial:.1f}'
            data['simplified_drift'] = f'{simplified_results.drift_estimate:.1f}'

            # Calculate discrepancies
            if fem_results and simplified_results.beam_moment > 0:
                moment_diff = abs(fem_results.max_beam_moment[0] - simplified_results.beam_moment)
                data['moment_discrepancy'] = int(moment_diff / simplified_results.beam_moment * 100)

            if fem_results and simplified_results.column_axial > 0:
                axial_diff = abs(fem_results.max_column_axial[0] - simplified_results.column_axial)
                data['axial_discrepancy'] = int(axial_diff / simplified_results.column_axial * 100)

        if ai_interpretation:
            # Code compliance
            data['code_compliance'] = [
                {
                    'check_name': c.check_name,
                    'status': c.status,
                    'actual_value': f'{c.actual_value:.1f}',
                    'limit_value': f'{c.limit_value:.1f}',
                }
                for c in ai_interpretation.code_compliance
            ]

            # Critical elements
            data['critical_elements'] = [
                {
                    'element_type': e.element_type.title(),
                    'location': e.location,
                    'issue': e.issue,
                    'criticality': e.criticality.value,
                    'recommendation': e.recommendation,
                }
                for e in ai_interpretation.critical_elements
            ]

            # Recommendations
            data['recommendations'] = ai_interpretation.recommendations

            # AI interpretation summary
            if ai_interpretation.summary:
                data['ai_interpretation'] = {
                    'summary': ai_interpretation.summary.replace('\n', '<br>'),
                    'confidence_score': ai_interpretation.confidence_score,
                }

        return data

    def _build_calc_data(self) -> dict:
        """Build step-by-step calculation data for template."""
        p = self.project
        g = p.geometry
        l = p.loads
        m = p.materials

        # Calculate design load
        gk = p.total_dead_load
        qk = l.live_load
        design_load = GAMMA_G * gk + GAMMA_Q * qk

        # Slab calculations
        slab_span = min(g.bay_x, g.bay_y)
        slab_data = {
            'span': f'{slab_span:.1f}',
            'slab_type': 'Continuous' if g.bay_x != g.bay_y else 'Two-way',
            'load_calc': f'{GAMMA_G:.1f}×{gk:.1f} + {GAMMA_Q:.1f}×{qk:.1f} = {design_load:.1f} kPa',
            'basic_ratio': '26',
            'mod_factor': '1.0',
            'modified_ratio': '26.0',
            'eff_depth': '--',
            'thickness': '--',
            'utilization': '--',
            'status_class': 'pass'
        }
        if p.slab_result:
            sr = p.slab_result
            # Calculate effective depth from thickness (h - cover - bar/2)
            cover = p.materials.cover_slab if hasattr(p.materials, 'cover_slab') else 25
            eff_depth = sr.thickness - cover - 6  # T12 bar = 12mm/2 = 6mm
            slab_data['eff_depth'] = f'{eff_depth:.0f}'
            slab_data['thickness'] = f'{sr.thickness}'
            slab_data['utilization'] = f'{sr.utilization * 100:.0f}'
            slab_data['status_class'] = self._get_status_class(sr.utilization)
            # Estimate modification factor from deflection ratio
            if sr.deflection_ratio > 0:
                mod_factor = (slab_span * 1000 / sr.thickness) / 26
                slab_data['mod_factor'] = f'{mod_factor:.2f}'
                slab_data['modified_ratio'] = f'{26 * mod_factor:.1f}'

        # Primary beam calculations
        pri_beam_data = {
            'span': '--',
            'trib_width': '--',
            'load_calc': '--',
            'moment_calc': '--',
            'shear_calc': '--',
            'width': '--',
            'depth': '--',
            'shear_stress': '--',
            'span_depth_ratio': '--',
            'v_max': f'{0.8 * (m.fcu_beam ** 0.5):.2f}',
            'utilization': '--',
            'status_class': 'pass'
        }
        if p.primary_beam_result:
            br = p.primary_beam_result
            # Determine primary beam span and tributary based on layout
            trib_w = g.bay_y / 2
            udl = design_load * trib_w
            moment = br.moment
            shear = br.shear

            pri_beam_data['span'] = f'{g.bay_x:.1f}'  # Assuming primary along X
            pri_beam_data['trib_width'] = f'{trib_w:.1f}'
            pri_beam_data['load_calc'] = f'{design_load:.1f} kPa × {trib_w:.1f} m = {udl:.1f} kN/m'
            pri_beam_data['moment_calc'] = f'1.1 × wL²/8 = 1.1 × {udl:.1f} × {g.bay_x:.1f}² / 8 = {moment:.0f} kNm'
            pri_beam_data['shear_calc'] = f'wL/2 = {udl:.1f} × {g.bay_x:.1f} / 2 = {shear:.0f} kN'
            pri_beam_data['width'] = f'{br.width}'
            pri_beam_data['depth'] = f'{br.depth}'
            d_eff = br.depth - 50  # effective depth
            shear_stress = br.shear * 1000 / (br.width * d_eff) if d_eff > 0 else 0
            pri_beam_data['shear_stress'] = f'{shear_stress:.2f}'
            pri_beam_data['span_depth_ratio'] = f'{g.bay_x * 1000 / br.depth:.1f}'
            pri_beam_data['utilization'] = f'{br.utilization * 100:.0f}'
            pri_beam_data['status_class'] = self._get_status_class(br.utilization)

        # Secondary beam calculations
        sec_beam_data = {
            'span': '--',
            'trib_width': '--',
            'load_calc': '--',
            'moment_calc': '--',
            'shear_calc': '--',
            'width': '--',
            'depth': '--',
            'shear_stress': '--',
            'utilization': '--',
            'status_class': 'pass'
        }
        if p.secondary_beam_result:
            sbr = p.secondary_beam_result
            sec_span = g.bay_y
            sec_trib = g.bay_x / 4  # Typical with 3 secondary beams
            sec_udl = design_load * sec_trib

            sec_beam_data['span'] = f'{sec_span:.1f}'
            sec_beam_data['trib_width'] = f'{sec_trib:.1f}'
            sec_beam_data['load_calc'] = f'{design_load:.1f} kPa × {sec_trib:.1f} m = {sec_udl:.1f} kN/m'
            sec_beam_data['moment_calc'] = f'1.1 × wL²/8 = 1.1 × {sec_udl:.1f} × {sec_span:.1f}² / 8 = {sbr.moment:.0f} kNm'
            sec_beam_data['shear_calc'] = f'wL/2 = {sec_udl:.1f} × {sec_span:.1f} / 2 = {sbr.shear:.0f} kN'
            sec_beam_data['width'] = f'{sbr.width}'
            sec_beam_data['depth'] = f'{sbr.depth}'
            sec_d_eff = sbr.depth - 50  # effective depth
            sec_shear_stress = sbr.shear * 1000 / (sbr.width * sec_d_eff) if sec_d_eff > 0 else 0
            sec_beam_data['shear_stress'] = f'{sec_shear_stress:.2f}'
            sec_beam_data['utilization'] = f'{sbr.utilization * 100:.0f}'
            sec_beam_data['status_class'] = self._get_status_class(sbr.utilization)

        # Column calculations
        column_data = {
            'trib_area': f'{g.bay_x * g.bay_y:.1f}',
            'floors': f'{g.floors}',
            'load_calc': '--',
            'ecc_check': 'Interior column - no eccentricity applied',
            'size_calc': '--',
            'slenderness_calc': '--',
            'size': '--',
            'utilization': '--',
            'status_class': 'pass'
        }
        if p.column_result:
            cr = p.column_result
            trib_area = g.bay_x * g.bay_y
            total_load = design_load * trib_area * g.floors

            column_data['load_calc'] = f'{design_load:.1f} kPa × {trib_area:.1f} m² × {g.floors} floors = {total_load:.0f} kN'
            # Check if lateral loads apply
            if cr.has_lateral_loads:
                column_data['ecc_check'] = f'Moment frame system - lateral moment = {cr.lateral_moment:.0f} kNm'
            else:
                column_data['ecc_check'] = 'Interior column - no eccentricity applied'
            column_data['size_calc'] = f'Required A_c = {cr.dimension}² = {cr.dimension * cr.dimension / 1e6:.3f} m²'
            slenderness = g.story_height * 1000 / cr.dimension if cr.dimension > 0 else 0
            column_data['slenderness_calc'] = f'{g.story_height:.1f} m × 1000 / {cr.dimension} mm = {slenderness:.1f}'
            column_data['size'] = f'{cr.dimension}'
            column_data['utilization'] = f'{cr.utilization * 100:.0f}'
            column_data['status_class'] = self._get_status_class(cr.utilization)

        return {
            'slab': slab_data,
            'pri_beam': pri_beam_data,
            'sec_beam': sec_beam_data,
            'column': column_data
        }

    def generate(
        self,
        ai_review: Optional[str] = None,
        fem_results: Optional[Any] = None,
        simplified_results: Optional[Any] = None,
        fem_interpretation: Optional[Any] = None,
    ) -> str:
        """
        Generate the complete HTML report.

        Args:
            ai_review: Optional AI-generated design review commentary
            fem_results: Optional FEMResultsSummary from FEM analysis
            simplified_results: Optional SimplifiedResultsSummary for comparison
            fem_interpretation: Optional ResultsInterpretation from AI

        Returns:
            Complete HTML string ready for rendering or saving
        """
        # Determine if we have FEM results
        has_fem_results = fem_results is not None or fem_interpretation is not None
        total_pages = 5 if has_fem_results else 4

        # Build FEM data if available
        fem_data = None
        if has_fem_results:
            fem_data = self._build_fem_data(
                fem_results=fem_results,
                simplified_results=simplified_results,
                ai_interpretation=fem_interpretation,
            )

        # Build template context
        context = {
            'project': self.project,
            'css_styles': CSS_STYLES,
            'icons': SVG_ICONS,
            'overall_status': self._get_overall_status(),
            'status_elements': self._build_status_elements(),
            'metrics': {
                'total_height': f'{self.project.geometry.floors * self.project.geometry.story_height:.1f}',
                'floor_area': f'{self.project.geometry.bay_x * self.project.geometry.bay_y:.0f}',
                'carbon_intensity': f'{self.project.carbon_emission / max(1, self.project.geometry.bay_x * self.project.geometry.bay_y * self.project.geometry.floors):.0f}'
            },
            'element_summary': self._build_element_summary(),
            'framing_svg': generate_framing_svg(self.project),
            'lateral': self._build_lateral_data(),
            'drift': self._build_drift_data(),
            'carbon': self._build_carbon_data(),
            'calc': self._build_calc_data(),
            'ai_review': ai_review,
            'materials': {
                'fcu_slab': self.project.materials.fcu_slab,
                'fcu_beam': self.project.materials.fcu_beam,
                'fcu_column': self.project.materials.fcu_column
            },
            'load_factors': {
                'gamma_g': GAMMA_G,
                'gamma_q': GAMMA_Q,
                'active_combination': self._get_load_combination_name()
            },
            'geometry': {
                'bay_x': self.project.geometry.bay_x,
                'bay_y': self.project.geometry.bay_y,
                'floors': self.project.geometry.floors,
                'story_height': self.project.geometry.story_height,
                'total_height': self.project.geometry.floors * self.project.geometry.story_height,
                'tributary_area': self.project.geometry.bay_x * self.project.geometry.bay_y
            },
            'loads': {
                'live_load': f'{self.project.loads.live_load:.1f}',
                'live_load_ref': f'Class {self.project.loads.live_load_class}.{self.project.loads.live_load_sub}',
                'dead_load': f'{self.project.loads.dead_load:.1f}',
                'slab_self_weight': f'{self.project.slab_result.self_weight:.1f}' if self.project.slab_result else '—',
                'total_dead': f'{self.project.total_dead_load:.1f}',
                'design_load': f'{self.project.get_design_load():.1f}'
            },
            'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M'),
            # FEM Results (Feature 14)
            'has_fem_results': has_fem_results,
            'total_pages': total_pages,
            'fem_data': fem_data,
        }

        # Render template
        return self.template.render(**context)

    def save(
        self,
        filepath: str,
        ai_review: Optional[str] = None,
        fem_results: Optional[Any] = None,
        simplified_results: Optional[Any] = None,
        fem_interpretation: Optional[Any] = None,
    ) -> str:
        """
        Generate and save the HTML report to a file.

        Args:
            filepath: Output file path
            ai_review: Optional AI-generated design review
            fem_results: Optional FEMResultsSummary from FEM analysis
            simplified_results: Optional SimplifiedResultsSummary for comparison
            fem_interpretation: Optional ResultsInterpretation from AI

        Returns:
            The filepath where the report was saved
        """
        html = self.generate(
            ai_review=ai_review,
            fem_results=fem_results,
            simplified_results=simplified_results,
            fem_interpretation=fem_interpretation,
        )

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        return filepath


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def generate_report(
    project: ProjectData,
    filepath: Optional[str] = None,
    ai_review: Optional[str] = None,
    fem_results: Optional[Any] = None,
    simplified_results: Optional[Any] = None,
    fem_interpretation: Optional[Any] = None,
) -> str:
    """
    Convenience function to generate a report.

    Args:
        project: ProjectData with calculation results
        filepath: Optional path to save the report
        ai_review: Optional AI-generated design review
        fem_results: Optional FEMResultsSummary from FEM analysis
        simplified_results: Optional SimplifiedResultsSummary for comparison
        fem_interpretation: Optional ResultsInterpretation from AI

    Returns:
        HTML string if no filepath, otherwise the saved filepath
    """
    generator = ReportGenerator(project)

    if filepath:
        return generator.save(
            filepath=filepath,
            ai_review=ai_review,
            fem_results=fem_results,
            simplified_results=simplified_results,
            fem_interpretation=fem_interpretation,
        )
    return generator.generate(
        ai_review=ai_review,
        fem_results=fem_results,
        simplified_results=simplified_results,
        fem_interpretation=fem_interpretation,
    )
