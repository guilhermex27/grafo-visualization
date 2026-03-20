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
import json
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
            'label': 'data(label)',
            'text-valign': 'center', 'color': '#333',
            'text-outline-color': '#333', 'text-outline-width': '1px',
            'background-color': 'white', 'border-width': 4, 'border-color': '#999998',
            'transition-property': 'background-color, border-width, border-color, width, height',
            'transition-duration': '0.2s',
        }
    },
    {
        'selector': 'edge',
        'style': {
            'label': 'data(label)', 'color': '#333',

            'text-background-color': '#ffffff',
            'text-background-opacity': 1,
            'text-background-shape': 'roundrectangle',
            'text-background-padding': '5px',
            'text-wrap': 'wrap',
            'text-z-index': 10,
            'text-outline-color': '#333', 'text-outline-width': '0.4px',
            'transition-property': 'line-color, width, target-arrow-color',
            'transition-duration': '0.2s',
        }
    },
    {
        'selector': ':selected',
        'style': {
            'border-width': 4, 'border-color': '#42a5f5',
            'background-color': '#64b5f6'
        }
    }
]

# =============================================================================
# 2. Lógica de Conversão e Persistência de Dados
# =============================================================================


def nx_to_cytoscape(graph_obj):
    cy_elements = []
    for node, attrs in graph_obj.nodes(data=True):

        label_atual = attrs.get('label', str(node))
        cy_node = {'data': {'id': str(node), 'label': str(label_atual)}}

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
    if graus:
        qtd_graus_distintos = len(set(graus))

        if qtd_graus_distintos == 1:
            props.append("Regular")
        else:
            props.append("Irregular")

    # 5. Completo
    n = graph_obj.number_of_nodes()
    e = graph_obj.number_of_edges()
    if n > 1 and not tem_lacos:
        max_edges = n * \
            (n - 1) if graph_obj.is_directed() else n * (n - 1) // 2
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
        lines = [line.strip()
                 for line in f.read().splitlines() if line.strip()]

    G.clear()
    if not lines:
        return

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


def save_graph_data(is_weighted=True):
    linhas_arestas = []
    
    for source, target, data in G.edges(data=True):
        s = data.get('real_source', source)
        t = data.get('real_target', target)
        peso = data.get('label', '1')
        
        # 1. Adiciona a aresta de ida (sempre)
        if is_weighted:
            linhas_arestas.append(f"{s} {t} {peso}")
        else:
            linhas_arestas.append(f"{s} {t}")
            
        # 2. A MÁGICA: Se for Não Orientado e não for um laço, obrigatoriamente salva a volta!
        if not G.is_directed() and s != t:
            if is_weighted:
                linhas_arestas.append(f"{t} {s} {peso}")
            else:
                linhas_arestas.append(f"{t} {s}")

    with open(GRAPH_FILE_PATH, 'w') as f:
        # O cabeçalho 'E' agora reflete EXATAMENTE o número de LINHAS do arquivo
        f.write(f"{G.number_of_nodes()} {len(linhas_arestas)}\n")
        
        for linha in linhas_arestas:
            f.write(linha + "\n")

# =============================================================================
# 3. Layout da Aplicação Dash
# =============================================================================


app = dash.Dash(__name__, external_stylesheets=[
                dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server


def serve_layout():
    os.makedirs(os.path.dirname(GRAPH_FILE_PATH), exist_ok=True)
    load_graph_data()
    initial_elements = nx_to_cytoscape(G)

    tipo_dir_init = "Orientado" if G.is_directed() else "Não Orientado"
    tipo_peso_init = "Ponderado"
    propriedades_init = obter_propriedades_grafo(G)
    graus = sum([d for n, d in G.degree()])

    initial_info_children = [
        html.B("Vértices: "), f"{G.number_of_nodes()}", html.Br(),
        html.B("Arestas: "), f"{G.number_of_edges()}", html.Br(),
        html.B("Soma dos Graus: "), f"{graus}", html.Br(),
        html.B("Direção: "), tipo_dir_init, html.Br(),
        html.B("Peso: "), tipo_peso_init, html.Br(),
        html.B("Propriedades: "), propriedades_init
    ]

    return dbc.Container(fluid=True, style={'padding': '10px', 'overflowX': 'hidden'}, children=[
        dcc.Store(id='source-node-store', data=None),
        dcc.Store(id='connect-mode-store', data=False),
        dcc.Store(id='aresta-edit-store', data=None),
        dcc.Store(id='edge-edit-store', data=None),
        dcc.Store(id='vertex-edit-store', data=None),
        dcc.Store(id='vertice-edit-store', data=None),
        dcc.Store(id='snapshots-store', data=None),
        dcc.Store(id='current-frame-store', data=0),
        dcc.Store(id='is-playing-store', data=False),
        dcc.Interval(id='animation-interval', interval=1000,
                     n_intervals=0, disabled=True),

        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Editar Peso da Aresta")),
            dbc.ModalBody([
                dbc.Input(id='modal-input-peso', type='number',
                          placeholder="Digite o novo peso inteiro", className="mb-2")
            ]),
            dbc.ModalFooter([
                dbc.Button('Cancelar', id='btn-cancelar-peso',
                           color="danger", className="me-2"),
                dbc.Button('Salvar', id='btn-salvar-peso', color="success")
            ])
        ], id='modal-editar-peso', is_open=False, centered=True),

        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Editar Rótulo do Vértice")),
            dbc.ModalBody([
                dbc.Input(id='modal-input-rotulo', type='number',
                          placeholder="Digite o novo rótulo", className="mb-2")
            ]),
            dbc.ModalFooter([
                dbc.Button('Cancelar', id='btn-cancelar-rotulo',
                           color="danger", className="me-2"),
                dbc.Button('Salvar', id='btn-salvar-rotulo', color="success")
            ])
        ], id='modal-editar-rotulo', is_open=False, centered=True),

        # --- LINHA 1: CABEÇALHO ---
        dbc.Row(id='top-buttons-container', className="align-items-center mb-3 mt-2", style={'transition': 'opacity 0.3s'}, children=[

            # Coluna do Título (ocupa 8/12)
            dbc.Col(html.H2("Editor de Grafo Interativo", className="m-0 fw-bold",
                    style={'color': '#333', 'paddingLeft': '10px'}), width=8),

            # Coluna dos Botões (ocupa 4/12 e alinha tudo no centro verticalmente e à direita horizontalmente)
            dbc.Col(className="d-flex justify-content-end align-items-center pe-3",  width=4, children=[

                html.Div(className='image-container', children=[
                    html.Button(
                        id='home-button', style={'backgroundImage': 'url(assets/home.png)'})
                ]),
                html.Div(className='image-container', style={'transform': 'translateY(7px)'}, children=[
                    html.A(id="download-link", href="/download/graph.txt", children=[
                        html.Button(
                            style={'backgroundImage': 'url(assets/download.png)'})
                    ])
                ]),
                html.Div(className='image-container', children=[
                    dcc.Upload(id='upload-data', style={'display': 'flex'}, children=[
                        html.Button(
                            style={'backgroundImage': 'url(assets/upload.png)'})
                    ])
                ])
            ])
        ]),

        # LINHA 2: GRAFO E PAINEL
        # Adicionado overflowX: hidden para não criar barra de rolagem quando o painel deslizar pra fora
        dbc.Row(style={'margin': '0', 'position': 'relative', 'overflowX': 'hidden'}, children=[

            # LADO ESQUERDO: O GRAFO (Agora sempre fixo em 12 colunas, nunca mais muda de tamanho!)
            dbc.Col(id='coluna-grafo', width=12, style={'position': 'relative', 'border': '1px solid #ccc', 'backgroundColor': '#fff', 'height': '85vh', 'padding': '0'}, children=[
                cyto.Cytoscape(
                    id='cytoscape-graph', elements=initial_elements, stylesheet=BASE_STYLESHEET,
                    style={'width': '100%', 'height': '100%'},
                    layout={'name': 'circle', 'animate': True,
                            'animationDuration': 500},
                    wheelSensitivity=0.1
                ),
                html.Div(id='empty-graph-message', style={'position': 'absolute', 'top': '10px',
                         'width': '100%', 'textAlign': 'center', 'pointerEvents': 'none'}),
                html.Div(id='keyboard-listener-dummy',
                         style={'display': 'none'}),
                html.Button(id='btn-hidden-center', n_clicks=0,
                            style={'display': 'none'}),

                html.Div(className='info-container', children=[

                    html.Div(className='info', children=[
                        html.Button(id='btn-info-grafo', n_clicks=0)
                    ]),
                    dbc.Card(id='card-info-grafo', className='card-info shadow', style={'display': 'none', 'transition': 'transform 0.3s ease', 'transform': 'translateY(-10px)'}, children=[
                        dbc.CardBody([
                            html.H5(
                                "Informações Gerais", className="fw-bold mb-3 text-dark", style={'marginTop': '0'}),

                            html.Div(id='texto-info-grafo', children=initial_info_children,
                                     className="fw mb-3 text-dark", style={'fontSize': '14px', 'lineHeight': '1.6', 'color': '#000000'}),

                            html.Div(id='info-detalhes-elemento', className="mt-3 pt-3 border-top text-dark", style={
                                     'display': 'none', 'fontSize': '14px', 'lineHeight': '1.6', 'color': '#080808'})
                        ])
                    ])
                ]),

                dbc.Card(id='card-execucao-algo', className="card shadow border-success p-0", style={
                    'display': 'none', 'position': 'absolute', 'top': '10px', 'right': '10px', 'zIndex': 50,
                    'backgroundColor': 'rgba(255, 255, 255, 0.95)', 'minWidth': '280px', 'maxWidth': '320px',
                    'borderWidth': '2px', 'borderRadius': '8px', 'overflow': 'hidden'
                }, children=[
                    dbc.CardHeader(html.H6(id='titulo-card-algo', children="⚙️ Execução",
                                   className="fw-bold m-0 text-center", style={'color': "#080808"})),

                    dbc.CardBody(className="p-3", children=[
                        html.Div(id='texto-narracao-algo', className="text-dark fw-bold mb-3 text-center",
                                 style={'fontSize': '14px', 'fontStyle': 'italic'}),

                        html.Div(id='texto-variaveis-algo')
                    ])
                ]),

                html.Div(id='player-flutuante', className='player card flex-column shadow-lg p-3 border-0', style={'display': 'none', 'backgroundColor': 'rgba(255, 255, 255, 0.95)'}, children=[

                    html.Div(className='d-flex justify-content-around mb-3 w-100 px-3', children=[
                        html.Button(
                            id='btn-stop-algo', style={'backgroundImage': 'url(assets/stop.svg)'}),
                        html.Button(
                            id='btn-prev-algo', style={'backgroundImage': 'url(assets/previous.svg)'}),
                        html.Button(
                            id='btn-play-algo', style={'backgroundImage': 'url(assets/play.svg)'}),
                        html.Button(
                            id='btn-step-algo', style={'backgroundImage': 'url(assets/next.svg)'}),
                    ]),

                    html.Div(className='text-center fw-bold text-dark mb-2',
                             style={'fontSize': '12px'}, children="Velocidade da Animação:"),

                    html.Div(className='w-100 px-2', children=[
                        dcc.Slider(
                            id='slider-velocidade', min=0, max=4, step=None, value=2,
                            marks={
                                0: {'label': '0.25x', 'style': {'fontWeight': 'bold'}},
                                1: {'label': '0.5x', 'style': {'fontWeight': 'bold'}},
                                2: {'label': '1x', 'style': {'fontWeight': 'bold'}},
                                3: {'label': '1.5x', 'style': {'fontWeight': 'bold'}},
                                4: {'label': '2x', 'style': {'fontWeight': 'bold'}}
                            }
                        )
                    ])
                ]),
            ]),

            # LADO DIREITO: O PAINEL (Agora com classes Bootstrap)
            html.Div(id='coluna-painel', style={
                'position': 'absolute', 'right': '0', 'top': '0',
                'width': '300px', 'height': '85vh', 'padding': '0',
                'transition': 'transform 0.3s ease', 'zIndex': 100,
                'transform': 'translateX(100%)'
            }, children=[

                html.Div(className='btn-paineis', style={'position': 'absolute', 'left': '-31px', 'top': '50%', 'transform': 'translateY(-50%)'}, children=[
                    html.Button('◀', id='toggle-painel-btn', n_clicks=0)
                ]),

                # CONTEÚDO DO PAINEL
                # Usamos d-flex, flex-column e gap-3 para dar o espaçamento simétrico perfeito
                html.Div(id='conteudo-paineis', className='d-flex flex-column gap-3 p-3 h-100', style={'backgroundColor': '#f4f4f9', 'overflowY': 'auto', 'boxSizing': 'border-box', 'borderLeft': '1px solid #ccc'}, children=[

                    # CARTÃO 1: Vértice
                    html.Div(className='card shadow-sm border-0 p-3', children=[
                        html.H6("Vértice", className="fw-bold mb-3 text-center"),
                        html.Button('Adicionar Vértice', id='add-vertex-button',
                                    className='btn btn-primary w-100 fw-bold')
                    ]),

                    # CARTÃO 2: Interação
                    html.Div(className='card shadow-sm border-0 p-3', children=[
                        html.H6("Interação",
                                className="fw-bold mb-3 text-center"),
                        html.Button('Modo: Seleção', id='connect-mode-button',
                                    className='btn btn-info text-white w-100 fw-bold mb-2'),
                        html.P(id='connect-mode-help-text', children="(Selecione elementos para deletar)",
                               className="text-muted text-center mb-0", style={'fontSize': '12px'})
                    ]),

                    # CARTÃO 3: Deletar
                    html.Div(className='card shadow-sm border-0 p-3', children=[
                        html.H6("Deletar", className="fw-bold mb-3 text-center"),

                        # Trocado para dbc.Button
                        dbc.Button('Deletar Selecionado', id='delete-selected-button',
                                   disabled=True, color="danger", className='w-100 fw-bold mb-2'),

                        # Trocado para dbc.Button com outline=True
                        dbc.Button('Limpar Tudo', id='clear-all-button',
                                   color="danger", outline=True, className='w-100 fw-bold')
                    ]),

                    # CARTÃO 4: Configurações
                    html.Div(className='card shadow-sm border-0 p-3', children=[
                        html.H6("Configurações",
                                className="fw-bold mb-3 text-center"),
                        dcc.RadioItems(id='toggle-direcao', options=[{'label': ' Não Orientado', 'value': 'nao_orientado'}, {'label': ' Orientado', 'value': 'orientado'}],
                                       value='nao_orientado', labelStyle={'display': 'block', 'textAlign': 'left', 'marginBottom': '5px'}, className="text-secondary"),
                        html.Hr(className="my-2"),
                        dcc.RadioItems(id='toggle-peso', options=[{'label': ' Com Peso', 'value': 'com_peso'}, {
                                       'label': ' Sem Peso', 'value': 'sem_peso'}], value='com_peso', labelStyle={'display': 'block', 'textAlign': 'left'}, className="text-secondary")
                    ]),

                    # CARTÃO 5: Algoritmos
                    html.Div(className='card shadow-sm border-0 p-3 mb-2', children=[
                        html.H6("Algoritmos",
                                className="fw-bold mb-3 text-center"),
                        dcc.Dropdown(id='dropdown-algo', options=[{'label': 'BFS (Busca em Largura)', 'value': 'bfs'}, {
                                     'label': 'DFS (Busca em Profundidade)', 'value': 'dfs'}], placeholder="Escolha o Algoritmo", className="mb-2", style={'fontSize': '12px'}),
                        dcc.Dropdown(id='dropdown-source', placeholder="Vértice de Origem",
                                     className="mb-3", style={'fontSize': '12px'}),
                        html.Button('Carregar Algoritmo', id='btn-carregar-algo',
                                    className="btn btn-dark w-100 fw-bold")
                    ])
                ])
            ])
        ]),
        html.Div(id='action-output-message', className="w-100 text-center mt-2", style={
            # SEM position: absolute! Ele flui naturalmente para debaixo do grafo.
            # Mantém o espaço reservado para a tela não dar "soquinhos" quando o texto aparece/some
            'minHeight': '30px',
            'pointerEvents': 'none',
            'fontWeight': 'bold',
            'color': '#444',         # Cinza escuro elegante
            'fontSize': '15px',
            'whiteSpace': 'nowrap'
        })
    ])


app.layout = serve_layout

# =============================================================================
# 4. Callbacks (Lógica de Interação)
# =============================================================================


def _update_node_positions(cyto_elements):
    if not cyto_elements:
        return
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
    Output('toggle-peso', 'value'), # <--- NOVO SAÍDA (Permite o Python mudar o botão sozinho)
    Input('add-vertex-button', 'n_clicks'),
    Input('delete-selected-button', 'n_clicks'),
    Input('clear-all-button', 'n_clicks'),
    Input('upload-data', 'contents'),
    Input('cytoscape-graph', 'tapNodeData'),
    Input('cytoscape-graph', 'tapEdgeData'),
    Input('btn-salvar-peso', 'n_clicks'),
    Input('btn-hidden-center', 'n_clicks'),
    Input('toggle-direcao', 'value'),
    Input('toggle-peso', 'value'),  # <--- MUDOU DE STATE PARA INPUT (Altera o arquivo na hora)
    Input('btn-salvar-rotulo', 'n_clicks'),
    State('cytoscape-graph', 'selectedNodeData'),
    State('cytoscape-graph', 'selectedEdgeData'),
    State('upload-data', 'filename'),
    State('cytoscape-graph', 'elements'),
    State('source-node-store', 'data'),
    State('connect-mode-store', 'data'),
    State('aresta-edit-store', 'data'),
    State('modal-input-peso', 'value'),
    State('snapshots-store', 'data'),
    State('modal-editar-peso', 'is_open'),
    State('modal-editar-rotulo', 'is_open'),
    State('modal-input-rotulo', 'value'),
    State('vertex-edit-store', 'data'),
    prevent_initial_call=True
)
def main_callback(
    add_v, del_s, clear_all, upload_contents, tapped_node_data, tapped_edge_data, btn_salvar_peso, btn_hidden_center, toggle_direcao, toggle_peso, btn_salvar_rotulo,
    sel_nodes, sel_edges, filename, cyto_elements, source_node_id, connect_mode_on,
    aresta_edit_store_data, modal_input_value, snaps, modal_is_open, modal_rotulo_is_open, modal_input_rotulo, vertex_edit_store_data
):
    global G
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    prop_id = ctx.triggered[0]['prop_id']

    _update_node_positions(cyto_elements)

    msg = dash.no_update
    layout_output = dash.no_update
    new_source_node = source_node_id
    graph_changed = False
    direcao_output = dash.no_update
    upload_reset = dash.no_update
    peso_output = dash.no_update # <--- NOVO CONTROLE

    if prop_id == 'add-vertex-button.n_clicks':
        if snaps:
            msg = html.Span("Bloqueado: Não é possível adicionar vértices durante a animação.", style={'color': 'red'})
        elif modal_is_open or modal_rotulo_is_open:
            msg = dash.no_update
        else:
            node_ids = {int(n) for n in G.nodes if str(n).isdigit()}
            new_id = 0
            while new_id in node_ids:
                new_id += 1

            coluna = new_id % 8
            linha = new_id // 8

            pos_x = 80 + (coluna * 70)
            pos_y = 80 + (linha * 70)

            G.add_node(str(new_id), position={'x': pos_x, 'y': pos_y})
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
            msg = html.Span("Bloqueado: Não é possível deletar durante a animação.", style={'color': 'red'})
        elif modal_is_open or modal_rotulo_is_open:
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

    elif prop_id == 'clear-all-button.n_clicks':
        if snaps:
            msg = html.Span("Bloqueado: Não é possível limpar a tela durante a animação.", style={'color': 'red'})
        elif modal_is_open or modal_rotulo_is_open:
            msg = dash.no_update
        elif not G.nodes:
            msg = html.Span(f"O grafo já está vazio. (Ação {clear_all})", style={'color': 'orange'})
        else:
            G.clear()
            msg = html.Span(f"Grafo completamente limpo. (Ação {clear_all})", style={'color': 'green'})
            graph_changed = True
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

    elif prop_id == 'btn-salvar-rotulo.n_clicks':
        if vertex_edit_store_data and modal_input_rotulo is not None:
            old_id = str(vertex_edit_store_data['id'])
            novo_id = str(modal_input_rotulo).strip()

            try:
                novo_id_int = int(novo_id)
                if novo_id_int < 0:
                    msg = html.Span("Erro: O ID deve ser positivo.", style={'color': 'red'})
                elif novo_id == old_id:
                    msg = dash.no_update
                elif G.has_node(novo_id):
                    msg = html.Span(f"Erro: O vértice '{novo_id}' já existe!", style={'color': 'red', 'fontWeight': 'bold'})
                elif G.has_node(old_id):
                    nx.relabel_nodes(G, {old_id: novo_id}, copy=False)
                    
                    arestas_incidentes = []
                    if G.is_directed():
                        arestas_incidentes.extend(G.out_edges(novo_id, data=True)) 
                        arestas_incidentes.extend(G.in_edges(novo_id, data=True))  
                    else:
                        arestas_incidentes.extend(G.edges(novo_id, data=True))

                    for u, v, data in arestas_incidentes:
                        if data.get('real_source') == old_id:
                            data['real_source'] = novo_id
                        if data.get('real_target') == old_id:
                            data['real_target'] = novo_id
                            
                    msg = html.Span(f"Vértice '{old_id}' alterado para '{novo_id}'.", style={'color': 'green'})
                    graph_changed = True
                    
                    if source_node_id == old_id:
                        new_source_node = novo_id
                        
            except ValueError:
                msg = html.Span("Erro: O ID deve ser um número inteiro.", style={'color': 'red'})

    elif prop_id == 'toggle-direcao.value':
        is_directed = (toggle_direcao == 'orientado')

        if is_directed and not G.is_directed():
            # NÃO ORIENTADO -> ORIENTADO (Expansão)
            novo_G = nx.DiGraph()
            novo_G.add_nodes_from(G.nodes(data=True))
            for u, v, attrs in G.edges(data=True):
                
                # 1. Cria a aresta original (Limpando fantasmas)
                attrs_ida = attrs.copy()
                attrs_ida['real_source'] = u
                attrs_ida['real_target'] = v
                novo_G.add_edge(u, v, **attrs_ida)
                
                # 2. Cria a aresta de volta espelhada (se não for laço)
                if u != v:
                    attrs_volta = attrs.copy()
                    attrs_volta['real_source'] = v
                    attrs_volta['real_target'] = u
                    novo_G.add_edge(v, u, **attrs_volta)
                    
            G = novo_G
            msg = html.Span("Grafo alterado para Orientado (arestas desdobradas).", style={'color': 'blue'})
            graph_changed = True

        elif not is_directed and G.is_directed():
            # ORIENTADO -> NÃO ORIENTADO (Trava de Segurança)
            conflito = False
            for u, v, data in G.edges(data=True):
                # Se existe a volta, checa se os pesos são idênticos
                if u != v and G.has_edge(v, u):
                    peso_ida = data.get('label', '1')
                    peso_volta = G.edges[v, u].get('label', '1')
                    if peso_ida != peso_volta:
                        conflito = True
                        break
            
            if conflito:
                msg = html.Span("Erro: Pesos divergentes em arestas de ida e volta. Unifique os pesos antes de converter.", style={'color': 'red', 'fontWeight': 'bold'})
                direcao_output = 'orientado'
            else:
                novo_G = nx.Graph()
                novo_G.add_nodes_from(G.nodes(data=True))
                for u, v, data in G.edges(data=True):
                    if not novo_G.has_edge(u, v):
                        # Limpa os fantasmas na unificação também!
                        data_limpa = data.copy()
                        data_limpa['real_source'] = u
                        data_limpa['real_target'] = v
                        novo_G.add_edge(u, v, **data_limpa)
                G = novo_G
                msg = html.Span("Grafo alterado para Não Orientado (arestas unificadas).", style={'color': 'blue'})
                graph_changed = True

    # --- AÇÃO QUANDO CLICA NO BOTÃO DE PESO DA TELA ---
    elif prop_id == 'toggle-peso.value':
        for u, v, data in G.edges(data=True):
            data['label'] = '1'
            
        if toggle_peso == 'sem_peso':
            msg = html.Span("Grafo alterado para Não Ponderado.", style={'color': 'blue'})
        else:
            msg = html.Span("Grafo alterado para Ponderado.", style={'color': 'blue'})
            
        graph_changed = True

    elif prop_id == 'upload-data.contents':
        if upload_contents:
            _, content_string = upload_contents.split(',')
            decoded = base64.b64decode(content_string).decode('utf-8')

            linhas = [linha.strip() for linha in decoded.splitlines() if linha.strip()]

            arquivo_valido = True
            msg_erro = ""
            vertices_unicos = set()
            qtd_arestas_reais = 0
            v_header = 0
            e_header = 0
            qtd_com_peso = 0
            qtd_sem_peso = 0
            
            arestas_lidas = {} # Guarda as arestas na memória: (u, v) -> peso

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
                        arquivo_valido, msg_erro = False, "O cabeçalho deve conter apenas inteiros."

            if arquivo_valido:
                for i, linha in enumerate(linhas[1:], start=2):
                    partes = linha.split()
                    if len(partes) not in [2, 3]:
                        arquivo_valido, msg_erro = False, f"Erro na linha {i}: A linha deve ter 2 ou 3 colunas."
                        break

                    try:
                        u = int(partes[0])
                        v = int(partes[1])
                        peso_str = '1'
                        if len(partes) == 3:
                            peso_str = str(int(partes[2]))
                            qtd_com_peso += 1  
                        else:
                            qtd_sem_peso += 1  
                    except ValueError:
                        arquivo_valido, msg_erro = False, f"Erro na linha {i}: Vértices e pesos devem ser inteiros."
                        break

                    vertices_unicos.add(str(u))
                    vertices_unicos.add(str(v))
                    qtd_arestas_reais += 1
                    
                    # Salva no dicionário para cruzamento de dados depois
                    arestas_lidas[(str(u), str(v))] = peso_str

            if arquivo_valido:
                if qtd_arestas_reais != e_header:
                    arquivo_valido, msg_erro = False, f"Inconsistência: Cabeçalho diz {e_header} arestas, mas há {qtd_arestas_reais} lidas."
                elif len(vertices_unicos) > v_header:
                    arquivo_valido, msg_erro = False, f"Inconsistência: Cabeçalho diz {v_header} vértices, mas arestas usam {len(vertices_unicos)} distintos."
                elif qtd_com_peso > 0 and qtd_sem_peso > 0:
                    arquivo_valido, msg_erro = False, "Inconsistência: Mistura de arestas COM e SEM peso no mesmo arquivo."

            if arquivo_valido:
                # --- DETECTOR DE SIMETRIA ---
                is_symmetric = True
                for (u, v), peso in arestas_lidas.items():
                    if u == v:
                        continue # Laço não influencia simetria
                    # Se não tem a volta exata com o MESMO PESO, quebra a simetria
                    if (v, u) not in arestas_lidas or arestas_lidas[(v, u)] != peso:
                        is_symmetric = False
                        break
                
                with open(GRAPH_FILE_PATH, 'w') as f:
                    f.write(decoded)

                # Define o motor do NetworkX com base no que leu
                if is_symmetric and qtd_arestas_reais > 0:
                    G = nx.Graph()
                    direcao_output = 'nao_orientado'
                    msg_dir = " (Detectado Não Orientado por simetria)"
                else:
                    G = nx.DiGraph()
                    direcao_output = 'orientado'
                    msg_dir = " (Detectado Orientado)"
                    
                # Auto-ajuste do painel para pesos
                if qtd_com_peso > 0:
                    peso_output = 'com_peso'
                    msg_peso = " Ponderado"
                elif qtd_sem_peso > 0:
                    peso_output = 'sem_peso'
                    msg_peso = " Não Ponderado"
                else:
                    msg_peso = ""
                    # Se for vazio, assume Orientado por padrão para evitar falhas
                    G = nx.DiGraph()
                    direcao_output = 'orientado'
                    msg_dir = " (Vazio, Orientado por padrão)"

                msg = html.Span(f"Arquivo{msg_peso} carregado!{msg_dir}", style={'color': 'green'})

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

    if graph_changed:
        # AQUI É ONDE ELE DECIDE COMO SALVAR:
        # Se um upload mudou a variável peso_output, usa ela. Senão, usa o estado do botão na tela!
        tipo_peso_final = peso_output if peso_output != dash.no_update else toggle_peso
        is_weighted = (tipo_peso_final == 'com_peso')
        save_graph_data(is_weighted) # Salva omitindo a 3ª coluna se for Falso!
        
        new_elements = nx_to_cytoscape(G)
        empty_msg = "" if G.nodes else "Grafo vazio. Adicione um vértice para começar."

        if not G.nodes:
            layout_output = {'name': 'preset'}
        elif layout_output == dash.no_update:
            layout_output = {'name': 'preset', 'animate': True, 'fit': False, 'animationDuration': 100}
    else:
        new_elements = dash.no_update
        empty_msg = dash.no_update

    tipo_peso_final = peso_output if peso_output != dash.no_update else toggle_peso
    tipo_dir = "Orientado" if G.is_directed() else "Não Orientado"
    tipo_peso_tela = "Não Ponderado" if tipo_peso_final == 'sem_peso' else "Ponderado"
    propriedades_atuais = obter_propriedades_grafo(G)

    info_texto = [
        html.B("Vértices: "), f"{G.number_of_nodes()}", html.Br(),
        html.B("Arestas: "), f"{G.number_of_edges()}", html.Br(),
        html.B("Soma dos Graus: "), f"{sum([d for n, d in G.degree()])}", html.Br(),
        html.B("Direção: "), tipo_dir, html.Br(),
        html.B("Peso: "), tipo_peso_tela, html.Br(),
        html.B("Propriedades: "), propriedades_atuais
    ]

    # Retorna o peso_output como 9º item para mudar o botão lá no painel!
    return new_elements, msg, layout_output, new_source_node, empty_msg, direcao_output, upload_reset, info_texto, peso_output


@app.callback(
    Output('connect-mode-store', 'data'),
    Output('connect-mode-button', 'children'),
    Output('connect-mode-help-text', 'children'),
    Output('source-node-store', 'data', allow_duplicate=True),
    Output('action-output-message', 'children',
           allow_duplicate=True),  # <--- NOVO (Mensagem)
    # <--- NOVO (Cor do Botão)
    Output('connect-mode-button', 'className'),
    Input('connect-mode-button', 'n_clicks'),
    State('connect-mode-store', 'data'),
    State('snapshots-store', 'data'),       # Trava do Player
    State('modal-editar-peso', 'is_open'),  # Trava do Modal
    State('modal-editar-rotulo', 'is_open'),  # Trava do Modal
    prevent_initial_call=True
)
def toggle_connect_mode(n_clicks, is_on, snaps, modal_is_open, modal_editar_rotulo_is_open):
    # Trava de segurança contra atalhos de teclado indevidos
    if snaps or modal_is_open or modal_editar_rotulo_is_open:
        raise PreventUpdate

    new_mode_is_on = not is_on

    if new_mode_is_on:
        # VISUAL MODO CONEXÃO (Laranja)
        button_text = "Modo: Conexão"
        help_text = "(Clique na Origem, depois no Destino)"
        btn_class = "btn btn-warning text-dark w-100 fw-bold mb-2"
        msg = html.Span("Modo de Conexão Ativado. Selecione o vértice de origem.", style={
                        'color': '#d97706'})
    else:
        # VISUAL MODO SELEÇÃO (Azul)
        button_text = "Modo: Seleção"
        help_text = "(Selecione elementos para deletar)"
        btn_class = "btn btn-info text-white w-100 fw-bold mb-2"
        msg = html.Span("Modo de Seleção Ativado.", style={'color': '#0284c7'})

    return new_mode_is_on, button_text, help_text, None, msg, btn_class


@app.callback(
    Output('cytoscape-graph', 'stylesheet'),
    Input('source-node-store', 'data'),
    Input('connect-mode-store', 'data'),
    Input('toggle-direcao', 'value'),
    Input('toggle-peso', 'value'),
    Input('current-frame-store', 'data'),  # <-- NOVO INPUT
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
        stylesheet.append(
            {'selector': ':selected', 'style': {'overlay-opacity': 0}})
        if source_node_id:
            stylesheet.append({'selector': f'node[id = "{source_node_id}"]', 'style': {
                              'border-width': 4, 'border-color': '#f5a442', 'background-color': "#ffaf4d"}})

    # --- NOVO: APLICA AS CORES DA ANIMAÇÃO DO ALGORITMO ---
    # --- NOVO: APLICA AS CORES DA ANIMAÇÃO DO ALGORITMO ---
    if snaps and current_frame is not None and current_frame < len(snaps):
        quadro = snaps[current_frame]
        cores = quadro.get('c', {})
        pi_dict = quadro.get('pi', {})
        aresta_atual = quadro.get('aresta_atual') # <--- LÊ O LASER

        # Pinta os Vértices
        for no_id, cor in cores.items():
            if cor == "Cinza":
                stylesheet.append({
                    'selector': f'node[id = "{no_id}"]',
                    'style': {'background-color': '#999998', 'border-width': 4, 'border-color': "#858582", 'color': '#333'}
                })
            elif cor == "Preto":
                stylesheet.append({
                    'selector': f'node[id = "{no_id}"]',
                    'style': {'background-color': '#212121', 'color': 'white', 'text-outline-color': 'white', 'border-color': '#212121'}
                })

        # Destaca a Árvore de Busca Consolidada (Laranja)
        for filho, pai in pi_dict.items():
            if pai is not None:
                # FIX DO BUG: Separa orientado de não orientado para não pintar ida e volta em grafos direcionados!
                if direcao == 'orientado':
                    seletor = f'edge[source = "{pai}"][target = "{filho}"]'
                else:
                    seletor = f'edge[source = "{pai}"][target = "{filho}"], edge[source = "{filho}"][target = "{pai}"]'
                    
                stylesheet.append({
                    'selector': seletor,
                    'style': {'line-color': '#FF9800', 'width': 4, 'target-arrow-color': '#FF9800'}
                })

        # NOVO VISUAL: Destaca a aresta exata sendo percorrida neste milissegundo (Vermelho)
        if aresta_atual:
            u, v = aresta_atual
            if direcao == 'orientado':
                seletor_atual = f'edge[source = "{u}"][target = "{v}"]'
            else:
                seletor_atual = f'edge[source = "{u}"][target = "{v}"], edge[source = "{v}"][target = "{u}"]'
                
            stylesheet.append({
                'selector': seletor_atual,
                'style': {
                    'line-color': "#a71233", # Um vermelho elegante
                    'width': 4, 
                    'target-arrow-color': '#a71233', 
                    'z-index': 9999
                }
            })

    return stylesheet


@app.callback(
    Output('delete-selected-button', 'disabled'),
    Input('cytoscape-graph', 'selectedNodeData'),
    Input('cytoscape-graph', 'selectedEdgeData'),
    Input('connect-mode-store', 'data'),
    Input('snapshots-store', 'data')  # <--- NOVO INPUT: Lê a fita de filme
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
    State('toggle-peso', 'value'), # <--- LÊ O ESTADO ATUAL DO PESO NA TELA
    prevent_initial_call=True
)
def reset_layout(n_clicks, cyto_elements, toggle_peso):
    if not n_clicks:
        raise PreventUpdate

    _update_node_positions(cyto_elements)
    
    # Salva o arquivo respeitando a regra do botão da interface
    save_graph_data(toggle_peso == 'com_peso') 

    return {
        'name': 'circle',
        'padding': 10,
        'animate': True,
        'animationDuration': 500,
        'refresh_trigger': n_clicks
    }


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

    # Fecha se apertou cancelar, salvar, ou se o algoritmo tá rodando
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

    # Fecha se apertou cancelar, salvar, ou se o algoritmo tá rodando
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

        if is_directed:
            in_edges = [f"{u}→{v}" for u, v in G.in_edges(node_id)]
            out_edges = [f"{u}→{v}" for u, v in G.out_edges(node_id)]
            todas_arestas = list(set(in_edges + out_edges))
        else:
            todas_arestas = [f"{u}-{v}" for u, v in G.edges(node_id)]

        conteudo.append(html.Span(
            f"Arestas Incidentes: {', '.join(todas_arestas) if todas_arestas else 'Nenhuma'}"))
        conteudo.append(html.Br())

        if is_directed:
            in_deg = G.in_degree(node_id)
            out_deg = G.out_degree(node_id)
            preds = list(G.predecessors(node_id))
            succs = list(G.successors(node_id))

            conteudo.extend([
                html.Span(f"Grau de Entrada: {in_deg}"), html.Br(),
                html.Span(f"Grau de Saída: {out_deg}"), html.Br(),
                html.Span(
                    f"Antecessores: {', '.join(preds) if preds else 'Nenhum'}"), html.Br(),
                html.Span(
                    f"Sucessores: {', '.join(succs) if succs else 'Nenhum'}"), html.Br()
            ])

            # Classificação Orientada
            if in_deg == 0 and out_deg > 0:
                tipo = "Fonte"
            elif out_deg == 0 and in_deg > 0:
                tipo = "Sumidouro"
            elif in_deg == 0 and out_deg == 0:
                tipo = "Isolado"
            else:
                tipo = "Comum"
        else:
            deg = G.degree(node_id)
            vizinhos = list(G.neighbors(node_id))

            conteudo.extend([
                html.Span(f"Grau: {deg}"), html.Br(),
                html.Span(
                    f"Vizinho(s): {', '.join(vizinhos) if vizinhos else 'Nenhum'}"), html.Br()
            ])

            # Classificação Não Orientada
            if deg == 0:
                tipo = "Isolado"
            elif deg == 1:
                tipo = "Folha"
            else:
                tipo = "Comum"

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
    if not elements:
        return []
    # Filtra apenas os nós (que não têm 'source' e 'target')
    nos = [ele['data']['id']
           for ele in elements if 'source' not in ele['data']]
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
    State('dropdown-source', 'value'),  # Lê o vértice escolhido
    prevent_initial_call=True
)
def gerenciar_fita_algoritmo(click_carregar, click_stop, algo, source):
    global G
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    prop_id = ctx.triggered[0]['prop_id']

    if prop_id == 'btn-stop-algo.n_clicks':
        msg_stop = html.Span(
            "Execução cancelada. Modo normal ativado.", style={'color': 'blue'})
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

        msg = html.Span(f"Algoritmo {algo.upper()} carregado! Modo de Execução Isolado iniciado.", style={
                        'color': 'green'})

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
    # <--- BÔNUS: Virou Input para ser instantâneo!
    Input('slider-velocidade', 'value'),
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
            return 0, True, False, intervalo_ms  # Chegou no fim, recomeça do zero
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
                return current_frame, False, True, intervalo_ms  # Auto-pause no fim
            return proximo_frame, True, False, intervalo_ms

    return current_frame, is_playing, not is_playing, intervalo_ms


@app.callback(
    Output('card-execucao-algo', 'style'),
    Output('titulo-card-algo', 'children'),  # <--- NOVA SAÍDA (TÍTULO)
    Output('texto-narracao-algo', 'children'),
    Output('texto-variaveis-algo', 'children'),
    Input('current-frame-store', 'data'),
    State('snapshots-store', 'data'),
    State('card-execucao-algo', 'style'),
    # <--- NOVO STATE (SABER QUAL ALGORITMO É)
    State('dropdown-algo', 'value'),
    prevent_initial_call=True
)
def atualizar_painel_raiox(current_frame, snaps, current_style, algo):
    novo_estilo = current_style.copy() if current_style else {}

    if not snaps or current_frame is None or (current_frame == 0 and not snaps):
        novo_estilo['display'] = 'none'
        return novo_estilo, dash.no_update, "", []

    novo_estilo['display'] = 'block'
    quadro = snaps[current_frame]
    narracao = quadro.get('descricao', '')

    # 1. TÍTULO E VARIÁVEIS GLOBAIS
    titulo = "BFS (Largura)" if algo == 'bfs' else "DFS (Profundidade)"
    elementos_globais = []

    if algo == 'bfs' and 'Q' in quadro:
        elementos_globais.append(html.Div([
            html.B("Fila Q: ",  style={'color': "#080808"}),
            html.Span(f"{quadro['Q']}", className="fw-bold")
        ], className="mb-2 text-center", style={'fontSize': '14px'}))

    if algo == 'dfs' and 'tempo' in quadro:
        elementos_globais.append(html.Div([
            html.B("Tempo: ",  style={'color': "#080808"}),
            html.Span(f"{quadro['tempo']}", className="fw-bold")
        ], className="mb-2 text-center", style={'fontSize': '14px'}))

    # 2. CONSTRUÇÃO DA TABELA DE VÉRTICES (ESTADOS)
    cores_dict = quadro.get('c', {})
    d_dict = quadro.get('d', {})
    pi_dict = quadro.get('pi', {})
    f_dict = quadro.get('f', {})  # Apenas DFS

    # Ordena os vértices numericamente se forem números, senão alfabeticamente
    vertices = sorted(list(cores_dict.keys()),
                      key=lambda x: int(x) if str(x).isdigit() else x)

    # Monta o Cabeçalho da Tabela
    thead_cols = [
        html.Th("V", title="Vértice", className="text-center"),
        html.Th("Cor", className="text-center")
    ]
    if algo == 'bfs':
        thead_cols.extend([
            html.Th("d", title="Distância", className="text-center"),
            html.Th("π", title="Predecessor", className="text-center")
        ])
    else:
        thead_cols.extend([
            html.Th("d", title="Descoberta", className="text-center"),
            html.Th("f", title="Finalização", className="text-center"),
            html.Th("π", title="Predecessor", className="text-center")
        ])

    # Monta o Corpo da Tabela
    tbody_rows = []
    for v in vertices:
        cor_nome = cores_dict.get(v, "Branco")
        # Transforma o texto da cor num emoji bonitinho para economizar espaço
        cor_badge = "⚪" if cor_nome == "Branco" else (
            "🔘" if cor_nome == "Cinza" else "⚫")

        pi_v = pi_dict.get(v, "-")
        if pi_v is None:
            pi_v = "-"

        d_v = d_dict.get(v, "-")
        if d_v is None or d_v == float('inf'):
            d_v = "∞"

        row_cols = [
            html.Td(v, className="fw-bold text-center align-middle"),
            html.Td(cor_badge, className="text-center align-middle")
        ]

        if algo == 'bfs':
            row_cols.extend([
                html.Td(str(d_v), className="text-center align-middle"),
                html.Td(str(pi_v), className="text-center align-middle")
            ])
        else:
            f_v = f_dict.get(v, "-") if f_dict else "-"
            row_cols.extend([
                html.Td(
                    str(d_v), className="text-center align-middle text-success fw-bold"),
                html.Td(
                    str(f_v), className="text-center align-middle text-danger fw-bold"),
                html.Td(str(pi_v), className="text-center align-middle")
            ])

        tbody_rows.append(html.Tr(row_cols))

    # Junta tudo num container com scroll (caso o grafo tenha muitos vértices)
    tabela_completa = html.Div(
        style={'maxHeight': '250px', 'overflowY': 'auto'},
        children=[
            html.Table(className="table table-sm table-bordered table-striped mb-0", style={'fontSize': '12px'}, children=[
                html.Thead(html.Tr(thead_cols), className="table-light"),
                html.Tbody(tbody_rows)
            ])
        ]
    )

    # O conteúdo final da área de variáveis é a junção das globais com a tabela
    conteudo_final = elementos_globais + [tabela_completa]

    return novo_estilo, titulo, narracao, conteudo_final


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
    s_top = style_top.copy() if style_top else {
        'display': 'flex', 'justifyContent': 'start', 'transition': 'opacity 0.3s'}
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
        # style_info_card_copy['display'] = 'none'
        # s_info['display'] = 'none'
        s_top['pointerEvents'] = 'none'
        s_top['opacity'] = '0.5'
        travar_painel = True
    else:
        # MODO NORMAL
        s_player['display'] = 'none'
        # style_info_card_copy['display'] = 'none'
        # s_info['display'] = 'block'
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


@app.callback(
    Output('btn-play-algo', 'style'),
    Input('is-playing-store', 'data'),
    State('btn-play-algo', 'style'),
    prevent_initial_call=True
)
def atualizar_icone_play(is_playing, estilo_atual):
    # Copia o estilo atual para não apagar nada que o Bootstrap ou CSS precisem
    novo_estilo = estilo_atual.copy() if estilo_atual else {}

    if is_playing:
        # Se a fita está rodando, mostra o botão de Pause
        novo_estilo['backgroundImage'] = 'url(assets/pause.svg)'
    else:
        # Se a fita está pausada ou parada, mostra o botão de Play
        novo_estilo['backgroundImage'] = 'url(assets/play.svg)'

    return novo_estilo

# =============================================================================
# Callbacks Javascript (Lado do Cliente)
# =============================================================================


app.clientside_callback(
    dash.ClientsideFunction(
        namespace='grafos', function_name='escutarTeclado'),
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
    dash.ClientsideFunction(
        namespace='grafos', function_name='editarRotuloVertice'),
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
            // O truque para reiniciar a animação CSS toda vez que uma mensagem nova chega
            el.style.animation = 'none';
            el.offsetHeight; /* Força o navegador a recalcular a tela */
            el.style.animation = 'fadeOutMsg 5.0s forwards'; /* Dura 3.5 segundos */
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output('keyboard-listener-dummy',
           'data-fade'),  # Apenas um output fantasma necessário
    Input('action-output-message', 'children'),
    prevent_initial_call=True
)


@server.route('/download/graph.txt')
def download_graph_file():
    return send_file(GRAPH_FILE_PATH, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
