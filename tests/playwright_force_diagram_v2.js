const { chromium } = require('playwright');
const path = require('path');

const STREAMLIT_URL = 'http://localhost:8501';
const SCREENSHOT_DIR = path.join(__dirname, '..', 'screenshots');

async function testForceDiagramWithDisplay() {
    console.log('=== PLAYWRIGHT TEST: Force Diagram Display Verification ===\n');
    
    const browser = await chromium.launch({ headless: false, slowMo: 100 });
    const context = await browser.newContext({ 
        viewport: { width: 1920, height: 1080 } 
    });
    const page = await context.newPage();
    
    try {
        console.log('1. Navigating to Streamlit app...');
        await page.goto(STREAMLIT_URL, { waitUntil: 'networkidle', timeout: 60000 });
        await page.waitForTimeout(3000);
        
        console.log('\n2. Running FEM Analysis...');
        const runButton = page.getByRole('button', { name: /Run FEM Analysis/i });
        if (await runButton.count() > 0) {
            await runButton.scrollIntoViewIfNeeded();
            await runButton.click();
            await page.waitForTimeout(8000);
            console.log('   FEM Analysis completed');
        }
        
        console.log('\n3. Looking for Display Options expander...');
        await page.evaluate(() => window.scrollTo(0, 0));
        await page.waitForTimeout(500);
        
        const mainContent = page.locator('[data-testid="stMainBlockContainer"], .main, main');
        await mainContent.first().evaluate(el => el.scrollTop = 0);
        
        const displayOptionsExpander = page.locator('details summary:has-text("Display Options"), [data-testid="stExpander"]:has-text("Display Options")');
        if (await displayOptionsExpander.count() > 0) {
            await displayOptionsExpander.first().scrollIntoViewIfNeeded();
            await displayOptionsExpander.first().click();
            await page.waitForTimeout(500);
            console.log('   Opened Display Options');
        }
        
        console.log('\n4. Looking for Section Forces dropdown...');
        const sectionForcesLabel = page.locator('text=/Section Forces|Force Type|Display section forces/i');
        if (await sectionForcesLabel.count() > 0) {
            await sectionForcesLabel.first().scrollIntoViewIfNeeded();
            console.log('   Found Section Forces control');
        }
        
        const forceSelectbox = page.locator('[aria-label*="Section Forces"], [aria-label*="Force Type"], select:near(:text("Section Forces"))');
        if (await forceSelectbox.count() > 0) {
            await forceSelectbox.first().click();
            await page.waitForTimeout(500);
            
            const mzOption = page.locator('li:has-text("Mz"), [role="option"]:has-text("Mz"), option:has-text("Mz")');
            if (await mzOption.count() > 0) {
                await mzOption.first().click();
                await page.waitForTimeout(1000);
                console.log('   Selected Mz force type');
            }
        }
        
        const radioMz = page.locator('label:has-text("Mz"), input[type="radio"][value*="Mz"]');
        if (await radioMz.count() > 0) {
            await radioMz.first().click({ force: true });
            await page.waitForTimeout(1000);
            console.log('   Clicked Mz radio option');
        }
        
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'force_01_options.png'), fullPage: true });
        
        console.log('\n5. Checking Plan View tab...');
        const planViewTab = page.locator('[data-baseweb="tab"]:has-text("Plan View"), button:has-text("Plan View"), [role="tab"]:has-text("Plan View")');
        if (await planViewTab.count() > 0) {
            await planViewTab.first().click();
            await page.waitForTimeout(2000);
            console.log('   Switched to Plan View');
        }
        
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'force_02_plan_view.png'), fullPage: true });
        
        const planChart = page.locator('.js-plotly-plot').first();
        if (await planChart.count() > 0) {
            await planChart.screenshot({ path: path.join(SCREENSHOT_DIR, 'force_03_plan_chart.png') });
        }
        
        console.log('\n6. Checking Elevation View tab...');
        const elevationViewTab = page.locator('[data-baseweb="tab"]:has-text("Elevation View"), button:has-text("Elevation View"), [role="tab"]:has-text("Elevation View")');
        if (await elevationViewTab.count() > 0) {
            await elevationViewTab.first().click();
            await page.waitForTimeout(2000);
            console.log('   Switched to Elevation View');
        }
        
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'force_04_elevation_view.png'), fullPage: true });
        
        const elevationChart = page.locator('.js-plotly-plot').first();
        if (await elevationChart.count() > 0) {
            await elevationChart.screenshot({ path: path.join(SCREENSHOT_DIR, 'force_05_elevation_chart.png') });
        }
        
        console.log('\n7. Final state...');
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'force_06_final.png'), fullPage: true });
        
        console.log('\n=== Screenshots saved to:', SCREENSHOT_DIR, '===');
        console.log('Inspect force_02_plan_view.png and force_04_elevation_view.png');
        console.log('Force diagrams should appear as red curved lines on beam elements');
        
        await page.waitForTimeout(5000);
        
    } catch (error) {
        console.error('\nTest error:', error.message);
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'force_error.png'), fullPage: true });
    } finally {
        await browser.close();
    }
}

testForceDiagramWithDisplay().catch(console.error);
