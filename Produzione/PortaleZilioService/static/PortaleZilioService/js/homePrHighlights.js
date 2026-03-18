document.addEventListener("DOMContentLoaded", () => {
    const ALERT_COLOR = "#c73a3a";
    const CELL_SELECTOR = ".js-pr-ultimi-12-mesi";

    const parsePercent = (rawValue) => {
        if (!rawValue) {
            return null;
        }

        let normalized = String(rawValue).replace("%", "").trim();
        if (!normalized || normalized === "--") {
            return null;
        }

        if (normalized.includes(",") && !normalized.includes(".")) {
            normalized = normalized.replace(",", ".");
        } else {
            normalized = normalized.replace(/,/g, "");
        }

        const parsed = Number.parseFloat(normalized);
        return Number.isFinite(parsed) ? parsed : null;
    };

    const applyPrHighlights = () => {
        document.querySelectorAll(CELL_SELECTOR).forEach((cell) => {
            const prValue = parsePercent(cell.textContent);
            if (prValue !== null && prValue > 100) {
                cell.style.color = ALERT_COLOR;
                cell.style.fontWeight = "700";
            } else {
                cell.style.removeProperty("color");
                cell.style.removeProperty("font-weight");
            }
        });
    };

    applyPrHighlights();
    document.addEventListener("portalezilio:tables-updated", applyPrHighlights);
});
