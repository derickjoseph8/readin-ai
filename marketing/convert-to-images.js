const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

async function convertHtmlToImage(htmlPath, outputPath, width, height) {
    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const page = await browser.newPage();

    // Set viewport to match the HTML dimensions
    await page.setViewport({ width, height, deviceScaleFactor: 2 });

    // Load the HTML file
    const htmlContent = fs.readFileSync(htmlPath, 'utf8');
    await page.setContent(htmlContent, { waitUntil: 'networkidle0' });

    // Take screenshot
    await page.screenshot({
        path: outputPath,
        type: 'png',
        fullPage: false,
        clip: { x: 0, y: 0, width, height }
    });

    await browser.close();
    console.log(`Created: ${outputPath}`);
}

async function main() {
    const instagramDir = path.join(__dirname, 'instagram');
    const logosDir = path.join(__dirname, 'logos');
    const outputDir = path.join(__dirname, 'images');

    // Create output directory
    if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
    }

    // Define dimensions for each file type
    const fileDimensions = {
        // Square posts (1080x1080)
        '01-hero-announcement.html': { width: 1080, height: 1080 },
        '02-pricing-africa.html': { width: 1080, height: 1080 },
        '03-features-grid.html': { width: 1080, height: 1080 },
        '05-use-cases.html': { width: 1080, height: 1080 },
        '06-mpesa-kenya.html': { width: 1080, height: 1080 },
        '07-download-cta.html': { width: 1080, height: 1080 },
        '11-job-interview-prep.html': { width: 1080, height: 1080 },
        '14-interview-remote.html': { width: 1080, height: 1080 },
        '15-interview-before-after.html': { width: 1080, height: 1080 },

        // Portrait posts (1080x1350)
        '04-problem-solution.html': { width: 1080, height: 1350 },
        '12-interview-anxiety.html': { width: 1080, height: 1350 },

        // Stories (1080x1920)
        '08-story-intro.html': { width: 1080, height: 1920 },
        '09-story-testimonial.html': { width: 1080, height: 1920 },
        '10-story-pricing.html': { width: 1080, height: 1920 },
        '13-interview-story.html': { width: 1080, height: 1920 },
    };

    // Logo dimensions
    const logoDimensions = {
        'readin-full-logo.html': { width: 800, height: 300 },
        'readin-full-logo-dark.html': { width: 800, height: 300 },
    };

    console.log('Converting Instagram posts...\n');

    // Convert Instagram HTML files
    for (const [filename, dims] of Object.entries(fileDimensions)) {
        const htmlPath = path.join(instagramDir, filename);
        if (fs.existsSync(htmlPath)) {
            const outputName = filename.replace('.html', '.png');
            const outputPath = path.join(outputDir, outputName);
            try {
                await convertHtmlToImage(htmlPath, outputPath, dims.width, dims.height);
            } catch (error) {
                console.error(`Error converting ${filename}:`, error.message);
            }
        }
    }

    console.log('\nConverting logos...\n');

    // Convert logo HTML files
    for (const [filename, dims] of Object.entries(logoDimensions)) {
        const htmlPath = path.join(logosDir, filename);
        if (fs.existsSync(htmlPath)) {
            const outputName = filename.replace('.html', '.png');
            const outputPath = path.join(outputDir, outputName);
            try {
                await convertHtmlToImage(htmlPath, outputPath, dims.width, dims.height);
            } catch (error) {
                console.error(`Error converting ${filename}:`, error.message);
            }
        }
    }

    console.log('\nDone! Images saved to:', outputDir);
}

main().catch(console.error);
