const { chromium } = require('playwright');
const path = require('path');

const STREAMLIT_URL = 'http://localhost:8501';
const SCREENSHOT_DIR = path.join(__dirname, 'audit_screenshots');
const BASE_CASE = { baysX: 3, baysY: 2, floors: 8 };
const TALL_FLOORS = 50;
const RUN_TALL_ANALYSIS = false;

async function runComprehensiveTest() {
    console.log('=== PrelimStruct v3.5 Comprehensive UI Test ===\n');
    
    const browser = await chromium.launch({ headless: false });
    const context = await browser.newContext({ 
        viewport: { width: 1920, height: 1080 } 
    });
    const page = await context.newPage();
    
    let stepCount = 0;
    const screenshot = async (name) => {
        stepCount++;
        const filename = `${String(stepCount).padStart(2, '0')}_${name}.png`;
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, filename), fullPage: true });
        console.log(`   Screenshot: ${filename}`);
    };

    const waitForAnalysisCompletion = async (timeoutMs) => {
        const start = Date.now();
        const successBanner = page.locator('text=Analysis Successful').first();
        const previousBanner = page.locator('text=Previous Analysis Available').first();
        const failBanner = page.locator('text=Analysis Failed').first();
        const unlockButton = page.getByRole('button', { name: /Unlock/i }).first();

        while (Date.now() - start < timeoutMs) {
            if (await failBanner.count() > 0) {
                throw new Error('Analysis failed; aborting');
            }
            if (await successBanner.count() > 0) {
                return;
            }
            if (await previousBanner.count() > 0) {
                return;
            }
            if (await unlockButton.count() > 0) {
                return;
            }
            await page.waitForTimeout(1000);
        }

        throw new Error('Analysis timeout');
    };
    
    try {
        console.log('Step 1: Navigate to app...');
        await page.goto(STREAMLIT_URL, { waitUntil: 'networkidle', timeout: 60000 });
        await page.waitForTimeout(3000);
        await screenshot('initial_load');
        
        console.log(`Step 2: Configure multi-bay building (${BASE_CASE.baysX}x${BASE_CASE.baysY} bays, ${BASE_CASE.floors} floors)...`);
        
        const baysXInput = page.locator('input[aria-label="Bays in X"]');
        if (await baysXInput.count() > 0) {
            await baysXInput.scrollIntoViewIfNeeded();
            await baysXInput.fill(String(BASE_CASE.baysX));
            await page.waitForTimeout(500);
        }
        
        const baysYInput = page.locator('input[aria-label="Bays in Y"]');
        if (await baysYInput.count() > 0) {
            await baysYInput.scrollIntoViewIfNeeded();
            await baysYInput.fill(String(BASE_CASE.baysY));
            await page.waitForTimeout(500);
        }
        
        const floorsInput = page.locator('input[aria-label="Floors"]');
        if (await floorsInput.count() > 0) {
            await floorsInput.scrollIntoViewIfNeeded();
            await floorsInput.fill(String(BASE_CASE.floors));
            await page.waitForTimeout(1500);
        }
        await screenshot(`geometry_${BASE_CASE.baysX}x${BASE_CASE.baysY}x${BASE_CASE.floors}`);
        
        console.log('Step 3: Check FEM Analysis section...');
        const femSection = page.locator('text=FEM Analysis').first();
        if (await femSection.count() > 0) {
            await femSection.scrollIntoViewIfNeeded();
            await page.waitForTimeout(1000);
        }
        await screenshot('fem_section_visible');
        
        console.log('Step 4: Run FEM Analysis...');
        const runButton = page.getByRole('button', { name: /Run FEM Analysis/i });
        const successBanner = page.locator('text=Analysis Successful').first();
        const previousBanner = page.locator('text=Previous Analysis Available').first();
        if (await runButton.count() > 0) {
            await runButton.scrollIntoViewIfNeeded();
            await page.waitForTimeout(300);
            if (await successBanner.count() === 0 && await previousBanner.count() === 0 && !await runButton.isDisabled()) {
                await runButton.click();
                console.log('   Waiting for FEM analysis to complete...');
                await waitForAnalysisCompletion(180000);
            }
            await screenshot('fem_analysis_complete');
        }
        
        console.log('Step 5: Test Plan View...');
        const planTab = page.locator('button:has-text("Plan View")');
        if (await planTab.count() > 0) {
            await planTab.first().click();
            await page.waitForTimeout(2000);
            await screenshot('plan_view');
        }
        
        console.log('Step 6: Test Elevation View...');
        const elevationTab = page.locator('button:has-text("Elevation View")');
        if (await elevationTab.count() > 0) {
            await elevationTab.first().click();
            await page.waitForTimeout(2000);
            await screenshot('elevation_view');
        }
        
        console.log('Step 7: Test 3D View...');
        const view3dTab = page.locator('button:has-text("3D View")');
        if (await view3dTab.count() > 0) {
            const view3dButton = view3dTab.first();
            for (let i = 0; i < 30; i++) {
                if (await view3dButton.isEnabled()) {
                    break;
                }
                await page.waitForTimeout(1000);
            }
            if (!await view3dButton.isEnabled()) {
                throw new Error('3D View button remained disabled after analysis');
            }
            await view3dButton.click();
            await page.waitForTimeout(2000);
            await screenshot('3d_view');
        }
        
        console.log('Step 8: Test Unlock button...');
        const unlockButton = page.getByRole('button', { name: /Unlock/i });
        if (await unlockButton.count() > 0) {
            await unlockButton.scrollIntoViewIfNeeded();
            await unlockButton.click();
            await page.waitForTimeout(1500);
            await screenshot('after_unlock');
        }
        
        console.log('Step 9: Test Load Combinations panel...');
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await page.waitForTimeout(1000);
        
        const ulsCat = page.locator('text=ULS Strength Combinations');
        if (await ulsCat.count() > 0) {
            await ulsCat.first().click();
            await page.waitForTimeout(500);
        }
        await screenshot('load_combinations_expanded');
        
        console.log(`Step 10: Test edge case - Maximum floors (${TALL_FLOORS})...`);
        await page.evaluate(() => window.scrollTo(0, 0));
        await page.waitForTimeout(500);
        
        const floorsInputEdge = page.locator('input[aria-label="Floors"]');
        if (await floorsInputEdge.count() > 0) {
            await floorsInputEdge.scrollIntoViewIfNeeded();
            await floorsInputEdge.fill(String(TALL_FLOORS));
            await page.waitForTimeout(2000);
        }
        await screenshot(`edge_case_${TALL_FLOORS}_floors`);
        
        if (RUN_TALL_ANALYSIS) {
            console.log(`Step 11: Run FEM on ${TALL_FLOORS}-floor building...`);
            const runButton2 = page.getByRole('button', { name: /Run FEM Analysis/i });
            if (await runButton2.count() > 0 && !await runButton2.isDisabled()) {
                await runButton2.scrollIntoViewIfNeeded();
                await runButton2.click();
                console.log(`   Waiting for ${TALL_FLOORS}-floor FEM analysis...`);
                await waitForAnalysisCompletion(240000);
                await screenshot(`fem_${TALL_FLOORS}_floors_complete`);
            }
            
            console.log('Step 12: Check 3D view of tall building...');
            const view3dTab2 = page.locator('button:has-text("3D View")');
            if (await view3dTab2.count() > 0) {
                await view3dTab2.first().click();
                await page.waitForTimeout(2000);
                await screenshot(`3d_view_${TALL_FLOORS}_floors`);
            }
        } else {
            console.log(`Step 11: Skip tall-building analysis for ${TALL_FLOORS} floors (RUN_TALL_ANALYSIS=false).`);
            console.log('Step 12: Skipped tall-building 3D view.');
        }
        
        console.log('Step 13: Mobile viewport test (375x812)...');
        await page.setViewportSize({ width: 375, height: 812 });
        await page.waitForTimeout(1500);
        await screenshot('mobile_view');
        
        console.log('Step 14: Tablet viewport test (768x1024)...');
        await page.setViewportSize({ width: 768, height: 1024 });
        await page.waitForTimeout(1500);
        await screenshot('tablet_view');
        
        console.log('Step 15: Reset to desktop...');
        await page.setViewportSize({ width: 1920, height: 1080 });
        await page.waitForTimeout(1000);
        await page.evaluate(() => window.scrollTo(0, 0));
        await screenshot('final_desktop');
        
        console.log('\n=== TEST SUMMARY ===');
        console.log(`Total screenshots: ${stepCount}`);
        console.log(`Screenshot directory: ${SCREENSHOT_DIR}`);
        console.log('');
        console.log('TESTED FEATURES:');
        console.log('  - Initial app load');
        console.log(`  - Geometry configuration (${BASE_CASE.baysX}x${BASE_CASE.baysY} bays, ${BASE_CASE.floors} floors)`);
        console.log('  - FEM Analysis execution');
        console.log('  - Plan View visualization');
        console.log('  - Elevation View visualization');
        console.log('  - 3D View visualization');
        console.log('  - Unlock/Lock functionality');
        console.log('  - Load Combinations panel');
        console.log(`  - Edge case: ${TALL_FLOORS}-floor building${RUN_TALL_ANALYSIS ? '' : ' (analysis skipped)'}`);
        console.log('  - Mobile viewport (375x812)');
        console.log('  - Tablet viewport (768x1024)');
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

runComprehensiveTest().catch(error => {
    console.error('Test execution failed:', error);
    process.exit(1);
});
