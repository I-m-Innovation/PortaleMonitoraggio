document.addEventListener("DOMContentLoaded", () => {
    const buttons = Array.from(document.querySelectorAll(".category-button[data-group][data-target]"));
    const panels = Array.from(document.querySelectorAll("[data-panel]"));
    const modal = document.getElementById("fv-form-modal");
    const modalOpenButtons = Array.from(document.querySelectorAll("[data-modal-open]"));
    const modalCloseButtons = Array.from(document.querySelectorAll("[data-modal-close]"));
    const formPanels = Array.from(document.querySelectorAll("[data-form-panel]"));
    const modalTitle = document.getElementById("fv-form-modal-title");
    const fvAddButtons = Array.from(document.querySelectorAll("[data-add-button-for]"));
    const tableTracks = Array.from(document.querySelectorAll(".table-scroll-track[data-auto-scroll='true']"));

    const modalTitles = {
        fv_clienti: "Nuovo Record FV Clienti",
        fv_proprieta: "Nuovo Record FV Proprieta",
        fv_in_costruzione: "Nuovo Record FV In Costruzione",
        fv_ppu: "Nuovo Record FV PPU",
    };

    const setFvAddButtons = (activeTargetId = "") => {
        fvAddButtons.forEach((btn) => {
            const isActive = btn.dataset.addButtonFor === activeTargetId;
            btn.hidden = !isActive;
            btn.disabled = !isActive;
        });
    };

    const updateStickyOffsets = () => {
        tableTracks.forEach((track) => {
            const table = track.querySelector("table");
            if (!table) {
                return;
            }
            const firstCell = table.querySelector("thead tr:last-child th:nth-child(1), tbody tr td:nth-child(1)");
            const firstWidth = firstCell ? firstCell.getBoundingClientRect().width : 0;
            table.style.setProperty("--sticky-left-2", `${Math.ceil(firstWidth)}px`);
        });
    };

    const createAutoScroller = (track) => {
        const panel = track.closest("[data-panel]");
        const state = {
            direction: 1,
            userPauseUntil: 0,
            edgePauseUntil: 0,
            hasOverflow: false,
            maxScroll: 0,
            lastTs: 0,
            rafId: null,
        };

        const SPEED_PX_PER_SEC = 60; 
        const END_PAUSE_MS = 2000;
        const USER_PAUSE_MS = 5000;

        const refresh = () => {
            const table = track.querySelector("table");
            const contentWidth = table ? table.scrollWidth : track.scrollWidth;
            state.maxScroll = Math.max(0, contentWidth - track.clientWidth);
            state.hasOverflow = state.maxScroll > 2;

            if (!state.hasOverflow) {
                state.direction = 1;
                track.scrollLeft = 0;
                state.lastTs = 0;
                state.edgePauseUntil = 0;
            } else if (track.scrollLeft > state.maxScroll) {
                track.scrollLeft = state.maxScroll;
            } else if (track.scrollLeft <= 0) {
                state.direction = 1;
            } else if (track.scrollLeft >= state.maxScroll) {
                state.direction = -1;
            }
        };

        const pauseForUser = () => {
            state.userPauseUntil = performance.now() + USER_PAUSE_MS;
            state.lastTs = 0;
        };

        const tick = (now) => {
            const isVisible = !panel || !panel.hidden;
            if (!state.hasOverflow || !isVisible) {
                state.lastTs = 0;
                state.rafId = requestAnimationFrame(tick);
                return;
            }

            if (now < state.userPauseUntil || now < state.edgePauseUntil) {
                state.lastTs = 0;
                state.rafId = requestAnimationFrame(tick);
                return;
            }

            if (!state.lastTs) {
                state.lastTs = now;
                state.rafId = requestAnimationFrame(tick);
                return;
            }

            const dtSec = Math.min(0.05, (now - state.lastTs) / 1000);
            state.lastTs = now;

            const prev = track.scrollLeft;
            const desired = prev + state.direction * SPEED_PX_PER_SEC * dtSec;
            const next = Math.max(0, Math.min(state.maxScroll, desired));
            track.scrollLeft = next;

            // Edge reached (or rounded to same pixel): reverse and pause briefly.
            if (Math.abs(track.scrollLeft - prev) < 0.5) {
                state.direction *= -1;
                state.edgePauseUntil = now + END_PAUSE_MS;
                state.lastTs = 0;
            }

            state.rafId = requestAnimationFrame(tick);
        };

        track.addEventListener("wheel", pauseForUser, { passive: true });
        track.addEventListener("touchstart", pauseForUser, { passive: true });
        track.addEventListener("mousedown", pauseForUser);
        track.addEventListener("focusin", pauseForUser);

        refresh();
        state.rafId = requestAnimationFrame(tick);
        return { refresh };
    };

    const autoScrollControllers = tableTracks.map((track) => createAutoScroller(track));

    const refreshTables = () => {
        updateStickyOffsets();
        autoScrollControllers.forEach((controller) => controller.refresh());
    };

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
        if (group === "fv") {
            setFvAddButtons("");
        }
        requestAnimationFrame(refreshTables);
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

        if (group === "fv") {
            setFvAddButtons(targetId);
        }
        requestAnimationFrame(refreshTables);
        setTimeout(refreshTables, 60);
        setTimeout(refreshTables, 180);
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

    setFvAddButtons("");
    refreshTables();
    window.addEventListener("resize", refreshTables);

    if (!modal) {
        return;
    }

    const setActiveFormPanel = (formType) => {
        formPanels.forEach((panel) => {
            panel.hidden = panel.dataset.formPanel !== formType;
        });
        if (modalTitle) {
            modalTitle.textContent = modalTitles[formType] || "Nuovo Record FV";
        }
    };

    const openModal = (formType) => {
        setActiveFormPanel(formType);
        modal.hidden = false;
        document.body.classList.add("modal-open");
    };

    const closeModal = () => {
        modal.hidden = true;
        document.body.classList.remove("modal-open");
    };

    modalOpenButtons.forEach((button) => {
        button.addEventListener("click", () => {
            const formType = button.dataset.modalOpen;
            if (formType) {
                openModal(formType);
            }
        });
    });

    modalCloseButtons.forEach((button) => {
        button.addEventListener("click", closeModal);
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !modal.hidden) {
            closeModal();
        }
    });

    const initialFormType = modal.dataset.openOnLoad;
    if (initialFormType) {
        openModal(initialFormType);
    }
});
