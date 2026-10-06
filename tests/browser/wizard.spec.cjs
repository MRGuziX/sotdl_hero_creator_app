const {test, expect} = require('@playwright/test');

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
    await page.getByRole('button', {name: 'Awansuj'}).click();
    await expect(page.locator('path-picker')).toBeVisible();
    await page.screenshot({path: test.info().outputPath('path-picker.png')});
    const path = page.locator('path-picker input[type=radio]').first();
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
    await page.getByRole('button', {name: 'Wznów zapisaną postać'}).click();
    await page.getByRole('button', {name: 'Wznów', exact: true}).click();
    await expect.poll(() => page.evaluate(() => window.creationStore.state?.state_id)).toBe(id);
});

test('random creation exports a versioned PDF and locks captured sources', async ({page}) => {
    await page.goto('/');
    await page.getByRole('button', {name: 'Tryb losowy'}).click();
    await page.locator('ancestry-picker .ancestry-item').filter({hasText: 'Człowiek'}).click();
    await page.getByRole('button', {name: 'Generuj', exact: true}).click();
    await expect(page.locator('#hero-frame')).toHaveAttribute('src', /\/pdf\/0/);
    const url = await page.locator('#hero-frame').getAttribute('src');
    expect((await page.request.get(url)).status()).toBe(200);
    if (test.info().project.name === 'phone') {
        await page.getByRole('button', {name: 'Zamknij podgląd'}).click();
    }
    await page.getByRole('button', {name: 'Wybierz suplementy'}).click();
    for (const input of await page.locator('supplement-selector input[type=checkbox]').all()) {
        await expect(input).toBeDisabled();
    }
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
