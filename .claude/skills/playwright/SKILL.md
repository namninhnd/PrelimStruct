# Playwright Browser Automation Skill

## Overview

Playwright is a browser automation library for end-to-end testing and web scraping. This guide covers effective patterns for automating web applications, with special focus on Streamlit apps.

## Quick Reference

```javascript
const { chromium } = require('playwright');

const browser = await chromium.launch({ headless: false });
const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
const page = await context.newPage();

await page.goto('http://localhost:8501');
// ... automation code
await browser.close();
```

## Core Principles

### 1. Always Wait for Stability

Never assume elements are ready immediately. Streamlit apps especially have async rendering.

```javascript
// BAD: Immediate action after navigation
await page.goto(url);
await page.click('button');

// GOOD: Wait for network idle + explicit wait
await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
await page.waitForTimeout(2000);
await page.click('button');
```

### 2. Scroll Before Interact

Elements outside viewport often fail clicks. Always scroll into view first.

```javascript
// BAD: Click without ensuring visibility
await page.click('button:has-text("Submit")');

// GOOD: Scroll into view, then click
const button = page.locator('button:has-text("Submit")');
await button.scrollIntoViewIfNeeded();
await page.waitForTimeout(300);
await button.click();
```

### 3. Use Multiple Locator Strategies

Have fallbacks when primary locator fails.

```javascript
// Primary: By role
let element = page.getByRole('button', { name: /Run Analysis/i });

// Fallback 1: By text
if (await element.count() === 0) {
    element = page.locator('button:has-text("Run Analysis")');
}

// Fallback 2: By data attribute
if (await element.count() === 0) {
    element = page.locator('[data-testid="run-analysis-btn"]');
}
```

---

## Streamlit-Specific Patterns

Streamlit apps have unique DOM structures that require special handling.

### Input Fields

Streamlit inputs have `aria-label` attributes matching their labels.

```javascript
// Number inputs
const baysX = page.locator('input[aria-label="Bays in X"]');
await baysX.fill('3');

// Text inputs
const projectName = page.locator('input[aria-label="Project Name"]');
await projectName.fill('Test Project');

// Sliders (use keyboard)
const slider = page.locator('[aria-label="Story Height"]');
await slider.focus();
await page.keyboard.press('ArrowRight');
```

### Buttons

```javascript
// Standard button
await page.getByRole('button', { name: /Run FEM Analysis/i }).click();

// Button with emoji
await page.getByRole('button', { name: /🔓 Unlock/i }).click();

// Disabled button check
const isDisabled = await page.locator('button:has-text("Run")').isDisabled();
```

### Radio Buttons

Streamlit radio buttons are tricky - the actual input is hidden. Click the label instead.

```javascript
// BAD: Click hidden radio input
await page.getByRole('radio', { name: /Mz/i }).click(); // Often fails

// GOOD: Click the visible label
const label = page.locator('label:has-text("Mz (Moment Z)")');
await label.scrollIntoViewIfNeeded();
await label.click();

// Alternative: Force click on radio
await page.getByRole('radio', { name: /Mz/i }).click({ force: true });
```

### Expanders

Streamlit expanders need to be clicked to reveal content.

```javascript
// Click expander to open
const expander = page.getByText('Display Options');
await expander.scrollIntoViewIfNeeded();
await expander.click();
await page.waitForTimeout(500); // Wait for animation

// Now interact with content inside
await page.locator('label:has-text("Show nodes")').click();
```

### Selectboxes

```javascript
// Open selectbox
await page.locator('[aria-label="Load Case"]').click();
await page.waitForTimeout(300);

// Select option
await page.locator('li:has-text("ULS Gravity")').click();
```

### Tabs

```javascript
// Click tab
await page.locator('[data-baseweb="tab"]:has-text("Elevation View")').click();
await page.waitForTimeout(1000); // Wait for content to render
```

### Sidebar

```javascript
// Sidebar is usually visible, but may need scroll
await page.evaluate(() => {
    const sidebar = document.querySelector('[data-testid="stSidebar"]');
    if (sidebar) sidebar.scrollTop = 0;
});

// Interact with sidebar element
await page.locator('[data-testid="stSidebar"] input[aria-label="Floors"]').fill('10');
```

---

## Scrolling Strategies

### Page-Level Scroll

```javascript
// Scroll by pixels
await page.evaluate(() => window.scrollBy(0, 400));

// Scroll to bottom
await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));

// Scroll to top
await page.evaluate(() => window.scrollTo(0, 0));
```

### Element-Based Scroll

```javascript
// Scroll element into view (centered)
await page.evaluate(() => {
    const el = document.querySelector('h3:has-text("FEM Analysis")');
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
});

// Using Playwright's built-in method
await page.locator('h3:has-text("FEM Analysis")').scrollIntoViewIfNeeded();
```

### Container Scroll

```javascript
// Scroll within a specific container
await page.evaluate(() => {
    const container = document.querySelector('.main-content');
    if (container) container.scrollTop += 300;
});
```

---

## Waiting Strategies

### Explicit Waits

```javascript
// Fixed timeout (use sparingly)
await page.waitForTimeout(2000);

// Wait for element
await page.waitForSelector('button:has-text("Success")', { timeout: 10000 });

// Wait for element to be visible
await page.locator('.result-panel').waitFor({ state: 'visible' });

// Wait for element to be hidden
await page.locator('.loading-spinner').waitFor({ state: 'hidden' });
```

### Network Waits

```javascript
// Wait for all network requests to complete
await page.waitForLoadState('networkidle');

// Wait for specific request
await page.waitForResponse(response => 
    response.url().includes('/api/analyze') && response.status() === 200
);
```

### Content-Based Waits

```javascript
// Wait for text to appear
await page.waitForSelector('text=Analysis Complete');

// Wait for text to disappear
await page.waitForFunction(() => 
    !document.body.textContent.includes('Loading...')
);

// Wait for element count
await page.waitForFunction(() => 
    document.querySelectorAll('.data-row').length >= 10
);
```

---

## Screenshot Best Practices

### Full Page vs Viewport

```javascript
// Full page (entire scrollable content)
await page.screenshot({ path: 'full.png', fullPage: true });

// Viewport only (what's visible)
await page.screenshot({ path: 'viewport.png', fullPage: false });
```

### Element Screenshots

```javascript
// Screenshot specific element
const chart = page.locator('.plotly-chart');
await chart.screenshot({ path: 'chart.png' });
```

### Before/After Pattern

```javascript
// Before action
await page.screenshot({ path: 'before_click.png' });

// Perform action
await page.click('button:has-text("Analyze")');
await page.waitForTimeout(3000);

// After action
await page.screenshot({ path: 'after_click.png' });
```

### Screenshot on Error

```javascript
try {
    await riskyOperation();
} catch (error) {
    await page.screenshot({ path: 'error_state.png', fullPage: true });
    throw error;
}
```

---

## Common Anti-Patterns

### 1. Not Checking Element Existence

```javascript
// BAD: Assumes element exists
await page.click('button:has-text("Optional Feature")');

// GOOD: Check first
const button = page.locator('button:has-text("Optional Feature")');
if (await button.count() > 0) {
    await button.click();
} else {
    console.log('Button not found, skipping');
}
```

### 2. Hardcoded Sleep Instead of Condition

```javascript
// BAD: Arbitrary wait
await page.waitForTimeout(10000);

// GOOD: Wait for condition
await page.waitForSelector('.results-loaded', { timeout: 10000 });
```

### 3. Not Handling Streamlit Reruns

Streamlit reruns the entire app on input changes, which can cause elements to detach.

```javascript
// BAD: Reference element, then wait, then use
const button = page.locator('button');
await page.fill('input', 'value'); // This triggers rerun
await button.click(); // Button reference may be stale!

// GOOD: Re-query after actions that cause reruns
await page.fill('input', 'value');
await page.waitForTimeout(1000); // Wait for rerun
await page.locator('button').click(); // Fresh query
```

### 4. Clicking Hidden Elements

```javascript
// BAD: Click without visibility check
await page.click('input[type="radio"]');

// GOOD: Use force for intentionally hidden inputs, or click label
await page.click('input[type="radio"]', { force: true });
// OR
await page.click('label:has-text("Option A")');
```

---

## Debugging Tips

### 1. Slow Down Execution

```javascript
const browser = await chromium.launch({ 
    headless: false,
    slowMo: 500  // 500ms delay between actions
});
```

### 2. Pause for Inspection

```javascript
await page.pause(); // Opens Playwright Inspector
```

### 3. Console Logging from Page

```javascript
page.on('console', msg => console.log('PAGE:', msg.text()));
```

### 4. Screenshot at Each Step

```javascript
let step = 0;
const screenshot = async (name) => {
    step++;
    await page.screenshot({ path: `debug_${step}_${name}.png` });
};

await screenshot('initial');
await page.click('button');
await screenshot('after_click');
```

### 5. Trace Recording

```javascript
await context.tracing.start({ screenshots: true, snapshots: true });

// ... your test code ...

await context.tracing.stop({ path: 'trace.zip' });
// Open with: npx playwright show-trace trace.zip
```

---

## Complete Test Template

```javascript
const { chromium } = require('playwright');
const path = require('path');

const STREAMLIT_URL = 'http://localhost:8501';
const SCREENSHOT_DIR = path.join(__dirname, '..', 'screenshots');

async function runTest() {
    console.log('Starting test...');
    
    const browser = await chromium.launch({ headless: false });
    const context = await browser.newContext({ 
        viewport: { width: 1920, height: 1080 } 
    });
    const page = await context.newPage();
    
    try {
        // 1. Navigate
        console.log('1. Navigating...');
        await page.goto(STREAMLIT_URL, { waitUntil: 'networkidle', timeout: 60000 });
        await page.waitForTimeout(3000);
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '01_initial.png') });
        
        // 2. Configure inputs
        console.log('2. Configuring inputs...');
        const input = page.locator('input[aria-label="Floors"]');
        if (await input.count() > 0) {
            await input.scrollIntoViewIfNeeded();
            await input.fill('10');
            await page.waitForTimeout(1000);
        }
        
        // 3. Click action button
        console.log('3. Running action...');
        const runButton = page.getByRole('button', { name: /Run/i });
        if (await runButton.count() > 0) {
            await runButton.scrollIntoViewIfNeeded();
            await runButton.click();
            await page.waitForTimeout(5000);
            await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02_after_run.png') });
        }
        
        // 4. Verify results
        console.log('4. Verifying results...');
        const successIndicator = await page.locator('text=Success').count();
        console.log(`   Success indicator found: ${successIndicator > 0}`);
        
        // 5. Final screenshot
        console.log('5. Final screenshot...');
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '03_final.png'), fullPage: true });
        
        console.log('\n=== TEST COMPLETE ===');
        
    } catch (error) {
        console.error('Test failed:', error.message);
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'error.png'), fullPage: true });
    } finally {
        await browser.close();
    }
}

runTest().catch(console.error);
```

---

## Checklist Before Running

- [ ] Streamlit app is running (`streamlit run app.py`)
- [ ] Screenshots directory exists
- [ ] Playwright is installed (`npm install playwright`)
- [ ] Browser binaries installed (`npx playwright install chromium`)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Element not found | Add scroll + wait before interaction |
| Click has no effect | Try `click({ force: true })` or click label instead |
| Stale element | Re-query element after Streamlit reruns |
| Timeout on navigation | Increase timeout, check if app is running |
| Wrong element clicked | Use more specific locator (aria-label, data-testid) |
| Radio button won't select | Click the label text, not the hidden input |
