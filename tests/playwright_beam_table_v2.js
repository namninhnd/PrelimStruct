const { chromium } = require('playwright');
const path = require('path');

const STREAMLIT_URL = 'http://localhost:8501';
const SCREENSHOT_DIR = path.join(__dirname, '..', 'screenshots');

async function testBeamForcesTable() {
    console.log('=== PLAYWRIGHT TEST: Beam Forces Table (v2) ===\n');
    
    const browser = await chromium.launch({ headless: false, slowMo: 50 });
    const context = await browser.newContext({ 
        viewport: { width: 1920, height: 1080 } 
    });
    const page = await context.newPage();
    
    try {
        console.log('1. Navigating to Streamlit app...');
        await page.goto(STREAMLIT_URL, { waitUntil: 'networkidle', timeout: 60000 });
        await page.waitForTimeout(3000);
        
        console.log('\n2. Refreshing page to ensure latest code...');
        await page.reload({ waitUntil: 'networkidle' });
        await page.waitForTimeout(3000);
        
        console.log('\n3. Running FEM Analysis...');
        const runButton = page.getByRole('button', { name: /Run FEM Analysis/i });
        if (await runButton.count() > 0) {
            await runButton.scrollIntoViewIfNeeded();
            await runButton.click();
            console.log('   Waiting for analysis...');
            await page.waitForTimeout(12000);
            console.log('   Analysis completed');
        }
        
        console.log('\n4. Searching for Beam Section Forces expander...');
        
        const pageContent = await page.content();
        const hasBeamSectionForces = pageContent.includes('Beam Section Forces');
        console.log('   Page contains "Beam Section Forces":', hasBeamSectionForces);
        
        const hasReactionForces = pageContent.includes('Reaction Forces Table');
        console.log('   Page contains "Reaction Forces Table":', hasReactionForces);
        
        if (hasReactionForces) {
            const reactionExpander = page.locator('text=Reaction Forces Table');
            if (await reactionExpander.count() > 0) {
                await reactionExpander.first().scrollIntoViewIfNeeded();
                console.log('   Found Reaction Forces Table - scrolling near it');
                await page.waitForTimeout(500);
                
                await page.evaluate(() => window.scrollBy(0, 200));
                await page.waitForTimeout(500);
            }
        }
        
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'beam_v2_01_reaction_area.png'), fullPage: true });
        
        const allText = await page.locator('body').textContent();
        const lines = allText.split('\n').filter(l => l.includes('Beam') || l.includes('Forces') || l.includes('Table'));
        console.log('   Lines with Beam/Forces/Table:', lines.slice(0, 10));
        
        console.log('\n5. Looking for all expanders on page...');
        const allExpanders = page.locator('[data-testid="stExpander"], details');
        const expanderCount = await allExpanders.count();
        console.log(`   Found ${expanderCount} expanders`);
        
        for (let i = 0; i < Math.min(expanderCount, 10); i++) {
            const expander = allExpanders.nth(i);
            const text = await expander.textContent();
            if (text) {
                console.log(`   [${i}] ${text.substring(0, 60)}...`);
            }
        }
        
        console.log('\n6. Scrolling to bottom of page...');
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await page.waitForTimeout(1000);
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'beam_v2_02_bottom.png'), fullPage: true });
        
        console.log('\n=== TEST COMPLETE ===');
        console.log('Screenshots saved to:', SCREENSHOT_DIR);
        
        await page.waitForTimeout(3000);
        
    } catch (error) {
        console.error('\nTest error:', error.message);
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'beam_v2_error.png'), fullPage: true });
    } finally {
        await browser.close();
    }
}

testBeamForcesTable().catch(console.error);
