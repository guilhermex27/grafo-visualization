if (!window.dash_clientside) {
    window.dash_clientside = {};
}

window.dash_clientside.grafos = {
    
    editarAresta: function(edgeData) {
        if (!edgeData) return window.dash_clientside.no_update;
        
        let now = new Date().getTime();
        
        if (!window.ultimaArestaClicada) {
            window.ultimaArestaClicada = { time: now, id: edgeData.id };
            return window.dash_clientside.no_update;
        }
        
        let tempoDecorrido = now - window.ultimaArestaClicada.time;
        let mesmaAresta = window.ultimaArestaClicada.id === edgeData.id;
        
        window.ultimaArestaClicada = { time: now, id: edgeData.id };
        
        if (tempoDecorrido < 400 && mesmaAresta) {
            return {
                source: edgeData.source,
                target: edgeData.target,
                label: edgeData.label || ''
            };
        }
        return window.dash_clientside.no_update;
    },

    escutarTeclado: function(graph_id) {
        if (!window.keydownListenerAdded) {

            document.addEventListener('keydown', function(event) {
                // TRAVA CRÍTICA: Ignora o teclado se o usuário estiver digitando no Input do Modal de peso!
                if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
                    return;
                }

                // Atalho 1: Delete (Deleta selecionado)
                if (event.key === 'Delete') {
                    var btnDeletar = document.getElementById('delete-selected-button');
                    if (btnDeletar && !btnDeletar.disabled) {
                        btnDeletar.click();
                    }
                }

                // Atalho 2: Tecla '+' ou '=' (Adiciona vértice)
                // Usamos '=' também porque muitas vezes o '+' requer segurar Shift no teclado
                if (event.key === '+' || event.key === '=') {
                    var btnAdicionar = document.getElementById('add-vertex-button');
                    if (btnAdicionar) {
                        btnAdicionar.click();
                    }
                }

                // Atalho 3: Tecla 'a' ou 'A' (Alterna modo de conexão/seleção)
                if (event.key === 'a' || event.key === 'A') {
                    var btnConexao = document.getElementById('connect-mode-button');
                    if (btnConexao) {
                        btnConexao.click();
                    }
                }
            });

            document.addEventListener('dblclick', function(event) {
                let container = document.getElementById('cytoscape-graph');
                if (container && container.contains(event.target)) {
                    let btnCentralizar = document.getElementById('btn-hidden-center');
                    if (btnCentralizar) {
                        btnCentralizar.click();
                    }
                }
            });

            window.keydownListenerAdded = true;
        }
        return window.dash_clientside.no_update;
    }
};