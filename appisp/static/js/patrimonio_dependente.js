document.addEventListener('DOMContentLoaded', function() {
    // Usamos o seletor de ID do Django para os campos
    const empresaSelect = document.querySelector('#id_empresa');
    const equipamentoSelect = document.querySelector('#id_equipamento');
    const localizacaoSelect = document.querySelector('#id_localizacao');

    if (!empresaSelect || !equipamentoSelect || !localizacaoSelect) {
        console.error("Um ou mais campos (empresa, equipamento, localizacao) não foram encontrados.");
        return;
    }

    function carregarOpcoes(selectElement, url) {
        fetch(url)
            .then(response => response.json())
            .then(data => {
                // Guarda o valor selecionado atualmente, se houver
                const selectedValue = selectElement.value;
                
                // Limpa as opções existentes
                selectElement.innerHTML = '<option value="">---------</option>';

                // Adiciona as novas opções
                data.forEach(item => {
                    const option = new Option(item.nome, item.id);
                    selectElement.add(option);
                });

                // Tenta restaurar o valor selecionado
                selectElement.value = selectedValue;
            });
    }

    empresaSelect.addEventListener('change', function() {
        const empresaId = this.value;
        carregarOpcoes(equipamentoSelect, `/get-equipamentos/?empresa_id=${empresaId}`);
        carregarOpcoes(localizacaoSelect, `/get-pops/?empresa_id=${empresaId}`); // Precisaremos criar esta URL
    });
});