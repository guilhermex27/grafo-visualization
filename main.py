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
import dash_bootstrap_components as dbc

import networkx as nx

from scripts.bfs import bfs_snapshots
from scripts.dfs import dfs_snapshots

# =============================================================================
# 1. Backend: NetworkX e Configurações
# =============================================================================

G = nx.Graph()
GRAPH_FILE_PATH = 'data/graph.txt'

BASE_STYLESHEET = [
    {
        'selector': 'node',
        'style': {
            'label': 'data(id)',
            'text-valign': 'center', 'color': '#333',
            'text-outline-color': '#333', 'text-outline-width': '1px',
            'background-color': 'white', 'border-width': 4, 'border-color': '#999998',
            'transition-property': 'background-color, border-width, border-color, width, height',
            'transition-duration': '0.2s' 
        }
    },
    {
        'selector': 'edge',
        'style': {
            'label': 'data(label)', 'color': 'black', 'font-weight': '800',
            'text-margin-y': '-20vh', 'text-margin-x': '0',
            'transition-property': 'line-color, width, target-arrow-color',
            'transition-duration': '0.2s'
        }
    },
    {
        'selector': ':selected',
        'style': {
            'border-width': 4, 'border-color': '#42a5f5',
            'background-color': '#64b5f6' # Fica mais claro quando selecionado
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
        s = attrs.get('real_source', source)
        t = attrs.get('real_target', target)
        cy_edge = {'data': {'source': str(s), 'target': str(t)}}
        if attrs.get('label'):
            cy_edge['data']['label'] = attrs['label']
        cy_elements.append(cy_edge)
    return cy_elements

def obter_propriedades_grafo(graph_obj):
    if graph_obj.number_of_nodes() == 0:
        return "Vazio"
        
    props = []
    
    # 1. Simples vs Pseudografo (Checa laços)
    tem_lacos = nx.number_of_selfloops(graph_obj) > 0
    if tem_lacos:
        props.append("Pseudografo")
    else:
        props.append("Simples")
        
    # 2. Conectividade e Ciclos
    if graph_obj.is_directed():
        if nx.is_strongly_connected(graph_obj):
            props.append("Fortemente Conexo")
        elif nx.is_weakly_connected(graph_obj):
            props.append("Fracamente Conexo")
        else:
            props.append("Desconexo")
            
        if nx.is_directed_acyclic_graph(graph_obj):
            props.append("DAG (Acíclico)")
    else:
        if nx.is_connected(graph_obj):
            props.append("Conexo")
        else:
            props.append("Desconexo")
            
        if nx.is_tree(graph_obj):
            props.append("Árvore")
        elif nx.is_forest(graph_obj):
            props.append("Floresta")
            
    # 3. Bipartido
    if nx.is_bipartite(graph_obj):
        props.append("Bipartido")
        
    # 4. Regular (Todos os nós têm o mesmo grau)
    graus = [d for n, d in graph_obj.degree()]
    if graus and len(set(graus)) == 1:
        props.append("Regular")
        
    # 5. Completo
    n = graph_obj.number_of_nodes()
    e = graph_obj.number_of_edges()
    if n > 1 and not tem_lacos:
        max_edges = n * (n - 1) if graph_obj.is_directed() else n * (n - 1) // 2
        if e == max_edges:
            props.append("Completo")
            
    return ", ".join(props)

def load_graph_data():
    global G

    is_directed = G.is_directed() if hasattr(G, 'is_directed') else False
    
    if not os.path.exists(GRAPH_FILE_PATH) or os.path.getsize(GRAPH_FILE_PATH) == 0:
        G = nx.DiGraph() if is_directed else nx.Graph()
        return
        
    with open(GRAPH_FILE_PATH, 'r') as f:
        lines = [line.strip() for line in f.read().splitlines() if line.strip()]
        
    G.clear()
    if not lines: return
    
    G = nx.DiGraph() if is_directed else nx.Graph()

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
            s = data.get('real_source', source)
            t = data.get('real_target', target)
            f.write(f"{s} {t} {data.get('label', '1')}\n")

# =============================================================================
# 3. Layout da Aplicação Dash
# =============================================================================

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server

def serve_layout():
    os.makedirs(os.path.dirname(GRAPH_FILE_PATH), exist_ok=True)
    load_graph_data()
    initial_elements = nx_to_cytoscape(G)

    tipo_dir_init = "Orientado" if G.is_directed() else "Não Orientado"
    tipo_peso_init = "Ponderado" 
    propriedades_init = obter_propriedades_grafo(G)
    
    initial_info_children = [
        html.B("Vértices: "), f"{G.number_of_nodes()}", html.Br(),
        html.B("Arestas: "), f"{G.number_of_edges()}", html.Br(),
        html.B("Direção: "), tipo_dir_init, html.Br(),
        html.B("Peso: "), tipo_peso_init, html.Br(),
        html.B("Propriedades: "), propriedades_init
    ]

    return dbc.Container(fluid=True, style={'padding': '10px', 'overflowX': 'hidden'}, children=[
        dcc.Store(id='source-node-store', data=None),
        dcc.Store(id='connect-mode-store', data=False),
        dcc.Store(id='aresta-edit-store', data=None),
        dcc.Store(id='edge-edit-store', data=None),
        dcc.Store(id='snapshots-store', data=None),       
        dcc.Store(id='current-frame-store', data=0),      
        dcc.Store(id='is-playing-store', data=False),     
        dcc.Interval(id='animation-interval', interval=1000, n_intervals=0, disabled=True), 

        # MODAL ORIGINAL MANTIDO
        html.Div(id='modal-editar-peso', className='modal', style={'display': 'none'}, children=[
            html.Div(className='modal-box', children=[
                html.H3("Editar Peso da Aresta", style={'marginTop': '0'}),
                dcc.Input(id='modal-input-peso', type='text', style={'width': '100%', 'marginBottom': '20px', 'padding': '10px', 'boxSizing': 'border-box', 'fontSize': '14px'}),
                html.Div(style={'display': 'flex', 'justifyContent': 'space-between'}, children=[
                    html.Button('Cancelar', id='btn-cancelar-peso', style={'backgroundColor': '#f44336', 'color': 'white', 'flex': '1', 'marginRight': '5px'}),
                    html.Button('Salvar', id='btn-salvar-peso', style={'backgroundColor': '#4CAF50', 'color': 'white', 'flex': '1', 'marginLeft': '5px'})
                ])
            ])
        ]),

        # LINHA 1: CABEÇALHO ORIGINAL
        dbc.Row(id='top-buttons-container', style={'display': 'flex', 'justifyContent': 'start', 'transition': 'opacity 0.3s', 'marginBottom': '10px'}, children=[
            dbc.Col(html.H1("Editor de Grafo Interativo", style={'paddingLeft': '10px','paddingRight': '20px', 'margin': '0'}), width=8),
            dbc.Col(style={'display': 'flex', 'justifyContent': 'flex-end'}, width=4, children=[
                html.Div([html.Button(id='home-button')], className='image-container'),
                html.Div([html.A(html.Button(style={'backgroundImage': 'url(assets/download.png)','backgroundPositionX': '1px','backgroundPositionY': '7px'}), id="download-link", href="/download/graph.txt")], className='image-container'),
                html.Div(children=[dcc.Upload(id='upload-data', children=html.Button(style={'backgroundImage': 'url(assets/upload.png)','backgroundPositionX': '-1px','marginTop':'13px'}))], className='image-container')
            ])
        ]),

        # LINHA 2: GRAFO E PAINEL
       # LINHA 2: GRAFO E PAINEL
        # Adicionado overflowX: hidden para não criar barra de rolagem quando o painel deslizar pra fora
        dbc.Row(style={'margin': '0', 'position': 'relative', 'overflowX': 'hidden'}, children=[

            # LADO ESQUERDO: O GRAFO (Agora sempre fixo em 12 colunas, nunca mais muda de tamanho!)
            dbc.Col(id='coluna-grafo', width=12, style={'position': 'relative', 'border': '1px solid #ccc', 'borderRadius': '8px', 'backgroundColor': '#fff', 'height': '85vh', 'padding': '0'}, children=[
                cyto.Cytoscape(
                    id='cytoscape-graph', elements=initial_elements, stylesheet=BASE_STYLESHEET,
                    style={'width': '100%', 'height': '100%'},
                    layout={'name': 'circle', 'animate': True, 'animationDuration': 500},
                    wheelSensitivity=0.1
                ),
                html.Div(id='empty-graph-message', style={'position': 'absolute', 'top': '10px', 'width': '100%', 'textAlign': 'center', 'pointerEvents': 'none'}),
                html.Div(id='action-output-message', style={'position': 'absolute', 'bottom': '10px', 'width': '100%', 'textAlign': 'center', 'pointerEvents': 'none', 'fontWeight': 'bold'}),
                html.Div(id='keyboard-listener-dummy', style={'display': 'none'}),
                html.Button(id='btn-hidden-center', n_clicks=0, style={'display': 'none'}),

                html.Div([html.Button(id='btn-info-grafo', n_clicks=0)], className='info'),
                html.Div(id='card-info-grafo', className='card-info', style={'display': 'none'}, children=[
                    html.H4("Informações Gerais", style={'marginTop': '0', 'marginBottom': '10px', 'color': '#333'}),
                    html.Div(id='texto-info-grafo', children=initial_info_children, style={'fontSize': '14px', 'lineHeight': '1.6', 'color': '#444'}),
                    html.Div(id='info-detalhes-elemento', style={'display': 'none', 'marginTop': '10px', 'paddingTop': '10px', 'borderTop': '1px solid #ccc', 'fontSize': '13px', 'lineHeight': '1.6', 'color': '#555'})
                ]),

                html.Div(id='card-execucao-algo', style={'display': 'none', 'position': 'absolute', 'top': '10px', 'right': '10px', 'zIndex': 50, 'backgroundColor': 'rgba(255, 255, 255, 0.95)', 'border': '2px solid #4CAF50', 'borderRadius': '8px', 'padding': '15px', 'boxShadow': '0 4px 15px rgba(0,0,0,0.2)', 'minWidth': '220px', 'maxWidth': '300px'}, children=[
                    html.H4("⚙️ Execução: Passo a Passo", style={'marginTop': '0', 'marginBottom': '10px', 'color': '#2E7D32'}),
                    html.Div(id='texto-narracao-algo', style={'fontSize': '14px', 'fontWeight': 'bold', 'color': '#333', 'marginBottom': '10px', 'fontStyle': 'italic'}),
                    html.Hr(style={'margin': '5px 0', 'border': '0.5px solid #ccc'}),
                    html.Div(id='texto-variaveis-algo', style={'fontSize': '13px', 'lineHeight': '1.6', 'color': '#444'})
                ]),

                html.Div(id='player-flutuante', className='player', style={'display': 'none'}, children=[
                    html.Div(style={'display': 'flex', 'gap': '10px', 'marginBottom': '10px', 'width': '100%', 'justifyContent': 'space-between'}, children=[
                        html.Button(id='btn-stop-algo', style={'backgroundImage': 'url(assets/stop.png)'}),
                        html.Button(id='btn-prev-algo', style={'backgroundImage': 'url(assets/previous.png)'}),
                        html.Button(id='btn-play-algo', style={'backgroundImage': 'url(assets/play.png)'}),
                        html.Button(id='btn-step-algo', style={'backgroundImage': 'url(assets/next.png)'}),
                    ]),
                    html.Div(style={'fontSize': '12px', 'marginBottom': '15px', 'color': '#333', 'fontWeight': 'bold'}, children="Velocidade da Animação:"),
                    html.Div(style={'width': '95%', 'paddingBottom': '10px'}, children=[
                        dcc.Slider(
                            id='slider-velocidade', min=0, max=4, step=None, value=2, 
                            marks={0: {'label': '0.25x', 'style': {'fontWeight': 'bold'}}, 1: {'label': '0.5x', 'style': {'fontWeight': 'bold'}}, 2: {'label': '1x', 'style': {'fontWeight': 'bold'}}, 3: {'label': '1.5x', 'style': {'fontWeight': 'bold'}}, 4: {'label': '2x', 'style': {'fontWeight': 'bold'}}}
                        )
                    ])
                ]),
                # A SETINHA SAIU DAQUI!
            ]),

            # LADO DIREITO: O PAINEL (Agora é um elemento flutuante que desliza)
            html.Div(id='coluna-painel', style={
                'position': 'absolute', 'right': '0', 'top': '0', 
                'width': '300px', 'height': '85vh', 'padding': '0',
                'transition': 'transform 0.3s ease', 'zIndex': 100,
                'transform': 'translateX(0%)' # <--- INICIA TOTALMENTE FORA DA TELA
            }, children=[
                
                html.Div(className='btn-paineis', style={'position': 'absolute', 'left': '-31px', 'top': '50%', 'transform': 'translateY(-50%)'}, children=[
                    html.Button('◀', id='toggle-painel-btn', n_clicks=0) # <--- SETA APONTANDO PARA PUXAR
                ]),

                # CONTEÚDO DO PAINEL
                html.Div(id='conteudo-paineis', className='container-paineis', style={'width': '100%', 'height': '100%', 'overflowY': 'auto', 'boxSizing': 'border-box'}, children=[
                    html.Div(className='cartao-painel', children=[
                        html.H3("Vértice", style={'marginTop': '0', 'fontSize': '16px'}),
                        html.Button('Adicionar Vértice', id='add-vertex-button', style={'width': '100%'})
                    ]),
                    html.Div(className='cartao-painel', children=[
                        html.H3("Interação", style={'marginTop': '0', 'fontSize': '16px'}),
                        html.Button('Modo: Seleção', id='connect-mode-button', style={'width': '100%'}),
                        html.P(id='connect-mode-help-text', children="(Selecione elementos para deletar)", style={'fontSize': '12px', 'color': 'grey', 'marginBottom': '0'})
                    ]),
                    html.Div(className='cartao-painel', children=[
                        html.H3("Deletar", style={'marginTop': '0', 'fontSize': '16px'}),
                        html.Button('Deletar Selecionado', id='delete-selected-button', disabled=True, style={'width': '100%'})
                    ]),
                    html.Div(className='cartao-painel', children=[
                        html.H3("Configurações", style={'marginTop': '0', 'fontSize': '16px'}),
                        dcc.RadioItems(id='toggle-direcao', options=[{'label': ' Não Orientado', 'value': 'nao_orientado'}, {'label': ' Orientado', 'value': 'orientado'}], value='nao_orientado', labelStyle={'display': 'block', 'textAlign': 'left', 'marginBottom': '5px'}),
                        html.Hr(style={'margin': '5px 0', 'border': '0.5px solid #ccc'}),
                        dcc.RadioItems(id='toggle-peso', options=[{'label': ' Com Peso', 'value': 'com_peso'}, {'label': ' Sem Peso', 'value': 'sem_peso'}], value='com_peso', labelStyle={'display': 'block', 'textAlign': 'left'})
                    ]),
                    html.Div(className='cartao-painel', children=[
                        html.H3("Algoritmos", style={'marginTop': '0', 'fontSize': '16px'}),
                        dcc.Dropdown(id='dropdown-algo', options=[{'label': 'BFS (Busca em Largura)', 'value': 'bfs'}, {'label': 'DFS (Busca em Profundidade)', 'value': 'dfs'}], placeholder="Escolha o Algoritmo", style={'marginBottom': '5px', 'fontSize': '12px'}),
                        dcc.Dropdown(id='dropdown-source', placeholder="Vértice de Origem", style={'marginBottom': '5px', 'fontSize': '12px'}),
                        html.Button('Carregar Algoritmo', id='btn-carregar-algo', style={'width': '100%', 'backgroundColor': '#2196F3', 'color': 'white', 'padding': '8px', 'borderRadius': '4px', 'border': 'none', 'cursor': 'pointer'})
                    ])
                ])
            ])
        ])
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
    Output('toggle-direcao', 'value'),
    Output('upload-data', 'contents'),
    Output('texto-info-grafo', 'children'),
    Input('add-vertex-button', 'n_clicks'),
    Input('delete-selected-button', 'n_clicks'),
    Input('upload-data', 'contents'),
    Input('cytoscape-graph', 'tapNodeData'),
    Input('cytoscape-graph', 'tapEdgeData'),
    Input('btn-salvar-peso', 'n_clicks'),
    Input('btn-hidden-center', 'n_clicks'),
    Input('toggle-direcao', 'value'),
    State('cytoscape-graph', 'selectedNodeData'),
    State('cytoscape-graph', 'selectedEdgeData'),
    State('upload-data', 'filename'),
    State('cytoscape-graph', 'elements'),
    State('source-node-store', 'data'),
    State('connect-mode-store', 'data'),
    State('aresta-edit-store', 'data'),
    State('modal-input-peso', 'value'),
    State('toggle-peso', 'value'),
    State('snapshots-store', 'data'),
    State('modal-editar-peso', 'style'),
    prevent_initial_call=True
)
def main_callback(
    add_v, del_s, upload_contents, tapped_node_data, tapped_edge_data, btn_salvar_peso, btn_hidden_center, toggle_direcao,
    sel_nodes, sel_edges, filename, cyto_elements, source_node_id, connect_mode_on,
    aresta_edit_store_data, modal_input_value, toggle_peso, snaps, modal_style
):
    global G
    ctx = dash.callback_context
    if not ctx.triggered: raise PreventUpdate
    prop_id = ctx.triggered[0]['prop_id']

    _update_node_positions(cyto_elements)
    
    msg = dash.no_update
    layout_output = dash.no_update
    new_source_node = source_node_id
    graph_changed = False
    direcao_output = dash.no_update
    upload_reset = dash.no_update

    if prop_id == 'add-vertex-button.n_clicks':
        node_ids = {int(n) for n in G.nodes if str(n).isdigit()}
        new_id = 0
        while new_id in node_ids: new_id += 1
        G.add_node(str(new_id))
        msg = html.Span(f"Vértice '{new_id}' adicionado.", style={'color': 'green'})
        graph_changed = True

    elif prop_id == 'cytoscape-graph.tapNodeData':
        if connect_mode_on:
            if tapped_node_data:
                target_node_id = tapped_node_data['id']
                if not source_node_id:
                    new_source_node = target_node_id
                    msg = html.Span(f"Vértice de origem {target_node_id} selecionado.", style={'color': '#f5a442'})
                elif source_node_id == target_node_id:
                    if G.has_edge(source_node_id, target_node_id):
                        msg = html.Span("Laço já existe neste vértice.", style={'color': 'orange'})
                    else:
                        G.add_edge(source_node_id, target_node_id, label='1')
                        G.edges[source_node_id, target_node_id]['real_source'] = source_node_id
                        G.edges[source_node_id, target_node_id]['real_target'] = target_node_id
                        msg = html.Span(f"Laço criado no vértice {source_node_id}.", style={'color': 'green'})
                        graph_changed = True
                    new_source_node = None
                else:
                    if G.has_edge(source_node_id, target_node_id):
                        msg = html.Span("Aresta já existe.", style={'color': 'orange'})
                    else:
                        G.add_edge(source_node_id, target_node_id, label='1')
                        msg = html.Span(f"Aresta de {source_node_id} a {target_node_id} criada.", style={'color': 'green'})
                        graph_changed = True
                    new_source_node = None
        else:
            if tapped_node_data:
                node_id = tapped_node_data['id']
                msg = html.Span(f"Vértice {node_id} selecionado.")
            
    elif prop_id == 'cytoscape-graph.tapEdgeData':
        if not connect_mode_on and tapped_edge_data:
            source = tapped_edge_data['source']
            target = tapped_edge_data['target']
            msg = html.Span(f"Aresta {source}-{target} selecionada.")

    elif prop_id == 'delete-selected-button.n_clicks':
        if snaps:
            # Se o filme estiver rodando, ignora a tecla e avisa o usuário
            msg = html.Span("Bloqueado: Não é possível deletar durante a animação.", style={'color': 'red'})
        elif modal_style and modal_style.get('display') == 'flex':
            # --- NOVA TRAVA: Ignora o Delete/Backspace se o usuário estiver digitando o peso! ---
            msg = dash.no_update
        elif not connect_mode_on and (sel_nodes or sel_edges):
            nodes_to_remove = {n['id'] for n in sel_nodes} if sel_nodes else set()
            edges_to_remove = [(e['source'], e['target']) for e in sel_edges] if sel_edges else []
            G.remove_nodes_from(nodes_to_remove)
            G.remove_edges_from(edges_to_remove)
            msg = html.Span("Elemento(s) removido(s).", style={'color': 'green'})
            graph_changed = True
            if source_node_id in nodes_to_remove:
                new_source_node = None
    
    elif prop_id == 'btn-salvar-peso.n_clicks':
        if aresta_edit_store_data and modal_input_value is not None:
            src = aresta_edit_store_data['source']
            tgt = aresta_edit_store_data['target']
            novo_peso_str = str(modal_input_value).strip()

            try:
                novo_peso_int = int(novo_peso_str)
                
                if G.has_edge(src, tgt):
                    G.edges[src, tgt]['label'] = str(novo_peso_int)
                    msg = html.Span(f"Peso atualizado para {novo_peso_int}", style={'color': 'green'})
                    graph_changed = True
            except ValueError:
                msg = html.Span("Erro: O peso deve ser um número inteiro.", style={'color': 'red'})

    elif prop_id == 'upload-data.contents':
        if upload_contents:
            _, content_string = upload_contents.split(',')
            decoded = base64.b64decode(content_string).decode('utf-8')
            
            linhas = [linha.strip() for linha in decoded.splitlines() if linha.strip()]
            
            # --- 1. VARIÁVEIS DE CONTROLE DA VALIDAÇÃO ---
            arquivo_valido = True
            msg_erro = ""
            arestas_vistas = set()
            vertices_unicos = set() # <--- Rastreia os vértices
            tem_ida_e_volta = False
            qtd_arestas_reais = 0   # <--- Conta as linhas de arestas
            v_header = 0
            e_header = 0
            
            # --- 2. VALIDAÇÃO DO CABEÇALHO ---
            if not linhas:
                arquivo_valido, msg_erro = False, "O arquivo está vazio."
            else:
                cabecalho = linhas[0].split()
                if len(cabecalho) != 2:
                    arquivo_valido, msg_erro = False, "Cabeçalho inválido. Use: <qtd_vertices> <qtd_arestas>"
                else:
                    try:
                        v_header = int(cabecalho[0])
                        e_header = int(cabecalho[1])
                    except ValueError:
                        arquivo_valido, msg_erro = False, "O cabeçalho deve conter apenas números inteiros."

            # --- 3. VALIDAÇÃO DAS LINHAS (ARESTAS E PESOS) ---
            if arquivo_valido:
                for i, linha in enumerate(linhas[1:], start=2):
                    partes = linha.split()
                    
                    if len(partes) not in [2, 3]:
                        arquivo_valido, msg_erro = False, f"Erro na linha {i}: A linha deve ter 2 ou 3 colunas."
                        break
                    
                    try:
                        u = int(partes[0])
                        v = int(partes[1])
                        if len(partes) == 3:
                            peso = int(partes[2]) 
                    except ValueError:
                        arquivo_valido, msg_erro = False, f"Erro na linha {i}: Vértices e pesos devem ser números inteiros."
                        break
                    
                    # Guarda os vértices únicos e conta a aresta
                    vertices_unicos.add(str(u))
                    vertices_unicos.add(str(v))
                    qtd_arestas_reais += 1
                    
                    if (str(v), str(u)) in arestas_vistas:
                        tem_ida_e_volta = True
                    arestas_vistas.add((str(u), str(v)))

            # --- 3.5. VALIDAÇÃO DE INTEGRIDADE (CABEÇALHO VS DADOS) ---
            if arquivo_valido:
                if qtd_arestas_reais != e_header:
                    arquivo_valido, msg_erro = False, f"Inconsistência: Cabeçalho diz {e_header} arestas, mas há {qtd_arestas_reais} lidas."
                elif len(vertices_unicos) > v_header:
                    arquivo_valido, msg_erro = False, f"Inconsistência: Cabeçalho diz {v_header} vértices, mas as arestas usam {len(vertices_unicos)} distintos."

            # --- 4. EXECUÇÃO OU BLOQUEIO ---
            if arquivo_valido:
                with open(GRAPH_FILE_PATH, 'w') as f: 
                    f.write(decoded)
                
                if tem_ida_e_volta and toggle_direcao == 'nao_orientado':
                    G = nx.DiGraph() 
                    direcao_output = 'orientado'
                    msg = html.Span("Arquivo carregado (Alterado para Orientado automaticamente!)", style={'color': 'blue'})
                else:
                    msg = html.Span("Arquivo carregado com sucesso!", style={'color': 'green'})
                    
                load_graph_data()
                layout_output = {'name': 'circle', 'animate': True, 'animationDuration': 500}
                new_source_node = None
                graph_changed = True
            else:
                msg = html.Span(f"Falha ao carregar: {msg_erro}", style={'color': 'red'})

            upload_reset = None
    
    elif prop_id == 'btn-hidden-center.n_clicks':
        if btn_hidden_center:
            layout_output = {
                'name': 'preset', 
                'fit': True,        
                'padding': 30,      
                'animate': True, 
                'animationDuration': 500,
                'refresh_trigger': f"zoom_{btn_hidden_center}"
            }

    elif prop_id == 'toggle-direcao.value':
        is_directed = (toggle_direcao == 'orientado')
        
        if is_directed and not G.is_directed():
            novo_G = nx.DiGraph()
            novo_G.add_nodes_from(G.nodes(data=True))
            # Usa a memória fotográfica para apontar a seta pro lado certo!
            for u, v, attrs in G.edges(data=True):
                s = attrs.get('real_source', u)
                t = attrs.get('real_target', v)
                novo_G.add_edge(s, t, **attrs)
            G = novo_G
            msg = html.Span("Grafo alterado para Orientado.", style={'color': 'blue'})
            graph_changed = True
            
        elif not is_directed and G.is_directed():
            novo_G = nx.Graph()
            novo_G.add_nodes_from(G.nodes(data=True))
            
            for u, v, data in G.edges(data=True):
                try:
                    peso_atual = int(data.get('label', '1'))
                except ValueError:
                    peso_atual = 1
                    
                if novo_G.has_edge(u, v):
                    try:
                        peso_existente = int(novo_G.edges[u, v].get('label', '1'))
                    except ValueError:
                        peso_existente = 1
                        
                    if peso_atual < peso_existente:
                        novo_G.edges[u, v]['label'] = str(peso_atual)
                        # O peso atual venceu! Atualiza a memória com a direção dele
                        novo_G.edges[u, v]['real_source'] = u
                        novo_G.edges[u, v]['real_target'] = v
                else:
                    data_copy = data.copy()
                    # Aresta nova! Grava a direção inicial dela
                    data_copy['real_source'] = u
                    data_copy['real_target'] = v
                    novo_G.add_edge(u, v, **data_copy)
                    
            G = novo_G
            msg = html.Span("Grafo alterado para Não Orientado.", style={'color': 'blue'})
            graph_changed = True

    if graph_changed:
        save_graph_data()
        new_elements = nx_to_cytoscape(G)
        empty_msg = "" if G.nodes else "Grafo vazio. Adicione um vértice para começar."
        
        if layout_output == dash.no_update:
            layout_output = {'name': 'preset', 'animate': True, 'animationDuration': 100}
    else:
        new_elements = dash.no_update
        empty_msg = dash.no_update

    tipo_dir = "Orientado" if G.is_directed() else "Não Orientado"
    tipo_peso = "Não Ponderado" if toggle_peso == 'sem_peso' else "Ponderado"
    propriedades_atuais = obter_propriedades_grafo(G)
    
    info_texto = [
        html.B("Vértices: "), f"{G.number_of_nodes()}", html.Br(),
        html.B("Arestas: "), f"{G.number_of_edges()}", html.Br(),
        html.B("Direção: "), tipo_dir, html.Br(),
        html.B("Peso: "), tipo_peso, html.Br(),
        html.B("Propriedades: "), propriedades_atuais
    ]

    return new_elements, msg, layout_output, new_source_node, empty_msg, direcao_output, upload_reset, info_texto

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
    return new_mode_is_on, button_text, help_text, None 

@app.callback(
    Output('cytoscape-graph', 'stylesheet'),
    Input('source-node-store', 'data'),
    Input('connect-mode-store', 'data'),
    Input('toggle-direcao', 'value'),
    Input('toggle-peso', 'value'),
    Input('current-frame-store', 'data'), # <-- NOVO INPUT
    State('snapshots-store', 'data')      # <-- NOVO STATE
)
def update_stylesheet(source_node_id, connect_mode_on, direcao, peso, current_frame, snaps):
    stylesheet = []
    for s in BASE_STYLESHEET:
        novo_s = s.copy()
        novo_s['style'] = s['style'].copy()
        stylesheet.append(novo_s)
        
    for style in stylesheet:
        if style['selector'] == 'edge':
            style['style']['curve-style'] = 'bezier'
            if direcao == 'orientado':
                style['style']['target-arrow-shape'] = 'triangle'
            else:
                style['style']['target-arrow-shape'] = 'none' 
                
            if peso == 'sem_peso':
                style['style']['label'] = '' 
            else:
                style['style']['label'] = 'data(label)'

    # ... Lógica do connect_mode_on (borda laranja etc) ...
    if connect_mode_on:
        stylesheet.append({'selector': ':selected', 'style': {'overlay-opacity': 0}})
        if source_node_id:
            stylesheet.append({'selector': f'node[id = "{source_node_id}"]', 'style': {'border-width': 3, 'border-color': '#f5a442'}})

    # --- NOVO: APLICA AS CORES DA ANIMAÇÃO DO ALGORITMO ---
    if snaps and current_frame is not None and current_frame < len(snaps):
        quadro = snaps[current_frame]
        cores = quadro.get('c', {})
        pi_dict = quadro.get('pi', {})
        
        # Pinta os Vértices
        for no_id, cor in cores.items():
            if cor == "Cinza":
                stylesheet.append({
                    'selector': f'node[id = "{no_id}"]',
                    'style': {'background-color': '#999998', 'border-width': 4, 'border-color': '#FFC107', 'color': '#333'}
                })
            elif cor == "Preto":
                stylesheet.append({
                    'selector': f'node[id = "{no_id}"]',
                    'style': {'background-color': '#212121', 'color': 'white', 'text-outline-color': 'white', 'border-color': '#212121'}
                })
        
        # Destaca a Árvore de Busca (Arestas) usando o π
        for filho, pai in pi_dict.items():
            if pai is not None:
                stylesheet.append({
                    'selector': f'edge[source = "{pai}"][target = "{filho}"], edge[source = "{filho}"][target = "{pai}"]',
                    'style': {'line-color': '#FF9800', 'width': 4, 'target-arrow-color': '#FF9800'}
                })

    return stylesheet

@app.callback(
    Output('delete-selected-button', 'disabled'),
    Input('cytoscape-graph', 'selectedNodeData'),
    Input('cytoscape-graph', 'selectedEdgeData'),
    Input('connect-mode-store', 'data'),
    Input('snapshots-store', 'data') # <--- NOVO INPUT: Lê a fita de filme
)
def toggle_delete_button(nodes, edges, connect_mode_on, snaps):
    # Se tem filme rodando, trava o botão incondicionalmente!
    if snaps:
        return True
    if connect_mode_on:
        return True
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
    
    return {
        'name': 'circle', 
        'padding': 10, 
        'animate': True, 
        'animationDuration': 500,
        'refresh_trigger': n_clicks
    }
    
@app.callback(
    Output('modal-editar-peso', 'style'),
    Output('modal-input-peso', 'value'),
    Output('aresta-edit-store', 'data'),
    Input('edge-edit-store', 'data'),   
    Input('btn-cancelar-peso', 'n_clicks'), 
    Input('btn-salvar-peso', 'n_clicks'),   
    State('modal-editar-peso', 'style'),
    State('toggle-peso', 'value'),
    State('snapshots-store', 'data'), # <--- NOVO: Lê a fita de filme
    prevent_initial_call=True
)
def alternar_modal(edge_data, cancel_clicks, save_clicks, current_style, modo_peso, snaps):
    ctx = dash.callback_context
    if not ctx.triggered: raise PreventUpdate
    prop_id = ctx.triggered[0]['prop_id']

    novo_estilo = current_style.copy()
    
    # --- NOVA VALIDAÇÃO: Se o filme está rodando, tranca o modal! ---
    if snaps: 
        novo_estilo['display'] = 'none'
        return novo_estilo, dash.no_update, dash.no_update

    if prop_id == 'edge-edit-store.data' and edge_data:
        if modo_peso == 'sem_peso':
            return novo_estilo, dash.no_update, dash.no_update
    
        novo_estilo['display'] = 'flex'
        return novo_estilo, edge_data.get('label', ''), edge_data
    
    novo_estilo['display'] = 'none'
    return novo_estilo, dash.no_update, dash.no_update
    
@app.callback(
    Output('coluna-grafo', 'width'),
    Output('coluna-painel', 'style'),
    Output('toggle-painel-btn', 'children'),
    Input('toggle-painel-btn', 'n_clicks'),
    prevent_initial_call=True
)
def alternar_painel_inteiro(n_clicks):
    # O estilo base do painel flutuante
    estilo_painel = {
        'position': 'absolute', 'right': '0', 'top': '0', 
        'width': '300px', 'height': '85vh', 'padding': '0',
        'transition': 'transform 0.3s ease', 'zIndex': 100
    }
    
    if n_clicks % 2 == 0: 
        # FECHAR: Desliza o painel 100% da sua largura para a direita (fora da tela)
        estilo_painel['transform'] = 'translateX(100%)'
        return 12, estilo_painel, '◀'
    else:
        # ABRIR: Desliza o painel de volta para a posição original (0)
        estilo_painel['transform'] = 'translateX(0%)'
        return 12, estilo_painel, '▶'  
    
@app.callback(
    Output('card-info-grafo', 'style'),
    Input('btn-info-grafo', 'n_clicks'),
    State('card-info-grafo', 'style'),
    prevent_initial_call=True
)
def toggle_info_card(n_clicks, current_style):
    novo_estilo = current_style.copy()
    if novo_estilo.get('display') == 'none':
        novo_estilo['display'] = 'block'
    else:
        novo_estilo['display'] = 'none'
    return novo_estilo

@app.callback(
    Output('info-detalhes-elemento', 'children'),
    Output('info-detalhes-elemento', 'style'),
    Input('cytoscape-graph', 'selectedNodeData'),
    Input('cytoscape-graph', 'selectedEdgeData'),
    State('toggle-direcao', 'value'),
    State('info-detalhes-elemento', 'style'),
    State('toggle-peso', 'value'),  
    prevent_initial_call=True
)
def exibir_detalhes_elemento(sel_nodes, sel_edges, direcao, current_style, modo_peso):
    global G
    novo_estilo = current_style.copy()
    
    # Se clicou no fundo branco (limpou a seleção), esconde o bloco
    if not sel_nodes and not sel_edges:
        novo_estilo['display'] = 'none'
        return dash.no_update, novo_estilo
        
    novo_estilo['display'] = 'block'
    is_directed = (direcao == 'orientado')
    conteudo = []

    # --------------------------------------------------------
    # 1. SE CLICOU EM UM VÉRTICE
    # --------------------------------------------------------
    if sel_nodes and len(sel_nodes) == 1:
        node_id = str(sel_nodes[0]['id'])
        if not G.has_node(node_id): 
            novo_estilo['display'] = 'none'
            return dash.no_update, novo_estilo
        
        conteudo.append(html.B(f"Vértice: {node_id}"))
        conteudo.append(html.Br())
        
        has_loop = G.has_edge(node_id, node_id)
        conteudo.append(html.Span(f"Laço: {'Sim' if has_loop else 'Não'}"))
        conteudo.append(html.Br())

        list_edges = list(G.edges(node_id))
        conteudo.append(html.Span(f"Arestas Incidentes: {', '.join([f'{u}-{v}' for u, v in list_edges]) if list_edges else 'Nenhuma'}"))
        conteudo.append(html.Br())

        if is_directed:
            in_deg = G.in_degree(node_id)
            out_deg = G.out_degree(node_id)
            preds = list(G.predecessors(node_id))
            succs = list(G.successors(node_id))
            
            conteudo.extend([
                html.Span(f"Grau de Entrada: {in_deg}"), html.Br(),
                html.Span(f"Grau de Saída: {out_deg}"), html.Br(),
                html.Span(f"Antecessores: {', '.join(preds) if preds else 'Nenhum'}"), html.Br(),
                html.Span(f"Sucessores: {', '.join(succs) if succs else 'Nenhum'}"), html.Br()
            ])
            
            # Classificação Orientada
            if in_deg == 0 and out_deg > 0: tipo = "Fonte"
            elif out_deg == 0 and in_deg > 0: tipo = "Sumidouro"
            elif in_deg == 0 and out_deg == 0: tipo = "Isolado"
            else: tipo = "Comum"
        else:
            deg = G.degree(node_id)
            vizinhos = list(G.neighbors(node_id))
            
            conteudo.extend([
                html.Span(f"Grau: {deg}"), html.Br(),
                html.Span(f"Adjacentes: {', '.join(vizinhos) if vizinhos else 'Nenhum'}"), html.Br()
            ])
            
            # Classificação Não Orientada
            if deg == 0: tipo = "Isolado"
            elif deg == 1: tipo = "Folha"
            else: tipo = "Comum"
            
        conteudo.append(html.Span(f"Classificação: {tipo}"))

    # --------------------------------------------------------
    # 2. SE CLICOU EM UMA ARESTA
    # --------------------------------------------------------
    elif sel_edges and len(sel_edges) == 1:
        edge = sel_edges[0]
        src = str(edge['source'])
        tgt = str(edge['target'])
        
        if not G.has_edge(src, tgt):
            novo_estilo['display'] = 'none'
            return dash.no_update, novo_estilo
            
        peso = G.edges[src, tgt].get('label', '1')
        tipo = "Laço" if src == tgt else "Simples"
        
        if modo_peso != 'sem_peso':
            conteudo.extend([
                html.B(f"Aresta Selecionada: {src} - {tgt}"), html.Br(),
                html.Span(f"Origem: {src}"), html.Br(),
                html.Span(f"Destino: {tgt}"), html.Br(),
                html.Span(f"Peso: {peso}"), html.Br(),
                html.Span(f"Tipo: {tipo}")
            ])
        else:
            conteudo.extend([
                html.B(f"Aresta Selecionada: {src} - {tgt}"), html.Br(),
                html.Span(f"Origem: {src}"), html.Br(),
                html.Span(f"Destino: {tgt}"), html.Br(),
                html.Span(f"Tipo: {tipo}")
            ])
    else:
        # Se selecionou mais de um por engano, não mostra nada
        novo_estilo['display'] = 'none'
        return dash.no_update, novo_estilo

    return conteudo, novo_estilo

@app.callback(
    Output('dropdown-source', 'options'),
    Input('cytoscape-graph', 'elements')
)
def atualizar_opcoes_origem(elements):
    if not elements: return []
    # Filtra apenas os nós (que não têm 'source' e 'target')
    nos = [ele['data']['id'] for ele in elements if 'source' not in ele['data']]
    return [{'label': f'Vértice {n}', 'value': n} for n in nos]

@app.callback(
    Output('snapshots-store', 'data'),
    Output('current-frame-store', 'data', allow_duplicate=True),
    Output('is-playing-store', 'data', allow_duplicate=True),
    Output('action-output-message', 'children', allow_duplicate=True),
    Output('connect-mode-store', 'data', allow_duplicate=True),
    Output('connect-mode-button', 'children', allow_duplicate=True),
    Input('btn-carregar-algo', 'n_clicks'),
    Input('btn-stop-algo', 'n_clicks'),
    State('dropdown-algo', 'value'),
    State('dropdown-source', 'value'), # Lê o vértice escolhido
    prevent_initial_call=True
)
def gerenciar_fita_algoritmo(click_carregar, click_stop, algo, source):
    global G
    ctx = dash.callback_context
    if not ctx.triggered: raise PreventUpdate
    prop_id = ctx.triggered[0]['prop_id']

    if prop_id == 'btn-stop-algo.n_clicks':
        msg_stop = html.Span("Execução cancelada. Modo normal ativado.", style={'color': 'blue'})
        return None, 0, False, msg_stop, dash.no_update, dash.no_update

    if prop_id == 'btn-carregar-algo.n_clicks':
        if not algo: 
            return dash.no_update, dash.no_update, dash.no_update, html.Span("Erro: Escolha um algoritmo primeiro!", style={'color': 'red', 'fontWeight': 'bold'}), dash.no_update, dash.no_update
        
        # --- NOVA VALIDAÇÃO: Origem agora é obrigatória para tudo! ---
        if source is None or str(source) == "": 
            return dash.no_update, dash.no_update, dash.no_update, html.Span("Erro: Selecione um Vértice de Origem!", style={'color': 'red', 'fontWeight': 'bold'}), dash.no_update, dash.no_update

        # Passou nas validações, gera a fita:
        if algo == 'bfs':
            snaps = bfs_snapshots(G, str(source))
        else:
            snaps = dfs_snapshots(G, str(source))

        msg = html.Span(f"Algoritmo {algo.upper()} carregado! Modo de Execução Isolado iniciado.", style={'color': 'green'})
        
        return snaps, 0, False, msg, False, "Modo: Seleção"

@app.callback(
    Output('current-frame-store', 'data'),
    Output('is-playing-store', 'data'),
    Output('animation-interval', 'disabled'),
    Output('animation-interval', 'interval'),
    Input('btn-play-algo', 'n_clicks'),
    Input('btn-step-algo', 'n_clicks'),
    Input('btn-prev-algo', 'n_clicks'),
    Input('animation-interval', 'n_intervals'),
    Input('slider-velocidade', 'value'),  # <--- BÔNUS: Virou Input para ser instantâneo!
    State('is-playing-store', 'data'),
    State('current-frame-store', 'data'),
    State('snapshots-store', 'data'),
    prevent_initial_call=True
)
def controlar_player(btn_play, btn_step, btn_prev, n_ints, velocidade_idx, is_playing, current_frame, snaps):
    ctx = dash.callback_context
    if not ctx.triggered or not snaps: 
        raise PreventUpdate

    prop_id = ctx.triggered[0]['prop_id']
    total_frames = len(snaps)

    # --- A MÁGICA DA TRADUÇÃO DE VELOCIDADE ---
    # 0.25x (4s), 0.5x (2s), 1x (1s), 2x (0.5s)
    mapa_ms = {0: 4000, 1: 2000, 2: 1000, 3: 667, 4: 500}
    intervalo_ms = mapa_ms.get(velocidade_idx, 1000)
    # ------------------------------------------

    # Se o gatilho foi APENAS arrastar o slider, atualizamos o relógio sem pular o frame
    if prop_id == 'slider-velocidade.value':
        return current_frame, is_playing, not is_playing, intervalo_ms

    if prop_id == 'btn-play-algo.n_clicks':
        novo_status_play = not is_playing
        if novo_status_play and current_frame >= total_frames - 1:
            return 0, True, False, intervalo_ms # Chegou no fim, recomeça do zero
        return current_frame, novo_status_play, not novo_status_play, intervalo_ms

    elif prop_id == 'btn-step-algo.n_clicks':
        proximo_frame = min(current_frame + 1, total_frames - 1)
        return proximo_frame, False, True, intervalo_ms

    elif prop_id == 'btn-prev-algo.n_clicks':
        quadro_anterior = max(current_frame - 1, 0)
        return quadro_anterior, False, True, intervalo_ms

    elif prop_id == 'animation-interval.n_intervals':
        if is_playing:
            proximo_frame = current_frame + 1
            if proximo_frame >= total_frames:
                return current_frame, False, True, intervalo_ms # Auto-pause no fim
            return proximo_frame, True, False, intervalo_ms

    return current_frame, is_playing, not is_playing, intervalo_ms

@app.callback(
    Output('card-execucao-algo', 'style'),
    Output('texto-narracao-algo', 'children'),
    Output('texto-variaveis-algo', 'children'),
    Input('current-frame-store', 'data'),
    State('snapshots-store', 'data'),
    State('card-execucao-algo', 'style'),
    prevent_initial_call=True
)
def atualizar_painel_raiox(current_frame, snaps, current_style):
    novo_estilo = current_style.copy()
    
    if not snaps or current_frame is None or current_frame == 0 and not snaps:
        novo_estilo['display'] = 'none'
        return novo_estilo, "", ""
        
    novo_estilo['display'] = 'block'
    quadro = snaps[current_frame]
    narracao = quadro.get('descricao', '')
    
    # Formata as variáveis matemáticas (pi, d, f, Q, etc)
    linhas_vars = []
    
    # Se for BFS (Tem fila Q)
    if 'Q' in quadro:
        linhas_vars.append(html.B(f"Fila Q: {quadro['Q']}"))
        linhas_vars.append(html.Br())
    
    # Se for DFS (Tem tempo)
    if 'tempo' in quadro:
        linhas_vars.append(html.B(f"Tempo atual: {quadro['tempo']}"))
        linhas_vars.append(html.Br())
        
    # Variáveis gerais (d e pi)
    d_dict = quadro.get('d', {})
    pi_dict = quadro.get('pi', {})
    
    linhas_vars.append(html.Span("Distância/Tempo Descoberta (d): "))
    linhas_vars.append(html.Br())
    linhas_vars.append(html.Span(f"{d_dict}", style={'fontSize': '12px'}))
    linhas_vars.append(html.Br())
    
    linhas_vars.append(html.Span("Antecessores (π): "))
    linhas_vars.append(html.Br())
    linhas_vars.append(html.Span(f"{pi_dict}", style={'fontSize': '12px'}))

    return novo_estilo, narracao, linhas_vars

@app.callback(
    Output('player-flutuante', 'style'),
    Output('coluna-grafo', 'width', allow_duplicate=True),
    Output('coluna-painel', 'style', allow_duplicate=True),
    Output('toggle-painel-btn', 'children', allow_duplicate=True),
    Output('btn-info-grafo', 'style'),
    Output('top-buttons-container', 'style'),
    Output('toggle-painel-btn', 'disabled'),
    Output('card-info-grafo', 'style', allow_duplicate=True),
    Input('snapshots-store', 'data'),
    State('player-flutuante', 'style'),
    State('btn-info-grafo', 'style'),
    State('top-buttons-container', 'style'),
    State('toggle-painel-btn', 'n_clicks'),
    State('card-info-grafo', 'style'),
    prevent_initial_call=True
)
def alternar_modo_execucao(snaps, style_player, style_info, style_top, n_clicks_toggle, style_info_card):
    s_player = style_player.copy() if style_player else {}
    s_info = style_info.copy() if style_info else {}
    style_info_card_copy = style_info_card.copy() if style_info_card else {}
    s_top = style_top.copy() if style_top else {'display': 'flex', 'justifyContent': 'start', 'transition': 'opacity 0.3s'}
    n_clicks = n_clicks_toggle if n_clicks_toggle is not None else 0

    estilo_painel = {
        'position': 'absolute', 'right': '0', 'top': '0', 
        'width': '300px', 'height': '85vh', 'padding': '0', 'zIndex': 100
    }

    if snaps:
        # MODO EXECUÇÃO: Player aparece, força fechamento do painel pra fora da tela
        s_player['display'] = 'flex'
        estilo_painel['transform'] = 'translateX(100%)' 
        seta = '◀'
        style_info_card_copy['display'] = 'none'
        s_info['display'] = 'none'
        s_top['pointerEvents'] = 'none' 
        s_top['opacity'] = '0.3'
        travar_painel = True
    else:
        # MODO NORMAL
        s_player['display'] = 'none'
        style_info_card_copy['display'] = 'none'
        s_info['display'] = 'block'
        s_top['pointerEvents'] = 'auto'
        s_top['opacity'] = '1'
        travar_painel = False
        
        # Respeita o clique anterior
        if n_clicks % 2 == 0:
            estilo_painel['transform'] = 'translateX(100%)'
            seta = '◀'
        else:
            estilo_painel['display'] = 'block'
            seta = '▶'
        
    return s_player, 12, estilo_painel, seta, s_info, s_top, travar_painel, style_info_card_copy

# =============================================================================
# Callbacks Javascript (Lado do Cliente)
# =============================================================================

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

@server.route('/download/graph.txt')
def download_graph_file():
    return send_file(GRAPH_FILE_PATH, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))