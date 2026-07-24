(function () {
    "use strict";
    const fab = document.getElementById("sheet-fab");
    const sheet = document.getElementById("pdf-panel");
    const toast = document.getElementById("event-toast");

    function toggleSheet() {
        if (!sheet || !fab) return;
        const open = sheet.classList.toggle("drawer-open");
        fab.setAttribute("aria-expanded", String(open));
    }
    window.showWizardToast = function (message) {
        if (!toast) return;
        toast.textContent = message;
        toast.classList.add("visible");
        window.clearTimeout(window.__toastTimer);
        window.__toastTimer = window.setTimeout(() => toast.classList.remove("visible"), 3500);
    };
    fab?.addEventListener("click", toggleSheet);
    document.querySelectorAll(".ancestry-item").forEach((tile) => {
        tile.setAttribute("tabindex", "0");
        tile.setAttribute("role", "button");
        tile.addEventListener("keydown", (event) => {
            if (event.key === "Enter" || event.key === " ") { event.preventDefault(); tile.click(); }
        });
    });
})();