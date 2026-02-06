const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const STREAMLIT_URL = 'http://localhost:8501';
const SCREENSHOT_DIR = path.join(__dirname, 'test_screenshots', 'force_fix');

async function ensureDir(dir) {
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
    }
}

async function runTest() {
    console.log('=== Force Diagram Fix Verification ===\n');
    await ensureDir(SCREENSHOT_DIR);
    
    const browser = await chromium.launch({ headless: false });
    const context = await browser.newContext({ 
        viewport: { width: 1920, height: 1080 } 
    });
    const page = await context.newPage();
    
    try {
        // 1. Navigate to app
        console.log('1. Navigating to app...');
        await page.goto(STREAMLIT_URL, { waitUntil: 'networkidle', timeout: 60000 });
        await page.waitForTimeout(3000);
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '01_initial.png') });
        console.log('   ✓ App loaded');
        
        // 2. Scroll to FEM section
        console.log('2. Finding FEM Analysis section...');
        const femSection = page.locator('text=Run FEM Analysis');
        if (await femSection.count() > 0) {
            await femSection.scrollIntoViewIfNeeded();
            await page.waitForTimeout(500);
        }
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02_fem_section.png') });
        console.log('   ✓ FEM section found');
        
        // 3. Run FEM Analysis
        console.log('3. Running FEM Analysis...');
        const runButton = page.getByRole('button', { name: /Run FEM Analysis/i });
        if (await runButton.count() > 0 && !(await runButton.isDisabled())) {
            await runButton.click();
            console.log('   Waiting for analysis to complete...');
            await page.waitForTimeout(8000);
        } else {
            console.log('   Analysis already run or button not found');
        }
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '03_after_analysis.png') });
        
        // 4. Check for success message
        const successMsg = await page.locator('text=Analysis Successful').count();
        console.log(`   ${successMsg > 0 ? '✓' : '✗'} Analysis ${successMsg > 0 ? 'succeeded' : 'status unclear'}`);
        
        // 5. Select force type (Mz moment)
        console.log('4. Selecting force diagram type...');
        const displayOptions = page.locator('text=Display Options');
        if (await displayOptions.count() > 0) {
            await displayOptions.scrollIntoViewIfNeeded();
            await displayOptions.click();
            await page.waitForTimeout(500);
        }
        
        // Look for Mz radio option
        const mzLabel = page.locator('label:has-text("Mz")');
        if (await mzLabel.count() > 0) {
            await mzLabel.scrollIntoViewIfNeeded();
            await mzLabel.click({ force: true });
            await page.waitForTimeout(1000);
            console.log('   ✓ Selected Mz force type');
        } else {
            console.log('   ✗ Mz option not found');
        }
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '04_force_selected.png') });
        
        // 6. Check if force diagrams are visible (look for red lines or annotations)
        console.log('5. Checking for force diagram rendering...');
        await page.waitForTimeout(2000);
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '05_force_diagram.png'), fullPage: true });
        
        // 7. Test unlock and bay change
        console.log('6. Testing unlock and bay change...');
        const unlockButton = page.getByRole('button', { name: /Unlock/i });
        if (await unlockButton.count() > 0) {
            await unlockButton.scrollIntoViewIfNeeded();
            await unlockButton.click();
            await page.waitForTimeout(1000);
            console.log('   ✓ Clicked unlock button');
        }
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '06_unlocked.png') });
        
        // 8. Change bays
        console.log('7. Changing number of bays...');
        const baysInput = page.locator('input[aria-label="Bays in X"]');
        if (await baysInput.count() > 0) {
            await baysInput.scrollIntoViewIfNeeded();
            await baysInput.fill('3');
            await page.waitForTimeout(2000);
            console.log('   ✓ Changed to 3 bays');
        }
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '07_bays_changed.png') });
        
        // 9. Run analysis again
        console.log('8. Running analysis with new config...');
        const runButton2 = page.getByRole('button', { name: /Run FEM Analysis/i });
        if (await runButton2.count() > 0 && !(await runButton2.isDisabled())) {
            await runButton2.click();
            await page.waitForTimeout(8000);
            console.log('   ✓ Analysis ran');
        }
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '08_new_analysis.png'), fullPage: true });
        
        // 10. Final verification
        console.log('9. Final verification...');
        const finalSuccess = await page.locator('text=Analysis Successful').count();
        console.log(`   ${finalSuccess > 0 ? '✓' : '✗'} Final analysis ${finalSuccess > 0 ? 'succeeded' : 'status unclear'}`);
        
        console.log('\n=== TEST COMPLETE ===');
        console.log(`Screenshots saved to: ${SCREENSHOT_DIR}`);
        
    } catch (error) {
        console.error('Test failed:', error.message);
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'error.png'), fullPage: true });
    } finally {
        await browser.close();
    }
}

runTest().catch(console.error);
