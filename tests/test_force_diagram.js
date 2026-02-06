const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const URL = 'http://localhost:8501';
const SCREENSHOTS = path.join(__dirname, 'test_screenshots', 'force_diagram');

async function run() {
    fs.mkdirSync(SCREENSHOTS, { recursive: true });
    
    const browser = await chromium.launch({ headless: false });
    const page = await (await browser.newContext({ 
        viewport: { width: 1920, height: 1080 } 
    })).newPage();
    
    try {
        console.log('1. Loading page...');
        await page.goto(URL, { waitUntil: 'networkidle', timeout: 60000 });
        await page.waitForTimeout(3000);
        await page.screenshot({ path: path.join(SCREENSHOTS, '01_initial.png') });
        
        console.log('2. Looking for FEM Analysis button...');
        const femButton = page.getByRole('button', { name: /Run FEM Analysis/i });
        await femButton.scrollIntoViewIfNeeded();
        await femButton.click();
        console.log('   Clicked Run FEM Analysis');
        await page.waitForTimeout(10000);
        await page.screenshot({ path: path.join(SCREENSHOTS, '02_after_analysis.png') });
        
        console.log('3. Expanding Display Options...');
        const displayExpander = page.locator('text=Display Options');
        if (await displayExpander.count() > 0) {
            await displayExpander.click();
            await page.waitForTimeout(500);
        }
        
        console.log('4. Scrolling to Section Forces...');
        const sectionForces = page.locator('text=Section Forces');
        if (await sectionForces.count() > 0) {
            await sectionForces.scrollIntoViewIfNeeded();
            await page.waitForTimeout(500);
        }
        await page.screenshot({ path: path.join(SCREENSHOTS, '03_section_forces.png') });
        
        console.log('5. Selecting My (Moment Y) - the major bending moment...');
        // Try clicking on "My (Moment Y)" label - this is the gravity bending moment
        const myLabel = page.locator('label:has-text("My (Moment Y)")');
        if (await myLabel.count() > 0) {
            await myLabel.click({ force: true });
            console.log('   Selected My (Moment Y)');
        } else {
            // Fallback - try M-major if labels updated
            const mMajor = page.locator('label:has-text("M-major")');
            if (await mMajor.count() > 0) {
                await mMajor.click({ force: true });
                console.log('   Selected M-major');
            }
        }
        
        console.log('6. Waiting for force diagram to render...');
        await page.waitForTimeout(5000);
        await page.screenshot({ path: path.join(SCREENSHOTS, '04_after_my_selected.png') });
        
        console.log('7. Checking what rendered...');
        const mplFig = await page.locator('img[src*="data:image"]').count();
        const plotlyChart = await page.locator('.js-plotly-plot').count();
        const stImage = await page.locator('[data-testid="stImage"]').count();
        const warning = await page.locator('text=opsvis force diagram failed').count();
        
        console.log(`   Results:`);
        console.log(`   - st.pyplot/image: ${stImage}`);
        console.log(`   - Matplotlib base64: ${mplFig}`);
        console.log(`   - Plotly charts: ${plotlyChart}`);
        console.log(`   - opsvis warning: ${warning}`);
        
        if (warning > 0) {
            console.log('\n   ⚠️ WARNING: opsvis failed, using Plotly fallback');
        } else if (stImage > 0 || mplFig > 0) {
            console.log('\n   ✓ SUCCESS: Matplotlib/opsvis figure rendered');
        } else if (plotlyChart > 0) {
            console.log('\n   ℹ️ INFO: Plotly chart rendered (opsvis may have failed silently)');
        }
        
        await page.screenshot({ path: path.join(SCREENSHOTS, '05_final.png'), fullPage: true });
        
        console.log('\n=== TEST COMPLETE ===');
        console.log(`Screenshots saved to: ${SCREENSHOTS}`);
        
    } catch (error) {
        console.error('Test failed:', error.message);
        await page.screenshot({ path: path.join(SCREENSHOTS, 'error.png') });
    } finally {
        await browser.close();
    }
}

run().catch(console.error);
