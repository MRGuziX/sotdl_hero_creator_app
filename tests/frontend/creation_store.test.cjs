const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');

const DRAFT_KEY = 'sotdl.browserDraft.v1';
function setup(handler, remembered) {
    const window = new EventTarget();
    const saved = new Map(remembered ? [[DRAFT_KEY, JSON.stringify(remembered)]] : []);
    const requests = [];
    const urls = [], revoked = [];
    class CustomEvent extends Event {
        constructor(type, options = {}) { super(type); this.detail = options.detail; }
    }
    const storage = {setItem: (k, v) => saved.set(k, v), getItem: k => saved.get(k), removeItem: k => saved.delete(k)};
    const context = vm.createContext({window, EventTarget, CustomEvent, AbortController, DOMException,
        sessionStorage: storage,
        URL: {createObjectURL: blob => { urls.push(blob); return 'blob:test-' + urls.length; },
              revokeObjectURL: url => revoked.push(url)},
        fetch: async (url, options) => { requests.push({url, options}); return handler(url, options); }
    });
    vm.runInContext(fs.readFileSync('static/js/creation_store.js', 'utf8'), context);
    const store = window.creationStore;
    const errors = [];
    store.addEventListener('error', e => errors.push(e.detail));
    return {store, window, saved, requests, errors, urls, revoked, storage};
}

const state = (version = 0) => ({state_id: 'carried', state_version: version, current_level: 0,
    choice_cursor: 0, can_finalize: false, enabled_sources: ['PG', 'SWD']});
const contract = (version = 0) => ({state: state(version), state_token: 'capsule-' + version});
const draft = {creation_id: 'carried', state_token: 'capsule-2'};
const response = (data, status = 200) => ({ok: status < 400, status, json: async () => data});
const pdf = (content = '%PDF-1.7 test', type = 'application/pdf') => ({ok: true, status: 200,
    headers: {get: () => type}, blob: async () => new Blob([content], {type})});

test('refresh carries the tab token to Python and restores captured sources', async () => {
    const env = setup(() => response(contract(2)), draft);
    await env.store.restore();
    assert.equal(env.store.state.state_version, 2);
    assert.equal(env.requests[0].url, '/api/creations/carried/resume');
    assert.equal(JSON.parse(env.requests[0].options.body).state_token, draft.state_token);
    assert.equal(env.requests[0].options.credentials, 'omit');
    assert.equal(env.window.enabledSupplements.has('SWD'), true);
    env.window.toggleSupplement('SWD');
    assert.equal(env.window.enabledSupplements.has('SWD'), true);
});

test('overlapping mutations are ignored and commands carry the signed state', async () => {
    let resolve;
    const env = setup(() => new Promise(done => { resolve = done; }));
    env.store.setContract(contract());
    const first = env.store.advance();
    assert.equal(env.store.busy, true);
    assert.equal(await env.store.advance(), null);
    resolve(response(contract(1)));
    await first;
    assert.equal(env.requests.length, 1);
    assert.equal(JSON.parse(env.requests[0].options.body).state_token, 'capsule-0');
    assert.equal(env.store.busy, false);
});

test('reset suppresses late creation responses', async () => {
    let resolve;
    const env = setup(() => new Promise(done => { resolve = done; }));
    const pending = env.store.start('manual', 'human');
    env.store.reset();
    resolve(response(contract()));
    assert.equal(await pending, null);
    assert.equal(env.store.state, null);
    assert.equal(env.saved.size, 0);
    assert.equal(env.errors.length, 0);
});

test('rejected commands retain the browser draft without replay or server reload', async () => {
    const env = setup(() => response({error: 'stale'}, 409));
    env.store.setContract(contract());
    const before = env.saved.get(DRAFT_KEY);
    assert.equal(await env.store.advance(), null);
    assert.equal(env.store.state.state_version, 0);
    assert.equal(env.saved.get(DRAFT_KEY), before);
    assert.equal(env.requests.length, 1);
    assert.match(env.errors[0], /bieżącego etapu/);
});

test('non-JSON server failure is visible and releases busy state', async () => {
    const env = setup(() => ({ok: false, status: 502, json: async () => { throw new Error('HTML'); }}));
    assert.equal(await env.store.start('manual', 'human'), null);
    assert.match(env.errors[0], /nieprawidłową/);
    assert.equal(env.store.busy, false);
});

test('invalid signed draft clears tab storage and explains recovery', async () => {
    const env = setup(() => response({error: 'incompatible'}, 410), draft);
    await env.store.restore();
    assert.equal(env.saved.size, 0);
    assert.equal(env.store.state, null);
    assert.match(env.errors[0], /Rozpocznij nową/);
});

test('concurrent PDF clicks issue one export and download reuses preview bytes', async () => {
    let resolve;
    const env = setup(() => new Promise(done => { resolve = done; }));
    const completed = [], finalized = [];
    env.store.addEventListener('completed', e => completed.push(e.detail.downloadUrl));
    env.store.addEventListener('finalized', e => finalized.push(e.detail.downloadUrl));
    env.store.setContract(contract(3));
    const first = env.store.finalize();
    assert.equal(await env.store.finalize(), null);
    resolve(pdf());
    await first;
    await env.store.finalize(true);
    assert.equal(env.requests.length, 1);
    assert.equal(JSON.parse(env.requests[0].options.body).state_version, 3);
    assert.equal(JSON.parse(env.requests[0].options.body).state_token, 'capsule-3');
    assert.deepEqual(completed, ['blob:test-1', 'blob:test-1']);
    assert.deepEqual(finalized, ['blob:test-1']);
    assert.equal(await env.urls[0].text(), '%PDF-1.7 test');
});

test('choice undo is available after the completed cursor resets to zero', async () => {
    const env = setup(() => response(contract(4)));
    env.store.setContract(contract(3));
    await env.store.rewindChoice();
    assert.equal(env.requests[0].url, '/api/creations/carried/rewind_choice');
});

test('cancelling a path pick carries state/version without opening the PDF drawer', async () => {
    const env = setup(() => response({state: {...state(4), can_finalize: true}, state_token: 'capsule-4'}));
    env.store.setContract(contract(3));
    await env.store.cancelAdvance();
    assert.equal(env.requests.length, 1);
    assert.equal(env.requests[0].url, '/api/creations/carried/cancel_advance');
    assert.deepEqual(JSON.parse(env.requests[0].options.body), {state_version: 3, state_token: 'capsule-3'});
    assert.equal(env.store.state.state_version, 4);
    assert.equal(env.urls.length, 0);
    assert.equal(env.store.busy, false);
});

test('reset revokes the PDF object URL and removes the token', async () => {
    const env = setup(() => pdf());
    env.store.setContract(contract());
    await env.store.finalize();
    env.store.reset();
    assert.deepEqual(env.revoked, ['blob:test-1']);
    assert.equal(env.store.pdfUrl, null);
    assert.equal(env.store.stateToken, null);
    assert.equal(env.saved.size, 0);
});

test('mutations invalidate old PDF URLs even when the command fails', async () => {
    const env = setup(url => url.endsWith('/finalize') ? pdf() : response({error: 'Rejected'}, 400));
    env.store.setContract(contract());
    await env.store.finalize();
    await env.store.advance();
    assert.deepEqual(env.revoked, ['blob:test-1']);
    assert.equal(env.store.pdfUrl, null);
    assert.equal(env.store.state.state_version, 0);
});

test('reset during PDF transfer cannot publish a stale Blob URL', async () => {
    let resolve;
    const env = setup(() => ({...pdf(), blob: () => new Promise(done => { resolve = done; })}));
    env.store.setContract(contract());
    const pending = env.store.finalize();
    await new Promise(done => setImmediate(done));
    env.store.reset();
    resolve(new Blob(['%PDF-1.7 test']));
    await pending;
    assert.equal(env.urls.length, 0);
    assert.equal(env.errors.length, 0);
});

test('non-PDF and malformed PDF success responses are rejected', async () => {
    for (const result of [pdf('<html>', 'text/html'), pdf('broken'), pdf('%PDF-1.7', 'application/pdf-fake')]) {
        const env = setup(() => result);
        env.store.setContract(contract());
        assert.equal(await env.store.finalize(), null);
        assert.equal(env.urls.length, 0);
        assert.equal(env.errors.length, 1);
        assert.equal(env.store.busy, false);
    }
});

test('quota failures remove obsolete drafts while keeping the live character usable', async () => {
    const env = setup(() => response(contract()), draft);
    env.storage.setItem = () => { throw new Error('Quota exceeded'); };
    await env.store.start('manual', 'human');
    assert.equal(env.saved.size, 0);
    assert.equal(env.store.state.state_id, 'carried');
    assert.match(env.errors[0], /Nie odświeżaj/);
});

test('a response without a signed capsule cannot replace the active draft', async () => {
    const env = setup(() => response({state: state(9)}));
    env.store.setContract(contract());
    await env.store.advance();
    assert.equal(env.store.state.state_version, 0);
    assert.equal(env.store.stateToken, 'capsule-0');
    assert.match(env.errors[0], /nieprawidłowy stan/);
});

test('oversized command responses retain the previous browser token and draft', async () => {
    const env = setup(() => response({error: 'Creation is too large'}, 413));
    env.store.setContract(contract());
    const before = env.saved.get(DRAFT_KEY);
    await env.store.advance();
    assert.equal(env.store.stateToken, 'capsule-0');
    assert.equal(env.saved.get(DRAFT_KEY), before);
    assert.equal(env.requests.length, 1);
    assert.equal(env.errors[0], 'Creation is too large');
});
