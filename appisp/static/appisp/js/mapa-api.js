// Importa as funções para atualizar o estado e renderizar o mapa
import { setNodes, setLinks, setUserIsAdmin } from './mapa-state.js';
import { renderMapa } from './mapa-render.js';

// Função para carregar os dados iniciais do mapa
export async function loadMapData(empresaId) {
    if (!empresaId) {
        setNodes([]);
        setLinks([]);
        renderMapa();
        return;
    }

    try {
        const response = await fetch(`/api/mapa-dados?empresa_id=${empresaId}`);
        if (!response.ok) {
            throw new Error(`Erro na API: ${response.statusText}`);
        }
        const data = await response.json();

        setNodes(data.nodes || []);
        setLinks(data.links || []);
        setUserIsAdmin(data.user_is_admin || false);

        renderMapa();

    } catch (error) {
        console.error("Erro ao carregar dados do mapa:", error);
        alert("Não foi possível carregar os dados do mapa.");
    }
}

// Função para conectar portas, com a palavra-chave 'export'
export function conectarPortas(portaOrigemId, portaDestinoId, observacao) {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    fetch('/api/conectar-portas/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            porta_origem_id: portaOrigemId,
            porta_destino_id: portaDestinoId,
            observacao: observacao
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Conexão criada com sucesso!');
            document.getElementById('portaModal').style.display = 'none';
            const empresaId = document.getElementById('empresa-selector').value;
            loadMapData(empresaId); // Recarrega os dados para mostrar a nova conexão
        } else {
            alert('Erro ao criar conexão: ' + (data.error || 'Erro desconhecido'));
        }
    })
    .catch(error => {
        console.error('Erro na requisição para conectar portas:', error);
        alert('Ocorreu um erro de comunicação ao tentar criar a conexão.');
    });
}