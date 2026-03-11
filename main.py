'''
Este script implementa um editor de grafos interativo usando Dash, Cytoscape e NetworkX.

Funcionalidades:
- Modos de Interação: um para 'Seleção' (deletar) e um para 'Conexão' (criar arestas).
- Visualização de grafos (orientados e não orientados).
- Adicionar/Remover vértices e arestas de forma interativa.
- Carregar e Salvar grafos em formato de lista de adjacências.
- Manutenção das posições dos nós na interface.
- Backend de dados gerenciado pela biblioteca NetworkX.
'''

import os
import base64
from flask import send_file
import dash
import dash_cytoscape as cyto
from dash import dcc, html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import networkx as nx

# =============================================================================
# 1. Backend: NetworkX como Fonte da Verdade e Configurações
# =============================================================================

G = nx.Graph()
GRAPH_FILE_PATH = 'data/graph.txt'

BASE_STYLESHEET = [
    {
        'selector': 'node',
        'style': {
            'label': 'data(id)',
            'text-valign': 'center', 'color': 'white',
            'text-outline-color': '#333', 'text-outline-width': '2px',
            'background-color': '#888'
        }
    },
    {
        'selector': 'edge',
        'style': {
            'label': 'data(label)', 'color': 'black',
            'text-margin-y': '-13px', 
        }
    },
    {
        'selector': ':selected',
        'style': {
            'border-width': 3, 'border-color': '#42a5f5' # Destaque azul para seleção
        }
    }
]

# =============================================================================
# 2. Lógica de Conversão e Persistência de Dados
# =============================================================================

def nx_to_cytoscape(graph_obj):
    cy_elements = []
    for node, attrs in graph_obj.nodes(data=True):
        cy_node = {'data': {'id': str(node), 'label': str(node)}}
        if 'position' in attrs:
            cy_node['position'] = attrs['position']
        cy_elements.append(cy_node)
    for source, target, attrs in graph_obj.edges(data=True):
        cy_edge = {'data': {'source': str(source), 'target': str(target)}}
        if attrs.get('label'):
            cy_edge['data']['label'] = attrs['label']
        cy_elements.append(cy_edge)
    return cy_elements

def load_graph_data():
    global G
    if not os.path.exists(GRAPH_FILE_PATH) or os.path.getsize(GRAPH_FILE_PATH) == 0:
        G = nx.Graph()
        return
    with open(GRAPH_FILE_PATH, 'r') as f:
        lines = [line.strip() for line in f.read().splitlines() if line.strip()]
    G.clear()
    if not lines: return
    G = nx.Graph()
    try:
        header = lines.pop(0).split()
        num_nodes_header = int(header[0])
        nodes_in_edges = set()
        for line in lines:
            parts = line.split()
            if len(parts) >= 2:
                source, target = parts[0], parts[1]
                weight = parts[2] if len(parts) > 2 else '1'
                G.add_edge(source, target, label=weight)
                nodes_in_edges.add(source)
                nodes_in_edges.add(target)
        nodes_to_add_count = num_nodes_header - len(G.nodes)
        if nodes_to_add_count > 0:
            i = 0
            while nodes_to_add_count > 0:
                node_id = str(i)
                if not G.has_node(node_id):
                    G.add_node(node_id)
                    nodes_to_add_count -= 1
                i += 1
    except Exception as e:
        print(f"Erro ao processar o arquivo de grafo: {e}")
        G.clear()

def save_graph_data():
    with open(GRAPH_FILE_PATH, 'w') as f:
        f.write(f"{G.number_of_nodes()} {G.number_of_edges()}\n")
        for source, target, data in G.edges(data=True):
            f.write(f"{source} {target} {data.get('label', '1')}\n")

# =============================================================================
# 3. Layout da Aplicação Dash
# =============================================================================

app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

def serve_layout():
    os.makedirs(os.path.dirname(GRAPH_FILE_PATH), exist_ok=True)
    load_graph_data()
    initial_elements = nx_to_cytoscape(G)

    return html.Div([
        dcc.Store(id='source-node-store', data=None),
        dcc.Store(id='connect-mode-store', data=False), # False: Modo Seleção, True: Modo Conexão
        html.Div([ html.H1("Editor de Grafo Interativo"), html.Button('Redefinir Visualização', id='home-button')]),
        cyto.Cytoscape(
            id='cytoscape-graph',
            elements=initial_elements,
            stylesheet=BASE_STYLESHEET,
            style={'width': '100%', 'height': '450px'},
            layout={'name': 'circle', 'animate': True, 'animationDuration': 500},
            wheelSensitivity=0.1
        ),
        html.Div(id='empty-graph-message', style={'textAlign': 'center', 'padding': '20px'}),
        html.Hr(),
        html.Div([
            html.Div([html.H3("Vértice"), html.Button('Adicionar Vértice', id='add-vertex-button')]),
            html.Div([
                html.H3("Interação"),
                html.Button('Modo: Seleção', id='connect-mode-button', style={'width': '150px'}),
                html.P(id='connect-mode-help-text', children="(Selecione elementos para deletar)", style={'fontSize': '12px', 'color': 'grey'})
            ], style={'textAlign': 'center'}),
            html.Div([html.H3("Deletar"), html.Button('Deletar Selecionado', id='delete-selected-button', disabled=True)])
        ], style={'display': 'flex', 'justifyContent': 'space-around', 'alignItems': 'center'}),
        html.Div(id='action-output-message', style={'marginTop': '15px', 'textAlign': 'center'}),
        html.Hr(),
        html.H2("Gerenciar Arquivo"),
        html.Div([ dcc.Upload(id='upload-data', children=html.Button('Carregar Arquivo')), html.A(html.Button("Salvar e Baixar"), id="download-link", href="/download/graph.txt") ], style={'textAlign': 'center', 'padding': '10px'})
    ])

app.layout = serve_layout

# =============================================================================
# 4. Callbacks (Lógica de Interação)
# =============================================================================

def _update_node_positions(cyto_elements):
    if not cyto_elements: return
    for element in cyto_elements:
        if 'position' in element and 'id' in element.get('data', {}):
            node_id = element['data']['id']
            if G.has_node(node_id):
                G.nodes[node_id]['position'] = element['position']

@app.callback(
    Output('cytoscape-graph', 'elements'),
    Output('action-output-message', 'children'),
    Output('cytoscape-graph', 'layout'),
    Output('source-node-store', 'data', allow_duplicate=True),
    Output('empty-graph-message', 'children'),
    Input('add-vertex-button', 'n_clicks'),
    Input('delete-selected-button', 'n_clicks'),
    Input('upload-data', 'contents'),
    Input('cytoscape-graph', 'tapNodeData'),
    State('cytoscape-graph', 'selectedNodeData'),
    State('cytoscape-graph', 'selectedEdgeData'),
    State('upload-data', 'filename'),
    State('cytoscape-graph', 'elements'),
    State('source-node-store', 'data'),
    State('connect-mode-store', 'data'),
    prevent_initial_call=True
)
def main_callback(
    add_v, del_s, upload_contents, tapped_node_data,
    sel_nodes, sel_edges, filename, cyto_elements, source_node_id, connect_mode_on
):
    global G
    ctx = dash.callback_context
    if not ctx.triggered: raise PreventUpdate
    prop_id = ctx.triggered[0]['prop_id']

    _update_node_positions(cyto_elements)
    msg, layout_output, new_source_node = "", dash.no_update, source_node_id

    if prop_id == 'add-vertex-button.n_clicks':
        node_ids = {int(n) for n in G.nodes if str(n).isdigit()}
        new_id = 0
        while new_id in node_ids: new_id += 1
        G.add_node(str(new_id))
        msg = html.Span(f"Vértice '{new_id}' adicionado.", style={'color': 'green'})

    elif prop_id == 'cytoscape-graph.tapNodeData':
        if connect_mode_on:
            target_node_id = tapped_node_data['id']
            if not source_node_id:
                new_source_node = target_node_id
                msg = html.Span(f"Nó de origem '{target_node_id}' selecionado.", style={'color': '#f5a442'})
            elif source_node_id == target_node_id:
                new_source_node = None
                msg = html.Span("Modo de conexão cancelado.", style={'color': 'grey'})
            else:
                if G.has_edge(source_node_id, target_node_id):
                    msg = html.Span("Aresta já existe.", style={'color': 'orange'})
                else:
                    G.add_edge(source_node_id, target_node_id, label='1')
                    msg = html.Span(f"Aresta de '{source_node_id}' a '{target_node_id}' criada.", style={'color': 'green'})
                new_source_node = None
        else:
            node_id = tapped_node_data['id']
            msg = html.Span(f"Nó '{node_id}' selecionado. Use 'Deletar' ou mude de modo.")

    elif prop_id == 'delete-selected-button.n_clicks':
        if not connect_mode_on and (sel_nodes or sel_edges):
            nodes_to_remove = {n['id'] for n in sel_nodes} if sel_nodes else set()
            edges_to_remove = [(e['source'], e['target']) for e in sel_edges] if sel_edges else []
            G.remove_nodes_from(nodes_to_remove)
            G.remove_edges_from(edges_to_remove)
            msg = html.Span("Elemento(s) removido(s).", style={'color': 'green'})
            if source_node_id in nodes_to_remove:
                new_source_node = None

    elif prop_id == 'upload-data.contents':
        _, content_string = upload_contents.split(',')
        with open(GRAPH_FILE_PATH, 'w') as f: f.write(base64.b64decode(content_string).decode('utf-8'))
        load_graph_data()
        msg = html.Span(f"Arquivo '{filename}' carregado com sucesso!", style={'color': 'green'})
        layout_output = {'name': 'circle', 'animate': True, 'animationDuration': 500}
        new_source_node = None

    save_graph_data()
    new_elements = nx_to_cytoscape(G)
    layout_output = {'name': 'preset', 'animate': True, 'animationDuration': 100} if layout_output == dash.no_update else layout_output
    empty_msg = "" if G.nodes else "Grafo vazio. Adicione um vértice para começar."

    return new_elements, msg, layout_output, new_source_node, empty_msg

@app.callback(
    Output('connect-mode-store', 'data'),
    Output('connect-mode-button', 'children'),
    Output('connect-mode-help-text', 'children'),
    Output('source-node-store', 'data', allow_duplicate=True),
    Input('connect-mode-button', 'n_clicks'),
    State('connect-mode-store', 'data'),
    prevent_initial_call=True
)
def toggle_connect_mode(n_clicks, is_on):
    new_mode_is_on = not is_on
    button_text = "Modo: Conexão" if new_mode_is_on else "Modo: Seleção"
    help_text = "(Clique em um nó, depois em outro)" if new_mode_is_on else "(Selecione elementos para deletar)"
    return new_mode_is_on, button_text, help_text, None # Reseta o nó de origem na troca de modo

@app.callback(
    Output('cytoscape-graph', 'stylesheet'),
    Input('source-node-store', 'data'),
    Input('connect-mode-store', 'data')
)
def update_stylesheet(source_node_id, connect_mode_on):
    stylesheet = [s.copy() for s in BASE_STYLESHEET]
    if connect_mode_on:
        # No modo de conexão, o feedback de seleção é uma borda laranja (para a origem) 
        # e a seleção padrão (azul) é desativada para não haver conflito visual.
        stylesheet.append({'selector': ':selected', 'style': {'overlay-opacity': 0}})
        if source_node_id:
            stylesheet.append({
                'selector': f'node[id = "{source_node_id}"]',
                'style': {'border-width': 3, 'border-color': '#f5a442'}
            })
    return stylesheet

@app.callback(
    Output('delete-selected-button', 'disabled'),
    Input('cytoscape-graph', 'selectedNodeData'),
    Input('cytoscape-graph', 'selectedEdgeData'),
    Input('connect-mode-store', 'data')
)
def toggle_delete_button(nodes, edges, connect_mode_on):
    if connect_mode_on:
        return True # Desativado no modo de conexão
    return not (nodes or edges)

@app.callback(
    Output('cytoscape-graph', 'layout', allow_duplicate=True),
    Input('home-button', 'n_clicks'),
    State('cytoscape-graph', 'elements'),
    prevent_initial_call=True
)
def reset_layout(n_clicks, cyto_elements):
    if not n_clicks: raise PreventUpdate
    _update_node_positions(cyto_elements)
    save_graph_data()
    return {'name': 'circle', 'padding': 10, 'animate': True, 'animationDuration': 500}

@server.route('/download/graph.txt')
def download_graph_file():
    return send_file(GRAPH_FILE_PATH, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))