document.addEventListener('DOMContentLoaded', function () {
    console.log('Script carregado corretamente!');

    function configurarEventoEmpresa() {
        const empresaSelect = document.querySelector('#id_empresa');
        const equipamentoSelect = document.querySelector('#id_equipamento');
        const portaSelect = document.querySelector('#id_porta');

        if (!empresaSelect || !equipamentoSelect || !portaSelect) {
            console.log('Algum campo não foi encontrado no DOM.');
            return;
        }

        console.log('Campo de empresa encontrado:', empresaSelect);

        $(empresaSelect).on('change', function () {
            const empresaId = $(this).val();
            console.log('Empresa Selecionada:', empresaId);

            if (empresaId) {
                fetch(`/get-equipamentos/?empresa_id=${empresaId}`)
                    .then(response => response.json())
                    .then(data => {
                        console.log('Equipamentos Recebidos:', data);
                        equipamentoSelect.innerHTML = '<option value="">---------</option>';
                        data.forEach(equipamento => {
                            const option = document.createElement('option');
                            option.value = equipamento.id;
                            option.textContent = equipamento.nome;
                            equipamentoSelect.appendChild(option);
                        });
                        $(equipamentoSelect).trigger('change.select2');
                    })
                    .catch(error => console.error('Erro ao buscar equipamentos:', error));
            } else {
                equipamentoSelect.innerHTML = '<option value="">---------</option>';
                $(equipamentoSelect).trigger('change.select2');
            }
        });

        $(equipamentoSelect).on('change', function () {
            const equipamentoId = $(this).val();
            console.log('Equipamento Selecionado:', equipamentoId);

            if (equipamentoId) {
                fetch(`/get-portas/?equipamento_id=${equipamentoId}`)
                    .then(response => response.json())
                    .then(data => {
                        console.log('Portas Recebidas:', data);
                        portaSelect.innerHTML = '<option value="">---------</option>';
                        data.forEach(porta => {
                            const option = document.createElement('option');
                            option.value = porta.id;
                            option.textContent = porta.nome;
                            portaSelect.appendChild(option);
                        });
                        $(portaSelect).trigger('change.select2');
                    })
                    .catch(error => console.error('Erro ao buscar portas:', error));
            } else {
                portaSelect.innerHTML = '<option value="">---------</option>';
                $(portaSelect).trigger('change.select2');
            }
        });
    }


    if ($.fn.select2) {
        configurarEventoEmpresa();
    } else {
        console.log('Aguardando carregamento do Select2...');
        const observer = new MutationObserver(() => {
            if ($.fn.select2) {
                console.log('Select2 detectado, inicializando script.');
                observer.disconnect();
                configurarEventoEmpresa();
            }
        });

        observer.observe(document.body, { childList: true, subtree: true });
    }
});
