document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.getElementById('searchInput');
    const cpfCnpjFilter = document.getElementById('cpfCnpjFilter');
    const statusFilter = document.getElementById('statusFilter');
    const cityFilter = document.getElementById('cityFilter');
    const clientContainers = document.querySelectorAll('.client-container');

    function filterClients() {
        const searchTerm = searchInput.value.toLowerCase();
        const cpfCnpjTerm = cpfCnpjFilter.value.replace(/[^\d]/g, '');
        const selectedStatus = statusFilter.value.toLowerCase();
        const selectedCity = cityFilter.value.toLowerCase();

        let hasResults = false;

        clientContainers.forEach(container => {
            const clientRazaoSocial = container.dataset.razaoSocial.toLowerCase();
            const clientCpfCnpj = container.dataset.cpfCnpj.replace(/[^\d]/g, '');
            const clientStatus = container.dataset.status.toLowerCase();
            const clientCity = container.dataset.city.toLowerCase();

            const matchesSearch = !searchTerm || clientRazaoSocial.includes(searchTerm);
            const matchesCpfCnpj = !cpfCnpjTerm || clientCpfCnpj.includes(cpfCnpjTerm);
            const matchesStatus = !selectedStatus || clientStatus === selectedStatus;
            const matchesCity = !selectedCity || clientCity === selectedCity;

            if (matchesSearch && matchesCpfCnpj && matchesStatus && matchesCity) {
                container.style.display = '';
                hasResults = true;
            } else {
                container.style.display = 'none';
            }
        });

        const noResultsMessage = document.getElementById('noResultsMessage');
        if (!hasResults) {
            if (!noResultsMessage) {
                const message = document.createElement('div');
                message.id = 'noResultsMessage';
                message.classList.add('no-results-message');
                message.innerText = 'Nenhum cliente encontrado.';
                document.getElementById('clientList').appendChild(message);
            }
        } else {
            if (noResultsMessage) {
                noResultsMessage.remove();
            }
        }
    }

    searchInput.addEventListener('keyup', filterClients);
    cpfCnpjFilter.addEventListener('keyup', filterClients);
    statusFilter.addEventListener('change', filterClients);
    cityFilter.addEventListener('change', filterClients);
});
