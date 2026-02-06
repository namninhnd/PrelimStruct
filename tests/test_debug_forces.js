const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const STREAMLIT_URL = 'http://localhost:8502';
const SCREENSHOT_DIR = path.join(__dirname, 'test_screenshots', 'debug');

if (!fs.existsSync(SCREENSHOT_DIR)) {
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

async function runDebugTest() {
    console.log('Force Diagram Debug Test');
    console.log('='.repeat(50));
    
    const browser = await chromium.launch({ headless: false, slowMo: 200 });
    const context = await browser.newContext({ viewport: { width: 1920, height: 1200 } });
    const page = await context.newPage();
    
    try {
        await page.goto(STREAMLIT_URL, { waitUntil: 'networkidle', timeout: 60000 });
        await page.waitForTimeout(3000);
        
        const femHeader = page.locator('text=FEM Analysis').first();
        if (await femHeader.count() > 0) {
            await femHeader.scrollIntoViewIfNeeded();
            await page.waitForTimeout(1000);
        }
        
        const unlockButton = page.getByRole('button', { name: /Unlock/i });
        if (await unlockButton.count() > 0) {
            console.log('Analysis already run (locked state)');
        } else {
            const runButton = page.getByRole('button', { name: /Run FEM Analysis/i });
            if (await runButton.count() > 0 && !(await runButton.isDisabled())) {
                console.log('Running FEM Analysis...');
                await runButton.click();
                await page.waitForTimeout(12000);
            }
        }
        
        const elevationButton = page.getByRole('button', { name: 'Elevation View' });
        if (await elevationButton.count() > 0) {
            await elevationButton.click();
            await page.waitForTimeout(2000);
        }
        
        const displayExpander = page.locator('text=Display Options');
        if (await displayExpander.count() > 0) {
            await displayExpander.scrollIntoViewIfNeeded();
            await displayExpander.click();
            await page.waitForTimeout(1000);
        }
        
        const mzRadio = page.locator('label:has-text("Mz (Moment Z)")');
        if (await mzRadio.count() > 0) {
            await mzRadio.click({ force: true });
            await page.waitForTimeout(2000);
        }
        
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'debug_elevation_mz.png'), fullPage: true });
        console.log('Screenshot saved: debug_elevation_mz.png');
        
        const debugText = await page.locator('text=[DEBUG]').first();
        if (await debugText.count() > 0) {
            const text = await debugText.innerText();
            console.log('DEBUG OUTPUT:', text);
        } else {
            console.log('DEBUG text not found on page');
        }
        
    } catch (error) {
        console.error('Error:', error.message);
    } finally {
        await page.waitForTimeout(2000);
        await browser.close();
    }
}

runDebugTest().catch(console.error);
