const { chromium } = require('playwright');
const path = require('path');

const STREAMLIT_URL = 'http://localhost:8501';
const SCREENSHOT_DIR = path.join(__dirname, '..', 'screenshots');

async function testBeamForcesTable() {
    console.log('=== PLAYWRIGHT TEST: Beam Forces Table ===\n');
    
    const browser = await chromium.launch({ headless: false, slowMo: 50 });
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
            console.log('   Waiting for analysis...');
            await page.waitForTimeout(10000);
            console.log('   Analysis completed');
        }
        
        console.log('\n3. Looking for Beam Section Forces expander...');
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight * 0.7));
        await page.waitForTimeout(500);
        
        const beamForcesExpander = page.locator('details summary:has-text("Beam Section Forces"), [data-testid="stExpander"]:has-text("Beam Section Forces")');
        if (await beamForcesExpander.count() > 0) {
            await beamForcesExpander.first().scrollIntoViewIfNeeded();
            await beamForcesExpander.first().click();
            await page.waitForTimeout(1000);
            console.log('   Opened Beam Section Forces expander');
            
            await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'beam_table_01_opened.png'), fullPage: true });
        } else {
            console.log('   Beam Section Forces expander NOT found');
            
            const allExpanders = await page.locator('[data-testid="stExpander"] summary, details summary').allTextContents();
            console.log('   Available expanders:', allExpanders.slice(0, 5));
        }
        
        console.log('\n4. Looking for beam forces table...');
        const dataframe = page.locator('[data-testid="stDataFrame"], .dataframe, table');
        if (await dataframe.count() > 0) {
            console.log('   Found dataframe/table');
            await dataframe.first().scrollIntoViewIfNeeded();
            await dataframe.first().screenshot({ path: path.join(SCREENSHOT_DIR, 'beam_table_02_dataframe.png') });
        }
        
        console.log('\n5. Checking for floor selector...');
        const floorSelector = page.locator('[aria-label="Floor Level"], select:near(:text("Floor Level"))');
        if (await floorSelector.count() > 0) {
            console.log('   Floor selector found');
        }
        
        console.log('\n6. Checking for beam selector...');
        const beamSelector = page.locator('[aria-label="Beam"], select:near(:text("Beam"))');
        if (await beamSelector.count() > 0) {
            console.log('   Beam selector found');
        }
        
        console.log('\n7. Checking for download buttons...');
        const csvButton = page.getByRole('button', { name: /Download CSV/i });
        const excelButton = page.getByRole('button', { name: /Download Excel/i });
        
        if (await csvButton.count() > 0) {
            console.log('   CSV download button found');
        }
        if (await excelButton.count() > 0) {
            console.log('   Excel download button found');
        }
        
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'beam_table_03_final.png'), fullPage: true });
        
        console.log('\n=== TEST COMPLETE ===');
        console.log('Screenshots saved to:', SCREENSHOT_DIR);
        
        await page.waitForTimeout(3000);
        
    } catch (error) {
        console.error('\nTest error:', error.message);
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'beam_table_error.png'), fullPage: true });
    } finally {
        await browser.close();
    }
}

testBeamForcesTable().catch(console.error);
