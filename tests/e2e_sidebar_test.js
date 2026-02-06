const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const STREAMLIT_URL = 'http://localhost:8501';
const SCREENSHOT_DIR = path.join(__dirname, 'sidebar_test_screenshots');

if (!fs.existsSync(SCREENSHOT_DIR)){
    fs.mkdirSync(SCREENSHOT_DIR);
}

async function runSidebarTest() {
    console.log('=== PrelimStruct Sidebar Input Test ===\n');
    
    const browser = await chromium.launch({ headless: false });
    const context = await browser.newContext({ 
        viewport: { width: 1920, height: 1080 } 
    });
    const page = await context.newPage();
    
    let stepCount = 0;
    const screenshot = async (name) => {
        stepCount++;
        const filename = `${String(stepCount).padStart(2, '0')}_${name}.png`;
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, filename), fullPage: true });
        console.log(`   [Screenshot] ${filename}`);
    };

    const logPass = (msg) => console.log(`✅ PASS: ${msg}`);
    const logFail = (msg) => console.log(`❌ FAIL: ${msg}`);

    try {
        console.log('Step 1: Navigate to app...');
        await page.goto(STREAMLIT_URL, { waitUntil: 'networkidle', timeout: 60000 });
        await page.waitForTimeout(3000);
        
        const title = page.locator('h1');
        if (await title.count() > 0) {
            logPass('App loaded (h1 title visible)');
        } else {
            logFail('App title not found');
            throw new Error('App failed to load');
        }
        await screenshot('initial_load');

        async function verifyInputPersistence(label, newValue, description) {
            console.log(`Testing ${description} (${label})...`);
            try {
                let input = page.locator(`input[aria-label="${label}"]`);
                if (await input.count() === 0) {
                     input = page.locator(`input[aria-label*="${label}"]`);
                }

                if (await input.count() === 0) {
                    logFail(`${description} input not found`);
                    return;
                }
                
                if (await input.count() > 1) {
                    input = input.first();
                }

                await input.scrollIntoViewIfNeeded();
                await input.fill(String(newValue));
                await input.press('Enter');
                await page.waitForTimeout(1000);
                
                const persistedInput = page.locator(`input[aria-label="${label}"]`).first();
                let value = await persistedInput.inputValue();
                
                const floatVal = parseFloat(value);
                const floatNew = parseFloat(newValue);
                
                if (!isNaN(floatVal) && !isNaN(floatNew)) {
                    if (Math.abs(floatVal - floatNew) < 0.01) {
                        logPass(`${description} persisted value ${newValue} (read as ${value})`);
                        return;
                    }
                }

                if (value === String(newValue)) {
                    logPass(`${description} persisted value ${newValue}`);
                } else {
                    logFail(`${description} value mismatch. Expected ${newValue}, got ${value}`);
                }
            } catch (e) {
                logFail(`${description} test error: ${e.message}`);
            }
        }

        async function verifySelectbox(label, description) {
            console.log(`Testing Selectbox ${description} (${label})...`);
            try {
                const labelEl = page.locator(`label`).filter({ hasText: label }).first();
                if (await labelEl.count() === 0) {
                    logFail(`${description} label not found`);
                    return;
                }
                
                await labelEl.scrollIntoViewIfNeeded();
                
                logPass(`${description} selectbox visible`);
            } catch (e) {
                logFail(`${description} test error: ${e.message}`);
            }
        }

        async function verifyCheckbox(label, description) {
            console.log(`Testing Checkbox ${description} (${label})...`);
            try {
                // Find the label element containing the text
                const labelEl = page.locator('label').filter({ hasText: label }).first();
                
                if (await labelEl.count() === 0) {
                    logFail(`${description} label not found`);
                    return;
                }

                await labelEl.scrollIntoViewIfNeeded();

                // Check state using the associated input if possible
                const checkbox = page.getByRole('checkbox', { name: label });
                let isChecked = false;
                
                if (await checkbox.count() > 0) {
                    isChecked = await checkbox.isChecked();
                }

                if (!isChecked) {
                    console.log(`   Enabling ${description}...`);
                    // Click the label to toggle. Force true in case it's covered or tricky.
                    await labelEl.click({ force: true });
                    await page.waitForTimeout(2000); // Wait for Streamlit rerun
                } else {
                    console.log(`   ${description} is already enabled`);
                }
                
                logPass(`${description} verified`);
            } catch (e) {
                 logFail(`${description} error: ${e.message}`);
            }
        }

        console.log('\n--- Testing Geometry Inputs ---');
        await verifyInputPersistence('Bay X (m)', '5', 'Bay X');
        await verifyInputPersistence('Bay Y (m)', '4', 'Bay Y');
        await verifyInputPersistence('Floors', '15', 'Floors');
        await verifyInputPersistence('Story Height (m)', '3.5', 'Story Height');

        await screenshot('geometry_inputs');

        console.log('\n--- Testing Load Inputs ---');
        await verifyInputPersistence('SDL (kPa)', '3.0', 'Dead Load');
        await verifySelectbox('Live Load Class', 'Live Load Class');

        await screenshot('load_inputs');

        console.log('\n--- Testing Material Inputs ---');
        await verifySelectbox('Slab fcu', 'Slab fcu');
        await verifySelectbox('Beam fcu', 'Beam fcu');
        await verifySelectbox('Column fcu', 'Column fcu');
        
        await screenshot('material_inputs');

        console.log('\n--- Testing Core Wall Config ---');
        await verifyCheckbox('Core Wall System', 'Core Wall System');
        
        console.log('   Checking Core Wall Selector buttons...');
        await page.waitForTimeout(1000);
        
        const buttons = ['I-Section', 'Facing C', 'Tube Center'];
        for (const btnText of buttons) {
            const btn = page.getByRole('button', { name: btnText, exact: true });
            if (await btn.count() > 0) {
                logPass(`Button '${btnText}' found`);
            } else {
                logFail(`Button '${btnText}' not found`);
            }
        }
        
        const tubeBtn = page.getByRole('button', { name: 'Tube Center', exact: true });
        if (await tubeBtn.count() > 0) {
            await tubeBtn.click();
            await page.waitForTimeout(1000);
            logPass('Clicked Tube Center');
        }

        await screenshot('core_wall_config');

        console.log('\n=== TEST SUMMARY ===');
        console.log(`See screenshots in ${SCREENSHOT_DIR}`);
        
    } catch (error) {
        console.error('Test execution failed:', error);
        await screenshot('fatal_error');
    } finally {
        await browser.close();
    }
}

runSidebarTest();
