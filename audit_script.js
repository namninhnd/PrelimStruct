const { chromium } = require('playwright');
const path = require('path');

const STREAMLIT_URL = 'http://localhost:8501';
const SCREENSHOT_DIR = path.join(__dirname, 'audit_screenshots');

async function runAudit() {
    console.log('=== PrelimStruct UI/UX Audit Starting ===\n');
    
    const browser = await chromium.launch({ headless: false });
    const context = await browser.newContext({ 
        viewport: { width: 1920, height: 1080 } 
    });
    const page = await context.newPage();
    
    const findings = {
        screenshots: [],
        issues: [],
        observations: [],
        interactions: []
    };
    
    try {
        // 1. INITIAL NAVIGATION
        console.log('1. Navigating to app...');
        await page.goto(STREAMLIT_URL, { waitUntil: 'networkidle', timeout: 60000 });
        await page.waitForTimeout(3000);
        
        const screenshotPath1 = path.join(SCREENSHOT_DIR, '01_initial_state.png');
        await page.screenshot({ path: screenshotPath1, fullPage: true });
        findings.screenshots.push('01_initial_state.png');
        console.log('   ✓ Initial state captured');
        
        // 2. CONFIGURE GEOMETRY
        console.log('\n2. Configuring multi-bay building...');
        
        // Bay X: 8.0m
        const bayX = page.locator('input[aria-label="Bay X (m)"]').first();
        if (await bayX.count() > 0) {
            await bayX.scrollIntoViewIfNeeded();
            await bayX.fill('8.0');
            await page.waitForTimeout(800);
            findings.observations.push('Bay X input found and set to 8.0');
        } else {
            findings.issues.push({ element: 'input[aria-label="Bay X (m)"]', issue: 'Element not found', severity: 'critical' });
        }
        
        // Bay Y: 10.0m
        const bayY = page.locator('input[aria-label="Bay Y (m)"]').first();
        if (await bayY.count() > 0) {
            await bayY.scrollIntoViewIfNeeded();
            await bayY.fill('10.0');
            await page.waitForTimeout(800);
            findings.observations.push('Bay Y input found and set to 10.0');
        } else {
            findings.issues.push({ element: 'input[aria-label="Bay Y (m)"]', issue: 'Element not found', severity: 'critical' });
        }
        
        // Bays in X: 4
        const baysX = page.locator('input[aria-label="Bays in X"]').first();
        if (await baysX.count() > 0) {
            await baysX.scrollIntoViewIfNeeded();
            await baysX.fill('4');
            await page.waitForTimeout(800);
            findings.observations.push('Bays in X set to 4');
        } else {
            findings.issues.push({ element: 'input[aria-label="Bays in X"]', issue: 'Element not found', severity: 'critical' });
        }
        
        // Bays in Y: 3
        const baysY = page.locator('input[aria-label="Bays in Y"]').first();
        if (await baysY.count() > 0) {
            await baysY.scrollIntoViewIfNeeded();
            await baysY.fill('3');
            await page.waitForTimeout(800);
            findings.observations.push('Bays in Y set to 3');
        } else {
            findings.issues.push({ element: 'input[aria-label="Bays in Y"]', issue: 'Element not found', severity: 'critical' });
        }
        
        // Floors: 25
        const floors = page.locator('input[aria-label="Floors"]').first();
        if (await floors.count() > 0) {
            await floors.scrollIntoViewIfNeeded();
            await floors.fill('25');
            await page.waitForTimeout(800);
            findings.observations.push('Floors set to 25');
        } else {
            findings.issues.push({ element: 'input[aria-label="Floors"]', issue: 'Element not found', severity: 'critical' });
        }
        
        // Story Height: 3.5m
        const storyHeight = page.locator('input[aria-label="Story Height (m)"]').first();
        if (await storyHeight.count() > 0) {
            await storyHeight.scrollIntoViewIfNeeded();
            await storyHeight.fill('3.5');
            await page.waitForTimeout(800);
            findings.observations.push('Story Height set to 3.5m');
        } else {
            findings.issues.push({ element: 'input[aria-label="Story Height (m)"]', issue: 'Element not found', severity: 'critical' });
        }
        
        const screenshotPath2 = path.join(SCREENSHOT_DIR, '02_geometry_configured.png');
        await page.screenshot({ path: screenshotPath2, fullPage: true });
        findings.screenshots.push('02_geometry_configured.png');
        console.log('   ✓ Geometry configured');
        
        // 3. ENABLE CORE WALL SYSTEM
        console.log('\n3. Enabling Core Wall System...');
        
        // Look for Core Wall checkbox
        const coreWallCheckbox = page.locator('input[type="checkbox"]').filter({ hasText: /Core Wall/i });
        const coreWallLabel = page.locator('label:has-text("Enable Core Wall")');
        
        if (await coreWallLabel.count() > 0) {
            await coreWallLabel.scrollIntoViewIfNeeded();
            await coreWallLabel.click();
            await page.waitForTimeout(1500);
            findings.observations.push('Core Wall System enabled via label');
        } else if (await coreWallCheckbox.count() > 0) {
            await coreWallCheckbox.first().click({ force: true });
            await page.waitForTimeout(1500);
            findings.observations.push('Core Wall System enabled via checkbox');
        } else {
            findings.issues.push({ element: 'Core Wall checkbox', issue: 'Element not found', severity: 'high' });
        }
        
        // 4. SELECT I_SECTION CONFIGURATION
        console.log('\n4. Selecting I_SECTION configuration...');
        
        // Look for configuration selector (might be radio buttons or selectbox)
        const iSectionRadio = page.locator('label:has-text("I_SECTION")');
        
        if (await iSectionRadio.count() > 0) {
            await iSectionRadio.scrollIntoViewIfNeeded();
            await iSectionRadio.click();
            await page.waitForTimeout(1000);
            findings.observations.push('I_SECTION configuration selected');
        } else {
            findings.issues.push({ element: 'I_SECTION radio', issue: 'Element not found', severity: 'medium' });
        }
        
        const screenshotPath3 = path.join(SCREENSHOT_DIR, '03_core_wall_configured.png');
        await page.screenshot({ path: screenshotPath3, fullPage: true });
        findings.screenshots.push('03_core_wall_configured.png');
        console.log('   ✓ Core wall configuration captured');
        
        // 5. LOOK FOR FRAMING PLAN VISUALIZATION
        console.log('\n5. Checking for framing plan visualization...');
        
        await page.evaluate(() => window.scrollBy(0, 500));
        await page.waitForTimeout(1000);
        
        const framingPlan = await page.locator('h3:has-text("Framing Plan")').count();
        if (framingPlan > 0) {
            findings.observations.push('Framing Plan section found');
            const screenshotPath4 = path.join(SCREENSHOT_DIR, '04_framing_plan.png');
            await page.screenshot({ path: screenshotPath4, fullPage: true });
            findings.screenshots.push('04_framing_plan.png');
        } else {
            findings.observations.push('Framing Plan section not visible');
        }
        
        // 6. LOOK FOR FEM VIEWS SECTION
        console.log('\n6. Checking for FEM Views section...');
        
        await page.evaluate(() => window.scrollBy(0, 500));
        await page.waitForTimeout(1000);
        
        const femViews = await page.locator('h3:has-text("FEM")').count();
        if (femViews > 0) {
            findings.observations.push('FEM Views section found');
            const screenshotPath5 = path.join(SCREENSHOT_DIR, '05_fem_views.png');
            await page.screenshot({ path: screenshotPath5, fullPage: true });
            findings.screenshots.push('05_fem_views.png');
        } else {
            findings.observations.push('FEM Views section not visible');
        }
        
        // 7. LOOK FOR RUN FEM ANALYSIS BUTTON
        console.log('\n7. Looking for Run FEM Analysis button...');
        
        const runButton = page.getByRole('button', { name: /Run FEM Analysis/i });
        if (await runButton.count() > 0) {
            findings.observations.push('Run FEM Analysis button found');
            
            await runButton.scrollIntoViewIfNeeded();
            await page.waitForTimeout(500);
            
            const isDisabled = await runButton.isDisabled();
            if (isDisabled) {
                findings.issues.push({ 
                    element: 'Run FEM Analysis button', 
                    issue: 'Button is disabled - unclear why', 
                    severity: 'high' 
                });
            } else {
                console.log('   Running FEM Analysis...');
                await runButton.click();
                await page.waitForTimeout(8000); // Wait for analysis
                
                const screenshotPath6 = path.join(SCREENSHOT_DIR, '06_after_fem_analysis.png');
                await page.screenshot({ path: screenshotPath6, fullPage: true });
                findings.screenshots.push('06_after_fem_analysis.png');
            }
        } else {
            findings.issues.push({ 
                element: 'Run FEM Analysis button', 
                issue: 'Button not found', 
                severity: 'critical' 
            });
        }
        
        // 8. CHECK FOR TABS (Plan View / Elevation View / 3D View)
        console.log('\n8. Checking for visualization tabs...');
        
        const planTab = await page.locator('[data-baseweb="tab"]:has-text("Plan View")').count();
        const elevationTab = await page.locator('[data-baseweb="tab"]:has-text("Elevation View")').count();
        const view3DTab = await page.locator('[data-baseweb="tab"]:has-text("3D View")').count();
        
        if (planTab > 0) {
            findings.observations.push('Plan View tab found');
            await page.locator('[data-baseweb="tab"]:has-text("Plan View")').click();
            await page.waitForTimeout(1500);
            const screenshotPath7 = path.join(SCREENSHOT_DIR, '07_plan_view.png');
            await page.screenshot({ path: screenshotPath7, fullPage: true });
            findings.screenshots.push('07_plan_view.png');
        }
        
        if (elevationTab > 0) {
            findings.observations.push('Elevation View tab found');
            await page.locator('[data-baseweb="tab"]:has-text("Elevation View")').click();
            await page.waitForTimeout(1500);
            const screenshotPath8 = path.join(SCREENSHOT_DIR, '08_elevation_view.png');
            await page.screenshot({ path: screenshotPath8, fullPage: true });
            findings.screenshots.push('08_elevation_view.png');
        }
        
        if (view3DTab > 0) {
            findings.observations.push('3D View tab found');
            await page.locator('[data-baseweb="tab"]:has-text("3D View")').click();
            await page.waitForTimeout(1500);
            const screenshotPath9 = path.join(SCREENSHOT_DIR, '09_3d_view.png');
            await page.screenshot({ path: screenshotPath9, fullPage: true });
            findings.screenshots.push('09_3d_view.png');
        }
        
        // 9. MOBILE VIEWPORT TEST
        console.log('\n9. Testing mobile viewport (375x812)...');
        await page.setViewportSize({ width: 375, height: 812 });
        await page.waitForTimeout(1500);
        const screenshotPath10 = path.join(SCREENSHOT_DIR, '10_mobile_view.png');
        await page.screenshot({ path: screenshotPath10, fullPage: true });
        findings.screenshots.push('10_mobile_view.png');
        
        // Check for mobile responsiveness issues
        const sidebarVisible = await page.locator('[data-testid="stSidebar"]').isVisible();
        if (sidebarVisible) {
            findings.issues.push({
                element: 'Sidebar',
                issue: 'Sidebar may be obstructing content on mobile',
                severity: 'medium'
            });
        }
        
        // 10. TABLET VIEWPORT TEST
        console.log('\n10. Testing tablet viewport (768x1024)...');
        await page.setViewportSize({ width: 768, height: 1024 });
        await page.waitForTimeout(1500);
        const screenshotPath11 = path.join(SCREENSHOT_DIR, '11_tablet_view.png');
        await page.screenshot({ path: screenshotPath11, fullPage: true });
        findings.screenshots.push('11_tablet_view.png');
        
        // Reset to desktop
        await page.setViewportSize({ width: 1920, height: 1080 });
        await page.waitForTimeout(1000);
        
        // 11. EDGE CASE TESTING
        console.log('\n11. Testing edge cases...');
        
        // Navigate back to inputs
        await page.goto(STREAMLIT_URL, { waitUntil: 'networkidle', timeout: 60000 });
        await page.waitForTimeout(2000);
        
        // Test max bays
        const baysXEdge = page.locator('input[aria-label="Bays in X"]').first();
        if (await baysXEdge.count() > 0) {
            await baysXEdge.scrollIntoViewIfNeeded();
            await baysXEdge.fill('10');
            await page.waitForTimeout(1500);
            findings.interactions.push('Set Bays in X to 10 (max)');
            
            const screenshotPath12 = path.join(SCREENSHOT_DIR, '12_edge_case_max_bays.png');
            await page.screenshot({ path: screenshotPath12, fullPage: true });
            findings.screenshots.push('12_edge_case_max_bays.png');
        }
        
        // Test extreme floors
        const floorsEdge = page.locator('input[aria-label="Floors"]').first();
        if (await floorsEdge.count() > 0) {
            await floorsEdge.scrollIntoViewIfNeeded();
            await floorsEdge.fill('50');
            await page.waitForTimeout(1500);
            findings.interactions.push('Set Floors to 50 (extreme)');
            
            const screenshotPath13 = path.join(SCREENSHOT_DIR, '13_edge_case_50_floors.png');
            await page.screenshot({ path: screenshotPath13, fullPage: true });
            findings.screenshots.push('13_edge_case_50_floors.png');
        }
        
        // 12. ACCESSIBILITY CHECKS
        console.log('\n12. Running accessibility checks...');
        
        // Check for color contrast issues
        const bodyBgColor = await page.evaluate(() => {
            return window.getComputedStyle(document.body).backgroundColor;
        });
        findings.observations.push(`Body background color: ${bodyBgColor}`);
        
        // Check for keyboard navigation
        await page.keyboard.press('Tab');
        await page.waitForTimeout(500);
        const focusedElement = await page.evaluate(() => {
            const el = document.activeElement;
            return el ? el.tagName + (el.getAttribute('aria-label') ? ` [${el.getAttribute('aria-label')}]` : '') : 'None';
        });
        findings.observations.push(`First focusable element: ${focusedElement}`);
        
        // 13. FINAL FULL PAGE SCREENSHOT
        console.log('\n13. Capturing final state...');
        await page.goto(STREAMLIT_URL, { waitUntil: 'networkidle', timeout: 60000 });
        await page.waitForTimeout(2000);
        const screenshotPath14 = path.join(SCREENSHOT_DIR, '14_final_state.png');
        await page.screenshot({ path: screenshotPath14, fullPage: true });
        findings.screenshots.push('14_final_state.png');
        
        console.log('\n=== AUDIT COMPLETE ===');
        console.log(`Screenshots saved: ${findings.screenshots.length}`);
        console.log(`Issues found: ${findings.issues.length}`);
        console.log(`Observations: ${findings.observations.length}`);
        
        // Write findings to JSON
        const fs = require('fs');
        const findingsPath = path.join(__dirname, 'audit_findings.json');
        fs.writeFileSync(findingsPath, JSON.stringify(findings, null, 2));
        console.log(`\nFindings saved to: ${findingsPath}`);
        
    } catch (error) {
        console.error('\n❌ AUDIT FAILED:', error.message);
        await page.screenshot({ 
            path: path.join(SCREENSHOT_DIR, 'error_state.png'), 
            fullPage: true 
        });
        findings.issues.push({
            element: 'Script execution',
            issue: error.message,
            severity: 'critical'
        });
    } finally {
        await browser.close();
    }
    
    return findings;
}

runAudit().catch(console.error);
