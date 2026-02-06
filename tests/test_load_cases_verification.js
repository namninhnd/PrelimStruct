const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const URL = 'http://localhost:8501';
const SCREENSHOTS = path.join(__dirname, 'test_screenshots', 'load_cases_fix');

async function run() {
    fs.mkdirSync(SCREENSHOTS, { recursive: true });
    
    const browser = await chromium.launch({ headless: false });
    const page = await (await browser.newContext({ 
        viewport: { width: 1920, height: 1080 } 
    })).newPage();
    
    try {
        console.log('1. Navigating to app...');
        await page.goto(URL, { waitUntil: 'networkidle', timeout: 60000 });
        await page.waitForTimeout(3000);
        
        console.log('2. Taking initial screenshot...');
        await page.screenshot({ path: path.join(SCREENSHOTS, '01_initial.png') });
        
        console.log('3. Looking for Unlock button (to clear cached results)...');
        const unlockButton = page.getByRole('button', { name: /Unlock/i });
        if (await unlockButton.count() > 0) {
            console.log('   Found Unlock button, clicking to reset...');
            await unlockButton.click();
            await page.waitForTimeout(2000);
        }
        
        console.log('4. Clicking Run FEM Analysis button...');
        const runButton = page.getByRole('button', { name: /Run FEM Analysis/i });
        if (await runButton.count() > 0) {
            await runButton.scrollIntoViewIfNeeded();
            await runButton.click();
            console.log('   Button clicked, waiting for analysis...');
            await page.waitForTimeout(20000);
        } else {
            console.log('   Run FEM Analysis button not found');
        }
        
        await page.screenshot({ path: path.join(SCREENSHOTS, '02_after_analysis.png') });
        
        console.log('5. Scrolling to look for Load Case dropdown...');
        await page.evaluate(() => window.scrollTo(0, 0));
        await page.waitForTimeout(500);
        
        console.log('6. Looking for Load Case selectbox...');
        const loadCaseLabel = page.locator('text=Load Case');
        const labelCount = await loadCaseLabel.count();
        console.log(`   "Load Case" label found: ${labelCount > 0}`);
        
        const selectboxes = page.locator('[data-baseweb="select"]');
        const selectCount = await selectboxes.count();
        console.log(`   Total selectboxes found: ${selectCount}`);
        
        if (labelCount > 0) {
            await loadCaseLabel.first().scrollIntoViewIfNeeded();
            await page.waitForTimeout(500);
            await page.screenshot({ path: path.join(SCREENSHOTS, '03_load_case_area.png') });
            
            const selectNearLabel = page.locator('text=Load Case').locator('..').locator('[data-baseweb="select"]');
            if (await selectNearLabel.count() > 0) {
                console.log('   Found selectbox near Load Case label, clicking...');
                await selectNearLabel.first().click();
                await page.waitForTimeout(500);
                await page.screenshot({ path: path.join(SCREENSHOTS, '04_dropdown_open.png') });
            }
        }
        
        await page.screenshot({ path: path.join(SCREENSHOTS, '05_final.png'), fullPage: true });
        
        console.log('\n7. Checking page content for load cases...');
        const pageContent = await page.content();
        const hasLoadCaseText = pageContent.includes('Load Case');
        const hasDLOption = pageContent.includes('>DL<') || pageContent.includes('\"DL\"');
        console.log(`   Page contains "Load Case": ${hasLoadCaseText}`);
        console.log(`   Page contains DL option: ${hasDLOption}`);
        
        console.log('\n8. Checking analysis message...');
        const analysisMsg = await page.locator('text=Analysis').first().textContent();
        console.log(`   Analysis message: ${analysisMsg}`);
        
        console.log('\n=== TEST COMPLETE ===\n');
        
    } catch (error) {
        console.error('Test failed:', error.message);
        await page.screenshot({ path: path.join(SCREENSHOTS, 'error.png'), fullPage: true });
    } finally {
        await browser.close();
    }
}

run().catch(console.error);
