const { chromium } = require('playwright');
const path = require('path');

const STREAMLIT_URL = 'http://localhost:8501';
const SCREENSHOT_DIR = path.join(__dirname, 'screenshots');

async function runTest() {
    console.log('=== OPSVIS Force Diagram Debug Test ===\n');

    const browser = await chromium.launch({ headless: false, slowMo: 300 });
    const context = await browser.newContext({
        viewport: { width: 1920, height: 1080 }
    });
    const page = await context.newPage();

    page.on('console', msg => {
        if (msg.type() === 'error' || msg.text().includes('opsvis')) {
            console.log('PAGE:', msg.text());
        }
    });

    try {
        console.log('1. Navigating to Streamlit app...');
        await page.goto(STREAMLIT_URL, { waitUntil: 'networkidle', timeout: 60000 });
        await page.waitForTimeout(3000);
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '01_initial.png') });
        console.log('   Screenshot: 01_initial.png');

        console.log('2. Scrolling to FEM Analysis section...');
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight / 2));
        await page.waitForTimeout(1000);

        const femHeader = page.locator('text=FEM Analysis');
        if (await femHeader.count() > 0) {
            await femHeader.first().scrollIntoViewIfNeeded();
            await page.waitForTimeout(500);
        }
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02_fem_section.png') });
        console.log('   Screenshot: 02_fem_section.png');

        console.log('3. Looking for Run FEM Analysis button...');
        const runButton = page.getByRole('button', { name: /Run FEM Analysis/i });
        const runButtonCount = await runButton.count();
        console.log(`   Found ${runButtonCount} Run FEM Analysis button(s)`);

        if (runButtonCount > 0) {
            await runButton.first().scrollIntoViewIfNeeded();
            await page.waitForTimeout(500);
            console.log('4. Clicking Run FEM Analysis...');
            await runButton.first().click();

            console.log('   Waiting for analysis to complete...');
            await page.waitForTimeout(10000);
            await page.screenshot({ path: path.join(SCREENSHOT_DIR, '03_after_analysis.png') });
            console.log('   Screenshot: 03_after_analysis.png');
        } else {
            console.log('   Run FEM Analysis button not found, checking if already analyzed...');
        }

        console.log('5. Looking for Display Options expander...');
        const displayOptions = page.locator('text=Display Options');
        if (await displayOptions.count() > 0) {
            await displayOptions.first().scrollIntoViewIfNeeded();
            await page.waitForTimeout(500);
            await displayOptions.first().click();
            await page.waitForTimeout(1000);
            console.log('   Expanded Display Options');
        }
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '04_display_options.png') });
        console.log('   Screenshot: 04_display_options.png');

        const opsvisToggle = page.getByRole('checkbox', { name: /Use opsvis force diagram/i });
        if (await opsvisToggle.count() > 0) {
            await opsvisToggle.first().scrollIntoViewIfNeeded();
            try {
                await opsvisToggle.first().click({ force: true });
            } catch (err) {
                await page.evaluate(() => {
                    const input = document.querySelector('input[aria-label="Use opsvis force diagram (experimental)"]');
                    if (input) {
                        input.click();
                    }
                });
            }
            await page.waitForTimeout(1000);
            console.log('   Enabled opsvis force diagram');
        } else {
            const opsvisText = page.getByText('Use opsvis force diagram (experimental)');
            if (await opsvisText.count() > 0) {
                await opsvisText.first().scrollIntoViewIfNeeded();
                await opsvisText.first().click({ force: true });
                await page.waitForTimeout(1000);
                console.log('   Enabled opsvis force diagram (text click)');
            } else {
                console.log('   opsvis toggle not found');
            }
        }

        console.log('6. Looking for Force Type selector...');
        const forceTypeLabel = page.locator('text=Force Type');
        if (await forceTypeLabel.count() > 0) {
            console.log('   Found Force Type label');
        }

        const selectbox = page.locator('[aria-label="Force Type"]');
        if (await selectbox.count() > 0) {
            await selectbox.scrollIntoViewIfNeeded();
            await selectbox.click();
            await page.waitForTimeout(500);
            console.log('   Opened Force Type dropdown');
            await page.screenshot({ path: path.join(SCREENSHOT_DIR, '05_dropdown_open.png') });

            console.log('7. Selecting Mz (Major Moment) force type...');
            const majorOption = page.locator('li:has-text("Mz (Major Moment)")');
            if (await majorOption.count() > 0) {
                await majorOption.first().click();
                console.log('   Selected Mz (Major Moment) option');
            } else {
                const myOption = page.locator('li:has-text("My")');
                if (await myOption.count() > 0) {
                    await myOption.first().click();
                    console.log('   Selected My option');
                }
            }

            console.log('   Waiting for force diagram to render...');
            await page.waitForTimeout(5000);
            await page.screenshot({ path: path.join(SCREENSHOT_DIR, '06_force_diagram.png'), fullPage: true });
            console.log('   Screenshot: 06_force_diagram.png');
        } else {
            console.log('   Force Type selectbox not found');

            const radioMy = page.locator('label:has-text("Mz (Major Moment)")');
            if (await radioMy.count() > 0) {
                console.log('   Found Mz (Major Moment) radio button, clicking...');
                await radioMy.first().scrollIntoViewIfNeeded();
                await radioMy.first().click();
                await page.waitForTimeout(5000);
                await page.screenshot({ path: path.join(SCREENSHOT_DIR, '06_force_diagram.png'), fullPage: true });
            }
        }

        console.log('8. Checking for error messages...');
        const errorMsg = page.locator('text=opsvis force diagram failed');
        if (await errorMsg.count() > 0) {
            console.log('   ERROR DETECTED: opsvis force diagram failed');
            const warningBox = page.locator('.stAlert');
            if (await warningBox.count() > 0) {
                const warningText = await warningBox.first().textContent();
                console.log('   Warning text:', warningText);
            }
        } else {
            console.log('   No error message visible');
        }

        const matplotlibFig = page.locator('.stImage, [data-testid="stImage"]');
        if (await matplotlibFig.count() > 0) {
            console.log('   SUCCESS: Matplotlib figure detected (opsvis worked!)');
        }

        const plotlyChart = page.locator('.js-plotly-plot');
        if (await plotlyChart.count() > 0) {
            console.log('   Plotly chart detected (fallback was used)');
        }

        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '07_final.png'), fullPage: true });
        console.log('   Screenshot: 07_final.png');

        console.log('\n=== TEST COMPLETE ===');
        console.log('Check screenshots directory for results.');

    } catch (error) {
        console.error('\nTest failed:', error.message);
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'error.png'), fullPage: true });
        console.log('Error screenshot saved');
    } finally {
        await page.waitForTimeout(3000);
        await browser.close();
    }
}

runTest().catch(console.error);
