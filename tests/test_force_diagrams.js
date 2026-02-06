/**
 * Force Diagram Verification Test
 * 
 * This script specifically tests force diagram rendering and captures
 * screenshots with moment/shear values visible for verification.
 */
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const STREAMLIT_URL = 'http://localhost:8502';
const SCREENSHOT_DIR = path.join(__dirname, 'test_screenshots', 'force_diagrams');

if (!fs.existsSync(SCREENSHOT_DIR)) {
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

async function screenshot(page, name) {
    const filename = `${name}.png`;
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, filename), fullPage: true });
    console.log(`  Screenshot: ${filename}`);
}

async function runTest() {
    console.log('='.repeat(60));
    console.log('FORCE DIAGRAM VERIFICATION TEST');
    console.log('='.repeat(60));
    
    const browser = await chromium.launch({ headless: false, slowMo: 150 });
    const context = await browser.newContext({ viewport: { width: 1920, height: 1200 } });
    const page = await context.newPage();
    
    try {
        // 1. Load page
        console.log('\n[1] Loading Streamlit app...');
        await page.goto(STREAMLIT_URL, { waitUntil: 'networkidle', timeout: 60000 });
        await page.waitForTimeout(3000);
        
        // 2. Scroll to FEM Analysis section
        console.log('\n[2] Navigating to FEM Analysis section...');
        const femHeader = page.locator('text=FEM Analysis').first();
        if (await femHeader.count() > 0) {
            await femHeader.scrollIntoViewIfNeeded();
            await page.waitForTimeout(1000);
        }
        
        // 3. Run FEM Analysis if not already run
        console.log('\n[3] Checking FEM Analysis status...');
        const runButton = page.getByRole('button', { name: /Run FEM Analysis/i });
        const unlockButton = page.getByRole('button', { name: /Unlock/i });
        
        // If unlock button exists, analysis was already run
        if (await unlockButton.count() > 0) {
            console.log('  Analysis already completed (locked state)');
        } else if (await runButton.count() > 0) {
            const isDisabled = await runButton.isDisabled();
            if (!isDisabled) {
                console.log('  Running FEM Analysis...');
                await runButton.click();
                await page.waitForTimeout(12000); // Wait for analysis
                console.log('  Analysis complete');
            }
        }
        
        await screenshot(page, '01_after_analysis');
        
        // 4. Switch to Elevation View - this is where force diagrams are visible
        // The views are BUTTONS, not tabs!
        console.log('\n[4] Switching to Elevation View...');
        const elevationButton = page.getByRole('button', { name: 'Elevation View' });
        if (await elevationButton.count() > 0) {
            await elevationButton.click();
            await page.waitForTimeout(2000);
            console.log('  Switched to Elevation View');
            await screenshot(page, '02_elevation_view_initial');
        } else {
            console.log('  WARNING: Elevation View button not found');
        }
        
        // 5. Open Display Options expander
        console.log('\n[5] Opening Display Options...');
        const displayExpander = page.locator('text=Display Options');
        if (await displayExpander.count() > 0) {
            await displayExpander.scrollIntoViewIfNeeded();
            await displayExpander.click();
            await page.waitForTimeout(1000);
            console.log('  Display Options expanded');
        }
        
        // 6. Select Mz (Moment Z) force type
        console.log('\n[6] Selecting Mz (Moment Z) force type...');
        // The radio buttons have labels like "Mz (Moment Z)"
        const mzRadio = page.locator('label:has-text("Mz (Moment Z)")');
        if (await mzRadio.count() > 0) {
            await mzRadio.click({ force: true });
            await page.waitForTimeout(2000);
            console.log('  Selected Mz (Moment Z)');
            
            // Scroll up to see the chart
            const plotlyChart = page.locator('.js-plotly-plot').first();
            if (await plotlyChart.count() > 0) {
                await plotlyChart.scrollIntoViewIfNeeded();
            }
            await page.waitForTimeout(1000);
            await screenshot(page, '03_elevation_mz_moment');
        } else {
            console.log('  WARNING: Mz radio button not found');
            // Try alternative selector
            const forceTypeRadios = page.locator('div[data-testid="stRadio"] label');
            const count = await forceTypeRadios.count();
            console.log(`  Found ${count} radio buttons`);
            for (let i = 0; i < count; i++) {
                const text = await forceTypeRadios.nth(i).innerText();
                console.log(`    [${i}]: ${text}`);
            }
        }
        
        // 7. Select Vy (Shear Y) force type
        console.log('\n[7] Selecting Vy (Shear Y) force type...');
        const vyRadio = page.locator('label:has-text("Vy (Shear Y)")');
        if (await vyRadio.count() > 0) {
            await vyRadio.click({ force: true });
            await page.waitForTimeout(2000);
            console.log('  Selected Vy (Shear Y)');
            
            const plotlyChart = page.locator('.js-plotly-plot').first();
            if (await plotlyChart.count() > 0) {
                await plotlyChart.scrollIntoViewIfNeeded();
            }
            await page.waitForTimeout(1000);
            await screenshot(page, '04_elevation_vy_shear');
        }
        
        // 8. Switch to Plan View and check force diagrams
        console.log('\n[8] Switching to Plan View...');
        const planButton = page.getByRole('button', { name: 'Plan View' });
        if (await planButton.count() > 0) {
            await planButton.click();
            await page.waitForTimeout(2000);
            console.log('  Switched to Plan View');
            
            // Select Mz again for Plan View
            const mzRadioAgain = page.locator('label:has-text("Mz (Moment Z)")');
            if (await mzRadioAgain.count() > 0) {
                await mzRadioAgain.click({ force: true });
                await page.waitForTimeout(2000);
            }
            await screenshot(page, '05_plan_mz_moment');
        }
        
        // 9. Check for N (Axial) force in columns
        console.log('\n[9] Selecting N (Normal) force type...');
        const nRadio = page.locator('label:has-text("N (Normal)")');
        if (await nRadio.count() > 0) {
            await nRadio.click({ force: true });
            await page.waitForTimeout(2000);
            console.log('  Selected N (Normal)');
            await screenshot(page, '06_plan_n_axial');
        }
        
        // 10. Check 3D View (force diagrams not supported, just verify)
        console.log('\n[10] Switching to 3D View...');
        const view3dButton = page.getByRole('button', { name: '3D View' });
        if (await view3dButton.count() > 0) {
            await view3dButton.click();
            await page.waitForTimeout(2000);
            console.log('  Switched to 3D View');
            await screenshot(page, '07_3d_view');
        }
        
        console.log('\n' + '='.repeat(60));
        console.log('TEST COMPLETE');
        console.log('='.repeat(60));
        console.log(`\nScreenshots saved to: ${SCREENSHOT_DIR}`);
        
    } catch (error) {
        console.error('\n[ERROR]', error.message);
        await screenshot(page, 'error_state');
    } finally {
        await page.waitForTimeout(3000);
        await browser.close();
    }
}

runTest().catch(console.error);
