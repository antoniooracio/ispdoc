import { nodes } from './mapa-state.js';

// Adiciona 'export' para que a função possa ser importada em outros arquivos
export function showModal(event, d) {
    fetch(`/api/equipamento/${d.id}/`)
        .then(response => response.json())
        .then(data => {
            // Preenche os campos do modal com os dados do equipamento
            document.getElementById('modalTitle').textContent = data.nome;
            document.getElementById('equipamentoId').value = data.id;
            document.getElementById('nome').value = data.nome;
            document.getElementById('tipo').value = data.tipo;
            document.getElementById('ip').value = data.ip_address;
            document.getElementById('usuario').value = data.usuario;
            document.getElementById('senha').value = data.senha;
            document.getElementById('status').value = data.status;
            
            // Mostra o modal
            document.getElementById('modalEquipamento').classList.add('show');
            document.getElementById('modalOverlay').style.display = 'block';
        })
        .catch(error => console.error('Erro ao buscar informações do equipamento:', error));
}

// Adiciona 'export'
export function mostrarInformacoesConexao(d) {
    const equipamentoFonte = nodes.find(node => node.id === d.source.id);
    const equipamentoDestino = nodes.find(node => node.id === d.target.id);
    const portaFonte = d.porta_origem || 'N/A';
    const portaDestino = d.porta_destino || 'N/A';
    const portaObs = d.Obs || 'N/A';

    document.querySelector('.modal-conexao-header').innerHTML = `<div class="d-flex align-items-center"><i class="bi bi-plug-fill me-2 text-warning"></i><h3 class="modal-title fw-bold text-warning mb-0">Conexão ${d.tipo}</h3></div>`;
    document.querySelector('.modal-conexao-body').innerHTML = `
        <div class="px-3 py-2">
            <div class="mb-2 row"><label class="col-sm-2 col-form-label"><strong>Velocidade:</strong></label><div class="col-sm-9"><input type="text" class="form-control" value="${d.speed}" readonly></div></div>
            <div class="mb-2 row"><label class="col-sm-2 col-form-label"><strong>Fonte:</strong></label><div class="col-sm-9"><input type="text" class="form-control" value="${equipamentoFonte.nome} (${portaFonte})" readonly></div></div>
            <div class="mb-2 row"><label class="col-sm-2 col-form-label"><strong>Destino:</strong></label><div class="col-sm-9"><input type="text" class="form-control" value="${equipamentoDestino.nome} (${portaDestino})" readonly></div></div>
            <div class="mb-2 row"><label class="col-sm-2 col-form-label"><strong>Obs.:</strong></label><div class="col-sm-9 border rounded bg-light p-2" style="min-height: 80px;">${portaObs}</div></div>
        </div>`;

    document.getElementById('modalConexao').classList.add('show');
    document.getElementById('modalOverlayConexao').style.display = 'block';

    const excluirBtn = document.getElementById('excluirConexaoBtn');
    if (excluirBtn) {
        excluirBtn.onclick = () => {
            if (confirm('Tem certeza que deseja excluir esta conexão?')) {
                // Adicionar chamada à API para excluir a conexão
                console.log(`Excluir conexão com porta de origem ID: ${d.porta_origem_id}`);
            }
        };
    }
}

// Adiciona 'export'
export function handleRightClick(event, equipamentoData) {
    event.preventDefault();
    const portaModal = document.getElementById('portaModal');
    portaModal.style.display = "block";
    
    const equipamentoDropdown = document.getElementById('equipamento-dropdown');
    const portaDropdown = document.getElementById('porta-dropdown');
    const portaDestinoDropdown = document.getElementById('porta-destino-dropdown');

    // Limpa dropdowns
    portaDropdown.innerHTML = '<option value="">Carregando...</option>';
    equipamentoDropdown.innerHTML = '<option value="">Selecione um equipamento</option>';
    portaDestinoDropdown.innerHTML = '<option value="">Selecione uma porta</option>';

    // Preenche dropdown de portas do equipamento de origem (clicado)
    fetch(`/api/portas?equipamento_id=${equipamentoData.id}`)
        .then(response => response.json())
        .then(portas => {
            portaDropdown.innerHTML = '<option value="">Selecione uma porta</option>';
            portas.forEach(porta => {
                const option = document.createElement('option');
                option.value = porta.id;
                option.textContent = `${porta.nome} - ${porta.tipo} - ${porta.speed}`;
                portaDropdown.appendChild(option);
            });
        });

    // Preenche dropdown de equipamentos da mesma empresa
    nodes.forEach(node => {
        if (node.id !== equipamentoData.id) { // Não lista o próprio equipamento
            const option = document.createElement('option');
            option.value = node.id;
            option.textContent = node.nome;
            equipamentoDropdown.appendChild(option);
        }
    });
}

// Esta função parece ser usada internamente, então não precisa de export
function toggleModalPassword(inputId, btn) {
    const input = document.getElementById(inputId);
    if (input.type === "password") {
        input.type = "text";
        btn.innerHTML = '<i class="fas fa-eye-slash"></i>';
    } else {
        input.type = "password";
        btn.innerHTML = '<i class="fas fa-eye"></i>';
    }
}