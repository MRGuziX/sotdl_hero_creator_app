const {defineConfig} = require('@playwright/test');

module.exports = defineConfig({
    testDir: './tests/browser',
    fullyParallel: false,
    workers: 1,
    // Full Chromium renders embedded PDFs; the default headless shell does not.
    use: {baseURL: 'http://127.0.0.1:5057', trace: 'retain-on-failure', channel: 'chromium'},
    projects: [
        {name: 'desktop', use: {browserName: 'chromium', viewport: {width: 1440, height: 1000}}},
        {name: 'phone', use: {browserName: 'chromium', viewport: {width: 390, height: 844}, isMobile: true, hasTouch: true}}
    ],
    webServer: {
        command: '.venv/bin/python -m flask --app main run --host 127.0.0.1 --port 5057',
        url: 'http://127.0.0.1:5057',
        env: {SECRET_KEY: 'browser-tests-only', VERCEL: '1'},
        reuseExistingServer: false,
        stderr: 'ignore'
    }
});
