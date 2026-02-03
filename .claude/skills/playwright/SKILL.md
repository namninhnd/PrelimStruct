# Playwright Browser Automation

**MUST USE** for any browser-related tasks. Browser automation via Playwright MCP server and direct Node.js usage.

## Overview

This skill provides comprehensive browser automation using Playwright. It supports:
- Playwright MCP server for agent-driven browser control
- Direct Node.js Playwright API for custom scripts
- Testing, scraping, and UI automation
- **Streamlit apps** (special patterns included)

---

## CRITICAL: Agent Invocation Priority

When delegating Playwright tasks to subagents, **USE `task` tool, NOT `delegate_task`**.

### Why Task Tool Over delegate_task?

| Aspect | `task` tool | `delegate_task` |
|--------|-------------|-----------------|
| **Context** | Full skill injection | Category-based, may miss details |
| **Reliability** | Direct subagent spawn | Extra routing layer |
| **Skill loading** | Automatic from prompt | Requires explicit `load_skills` |
| **Recommended for** | Playwright, specialized work | General categorized tasks |

### Correct Pattern

```javascript
// ✅ CORRECT: Use task tool with playwright subagent
task(
  subagent_type="build",  // or specific agent type
  description="Run Playwright FEM audit",
  prompt=`
    Load the playwright skill and execute browser automation:
    1. Navigate to http://localhost:8501
    2. Run FEM analysis
    3. Take screenshots of results
    4. Verify lock indicator appears
    
    Use the patterns from the playwright skill for Streamlit apps.
  `
)

// ❌ AVOID: delegate_task for Playwright work
delegate_task(
  category="quick",
  load_skills=["playwright"],
  prompt="..."
)
```

### When to Use Each

| Scenario | Use |
|----------|-----|
| Browser automation, testing, scraping | `task` with playwright skill |
| Quick file edits, simple changes | `delegate_task` with category |
| Frontend UI work | `delegate_task` with visual-engineering |
| Research/exploration | `delegate_task` with explore/librarian |

---

## Part 1: Quick Start

### Installation

```bash
# Global installation
npm install -g playwright
npx playwright install chromium

# Local project installation
npm init -y
npm install playwright
npx playwright install chromium

# Verify installation
npx playwright install --list
```

### Basic Usage

```javascript
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();
  
  await page.goto('https://example.com');
  console.log('Page title:', await page.title());
  await page.screenshot({ path: 'screenshot.png' });
  
  await browser.close();
})();
```

---

## Part 2: MCP Server Tools

Use `skill_mcp` with `mcp_name="playwright"`:

### Navigation
- `browser_navigate` - Navigate to a URL
- `browser_navigate_back` - Go back to previous page

### Page Interaction
- `browser_click` - Click on an element
- `browser_type` - Type text into an input field
- `browser_fill_form` - Fill multiple form fields
- `browser_select_option` - Select dropdown option
- `browser_drag` - Drag and drop elements
- `browser_hover` - Hover over an element
- `browser_press_key` - Press keyboard keys

### Information Extraction
- `browser_snapshot` - Get accessibility snapshot (use this for identifying elements)
- `browser_take_screenshot` - Capture page screenshot
- `browser_evaluate` - Run JavaScript on the page

### Tab Management
- `browser_tabs` - List, create, close, or select tabs

### Monitoring
- `browser_network_requests` - Get network requests
- `browser_console_messages` - Get console messages
- `browser_wait_for` - Wait for text or time

---

## Part 3: Official Best Practices

### 1. Test User-Visible Behavior
- Verify what end users see/interact with
- Avoid implementation details (function names, CSS classes)
- Focus on rendered output and user interactions

### 2. Use Web-First Assertions

```typescript
// ✅ DO: Auto-waits and retries
await expect(page.getByText('welcome')).toBeVisible();
await expect(page).toHaveTitle(/Playwright/);
await expect(page).toHaveURL(/login/);

// ❌ DON'T: Doesn't wait or retry
expect(await page.getByText('welcome').isVisible()).toBe(true);
```

### 3. Locator Priority (Most to Least Resilient)

| Priority | Method | Use Case |
|----------|--------|----------|
| 1 | `page.getByRole()` | User-facing, accessibility-first |
| 2 | `page.getByLabel()` | Form controls with labels |
| 3 | `page.getByText()` | Non-interactive elements |
| 4 | `page.getByTestId()` | Most resilient, but not user-facing |
| 5 | `page.locator()` with CSS/XPath | ❌ NOT recommended |

```typescript
// Priority 1: Role-based (best)
await page.getByRole('button', { name: 'Submit' }).click();
await page.getByRole('checkbox', { name: 'Subscribe' }).check();

// Priority 2: Label-based
await page.getByLabel('Email address').fill('test@example.com');

// Priority 3: Text-based
await expect(page.getByText('Welcome, John')).toBeVisible();

// Priority 4: Test ID
await page.getByTestId('submit-button').click();
```

### 4. Advanced Locator Patterns

```typescript
// Chaining and Filtering
const product = page.getByRole('listitem').filter({ hasText: 'Product 2' });
await product.getByRole('button', { name: 'Add to cart' }).click();

// Filter by child/descendant
await page
  .getByRole('listitem')
  .filter({ has: page.getByRole('heading', { name: 'Product 2' }) })
  .getByRole('button', { name: 'Add to cart' })
  .click();

// Alternative locators (OR logic)
const newEmail = page.getByRole('button', { name: 'New' });
const dialog = page.getByText('Confirm security settings');
await expect(newEmail.or(dialog).first()).toBeVisible();
```

### 5. Auto-Waiting (Playwright Handles This)

Playwright automatically waits for elements to be:
- Attached to DOM
- Visible
- Stable (not animating)
- Enabled
- Receives events (not obscured)

```typescript
// Automatically waits for element
await page.getByRole('button').click();
```

**⚠️ Exception:** Streamlit apps may need explicit waits due to full-page reruns.

### 6. Dialog Handling

```typescript
// Auto-dismiss by default (no handler needed for simple cases)

// Custom handling
page.on('dialog', dialog => dialog.accept());
await page.getByRole('button').click();

// With prompt value
page.on('dialog', dialog => dialog.accept('answer!'));

// Dismiss dialog
page.on('dialog', dialog => dialog.dismiss());
```

**⚠️ CRITICAL:** Dialog handlers MUST handle the dialog, or actions will stall!

### 7. Page Object Model (POM)

```typescript
export class PlaywrightDevPage {
  readonly page: Page;
  readonly getStartedLink: Locator;
  
  constructor(page: Page) {
    this.page = page;
    this.getStartedLink = page.locator('a', { hasText: 'Get started' });
  }
  
  async goto() {
    await this.page.goto('https://playwright.dev');
  }
  
  async getStarted() {
    await this.getStartedLink.first().click();
  }
}

// Usage:
const playwrightDev = new PlaywrightDevPage(page);
await playwrightDev.goto();
await playwrightDev.getStarted();
```

### 8. Configuration Best Practices

```typescript
// playwright.config.ts
export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  
  use: {
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    baseURL: 'http://localhost:3000',
  },
  
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
  ],
});
```

---

## Part 4: Streamlit-Specific Patterns

Streamlit apps have unique DOM structures and behavior that require special handling.

### Key Difference: Streamlit Reruns

Streamlit reruns the entire app on input changes, which can cause elements to detach. Always re-query elements after actions that trigger reruns.

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

### Radio Buttons (TRICKY!)

Streamlit radio buttons have hidden inputs. Click the label instead.

```javascript
// BAD: Click hidden radio input - often fails
await page.getByRole('radio', { name: /Mz/i }).click();

// GOOD: Click the visible label
const label = page.locator('label:has-text("Mz (Moment Z)")');
await label.scrollIntoViewIfNeeded();
await label.click();

// Alternative: Force click on radio
await page.getByRole('radio', { name: /Mz/i }).click({ force: true });
```

### Expanders

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
// Sidebar may need scroll
await page.evaluate(() => {
    const sidebar = document.querySelector('[data-testid="stSidebar"]');
    if (sidebar) sidebar.scrollTop = 0;
});

// Interact with sidebar element
await page.locator('[data-testid="stSidebar"] input[aria-label="Floors"]').fill('10');
```

---

## Part 5: Scrolling Strategies

Elements outside viewport often fail clicks. Always scroll into view first.

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
    const el = document.querySelector('h3');
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
});

// Using Playwright's built-in method (preferred)
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

### Scroll Before Click Pattern

```javascript
// BAD: Click without ensuring visibility
await page.click('button:has-text("Submit")');

// GOOD: Scroll into view, then click
const button = page.locator('button:has-text("Submit")');
await button.scrollIntoViewIfNeeded();
await page.waitForTimeout(300);
await button.click();
```

---

## Part 6: Waiting Strategies

### When Auto-Wait Works

Standard web apps with predictable rendering:
```typescript
// Playwright auto-waits - no manual wait needed
await page.getByRole('button').click();
```

### When Manual Waits Are Needed

Streamlit apps or apps with async rendering:

```javascript
// Wait after navigation
await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
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

## Part 7: Screenshots

### Full Page vs Viewport

```javascript
// Full page (entire scrollable content)
await page.screenshot({ path: 'full.png', fullPage: true });

// Viewport only (what's visible)
await page.screenshot({ path: 'viewport.png', fullPage: false });
```

### Element Screenshots

```javascript
const chart = page.locator('.plotly-chart');
await chart.screenshot({ path: 'chart.png' });
```

### Before/After Pattern

```javascript
await page.screenshot({ path: 'before_click.png' });
await page.click('button:has-text("Analyze")');
await page.waitForTimeout(3000);
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

## Part 8: Debugging

### Slow Down Execution

```javascript
const browser = await chromium.launch({ 
    headless: false,
    slowMo: 500  // 500ms delay between actions
});
```

### Pause for Inspection

```javascript
await page.pause(); // Opens Playwright Inspector
```

### Console Logging

```javascript
page.on('console', msg => console.log('PAGE:', msg.text()));
```

### Screenshot at Each Step

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

### Trace Recording

```javascript
await context.tracing.start({ screenshots: true, snapshots: true });

// ... your test code ...

await context.tracing.stop({ path: 'trace.zip' });
// Open with: npx playwright show-trace trace.zip
```

### Playwright Inspector & Codegen

```bash
npx playwright test --debug
npx playwright codegen https://example.com  # Generate tests
```

---

## Part 9: Anti-Patterns

### 1. Not Checking Element Existence

```javascript
// BAD
await page.click('button:has-text("Optional Feature")');

// GOOD
const button = page.locator('button:has-text("Optional Feature")');
if (await button.count() > 0) {
    await button.click();
}
```

### 2. Hardcoded Sleep Instead of Condition

```javascript
// BAD
await page.waitForTimeout(10000);

// GOOD
await page.waitForSelector('.results-loaded', { timeout: 10000 });
```

### 3. Using CSS/XPath When Better Options Exist

```javascript
// BAD
await page.locator('#submit-btn').click();
await page.locator('//button[@class="primary"]').click();

// GOOD
await page.getByRole('button', { name: 'Submit' }).click();
```

### 4. Clicking Hidden Elements (Streamlit Radios)

```javascript
// BAD
await page.click('input[type="radio"]');

// GOOD
await page.click('input[type="radio"]', { force: true });
// OR
await page.click('label:has-text("Option A")');
```

### 5. Forgetting to Handle Dialogs

```javascript
// BAD: Dialog will stall the test
await page.click('button:has-text("Delete")');

// GOOD: Set up handler before triggering dialog
page.on('dialog', dialog => dialog.accept());
await page.click('button:has-text("Delete")');
```

---

## Part 10: Complete Templates

### Streamlit Test Template

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

### TypeScript Test Template (with POM)

```typescript
import { test, expect, Page, Locator } from '@playwright/test';

class LoginPage {
  readonly page: Page;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly submitButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.emailInput = page.getByLabel('Email');
    this.passwordInput = page.getByLabel('Password');
    this.submitButton = page.getByRole('button', { name: 'Sign in' });
  }

  async goto() {
    await this.page.goto('/login');
  }

  async login(email: string, password: string) {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.submitButton.click();
  }
}

test('user can login', async ({ page }) => {
  const loginPage = new LoginPage(page);
  await loginPage.goto();
  await loginPage.login('test@example.com', 'password123');
  await expect(page).toHaveURL(/dashboard/);
});
```

---

## Part 11: Troubleshooting

| Issue | Solution |
|-------|----------|
| Element not found | Add scroll + wait before interaction |
| Click has no effect | Try `click({ force: true })` or click label instead |
| Stale element | Re-query element after Streamlit reruns |
| Timeout on navigation | Increase timeout, check if app is running |
| Wrong element clicked | Use more specific locator (aria-label, data-testid) |
| Radio button won't select | Click the label text, not the hidden input |
| Dialog stalls test | Add `page.on('dialog', ...)` handler |
| "browserType.launchPersistentContext: spawn UNKNOWN" | Use direct Node.js API instead of MCP |
| "Cannot find module 'playwright'" | Run `npm install playwright && npx playwright install chromium` |

---

## Part 12: Checklist

### Before Running Tests
- [ ] Target app is running (e.g., `streamlit run app.py`)
- [ ] Screenshots directory exists
- [ ] Playwright installed (`npm install playwright`)
- [ ] Browser binaries installed (`npx playwright install chromium`)

### DOs
- ✅ Use role-based locators (`getByRole`) - most resilient
- ✅ Use web-first assertions - auto-wait and retry
- ✅ Scroll elements into view before clicking
- ✅ Re-query elements after Streamlit reruns
- ✅ Handle dialogs before triggering them
- ✅ Take screenshots on error for debugging
- ✅ Use Trace Viewer for CI debugging

### DON'Ts
- ❌ Use CSS/XPath locators - fragile
- ❌ Use manual assertions without waiting
- ❌ Assume elements are visible without scrolling
- ❌ Forget to handle dialogs
- ❌ Cache element references across Streamlit reruns

---

## Resources

- **Official Docs**: https://playwright.dev/docs/best-practices
- **Locators Guide**: https://playwright.dev/docs/locators
- **Trace Viewer**: https://playwright.dev/docs/trace-viewer
- **Page Object Models**: https://playwright.dev/docs/pom
- **GitHub**: https://github.com/microsoft/playwright
