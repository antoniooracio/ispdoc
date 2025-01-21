function renderMapa() {
    const empresaId = empresaSelector.value;
    const equipamentosFiltrados = empresaId
        ? equipamentos.filter(equipamento => equipamento.empresa == empresaId)
        : equipamentos;

    mapa.selectAll('*').remove();

    mapa.node

    const svg = mapa.append('svg')
        .attr('width', width)
        .attr('height', height);

    const g = svg.append('g');

    const zoom = d3.zoom()
        .scaleExtent([0.5, 3])
        .on('zoom', (event) => {
            g.attr('transform', event.transform);
        });

    svg.call(zoom);

    // Função para iniciar o movimento
    function dragStarted(event, d) {
        d3.select(this).raise().classed('active', true);
    }

    // Função para arrastar o equipamento
    function dragged(event, d) {
        d.x = event.x;
        d.y = event.y;

        d3.select(this)
            .attr('transform', `translate(${d.x},${d.y})`);
    }

    // Função para finalizar o movimento e enviar ao backend
    function dragEnded(event, d) {
        d3.select(this).classed('active', false);

        // Enviar os dados atualizados ao backend
        fetch(`/admin/mapa-rede/atualizar-posicao/${d.id}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(), // Função para capturar o token CSRF
            },
            body: JSON.stringify({ x: d.x, y: d.y }),
        })
        .then(response => {
            if (response.ok) {
                console.log(`Posição do equipamento ${d.id} atualizada com sucesso.`);
            } else {
                console.error('Erro ao atualizar a posição do equipamento.');
            }
        });
    }

    // Criar comportamento de arraste
    const drag = d3.drag()
        .on('start', dragStarted)
        .on('drag', dragged)
        .on('end', dragEnded);

    // Renderizar equipamentos
    const equipamentosG = g.selectAll('.equipamento')
        .data(equipamentosFiltrados)
        .enter().append('g')
        .attr('class', 'equipamento')
        .attr('transform', d => `translate(${d.x},${d.y})`)
        .call(drag) // Adiciona o comportamento de arraste
        .on('click', (event, d) => abrirModal(d));

    equipamentosG.append('circle')
        .attr('r', 20)
        .attr('fill', d => d.status === 'Ativo' ? 'green' : 'red');

    equipamentosG.append('text')
        .text(d => d.nome)
        .attr('x', 25)
        .attr('y', 5)
        .style('font-size', '12px')
        .style('pointer-events', 'none'); // Previne que o texto capture eventos de clique
}

// Função para obter o token CSRF do cookie
function getCSRFToken() {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        if (cookie.trim().startsWith('csrftoken=')) {
            return cookie.trim().split('=')[1];
        }
    }
    return '';
}

empresaSelector.addEventListener('change', renderMapa);

renderMapa();
