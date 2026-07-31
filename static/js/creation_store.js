/* Server-authoritative creation state for the progressive wizard. */
(function () {
    window.enabledSupplements = new Set(["PG"]);

    window.toggleSupplement = function (source) {
        if (source === "PG") return;
        if (window.enabledSupplements.has(source)) {
            window.enabledSupplements.delete(source);
        } else {
            window.enabledSupplements.add(source);
        }
        window.dispatchEvent(new CustomEvent("supplements-change"));
    };

    class CreationStore extends EventTarget {
        constructor() {
            super();
            this.state = null;
            this.step = null;
            this._pending = false;
        }

        setContract(contract) {
            this.state = contract.state !== undefined ? contract.state : contract;
            this.step = contract.step || null;
            this.dispatchEvent(new CustomEvent("statechange", {detail: this.state}));
        }

        get activeLevel() {
            return this.state ? this.state.current_level : 0;
        }

        _tryFinalize() {
            if (this.state && this.state.can_finalize) {
                this.finalize().catch(e => console.warn("finalize failed:", e));
            }
        }

        async start(mode, ancestry, options = {}) {
            if (this._pending) return;
            this._pending = true;
            try {
                const body = {mode, ancestry, enabled_sources: Array.from(window.enabledSupplements)};
                if (mode === "random") {
                    body.target_level = options.targetLevel ?? 0;
                    body.paths = options.paths || {novice: null, expert: [], master: null};
                }
                const response = await fetch("/api/creations", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify(body)
                });
                const contract = await response.json();
                if (!response.ok) throw new Error(contract.error || "Unable to start creation");
                this.setContract(contract);
                if (mode === "random") {
                    await this.finalize();
                }
                return contract;
            } finally { this._pending = false; }
        }

        async advance() {
            if (this._pending) return;
            this._pending = true;
            try {
                if (!this.state) throw new Error("No active creation");
                if (window.hidePdfPanel) window.hidePdfPanel();
                const response = await fetch(`/api/creations/${this.state.state_id}/advance`, {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({state_version: this.state.state_version})
                });
                const result = await response.json();
                if (!response.ok) throw new Error(result.error || "Unable to advance");
                this.setContract(result);
                return result;
            } finally { this._pending = false; }
        }

        async pickPath(tier, pathId) {
            if (this._pending) return;
            this._pending = true;
            try {
                if (!this.state) throw new Error("No active creation");
                const response = await fetch(`/api/creations/${this.state.state_id}/paths/${tier}`, {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({path_id: pathId, state_version: this.state.state_version})
                });
                const result = await response.json();
                if (!response.ok) throw new Error(result.error || "Unable to choose path");
                this.setContract(result);
                this._tryFinalize();
                return result;
            } finally { this._pending = false; }
        }

        reset() {
            this.state = null;
            this.step = null;
            this.dispatchEvent(new CustomEvent("statechange", {detail: null}));
        }

        async applyChoices(selections) {
            if (this._pending) return;
            this._pending = true;
            try {
                if (!this.state) throw new Error("No active creation");
                const response = await fetch(
                    `/api/creations/${this.state.state_id}/steps/${this.activeLevel}/choices`,
                    {
                        method: "POST",
                        headers: {"Content-Type": "application/json"},
                        body: JSON.stringify({
                            selections,
                            choice_cursor: this.state.choice_cursor,
                            state_version: this.state.state_version
                        })
                    }
                );
                const result = await response.json();
                if (!response.ok) throw new Error(result.error || "Unable to apply choices");
                if (result.state || result.step) this.setContract(result);
                this._tryFinalize();
                if (result.download_url) {
                    this.dispatchEvent(new CustomEvent("completed", {detail: {downloadUrl: result.download_url}}));
                }
                return result;
            } finally { this._pending = false; }
        }

        async rewind(targetLevel) {
            if (this._pending) return;
            this._pending = true;
            try {
                if (!this.state) return;
                const response = await fetch(`/api/creations/${this.state.state_id}/rewind`, {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({target_level: targetLevel, state_version: this.state.state_version})
                });
                const result = await response.json();
                if (!response.ok) throw new Error(result.error || "Unable to rewind creation");
                this.setContract(result);
                this._tryFinalize();
                return result;
            } finally { this._pending = false; }
        }

        async rewindChoice() {
            if (this._pending) return;
            this._pending = true;
            try {
                if (!this.state || this.state.choice_cursor <= 0) return;
                const response = await fetch(`/api/creations/${this.state.state_id}/rewind_choice`, {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({state_version: this.state.state_version})
                });
                const result = await response.json();
                if (!response.ok) throw new Error(result.error || "Unable to rewind choice");
                this.setContract(result);
                this._tryFinalize();
                return result;
            } finally { this._pending = false; }
        }

        async setEquipment(selections) {
            if (this._pending) return;
            this._pending = true;
            try {
                if (!this.state) throw new Error("No active creation");
                const response = await fetch(`/api/creations/${this.state.state_id}/equipment`, {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({...selections, state_version: this.state.state_version})
                });
                const result = await response.json();
                if (!response.ok) throw new Error(result.error || "Unable to set equipment");
                this.setContract(result);
                this._tryFinalize();
                return result;
            } finally { this._pending = false; }
        }

        async finalize(manual = false) {
            if (!this.state) throw new Error("No active creation");
            const response = await fetch(`/api/creations/${this.state.state_id}/finalize`, {
                method: "POST",
                headers: {"Content-Type": "application/json"}
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || "Unable to finalize creation");
            this.dispatchEvent(new CustomEvent("completed", {detail: {downloadUrl: result.pdf_url}}));
            if (manual) {
                this.dispatchEvent(new CustomEvent("finalized", {detail: result}));
            }
            return result;
        }
    }

    window.creationStore = new CreationStore();
})();
