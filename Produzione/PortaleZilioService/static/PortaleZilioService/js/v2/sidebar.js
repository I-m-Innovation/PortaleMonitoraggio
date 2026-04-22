document.querySelectorAll('.tree-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
        btn.closest('.tree-item').classList.toggle('open');
    });
});
