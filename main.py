import os
import networkx as nx
from flask import send_file
import dash
import dash_cytoscape as cyto
from dash import dcc, html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import base64

# --- CONFIGURAÇÃO --- #
GRAPH_FILE_PATH = 'data/graph.txt'

# --- FUNÇÕES AUXILIARES DE DADOS DO GRAFO --- #

def load_graph_data():
    """Lê o arquivo de grafo e retorna os elementos para o Cytoscape."""
    if not os.path.exists(GRAPH_FILE_PATH) or os.path.getsize(GRAPH_FILE_PATH) == 0:
        return []

    with open(GRAPH_FILE_PATH, 'r') as f:
        lines = [line for line in f.read().splitlines() if line.strip()]
    
    if not lines or len(lines) < 1:
        return []

    G = nx.Graph()
    for line in lines[1:]:
        parts = line.split()
        if len(parts) == 2:
            G.add_edge(parts[0], parts[1])
        elif len(parts) == 1:
            G.add_node(parts[0])

    elements = []
    for node in G.nodes():
        elements.append({'data': {'id': node, 'label': f'Vértice {node}'}})
        
    for edge in G.edges():
        elements.append({'data': {'source': edge[0], 'target': edge[1]}})
            
    return elements

def save_graph_data(elements):
    """Salva os elementos do Cytoscape no arquivo de texto do grafo."""
    if not elements:
        with open(GRAPH_FILE_PATH, 'w') as f:
            f.write("0 0\n")
        return

    nodes = {ele['data']['id'] for ele in elements if 'source' not in ele['data']}
    edges = [(ele['data']['source'], ele['data']['target']) for ele in elements if 'source' in ele['data']]

    for source, target in edges:
        nodes.add(source)
        nodes.add(target)

    nodes_in_edges = set()
    for source, target in edges:
        nodes_in_edges.add(source)
        nodes_in_edges.add(target)
    
    isolated_nodes = nodes - nodes_in_edges

    with open(GRAPH_FILE_PATH, 'w') as f:
        f.write(f"{len(nodes)} {len(edges)}\n")
        for source, target in edges:
            f.write(f"{source} {target}\n")
        for node in isolated_nodes:
            f.write(f"{node}\n")

# --- APLICAÇÃO DASH --- #

app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

def serve_layout():
    initial_elements = load_graph_data()
    return html.Div([
        dcc.Store(id='graph-elements-store', data=initial_elements),

        html.Div([
            html.H1("Editor de Grafo Interativo", style={'display': 'inline-block', 'marginRight': '20px'}),
            html.Button('Redefinir Visualização', id='home-button', n_clicks=0)
        ]),
        
        cyto.Cytoscape(
            id='cytoscape-graph',
            elements=initial_elements,
            style={'width': '100%', 'height': '450px'},
            layout={'name': 'circle'},
            wheelSensitivity=0.1
        ),
        html.Div(id='empty-graph-message', children="Grafo vazio. Adicione um vértice para começar." if not initial_elements else "",
                 style={'textAlign': 'center', 'padding': '20px', 'color': 'grey'}),

        html.Hr(),

        html.Div([
            html.Div([
                html.H3("Vértice"),
                dcc.Input(id='vertex-id-input', placeholder='ID do Vértice', type='text'),
                html.Button('Adicionar Vértice', id='add-vertex-button', n_clicks=0, style={'marginLeft':'10px'})
            ], className='control-panel'),
            html.Div([
                html.H3("Aresta"),
                dcc.Input(id='edge-source-input', placeholder='Origem', type='text', style={'width': '80px'}),
                dcc.Input(id='edge-target-input', placeholder='Destino', type='text', style={'width': '80px', 'marginLeft':'5px'}),
                html.Button('Adicionar Aresta', id='add-edge-button', n_clicks=0, style={'marginLeft':'10px'})
            ], className='control-panel'),
            html.Div([
                html.H3("Deletar"),
                html.P("(Clique em um elemento no grafo)", style={'fontSize': '12px', 'color': 'grey'}),
                html.Button('Deletar Elemento Selecionado', id='delete-selected-button', n_clicks=0, disabled=True)
            ], className='control-panel')
        ], style={'display': 'flex', 'justifyContent': 'space-around'}),

        html.Div(id='action-output-message', style={'marginTop': '15px', 'textAlign': 'center'}),
        html.Hr(),

        html.H2("Gerenciar Arquivo", style={'textAlign': 'center'}),
        html.Div([
            dcc.Upload(id='upload-data', children=html.Button('Carregar Arquivo de Grafo')),
            html.A(html.Button("Salvar e Baixar Grafo"), id="download-link", href="/download/graph.txt", style={'marginLeft': '20px'})
        ], style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center', 'padding': '10px'})
    ])

app.layout = serve_layout

# --- CALLBACKS --- #

@app.callback(
    Output('cytoscape-graph', 'elements'),
    Output('empty-graph-message', 'children'),
    Input('graph-elements-store', 'data')
)
def update_view_from_store(data):
    message = "Grafo vazio. Adicione um vértice para começar." if not data else ""
    return data, message

@app.callback(
    Output('graph-elements-store', 'data'),
    Output('action-output-message', 'children'),
    Input('add-vertex-button', 'n_clicks'),
    Input('add-edge-button', 'n_clicks'),
    Input('delete-selected-button', 'n_clicks'),
    Input('upload-data', 'contents'),
    State('vertex-id-input', 'value'),
    State('edge-source-input', 'value'),
    State('edge-target-input', 'value'),
    State('cytoscape-graph', 'selectedNodeData'),
    State('cytoscape-graph', 'selectedEdgeData'),
    State('graph-elements-store', 'data'),
    State('upload-data', 'filename'),
    prevent_initial_call=True
)
def update_store_data(add_v, add_e, del_s, upload_contents, vertex_id, edge_source, edge_target, selected_nodes, selected_edges, elements, filename):
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    elements = (elements or []).copy()
    msg = ""

    try:
        if vertex_id: vertex_id = vertex_id.strip()
        if edge_source: edge_source = edge_source.strip()
        if edge_target: edge_target = edge_target.strip()

        if trigger_id == 'add-vertex-button' and vertex_id:
            node_ids = {el['data']['id'] for el in elements if 'source' not in el['data']}
            if vertex_id in node_ids:
                raise ValueError(f"Vértice '{vertex_id}' já existe.")
            elements.append({'data': {'id': vertex_id, 'label': f'Vértice {vertex_id}'}})
            save_graph_data(elements)
            msg = html.Span(f"Vértice '{vertex_id}' adicionado.", style={'color': 'green'})
        
        elif trigger_id == 'add-edge-button' and edge_source and edge_target:
            node_ids = {el['data']['id'] for el in elements if 'source' not in el['data']}
            if not edge_source in node_ids or not edge_target in node_ids:
                 raise ValueError("Ambos os vértices (origem e destino) devem existir.")
            
            existing_edges = {tuple(sorted((e['data']['source'], e['data']['target']))) for e in elements if 'source' in e['data']}
            new_edge = tuple(sorted((edge_source, edge_target)))
            if new_edge in existing_edges:
                raise ValueError(f"Aresta entre '{edge_source}' e '{edge_target}' já existe.")

            elements.append({'data': {'source': edge_source, 'target': edge_target}})
            save_graph_data(elements)
            msg = html.Span(f"Aresta de '{edge_source}' para '{edge_target}' adicionada.", style={'color': 'green'})

        elif trigger_id == 'delete-selected-button':
            original_len = len(elements)
            ids_to_remove = {n['id'] for n in selected_nodes} if selected_nodes else set()
            edges_to_remove = {tuple(sorted((e['source'], e['target']))) for e in selected_edges} if selected_edges else set()

            new_elements = []
            for elem in elements:
                if 'source' not in elem['data']:
                    if elem['data']['id'] not in ids_to_remove:
                        new_elements.append(elem)
                else:
                    source_is_deleted = elem['data']['source'] in ids_to_remove
                    target_is_deleted = elem['data']['target'] in ids_to_remove
                    edge_is_selected = tuple(sorted((elem['data']['source'], elem['data']['target']))) in edges_to_remove
                    
                    if not source_is_deleted and not target_is_deleted and not edge_is_selected:
                        new_elements.append(elem)
            
            if len(new_elements) < original_len:
                elements = new_elements
                save_graph_data(elements)
                msg = html.Span("Elemento(s) selecionado(s) removido(s).", style={'color': 'green'})
            else:
                raise PreventUpdate

        elif trigger_id == 'upload-data' and upload_contents:
            content_type, content_string = upload_contents.split(',')
            decoded = base64.b64decode(content_string)
            file_content = decoded.decode('utf-8')
            with open(GRAPH_FILE_PATH, 'w') as f: f.write(file_content)
            elements = load_graph_data()
            msg = html.Span(f"Arquivo '{filename}' carregado com sucesso!", style={'color': 'green'})

        return elements, msg
    
    except (ValueError, IndexError, Exception) as e:
        return dash.no_update, html.Span(f"Erro: {e}", style={'color': 'red'})


@app.callback(
    Output('delete-selected-button', 'disabled'),
    Input('cytoscape-graph', 'selectedNodeData'),
    Input('cytoscape-graph', 'selectedEdgeData')
)
def toggle_delete_button(nodes, edges):
    return not (nodes or edges)

@app.callback(
    Output('cytoscape-graph', 'layout'),
    Input('home-button', 'n_clicks'),
    prevent_initial_call=True
)
def reset_layout(n_clicks):
    return {'name': 'circle', 'padding': 10, 'animate': True, '_nocache': n_clicks}

@server.route('/download/graph.txt')
def download_graph_file():
    return send_file(GRAPH_FILE_PATH, as_attachment=True)

# --- PONTO DE ENTRADA --- #
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
