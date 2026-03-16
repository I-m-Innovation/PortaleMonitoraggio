document.addEventListener('DOMContentLoaded', function () {
    const selettoreAnno = document.getElementById('selettore-anno');
    const annoIniziale = 2021;
    const annoCorrente = new Date().getFullYear();

    if (!selettoreAnno) {
        return;
    }

    for (let anno = annoIniziale; anno <= annoCorrente; anno++) {
        const option = document.createElement('option');
        option.value = anno;
        option.textContent = anno;
        option.selected = anno === annoCorrente;
        selettoreAnno.appendChild(option);
    }
});
