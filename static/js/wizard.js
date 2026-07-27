(function () {
    "use strict";

    const ATTRIBUTE_LABELS = {
        strength: "Siła",
        dexterity: "Zręczność",
        intelligence: "Intelekt",
        will: "Wola"
    };

    function traditionForSpell(spellName, magicContext) {
        const spellsByTradition = (magicContext && magicContext.spells_by_tradition) || {};
        return Object.keys(spellsByTradition).find(
            (tradition) => spellsByTradition[tradition].includes(spellName)
        );
    }

    function describeOption(option, hero, magicContext) {
        const type = option.type;
        if (type === "add_attribute") {
            const label = ATTRIBUTE_LABELS[option.name] || option.name;
            return `Zwiększ ${label} o ${option.value}`;
        }
        if (type === "add_language") {
            return `Język: ${option.name === "any" ? "Dodatkowy język" : option.name}`;
        }
        if (type === "add_profession") {
            return `Profesja: ${option.name === "any" ? "Dodatkowa profesja" : option.name}`;
        }
        if (type === "add_item") {
            return `Przedmiot: ${option.name}`;
        }
        if (type === "grant_literacy") {
            return `Nauka pisania: ${option.target === "any" ? "dowolny język" : option.target}`;
        }
        if (type === "add_talent") {
            const talents = (hero && hero.talents) || [];
            const known = talents.some((talent) => talent.name === option.name || talent.name === `${option.name} (poz. 2)`);
            return `Talent: ${option.name}${known ? " (ULEPSZENIE)" : ""}`;
        }
        if (type === "add_religion") {
            return `Religia: ${option.name === "any" ? "Wybierz religię" : option.name}`;
        }
        if (type === "add_tradition") {
            return `Tradycja: ${option.name === "religious_tradition" ? "Tradycja religijna" : option.name}`;
        }
        if (type === "add_spell") {
            if (option.name === "known_tradition" || option.name === "any") {
                return `Czar: ${option.name === "known_tradition" ? "Czar ze znanej tradycji" : "Dowolny czar"}`;
            }
            const tradition = traditionForSpell(option.name, magicContext);
            return tradition ? `Czar: ${option.name} (${tradition})` : `Czar: ${option.name}`;
        }
        if (type === "update_language") {
            return `Aktualizacja języka: ${option.name}`;
        }
        return JSON.stringify(option);
    }

    class WizardPopover {
        static init() {
            if (this.el) return;
            this.overlay = document.createElement("div");
            this.overlay.className = "wizard-popover-overlay";
            this.el = document.createElement("div");
            this.el.className = "wizard-popover";
            document.body.append(this.overlay, this.el);

            this.overlay.addEventListener("click", () => this.close());
            window.addEventListener("keydown", (e) => {
                if (e.key === "Escape") this.close();
            });

            // Reposition on scroll/resize
            window.addEventListener("resize", () => this.reposition());
            window.addEventListener("scroll", () => this.reposition(), true);
        }

        static toggle(trigger, content) {
            this.init();
            if (this.isVisible && this.currentTarget === trigger) {
                this.close();
            } else {
                this.open(trigger, content);
            }
        }

        static open(trigger, content) {
            this.init();
            this.currentTarget = trigger;
            this.el.textContent = content;
            
            // Set visibility to hidden to measure first
            this.el.style.visibility = "hidden";
            this.el.classList.add("visible");
            this.isVisible = true;

            this.reposition();

            this.el.style.visibility = "";
            this.overlay.classList.add("visible");
        }

        static close() {
            if (!this.el) return;
            this.isVisible = false;
            this.el.classList.remove("visible");
            this.overlay.classList.remove("visible");
            this.currentTarget = null;
        }

        static reposition() {
            if (!this.currentTarget || !this.isVisible) return;
            
            if (window.innerWidth <= 1024) {
                this.el.style.top = "";
                this.el.style.left = "";
                return;
            }

            const rect = this.currentTarget.getBoundingClientRect();
            const popRect = this.el.getBoundingClientRect();

            let top = rect.top + (rect.height / 2) - (popRect.height / 2);
            let left = rect.right + 12;

            if (left + popRect.width > window.innerWidth - 20) {
                left = rect.left - popRect.width - 12;
            }
            if (left < 10) left = 10;
            
            if (top + popRect.height > window.innerHeight - 20) {
                top = window.innerHeight - popRect.height - 20;
            }
            if (top < 10) top = 10;

            this.el.style.top = `${top}px`;
            this.el.style.left = `${left}px`;
        }
    }

    class ProgressNavigator extends HTMLElement {
        connectedCallback() {
            this.store = window.creationStore;
            this.render();
            this._onStateChange = () => this.render();
            this._onUiChange = () => this.render();
            this.store.addEventListener("statechange", this._onStateChange);
            window.addEventListener("ui-level-change", this._onUiChange);
            window.addEventListener("ui-screen-change", this._onUiChange);
        }
        disconnectedCallback() {
            this.store.removeEventListener("statechange", this._onStateChange);
            window.removeEventListener("ui-level-change", this._onUiChange);
            window.removeEventListener("ui-screen-change", this._onUiChange);
        }

        updateVisibility() {
            const shell = document.querySelector('wizard-shell');
            const screen = (shell && shell._screen) || 'menu';
            const state = this.store && this.store.state;
            if (state || screen !== 'menu') {
                this.classList.add('visible');
            } else {
                this.classList.remove('visible');
            }
        }

        render() {
            this.updateVisibility();
            const state = this.store && this.store.state;
            let currentLevel = 0;
            if (state) {
                currentLevel = state.current_level;
            } else {
                const shell = document.querySelector('wizard-shell');
                currentLevel = (shell && shell._lvl !== undefined) ? shell._lvl : 0;
            }

            this.replaceChildren();
            for (let level = 0; level <= 10; level += 1) {
                const button = document.createElement("button");
                const active = level === currentLevel;
                const completed = state && state.completed_steps.includes(level) && !active;

                button.type = "button";
                button.textContent = String(level);
                button.className = active ? "is-active" : (completed ? "is-complete" : "is-locked");
                this.append(button);
            }
        }
    }

    class MainMenu extends HTMLElement {
        connectedCallback() { this.render(); }
        render() {
            this.replaceChildren();
            const heading = document.createElement("h3");
            heading.className = "section-title main-menu-title";
            heading.textContent = "Jak chcesz stworzyć bohatera?";
            this.append(heading);

            const actions = document.createElement("div");
            actions.className = "main-menu-actions";

            const randomButton = document.createElement("button");
            randomButton.type = "button";
            randomButton.className = "generate-button enabled main-menu-button";
            randomButton.textContent = "🎲 Tryb losowy";
            randomButton.addEventListener("click", () => this.dispatchEvent(new CustomEvent("choose-mode", {detail: {mode: "random"}})));

            const manualButton = document.createElement("button");
            manualButton.type = "button";
            manualButton.className = "confirm-button main-menu-button";
            manualButton.textContent = "✅ Tryb ręczny";
            manualButton.addEventListener("click", () => this.dispatchEvent(new CustomEvent("choose-mode", {detail: {mode: "manual"}})));

            actions.append(randomButton, manualButton);
            this.append(actions);
        }
    }

    class AncestryPicker extends HTMLElement {
        constructor() {
            super();
            this.nextLabel = "Dalej";
        }
        connectedCallback() {
            this._selected = null;
            this.render();
        }
        render() {
            this.replaceChildren();
            const heading = document.createElement("h3");
            heading.className = "section-title";
            heading.textContent = "Wybierz pochodzenie";
            this.append(heading);

            const grid = document.createElement("div");
            grid.className = "ancestry-grid";
            const list = [
                {id: "human", name: "Człowiek"}, {id: "automaton", name: "Automaton"},
                {id: "goblin", name: "Goblin"}, {id: "dwarf", name: "Krasnolud"},
                {id: "orc", name: "Ork"}, {id: "changeling", name: "Odmieniec"}
            ];
            const descriptions = window.ancestryDescriptions || {};

            list.forEach(({id, name}) => {
                const card = document.createElement("div");
                card.className = "ancestry-item";
                if (this._selected === id) card.classList.add("active");
                card.tabIndex = 0; card.setAttribute("role", "button");

                const label = document.createElement("span");
                label.className = "ancestry-name";
                label.textContent = name;
                card.append(label);

                const tooltipBtn = document.createElement("button");
                tooltipBtn.type = "button"; tooltipBtn.className = "ancestry-tooltip-trigger";
                tooltipBtn.textContent = "ⓘ";
                tooltipBtn.addEventListener("click", (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    WizardPopover.toggle(tooltipBtn, descriptions[id] || "Brak opisu.");
                });
                card.append(tooltipBtn);

                card.addEventListener("click", () => {
                    this._selected = id;
                    this.render();
                });
                card.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); card.click(); } });
                grid.append(card);
            });
            this.append(grid);

            const footer = document.createElement("div");
            footer.className = "step-shell-footer";

            const backButton = document.createElement("button");
            backButton.type = "button"; backButton.className = "step-back-button ancestry-picker-back";
            backButton.textContent = "Wstecz";
            backButton.addEventListener("click", () => this.dispatchEvent(new CustomEvent("back")));

            const nextButton = document.createElement("button");
            nextButton.type = "button"; nextButton.className = "confirm-button step-next-button";
            nextButton.textContent = this.nextLabel;
            nextButton.disabled = !this._selected;
            nextButton.addEventListener("click", () => {
                if (this._selected) {
                    this.dispatchEvent(new CustomEvent("choose-ancestry", {detail: {ancestry: this._selected}}));
                }
            });

            footer.append(backButton, nextButton);
            this.append(footer);
        }
    }

    class StepShell extends HTMLElement {
        connectedCallback() {
            this.store = window.creationStore;
            this._selections = [];
            this.render();
            this._onStateChange = () => { this._selections = []; this.render(); };
            this.store.addEventListener("statechange", this._onStateChange);
        }
        disconnectedCallback() { this.store.removeEventListener("statechange", this._onStateChange); }

        render() {
            const state = this.store && this.store.state;
            this.replaceChildren();
            if (!state) { this.hidden = true; return; }
            this.hidden = false;

            const magicContext = this.store.step || {};
            const groups = state.level_choices || [];
            const cursor = state.choice_cursor || 0;
            const currentGroup = groups[cursor];

            // Pre-fill selections if we are navigating back to a resolved choice
            const pastSelections = state.selections || [];
            if (this._selections.length === 0 && pastSelections[cursor] !== undefined) {
                // If it's a single index (standard)
                const selectedIdx = pastSelections[cursor];
                if (typeof selectedIdx === "number") {
                    this._selections = [currentGroup[selectedIdx]];
                } else if (Array.isArray(selectedIdx)) {
                    this._selections = selectedIdx.map(i => currentGroup[i]);
                }
            }

            const heading = document.createElement("h3");
            heading.className = "step-shell-title";
            const total = state.total_choices_in_level || 0;
            heading.textContent = total ? `Poziom ${state.current_level} wybór ${cursor + 1}/${total}` : `Poziom ${state.current_level}`;
            this.append(heading);

            if (!currentGroup || !currentGroup.length) {
                const empty = document.createElement("p");
                empty.className = "step-shell-empty";
                empty.textContent = "Brak oczekujących wyborów na tym poziomie.";
                this.append(empty);
                return;
            }

            const isAttrGroup = currentGroup.every(a => a.type === "add_attribute");
            if (isAttrGroup) {
                const isPaired = groups[cursor + 1]
                    && groups[cursor + 1].every(a => a.type === "add_attribute");
                this._renderAttributeStepper(currentGroup, state, isPaired ? 2 : 1);
            } else {
                this._renderStandardChoice(currentGroup, state, magicContext);
            }

            this._renderFooter(state);
        }

        _renderAttributeStepper(group, state, requiredCount) {
            const panel = document.createElement("div");
            panel.className = "left-panel-tools";

            const attrs = group.map(a => a.name);
            const selected = new Map();
            this._selections.forEach(s => selected.set(s.name, s));

            const updateUI = () => {
                panel.querySelectorAll(".tool-row").forEach(row => {
                    const attr = row.dataset.attr;
                    const isSelected = selected.has(attr);
                    const plusBtn = row.querySelector(".stepper-plus");
                    const minusBtn = row.querySelector(".stepper-minus");
                    const val = row.querySelector(".stepper-value");
                    plusBtn.disabled = isSelected || selected.size >= requiredCount;
                    minusBtn.disabled = !isSelected;
                    val.textContent = isSelected ? state.hero[attr] + 1 : state.hero[attr];
                    if (isSelected) val.classList.add("highlight-text");
                    else val.classList.remove("highlight-text");
                });
                const nextBtn = this.querySelector(".step-next-button");
                if (nextBtn) nextBtn.disabled = selected.size !== requiredCount;
                this._selections = Array.from(selected.values());
            };

            attrs.forEach(attr => {
                const row = document.createElement("div");
                row.className = "tool-row";
                row.dataset.attr = attr;

                const label = document.createElement("span");
                label.className = "tool-label";
                label.textContent = ATTRIBUTE_LABELS[attr] || attr;

                const stepper = document.createElement("div");
                stepper.className = "level-stepper";

                const minusBtn = document.createElement("button");
                minusBtn.type = "button";
                minusBtn.className = "stepper-btn stepper-minus";
                minusBtn.textContent = "−";
                minusBtn.disabled = !selected.has(attr);
                minusBtn.addEventListener("click", () => {
                    selected.delete(attr);
                    updateUI();
                });

                const val = document.createElement("span");
                val.className = "stepper-value";
                val.textContent = state.hero[attr];

                const plusBtn = document.createElement("button");
                plusBtn.type = "button";
                plusBtn.className = "stepper-btn stepper-plus";
                plusBtn.textContent = "+";
                plusBtn.addEventListener("click", () => {
                    if (selected.size < requiredCount) {
                        selected.set(attr, {type: "add_attribute", name: attr, value: 1});
                        updateUI();
                    }
                });

                stepper.append(minusBtn, val, plusBtn);
                row.append(label, stepper);
                panel.append(row);
            });

            this.append(panel);
            updateUI();

            this._submit = async () => {
                if (selected.size !== requiredCount) return;
                try {
                    await this.store.applyChoices(Array.from(selected.values()));
                    window.showWizardToast?.("Atrybuty zwiększone.");
                } catch (e) { window.showWizardToast?.(e.message); }
            };
        }

        _renderStandardChoice(group, state, magicContext) {
            const isMagic = group.some(a => a.type === "add_tradition" || a.type === "add_spell");
            const isProf = group.some(a => a.type === "add_profession" || a.type === "add_language");

            if (isMagic || isProf) {
                this._renderModalChoice(group, state, magicContext, isMagic ? "Magia" : "Profesje");
            } else {
                this._renderRadioChoice(group, state, magicContext);
            }
        }

        _renderRadioChoice(group, state, magicContext) {
            const fieldset = document.createElement("fieldset");
            fieldset.className = "step-card";
            const legend = document.createElement("legend");
            legend.textContent = "Wybierz opcję:";
            fieldset.append(legend);

            group.forEach((opt, idx) => {
                const label = document.createElement("label");
                label.className = "step-option";
                const radio = document.createElement("input");
                radio.type = "radio"; radio.name = "choice"; radio.value = idx;
                radio.checked = this._selections.some(s => JSON.stringify(s) === JSON.stringify(opt));
                radio.addEventListener("change", () => this._selections = [opt]);
                const mark = document.createElement("span");
                mark.className = "step-option-mark";
                const text = document.createElement("span");
                text.className = "step-option-text";
                text.textContent = describeOption(opt, state.hero, magicContext);
                label.append(radio, mark, text);

                if (opt.description) {
                    const tooltipBtn = document.createElement("button");
                    tooltipBtn.type = "button"; tooltipBtn.className = "ancestry-tooltip-trigger inner-tooltip";
                    tooltipBtn.textContent = "ⓘ";
                    tooltipBtn.addEventListener("click", (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        WizardPopover.toggle(tooltipBtn, opt.description);
                    });
                    label.append(tooltipBtn);
                }

                fieldset.append(label);
            });
            this.append(fieldset);
        }

        _renderModalChoice(group, state, magicContext, labelText) {
            const btn = document.createElement("button");
            btn.className = "confirm-button";
            btn.textContent = `Otwórz wybór: ${labelText}`;
            
            const container = document.createElement("div");
            container.className = "choices-container";
            
            const scroll = document.createElement("div");
            scroll.className = "choices-scroll";
            
            const isSpellStep = group.every(a => a.type === "add_spell");
            const hasSztuczki = state.hero.talents.some(t => t.name === "Sztuczki");
            const requiredCount = (isSpellStep && hasSztuczki) ? 2 : 1;
            
            const counter = document.createElement("h3");
            counter.className = "magic-counter";
            if (requiredCount > 1) counter.classList.add("highlight-text");
            const updateCounter = () => {
                counter.textContent = `Wybierz ${requiredCount} ${requiredCount > 1 ? "zaklęcia" : "opcję"} (${this._selections.length}/${requiredCount})`;
                const nextBtn = this.querySelector(".step-next-button");
                if (nextBtn) nextBtn.disabled = this._selections.length !== requiredCount;
            };

            group.forEach((opt, idx) => {
                const tile = document.createElement("label");
                tile.className = "step-option";
                const input = document.createElement("input");
                input.type = requiredCount > 1 ? "checkbox" : "radio";
                input.name = "modal-choice";
                input.checked = this._selections.some(s => JSON.stringify(s) === JSON.stringify(opt));
                input.addEventListener("change", () => {
                    if (input.checked) {
                        if (requiredCount === 1) this._selections = [opt];
                        else if (this._selections.length < requiredCount) this._selections.push(opt);
                        else input.checked = false;
                    } else {
                        this._selections = this._selections.filter(s => JSON.stringify(s) !== JSON.stringify(opt));
                    }
                    updateCounter();
                });
                const mark = document.createElement("span");
                mark.className = "step-option-mark";
                const text = document.createElement("span");
                text.className = "step-option-text";
                text.textContent = describeOption(opt, state.hero, magicContext);
                tile.append(input, mark, text);

                if (opt.description) {
                    const tooltipBtn = document.createElement("button");
                    tooltipBtn.type = "button"; tooltipBtn.className = "ancestry-tooltip-trigger inner-tooltip";
                    tooltipBtn.textContent = "ⓘ";
                    tooltipBtn.addEventListener("click", (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        WizardPopover.toggle(tooltipBtn, opt.description);
                    });
                    tile.append(tooltipBtn);
                }

                scroll.append(tile);
            });

            container.append(counter, scroll);
            btn.addEventListener("click", () => container.classList.toggle("visible"));
            
            this.append(btn, container);
            updateCounter();
        }

        _renderFooter(state) {
            const footer = document.createElement("div");
            footer.className = "step-shell-footer";
            const back = document.createElement("button");
            back.className = "step-back-button"; back.textContent = "Wstecz";
            back.addEventListener("click", () => {
                if (state.choice_cursor > 0) this.store.rewindChoice();
                else if (state.current_level === 0) this.store.reset();
                else this.store.rewind(state.current_level - 1);
            });
            const next = document.createElement("button");
            next.className = "confirm-button step-next-button"; next.textContent = "Dalej";
            next.addEventListener("click", () => this._submit());
            footer.append(back, next);
            this.append(footer);
        }

        async _submit() {
            if (!this._selections.length) { window.showWizardToast?.("Wybierz opcję."); return; }
            try {
                await this.store.applyChoices(this._selections);
            } catch (e) { window.showWizardToast?.(e.message); }
        }
    }

    class PathPicker extends HTMLElement {
        connectedCallback() { this.store = window.creationStore; this._search = ""; this._cursorPos = 0; this._selected = null; this.render(); }
        get tier() { return this.getAttribute("tier"); }
        render() {
            this.replaceChildren();
            const tier = this.tier;
            const heading = document.createElement("h3");
            heading.className = "section-title";
            heading.textContent = `Wybierz Ścieżkę ${tier === "novice" ? "Nowicjusza" : tier === "expert" ? "Eksperta" : "Mistrza"}`;
            this.append(heading);

            if (tier === "expert" || tier === "master") {
                const search = document.createElement("input");
                search.className = "path-picker-search"; search.placeholder = "Szukaj...";
                search.value = this._search;
                search.addEventListener("input", (e) => { this._search = e.target.value; this._cursorPos = e.target.selectionStart; this.render(); });
                this.append(search);
                if (this._search) { search.focus(); search.setSelectionRange(this._cursorPos, this._cursorPos); }
            }

            const grid = document.createElement("div");
            grid.className = "ancestry-grid";
            const catalog = (window.PATH_CATALOG && window.PATH_CATALOG[tier]) || [];
            const needle = this._search.toLowerCase();
            catalog.filter(p => p.name.toLowerCase().includes(needle)).forEach(p => {
                const card = document.createElement("div");
                card.className = "ancestry-item";
                if (this._selected === p.id) card.classList.add("active");
                card.textContent = p.name;
                card.addEventListener("click", () => { this._selected = p.id; this._selectedTier = tier; this.render(); });
                grid.append(card);
            });
            this.append(grid);
            
            if (tier === "master") {
                const hint = document.createElement("p");
                hint.className = "path-picker-hint"; hint.textContent = "...lub wybierz drugą Ścieżkę Eksperta:";
                this.append(hint);
                const expertGrid = document.createElement("div");
                expertGrid.className = "ancestry-grid";
                const chosen = new Set(this.store.state.paths.expert);
                window.PATH_CATALOG.expert.filter(p => !chosen.has(p.id) && p.name.toLowerCase().includes(needle)).forEach(p => {
                    const card = document.createElement("div");
                    card.className = "ancestry-item";
                    if (this._selected === p.id) card.classList.add("active");
                    card.textContent = p.name;
                    card.addEventListener("click", () => { this._selected = p.id; this._selectedTier = "expert"; this.render(); });
                    expertGrid.append(card);
                });
                this.append(expertGrid);
            }

            const footer = document.createElement("div");
            footer.className = "step-shell-footer";
            const back = document.createElement("button");
            back.className = "step-back-button"; back.textContent = "Wstecz";
            back.addEventListener("click", () => this.store.rewind(this.store.state.current_level));
            const next = document.createElement("button");
            next.className = "confirm-button step-next-button";
            next.textContent = "Dalej";
            next.disabled = !this._selected;
            next.addEventListener("click", () => {
                if (this._selected) this.store.pickPath(this._selectedTier, this._selected);
            });
            footer.append(back, next);
            this.append(footer);
        }
    }

    class CrossroadsScreen extends HTMLElement {
        connectedCallback() { this.render(); }
        render() {
            this.replaceChildren();
            const state = window.creationStore.state;
            const heading = document.createElement("h3");
            heading.className = "section-title"; 
            heading.textContent = state.current_level >= 10 ? "Bohater gotowy!" : `Poziom ${state.current_level} osiągnięty`;
            const summary = document.createElement("p");
            summary.className = "crossroads-summary";
            summary.textContent = state.current_level >= 10 ? "Wszystkie wybory zostały dokonane." : "Zapisz aktualny stan karty PDF lub awansuj bohatera dalej.";
            const actions = document.createElement("div");
            actions.className = "crossroads-actions";
            const save = document.createElement("button");
            save.className = "generate-button enabled"; 
            save.textContent = "📜 Zapisz PDF";
            save.addEventListener("click", () => window.creationStore.finalize(true));
            actions.append(save);

            if (state.mode === "random") {
                const reset = document.createElement("button");
                reset.className = "confirm-button";
                reset.textContent = "🔄 Od początku";
                reset.addEventListener("click", () => {
                    window.creationStore.reset();
                    const shell = document.querySelector("wizard-shell");
                    if (shell) {
                        shell._screen = "menu";
                        shell._lvl = 0;
                        shell._mode = null;
                        shell.render();
                        window.dispatchEvent(new CustomEvent("ui-screen-change"));
                    }
                });
                actions.append(reset);
            }

            if (state.can_advance && state.mode !== "random") {
                const adv = document.createElement("button");
                adv.className = "confirm-button"; adv.textContent = "⬆ Awansuj";
                adv.addEventListener("click", () => window.creationStore.advance());
                actions.append(adv);
            }
            
            this.append(heading, summary, actions);

            if (state.mode !== "random") {
                const footer = document.createElement("div");
                footer.className = "step-shell-footer";
                const back = document.createElement("button");
                back.className = "step-back-button"; back.textContent = "Wstecz";
                back.addEventListener("click", () => window.creationStore.rewindChoice());
                footer.append(back);
                this.append(footer);
            }
        }
    }

    class RandomConfigScreen extends HTMLElement {
        connectedCallback() { this.render(); }
        render() {
            this.replaceChildren();
            
            const heading = document.createElement("h3");
            heading.className = "section-title";
            heading.textContent = "Ustaw poziom docelowy";
            this.append(heading);
            
            const footer = document.createElement("div");
            footer.className = "step-shell-footer";
            
            const back = document.createElement("button");
            back.className = "step-back-button"; back.textContent = "Wstecz";
            back.addEventListener("click", () => this.dispatchEvent(new CustomEvent("back")));
            
            const start = document.createElement("button");
            start.className = "confirm-button step-next-button"; start.textContent = "Generuj";
            start.addEventListener("click", () => this.dispatchEvent(new CustomEvent("start")));
            
            footer.append(back, start);
            this.append(footer);
        }
    }

    class WizardShell extends HTMLElement {
        constructor() {
            super();
            this.store = window.creationStore;
            this._screen = "menu";
            this._mode = null;
            this._lvl = 0;
            this._chosenPaths = { novice: null, expert: null, master: null };
        }
        connectedCallback() {
            this._renderQueued = false;
            this._onStateChange = () => {
                if (this._renderQueued) return;
                this._renderQueued = true;
                queueMicrotask(() => { this._renderQueued = false; this.render(); });
            };
            this.render();
            this.store.addEventListener("statechange", this._onStateChange);
        }
        disconnectedCallback() {
            this.store.removeEventListener("statechange", this._onStateChange);
        }

        _buildPaths() {
            const paths = { novice: null, expert: [], master: null };
            if (this._lvl >= 1) paths.novice = this._chosenPaths.novice;
            if (this._lvl >= 3 && this._chosenPaths.expert) paths.expert.push(this._chosenPaths.expert);
            if (this._lvl >= 7 && this._chosenPaths.master) {
                const mId = this._chosenPaths.master;
                const isExp = window.PATH_CATALOG.expert.some(p => p.id === mId);
                if (isExp) paths.expert.push(mId);
                else paths.master = mId;
            }
            return paths;
        }

        _createPathSelect(tier, placeholder, options) {
            const select = document.createElement("select");
            select.className = "random-path-select";
            
            const optNone = document.createElement("option");
            optNone.value = "";
            optNone.textContent = placeholder;
            select.append(optNone);

            options.forEach(p => {
                const opt = document.createElement("option");
                opt.value = p.id;
                opt.textContent = p.name;
                if (this._chosenPaths[tier] === p.id) opt.selected = true;
                select.append(opt);
            });

            select.addEventListener("change", (e) => {
                const val = e.target.value || null;
                this._chosenPaths[tier] = val;
                // If expert changed, we might need to re-render master to update available experts
                if (tier === "expert") this.render();
            });

            return select;
        }

        render() {
            this.replaceChildren();
            const state = this.store.state;
            if (state && state.mode) {
                this._mode = state.mode;
            }

            if (this._screen === "menu") {
                const m = document.createElement("main-menu");
                m.addEventListener("choose-mode", (e) => {
                    this._mode = e.detail.mode;
                    this._screen = "ancestry";
                    this._chosenPaths = { novice: null, expert: null, master: null };
                    this.render();
                    window.dispatchEvent(new CustomEvent("ui-screen-change"));
                });
                this.append(m);
                return;
            }

            const panel = document.createElement("div");
            panel.className = "workspace-panel";

            // Level Stepper (Integrated Indicator)
            if (this._mode === "random" && !state) {
                const levelTools = document.createElement("div");
                levelTools.className = "left-panel-tools";
                const levelRow = document.createElement("div");
                levelRow.className = "tool-row";
                const levelLabel = document.createElement("span");
                levelLabel.className = "tool-label";
                levelLabel.textContent = "Poziom";
                const stepper = document.createElement("div");
                stepper.className = "level-stepper";
                const levelVal = document.createElement("span");
                levelVal.id = "level-value";
                levelVal.textContent = state ? state.current_level : this._lvl;
                
                const down = document.createElement("button");
                down.type = "button";
                down.className = "stepper-btn"; down.textContent = "−";
                down.disabled = true;
                const up = document.createElement("button");
                up.type = "button";
                up.className = "stepper-btn"; up.textContent = "+";
                up.disabled = true;

                if (!state && this._mode === "random") {
                    down.disabled = this._lvl <= 0;
                    up.disabled = this._lvl >= 10;
                    down.addEventListener("click", () => {
                        this._lvl = Math.max(0, this._lvl - 1);
                        this.render();
                        window.dispatchEvent(new CustomEvent("ui-level-change"));
                    });
                    up.addEventListener("click", () => {
                        this._lvl = Math.min(10, this._lvl + 1);
                        this.render();
                        window.dispatchEvent(new CustomEvent("ui-level-change"));
                    });
                }
                
                stepper.append(down, levelVal, up);
                levelRow.append(levelLabel, stepper);
                levelTools.append(levelRow);

                if (!state && this._mode === "random" && this._lvl >= 1) {
                    // Novice Path
                    if (this._lvl >= 1) {
                        const sel = this._createPathSelect("novice", "Wybierz ścieżkę Nowicjusza (opcjonalne)", window.PATH_CATALOG.novice);
                        levelTools.append(sel);
                    }
                    // Expert Path
                    if (this._lvl >= 3) {
                        const sel = this._createPathSelect("expert", "Wybierz ścieżkę Eksperta (opcjonalne)", window.PATH_CATALOG.expert);
                        levelTools.append(sel);
                    }
                    // Master / Second Expert Path
                    if (this._lvl >= 7) {
                        const expertId = this._chosenPaths.expert;
                        const availableExperts = window.PATH_CATALOG.expert.filter(p => p.id !== expertId);
                        const masterOptions = [
                            ...window.PATH_CATALOG.master,
                            ...availableExperts.map(p => ({...p, name: `${p.name} (Ekspert)`}))
                        ];
                        const sel = this._createPathSelect("master", "Wybierz ścieżkę Mistrza lub Eksperta (opcjonalne)", masterOptions);
                        levelTools.append(sel);
                    }
                }
                panel.append(levelTools);
            }

            const content = document.createElement("div");
            content.className = "workspace-content";

            if (!state) {
                if (this._screen === "ancestry") {
                    const p = document.createElement("ancestry-picker");
                    if (this._mode === "random") {
                        p.nextLabel = "Generuj";
                    }
                    p.addEventListener("choose-ancestry", (e) => {
                        this._ancestry = e.detail.ancestry;
                        if (this._mode === "manual") this.store.start("manual", this._ancestry);
                        else {
                            this.store.start("random", this._ancestry, {targetLevel: this._lvl, paths: this._buildPaths()});
                        }
                    });
                    p.addEventListener("back", () => {
                        this._lvl = 0;
                        this.store.reset();
                        this._screen = "menu";
                        this.render();
                        window.dispatchEvent(new CustomEvent("ui-screen-change"));
                    });
                    content.append(p);
                } else if (this._screen === "random-config") {
                    const c = document.createElement("random-config-screen");
                    c.chosenPaths = this._chosenPaths;
                    c.addEventListener("start", () => {
                        this.store.start("random", this._ancestry, {targetLevel: this._lvl, paths: this._buildPaths()});
                    });
                    c.addEventListener("back", () => {
                        this._screen = "ancestry";
                        this.render();
                    });
                    content.append(c);
                }
            } else {
                const awaiting = state.awaiting_path_pick;
                if (awaiting) {
                    const p = document.createElement("path-picker");
                    p.setAttribute("tier", awaiting);
                    content.append(p);
                } else if (state.level_choices && state.choice_cursor < state.total_choices_in_level) {
                    content.append(document.createElement("step-shell"));
                } else {
                    content.append(document.createElement("crossroads-screen"));
                }
            }
            panel.append(content);
            this.append(panel);
        }
    }

    // Initialize UI helpers
    const fab = document.getElementById("open-sheet-btn");
    const sheet = document.getElementById("pdf-panel");
    const toast = document.getElementById("event-toast");

    fab?.addEventListener("click", () => {
        const open = sheet.classList.toggle("drawer-open");
        fab.setAttribute("aria-expanded", String(open));
    });

    window.showWizardToast = (msg) => {
        if (!toast) return;
        toast.textContent = msg; toast.classList.add("visible");
        clearTimeout(window._t); window._t = setTimeout(() => toast.classList.remove("visible"), 3000);
    };

    window.customElements.define("progress-navigator", ProgressNavigator);
    window.customElements.define("main-menu", MainMenu);
    window.customElements.define("ancestry-picker", AncestryPicker);
    window.customElements.define("step-shell", StepShell);
    window.customElements.define("path-picker", PathPicker);
    window.customElements.define("crossroads-screen", CrossroadsScreen);
    window.customElements.define("random-config-screen", RandomConfigScreen);
    window.customElements.define("wizard-shell", WizardShell);
})();
