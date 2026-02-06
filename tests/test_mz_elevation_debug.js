const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const URL = 'http://localhost:8501';
const SCREENSHOTS = path.join(__dirname, 'test_screenshots', 'mz_elevation_debug');

async function run() {
    fs.mkdirSync(SCREENSHOTS, { recursive: true });
    
    const browser = await chromium.launch({ headless: false });
    const page = await (await browser.newContext({ 
        viewport: { width: 1920, height: 1080 } 
    })).newPage();
    
    page.on('console', msg => {
        if (msg.type() !== 'debug') {
            console.log(`[BROWSER] ${msg.type()}: ${msg.text()}`);
        }
    });
    
    try {
        console.log('1. Navigating to Streamlit app...');
        await page.goto(URL, { waitUntil: 'networkidle', timeout: 60000 });
        await page.waitForTimeout(3000);
        
        console.log('2. Running FEM Analysis...');
        const runBtn = page.getByRole('button', { name: /Run FEM Analysis/i });
        await runBtn.scrollIntoViewIfNeeded();
        await runBtn.click({ force: true });
        await page.waitForTimeout(8000);
        
        console.log('3. Switching to Elevation View FIRST...');
        const elevTab = page.locator('button:has-text("Elevation View")');
        if (await elevTab.count() > 0) {
            await elevTab.click();
            await page.waitForTimeout(2000);
        }
        await page.screenshot({ path: path.join(SCREENSHOTS, '01_elevation_no_forces.png') });
        
        console.log('4. Opening Display Options...');
        const displayOptions = page.locator('text=Display Options');
        if (await displayOptions.count() > 0) {
            await displayOptions.click();
            await page.waitForTimeout(500);
        }
        
        console.log('5. Selecting Mz force type...');
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
        await page.waitForTimeout(3000);
        
        console.log('6. Taking Mz Elevation View screenshot...');
        await page.screenshot({ path: path.join(SCREENSHOTS, '02_elevation_with_mz.png'), fullPage: true });
        
        console.log('7. Looking for DEBUG caption...');
        const debugCaption = await page.locator('text=/force_code=Mz/').first().textContent().catch(() => 'not found');
        console.log(`   Debug caption: ${debugCaption}`);
        
        console.log('8. Taking focused screenshot of the plot area...');
        const plotArea = page.locator('.plotly').first();
        if (await plotArea.count() > 0) {
            await plotArea.screenshot({ path: path.join(SCREENSHOTS, '03_plot_area.png') });
        }
        
        console.log('\n✅ Test completed! Check screenshots in:', SCREENSHOTS);
        
    } catch (err) {
        console.error('Error:', err.message);
        await page.screenshot({ path: path.join(SCREENSHOTS, 'error.png') });
    } finally {
        await browser.close();
    }
}

run().catch(console.error);
