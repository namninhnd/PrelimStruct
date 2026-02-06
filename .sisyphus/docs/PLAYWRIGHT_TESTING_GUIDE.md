# Playwright Testing Guide for PrelimStruct

## Quick Start

```bash
cd "C:\Users\daokh\Desktop\PrelimStruct v3-5"

# 1. Start Streamlit (if not running)
powershell -Command "Start-Process -FilePath 'streamlit' -ArgumentList 'run', 'app.py', '--server.headless', 'true' -WindowStyle Hidden"

# 2. Wait for app to start
ping -n 6 127.0.0.1 >nul && netstat -an | findstr ":8501"

# 3. Run test script
node test_script.js
```

## Minimal Test Template

```javascript
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const URL = 'http://localhost:8501';
const SCREENSHOTS = path.join(__dirname, 'test_screenshots', 'test_name');

async function run() {
    fs.mkdirSync(SCREENSHOTS, { recursive: true });
    
    const browser = await chromium.launch({ headless: false });
    const page = await (await browser.newContext({ 
        viewport: { width: 1920, height: 1080 } 
    })).newPage();
    
    try {
        await page.goto(URL, { waitUntil: 'networkidle', timeout: 60000 });
        await page.waitForTimeout(3000);
        
        // YOUR TEST CODE HERE
        
        await page.screenshot({ path: path.join(SCREENSHOTS, 'result.png') });
    } finally {
        await browser.close();
    }
}

run().catch(console.error);
```

## Streamlit-Specific Patterns

### Inputs
```javascript
// Number/text input
await page.locator('input[aria-label="Bays in X"]').fill('3');

// Wait after input (Streamlit reruns)
await page.waitForTimeout(1000);
```

### Buttons
```javascript
// Standard button
await page.getByRole('button', { name: /Run FEM Analysis/i }).click();

// Wait for action to complete
await page.waitForTimeout(5000);
```

### Radio Buttons (TRICKY!)
```javascript
// Click label, not hidden input
await page.locator('label:has-text("Mz")').click({ force: true });
```

### Expanders
```javascript
await page.locator('text=Display Options').click();
await page.waitForTimeout(500);
```

### Scroll Before Click
```javascript
const elem = page.locator('button:has-text("Submit")');
await elem.scrollIntoViewIfNeeded();
await elem.click();
```

## Key Timeouts

| Action | Wait Time |
|--------|-----------|
| After page.goto() | 3000ms |
| After input change | 1000ms |
| After button click (simple) | 1000ms |
| After FEM analysis | 8000ms |
| After expander open | 500ms |

## Verification Patterns

```javascript
// Check element exists
const count = await page.locator('text=Analysis Successful').count();
console.log(count > 0 ? '✓ Found' : '✗ Not found');

// Check button disabled
const disabled = await page.locator('button:has-text("Run")').isDisabled();
```

## Screenshot Evidence

```javascript
// Viewport only
await page.screenshot({ path: 'view.png' });

// Full page (scrollable)
await page.screenshot({ path: 'full.png', fullPage: true });
```

## Common Issues

| Issue | Solution |
|-------|----------|
| Element not found | Add `scrollIntoViewIfNeeded()` |
| Click no effect | Use `click({ force: true })` |
| Stale element | Re-query after Streamlit rerun |
| Radio won't select | Click label text instead |

## File Locations

- Test scripts: Project root (`test_*.js`)
- Screenshots: `test_screenshots/<test_name>/`
- Evidence: `.sisyphus/evidence/`
