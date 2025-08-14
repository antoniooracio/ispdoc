// Importa as funções necessárias dos outros módulos
import { conectarPortas, loadMapData } from './mapa-api.js';
import { atualizarMapa } from './mapa-render.js';

// A função principal que será exportada e chamada pelo mapa.js
export function initializeMap() {
    let editorObservacao;

    // Inicializa o editor de texto CKEditor
    ClassicEditor
        .create(document.querySelector('#observacao'))
        .then(editor => {
            editorObservacao = editor;
            // Estilização do editor pode ser movida para o CSS se preferir
            const editable = editor.ui.view.editable.element;
            editable.style.minHeight = '150px';
            editable.style.backgroundColor = '#ffffff';
            editable.style.color = '#000000';
        })
        .catch(error => console.error('Erro ao inicializar o editor:', error));

    // CORREÇÃO: Adiciona o evento para CARREGAR OS DADOS ao selecionar uma empresa
    document.getElementById('empresa-selector').addEventListener('change', (event) => {
        loadMapData(event.target.value);
    });

    // Evento para fechar o modal do equipamento
    document.getElementById('closeModal').addEventListener('click', () => {
        document.getElementById('modalEquipamento').classList.remove('show');
        document.getElementById('modalOverlay').style.display = 'none';
    });

    // Evento para o botão de conectar portas
    document.getElementById('conectar').addEventListener('click', function(event) {
        event.preventDefault();
        const portaOrigemId = document.getElementById('porta-dropdown').value;
        const portaDestinoId = document.getElementById('porta-destino-dropdown').value;
        const observacao = editorObservacao ? editorObservacao.getData() : '';
        if (portaOrigemId && portaDestinoId) {
            conectarPortas(portaOrigemId, portaDestinoId, observacao);
        } else {
            alert('Por favor, selecione as portas de origem e destino.');
        }
    });

    // Evento para fechar o modal de conexão
    document.getElementById('closeModalConexao').addEventListener('click', () => {
        document.getElementById('portaModal').style.display = "none";
    });

    // Evento para carregar as portas de destino quando um equipamento é selecionado
    document.getElementById('equipamento-dropdown').addEventListener('change', function() {
        const equipamentoId = this.value;
        if (!equipamentoId) return;

        fetch(`/api/portas?equipamento_id=${equipamentoId}`)
            .then(response => response.json())
            .then(data => {
                const portaDestinoDropdown = document.getElementById('porta-destino-dropdown');
                portaDestinoDropdown.innerHTML = '<option value="">Selecione uma porta</option>';
                data.forEach(porta => {
                    const option = document.createElement('option');
                    option.value = porta.id;
                    option.textContent = `${porta.nome} - ${porta.tipo} - ${porta.speed}`;
                    portaDestinoDropdown.appendChild(option);
                });
            })
            .catch(error => console.error('Erro ao buscar portas de destino:', error));
    });

    // Define um intervalo para atualizar o mapa a cada 30 segundos
    setInterval(() => {
        const empresaId = document.getElementById('empresa-selector').value;
        if (empresaId) {
            console.log("Atualizando mapa periodicamente...");
            atualizarMapa(empresaId);
        }
    }, 30000);

    console.log("Mapa inicializado e eventos configurados!");
}