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
    """Lê o arquivo de grafo, respeitando o número de vértices no cabeçalho."""
    if not os.path.exists(GRAPH_FILE_PATH) or os.path.getsize(GRAPH_FILE_PATH) == 0:
        return []

    with open(GRAPH_FILE_PATH, 'r') as f:
        lines = [line for line in f.read().splitlines() if line.strip()]
    
    if not lines or len(lines) < 1:
        return []

    header_parts = lines[0].split()
    if len(header_parts) != 2:
        return [] # Cabeçalho inválido

    try:
        num_vertices = int(header_parts[0])
    except ValueError:
        return [] # Número de vértices inválido

    G = nx.Graph()
    # 1. Adiciona todos os nós primeiro, com base no cabeçalho
    for i in range(num_vertices):
        G.add_node(str(i))

    # 2. Adiciona as arestas
    for line in lines[1:]:
        parts = line.split()
        if len(parts) == 3:
            G.add_edge(parts[0], parts[1], weight=parts[2])

    elements = []
    for node in G.nodes():
        elements.append({'data': {'id': node}})
        
    for edge in G.edges(data=True):
        elements.append({
            'data': {
                'source': edge[0],
                'target': edge[1],
                'label': str(edge[2].get('weight', 1))
            }
        })
            
    return elements

def save_graph_data(elements):
    """Salva os elementos no formato de texto, com nós isolados implícitos no contador."""
    if not elements:
        with open(GRAPH_FILE_PATH, 'w') as f:
            f.write("0 0\n")
        return

    all_nodes = set()
    edges_with_weights = []

    # Coleta todas as arestas e os nós, incluindo os isolados
    for ele in elements:
        if 'source' in ele['data']:
            source = ele['data']['source']
            target = ele['data']['target']
            weight = ele['data'].get('label', '1')
            edges_with_weights.append((source, target, weight))
            all_nodes.add(source)
            all_nodes.add(target)
        else:
             all_nodes.add(ele['data']['id'])
    
    # Garante que os nós sejam contados de 0 até o máximo id, sem pulos
    if not all_nodes:
        max_id = -1
    else:
        max_id = max(int(n) for n in all_nodes)
    
    num_vertices = max_id + 1

    with open(GRAPH_FILE_PATH, 'w') as f:
        f.write(f"{num_vertices} {len(edges_with_weights)}\n")
        # Escreve apenas as arestas, como definido no padrão
        for source, target, weight in edges_with_weights:
            f.write(f"{source} {target} {weight}\n")

# --- APLICAÇÃO DASH --- #

app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

def serve_layout():
    """Função que gera o layout dinamicamente a cada carregamento da página."""
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
            stylesheet=[ # Define o estilo visual dos elementos do grafo
                {
                    'selector': 'node', # Estilo para os Vértices
                    'style': {
                        'label': 'data(id)', # Usa o ID do vértice como seu rótulo
                        'text-valign': 'center',
                        'color': 'white',
                        'text-outline-color': '#888',
                        'text-outline-width': '2px' 
                    }
                },
                {
                    'selector': 'edge', # Estilo para as Arestas
                    'style': {
                        'label': 'data(label)', # Usa o campo 'label' (peso) como rótulo
                        'text-rotation': 'autorotate',
                        'text-margin-y': '-15px' # Desloca o rótulo para CIMA da aresta
                    }
                }
            ],
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
                html.Button('Adicionar Vértice', id='add-vertex-button', n_clicks=0)
            ], className='control-panel'),
            html.Div([
                html.H3("Aresta"),
                dcc.Input(id='edge-source-input', placeholder='Origem', type='text', style={'width': '80px'}),
                dcc.Input(id='edge-target-input', placeholder='Destino', type='text', style={'width': '80px', 'marginLeft':'5px'}),
                dcc.Input(id='edge-weight-input', placeholder='Peso', type='number', value=1, style={'width':'70px', 'marginLeft':'5px'}),
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

# Atribui a FUNÇÃO ao layout, para que seja chamada a cada recarregamento
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
    State('edge-source-input', 'value'),
    State('edge-target-input', 'value'),
    State('edge-weight-input', 'value'),
    State('cytoscape-graph', 'selectedNodeData'),
    State('cytoscape-graph', 'selectedEdgeData'),
    State('graph-elements-store', 'data'),
    State('upload-data', 'filename'),
    prevent_initial_call=True
)
def update_store_data(add_v_clicks, add_e_clicks, del_clicks, upload_contents, edge_source, edge_target, edge_weight, selected_nodes, selected_edges, elements, filename):
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    elements = (elements or []).copy()
    msg = ""

    try:
        if edge_source: edge_source = edge_source.strip()
        if edge_target: edge_target = edge_target.strip()

        if trigger_id == 'add-vertex-button':
            node_ids = {int(el['data']['id']) for el in elements if el['data'].get('id')}
            new_id = str(max(node_ids) + 1 if node_ids else 0)
            elements.append({'data': {'id': new_id}})
            save_graph_data(elements)
            msg = html.Span(f"Vértice '{new_id}' adicionado.", style={'color': 'green'})
        
        elif trigger_id == 'add-edge-button' and edge_source and edge_target:
            if edge_weight is None:
                raise ValueError("O peso da aresta não pode ser vazio.")

            node_ids = {el['data']['id'] for el in elements if el['data'].get('id')}
            if not edge_source in node_ids or not edge_target in node_ids:
                 raise ValueError("Ambos os vértices (origem e destino) devem existir.")
            
            existing_edges = {tuple(sorted((e['data']['source'], e['data']['target']))) for e in elements if 'source' in e['data']}
            new_edge = tuple(sorted((edge_source, edge_target)))
            if new_edge in existing_edges:
                raise ValueError(f"Aresta entre '{edge_source}' e '{edge_target}' já existe.")

            elements.append({'data': {'source': edge_source, 'target': edge_target, 'label': str(edge_weight)}})
            save_graph_data(elements)
            msg = html.Span(f"Aresta de '{edge_source}' para '{edge_target}' (Peso: {edge_weight}) adicionada.", style={'color': 'green'})

        elif trigger_id == 'delete-selected-button':
            if not selected_nodes and not selected_edges:
                raise PreventUpdate

            ids_to_remove = {n['id'] for n in selected_nodes} if selected_nodes else set()
            edges_to_remove = {tuple(sorted((e['data']['source'], e['data']['target']))) for e in selected_edges} if selected_edges else set()

            # Primeira passagem: remove os elementos selecionados
            temp_elements = []
            for elem in elements:
                if 'source' not in elem['data']:
                    if elem['data']['id'] not in ids_to_remove:
                        temp_elements.append(elem)
                else:
                    source_is_deleted = elem['data']['source'] in ids_to_remove
                    target_is_deleted = elem['data']['target'] in ids_to_remove
                    edge_is_selected = tuple(sorted((elem['data']['source'], elem['data']['target']))) in edges_to_remove
                    if not source_is_deleted and not target_is_deleted and not edge_is_selected:
                        temp_elements.append(elem)

            if len(temp_elements) == len(elements):
                raise PreventUpdate # Nada foi efetivamente removido

            # Segunda passagem: renumerar os nós para garantir a continuidade
            remaining_node_ids = sorted([int(el['data']['id']) for el in temp_elements if 'source' not in el['data']])
            id_map = {str(old_id): str(new_id) for new_id, old_id in enumerate(remaining_node_ids)}
            
            final_elements = []
            for elem in temp_elements:
                if 'source' not in elem['data']:
                    old_id = elem['data']['id']
                    elem['data']['id'] = id_map[old_id]
                    final_elements.append(elem)
                else:
                    old_source = elem['data']['source']
                    old_target = elem['data']['target']
                    elem['data']['source'] = id_map[old_source]
                    elem['data']['target'] = id_map[old_target]
                    final_elements.append(elem)

            elements = final_elements
            save_graph_data(elements)
            msg = html.Span("Elemento(s) removido(s) e IDs renumerados.", style={'color': 'green'})

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
