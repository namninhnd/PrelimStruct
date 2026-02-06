const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const URL = 'http://localhost:8501';
const SCREENSHOTS = path.join(__dirname, 'test_screenshots', 'my_moment_test');

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
        
        console.log('2. Running FEM Analysis...');
        const runBtn = page.getByRole('button', { name: /Run FEM Analysis/i });
        await runBtn.scrollIntoViewIfNeeded();
        await runBtn.click({ force: true });
        await page.waitForTimeout(8000);
        
        console.log('3. Switching to Elevation View...');
        const elevTab = page.locator('button:has-text("Elevation View")');
        if (await elevTab.count() > 0) {
            await elevTab.click();
            await page.waitForTimeout(2000);
        }
        
        console.log('4. Opening Display Options...');
        const displayOptions = page.locator('text=Display Options');
        if (await displayOptions.count() > 0) {
            await displayOptions.click();
            await page.waitForTimeout(500);
        }
        
        console.log('5. Selecting My force type (bending moment for gravity)...');
        const myLabel = page.locator('label:has-text("My (Moment Y)")');
        if (await myLabel.count() > 0) {
            await myLabel.click({ force: true });
            console.log('   Clicked My label');
        }
        await page.waitForTimeout(3000);
        
        console.log('6. Taking My Elevation View screenshot...');
        await page.screenshot({ path: path.join(SCREENSHOTS, '01_my_elevation.png'), fullPage: true });
        
        const debugCaption = await page.locator('text=/force_code=/').first().textContent().catch(() => 'not found');
        console.log(`   Debug caption: ${debugCaption}`);
        
        console.log('7. Selecting Vy force type (shear for gravity)...');
        const vyLabel = page.locator('label:has-text("Vy (Shear Y)")');
        if (await vyLabel.count() > 0) {
            await vyLabel.click({ force: true });
            console.log('   Clicked Vy label');
        }
        await page.waitForTimeout(3000);
        
        console.log('8. Taking Vy Elevation View screenshot...');
        await page.screenshot({ path: path.join(SCREENSHOTS, '02_vy_elevation.png'), fullPage: true });
        
        console.log('\n✅ Test completed! Check screenshots in:', SCREENSHOTS);
        console.log('\nFor horizontal beams with gravity loads:');
        console.log('- My (moment about Y) should show parabolic curves with non-zero values');
        console.log('- Mz (moment about Z) will be zero for in-plane bending');
        
    } catch (err) {
        console.error('Error:', err.message);
        await page.screenshot({ path: path.join(SCREENSHOTS, 'error.png') });
    } finally {
        await browser.close();
    }
}

run().catch(console.error);
