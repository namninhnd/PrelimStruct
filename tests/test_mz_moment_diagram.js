const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const URL = 'http://localhost:8501';
const SCREENSHOTS = path.join(__dirname, 'test_screenshots', 'mz_moment_fix');

async function run() {
    fs.mkdirSync(SCREENSHOTS, { recursive: true });
    
    const browser = await chromium.launch({ headless: false });
    const page = await (await browser.newContext({ 
        viewport: { width: 1920, height: 1080 } 
    })).newPage();
    
    try {
        console.log('1. Navigating to Streamlit app...');
        await page.goto(URL, { waitUntil: 'networkidle', timeout: 60000 });
        await page.waitForTimeout(3000);
        
        console.log('2. Taking initial screenshot...');
        await page.screenshot({ path: path.join(SCREENSHOTS, '01_initial.png') });
        
        console.log('3. Running FEM Analysis...');
        const runBtn = page.getByRole('button', { name: /Run FEM Analysis/i });
        await runBtn.scrollIntoViewIfNeeded();
        await runBtn.click({ force: true });
        await page.waitForTimeout(8000);
        
        console.log('4. Taking post-analysis screenshot...');
        await page.screenshot({ path: path.join(SCREENSHOTS, '02_after_analysis.png') });
        
        console.log('5. Looking for Display Options expander...');
        const displayOptions = page.locator('text=Display Options');
        if (await displayOptions.count() > 0) {
            await displayOptions.click();
            await page.waitForTimeout(500);
        }
        
        console.log('6. Selecting Mz force type...');
        const mzLabel = page.locator('label:has-text("Mz (Moment Z)")');
        if (await mzLabel.count() > 0) {
            await mzLabel.click({ force: true });
            console.log('   Clicked Mz label');
        } else {
            const mzRadio = page.locator('text=Mz');
            if (await mzRadio.count() > 0) {
                await mzRadio.first().click({ force: true });
                console.log('   Clicked Mz text');
            }
        }
        await page.waitForTimeout(2000);
        
        console.log('7. Taking Mz screenshot (Plan View)...');
        await page.screenshot({ path: path.join(SCREENSHOTS, '03_mz_plan_view.png') });
        
        console.log('8. Switching to Elevation View...');
        const elevTab = page.locator('button:has-text("Elevation View")');
        if (await elevTab.count() > 0) {
            await elevTab.click();
            await page.waitForTimeout(2000);
        }
        
        console.log('9. Taking Mz Elevation View screenshot...');
        await page.screenshot({ path: path.join(SCREENSHOTS, '04_mz_elevation_view.png'), fullPage: true });
        
        console.log('10. Looking for force diagram traces (red lines)...');
        const plotArea = page.locator('.plotly');
        if (await plotArea.count() > 0) {
            console.log('   Found Plotly chart');
        }
        
        console.log('\n✅ Test completed! Check screenshots in:', SCREENSHOTS);
        console.log('\nTo verify the fix:');
        console.log('1. Open 04_mz_elevation_view.png');
        console.log('2. Look for RED curves/lines on beams');
        console.log('3. For UDL gravity loads, the curve should be PARABOLIC (curved), not straight');
        
    } catch (err) {
        console.error('Error:', err.message);
        await page.screenshot({ path: path.join(SCREENSHOTS, 'error.png') });
    } finally {
        await browser.close();
    }
}

run().catch(console.error);
