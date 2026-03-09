document.addEventListener("DOMContentLoaded", () => {
    const buttons = Array.from(document.querySelectorAll(".category-button"));
    const panels = Array.from(document.querySelectorAll("[data-panel]"));

    const resetGroup = (group) => {
        panels.forEach((panel) => {
            if (panel.dataset.group === group) {
                panel.hidden = panel.id !== `${group}-empty`;
            }
        });
        buttons.forEach((button) => {
            if (button.dataset.group === group) {
                button.setAttribute("aria-pressed", "false");
                button.classList.remove("active");
            }
        });
    };

    const activateButton = (button) => {
        const group = button.dataset.group;
        const targetId = button.dataset.target;
        const targetPanel = document.getElementById(targetId);

        panels.forEach((panel) => {
            if (panel.dataset.group === group) {
                panel.hidden = panel !== targetPanel;
            }
        });

        buttons.forEach((btn) => {
            if (btn.dataset.group === group) {
                const isActive = btn === button;
                btn.setAttribute("aria-pressed", String(isActive));
                btn.classList.toggle("active", isActive);
            }
        });
    };

    buttons.forEach((button) => {
        button.addEventListener("click", () => {
            if (button.classList.contains("active")) {
                resetGroup(button.dataset.group);
                return;
            }
            activateButton(button);
        });
    });
});
