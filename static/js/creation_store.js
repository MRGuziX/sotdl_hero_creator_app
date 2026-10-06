/* Python processes commands; the browser carries each tab's signed creation state. */
(function () {
    const ACTIVE_KEY = "sotdl.browserDraft.v1";
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
            this.stateToken = null;
            this.pdfUrl = null;
            this.pdfVersion = null;
            this._token = null;
        }

        get busy() { return this._token !== null; }
        get activeLevel() { return this.state ? this.state.current_level : 0; }

        _remember(draft) {
            try {
                if (draft) sessionStorage.setItem(ACTIVE_KEY, JSON.stringify(draft));
                else sessionStorage.removeItem(ACTIVE_KEY);
            } catch (_) {
                // Do not leave an older, misleading draft behind after a quota failure.
                try { sessionStorage.removeItem(ACTIVE_KEY); } catch (_) { /* Storage disabled. */ }
                if (draft) this.dispatchEvent(new CustomEvent("error", {detail:
                    "Przeglądarka nie zapisała szkicu. Nie odświeżaj strony przed pobraniem PDF."}));
            }
        }

        setContract(contract) {
            if (!contract.state?.state_id || typeof contract.state_token !== "string" || !contract.state_token) {
                throw new Error("Serwer zwrócił nieprawidłowy stan postaci. Spróbuj ponownie.");
            }
            this.clearPdf();
            this.state = contract.state;
            this.step = contract.step || null;
            this.stateToken = contract.state_token;
            this._remember({creation_id: this.state.state_id, state_token: this.stateToken});
            if (this.state?.enabled_sources) {
                window.enabledSupplements = new Set(this.state.enabled_sources);
            }
            this.dispatchEvent(new CustomEvent("statechange", {detail: this.state}));
            window.dispatchEvent(new CustomEvent("supplements-change"));
        }

        async _request(url, body, token, pdf = false) {
            const response = await fetch(url, {
                method: body === undefined ? "GET" : "POST",
                headers: {"Content-Type": "application/json"},
                ...(body === undefined ? {} : {body: JSON.stringify(body)}),
                signal: token.controller.signal,
                credentials: "omit",
                cache: "no-store"
            });
            if (this._token !== token) throw new DOMException("Cancelled", "AbortError");
            if (response.ok && pdf) {
                if (response.headers.get("Content-Type")?.split(";")[0].trim().toLowerCase() !== "application/pdf") {
                    throw new Error("Serwer nie zwrócił pliku PDF. Spróbuj ponownie.");
                }
                const blob = await response.blob();
                if (await blob.slice(0, 5).text() !== "%PDF-") {
                    throw new Error("Serwer zwrócił nieprawidłowy plik PDF. Spróbuj ponownie.");
                }
                if (this._token !== token) throw new DOMException("Cancelled", "AbortError");
                return blob;
            }
            let result;
            try { result = await response.json(); }
            catch (_) { throw new Error("Serwer zwrócił nieprawidłową odpowiedź. Spróbuj ponownie."); }
            if (this._token !== token) throw new DOMException("Cancelled", "AbortError");
            if (!response.ok) {
                if (response.status === 409 && this.state) {
                    throw new Error("Wybór nie pasuje do bieżącego etapu. Sprawdź wybory i spróbuj ponownie.");
                }
                if ([404, 410].includes(response.status)) {
                    token.reportError = true;
                    this.reset();
                    throw new Error("Szkic jest nieprawidłowy lub niezgodny. Rozpocznij nową postać.");
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

        resume(draft) {
            return this._run(async token => {
                const result = await this._request("/api/creations/" + encodeURIComponent(draft.creation_id) + "/resume",
                    {state_token: draft.state_token}, token);
                this.setContract(result);
                return result;
            }, true);
        }

        restore() {
            try {
                sessionStorage.removeItem("sotdl.activeCreation"); // Old database IDs cannot be resumed.
                const saved = sessionStorage.getItem(ACTIVE_KEY);
                if (saved) {
                    const draft = JSON.parse(saved);
                    if (!draft?.creation_id || typeof draft.state_token !== "string" || !draft.state_token) {
                        throw new Error("Invalid browser draft");
                    }
                    return this.resume(draft);
                }
            } catch (_) { this._remember(null); }
            return Promise.resolve(null);
        }

        _mutate(suffix, body = {}, preview = true) {
            return this._run(async token => {
                if (!this.state) throw new Error("Brak aktywnej postaci.");
                this.clearPdf();
                window.hidePdfPanel?.();
                const result = await this._request("/api/creations/" + this.state.state_id + "/" + suffix,
                    {...body, state_version: this.state.state_version, state_token: this.stateToken}, token);
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
            if (!this.pdfUrl || this.pdfVersion !== this.state.state_version) {
                const blob = await this._request("/api/creations/" + this.state.state_id + "/finalize",
                    {state_version: this.state.state_version, state_token: this.stateToken}, token, true);
                this.clearPdf();
                this.pdfUrl = URL.createObjectURL(blob);
                this.pdfVersion = this.state.state_version;
            }
            const result = {downloadUrl: this.pdfUrl};
            this.dispatchEvent(new CustomEvent("completed", {detail: result}));
            if (manual) this.dispatchEvent(new CustomEvent("finalized", {detail: result}));
            return result;
        }

        finalize(manual = false) { return this._run(token => this._export(token, manual)); }

        clearPdf() {
            if (this.pdfUrl) URL.revokeObjectURL(this.pdfUrl);
            this.pdfUrl = null;
            this.pdfVersion = null;
            this.dispatchEvent(new CustomEvent("pdfclear"));
        }

        reset() {
            this._token?.controller.abort();
            this._token = null;
            this.state = null;
            this.step = null;
            this.stateToken = null;
            this.clearPdf();
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
