document.addEventListener("DOMContentLoaded", () => {
    const infoToggle = document.querySelector("[data-overview-info-toggle]");
    const infoPanel = document.querySelector("[data-overview-info-panel]");
    const infoClose = document.querySelector("[data-overview-info-close]");

    const setInfoPanelOpen = (isOpen) => {
        if (!infoToggle || !infoPanel) {
            return;
        }
        infoToggle.setAttribute("aria-expanded", String(isOpen));
        infoPanel.hidden = !isOpen;
    };

    if (!infoToggle || !infoPanel) {
        return;
    }

    infoToggle.addEventListener("click", () => {
        const isOpen = infoToggle.getAttribute("aria-expanded") === "true";
        setInfoPanelOpen(!isOpen);
    });

    if (infoClose) {
        infoClose.addEventListener("click", () => {
            setInfoPanelOpen(false);
        });
    }

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            setInfoPanelOpen(false);
        }
    });

    document.addEventListener("click", (event) => {
        const target = event.target;
        if (!(target instanceof Node)) {
            return;
        }
        if (infoPanel.hidden) {
            return;
        }
        if (infoPanel.contains(target) || infoToggle.contains(target)) {
            return;
        }
        setInfoPanelOpen(false);
    });
});
