/* Server-authoritative state; each tab resumes its own active creation. */
(function () {
    const ACTIVE_KEY = "sotdl.activeCreation";
    window.enabledSupplements = new Set(["PG"]);

    window.toggleSupplement = function (source) {
        if (source === "PG" || window.creationStore.state || window.creationStore.busy) return;
        if (window.enabledSupplements.has(source)) window.enabledSupplements.delete(source);
        else window.enabledSupplements.add(source);
        window.dispatchEvent(new CustomEvent("supplements-change"));
    };

    class CreationStore extends EventTarget {
        constructor() {
            super();
            this.state = null;
            this.step = null;
            this._token = null;
        }

        get busy() { return this._token !== null; }
        get activeLevel() { return this.state ? this.state.current_level : 0; }

        _remember(id) {
            try {
                if (id) sessionStorage.setItem(ACTIVE_KEY, id);
                else sessionStorage.removeItem(ACTIVE_KEY);
            } catch (_) { /* Storage-disabled browsers still support the current session. */ }
        }

        setContract(contract) {
            this.state = contract.state !== undefined ? contract.state : contract;
            this.step = contract.step || null;
            this._remember(this.state?.state_id);
            if (this.state?.enabled_sources) {
                window.enabledSupplements = new Set(this.state.enabled_sources);
            }
            this.dispatchEvent(new CustomEvent("statechange", {detail: this.state}));
            window.dispatchEvent(new CustomEvent("supplements-change"));
        }

        async _request(url, body, token) {
            const response = await fetch(url, {
                method: body === undefined ? "GET" : "POST",
                headers: {"Content-Type": "application/json"},
                ...(body === undefined ? {} : {body: JSON.stringify(body)}),
                signal: token.controller.signal
            });
            if (this._token !== token) throw new DOMException("Cancelled", "AbortError");
            let result;
            try { result = await response.json(); }
            catch (_) { throw new Error("Serwer zwrócił nieprawidłową odpowiedź. Spróbuj ponownie."); }
            if (this._token !== token) throw new DOMException("Cancelled", "AbortError");
            if (!response.ok) {
                if (response.status === 409 && this.state) {
                    const current = await this._request("/api/creations/" + this.state.state_id, undefined, token);
                    this.setContract(current);
                    throw new Error("Postać została odświeżona. Sprawdź wybory i spróbuj ponownie.");
                }
                if ([404, 410].includes(response.status)) {
                    token.reportError = true;
                    this.reset();
                    throw new Error("Zapis wygasł lub jest niezgodny. Rozpocznij nową postać.");
                }
                throw new Error(result.error || "Nie udało się wykonać operacji.");
            }
            return result;
        }

        async _run(operation, preview = false) {
            if (this.busy) return null;
            const token = {controller: new AbortController()};
            this._token = token;
            this.dispatchEvent(new CustomEvent("busychange", {detail: true}));
            try {
                const result = await operation(token);
                if (preview && this.state?.can_finalize && this._token === token) await this._export(token);
                return result;
            } catch (error) {
                if (error.name !== "AbortError" && (this._token === token || token.reportError)) {
                    this.dispatchEvent(new CustomEvent("error", {detail: error.message}));
                }
                return null; // UI event handlers never leak rejected promises.
            } finally {
                if (this._token === token) {
                    this._token = null;
                    this.dispatchEvent(new CustomEvent("busychange", {detail: false}));
                }
            }
        }

        start(mode, ancestry, options = {}) {
            return this._run(async token => {
                const body = {mode, ancestry, enabled_sources: Array.from(window.enabledSupplements)};
                if (mode === "random") {
                    body.target_level = options.targetLevel ?? 0;
                    body.paths = options.paths || {novice: null, expert: [], master: null};
                }
                const result = await this._request("/api/creations", body, token);
                this.setContract(result);
                return result;
            }, true);
        }

        resume(id) {
            return this._run(async token => {
                const result = await this._request("/api/creations/" + encodeURIComponent(id), undefined, token);
                this.setContract(result);
                return result;
            }, true);
        }

        restore() {
            try {
                const id = sessionStorage.getItem(ACTIVE_KEY);
                if (id) return this.resume(id);
            } catch (_) { /* No tab storage. */ }
            return Promise.resolve(null);
        }

        listCreations() {
            return this._run(token => this._request("/api/creations", undefined, token));
        }

        _mutate(suffix, body = {}, preview = true) {
            return this._run(async token => {
                if (!this.state) throw new Error("Brak aktywnej postaci.");
                window.hidePdfPanel?.();
                const result = await this._request("/api/creations/" + this.state.state_id + "/" + suffix,
                    {...body, state_version: this.state.state_version}, token);
                this.setContract(result);
                return result;
            }, preview);
        }

        advance() { return this._mutate("advance"); }
        pickPath(tier, pathId) { return this._mutate("paths/" + tier, {path_id: pathId}); }
        applyChoices(selections) {
            return this._mutate("steps/" + this.activeLevel + "/choices", {
                selections, choice_cursor: this.state?.choice_cursor
            });
        }
        rewind(targetLevel) { return this._mutate("rewind", {target_level: targetLevel}); }
        rewindChoice() { return this._mutate("rewind_choice"); }
        setEquipment(selections) { return this._mutate("equipment", selections); }

        async _export(token, manual = false) {
            if (!this.state) throw new Error("Brak aktywnej postaci.");
            const result = await this._request("/api/creations/" + this.state.state_id + "/finalize",
                {state_version: this.state.state_version}, token);
            this.dispatchEvent(new CustomEvent("completed", {detail: {downloadUrl: result.pdf_url}}));
            if (manual) this.dispatchEvent(new CustomEvent("finalized", {detail: result}));
            return result;
        }

        finalize(manual = false) { return this._run(token => this._export(token, manual)); }

        reset() {
            this._token?.controller.abort();
            this._token = null;
            this.state = null;
            this.step = null;
            this._remember(null);
            this.dispatchEvent(new CustomEvent("reset"));
            this.dispatchEvent(new CustomEvent("statechange", {detail: null}));
            this.dispatchEvent(new CustomEvent("busychange", {detail: false}));
            window.dispatchEvent(new CustomEvent("supplements-change"));
        }
    }

    window.creationStore = new CreationStore();
    window.addEventListener("DOMContentLoaded", () => window.creationStore.restore());
})();
