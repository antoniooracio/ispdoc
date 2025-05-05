
document.addEventListener("DOMContentLoaded", function () {
    // ============================ //
    // 1. INICIALIZAÇÃO CKEDITOR   //
    // ============================ //
    let editorObservacao;

ClassicEditor
    .create(document.querySelector('#observacao'), {
        toolbar: ['bold', 'italic', 'link', 'bulletedList', 'numberedList', 'undo', 'redo']
    })
    .then(editor => {
        editorObservacao = editor;

        const editable = editor.ui.view.editable.element;
        editable.style.minHeight = '150px';
        editable.style.maxHeight = '300px';
        editable.style.overflowY = 'auto';
        editable.style.backgroundColor = '#ffffff';
        editable.style.color = '#000000';
        editable.style.border = '1px solid #6c757d';
    })
    .catch(error => {
        console.error('Erro ao inicializar o editor:', error);
    });

    // ============================ //
    // 2. SCRIPT PRINCIPAL DO MAPA //
    // ============================ //
    const userIsAdmin = window.userIsAdmin;
    const userIsSenha = window.userIsSenha;

    const nodes = window.nodes || [];
    const links = window.links || [];
    const mapa = d3.select('#mapa');

    let zoomTransform = d3.zoomIdentity; // Variável global para armazenar o estado do zoom

    async function atualizarMapa() {
        try {
            const response = await fetch('/api/get_map_data/');
            const data = await response.json();

            nodes.length = 0;
            links.length = 0;
            nodes.push(...data.nodes);
            links.push(...data.links);
        } catch (error) {
            console.error('Erro ao atualizar o mapa:', error);
        }
    }

function abrirPopupEquipamento(url) {
    const largura = 800;
    const altura = 600;
    const left = window.screenX + (window.innerWidth - largura) / 2;
    const top = window.screenY + (window.innerHeight - altura) / 2;

    const popup = window.open(
        url,
        "_popup",
        `width=${largura},height=${altura},top=${top},left=${left},resizable=yes,scrollbars=yes`
    );

    if (popup) {
        popup.focus();
    } else {
        alert("Por favor, permita popups para este site.");
    }
}
// Garante que fique global
window.abrirPopupEquipamento = abrirPopupEquipamento;

// Função para carregar as posições salvas
function carregarPosicoes() {
    const posicoesSalvas = localStorage.getItem('posicoesEquipamentos');
    if (posicoesSalvas) {
        const posicoes = JSON.parse(posicoesSalvas);
        nodes.forEach((node) => {
            const posicaoSalva = posicoes.find(p => p.id === node.id);
            if (posicaoSalva) {
                node.x = posicaoSalva.x;
                node.y = posicaoSalva.y;
            }
        });
    }
}

// Função para salvar as posições
function salvarPosicoes() {
    const posicoes = nodes.map(node => ({
        id: node.id,
        x: node.x,
        y: node.y
    }));
    localStorage.setItem('posicoesEquipamentos', JSON.stringify(posicoes));
}

function limparMapa() {
    d3.select("#mapa").selectAll("*").remove();
}

function renderMapa() {
    carregarPosicoes();

    const empresaId = document.getElementById('empresa-selector').value;

    // Filtrar os equipamentos pela empresa selecionada
    const equipamentosFiltrados = empresaId
        ? nodes.filter(equipamento => equipamento.empresa === parseInt(empresaId))
        : [];  // Quando não há empresa selecionada, não mostra nenhum equipamento

    // Filtrar as conexões pela empresa selecionada
    const conexoesFiltradas = empresaId
        ? links.filter(link => {
            const sourceEquipamento = nodes.find(node => node.id === link.source);
            const targetEquipamento = nodes.find(node => node.id === link.target);
            return (sourceEquipamento.empresa === parseInt(empresaId) && targetEquipamento.empresa === parseInt(empresaId));
        })
        : [];  // Quando não há empresa selecionada, não mostra nenhuma conexão

    // Salvar o estado do zoom antes de limpar o mapa
    const svgElement = d3.select('#mapa svg');
    if (!svgElement.empty()) {
        zoomTransform = d3.zoomTransform(svgElement.node());
    }

    mapa.selectAll('*').remove();  // Limpar mapa antes de renderizar

    const width = mapa.node().offsetWidth || 800;
    const height = mapa.node().offsetHeight || 600;

    const svg = mapa.append('svg')
        .attr('width', width)
        .attr('height', height);

    const g = svg.append('g');

    const zoom = d3.zoom()
        .scaleExtent([0.5, 3])
        .on('zoom', (event) => {
            g.attr('transform', event.transform);
            document.getElementById('zoom-slider').value = event.transform.k;
            zoomTransform = event.transform; // Atualizar a transformação do zoom
        });

    svg.call(zoom);

    // Restaurar o zoom anterior
    svg.call(zoom.transform, zoomTransform);

    // Conecta o slider ao zoom
    document.getElementById('zoom-slider').addEventListener('input', (event) => {
        const newZoom = parseFloat(event.target.value);
        svg.transition().duration(200).call(zoom.scaleTo, newZoom);
    });

    const drag = d3.drag()
        .on('start', dragStarted)
        .on('drag', dragged)
        .on('end', dragEnded);

    // Armazenar as conexões já criadas
    let conexoesCriadas = [];

    // Função para calcular uma curva entre os pontos de conexão
    function calcularCurva(x1, y1, x2, y2, index) {
        const offset = index * 5;  // Cada conexão terá um deslocamento diferente para a curvatura
        const controlX = (x1 + x2) / 2;
        const controlY = (y1 + y2) / 2 - offset;
        return [[x1, y1], [controlX, controlY], [x2, y2]];
    }

    // Criação de um mapa para contar as conexões entre os pares de equipamentos
    const conexaoContagem = {};

    // Função para contar conexões entre os pares de equipamentos
    function contarConexoes(link) {
        const key = `${Math.min(link.source, link.target)}-${Math.max(link.source, link.target)}`;
        if (conexaoContagem[key]) {
            conexaoContagem[key]++;
        } else {
            conexaoContagem[key] = 1;
        }
    }

    // Renderizar as linhas de conexão com curvaturas, agora filtradas pela empresa
    const linhasConexao = g.selectAll('.linha-conexao')
        .data(conexoesFiltradas)
        .enter()
        .filter(d => {
            const sourceId = d.source;
            const targetId = d.target;
            const portaOrigem = d.porta_origem;
            const portaDestino = d.porta_destino;

            // Verifica se essa conexão já foi criada (evita adicionar linha duplicada)
            const conexaoExistente = conexoesCriadas.some(conexao =>
                (conexao.source === sourceId && conexao.target === targetId && conexao.portaOrigem === portaOrigem && conexao.portaDestino === portaDestino) ||
                (conexao.source === targetId && conexao.target === sourceId && conexao.portaOrigem === portaDestino && conexao.portaDestino === portaOrigem)
            );

            if (!conexaoExistente) {
                // Adiciona a conexão ao array de conexões já criadas
                conexoesCriadas.push({ source: sourceId, target: targetId, portaOrigem, portaDestino });
                // Conta a conexão entre os dois equipamentos
                contarConexoes(d);
            }

            return !conexaoExistente;  // Retorna true para desenhar a linha apenas se a conexão ainda não foi criada
        })
        .append('path')
        .attr('class', 'linha-conexao')
        .attr('d', function (d, i) {
            const x1 = nodes.find(node => node.id === d.source).x;
            const y1 = nodes.find(node => node.id === d.source).y;
            const x2 = nodes.find(node => node.id === d.target).x;
            const y2 = nodes.find(node => node.id === d.target).y;

            const key = `${Math.min(d.source, d.target)}-${Math.max(d.source, d.target)}`;
            const conexaoCount = conexaoContagem[key];

            if (conexaoCount === 1) {
                // Se houver apenas uma conexão entre os equipamentos, a linha será reta
                return `M ${x1},${y1} L ${x2},${y2}`;
            }

            const direction = i % 2 === 0 ? 1 : -1; // Alternar entre cima e baixo
            const intensity = (Math.floor(i / 2) * 10) + 5; // Aumenta a curvatura progressivamente

            const cx = (x1 + x2) / 2;
            const cy = (y1 + y2) / 2 + (direction * intensity); // Ajuste do ponto de controle

            return `M ${x1},${y1} Q ${cx},${cy} ${x2},${y2}`; // Curva Bézier Quadrática
        })
        .attr('stroke', d => {
            switch (d.tipo) {
                case 'Fibra': return 'blue';
                case 'Eletrico': return 'green';
                case 'Radio': return 'orange';
                case 'Transporte': return 'brown';
                default: return 'gray';
            }
        })
        .attr('stroke-width', d => {
            const widthMap = {
                '10G': 3,
                '20G': 4,
                '40G': 5,
                '100G': 6
            };
            return widthMap[d.speed] || 2;
        })
        .attr('fill', 'none')
        .on('click', function (event, d) {
            console.log("🔌 Conexão clicada:", d);
            mostrarInformacoesConexao(d);
        });


function excluirConexao(portaId) {
    const empresaId = document.getElementById('empresa-selector').value;
    localStorage.setItem('empresaSelecionada', empresaId);

    fetch('/api/desconectar-portas/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ porta_id: portaId })  // <- Aqui está o nome correto esperado no backend
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Conexão excluída com sucesso!');
            // Esconde o modal antes de recarregar a página
            document.getElementById('modalConexao').classList.remove('show');
            document.getElementById('modalOverlayConexao').style.display = 'none';

            // Pequeno delay para garantir que o modal feche antes do reload
            setTimeout(() => {
            atualizarMapa();
            renderMapa();
            // Fecha o modal após sucesso
            document.getElementById('modalConexao').classList.remove('show');
            document.getElementById('modalOverlayConexao').style.display = 'none';
            }, 100);
        } else {
            alert('Erro ao excluir: ' + (data.error || 'Erro desconhecido.'));
        }
    })
    .catch(error => {
        console.error('Erro ao excluir conexão:', error);
        alert('Erro na requisição.');
    });
}

    // Renderizar os equipamentos
    const equipamentosG = g.selectAll('.equipamento')
        .data(equipamentosFiltrados)
        .enter().append('g')
        .attr('class', 'equipamento')
        .attr('transform', d => `translate(${d.x},${d.y})`)
        .call(drag)
        .on('click', function(event, d) {
            // Clique com o botão esquerdo (mantenha o evento original)
            if (userIsAdmin) {
                showModal(event, d);
            } else {
                alert("Você não tem permissão para visualizar essas informações.");
            }
        })
        .on('contextmenu', function(event, d) {
            // Clique com o botão direito do mouse
            handleRightClick(event, d);
        });

    // Renderiza os ícones no mapa
    equipamentosG.each(function(d) {
        const grupo = d3.select(this);

        if (d.tipo === "Transporte") {
            // Ícone de nuvem
            grupo.append('path')
                .attr('d', 'M20 10 A10 10 0 0 1 40 10 A10 10 0 0 1 60 10 A10 10 0 0 1 50 30 A10 10 0 0 1 30 30 A10 10 0 0 1 20 10 Z')
                .attr('fill', d.status === 'Ativo' ? '#4B0082' : 'red') // Roxo escuro
                .attr('transform', 'scale(0.9) translate(-30, -20)');

        } else if (d.tipo === "Switch") {
            // Quadrado
            grupo.append('rect')
                .attr('width', 30)
                .attr('height', 30)
                .attr('x', -15)
                .attr('y', -15)
                .attr('fill', d.status === 'Ativo' ? 'blue' : 'red');

        } else if (d.tipo === "Passivo") {
            // Triângulo
            grupo.append('path')
                .attr('d', 'M -15,15 L 15,15 L 0,-15 Z') // Desenha um triângulo
                .attr('fill', 'orange');

        } else if (d.tipo === "Servidor") {
            // Retângulo horizontal com linhas (simulando um rack de servidor)
            grupo.append('rect')
                .attr('width', 40)
                .attr('height', 20)
                .attr('x', -20)
                .attr('y', -10)
                .attr('fill', d.status === 'Ativo' ? 'gray' : 'red');

            // Linhas no servidor para simular baias
            grupo.append('line').attr('x1', -15).attr('y1', -5).attr('x2', 15).attr('y2', -5).attr('stroke', 'black');
            grupo.append('line').attr('x1', -15).attr('y1', 5).attr('x2', 15).attr('y2', 5).attr('stroke', 'black');

        } else if (d.tipo === "VMWARE") {
            // Retângulo horizontal com linhas (simulando um rack de servidor)
            grupo.append('rect')
                .attr('width', 40)
                .attr('height', 20)
                .attr('x', -20)
                .attr('y', -10)
                .attr('fill', d.status === 'Ativo' ? 'gray' : 'red');

            // Linhas no servidor para simular baias
            grupo.append('line').attr('x1', -15).attr('y1', -5).attr('x2', 15).attr('y2', -5).attr('stroke', 'black');
            grupo.append('line').attr('x1', -15).attr('y1', 5).attr('x2', 15).attr('y2', 5).attr('stroke', 'black');

        } else if (d.tipo === "Olt") {
            // Retângulo pequeno representando uma OLT
            grupo.append('rect')
                .attr('width', 35)
                .attr('height', 15)
                .attr('x', -17.5)
                .attr('y', -7.5)
                .attr('fill', d.status === 'Ativo' ? 'purple' : 'red');

            // Círculos representando portas ópticas
            for (let i = -10; i <= 10; i += 10) {
                grupo.append('circle')
                    .attr('cx', i)
                    .attr('cy', 5)
                    .attr('r', 2)
                    .attr('fill', 'yellow');
            }

            } else {
                // Círculo para os demais tipos
                grupo.append('circle')
                    .attr('r', 20)
                    .attr('fill', d.status === 'Ativo' ? 'green' : 'red'); // Roxo escuro para ativo

                // Adiciona o "X" dentro do círculo
                grupo.append('line')
                    .attr('x1', -10)
                    .attr('y1', -10)
                    .attr('x2', 10)
                    .attr('y2', 10)
                    .attr('stroke', 'white')
                    .attr('stroke-width', 3);

                grupo.append('line')
                    .attr('x1', -10)
                    .attr('y1', 10)
                    .attr('x2', 10)
                    .attr('y2', -10)
                    .attr('stroke', 'white')
                    .attr('stroke-width', 3);
            }
    });

    equipamentosG.append('text')
        .text(d => d.nome)
        .attr('x', 25)
        .attr('y', 0)
        .style('font-size', '12px')
        .style('pointer-events', 'none');

// Função para exibir o modal e carregar as portas livres do equipamento escolhido
function handleRightClick(event, equipamentoId) {
    event.preventDefault(); // Prevenir o menu de contexto padrão

    const empresaId = document.getElementById('empresa-selector').value;

    if (!equipamentoId || !equipamentoId.id || !empresaId) {
        alert('ID do equipamento ou ID da empresa inválidos!');
        return;
    }

    // Corrigido: pegar o ID correto do objeto
    const equipamentoIdNum = parseInt(equipamentoId.id);
    const empresaIdNum = parseInt(empresaId);

    // Busca o equipamento correto dentro da lista de nodes
    const equipamento = nodes.find(node => parseInt(node.id) === equipamentoIdNum);

    if (!equipamento) {
        alert(`Equipamento com ID ${equipamentoIdNum} não encontrado na lista de nodes.`);
        return;
    }

    if (parseInt(equipamento.empresa) !== empresaIdNum) {
        alert('Equipamento não pertence à empresa selecionada!');
        return;
    }

    // Obter as portas livres do equipamento
    fetch(`/api/portas?equipamento_id=${equipamentoIdNum}&empresa_id=${empresaIdNum}`)
        .then(response => {
            if (!response.ok) {
                return Promise.reject('Falha ao buscar as portas livres.');
            }
            return response.json();
        })
        .then(data => {

            if (data.error) {
                alert(data.error);
                document.getElementById('portaModal').style.display = "none";
                return;
            }

            if (!Array.isArray(data)) {
                alert('Ocorreu um erro ao processar as portas livres.');
                return;
            }

            filtrarEquipamentosPorEmpresa();

            const portaDropdown = document.getElementById('porta-dropdown');
            const portaModal = document.getElementById('portaModal');
            const closeModal = document.getElementById('closeModal');
            const conectarButton = document.getElementById('conectar');

            if (!portaDropdown || !portaModal || !closeModal || !conectarButton) {
                return; // Se algum desses elementos não existir, a função termina
            }

            portaDropdown.innerHTML = '<option value="">Selecione uma porta</option>';

            data.forEach(porta => {
                const option = document.createElement('option');
                option.value = porta.id;
                option.textContent = `${porta.nome} - ${porta.tipo} - ${porta.speed}`;
                portaDropdown.appendChild(option);
            });

            portaModal.style.display = "block"; // Exibir o modal

            // Agora, verificamos se o botão "Conectar" existe antes de adicionar o eventListener
            if (conectarButton) {
                conectarButton.addEventListener('click', function(event) {
                    event.preventDefault(); // Previne o envio do formulário e recarregamento da página

                    const portaOrigemId = localStorage.getItem('portaOrigemSelecionada');
                    const portaDestinoId = localStorage.getItem('portaDestinoSelecionada');
                    // Capturar o valor correto do CKEditor antes de enviar
                    // const editor = ClassicEditor.instances['observacao'];
                    const observacao = editorObservacao ? editorObservacao.getData() : '';  // Obtém o conteúdo do CKEditor

                    // Verifique se a porta de origem e destino estão selecionadas e a observação foi preenchida
                    if (portaOrigemId && portaDestinoId && observacao) {
                        conectarPortas(portaOrigemId, portaDestinoId, observacao);
                    } else {
                        alert('Por favor, selecione uma porta de origem e uma de destino, juntamente com a observação.');
                    }
                });
            }

            // Ao clicar no botão "Fechar"
            const closeModalButton = document.getElementById('closeModalConexao');
            if (closeModalButton) {
                closeModalButton.addEventListener('click', function() {
                    const portaModal = document.getElementById('portaModal');
                    portaModal.style.display = "none"; // Fecha o modal
                });
            }

            // Fechar o modal ao clicar fora dele
            window.onclick = function(event) {
                const portaModal = document.getElementById('portaModal');
                if (event.target == portaModal) {
                    portaModal.style.display = "none"; // Fecha o modal
                }
            };

            // Armazenar as seleções no localStorage
            portaDropdown.addEventListener('change', function() {
                const portaOrigemSelecionada = portaDropdown.value;
                localStorage.setItem('portaOrigemSelecionada', portaOrigemSelecionada);
            });

            const portaDestinoDropdown = document.getElementById('porta-destino-dropdown');
            const equipamentoDestinoDropdown = document.getElementById('equipamento-destino-dropdown');

            portaDestinoDropdown.addEventListener('change', function() {
                const portaDestinoSelecionada = portaDestinoDropdown.value;
                localStorage.setItem('portaDestinoSelecionada', portaDestinoSelecionada);
            });

            equipamentoDestinoDropdown.addEventListener('change', function() {
                const equipamentoDestinoSelecionado = equipamentoDestinoDropdown.value;
                localStorage.setItem('equipamentoDestinoSelecionado', equipamentoDestinoSelecionado);
            });

        })
        .catch(error => {
            //alert('Ocorreu um erro ao tentar buscar as portas livres.');
        });
}


// Função para conectar as portas, agora com os dados necessários
function conectarPortas(portaOrigemId, portaDestinoId, observacao) {
    // Definindo o payload com os dados corretos que a API espera
    const payload = {
        porta_origem_id: portaOrigemId,
        porta_destino_id: portaDestinoId,
        observacao: observacao  // Enviando apenas os dados necessários
    };

    fetch('/api/conectar-portas/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()  // Adicionando o CSRF Token
        },
        body: JSON.stringify(payload),  // Passando o payload correto
        credentials: 'same-origin'  // Garantir que os cookies sejam enviados corretamente
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            alert(data.message);
            // Fechar o modal após a conexão ser bem-sucedida
            atualizarMapa();
            renderMapa();
            // Fecha o modal após sucesso
            document.getElementById('modalConexao').classList.remove('show');
            document.getElementById('modalOverlayConexao').style.display = 'none';
            const portaModal = document.getElementById('portaModal');
            portaModal.style.display = "none"; // Fecha o modal
        } else {
            alert("Erro ao conectar portas: " + (data.error || "Erro desconhecido"));
        }
    })
    .catch(error => {
        alert("Ocorreu um erro ao tentar conectar as portas.");
    });
}

// função para filtrar os equipamentos e mostrar no DropDown
function filtrarEquipamentosPorEmpresa() {
    const empresaId = document.getElementById('empresa-selector').value;

    // Filtrar os equipamentos pela empresa selecionada
    const equipamentosFiltrados = empresaId
        ? nodes.filter(equipamento => equipamento.empresa === parseInt(empresaId))
        : [];  // Caso nenhum empresa seja selecionada, não mostra equipamentos

    const equipamentosDropdown = document.getElementById('equipamento-dropdown');
    equipamentosDropdown.innerHTML = '<option value="">Selecione um equipamento</option>'; // Resetar dropdown

    // Adiciona as opções de equipamentos ao dropdown
    equipamentosFiltrados.forEach(equipamento => {
        const option = document.createElement('option');
        option.value = equipamento.id;
        option.textContent = `${equipamento.nome} - ${equipamento.tipo} - ${equipamento.status}`;
        equipamentosDropdown.appendChild(option);
    });
}

document.getElementById('equipamento-dropdown').addEventListener('change', function() {
    const equipamentoId = this.value;
    const empresaId = document.getElementById('empresa-selector').value;

    if (!equipamentoId || !empresaId) {
        alert('Por favor, selecione um equipamento e uma empresa.');
        return;
    }

    // Buscar as portas livres do equipamento selecionado
    fetch(`/api/portas?equipamento_id=${equipamentoId}&empresa_id=${empresaId}`)
        .then(response => {
            if (!response.ok) {
                return Promise.reject('Falha ao buscar as portas livres.');
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }

            if (!data || !Array.isArray(data)) {
                alert('Ocorreu um erro ao processar as portas livres.');
                return;
            }

            // Exibir as portas no dropdown de portas de destino
            const portaDestinoDropdown = document.getElementById('porta-destino-dropdown');
            portaDestinoDropdown.innerHTML = '<option value="">Selecione uma porta</option>'; // Resetar dropdown

            data.forEach(porta => {
                const option = document.createElement('option');
                option.value = porta.id;
                option.textContent = `${porta.nome} - ${porta.tipo} - ${porta.speed}`;
                portaDestinoDropdown.appendChild(option);
            });
        })
        .catch(error => {
        //    alert('Ocorreu um erro ao tentar buscar as portas livres.');
        });
});




// função para filtrar os equipamentos e mostrar no DropDown
function filtrarEquipamentosPorEmpresa() {
    const empresaId = document.getElementById('empresa-selector').value;

    // Filtrar os equipamentos pela empresa selecionada
    const equipamentosFiltrados = empresaId
        ? nodes.filter(equipamento => equipamento.empresa === parseInt(empresaId))
        : [];  // Caso nenhum empresa seja selecionada, não mostra equipamentos

    const equipamentosDropdown = document.getElementById('equipamento-dropdown');
    equipamentosDropdown.innerHTML = '<option value="">Selecione um equipamento</option>'; // Resetar dropdown

    // Adiciona as opções de equipamentos ao dropdown
    equipamentosFiltrados.forEach(equipamento => {
        const option = document.createElement('option');
        option.value = equipamento.id;
        option.textContent = `${equipamento.nome} - ${equipamento.tipo} - ${equipamento.status}`;
        equipamentosDropdown.appendChild(option);
    });
}


function getCSRFToken() {
    return document.cookie.split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
}


    // Função de arrasto
    function dragStarted(event, d) {
        d3.select(this).raise().classed('active', true);
    }

    function dragged(event, d) {
        d.x = event.x;
        d.y = event.y;
        d3.select(this).attr('transform', `translate(${d.x},${d.y})`);
        g.selectAll('.linha-conexao')
            .filter(l => l.source === d.id || l.target === d.id)
            .attr('d', function (d) {
                const x1 = nodes.find(node => node.id === d.source).x;
                const y1 = nodes.find(node => node.id === d.source).y;
                const x2 = nodes.find(node => node.id === d.target).x;
                const y2 = nodes.find(node => node.id === d.target).y;

                const curva = calcularCurva(x1, y1, x2, y2, 0);  // Atualiza a curva ao arrastar

                return d3.line()(curva);
            });
    }

    function dragEnded(event, d) {
        d3.select(this).classed('active', false);
        salvarPosicoes();
    }

        function mostrarInformacoesConexao(d) {
            const equipamentoFonte = nodes.find(node => node.id === d.source);
            const equipamentoDestino = nodes.find(node => node.id === d.target);

            const portaFonte = d.porta_origem || 'N/A';
            const portaDestino = d.porta_destino || 'N/A';
            const portaObs = d.Obs || 'N/A';
            const portaId = d.porta_origem_id || 'NA';

        document.querySelector('.modal-conexao-header').innerHTML = `
            <div class="d-flex align-items-center">
                <i class="bi bi-plug-fill me-2 text-warning"></i>
                <h3 class="modal-title fw-bold text-warning mb-0">Conexão ${d.tipo}</h3>
            </div>
        `;

        document.querySelector('.modal-conexao-body').innerHTML = `
            <div class="px-3 py-2">
                <div class="mb-2 row">
                    <label class="col-sm-2 col-form-label"><strong>Velocidade:</strong></label>
                    <div class="col-sm-9">
                        <input type="text" class="form-control" value="${d.speed}" readonly>
                    </div>
                </div>
                <div class="mb-2 row">
                    <label class="col-sm-2 col-form-label"><strong>Fonte:</strong></label>
                    <div class="col-sm-9">
                        <input type="text" class="form-control" value="${equipamentoFonte.nome} (${portaFonte})" readonly>
                    </div>
                </div>
                <div class="mb-2 row">
                    <label class="col-sm-2 col-form-label"><strong>Destino:</strong></label>
                    <div class="col-sm-9">
                        <input type="text" class="form-control" value="${equipamentoDestino.nome} (${portaDestino})" readonly>
                    </div>
                </div>
                <div class="mb-2 row">
                    <label class="col-sm-2 col-form-label"><strong>Obs.:</strong></label>
                    <div class="col-sm-9 border rounded bg-light p-2" style="min-height: 80px;">
                        ${portaObs}
                    </div>
                </div>
            </div>`;


            document.getElementById('modalConexao').classList.add('show');
            document.getElementById('modalOverlayConexao').style.display = 'block';

            // Configura o botão de excluir
            const excluirBtn = document.getElementById('excluirConexaoBtn');
            if (excluirBtn) {
                excluirBtn.replaceWith(excluirBtn.cloneNode(true));
                const novoExcluirBtn = document.getElementById('excluirConexaoBtn');

                novoExcluirBtn.onclick = function () {

                    if (!portaId) {
                        alert("Erro: ID da porta de origem não está disponível.");
                        return;
                    }

                    if (confirm('Tem certeza que deseja excluir esta conexão?')) {
                        fetch('/api/desconectar-portas/', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({ porta_id: portaId })
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                alert('Conexão removida com sucesso!');
                                atualizarMapa();
                                renderMapa();
                                // Fecha o modal após sucesso
                                document.getElementById('modalConexao').classList.remove('show');
                                document.getElementById('modalOverlayConexao').style.display = 'none';
                            } else {
                                alert('Erro ao desconectar: ' + (data.error || 'Erro desconhecido.'));
                            }
                        })
                        .catch(() => {
                            alert('Erro na requisição.');
                        });
                    }
                };
            }

            // Configura o botão de fechar modal
            const fecharBtn = document.getElementById('fecharConexaoBtn');
            if (fecharBtn) {
                fecharBtn.onclick = function () {
                    document.getElementById('modalConexao').classList.remove('show');
                    document.getElementById('modalOverlayConexao').style.display = 'none';
                };
            }
        }


        // Função para abrir o modal e buscar as informações do equipamento no backend
        function showModal(event, d) {
            // Requisição AJAX para buscar as informações do equipamento pelo ID
            fetch(`/api/equipamento/${d.id}/`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        alert(data.error);  // Caso o equipamento não seja encontrado
                    } else {
                        // Atualiza o modal com os dados recebidos
                        document.querySelector('.modal-header').textContent = `Equipamento ${data.nome}`;
                        document.getElementById('input-ip').value = data.ip || '';
                        document.getElementById('input-usuario').value = data.usuario || '';
                        document.getElementById('input-senha').value = data.senha || '';
                        document.getElementById('input-porta').value = data.porta || '';
                        document.getElementById('input-protocolo').value = data.protocolo || '';
                        document.getElementById('input-pop').value = data.pop || '';
                        document.getElementById('input-observacao').value = data.observacao || ''

                        // Exibe o modal
                        document.getElementById('modalEquipamento').classList.add('show');
                        document.getElementById('modalOverlay').style.display = 'block';
                    }
                })
                .catch(error => console.error('Erro ao buscar informações do equipamento:', error));
        }
            // Fechar modal
            document.getElementById('closeModal').addEventListener('click', () => {
                document.getElementById('modalEquipamento').classList.remove('show');
                document.getElementById('modalOverlay').style.display = 'none';
            });

        }

    // Executa a função quando a empresa é alterada
    document.getElementById('empresa-selector').addEventListener('change', async () => {
        await atualizarMapa();  // Aguarda a atualização dos dados
        renderMapa();           // Só renderiza depois dos dados atualizados
    });


    // Atualizar o mapa a cada 30 segundos
    setInterval(() => {
        // Fechar o modal, se estiver aberto
        //if (document.getElementById('modalEquipamento').classList.contains('show')) {
        //    document.getElementById('modalEquipamento').classList.remove('show');
        //    document.getElementById('modalOverlay').style.display = 'none';
        //}

        atualizarMapa();
        renderMapa();

        // Aguarda um pequeno tempo para renderizar e reaplica o zoom
        setTimeout(() => {
            const svg = d3.select('#mapa').select('svg');
            svg.call(d3.zoom().transform, zoomTransform);
        }, 100);
    }, 30000);

    // ============================ //
    // 3. TOGGLE SENHA             //
    // ============================ //
    // const userIsSenha = window.userIsSenha;

    function toggleModalPassword(inputId, btn) {
        if (!userIsSenha) {
            return;
        }

        const input = document.getElementById(inputId);
        if (input.type === "password") {
            input.type = "text";
            btn.textContent = "🙈";
        } else {
            input.type = "password";
            btn.textContent = "👁";
        }
    }
});
