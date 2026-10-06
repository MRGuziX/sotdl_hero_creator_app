const {test, expect} = require('@playwright/test');
const fs = require('node:fs/promises');

async function startManual(page) {
    await page.getByRole('button', {name: 'Tryb ręczny'}).click();
    await page.locator('ancestry-picker .ancestry-item').filter({hasText: 'Człowiek'}).click();
    await page.getByRole('button', {name: 'Dalej', exact: true}).click();
    await expect(page.locator('wizard-shell')).toHaveAttribute('aria-busy', 'false');
}

async function resolveLevel(page) {
    for (let i = 0; i < 30; i++) {
        const choices = await page.evaluate(() => window.creationStore.state.pending_choices[0]);
        if (!choices) return;
        const attributeButtons = page.locator('step-shell .stepper-plus');
        if (await attributeButtons.count()) {
            // The existing attribute UI has count limits; choose distinct available attributes.
            const enabled = page.locator('step-shell .stepper-plus:not(:disabled)');
            await enabled.first().click();
            while (await page.getByRole('button', {name: 'Dalej', exact: true}).isDisabled()) {
                await enabled.first().click();
            }
        } else {
            const radio = page.locator('step-shell input[type=radio]').first();
            await radio.focus();
            await page.keyboard.press('Space');
            await expect(radio).toBeChecked();
        }
        await page.getByRole('button', {name: 'Dalej', exact: true}).click();
        await expect(page.locator('wizard-shell')).toHaveAttribute('aria-busy', 'false');
    }
    throw new Error('Choice resolution did not terminate');
}

test('manual creation, reload, keyboard path selection, undo and Home', async ({page}) => {
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto('/');
    await startManual(page);
    const id = await page.evaluate(() => window.creationStore.state.state_id);
    await page.reload();
    await expect.poll(() => page.evaluate(() => window.creationStore.state?.state_id)).toBe(id);
    await resolveLevel(page);
    if (test.info().project.name === 'phone') {
        await expect(page.locator('#pdf-panel')).toHaveClass(/drawer-open/);
        await page.getByRole('button', {name: 'Zamknij podgląd'}).click();
    }
    await page.getByRole('button', {name: 'Awansuj'}).click();
    await expect(page.locator('path-picker')).toBeVisible();
    const tips = page.locator('path-picker .ancestry-tooltip-trigger');
    for (let index = 0; index < await tips.count(); index++) {
        await tips.nth(index).click();
        await expect(page.locator('.wizard-popover.visible')).toContainText('Opis roboczy:');
        const description = await page.evaluate(i => window.PATH_CATALOG.novice[i].description, index);
        await expect(page.locator('.wizard-popover.visible')).toHaveText(description);
        // Reading a description must not select its path.
        await expect(page.locator('path-picker input[type=radio]:checked')).toHaveCount(0);
        if (index === 0) await page.screenshot({path: test.info().outputPath('path-description.png')});
        await page.keyboard.press('Escape');
        await expect(page.locator('.wizard-popover')).not.toBeVisible();
    }
    const cards = page.locator('path-picker .path-option');
    const cardSize = await cards.first().boundingBox();
    // Clicking card padding, not just its name, must select the option.
    await cards.first().click({position: {x: 10, y: cardSize.height - 8}});
    await expect(cards.first()).toHaveClass(/active/);
    await expect(page.getByRole('button', {name: 'Dalej', exact: true})).toBeEnabled();
    await cards.nth(1).click({position: {x: 10, y: cardSize.height - 8}});
    await expect(cards.first()).not.toHaveClass(/active/);
    await expect(cards.nth(1)).toHaveClass(/active/);
    await expect(page.locator('path-picker input[type=radio]:checked')).toHaveCount(1);
    await page.screenshot({path: test.info().outputPath('path-picker.png')});
    const path = page.locator('path-picker input[type=radio]').first();
    expect(await path.evaluate(node => getComputedStyle(node).opacity)).toBe('0');
    await path.focus();
    await page.keyboard.press('Space');
    await expect(page.locator('path-picker input[type=radio]:checked')).toBeFocused();
    await page.getByRole('button', {name: 'Dalej', exact: true}).click();
    await expect(page.locator('wizard-shell')).toHaveAttribute('aria-busy', 'false');
    await page.evaluate(() => window.creationStore.rewind(0));
    await expect.poll(() => page.evaluate(() => window.creationStore.state.current_level)).toBe(0);
    await page.getByRole('button', {name: 'Strona główna'}).click();
    await expect(page.locator('main-menu')).toBeVisible();
    await expect(page.locator('#hero-frame')).toHaveAttribute('src', 'about:blank');
    await expect(page.locator('#pdf-panel')).not.toHaveClass(/visible|drawer-open/);
    expect(errors).toEqual([]);
    expect(await page.evaluate(() => sessionStorage.getItem('sotdl.browserDraft.v1'))).toBeNull();
    await expect(page.getByRole('button', {name: 'Wznów zapisaną postać'})).toHaveCount(0);
    await expect(page.locator('#download-sheet')).toBeHidden();
});

test('random hero previews and downloads the same PDF without a database', async ({page}) => {
    let exports = 0;
    page.on('request', request => { if (request.url().endsWith('/finalize')) exports += 1; });
    await page.goto('/');
    await page.getByRole('button', {name: 'Tryb losowy'}).click();
    await page.locator('ancestry-picker .ancestry-item').filter({hasText: 'Człowiek'}).click();
    await page.getByRole('button', {name: 'Generuj', exact: true}).click();
    await expect(page.locator('#hero-frame')).toHaveAttribute('src', /^blob:/);
    await expect(page.locator('#download-sheet')).toBeVisible();
    const preview = await page.evaluate(async () => {
        const response = await fetch(window.creationStore.pdfUrl);
        return Array.from(new Uint8Array(await response.arrayBuffer()));
    });
    expect(Buffer.from(preview).subarray(0, 5).toString()).toBe('%PDF-');
    const downloaded = page.waitForEvent('download');
    await page.getByRole('link', {name: 'Pobierz PDF', exact: true}).click();
    const download = await downloaded;
    expect(download.suggestedFilename()).toBe('Karta_Postaci_SotDL.pdf');
    expect(await fs.readFile(await download.path())).toEqual(Buffer.from(preview));
    await page.screenshot({path: test.info().outputPath('pdf-preview.png')});
    await page.evaluate(() => window.creationStore.finalize(true));
    expect(exports).toBe(1);
    expect(await page.context().cookies()).toEqual([]);
    if (test.info().project.name === 'phone') {
        await page.getByRole('button', {name: 'Zamknij podgląd'}).click();
    }
    await page.getByRole('button', {name: 'Wybierz suplementy'}).click();
    for (const input of await page.locator('supplement-selector input[type=checkbox]').all()) {
        await expect(input).toBeDisabled();
    }
    await page.getByRole('button', {name: 'Strona główna'}).click();
    await expect(page.locator('#hero-frame')).toHaveAttribute('src', 'about:blank');
    await expect(page.locator('#download-sheet')).toBeHidden();
    expect(await page.evaluate(() => window.creationStore.pdfUrl)).toBeNull();
});

test('failed start is visible and retry works without unhandled errors', async ({page}) => {
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('**/api/creations', route => route.fulfill({status: 502, contentType: 'text/html', body: 'Bad gateway'}));
    await page.goto('/');
    await page.getByRole('button', {name: 'Tryb ręczny'}).click();
    await page.locator('ancestry-picker .ancestry-item').filter({hasText: 'Człowiek'}).click();
    await page.getByRole('button', {name: 'Dalej', exact: true}).click();
    await expect(page.locator('#event-toast')).toContainText('nieprawidłową');
    await page.unroute('**/api/creations');
    await page.getByRole('button', {name: 'Dalej', exact: true}).click();
    await expect(page.locator('step-shell')).toBeVisible();
    expect(errors).toEqual([]);
});

test('two tabs retain independent active creations', async ({page, context}) => {
    await page.goto('/');
    await startManual(page);
    const firstId = await page.evaluate(() => window.creationStore.state.state_id);
    const second = await context.newPage();
    await second.goto('/');
    await expect(second.locator('main-menu')).toBeVisible();
    await startManual(second);
    const secondId = await second.evaluate(() => window.creationStore.state.state_id);
    expect(secondId).not.toBe(firstId);
    await page.reload();
    await second.reload();
    await expect.poll(() => page.evaluate(() => window.creationStore.state?.state_id)).toBe(firstId);
    await expect.poll(() => second.evaluate(() => window.creationStore.state?.state_id)).toBe(secondId);
});
