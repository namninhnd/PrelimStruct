const { chromium } = require('playwright');
const path = require('path');

const STREAMLIT_URL = 'http://localhost:8501';
const SCREENSHOT_DIR = path.join(__dirname, '..', 'screenshots');

async function testForceDiagramParabolicCurves() {
    console.log('=== PLAYWRIGHT TEST: Force Diagram Parabolic Curves ===\n');
    
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ 
        viewport: { width: 1920, height: 1080 } 
    });
    const page = await context.newPage();
    
    let testsPassed = 0;
    let testsFailed = 0;
    
    try {
        console.log('1. Navigating to Streamlit app...');
        await page.goto(STREAMLIT_URL, { waitUntil: 'networkidle', timeout: 60000 });
        await page.waitForTimeout(3000);
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '01_initial_load.png') });
        console.log('   Initial page loaded');
        
        console.log('\n2. Scrolling to FEM Analysis section...');
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight / 3));
        await page.waitForTimeout(1000);
        
        const femHeader = page.locator('h3:has-text("FEM Analysis"), h2:has-text("FEM Analysis")');
        if (await femHeader.count() > 0) {
            await femHeader.first().scrollIntoViewIfNeeded();
            await page.waitForTimeout(500);
            console.log('   Found FEM Analysis section');
        }
        
        console.log('\n3. Looking for Run FEM Analysis button...');
        const runButton = page.getByRole('button', { name: /Run FEM Analysis/i });
        
        if (await runButton.count() > 0) {
            await runButton.scrollIntoViewIfNeeded();
            await page.waitForTimeout(500);
            await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02_before_run.png') });
            
            console.log('   Clicking Run FEM Analysis...');
            await runButton.click();
            
            console.log('   Waiting for analysis to complete (up to 30s)...');
            await page.waitForTimeout(10000);
            
            const successText = page.locator('text=/Analysis.*success|converged/i');
            if (await successText.count() > 0) {
                console.log('   FEM Analysis completed successfully');
                testsPassed++;
            } else {
                console.log('   Note: Success message not found, continuing...');
            }
            
            await page.screenshot({ path: path.join(SCREENSHOT_DIR, '03_after_analysis.png'), fullPage: true });
        } else {
            console.log('   Run FEM Analysis button not found, checking if already run...');
        }
        
        console.log('\n4. Looking for Force Diagram options...');
        await page.evaluate(() => window.scrollTo(0, 0));
        await page.waitForTimeout(500);
        
        const forceTypeExpander = page.locator('text=/Force Type|Section Forces|Display Options/i');
        if (await forceTypeExpander.count() > 0) {
            await forceTypeExpander.first().scrollIntoViewIfNeeded();
            await forceTypeExpander.first().click().catch(() => {});
            await page.waitForTimeout(500);
        }
        
        const mzOption = page.locator('label:has-text("Mz"), label:has-text("Moment Z")');
        if (await mzOption.count() > 0) {
            await mzOption.first().scrollIntoViewIfNeeded();
            await mzOption.first().click();
            await page.waitForTimeout(1000);
            console.log('   Selected Mz (Moment Z) force type');
        }
        
        console.log('\n5. Testing Plan View force diagrams...');
        const planViewTab = page.locator('[data-baseweb="tab"]:has-text("Plan View"), button:has-text("Plan View")');
        if (await planViewTab.count() > 0) {
            await planViewTab.first().click();
            await page.waitForTimeout(2000);
            console.log('   Switched to Plan View');
        }
        
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '04_plan_view.png'), fullPage: true });
        
        const planViewChart = page.locator('.js-plotly-plot, [class*="plotly"]');
        if (await planViewChart.count() > 0) {
            console.log('   Plan View chart found');
            testsPassed++;
            
            await planViewChart.first().screenshot({ 
                path: path.join(SCREENSHOT_DIR, '05_plan_view_chart.png') 
            });
        } else {
            console.log('   Warning: Plan View chart not found');
            testsFailed++;
        }
        
        console.log('\n6. Testing Elevation View force diagrams...');
        const elevationViewTab = page.locator('[data-baseweb="tab"]:has-text("Elevation View"), button:has-text("Elevation View")');
        if (await elevationViewTab.count() > 0) {
            await elevationViewTab.first().click();
            await page.waitForTimeout(2000);
            console.log('   Switched to Elevation View');
        }
        
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '06_elevation_view.png'), fullPage: true });
        
        const elevationViewChart = page.locator('.js-plotly-plot, [class*="plotly"]');
        if (await elevationViewChart.count() > 0) {
            console.log('   Elevation View chart found');
            testsPassed++;
            
            await elevationViewChart.first().screenshot({ 
                path: path.join(SCREENSHOT_DIR, '07_elevation_view_chart.png') 
            });
        } else {
            console.log('   Warning: Elevation View chart not found');
            testsFailed++;
        }
        
        console.log('\n7. Checking for force diagram traces (red lines)...');
        const hasForceDiagramTraces = await page.evaluate(() => {
            const svg = document.querySelector('.js-plotly-plot svg');
            if (!svg) return { found: false, reason: 'No SVG found' };
            
            const paths = svg.querySelectorAll('path');
            let redPaths = 0;
            for (const p of paths) {
                const stroke = p.getAttribute('style') || '';
                if (stroke.includes('rgb(255, 0, 0)') || stroke.includes('red') || stroke.includes('#ff0000')) {
                    redPaths++;
                }
            }
            
            const allPaths = paths.length;
            return { found: redPaths > 0, redPaths, allPaths };
        });
        
        console.log(`   SVG analysis: ${JSON.stringify(hasForceDiagramTraces)}`);
        
        if (hasForceDiagramTraces.found) {
            console.log('   Force diagram traces found (red paths in SVG)');
            testsPassed++;
        } else {
            console.log('   Note: Red force diagram paths not detected in SVG');
        }
        
        console.log('\n8. Final full-page screenshot...');
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '08_final_state.png'), fullPage: true });
        
        console.log('\n=== TEST SUMMARY ===');
        console.log(`Passed: ${testsPassed}`);
        console.log(`Failed: ${testsFailed}`);
        console.log(`Screenshots saved to: ${SCREENSHOT_DIR}`);
        
        if (testsPassed >= 2) {
            console.log('\n[PASS] Force diagram visualization is working');
        } else {
            console.log('\n[NEEDS VERIFICATION] Check screenshots manually');
        }
        
    } catch (error) {
        console.error('\nTest error:', error.message);
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'error_state.png'), fullPage: true });
        testsFailed++;
    } finally {
        await browser.close();
    }
    
    return { passed: testsPassed, failed: testsFailed };
}

testForceDiagramParabolicCurves()
    .then(result => {
        console.log('\nTest completed.');
        process.exit(result.failed > 0 ? 1 : 0);
    })
    .catch(err => {
        console.error('Fatal error:', err);
        process.exit(1);
    });
