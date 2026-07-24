// Función para crear paginación en tablas
function setupPagination(tableSelector, rowsPerPage = 15) {
    const tables = document.querySelectorAll(tableSelector);

    tables.forEach(table => {
        const tbody = table.querySelector('tbody');
        if (!tbody) return;

        const rows = Array.from(tbody.querySelectorAll('tr'));
        if (rows.length <= rowsPerPage) return; // No necesita paginación

        const totalPages = Math.ceil(rows.length / rowsPerPage);
        let currentPage = 1;

        // Crear contenedor de paginación
        const paginationContainer = document.createElement('div');
        paginationContainer.className = 'pagination-container';
        table.parentElement.insertAdjacentElement('afterend', paginationContainer);

        // Info de paginación
        const paginationInfo = document.createElement('div');
        paginationInfo.className = 'pagination-info';
        paginationContainer.appendChild(paginationInfo);

        // Controles de paginación
        const paginationControls = document.createElement('div');
        paginationControls.className = 'pagination-controls';
        paginationContainer.appendChild(paginationControls);

        // Guardar referencias a los botones
        const pageButtons = {};

        // Función para mostrar página
        function showPage(page) {
            currentPage = page;
            const startIndex = (page - 1) * rowsPerPage;
            const endIndex = startIndex + rowsPerPage;

            // Mostrar/ocultar filas
            rows.forEach((row, index) => {
                row.style.display = index >= startIndex && index < endIndex ? '' : 'none';
            });

            // Actualizar info
            paginationInfo.textContent = `Página ${page} de ${totalPages} (${rows.length} registros)`;

            // Actualizar botones activos
            Object.keys(pageButtons).forEach(pageNum => {
                pageButtons[pageNum].classList.toggle('active', pageNum == page);
            });
        }

        // Botón anterior
        const prevBtn = document.createElement('button');
        prevBtn.textContent = '← Anterior';
        prevBtn.type = 'button';
        prevBtn.onclick = (e) => {
            e.preventDefault();
            if (currentPage > 1) showPage(currentPage - 1);
        };
        paginationControls.appendChild(prevBtn);

        // Botones de página
        for (let i = 1; i <= totalPages; i++) {
            const btn = document.createElement('button');
            btn.textContent = i;
            btn.type = 'button';
            btn.dataset.page = i;
            btn.onclick = (e) => {
                e.preventDefault();
                showPage(i);
            };
            if (i === 1) btn.classList.add('active');
            pageButtons[i] = btn;
            paginationControls.appendChild(btn);
        }

        // Botón siguiente
        const nextBtn = document.createElement('button');
        nextBtn.textContent = 'Siguiente →';
        nextBtn.type = 'button';
        nextBtn.onclick = (e) => {
            e.preventDefault();
            if (currentPage < totalPages) showPage(currentPage + 1);
        };
        paginationControls.appendChild(nextBtn);

        // Mostrar primera página
        showPage(1);
    });
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    setupPagination('.table-paginated', 15);
});
