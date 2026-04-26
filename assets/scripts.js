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

            // 2. DUPLO CLIQUE NO FUNDO
            document.addEventListener('dblclick', function(event) {
                let container = document.getElementById('cytoscape-graph');
                if (container && container.contains(event.target)) {
                    let btnCentralizar = document.getElementById('btn-hidden-center');
                    if (btnCentralizar) {
                        btnCentralizar.click();
                    }
                }
            });

            // 3. BOTÃO DIREITO DO MOUSE
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

            // 4. SHIFT + CLIQUE ESQUERDO
            document.addEventListener('mousedown', function(event) {
                if (event.shiftKey && event.button === 0) {
                    let container = document.getElementById('cytoscape-graph');
                    
                    if (container && container.contains(event.target)) {
                        event.preventDefault(); 
                        
                        let rect = container.getBoundingClientRect();
                        let x_tela = event.clientX - rect.left;
                        let y_tela = event.clientY - rect.top;
                        
                        let cy = null;
                        let reactKey = Object.keys(container).find(k => k.startsWith('__reactFiber$'));
                        if (reactKey) {
                            let fiber = container[reactKey];
                            while (fiber) {
                                if (fiber.stateNode && fiber.stateNode._cy) {
                                    cy = fiber.stateNode._cy;
                                    break;
                                }
                                if (fiber.stateNode && fiber.stateNode.cy) {
                                    cy = fiber.stateNode.cy;
                                    break;
                                }
                                fiber = fiber.return;
                            }
                        }

                        let cyto_zoom = 1.0;
                        let cyto_pan_x = 0;
                        let cyto_pan_y = 0;

                        if (cy) {
                            cyto_zoom = cy.zoom();
                            let pan = cy.pan();
                            cyto_pan_x = pan.x;
                            cyto_pan_y = pan.y;
                        } else {
                            let cam = window.my_cyto_camera || {};
                            cyto_zoom = cam.zoom || 1.0;
                            cyto_pan_x = (cam.pan && cam.pan.x !== undefined) ? cam.pan.x : 0;
                            cyto_pan_y = (cam.pan && cam.pan.y !== undefined) ? cam.pan.y : 0;
                        }
                        
                        
                        let x_real = (x_tela - cyto_pan_x) / cyto_zoom;
                        let y_real = (y_tela - cyto_pan_y) / cyto_zoom;
                        
                     
                        let input = document.getElementById('shift-click-coords');
                        if (input) {
                            let nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                            nativeInputValueSetter.call(input, x_real + "," + y_real + "," + new Date().getTime());
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                        }
                    }
                }
            }, true);
            
            // 5. AUTO-SAVE DE POSIÇÃO (COM DEBOUNCE E TIMESTAMP)
            let tryAttachCy = setInterval(function() {
                let container = document.getElementById('cytoscape-graph');
                if (container) {
                    let cy = null;
                    let reactKey = Object.keys(container).find(k => k.startsWith('__reactFiber$'));
                    if (reactKey) {
                        let fiber = container[reactKey];
                        while (fiber) {
                            if (fiber.stateNode && fiber.stateNode._cy) { cy = fiber.stateNode._cy; break; }
                            if (fiber.stateNode && fiber.stateNode.cy) { cy = fiber.stateNode.cy; break; }
                            fiber = fiber.return;
                        }
                    }
                    if (cy) {
                        // Limpa ouvidores antigos para não duplicar o salvamento
                        cy.off('dragfree', 'node');

                        let dragTimeout = null;
                        cy.on('dragfree', 'node', function(evt) {
                            if (dragTimeout) clearTimeout(dragTimeout);
                            
                            dragTimeout = setTimeout(function() {
                                let posicoes = {};
                                cy.nodes().forEach(n => {
                                    posicoes[n.id()] = n.position();
                                });

                                let inputAutoSave = document.getElementById('auto-save-data');
                                if(inputAutoSave) {
                                    // Adicionamos um timestamp para garantir que o 'value' mude SEMPRE
                                    let dataParaEnvio = {
                                        tempo: new Date().getTime(),
                                        posicoes: posicoes
                                    };
                                    
                                    let setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                                    setter.call(inputAutoSave, JSON.stringify(dataParaEnvio));
                                    inputAutoSave.dispatchEvent(new Event('input', { bubbles: true }));
                                }
                            }, 250); 
                        });
                    }
                }
            }, 1000);
            
            window.keydownListenerAdded = true;
        }
        return window.dash_clientside.no_update;
    }
};