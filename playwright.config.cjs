const {defineConfig} = require('@playwright/test');
const os = require('node:os');
const path = require('node:path');

module.exports = defineConfig({
    testDir: './tests/browser',
    fullyParallel: false,
    workers: 1,
    use: {baseURL: 'http://127.0.0.1:5057', trace: 'retain-on-failure'},
    projects: [
        {name: 'desktop', use: {browserName: 'chromium', viewport: {width: 1440, height: 1000}}},
        {name: 'phone', use: {browserName: 'chromium', viewport: {width: 390, height: 844}, isMobile: true, hasTouch: true}}
    ],
    webServer: {
        command: '.venv/bin/python -m flask --app main run --host 127.0.0.1 --port 5057',
        url: 'http://127.0.0.1:5057',
        env: {APP_ENV: 'development', SECRET_KEY: 'browser-tests-only', DATABASE_URL: '',
              CREATION_DB_PATH: path.join(os.tmpdir(), 'sotdl-e2e-' + process.pid + '.sqlite3')},
        reuseExistingServer: false,
        stderr: 'ignore'
    }
});
