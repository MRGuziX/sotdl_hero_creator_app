/* Server-authoritative creation state for the progressive wizard. */
(function () {
    class CreationStore extends EventTarget {
        constructor() {
            super();
            this.state = null;
            this.step = null;
        }

        setContract(contract) {
            this.state = contract.state || contract;
            this.step = contract.step || null;
            this.dispatchEvent(new CustomEvent("statechange", {detail: this.state}));
        }

        get characterState() { return this.state; }

        get activeLevel() {
            return this.state ? this.state.current_level : 0;
        }

        isCompleted(level) {
            return Boolean(this.state && this.state.completed_steps.includes(level));
        }

        isLocked(level) {
            return !this.state || (level > this.activeLevel && !this.isCompleted(level));
        }

        async start(mode, ancestry, options = {}) {
            const body = {mode, ancestry};
            if (mode === "random") {
                body.target_level = options.targetLevel || 0;
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
        }

        async advance() {
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
        }

        async pickPath(tier, pathId) {
            if (!this.state) throw new Error("No active creation");
            const response = await fetch(`/api/creations/${this.state.state_id}/paths/${tier}`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({path_id: pathId, state_version: this.state.state_version})
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || "Unable to choose path");
            this.setContract(result);
            try { await this.finalize(); } catch(e) {}
            return result;
        }

        reset() {
            this.state = null;
            this.step = null;
            this.dispatchEvent(new CustomEvent("statechange", {detail: null}));
        }

        async applyChoices(selections) {
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
            if (!response.ok) throw new Error(result.error || result);
            if (result.state || result.step) this.setContract(result);
            try { await this.finalize(); } catch(e) {}
            if (result.download_url) {
                this.dispatchEvent(new CustomEvent("completed", {detail: {downloadUrl: result.download_url}}));
            }
            return result;
        }

        async rewind(targetLevel) {
            if (!this.state) return;
            const response = await fetch(`/api/creations/${this.state.state_id}/rewind`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({target_level: targetLevel})
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || "Unable to rewind creation");
            this.setContract(result);
            try { await this.finalize(); } catch(e) {}
            return result;
        }

        async rewindChoice() {
            if (!this.state || this.state.choice_cursor <= 0) return;
            const response = await fetch(`/api/creations/${this.state.state_id}/rewind_choice`, {
                method: "POST",
                headers: {"Content-Type": "application/json"}
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || "Unable to rewind choice");
            this.setContract(result);
            try { await this.finalize(); } catch(e) {}
            return result;
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
