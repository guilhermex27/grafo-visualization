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
                if (event.key === 'Delete') {
                    var btnDeletar = document.getElementById('delete-selected-button');
                    if (btnDeletar && !btnDeletar.disabled) {
                        btnDeletar.click();
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