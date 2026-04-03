document.querySelectorAll("td[data-currency]").forEach(function(td) {
    var raw = td.getAttribute("data-currency");
    var val = parseFloat(raw);
    if (!isNaN(val)) {
        td.textContent = new Intl.NumberFormat("it-IT", {
            style: "currency",
            currency: "EUR",
        }).format(val);
    }
});
