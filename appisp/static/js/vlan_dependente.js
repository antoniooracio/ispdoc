document.addEventListener('DOMContentLoaded', function () {

    function configurarEventoEmpresa() {
        const empresaSelect = document.querySelector('#id_empresa');
        const equipamentoSelect = document.querySelector('#id_equipamento');

        if (!empresaSelect) {
            console.log('Campo de empresa não encontrado no DOM.');
            return;
        }
        if (!equipamentoSelect) {
            console.log('Campo de equipamento não encontrado no DOM.');
            return;
        }


        // Remove o atributo aria-hidden do select para evitar o erro no console
        empresaSelect.removeAttribute('aria-hidden');

        // Aguarda o Select2 estar pronto e adiciona evento ao campo real
        $(empresaSelect).on('change', function () {
            const empresaId = $(this).val(); // Obtém o valor do Select2 corretamente

            if (empresaId) {
                fetch(`/get-equipamentos/?empresa_id=${empresaId}`)
                    .then(response => response.json())
                    .then(data => {
                        equipamentoSelect.innerHTML = '<option value="">---------</option>';
                        data.forEach(function (equipamento) {
                            const option = document.createElement('option');
                            option.value = equipamento.id;
                            option.textContent = equipamento.nome;
                            equipamentoSelect.appendChild(option);
                        });

                        // Atualiza o Select2 no campo equipamento
                        $(equipamentoSelect).trigger('change.select2');
                    })
                    .catch(error => console.error('Erro ao buscar equipamentos:', error));
            } else {
                equipamentoSelect.innerHTML = '<option value="">---------</option>';
                $(equipamentoSelect).trigger('change.select2');
            }
        });
    }

    // Garante que o Select2 esteja carregado antes de configurar os eventos
    if ($.fn.select2) {
        configurarEventoEmpresa();
    } else {
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
