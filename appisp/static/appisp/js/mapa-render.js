import { nodes, links, userIsAdmin } from './mapa-state.js';
import { showModal, mostrarInformacoesConexao, handleRightClick } from './mapa-interactions.js';

let zoomTransform = d3.zoomIdentity;
const mapa = d3.select("#map-container");

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

function salvarPosicoes() {
    const posicoes = nodes.map(node => ({ id: node.id, x: node.x, y: node.y }));
    localStorage.setItem('posicoesEquipamentos', JSON.stringify(posicoes));
}

function desenharIconeComStatus(grupo, d) {
    const tamanhoIcone = 60;
    const tamanhoBorda = 2;
    const opacidadeInativo = 0.4;
    
    // CORREÇÃO: Usa o objeto global ICON_URLS injetado pelo template HTML
    const urlIcone = window.ICON_URLS[d.tipo] || window.ICON_URLS['default'];
    
    const posX = -tamanhoIcone / 2;
    const posY = -tamanhoIcone / 2;

    // 1. Desenha um retângulo cinza como base (placeholder).
    // Este retângulo SEMPRE será visível, mesmo se o ícone falhar.
    grupo.append('rect')
        .attr('x', posX)
        .attr('y', posY)
        .attr('width', tamanhoIcone)
        .attr('height', tamanhoIcone)
        .attr('fill', '#cccccc') // Um cinza neutro como fallback
        .attr('rx', 6) // Cantos arredondados
        .attr('ry', 6);
        

    if (d.status !== 'Ativo') {
        grupo.append('rect')
            .attr('x', posX - tamanhoBorda).attr('y', posY - tamanhoBorda)
            .attr('width', tamanhoIcone + (tamanhoBorda * 2)).attr('height', tamanhoIcone + (tamanhoBorda * 2))
            .attr('fill', 'red').attr('rx', 8).attr('ry', 8);
    }
    grupo.append('image')
        .attr('xlink:href', urlIcone)
        .attr('width', tamanhoIcone).attr('height', tamanhoIcone)
        .attr('x', posX).attr('y', posY);
    if (d.status !== 'Ativo') {
        grupo.append('rect')
            .attr('x', posX).attr('y', posY)
            .attr('width', tamanhoIcone).attr('height', tamanhoIcone)
            .attr('fill', 'red').attr('opacity', opacidadeInativo);
    }
}

export function renderMapa() {
    carregarPosicoes();
    const empresaId = document.getElementById('empresa-selector').value;
    if (!empresaId) {
        mapa.selectAll('*').remove();
        return;
    }

    const equipamentosFiltrados = nodes.filter(e => e.empresa === parseInt(empresaId));
    const conexoesFiltradas = links.filter(l => {
        const sourceEquip = nodes.find(n => n.id === l.source.id);
        const targetEquip = nodes.find(n => n.id === l.target.id);
        return sourceEquip && targetEquip && sourceEquip.empresa === parseInt(empresaId) && targetEquip.empresa === parseInt(empresaId);
    });

    const svgElement = mapa.select('svg');
    if (!svgElement.empty()) {
        zoomTransform = d3.zoomTransform(svgElement.node());
    }

    mapa.selectAll('*').remove();
    const width = mapa.node().getBoundingClientRect().width;
    const height = window.innerHeight - 150; 

    const svg = mapa.append('svg').attr('width', width).attr('height', height);
    const g = svg.append('g');

    const zoom = d3.zoom().scaleExtent([0.5, 3]).on('zoom', (event) => {
        g.attr('transform', event.transform);
        document.getElementById('zoom-slider').value = event.transform.k;
        zoomTransform = event.transform;
    });

    svg.call(zoom);
    svg.call(zoom.transform, zoomTransform);

    document.getElementById('zoom-slider').addEventListener('input', (event) => {
        const newZoom = parseFloat(event.target.value);
        svg.transition().duration(200).call(zoom.scaleTo, newZoom);
    });

    const drag = d3.drag().on('start', dragStarted).on('drag', dragged).on('end', dragEnded);

    const conexaoContagem = {};
    conexoesFiltradas.forEach(link => {
        const key = `${Math.min(link.source.id, link.target.id)}-${Math.max(link.source.id, link.target.id)}`;
        conexaoContagem[key] = (conexaoContagem[key] || 0) + 1;
    });

    g.selectAll('.linha-conexao').data(conexoesFiltradas).enter().append('path')
        .attr('class', 'linha-conexao')
        .attr('d', function (d, i) {
            const x1 = d.source.x, y1 = d.source.y;
            const x2 = d.target.x, y2 = d.target.y;
            const key = `${Math.min(d.source.id, d.target.id)}-${Math.max(d.source.id, d.target.id)}`;
            if (conexaoContagem[key] === 1) return `M ${x1},${y1} L ${x2},${y2}`;
            const direction = i % 2 === 0 ? 1 : -1;
            const intensity = (Math.floor(i / 2) * 10) + 5;
            const cx = (x1 + x2) / 2;
            const cy = (y1 + y2) / 2 + (direction * intensity);
            return `M ${x1},${y1} Q ${cx},${cy} ${x2},${y2}`;
        })
        .attr('stroke', d => ({ 'Fibra': 'blue', 'Eletrico': 'green', 'Radio': 'orange', 'Transporte': 'brown' }[d.tipo] || 'gray'))
        .attr('stroke-width', d => ({ '10G': 3, '20G': 4, '40G': 5, '100G': 6 }[d.speed] || 2))
        .attr('fill', 'none')
        .on('click', (event, d) => mostrarInformacoesConexao(d));

    const equipamentosG = g.selectAll('.equipamento').data(equipamentosFiltrados).enter().append('g')
        .attr('class', 'equipamento')
        .attr('transform', d => `translate(${d.x},${d.y})`)
        .call(drag)
        .on('click', (event, d) => userIsAdmin ? showModal(event, d) : alert("Você não tem permissão para visualizar essas informações."))
        .on('contextmenu', handleRightClick);

    equipamentosG.each(function (d) {
        desenharIconeComStatus(d3.select(this), d);
    });

    equipamentosG.append('text').text(d => d.nome).attr('x', 40).attr('y', 5).style('font-size', '12px').style('pointer-events', 'none');

    function dragStarted(event, d) { d3.select(this).raise().classed('active', true); }
    function dragged(event, d) {
        d.x = event.x;
        d.y = event.y;
        d3.select(this).attr('transform', `translate(${d.x},${d.y})`);
        g.selectAll('.linha-conexao').filter(l => l.source.id === d.id || l.target.id === d.id)
            .attr('d', function (l) {
                const x1 = l.source.x, y1 = l.source.y, x2 = l.target.x, y2 = l.target.y;
                const key = `${Math.min(l.source.id, l.target.id)}-${Math.max(l.source.id, l.target.id)}`;
                if (conexaoContagem[key] === 1) return `M ${x1},${y1} L ${x2},${y2}`;
                const i = conexoesFiltradas.indexOf(l);
                const direction = i % 2 === 0 ? 1 : -1;
                const intensity = (Math.floor(i / 2) * 10) + 5;
                const cx = (x1 + x2) / 2;
                const cy = (y1 + y2) / 2 + (direction * intensity);
                return `M ${x1},${y1} Q ${cx},${cy} ${x2},${y2}`;
            });
    }
    function dragEnded(event, d) {
        d3.select(this).classed('active', false);
        salvarPosicoes();
    }
}

export function atualizarMapa() {
    console.log("Atualizando dados e renderizando o mapa...");
    renderMapa();
}

export function getZoomTransform() {
    return zoomTransform;
}