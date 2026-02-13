const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const STREAMLIT_URL = 'http://localhost:8501';
const SCREENSHOT_DIR = path.join(__dirname, 'audit_screenshots', 'omitted_columns_regression');

function ensureDir(dir) {
    fs.mkdirSync(dir, { recursive: true });
}

async function waitForAnalysisCompletion(page, timeoutMs = 180000) {
    const start = Date.now();
    const successBanner = page.locator('text=Analysis Successful').first();
    const previousBanner = page.locator('text=Previous Analysis Available').first();
    const failedBanner = page.locator('text=Analysis Failed').first();

    while (Date.now() - start < timeoutMs) {
        if (await failedBanner.count() > 0) {
            const failText = ((await failedBanner.textContent()) || '').trim();
            throw new Error(`FEM analysis failed: ${failText}`);
        }
        if (await successBanner.count() > 0 || await previousBanner.count() > 0) {
            return;
        }
        await page.waitForTimeout(1000);
    }

    throw new Error(`Timed out after ${timeoutMs}ms waiting for FEM analysis completion`);
}

async function screenshot(page, name) {
    await page.screenshot({
        path: path.join(SCREENSHOT_DIR, name),
        fullPage: true,
    });
}

async function clickIfVisible(locator) {
    if (await locator.count() > 0) {
        await locator.first().scrollIntoViewIfNeeded();
        await locator.first().click();
        return true;
    }
    return false;
}

async function setInputByLabel(page, label, value) {
    const input = page.locator(`input[aria-label="${label}"]`).first();
    if (await input.count() === 0) {
        return false;
    }
    await input.scrollIntoViewIfNeeded();
    await input.fill(String(value));
    await page.waitForTimeout(700);
    return true;
}

async function selectOptionByLabel(page, label, optionText) {
    const combo = page.locator(`[aria-label="${label}"]`).first();
    if (await combo.count() === 0) {
        return false;
    }

    await combo.scrollIntoViewIfNeeded();
    await combo.click({ force: true });
    await page.waitForTimeout(400);

    const optionByRole = page.getByRole('option', { name: optionText }).first();
    if (await optionByRole.count() > 0) {
        await optionByRole.click({ force: true });
        await page.waitForTimeout(700);
        return true;
    }

    const optionByText = page.locator(`li:has-text("${optionText}")`).first();
    if (await optionByText.count() > 0) {
        await optionByText.click({ force: true });
        await page.waitForTimeout(700);
        return true;
    }

    return false;
}

async function getLegendCount(page, label) {
    return await page.locator(`g.legend text:has-text("${label}")`).count();
}

async function runFEMAudit() {
    ensureDir(SCREENSHOT_DIR);
    console.log('Starting omitted-columns Playwright regression audit...');

    const browser = await chromium.launch({ headless: false });
    const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
    const page = await context.newPage();

    try {
        console.log('1) Open app');
        await page.goto(STREAMLIT_URL, { waitUntil: 'networkidle', timeout: 60000 });
        await page.waitForTimeout(3000);
        await screenshot(page, '01_initial.png');

        console.log('2) Configure tube core and dimensions that trigger omitted-column suggestions');
        await setInputByLabel(page, 'Bays in X', 3);
        await setInputByLabel(page, 'Bays in Y', 2);
        await setInputByLabel(page, 'Floors', 8);

        const coreWallCheckbox = page.getByLabel('Core Wall System').first();
        if (await coreWallCheckbox.count() > 0) {
            if (!await coreWallCheckbox.isChecked()) {
                const coreWallLabel = page.locator('label:has-text("Core Wall System")').first();
                await coreWallLabel.scrollIntoViewIfNeeded();
                await coreWallLabel.click({ force: true });
                await page.waitForTimeout(1200);
            }

            const coreWallCheckboxPost = page.getByLabel('Core Wall System').first();
            if (!await coreWallCheckboxPost.isChecked()) {
                throw new Error('Core Wall System checkbox remained unchecked');
            }
        }

        const configSelected = await selectOptionByLabel(page, 'Core Wall Configuration', 'Tube with Openings');
        console.log(`   Core config select success: ${configSelected}`);
        if (!configSelected) {
            const tubeCardClicked = await clickIfVisible(page.getByRole('button', { name: 'Tube with Openings' }));
            console.log(`   Tube card click success: ${tubeCardClicked}`);
            if (!tubeCardClicked) {
                throw new Error('Tube with Openings selector not found');
            }
            await page.waitForTimeout(1200);
        }

        const lengthXSet = await setInputByLabel(page, 'Length X (m)', 7.0);
        const lengthYSet = await setInputByLabel(page, 'Length Y (m)', 7.0);
        console.log(`   Length inputs found: X=${lengthXSet}, Y=${lengthYSet}`);
        if (!lengthXSet || !lengthYSet) {
            throw new Error('Tube Length X/Y inputs not found; could not force omission scenario');
        }
        await screenshot(page, '02_geometry_set.png');

        console.log('3) Open Column Omission Review and verify suggestions are present');
        const omissionExpander = page
            .locator('[data-testid="stSidebar"]')
            .getByText('Column Omission Review')
            .first();
        if (await omissionExpander.count() === 0) {
            throw new Error('Column Omission Review expander not found');
        }
        await omissionExpander.scrollIntoViewIfNeeded();
        await omissionExpander.click({ force: true });
        await page.waitForTimeout(1000);

        const suggestionLine = page
            .locator('[data-testid="stSidebar"]')
            .locator('text=/columns suggested for omission:/i')
            .first();
        if (await suggestionLine.count() === 0) {
            throw new Error('No omitted-column suggestions detected; scenario not reproduced');
        }
        const suggestionText = (await suggestionLine.textContent()) || '';
        console.log(`   ${suggestionText.trim()}`);
        await screenshot(page, '03_sidebar_omit_controls.png');

        console.log('4) Run FEM analysis');
        const runButton = page.getByRole('button', { name: /Run FEM Analysis/i }).first();
        if (await runButton.count() === 0) {
            throw new Error('Run FEM Analysis button not found');
        }
        await runButton.scrollIntoViewIfNeeded();
        if (!await runButton.isDisabled()) {
            await runButton.click();
            await waitForAnalysisCompletion(page);
        }
        await screenshot(page, '04_analysis_complete.png');

        console.log('5) Open Plan View and capture omitted-columns legend count');
        await clickIfVisible(page.getByRole('button', { name: 'Plan View' }));
        await page.waitForTimeout(1500);
        const countBefore = await getLegendCount(page, 'Omitted Columns');
        console.log(`   Legend count before toggle: ${countBefore}`);
        await screenshot(page, '05_plan_before_toggle.png');

        console.log('6) Toggle "Show ghost cols" OFF and verify legend hides');
        const displayOptionsExpander = page.getByText('Display Options').first();
        await displayOptionsExpander.scrollIntoViewIfNeeded();
        await displayOptionsExpander.click();
        await page.waitForTimeout(700);

        const showGhostLabel = page.locator('label:has-text("Show ghost cols")').first();
        const showGhostInput = page.locator('input[aria-label="Show ghost cols"]').first();
        let ghostBefore = null;
        if (await showGhostInput.count() > 0) {
            ghostBefore = await showGhostInput.isChecked();
        }
        if (await showGhostLabel.count() > 0) {
            await showGhostLabel.scrollIntoViewIfNeeded();
            await showGhostLabel.click({ force: true });
            await page.waitForTimeout(1200);
        } else {
            console.log('   "Show ghost cols" control not found');
        }

        let ghostAfter = null;
        if (await showGhostInput.count() > 0) {
            ghostAfter = await showGhostInput.isChecked();
        }
        console.log(`   Show ghost cols state: before=${ghostBefore}, after=${ghostAfter}`);

        const countAfter = await getLegendCount(page, 'Omitted Columns');
        console.log(`   Legend count after toggle OFF: ${countAfter}`);
        await screenshot(page, '06_plan_after_toggle_off.png');

        if (countBefore === 0) {
            throw new Error('Omitted-columns legend not rendered; scenario reproduction failed');
        }
        if (countBefore > 1) {
            throw new Error(`Regression: duplicate "Omitted Columns" legend entries (${countBefore})`);
        }
        if (countBefore > 0 && countAfter > 0) {
            throw new Error(
                `Regression: omitted-columns legend still visible after toggle off (before=${countBefore}, after=${countAfter})`
            );
        }

        console.log('PASS: omitted-columns legend duplication/toggle regression not observed in this run.');
        console.log(`Screenshots saved to: ${SCREENSHOT_DIR}`);
    } catch (error) {
        console.error(`FAIL: ${error.message}`);
        await screenshot(page, '99_error_state.png');
        throw error;
    } finally {
        await browser.close();
    }
}

runFEMAudit().catch((error) => {
    console.error(error);
    process.exit(1);
});
