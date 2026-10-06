const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');

function setup(handler, remembered) {
    const window = new EventTarget();
    const saved = new Map(remembered ? [['sotdl.activeCreation', remembered]] : []);
    const requests = [];
    class CustomEvent extends Event {
        constructor(type, options = {}) { super(type); this.detail = options.detail; }
    }
    const context = vm.createContext({window, EventTarget, CustomEvent, AbortController, DOMException,
        sessionStorage: {setItem: (k, v) => saved.set(k, v), getItem: k => saved.get(k), removeItem: k => saved.delete(k)},
        fetch: async (url, options) => { requests.push({url, options}); return handler(url, options); }
    });
    vm.runInContext(fs.readFileSync('static/js/creation_store.js', 'utf8'), context);
    const store = window.creationStore;
    const errors = [];
    store.addEventListener('error', e => errors.push(e.detail));
    return {store, window, saved, requests, errors};
}

const state = (version = 0) => ({state_id: 'owned', state_version: version, current_level: 0,
    choice_cursor: 0, can_finalize: false, enabled_sources: ['PG', 'SWD']});
const response = (data, status = 200) => ({ok: status < 400, status, json: async () => data});

test('refresh restores this tab and captured source settings', async () => {
    const env = setup(() => response({state: state(2)}), 'owned');
    await env.store.restore();
    assert.equal(env.store.state.state_version, 2);
    assert.equal(env.requests[0].url, '/api/creations/owned');
    assert.equal(env.window.enabledSupplements.has('SWD'), true);
    env.window.toggleSupplement('SWD');
    assert.equal(env.window.enabledSupplements.has('SWD'), true);
});

test('overlapping mutations are ignored', async () => {
    let resolve;
    const env = setup(() => new Promise(done => { resolve = done; }));
    env.store.setContract({state: state()});
    const first = env.store.advance();
    assert.equal(env.store.busy, true);
    assert.equal(await env.store.advance(), null);
    resolve(response({state: state(1)}));
    await first;
    assert.equal(env.requests.length, 1);
    assert.equal(env.store.busy, false);
});

test('reset suppresses late creation responses', async () => {
    let resolve;
    const env = setup(() => new Promise(done => { resolve = done; }));
    const pending = env.store.start('manual', 'human');
    env.store.reset();
    resolve(response({state: state()}));
    assert.equal(await pending, null);
    assert.equal(env.store.state, null);
    assert.equal(env.saved.size, 0);
    assert.equal(env.errors.length, 0);
});

test('stale versions reload authoritative state without replaying the mutation', async () => {
    const env = setup(url => url.endsWith('/advance')
        ? response({error: 'stale'}, 409) : response({state: state(7)}));
    env.store.setContract({state: state()});
    assert.equal(await env.store.advance(), null);
    assert.equal(env.store.state.state_version, 7);
    assert.equal(env.requests.length, 2);
    assert.match(env.errors[0], /odświeżona/);
});

test('non-JSON server failure is visible and releases busy state', async () => {
    const env = setup(() => ({ok: false, status: 502, json: async () => { throw new Error('HTML'); }}));
    assert.equal(await env.store.start('manual', 'human'), null);
    assert.match(env.errors[0], /nieprawidłową/);
    assert.equal(env.store.busy, false);
});

test('expired saved state clears the tab ID and explains recovery', async () => {
    const env = setup(() => response({error: 'expired'}, 410), 'owned');
    await env.store.restore();
    assert.equal(env.saved.size, 0);
    assert.equal(env.store.state, null);
    assert.match(env.errors[0], /Rozpocznij nową/);
});

test('concurrent PDF clicks issue one versioned export request', async () => {
    let resolve;
    const env = setup(() => new Promise(done => { resolve = done; }));
    env.store.setContract({state: state(3)});
    const first = env.store.finalize();
    assert.equal(await env.store.finalize(), null);
    resolve(response({pdf_url: '/api/creations/owned/pdf/3'}));
    await first;
    assert.equal(env.requests.length, 1);
    assert.equal(JSON.parse(env.requests[0].options.body).state_version, 3);
});

test('choice undo is available after the completed cursor resets to zero', async () => {
    const env = setup(() => response({state: state(4)}));
    env.store.setContract({state: state(3)});
    await env.store.rewindChoice();
    assert.equal(env.requests[0].url, '/api/creations/owned/rewind_choice');
});
