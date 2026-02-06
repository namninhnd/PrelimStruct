const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const STREAMLIT_URL = 'http://localhost:8502';
const SCREENSHOT_DIR = path.join(__dirname, 'test_screenshots');

if (!fs.existsSync(SCREENSHOT_DIR)) {
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

let stepCounter = 0;
const screenshot = async (page, name) => {
    stepCounter++;
    const filename = `${String(stepCounter).padStart(2, '0')}_${name}.png`;
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, filename), fullPage: true });
    console.log(`  Screenshot: ${filename}`);
};

const issues = [];
const recordIssue = (category, description, severity = 'medium') => {
    issues.push({ category, description, severity, step: stepCounter });
    console.log(`  [ISSUE-${severity.toUpperCase()}] ${category}: ${description}`);
};

async function runAudit() {
    console.log('='.repeat(60));
    console.log('PRELIMSTRUCT v3.5 COMPREHENSIVE AUDIT');
    console.log('='.repeat(60));
    
    const browser = await chromium.launch({ headless: false, slowMo: 100 });
    const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
    const page = await context.newPage();
    
    page.on('console', msg => {
        if (msg.type() === 'error') {
            recordIssue('Console', msg.text(), 'low');
        }
    });
    
    page.on('pageerror', err => {
        recordIssue('PageError', err.message, 'high');
    });

    try {
        console.log('\n[PHASE 1] Initial Load');
        console.log('-'.repeat(40));
        
        await page.goto(STREAMLIT_URL, { waitUntil: 'networkidle', timeout: 60000 });
        await page.waitForTimeout(3000);
        await screenshot(page, 'initial_load');
        
        const title = await page.title();
        console.log(`  Page title: ${title}`);
        
        const mainContent = await page.locator('.main').count();
        if (mainContent === 0) {
            recordIssue('Layout', 'Main content area not found', 'high');
        }
        
        console.log('\n[PHASE 2] Sidebar Configuration');
        console.log('-'.repeat(40));
        
        const sidebar = page.locator('[data-testid="stSidebar"]');
        if (await sidebar.count() > 0) {
            console.log('  Sidebar found');
            
            await page.evaluate(() => {
                const sidebar = document.querySelector('[data-testid="stSidebar"]');
                if (sidebar) sidebar.scrollTop = 0;
            });
            await page.waitForTimeout(500);
            
            const floorsInput = page.locator('input[aria-label="Floors"]');
            if (await floorsInput.count() > 0) {
                await floorsInput.scrollIntoViewIfNeeded();
                await floorsInput.fill('');
                await floorsInput.fill('15');
                console.log('  Set Floors to 15');
                await page.waitForTimeout(1000);
            }
            
            const baysXInput = page.locator('input[aria-label*="Bays"]').first();
            if (await baysXInput.count() > 0) {
                await baysXInput.scrollIntoViewIfNeeded();
                await baysXInput.fill('');
                await baysXInput.fill('4');
                console.log('  Set Bays X to 4');
                await page.waitForTimeout(1000);
            }
            
            await screenshot(page, 'sidebar_configured');
        } else {
            recordIssue('Layout', 'Sidebar not found', 'high');
        }
        
        console.log('\n[PHASE 3] Main Dashboard Metrics');
        console.log('-'.repeat(40));
        
        await page.evaluate(() => window.scrollTo(0, 0));
        await page.waitForTimeout(500);
        
        const metrics = await page.locator('[data-testid="stMetric"]').count();
        console.log(`  Found ${metrics} metric cards`);
        
        if (metrics < 3) {
            recordIssue('Dashboard', `Only ${metrics} metrics found, expected >= 3`, 'medium');
        }
        
        await screenshot(page, 'dashboard_metrics');
        
        console.log('\n[PHASE 4] Design Results Section');
        console.log('-'.repeat(40));
        
        await page.evaluate(() => window.scrollBy(0, 600));
        await page.waitForTimeout(1000);
        await screenshot(page, 'design_results');
        
        const tabs = await page.locator('[data-baseweb="tab"]').count();
        console.log(`  Found ${tabs} tabs`);
        
        console.log('\n[PHASE 5] FEM Analysis Section');
        console.log('-'.repeat(40));
        
        const femSection = page.locator('text=FEM Analysis');
        if (await femSection.count() > 0) {
            await femSection.scrollIntoViewIfNeeded();
            await page.waitForTimeout(1000);
            await screenshot(page, 'fem_section_before_analysis');
            
            const runButton = page.getByRole('button', { name: /Run FEM Analysis/i });
            if (await runButton.count() > 0) {
                const isDisabled = await runButton.isDisabled();
                console.log(`  Run FEM Analysis button disabled: ${isDisabled}`);
                
                if (!isDisabled) {
                    console.log('  Clicking Run FEM Analysis...');
                    await runButton.click();
                    
                    await page.waitForTimeout(10000);
                    await screenshot(page, 'fem_analysis_running');
                    
                    const successMsg = await page.locator('text=Success').count();
                    const failedMsg = await page.locator('text=Failed').count();
                    const errorMsg = await page.locator('text=Error').count();
                    
                    if (successMsg > 0) {
                        console.log('  FEM Analysis: SUCCESS');
                    } else if (failedMsg > 0) {
                        console.log('  FEM Analysis: FAILED');
                        recordIssue('FEM', 'FEM analysis failed', 'high');
                    } else if (errorMsg > 0) {
                        console.log('  FEM Analysis: ERROR');
                        recordIssue('FEM', 'FEM analysis error', 'high');
                    }
                    
                    await screenshot(page, 'fem_analysis_complete');
                }
            } else {
                recordIssue('FEM', 'Run FEM Analysis button not found', 'high');
            }
        } else {
            recordIssue('FEM', 'FEM Analysis section not found', 'high');
        }
        
        console.log('\n[PHASE 6] FEM Visualization Views');
        console.log('-'.repeat(40));
        
        const viewTabs = ['Plan View', 'Elevation View', '3D View'];
        for (const viewName of viewTabs) {
            const tab = page.locator(`[data-baseweb="tab"]:has-text("${viewName}")`);
            if (await tab.count() > 0) {
                await tab.click();
                await page.waitForTimeout(2000);
                console.log(`  Switched to ${viewName}`);
                await screenshot(page, `view_${viewName.toLowerCase().replace(' ', '_')}`);
                
                const plotlyChart = await page.locator('.js-plotly-plot').count();
                if (plotlyChart === 0) {
                    recordIssue('Visualization', `${viewName} has no Plotly chart`, 'medium');
                }
            } else {
                recordIssue('Navigation', `${viewName} tab not found`, 'medium');
            }
        }
        
        console.log('\n[PHASE 7] Display Options');
        console.log('-'.repeat(40));
        
        const displayExpander = page.locator('text=Display Options');
        if (await displayExpander.count() > 0) {
            await displayExpander.scrollIntoViewIfNeeded();
            await displayExpander.click();
            await page.waitForTimeout(1000);
            await screenshot(page, 'display_options_expanded');
            
            const forceTypes = ['None', 'Mz', 'Vy', 'N'];
            for (const forceType of forceTypes) {
                const radioLabel = page.locator(`label:has-text("${forceType}")`).first();
                if (await radioLabel.count() > 0) {
                    await radioLabel.click({ force: true });
                    await page.waitForTimeout(1500);
                    console.log(`  Selected Force Type: ${forceType}`);
                    if (forceType !== 'None') {
                        await screenshot(page, `force_diagram_${forceType.toLowerCase()}`);
                    }
                }
            }
        }
        
        console.log('\n[PHASE 8] Reaction Table');
        console.log('-'.repeat(40));
        
        const reactionExpander = page.locator('text=Reaction Forces Table');
        if (await reactionExpander.count() > 0) {
            await reactionExpander.scrollIntoViewIfNeeded();
            await reactionExpander.click();
            await page.waitForTimeout(1000);
            await screenshot(page, 'reaction_table');
            
            const table = await page.locator('table').count();
            const dataframe = await page.locator('[data-testid="stDataFrame"]').count();
            if (table === 0 && dataframe === 0) {
                recordIssue('ReactionTable', 'No table/dataframe found in reaction section', 'medium');
            } else {
                console.log('  Reaction table found');
            }
            
            const loadCaseSelector = page.locator('[aria-label="Load Case"]');
            if (await loadCaseSelector.count() > 0) {
                console.log('  Load Case selector found');
            }
        }
        
        console.log('\n[PHASE 9] Export Functions');
        console.log('-'.repeat(40));
        
        const exportSection = page.locator('text=Export Visualization');
        if (await exportSection.count() > 0) {
            await exportSection.scrollIntoViewIfNeeded();
            await page.waitForTimeout(500);
            await screenshot(page, 'export_section');
            console.log('  Export section found');
        }
        
        console.log('\n[PHASE 10] Model Statistics');
        console.log('-'.repeat(40));
        
        const statsSection = page.locator('text=Model Statistics');
        if (await statsSection.count() > 0) {
            await statsSection.scrollIntoViewIfNeeded();
            await page.waitForTimeout(500);
            await screenshot(page, 'model_statistics');
            console.log('  Model Statistics section found');
        }
        
        console.log('\n[PHASE 11] Unlock/Lock Functionality');
        console.log('-'.repeat(40));
        
        const unlockButton = page.getByRole('button', { name: /Unlock/i });
        if (await unlockButton.count() > 0) {
            console.log('  Model is locked, testing unlock...');
            await unlockButton.click();
            await page.waitForTimeout(1000);
            await screenshot(page, 'after_unlock');
            
            const runButton = page.getByRole('button', { name: /Run FEM Analysis/i });
            const isNowEnabled = await runButton.isEnabled();
            console.log(`  Run button enabled after unlock: ${isNowEnabled}`);
            
            if (!isNowEnabled) {
                recordIssue('Lock', 'Run button still disabled after unlock', 'high');
            }
        }
        
        console.log('\n[PHASE 12] Edge Cases - Extreme Values');
        console.log('-'.repeat(40));
        
        const floorsInputExtreme = page.locator('input[aria-label="Floors"]');
        if (await floorsInputExtreme.count() > 0) {
            await floorsInputExtreme.scrollIntoViewIfNeeded();
            await floorsInputExtreme.fill('');
            await floorsInputExtreme.fill('50');
            await page.waitForTimeout(2000);
            await screenshot(page, 'extreme_50_floors');
            console.log('  Set extreme value: 50 floors');
            
            const errorMsgs = await page.locator('.stAlert').count();
            console.log(`  Alert messages: ${errorMsgs}`);
        }
        
        console.log('\n' + '='.repeat(60));
        console.log('AUDIT COMPLETE');
        console.log('='.repeat(60));
        
        console.log('\n[SUMMARY]');
        console.log('-'.repeat(40));
        console.log(`Total steps: ${stepCounter}`);
        console.log(`Issues found: ${issues.length}`);
        
        if (issues.length > 0) {
            console.log('\n[ISSUES DETAIL]');
            const high = issues.filter(i => i.severity === 'high');
            const medium = issues.filter(i => i.severity === 'medium');
            const low = issues.filter(i => i.severity === 'low');
            
            if (high.length > 0) {
                console.log('\nHIGH SEVERITY:');
                high.forEach(i => console.log(`  - [${i.category}] ${i.description}`));
            }
            if (medium.length > 0) {
                console.log('\nMEDIUM SEVERITY:');
                medium.forEach(i => console.log(`  - [${i.category}] ${i.description}`));
            }
            if (low.length > 0) {
                console.log('\nLOW SEVERITY:');
                low.forEach(i => console.log(`  - [${i.category}] ${i.description}`));
            }
        } else {
            console.log('\nNo issues found!');
        }
        
        fs.writeFileSync(
            path.join(SCREENSHOT_DIR, 'audit_report.json'),
            JSON.stringify({ steps: stepCounter, issues, timestamp: new Date().toISOString() }, null, 2)
        );
        console.log(`\nReport saved to: ${path.join(SCREENSHOT_DIR, 'audit_report.json')}`);
        
    } catch (error) {
        console.error('\n[FATAL ERROR]', error.message);
        await screenshot(page, 'error_state');
        recordIssue('Fatal', error.message, 'high');
    } finally {
        await page.waitForTimeout(2000);
        await browser.close();
    }
}

runAudit().catch(console.error);
