const { chromium } = require('playwright');
const path = require('path');

const STREAMLIT_URL = 'http://localhost:8501';
const SCREENSHOT_DIR = path.join(__dirname, 'audit_screenshots', 'force_diagram_test');

async function testBeamForceDiagramCaching() {
    console.log('=== Beam Force Diagram Caching Bug Test ===\n');
    console.log('This test verifies that beam force diagrams update correctly');
    console.log('when switching between different model configurations.\n');
    
    const browser = await chromium.launch({ headless: false, slowMo: 100 });
    const context = await browser.newContext({ 
        viewport: { width: 1920, height: 1080 } 
    });
    const page = await context.newPage();
    
    // Create screenshot directory
    const fs = require('fs');
    if (!fs.existsSync(SCREENSHOT_DIR)) {
        fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
    }
    
    let stepCount = 0;
    const screenshot = async (name) => {
        stepCount++;
        const filename = `${String(stepCount).padStart(2, '0')}_${name}.png`;
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, filename), fullPage: false });
        console.log(`   Screenshot: ${filename}`);
    };
    
    try {
        // ========== PHASE 1: First Model (2x2 bays) ==========
        console.log('\n--- PHASE 1: Build First Model (2x2 bays, 5 floors) ---');
        
        console.log('Step 1: Navigate to app...');
        await page.goto(STREAMLIT_URL, { waitUntil: 'networkidle', timeout: 60000 });
        await page.waitForTimeout(3000);
        await screenshot('01_initial_load');
        
        console.log('Step 2: Configure first model (2x2 bays, 5 floors)...');
        const baysXInput = page.locator('input[aria-label="Bays in X"]');
        if (await baysXInput.count() > 0) {
            await baysXInput.scrollIntoViewIfNeeded();
            await baysXInput.fill('2');
            await page.waitForTimeout(500);
        }
        
        const baysYInput = page.locator('input[aria-label="Bays in Y"]');
        if (await baysYInput.count() > 0) {
            await baysYInput.fill('2');
            await page.waitForTimeout(500);
        }
        
        const floorsInput = page.locator('input[aria-label="Floors"]');
        if (await floorsInput.count() > 0) {
            await floorsInput.fill('5');
            await page.waitForTimeout(1000);
        }
        await screenshot('02_model1_geometry');
        
        console.log('Step 3: Run FEM Analysis on first model...');
        const runButton1 = page.getByRole('button', { name: /Run FEM Analysis/i });
        if (await runButton1.count() > 0) {
            await runButton1.scrollIntoViewIfNeeded();
            await runButton1.click();
            console.log('   Waiting for analysis...');
            await page.waitForTimeout(8000);
        }
        await screenshot('03_model1_analyzed');
        
        console.log('Step 4: Switch to Elevation View...');
        const elevationTab = page.locator('button:has-text("Elevation View")');
        if (await elevationTab.count() > 0) {
            await elevationTab.first().click();
            await page.waitForTimeout(2000);
        }
        await screenshot('04_model1_elevation');
        
        console.log('Step 5: Select Mz (Moment Z) force type...');
        // Look for force type selector
        const forceSelector = page.locator('select:has-text("None"), [aria-label*="Force"], [aria-label*="force"]');
        const forceRadio = page.locator('label:has-text("Mz")');
        
        if (await forceRadio.count() > 0) {
            await forceRadio.first().scrollIntoViewIfNeeded();
            await forceRadio.first().click({ force: true });
            await page.waitForTimeout(2000);
        } else {
            // Try selectbox approach
            const forceSelectbox = page.locator('[aria-label="Force Type"]');
            if (await forceSelectbox.count() > 0) {
                await forceSelectbox.click();
                await page.waitForTimeout(300);
                await page.locator('li:has-text("Mz")').click();
                await page.waitForTimeout(2000);
            }
        }
        await screenshot('05_model1_mz_forces');
        
        // Record element count for first model
        const model1Stats = await page.locator('text=/\\d+ beams|\\d+ columns|\\d+ elements/i').allTextContents();
        console.log(`   Model 1 stats: ${model1Stats.join(', ')}`);
        
        // ========== PHASE 2: Unlock and Modify ==========
        console.log('\n--- PHASE 2: Unlock and Modify Model ---');
        
        console.log('Step 6: Click Unlock button...');
        const unlockButton = page.getByRole('button', { name: /Unlock/i });
        if (await unlockButton.count() > 0) {
            await unlockButton.scrollIntoViewIfNeeded();
            await unlockButton.click();
            await page.waitForTimeout(1500);
        }
        await screenshot('06_unlocked');
        
        // ========== PHASE 3: Second Model (4x4 bays) ==========
        console.log('\n--- PHASE 3: Build Second Model (4x4 bays, 10 floors) ---');
        
        console.log('Step 7: Configure second model (4x4 bays, 10 floors)...');
        const baysXInput2 = page.locator('input[aria-label="Bays in X"]');
        if (await baysXInput2.count() > 0) {
            await baysXInput2.scrollIntoViewIfNeeded();
            await baysXInput2.fill('4');
            await page.waitForTimeout(500);
        }
        
        const baysYInput2 = page.locator('input[aria-label="Bays in Y"]');
        if (await baysYInput2.count() > 0) {
            await baysYInput2.fill('4');
            await page.waitForTimeout(500);
        }
        
        const floorsInput2 = page.locator('input[aria-label="Floors"]');
        if (await floorsInput2.count() > 0) {
            await floorsInput2.fill('10');
            await page.waitForTimeout(1000);
        }
        await screenshot('07_model2_geometry');
        
        console.log('Step 8: Run FEM Analysis on second model...');
        const runButton2 = page.getByRole('button', { name: /Run FEM Analysis/i });
        if (await runButton2.count() > 0 && !await runButton2.isDisabled()) {
            await runButton2.scrollIntoViewIfNeeded();
            await runButton2.click();
            console.log('   Waiting for analysis...');
            await page.waitForTimeout(12000);
        }
        await screenshot('08_model2_analyzed');
        
        console.log('Step 9: Switch to Elevation View for second model...');
        const elevationTab2 = page.locator('button:has-text("Elevation View")');
        if (await elevationTab2.count() > 0) {
            await elevationTab2.first().click();
            await page.waitForTimeout(2000);
        }
        await screenshot('09_model2_elevation');
        
        console.log('Step 10: Verify Mz forces update for new model...');
        // Re-select Mz to trigger force diagram
        const forceRadio2 = page.locator('label:has-text("Mz")');
        if (await forceRadio2.count() > 0) {
            await forceRadio2.first().scrollIntoViewIfNeeded();
            await forceRadio2.first().click({ force: true });
            await page.waitForTimeout(3000);
        }
        await screenshot('10_model2_mz_forces');
        
        // Record element count for second model
        const model2Stats = await page.locator('text=/\\d+ beams|\\d+ columns|\\d+ elements/i').allTextContents();
        console.log(`   Model 2 stats: ${model2Stats.join(', ')}`);
        
        // ========== PHASE 4: Visual Comparison ==========
        console.log('\n--- PHASE 4: Visual Verification ---');
        
        console.log('Step 11: Check 3D View for model verification...');
        const view3dTab = page.locator('button:has-text("3D View")');
        if (await view3dTab.count() > 0) {
            await view3dTab.first().click();
            await page.waitForTimeout(2000);
        }
        await screenshot('11_model2_3d_view');
        
        console.log('Step 12: Final Plan View check...');
        const planTab = page.locator('button:has-text("Plan View")');
        if (await planTab.count() > 0) {
            await planTab.first().click();
            await page.waitForTimeout(2000);
        }
        await screenshot('12_model2_plan_view');
        
        // ========== SUMMARY ==========
        console.log('\n=== TEST SUMMARY ===');
        console.log(`Total screenshots: ${stepCount}`);
        console.log(`Screenshot directory: ${SCREENSHOT_DIR}`);
        console.log('');
        console.log('VERIFICATION CHECKLIST:');
        console.log('  [ ] Compare 05_model1_mz_forces.png vs 10_model2_mz_forces.png');
        console.log('  [ ] Model 2 should show MORE beam force lines (4x4 vs 2x2)');
        console.log('  [ ] Model 2 should show TALLER building (10 vs 5 floors)');
        console.log('  [ ] Force diagram scale should be consistent');
        console.log('');
        console.log('If screenshots 05 and 10 look the same, the CACHING BUG is confirmed.');
        console.log('');
        console.log('=== TEST COMPLETE ===\n');
        
    } catch (error) {
        console.error('\n=== TEST FAILED ===');
        console.error('Error:', error.message);
        await screenshot('error_state');
        throw error;
    } finally {
        await browser.close();
    }
}

testBeamForceDiagramCaching().catch(error => {
    console.error('Test execution failed:', error);
    process.exit(1);
});
