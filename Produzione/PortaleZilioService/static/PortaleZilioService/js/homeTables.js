document.addEventListener("DOMContentLoaded", () => {
    const buttons = Array.from(document.querySelectorAll(".category-button[data-group][data-target]"));
    const panels = Array.from(document.querySelectorAll("[data-panel]"));
    const syncBanner = document.querySelector("[data-sync-banner]");
    const groupAutoScrollButtons = new Map(
        Array.from(document.querySelectorAll("[data-group-auto-scroll-toggle]")).map((button) => [
            button.dataset.groupAutoScrollToggle,
            button,
        ])
    );

    let tableTracks = [];
    let autoScrollControllers = [];
    const autoScrollPreferenceByPanel = new Map();

    const syncPanelMap = {
        fv_clienti: "fv-clienti",
        fv_proprieta: "fv-proprieta",
        fv_agrivoltaico: "fv-agrivoltaico",
        fv_costruzione: "fv-costruzione",
        fv_ppu: "fv-ppu",
        idr_gse: "idr-gse",
        idr_proprieta: "idr-proprieta",
    };
    let bannerTimeoutId = null;

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

    const getTrackPreferenceKey = (track, index) => {
        const panel = track.closest("[data-panel]");
        if (panel?.id) {
            return panel.id;
        }
        return track.dataset.autoScrollKey || `table-track-${index}`;
    };

    const createAutoScroller = (track) => {
        const panel = track.closest("[data-panel]");
        const preferenceKey = track.dataset.autoScrollPreferenceKey || "";
        const state = {
            direction: 1,
            userPauseUntil: 0,
            edgePauseUntil: 0,
            hasOverflow: false,
            maxScroll: 0,
            lastTs: 0,
            rafId: null,
            isStopped: autoScrollPreferenceByPanel.get(preferenceKey) ?? false,
        };

        const SPEED_PX_PER_SEC = 30;
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

        const moveScroll = (delta) => {
            if (!state.hasOverflow || !Number.isFinite(delta) || delta === 0) {
                return false;
            }

            const prev = track.scrollLeft;
            const next = Math.max(0, Math.min(state.maxScroll, prev + delta));
            track.scrollLeft = next;

            if (Math.abs(next - prev) < 0.5) {
                return false;
            }

            state.direction = delta > 0 ? 1 : -1;
            state.edgePauseUntil = 0;
            return true;
        };

        const handleWheel = (event) => {
            pauseForUser();

            const dominantDelta = Math.abs(event.deltaX) > Math.abs(event.deltaY)
                ? event.deltaX
                : event.deltaY;

            if (!moveScroll(dominantDelta)) {
                return;
            }

            event.preventDefault();
        };

        const tick = (now) => {
            const isVisible = !panel || !panel.hidden;
            if (!state.hasOverflow || !isVisible || state.isStopped) {
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

            if (Math.abs(track.scrollLeft - prev) < 0.5) {
                state.direction *= -1;
                state.edgePauseUntil = now + END_PAUSE_MS;
                state.lastTs = 0;
            }

            state.rafId = requestAnimationFrame(tick);
        };

        track.addEventListener("wheel", handleWheel, { passive: false });
        track.addEventListener("touchstart", pauseForUser, { passive: true });
        track.addEventListener("mousedown", pauseForUser);
        track.addEventListener("focusin", pauseForUser);

        refresh();
        state.rafId = requestAnimationFrame(tick);
        return {
            refresh,
            isStopped: () => state.isStopped,
            setStopped: (isStopped) => {
                state.isStopped = Boolean(isStopped);
                state.lastTs = 0;
                if (preferenceKey) {
                    autoScrollPreferenceByPanel.set(preferenceKey, state.isStopped);
                }
            },
            stop: () => {
                if (state.rafId !== null) {
                    cancelAnimationFrame(state.rafId);
                }
            },
        };
    };

    const getVisiblePanelForGroup = (group) => (
        panels.find((panel) => panel.dataset.group === group && !panel.hidden) || null
    );

    const getControllerEntryForPanel = (panel) => {
        if (!panel) {
            return null;
        }
        return autoScrollControllers.find((entry) => entry.panelId === panel.id) || null;
    };

    const syncGroupAutoScrollToggle = (group) => {
        const button = groupAutoScrollButtons.get(group);
        if (!button) {
            return;
        }

        const visiblePanel = getVisiblePanelForGroup(group);
        const controllerEntry = getControllerEntryForPanel(visiblePanel);
        if (!controllerEntry) {
            button.hidden = true;
            button.onclick = null;
            return;
        }

        const { controller } = controllerEntry;
        const syncButtonState = () => {
            const isStopped = controller.isStopped();
            button.hidden = false;
            button.textContent = isStopped ? "Riavvia scorrimento" : "Stop scorrimento";
            button.setAttribute("aria-pressed", String(isStopped));
            button.classList.toggle("is-stopped", isStopped);
        };

        button.onclick = () => {
            controller.setStopped(!controller.isStopped());
            syncButtonState();
        };

        syncButtonState();
    };

    const syncAllGroupAutoScrollToggles = () => {
        groupAutoScrollButtons.forEach((_, group) => {
            syncGroupAutoScrollToggle(group);
        });
    };

    const rebuildTableControllers = () => {
        autoScrollControllers.forEach((entry) => entry.controller.stop());
        tableTracks = Array.from(document.querySelectorAll(".table-scroll-track[data-auto-scroll='true']"));
        autoScrollControllers = tableTracks.map((track, index) => {
            track.dataset.autoScrollPreferenceKey = getTrackPreferenceKey(track, index);
            const controller = createAutoScroller(track);
            const panel = track.closest("[data-panel]");
            return {
                track,
                panelId: panel?.id || "",
                controller,
            };
        });
        syncAllGroupAutoScrollToggles();
    };

    const refreshTables = () => {
        updateStickyOffsets();
        autoScrollControllers.forEach((entry) => entry.controller.refresh());
    };

    const setBannerState = (message, state) => {
        if (!syncBanner) {
            return;
        }
        if (bannerTimeoutId) {
            clearTimeout(bannerTimeoutId);
            bannerTimeoutId = null;
        }
        syncBanner.textContent = message;
        syncBanner.hidden = false;
        syncBanner.classList.remove("is-pending", "is-success", "is-error");
        if (state) {
            syncBanner.classList.add(state);
        }
        if (state === "is-success") {
            bannerTimeoutId = window.setTimeout(() => {
                syncBanner.hidden = true;
                bannerTimeoutId = null;
            }, 3000);
        }
    };

    const getCsrfToken = () => {
        const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : "";
    };

    const bindConstructionCategorySelects = () => {
        const endpoint = syncBanner?.dataset.fvConstructionCategoryUrl || "";
        if (!endpoint) {
            return;
        }

        document.querySelectorAll("[data-fv-construction-category]").forEach((select) => {
            if (select.dataset.bound === "true") {
                return;
            }
            select.dataset.bound = "true";
            select.dataset.lastValue = select.value || "";

            select.addEventListener("change", async () => {
                const previousValue = select.dataset.lastValue || "";
                const selectedValue = select.value;
                if (!selectedValue) {
                    select.value = previousValue;
                    return;
                }

                select.disabled = true;
                try {
                    const formData = new FormData();
                    formData.append("impianto_id", select.dataset.impiantoId || "");
                    formData.append("categoria_fv", selectedValue);

                    const response = await fetch(endpoint, {
                        method: "POST",
                        headers: {
                            "X-CSRFToken": getCsrfToken(),
                            "X-Requested-With": "XMLHttpRequest",
                        },
                        body: formData,
                    });
                    const payload = await response.json();
                    if (!response.ok || !payload.ok) {
                        throw new Error(payload.message || "Aggiornamento categoria non riuscito.");
                    }
                    select.dataset.lastValue = selectedValue;
                } catch (error) {
                    select.value = previousValue;
                    setBannerState(error.message || "Errore durante l'aggiornamento categoria.", "is-error");
                } finally {
                    select.disabled = false;
                }
            });
        });
    };

    const applyUpdatedTables = (tables) => {
        Object.entries(syncPanelMap).forEach(([payloadKey, panelId]) => {
            if (!tables[payloadKey]) {
                return;
            }
            const panel = document.getElementById(panelId);
            if (!panel) {
                return;
            }
            panel.innerHTML = tables[payloadKey];
        });

        rebuildTableControllers();
        bindConstructionCategorySelects();
        requestAnimationFrame(refreshTables);
        setTimeout(refreshTables, 60);
        setTimeout(refreshTables, 180);
        document.dispatchEvent(new CustomEvent("portalezilio:tables-updated"));
    };

    const triggerProviderMetricsSync = async () => {
        if (!syncBanner || !syncBanner.dataset.syncUrl) {
            return;
        }

        setBannerState("Aggiornamento metriche provider in corso...", "is-pending");

        try {
            const response = await fetch(syncBanner.dataset.syncUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCsrfToken(),
                    "X-Requested-With": "XMLHttpRequest",
                },
                body: JSON.stringify({}),
            });

            const payload = await response.json();
            if (!response.ok || !payload.ok) {
                throw new Error(payload.message || "Sync metriche provider non riuscito.");
            }

            applyUpdatedTables(payload.tables || {});
            setBannerState(payload.message || "Aggiornamento metriche provider completato.", "is-success");
        } catch (error) {
            setBannerState(error.message || "Errore durante l'aggiornamento delle metriche provider.", "is-error");
        }
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
        syncGroupAutoScrollToggle(group);
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

        syncGroupAutoScrollToggle(group);
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

    rebuildTableControllers();
    bindConstructionCategorySelects();
    const defaultFvButton = document.getElementById("clienti-tab-button");
    if (defaultFvButton) {
        activateButton(defaultFvButton);
    }
    syncAllGroupAutoScrollToggles();
    refreshTables();
    window.addEventListener("resize", refreshTables);
    triggerProviderMetricsSync();
});
