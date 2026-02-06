const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const URL = 'http://localhost:8501';
const SCREENSHOTS = path.join(__dirname, '.sisyphus', 'evidence');

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
        await page.screenshot({ path: path.join(SCREENSHOTS, '01-initial-load.png') });
        
        console.log('2. Running FEM Analysis...');
        const runBtn = page.getByRole('button', { name: /Run FEM Analysis/i });
        if (await runBtn.count() > 0) {
            await runBtn.click();
            console.log('   Waiting for analysis to complete...');
            await page.waitForTimeout(10000);
            await page.screenshot({ path: path.join(SCREENSHOTS, '02-after-analysis.png') });
        } else {
            console.log('   Run button not found, analysis may already be complete');
        }
        
        console.log('3. Looking for Display Options expander...');
        const displayOptionsExpander = page.locator('div[data-testid="stExpander"]:has-text("Display Options")');
        if (await displayOptionsExpander.count() > 0) {
            const expanderHeader = displayOptionsExpander.locator('summary, [data-testid="stExpanderHeader"], div:has-text("Display Options")').first();
            await expanderHeader.click();
            await page.waitForTimeout(1000);
            await page.screenshot({ path: path.join(SCREENSHOTS, '03-display-options-expanded.png') });
            console.log('   Display Options expanded');
        } else {
            console.log('   Display Options expander not found, trying alternative...');
            const altExpander = page.locator('text=Display Options').first();
            if (await altExpander.count() > 0) {
                await altExpander.click();
                await page.waitForTimeout(1000);
            }
        }
        
        console.log('4. Looking for Mz (Moment Z) radio button...');
        const mzRadio = page.locator('label:has-text("Mz (Moment Z)")');
        if (await mzRadio.count() > 0) {
            await mzRadio.scrollIntoViewIfNeeded();
            await mzRadio.click();
            await page.waitForTimeout(2000);
            await page.screenshot({ path: path.join(SCREENSHOTS, '04-mz-selected.png') });
            console.log('   Mz (Moment Z) selected');
        } else {
            console.log('   Mz radio button not found, trying alternative selectors...');
            const allLabels = await page.locator('label').allTextContents();
            console.log('   Available labels:', allLabels.filter(l => l.includes('M') || l.includes('V') || l.includes('N')));
        }
        
        console.log('5. Switching to Elevation View for better force diagram visibility...');
        const elevationBtn = page.getByRole('button', { name: /Elevation View/i });
        if (await elevationBtn.count() > 0) {
            await elevationBtn.click();
            await page.waitForTimeout(3000);
            await page.screenshot({ path: path.join(SCREENSHOTS, '05-elevation-view.png') });
            console.log('   Elevation View active');
        }
        
        console.log('6. Checking for Load Case dropdown...');
        const loadCaseLabel = page.locator('label:has-text("Load Case")');
        if (await loadCaseLabel.count() > 0) {
            console.log('   Load Case dropdown FOUND');
            await page.screenshot({ path: path.join(SCREENSHOTS, '06-load-case-found.png') });
        } else {
            console.log('   Load Case dropdown NOT found - checking if has_results is false');
        }
        
        console.log('7. Taking final screenshot of force diagram...');
        await page.screenshot({ path: path.join(SCREENSHOTS, '07-final-force-diagram.png'), fullPage: true });
        
        console.log('\n=== Visual Verification Complete ===');
        console.log('Screenshots saved to:', SCREENSHOTS);
        console.log('\nCheck the following:');
        console.log('- 04-mz-selected.png: Should show Mz radio selected');
        console.log('- 05-elevation-view.png: Should show force diagrams on beams/columns');
        console.log('- 06-load-case-found.png: Should show Load Case dropdown');
        
    } catch (error) {
        console.error('Error:', error.message);
        await page.screenshot({ path: path.join(SCREENSHOTS, 'error-state.png') });
    } finally {
        await browser.close();
    }
}

run().catch(console.error);
