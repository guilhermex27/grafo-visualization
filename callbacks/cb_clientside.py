import dash
from dash.dependencies import Input, Output

def registrar_clientside_callbacks(app):

    app.clientside_callback(
        dash.ClientsideFunction(namespace='grafos', function_name='escutarTeclado'),
        Output('keyboard-listener-dummy', 'children'),
        Input('cytoscape-graph', 'id')
    )

    app.clientside_callback(
        dash.ClientsideFunction(namespace='grafos', function_name='editarAresta'),
        Output('edge-edit-store', 'data'),
        Input('cytoscape-graph', 'tapEdgeData'),
        prevent_initial_call=True
    )

    app.clientside_callback(
        dash.ClientsideFunction(namespace='grafos', function_name='editarRotuloVertice'),
        Output('vertice-edit-store', 'data'),
        Input('cytoscape-graph', 'tapNodeData'),
        prevent_initial_call=True
    )

    app.clientside_callback(
        """
        function(children) {
            if (!children) return window.dash_clientside.no_update;
            
            var el = document.getElementById('action-output-message');
            if (el) {
                el.style.animation = 'none';
                el.offsetHeight;
                el.style.animation = 'fadeOutMsg 5.0s forwards';
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output('keyboard-listener-dummy', 'data-fade'),
        Input('action-output-message', 'children'),
        prevent_initial_call=True
    )

    app.clientside_callback(
        """
        function(zoom, pan) {
            window.my_cyto_camera = {
                zoom: zoom || 1.0, 
                pan: pan || {x: 0, y: 0}
            };
            return window.dash_clientside.no_update;
        }
        """,
        Output('camera-tracker-dummy', 'data'),
        Input('cytoscape-graph', 'zoom'),
        Input('cytoscape-graph', 'pan')
    )
    
    app.clientside_callback(
        """
        function(n_clicks) {
            if (n_clicks > 0) {
                html2canvas(document.getElementById('modal-matriz'), {ignoreElements: (el) => el.id === 'btn-exportar', useCORS: true}).then(function (canvas) {
                    var link = document.createElement('a');
                    link.download = 'matriz-de-adjacencia.png';
                    link.href = canvas.toDataURL();
                    link.click();
                });
            }
            return 0;
        }
        """,
        Output('btn-exportar', 'n_clicks'),
        Input('btn-exportar', 'n_clicks')
    )   