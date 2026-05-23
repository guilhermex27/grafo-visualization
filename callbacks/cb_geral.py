import os
import time
import math
import shutil
import dash
from dash import html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

import utils.graph_logic as gl
from utils.graph_logic import save_graph_data, load_graph_data, nx_to_cytoscape

def registrar_callbacks_geral(app):

    @app.callback(
        Output('cytoscape-graph', 'layout', allow_duplicate=True), 
        Input('home-button', 'n_clicks'),
        State('toggle-peso', 'value'), 
        prevent_initial_call=True
    )
    def reset_layout(n_clicks, toggle_peso):
        if not n_clicks:
            raise PreventUpdate
        
        nodes = list(gl.G.nodes())
        n_nodes = len(nodes)
        pos_dict = {} 
        
        if n_nodes > 0:
            raio = max(150, n_nodes * 32) 
            centro_x, centro_y = 400, 300
            
            for i, node in enumerate(nodes):
                angulo = 2 * math.pi * i / n_nodes
                nova_pos = {
                    'x': centro_x + raio * math.cos(angulo),
                    'y': centro_y + raio * math.sin(angulo)
                }
                gl.G.nodes[node]['position'] = nova_pos
                pos_dict[str(node)] = nova_pos 

        save_graph_data(toggle_peso == 'com_peso') 

        layout = {
            'name': 'preset',
            'positions': pos_dict,
            'fit': True,
            'padding': 30,
            'animate': True,
            'animationDuration': 500,
            'refresh_trigger': f"home_{time.time()}"
        }
        
        return layout

    @app.callback(
        Output('modal-editar-peso', 'is_open'),
        Output('modal-input-peso', 'value'),
        Output('aresta-edit-store', 'data'),
        Input('edge-edit-store', 'data'),
        Input('btn-cancelar-peso', 'n_clicks'),
        Input('btn-salvar-peso', 'n_clicks'),
        State('toggle-peso', 'value'),
        State('snapshots-store', 'data'),
        prevent_initial_call=True
    )
    def alternar_modal(edge_data, cancel_clicks, save_clicks, modo_peso, snaps):
        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate
        prop_id = ctx.triggered[0]['prop_id']

        if prop_id in ['btn-cancelar-peso.n_clicks', 'btn-salvar-peso.n_clicks'] or snaps:
            return False, dash.no_update, dash.no_update

        if prop_id == 'edge-edit-store.data' and edge_data:
            if modo_peso == 'sem_peso':
                return False, dash.no_update, dash.no_update
            return True, edge_data.get('label', ''), edge_data

        return False, dash.no_update, dash.no_update

    @app.callback(
        Output('modal-editar-rotulo', 'is_open'),
        Output('modal-input-rotulo', 'value'),
        Output('vertex-edit-store', 'data'),
        Input('vertice-edit-store', 'data'),
        Input('btn-cancelar-rotulo', 'n_clicks'),
        Input('btn-salvar-rotulo', 'n_clicks'),
        State('snapshots-store', 'data'),
        State('connect-mode-store', 'data'),
        prevent_initial_call=True
    )
    def alternar_modal_rotulo(vertex_data, cancel_clicks, save_clicks, snaps, connect_mode_on):
        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate
        prop_id = ctx.triggered[0]['prop_id']

        if prop_id in ['btn-cancelar-rotulo.n_clicks', 'btn-salvar-rotulo.n_clicks'] or snaps:
            return False, dash.no_update, dash.no_update

        if connect_mode_on:
            return False, dash.no_update, dash.no_update

        if prop_id == 'vertice-edit-store.data' and vertex_data:
            return True, vertex_data.get('label', ''), vertex_data

        return False, dash.no_update, dash.no_update

    @app.callback(
        Output('coluna-grafo', 'width'),
        Output('coluna-painel', 'style'),
        Output('toggle-painel-btn', 'children'),
        Input('toggle-painel-btn', 'n_clicks'),
        prevent_initial_call=True
    )
    def alternar_painel_inteiro(n_clicks):
        estilo_painel = {
            'position': 'absolute', 'right': '0', 'top': '0',
            'width': '300px', 'height': '88vh', 'padding': '0',
            'transition': 'transform 0.3s ease', 'zIndex': 100
        }

        if n_clicks % 2 == 0:
            estilo_painel['transform'] = 'translateX(100%)'
            return 12, estilo_painel, '◀'
        else:
            estilo_painel['transform'] = 'translateX(0%)'
            return 12, estilo_painel, '▶'

    @app.callback(
        Output('card-info-grafo', 'style'),
        Output('btn-info-grafo', 'style', allow_duplicate=True),
        Input('btn-info-grafo', 'n_clicks'),
        State('card-info-grafo', 'style'),
        State('btn-info-grafo', 'style'),
        prevent_initial_call=True
    )
    def toggle_info_card(n_clicks, current_style, current_style_btn):
        novo_estilo = current_style.copy()
        novo_estilo_btn = current_style_btn.copy()
        if novo_estilo.get('display') == 'none':
            novo_estilo['display'] = 'block'
            novo_estilo_btn['backgroundImage'] = 'url("/assets/icons/info-light.svg")'
        else:
            novo_estilo['display'] = 'none'
            novo_estilo_btn['backgroundImage'] = 'url("/assets/icons/info.svg")'
        return novo_estilo, novo_estilo_btn

    @app.callback(
        Output('cytoscape-graph', 'elements', allow_duplicate=True),
        Output('cytoscape-graph', 'layout', allow_duplicate=True),
        Output('action-output-message', 'children', allow_duplicate=True),
        Output('toggle-direcao', 'value', allow_duplicate=True),
        Output('toggle-peso', 'value', allow_duplicate=True),
        Output('empty-graph-message', 'children', allow_duplicate=True),
        Input('tpl-arvore', 'n_clicks'),
        Input('tpl-casa', 'n_clicks'),
        Input('tpl-estrela', 'n_clicks'),
        Input('tpl-hipercubo', 'n_clicks'),
        Input('tpl-triangulo', 'n_clicks'),
        Input('tpl-zedografo', 'n_clicks'),
        Input('tpl-k33', 'n_clicks'),
        prevent_initial_call=True
    )
    def carregar_template(n_arvore, n_casa, n_estrela, n_hipercubo, n_triangulo, n_ze, n_k33):
        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate

        prop_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        mapa_arquivos = {
            'tpl-arvore': 'arvore', 'tpl-casa': 'casa', 'tpl-estrela': 'estrela',
            'tpl-hipercubo': 'hipercubo', 'tpl-triangulo': 'trianguloCompleto',
            'tpl-k33': 'k33', 'tpl-zedografo': 'zeDoGrafo'
        }
        
        nome_base = mapa_arquivos.get(prop_id)
        if not nome_base:
            raise PreventUpdate
            
        caminho_txt_origem = f'templates/{nome_base}.txt'
        caminho_json_origem = f'templates/{nome_base}.json'

        os.makedirs('templates', exist_ok=True)

        if os.path.exists(caminho_txt_origem):
            shutil.copy(caminho_txt_origem, gl.GRAPH_FILE_PATH)
        else:
            return dash.no_update, dash.no_update, html.Span(f"Erro: Arquivo {caminho_txt_origem} não encontrado!", style={'color': 'red'}), dash.no_update, dash.no_update

        if os.path.exists(caminho_json_origem):
            shutil.copy(caminho_json_origem, 'data/config.json')
        else:
            if os.path.exists('data/config.json'):
                os.remove('data/config.json')
        
        config = load_graph_data(from_upload=False)
        novos_elementos = nx_to_cytoscape(gl.G)
        
        layout = {'name': 'preset', 'animate': True, 'animationDuration': 500, 'fit': True, 'padding': 40}
        msg = html.Span(f"Modelo: '{nome_base}' carregado com sucesso!", style={'color': 'black'})
        
        dir_val = 'orientado' if config.get('is_directed', False) else 'nao_orientado'
        peso_val = 'com_peso' if config.get('is_weighted', True) else 'sem_peso'
        
        return novos_elementos, layout, msg, dir_val, peso_val, ""

    @app.callback(
        Output("modal-ajuda", "is_open"),
        [Input("btn-abrir-ajuda", "n_clicks"), Input("btn-fechar-ajuda", "n_clicks")],
        [State("modal-ajuda", "is_open")],
        prevent_initial_call=True
    )
    def alternar_modal_ajuda(n_abrir, n_fechar, is_open):
        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate
        return not is_open
    
    @app.callback(
        Output("modal-matriz", "is_open"),
        [Input("btn-abrir-matriz", "n_clicks")],
        [State("modal-matriz", "is_open")],
        prevent_initial_call=True
    )
    def alternar_modal_matriz(n_abrir, is_open):
        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate
        return not is_open