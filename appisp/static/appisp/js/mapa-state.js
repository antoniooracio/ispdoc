// Estas variáveis armazenarão os dados do mapa.
// O 'export' permite que outros arquivos (como o mapa-render) leiam esses dados.
export let nodes = [];
export let links = [];
export let userIsAdmin = false;

// Estas funções serão usadas pelo 'mapa-api.js' para atualizar os dados
// depois que eles forem buscados do servidor.
export function setNodes(newNodes) {
    nodes = newNodes;
}

export function setLinks(newLinks) {
    links = newLinks;
}

export function setUserIsAdmin(isAdmin) {
    userIsAdmin = isAdmin;
}
