const { chromium } = require('playwright');
const path = require('path');

const STREAMLIT_URL = 'http://localhost:8501';
const SCREENSHOT_DIR = path.join(__dirname, '..', 'screenshots');

async function testForceDiagramParabolicCurves() {
    console.log('=== PLAYWRIGHT TEST: Force Diagram Parabolic Curves ===\n');

    const browser = await chromium.launch({ headless: false, slowMo: 50 });
    const context = await browser.newContext({
        viewport: { width: 1920, height: 1080 }
    });
    const page = await context.newPage();

    try {
        console.log('1. Navigating to Streamlit app...');
        await page.goto(STREAMLIT_URL, { waitUntil: 'networkidle', timeout: 60000 });
        await page.waitForTimeout(3000);

        console.log('\n2. Scrolling to FEM Analysis section...');
        const femHeader = page.locator('h3:has-text("FEM Analysis")');
        if (await femHeader.count() > 0) {
            await femHeader.first().scrollIntoViewIfNeeded();
            await page.waitForTimeout(500);
        }

        console.log('\n3. Running FEM Analysis...');
        const runButton = page.getByRole('button', { name: /Run FEM Analysis/i });
        if (await runButton.count() > 0) {
            await runButton.scrollIntoViewIfNeeded();
            await runButton.click();
            console.log('   Waiting for analysis...');
            await page.waitForTimeout(10000);
            console.log('   Analysis completed');
        }

        console.log('\n4. Selecting Mz (Major Moment) force type from radio buttons...');
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight * 0.6));
        await page.waitForTimeout(500);

        const sectionForcesLabel = page.locator('text=Section Forces');
        if (await sectionForcesLabel.count() > 0) {
            await sectionForcesLabel.first().scrollIntoViewIfNeeded();
            await page.waitForTimeout(300);
        }

        const mMajorRadio = page.locator('label:has-text("Mz (Major Moment)")');
        if (await mMajorRadio.count() > 0) {
            await mMajorRadio.scrollIntoViewIfNeeded();
            await mMajorRadio.click();
            await page.waitForTimeout(2000);
            console.log('   Selected Mz (Major Moment)');
        } else {
            console.log('   Mz (Major Moment) radio not found, trying alternatives...');

            const anyForceRadio = page.locator('label:has-text("My (Minor Moment)"), label:has-text("N (Axial)"), label:has-text("Vy (Major Shear)")');
            if (await anyForceRadio.count() > 0) {
                await anyForceRadio.first().scrollIntoViewIfNeeded();
                await anyForceRadio.first().click();
                await page.waitForTimeout(2000);
                console.log('   Selected alternative force type');
            }
        }

        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'force_01_selected_force.png'), fullPage: true });

        console.log('\n5. Checking Plan View tab...');
        const planViewTab = page.locator('[data-baseweb="tab"]:has-text("Plan View")');
        if (await planViewTab.count() > 0) {
            await planViewTab.first().click();
            await page.waitForTimeout(2000);
            console.log('   Switched to Plan View');
        }

        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'force_02_plan_view_with_forces.png'), fullPage: true });

        const planChart = page.locator('.js-plotly-plot').first();
        if (await planChart.count() > 0) {
            await planChart.screenshot({ path: path.join(SCREENSHOT_DIR, 'force_03_plan_chart_detail.png') });
            console.log('   Plan View chart captured');
        }

        console.log('\n6. Checking Elevation View tab...');
        const elevationViewTab = page.locator('[data-baseweb="tab"]:has-text("Elevation View")');
        if (await elevationViewTab.count() > 0) {
            await elevationViewTab.first().click();
            await page.waitForTimeout(2000);
            console.log('   Switched to Elevation View');
        }

        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'force_04_elevation_view_with_forces.png'), fullPage: true });

        const elevChart = page.locator('.js-plotly-plot').first();
        if (await elevChart.count() > 0) {
            await elevChart.screenshot({ path: path.join(SCREENSHOT_DIR, 'force_05_elevation_chart_detail.png') });
            console.log('   Elevation View chart captured');
        }

        console.log('\n7. Inspecting SVG for force diagram traces...');
        const svgInfo = await page.evaluate(() => {
            const plotly = document.querySelector('.js-plotly-plot');
            if (!plotly) return { error: 'No plotly chart found' };

            const svg = plotly.querySelector('svg.main-svg');
            if (!svg) return { error: 'No SVG found' };

            const allPaths = svg.querySelectorAll('path');
            let redPaths = [];

            for (const p of allPaths) {
                const style = p.getAttribute('style') || '';
                const stroke = p.getAttribute('stroke') || '';

                if (style.includes('rgb(255,') || style.includes('rgb(255, ') ||
                    stroke.includes('red') || stroke === '#ff0000' || stroke === 'rgb(255, 0, 0)') {
                    const d = p.getAttribute('d') || '';
                    if (d.length > 20) {
                        redPaths.push({
                            dLength: d.length,
                            points: (d.match(/[ML]/g) || []).length
                        });
                    }
                }
            }

            return {
                totalPaths: allPaths.length,
                redPaths: redPaths.length,
                pathDetails: redPaths.slice(0, 5)
            };
        });

        console.log('   SVG Analysis:', JSON.stringify(svgInfo, null, 2));

        console.log('\n8. Checking legend for force type...');
        const legendInfo = await page.evaluate(() => {
            const legend = document.querySelector('.legend');
            if (!legend) return { found: false };

            const items = legend.querySelectorAll('.legendtoggle');
            const texts = [];
            items.forEach(item => {
                const text = item.textContent || '';
                if (text.includes('M') || text.includes('kNm') || text.includes('Force')) {
                    texts.push(text.trim());
                }
            });
            return { found: true, items: texts };
        });

        console.log('   Legend:', JSON.stringify(legendInfo));

        console.log('\n=== TEST COMPLETE ===');
        console.log('Screenshots saved to:', SCREENSHOT_DIR);
        console.log('\nManually verify:');
        console.log('  - force_03_plan_chart_detail.png: Look for red curved lines on beams');
        console.log('  - force_05_elevation_chart_detail.png: Look for red curved lines on beams');

        await page.waitForTimeout(3000);

    } catch (error) {
        console.error('\nTest error:', error.message);
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'force_error.png'), fullPage: true });
    } finally {
        await browser.close();
    }
}

testForceDiagramParabolicCurves().catch(console.error);
