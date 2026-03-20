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

    editarRotuloVertice: function(vertexData) {
        if (!vertexData) return window.dash_clientside.no_update;
        
        let now = new Date().getTime();
        
        if (!window.ultimoVerticeClicado) {
            window.ultimoVerticeClicado = { time: now, id: vertexData.id };
            return window.dash_clientside.no_update;
        }
        
        // CORRIGIDO: Agora usa ultimoVerticeClicado em vez de ultimaArestaClicada
        let tempoDecorrido = now - window.ultimoVerticeClicado.time;
        let mesmoVertice = window.ultimoVerticeClicado.id === vertexData.id;
        
        window.ultimoVerticeClicado = { time: now, id: vertexData.id };
        
        if (tempoDecorrido < 400 && mesmoVertice) {
            return {
                id: vertexData.id,
                label: vertexData.label || ''
            };
        }
        return window.dash_clientside.no_update;
    },

    escutarTeclado: function(graph_id) {
        if (!window.keydownListenerAdded) {

            // 1. EVENTOS DE TECLADO
            document.addEventListener('keydown', function(event) {
                if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
                    return;
                }
                if (event.key === 'Delete') {
                    var btnDeletar = document.getElementById('delete-selected-button');
                    if (btnDeletar && !btnDeletar.disabled) {
                        btnDeletar.click();
                    }
                }
                if (event.key === '+' || event.key === '=') {
                    var btnAdicionar = document.getElementById('add-vertex-button');
                    if (btnAdicionar) {
                        btnAdicionar.click();
                    }
                }
            });

            // 2. DUPLO CLIQUE NO FUNDO (Centralizar)
            document.addEventListener('dblclick', function(event) {
                let container = document.getElementById('cytoscape-graph');
                if (container && container.contains(event.target)) {
                    let btnCentralizar = document.getElementById('btn-hidden-center');
                    if (btnCentralizar) {
                        btnCentralizar.click();
                    }
                }
            });

            // 3. BOTÃO DIREITO DO MOUSE (Modo Conexão)
            document.addEventListener('contextmenu', function(event) {
                let container = document.getElementById('cytoscape-graph');
                if (container && container.contains(event.target)) {
                    event.preventDefault();
                    var btnConexao = document.getElementById('connect-mode-button');
                    if (btnConexao) {
                        btnConexao.click();
                    }
                }
            });

            // 4. SHIFT + CLIQUE ESQUERDO (Adicionar Vértice no Mouse)
            document.addEventListener('mousedown', function(event) {
                if (event.shiftKey && event.button === 0) {
                    let container = document.getElementById('cytoscape-graph');
                    
                    if (container && container.contains(event.target)) {
                        event.preventDefault(); 
                        
                        let rect = container.getBoundingClientRect();
                        let x_tela = event.clientX - rect.left;
                        let y_tela = event.clientY - rect.top;
                        
                        // Resgata a câmera (com fallback seguro contra undefined)
                        let cam = window.my_cyto_camera || {};
                        let cyto_zoom = cam.zoom || 1.0;
                        let cyto_pan_x = (cam.pan && cam.pan.x !== undefined) ? cam.pan.x : 0;
                        let cyto_pan_y = (cam.pan && cam.pan.y !== undefined) ? cam.pan.y : 0;
                        
                        // MÁGICA REVERSA
                        let x_real = (x_tela - cyto_pan_x) / cyto_zoom;
                        let y_real = (y_tela - cyto_pan_y) / cyto_zoom;
                        
                        // Aciona o Python
                        let input = document.getElementById('shift-click-coords');
                        if (input) {
                            let nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                            nativeInputValueSetter.call(input, x_real + "," + y_real + "," + new Date().getTime());
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                        }
                    }
                }
            }, true); // <--- A Fase de Captura (true) está aqui!

            window.keydownListenerAdded = true;
        }
        return window.dash_clientside.no_update;
    }
};