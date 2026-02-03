const { chromium } = require('playwright');
const path = require('path');

const STREAMLIT_URL = 'http://localhost:8501';
const SCREENSHOT_DIR = path.join(__dirname, '..', 'screenshots');

async function runFEMAudit() {
    console.log('Starting Playwright FEM Audit...');
    
    const browser = await chromium.launch({ headless: false });
    const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
    const page = await context.newPage();
    
    try {
        console.log('1. Navigating to Streamlit app...');
        await page.goto(STREAMLIT_URL, { waitUntil: 'networkidle', timeout: 60000 });
        await page.waitForTimeout(3000);
        
        console.log('2. Taking initial screenshot...');
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '01_initial_load.png'), fullPage: true });
        
        console.log('3. Setting up multi-bay building (3x3 bays)...');
        const baysXInput = page.locator('input[aria-label="Bays in X"]');
        if (await baysXInput.count() > 0) {
            await baysXInput.fill('3');
        }
        
        const baysYInput = page.locator('input[aria-label="Bays in Y"]');
        if (await baysYInput.count() > 0) {
            await baysYInput.fill('3');
        }
        await page.waitForTimeout(2000);
        
        console.log('4. Scrolling to FEM section...');
        await page.evaluate(() => {
            const femSection = Array.from(document.querySelectorAll('h3')).find(el => el.textContent.includes('FEM'));
            if (femSection) femSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
        });
        await page.waitForTimeout(1000);
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02_multi_bay_setup.png'), fullPage: false });
        
        console.log('5. Looking for Run FEM Analysis button...');
        const runButton = page.getByRole('button', { name: /Run FEM Analysis/i });
        if (await runButton.count() > 0) {
            console.log('   Found Run FEM Analysis button, clicking...');
            await runButton.click();
            await page.waitForTimeout(5000);
            await page.screenshot({ path: path.join(SCREENSHOT_DIR, '03_after_analysis.png'), fullPage: false });
        } else {
            console.log('   Run FEM Analysis button not found');
        }
        
        console.log('6. Checking for Lock indicator...');
        const lockIndicator = await page.locator('text=🔒').count();
        console.log(`   Lock indicator visible: ${lockIndicator > 0}`);
        
        console.log('7. Scrolling down to Display Options...');
        await page.evaluate(() => window.scrollBy(0, 400));
        await page.waitForTimeout(500);
        
        console.log('8. Looking for Display Options expander...');
        const displayOptions = page.getByText('Display Options');
        if (await displayOptions.count() > 0) {
            // Scroll expander into view first
            await displayOptions.scrollIntoViewIfNeeded();
            await page.waitForTimeout(500);
            await displayOptions.click();
            await page.waitForTimeout(1000);
            
            console.log('9. Looking for Section Forces label and Mz radio...');
            // Scroll down more to reveal the radio buttons
            await page.evaluate(() => window.scrollBy(0, 300));
            await page.waitForTimeout(500);
            
            // Try clicking by label text which is more reliable for Streamlit radios
            const mzLabel = page.locator('label:has-text("Mz (Moment Z)")');
            if (await mzLabel.count() > 0) {
                console.log('   Found Mz label, scrolling into view and clicking...');
                await mzLabel.scrollIntoViewIfNeeded();
                await page.waitForTimeout(300);
                await mzLabel.click();
                await page.waitForTimeout(2000);
                await page.screenshot({ path: path.join(SCREENSHOT_DIR, '04_mz_force_selected.png'), fullPage: false });
            } else {
                // Fallback: try the radio input directly with force click
                const mzRadio = page.getByRole('radio', { name: /Mz/i });
                if (await mzRadio.count() > 0) {
                    console.log('   Found Mz radio, force clicking...');
                    await mzRadio.click({ force: true });
                    await page.waitForTimeout(2000);
                    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '04_mz_force_selected.png'), fullPage: false });
                } else {
                    console.log('   Mz radio not found, taking screenshot of current state...');
                    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '04_display_options_state.png'), fullPage: false });
                }
            }
        }
        
        console.log('10. Testing Unlock button...');
        const unlockButton = page.getByRole('button', { name: /Unlock to Modify/i });
        if (await unlockButton.count() > 0) {
            console.log('   Found Unlock button, clicking...');
            await unlockButton.click();
            await page.waitForTimeout(2000);
            await page.screenshot({ path: path.join(SCREENSHOT_DIR, '05_after_unlock.png'), fullPage: false });
        } else {
            console.log('   Unlock button not found (might not be locked)');
        }
        
        console.log('11. Changing secondary beams to test state invalidation...');
        const secBeamsInput = page.locator('input[aria-label="Number of Secondary Beams"]');
        if (await secBeamsInput.count() > 0) {
            await secBeamsInput.fill('5');
            await page.waitForTimeout(2000);
            await page.screenshot({ path: path.join(SCREENSHOT_DIR, '06_after_beam_change.png'), fullPage: false });
            
            const analysisCleared = await page.locator('text=Analysis Successful').count() === 0;
            console.log(`   Analysis state cleared after change: ${analysisCleared}`);
        }
        
        console.log('12. Final full page screenshot...');
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '07_final_state.png'), fullPage: true });
        
        console.log('\n=== AUDIT COMPLETE ===');
        console.log(`Screenshots saved to: ${SCREENSHOT_DIR}`);
        
    } catch (error) {
        console.error('Error during audit:', error.message);
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'error_state.png'), fullPage: true });
    } finally {
        await browser.close();
    }
}

runFEMAudit().catch(console.error);
