import os
import math
import base64
import time
import shutil
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
            'width': 40, 'height': 40,
            'text-valign': 'center', 'color': '#222',
            'text-outline-color': '#222', 'text-outline-width': '1px',
            'background-color': 'white', 'border-width': 4, 'border-color': '#222',
            'transition-property': 'background-color, border-width, border-color, width, height',
            'transition-duration': '0.2s',
        }
    },
    {
        'selector': 'edge',
        'style': {
            'label': 'data(label)', 
            'color': '#222',
            'line-color': '#222',    
            'target-arrow-color': '#222',
            'arrow-scale': 1.5,
            'text-background-color': '#ffffff',
            'text-background-opacity': 1,
            'text-background-shape': 'roundrectangle',
            'text-background-padding': '5px',
            'text-wrap': 'wrap',
            'text-outline-color': '#222', 'text-outline-width': '0.6px',
            'transition-property': 'line-color, width, target-arrow-color',
            'transition-duration': '0.2s',
            'curve-style': 'unbundled-bezier', 
            'control-point-step-size': '70px',
        }
    },
    {
        'selector': 'node:selected',
        'style': {
            'border-width': 4, 'border-color': '#42a5f5',
            'background-color': '#64b5f6',

            'color': '#ffffff',
            'text-outline-color': '#ffffff',

            'z-index': 9999
        }
    },
    {
    'selector': 'edge:selected', 
    'style': {
        'z-index': 9999,
        'line-color': '#42a5f5',
        'target-arrow-color': '#42a5f5',
        'text-outline-color': '#42a5f5', 'text-outline-width': '0.6px',
        'color': '#42a5f5',
        'width': '3px'        
    }
},
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

    tem_lacos = nx.number_of_selfloops(graph_obj) > 0
    if tem_lacos:
        props.append("Pseudografo")
    else:
        props.append("Simples")

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

    if nx.is_bipartite(graph_obj):
        props.append("Bipartido")

    if graph_obj.is_directed():
        degre_in = [d for n, d in graph_obj.in_degree()]
        degre_out = [d for n, d in graph_obj.out_degree()]
        if degre_in and degre_out:
            graus_distintos_in = len(set(degre_in))
            graus_distintos_out = len(set(degre_out))

            if graus_distintos_in == 1 and graus_distintos_out == 1 and degre_in[0] == degre_out[0]:
                props.append("Regular")
            else:
                props.append("Irregular")
    else:
        graus = [d for n, d in graph_obj.degree()]
        if graus:
            qtd_graus_distintos = len(set(graus))

            if qtd_graus_distintos == 1:
                props.append("Regular")
            else:
                props.append("Irregular")

    n = graph_obj.number_of_nodes()
    e = graph_obj.number_of_edges()
    if n > 1 and not tem_lacos:
        max_edges = n * \
            (n - 1) if graph_obj.is_directed() else n * (n - 1) // 2
        if e == max_edges:
            props.append("Completo")
            
    is_planar, _ = nx.check_planarity(graph_obj)
    if is_planar:
        props.append("Planar")
    else:
        props.append("Não Planar")

    return ", ".join(props)


def load_graph_data(from_upload=False):
    global G
    config = {'is_directed': False, 'is_weighted': True, 'positions': {}}

    if os.path.exists('data/config.json'):
        try:
            with open('data/config.json', 'r') as f:
                config = json.load(f)
        except Exception:
            pass

    if not from_upload:
        G = nx.DiGraph() if config.get('is_directed', False) else nx.Graph()

    if not os.path.exists(GRAPH_FILE_PATH) or os.path.getsize(GRAPH_FILE_PATH) == 0:
        return config

    with open(GRAPH_FILE_PATH, 'r') as f:
        lines = [line.strip()
                 for line in f.read().splitlines() if line.strip()]

    if not lines:
        return config

    try:
        header = lines.pop(0).split()
        num_nodes_header = int(header[0])
        for line in lines:
            parts = line.split()
            if len(parts) >= 2:
                source, target = parts[0], parts[1]
                weight = parts[2] if len(parts) > 2 else '1'

                if G.is_directed() or not G.has_edge(source, target):
                    G.add_edge(source, target, label=weight,
                               real_source=source, real_target=target)

        nodes_to_add_count = num_nodes_header - len(G.nodes)
        if nodes_to_add_count > 0:
            i = 0
            while nodes_to_add_count > 0:
                node_id = str(i)
                if not G.has_node(node_id):
                    G.add_node(node_id)
                    nodes_to_add_count -= 1
                i += 1

        if not from_upload:
            pos_dict = config.get('positions', {})
            for node_id in G.nodes():
                if node_id in pos_dict:
                    G.nodes[node_id]['position'] = pos_dict[node_id]

    except Exception as e:
        print(f"Erro ao processar: {e}")
        G.clear()

    return config


def save_graph_data(is_weighted=True):
    linhas_arestas = []

    for source, target, data in G.edges(data=True):
        s = data.get('real_source', source)
        t = data.get('real_target', target)
        peso = data.get('label', '1')

        if is_weighted:
            linhas_arestas.append(f"{s} {t} {peso}")
        else:
            linhas_arestas.append(f"{s} {t}")

        if not G.is_directed() and s != t:
            if is_weighted:
                linhas_arestas.append(f"{t} {s} {peso}")
            else:
                linhas_arestas.append(f"{t} {s}")

    with open(GRAPH_FILE_PATH, 'w') as f:
        f.write(f"{G.number_of_nodes()} {len(linhas_arestas)}\n")
        for linha in linhas_arestas:
            f.write(linha + "\n")

    config = {
        'is_directed': G.is_directed(),
        'is_weighted': is_weighted,
        'positions': {str(n): G.nodes[n].get('position', {'x': 0, 'y': 0}) for n in G.nodes}
    }
    with open('data/config.json', 'w') as f:
        json.dump(config, f)

# =============================================================================
# 3. Layout da Aplicação Dash
# =============================================================================


app = dash.Dash(__name__, external_stylesheets=[
                dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server


def serve_layout():
    os.makedirs(os.path.dirname(GRAPH_FILE_PATH), exist_ok=True)
    config = load_graph_data()  
    initial_elements = nx_to_cytoscape(G)

    tipo_dir_val = 'orientado' if config.get(
        'is_directed', False) else 'nao_orientado'
    tipo_peso_val = 'com_peso' if config.get(
        'is_weighted', True) else 'sem_peso'

    if config.get('positions') and initial_elements:
        layout_inicial = {'name': 'preset'}
    elif initial_elements:
        layout_inicial = {'name': 'circle',
                          'animate': True, 'animationDuration': 500}
    else:
        layout_inicial = {'name': 'preset'}

    tipo_dir_init = "Orientado" if G.is_directed() else "Não Orientado"
    tipo_peso_init = "Com Peso" if any(
        'label' in data for _, _, data in G.edges(data=True)) else "Sem Peso"

    propriedades_init = obter_propriedades_grafo(G)
    
    if G.is_directed():
        soma_in = sum([d for n, d in G.in_degree()])
        soma_out = sum([d for n, d in G.out_degree()])
        graus_text = [
            html.B("Soma dos Graus (Entrada): "), f"{soma_in}", html.Br(),
            html.B("Soma dos Graus (Saída): "), f"{soma_out}", html.Br()
        ]
    else:
        graus_text = [
            html.B("Soma dos Graus: "), f"{sum([d for n, d in G.degree()])}", html.Br()
        ]

    initial_info_children = [
        html.B("Vértices: "), f"{G.number_of_nodes()}", html.Br(),
        html.B("Arestas: "), f"{G.number_of_edges()}", html.Br()
    ] + graus_text + [
        html.B("Direção: "), tipo_dir_init, html.Br(),
        html.B("Peso: "), tipo_peso_init, html.Br(),
        html.B("Propriedades: "), propriedades_init
    ]

    modal_ajuda = dbc.Modal([
        dbc.ModalHeader(
            dbc.ModalTitle("Guia de Atalhos", className="fw-bold"), 
            close_button=True
        ),
        dbc.ModalBody([
            html.P("Utilize os atalhos abaixo para desenhar e editar seu grafo diretamente na tela:", className="text-muted mb-3"),
            
            html.Ul(className="list-group list-group-flush border rounded", children=[
                html.Li(className="list-group-item bg-light", children=[
                    html.B("🖱️ Shift + Clique Esquerdo ou '+' : "), "Adiciona um novo vértice na tela. Um atalho adiciona na posição do cursor e o outro enfileirando os vértices."
                ]),
                html.Li(className="list-group-item bg-light", children=[
                    html.B("🖱️ Clique Direito : "), "Alterna entre o Modo de Conexão e o Modo de Seleção rapidamente."
                ]),
                html.Li(className="list-group-item bg-light", children=[
                    html.B("🖱️ Clique Esquerdo: "), "Cria uma aresta após clicar encima de dois vértices (Se no modo de Conexão)."
                ]),
                html.Li(className="list-group-item bg-light", children=[
                    html.B("🖱️ Duplo Clique Esquerdo (Fundo) : "), "Centralizar a câmera e redefinir o zoom."
                ]),
                html.Li(className="list-group-item bg-light", children=[
                    html.B("🖱️ Duplo Clique Esquerdo (Vértice) : "), "Editar o rótulo do vértice (Se no modo de Seleção).",
                    html.Br(),
                    html.Small("⚠️ Aviso: A plataforma apenas permite rótulos inteiros positivos.", style={'color': '#dc3545', 'fontWeight': '600'})
                ]),
                html.Li(className="list-group-item bg-light", children=[
                    html.B("🖱️ Duplo Clique Esquerdo (Aresta) : "), "Editar o peso da aresta (Se ponderado)."
                ]),
                html.Li(className="list-group-item bg-light", children=[
                    html.B("🖱️ Ctrl + Clique Esquerdo: "), "Seleciona múltiplos itens simultaneamente."
                ]),
                html.Li(className="list-group-item bg-light", children=[
                    html.B("⌨️ Tecla Delete (Del) : "), "Exclui os elementos selecionados.",
                    html.Br(),
                    html.Small("⚠️ Aviso: Não é possível deletar elementos enquanto estiver no Modo Conexão.", style={'color': '#dc3545', 'fontWeight': '600'})
                ]),
            ])
        ]),
        dbc.ModalFooter(
            dbc.Button("Entendi", id="btn-fechar-ajuda", className="ms-auto", n_clicks=0, color="primary")
        ),
    ], id="modal-ajuda", is_open=False, size="lg", centered=True)

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

        modal_ajuda,

        # --- LINHA 1: CABEÇALHO ---
        dbc.Row(id='top-buttons-container', className="align-items-center mb-3 mt-2", style={'transition': 'opacity 0.3s'}, children=[

            dbc.Col(html.H2("Editor de Grafo Interativo", className="m-0 fw-bold",
                    style={'color': '#111', 'paddingLeft': '10px'}), width=8),

            dbc.Col(className="d-flex justify-content-between align-items-center pe-4",  width=4, children=[

                html.Div(className='image-container', children=[
                    html.Button(
                        id='home-button', style={'backgroundImage': 'url(assets/icons/home.svg)'})
                ]),

                html.Div(className='image-container', style={'marginRight': '5px'}, children=[
                    dbc.DropdownMenu(
                        label="", 
                        toggle_style={
                            'backgroundImage': 'url(assets/icons/menu.svg)',
                            'backgroundSize': 'cover',
                            'backgroundColor': 'transparent',
                            'border': 'none',
                            'width': '40px', 
                            'height': '40px',
                        },
                        caret=False,
                        className="menu-templates-espacado", 
                        direction="down",
                        align_end=False, 
                        children=[
                            dbc.DropdownMenuItem("Modelos Prontos", header=True, style={'fontSize': '14px', 'fontWeight': '700', 'textAlign': 'center', 'color': '#080808'}),
                            dbc.DropdownMenuItem(divider=True), 
                            
                            dbc.DropdownMenuItem("🌳 Árvore", id="tpl-arvore", style={'width': '220px', 'padding': '10px 15px', 'fontSize': '15px', 'fontWeight': '600'}),
                            dbc.DropdownMenuItem("🏠 Casa", id="tpl-casa", style={'width': '220px', 'padding': '10px 15px', 'fontSize': '15px', 'fontWeight': '600'}),
                            dbc.DropdownMenuItem("⭐ Estrela", id="tpl-estrela", style={'width': '220px', 'padding': '10px 15px', 'fontSize': '15px', 'fontWeight': '600'}),
                            dbc.DropdownMenuItem("🧊 Hipercubo", id="tpl-hipercubo", style={'width': '220px', 'padding': '10px 15px', 'fontSize': '15px', 'fontWeight': '600'}),
                            dbc.DropdownMenuItem("🔺 Triângulo Completo (K4)", id="tpl-triangulo", style={'width': '220px', 'padding': '10px 15px', 'fontSize': '15px', 'fontWeight': '600'}),
                            dbc.DropdownMenuItem("❌ Não Planar (K3,3)", id="tpl-k33", style={'width': '220px', 'padding': '10px 15px', 'fontSize': '15px', 'fontWeight': '600'}),
                            dbc.DropdownMenuItem("🧙 Zé do Grafo", id="tpl-zedografo", style={'width': '220px', 'padding': '10px 15px', 'fontSize': '15px', 'fontWeight': '600'}),
                        ]
                    )
                ]),

                html.Div(className='image-container', style={'transform': 'translateY(7px)'}, children=[
                    html.A(id="download-link", href="/download/graph.txt", children=[
                        html.Button(
                            style={'backgroundImage': 'url(assets/icons/download.svg)', 'height': '40px', 'marginBottom': '12px'})
                    ])
                ]),
                html.Div(className='image-container', children=[
                    dcc.Upload(id='upload-data', style={'display': 'flex'}, children=[
                        html.Button(
                            style={'backgroundImage': 'url(assets/icons/upload.svg)'})
                    ])
                ]),

                html.Div(className='image-container', style={'marginRight': '5px'}, children=[
                    html.Button(id='btn-abrir-ajuda', style={
                        'backgroundImage': 'url(assets/icons/help.svg)',
                        'backgroundSize': 'cover',
                        'backgroundColor': 'transparent',
                        'border': 'none',
                        'width': '45px',
                        'height': '45px',
                        'boxShadow': 'none'
                    })
                ]),
            ])
        ]),

        # LINHA 2: GRAFO E PAINEL

        dbc.Row(style={'margin': '0', 'position': 'relative', 'overflowX': 'hidden'}, children=[

            # LADO ESQUERDO: O GRAFO 
            dbc.Col(id='coluna-grafo', width=12, style={'position': 'relative', 'border': '1px solid #ccc', 'backgroundColor': '#fff', 'height': '85vh', 'padding': '0'}, children=[
                cyto.Cytoscape(
                    id='cytoscape-graph', elements=initial_elements, stylesheet=BASE_STYLESHEET,
                    style={'width': '100%', 'height': '100%'},
                    layout={'name': 'preset', 'animate': True,
                            'animationDuration': 500},
                    wheelSensitivity=0.1
                ),

                dcc.Input(id='shift-click-coords', type='text',
                          style={'display': 'none'}, value=""),
                dcc.Store(id='camera-tracker-dummy'),
                html.Button(id='btn-auto-save-pos', style={'display': 'none'}),

                html.Div("" if G.nodes else "Grafo vazio. Adicione um vértice para começar.", id='empty-graph-message', style={'position': 'absolute', 'top': '50%', 'left': '50%', 'transform': 'translate(-50%, -50%)', 'fontSize': '24px', 'color': '#888','fontWeight': 'bold',
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
                    'display': 'none', 'position': 'absolute', 'top': '10px', 'right': '0px', 'zIndex': 105,
                    'backgroundColor': 'rgba(255, 255, 255, 0.95)', 'minWidth': '320px', 'maxWidth': '320px',
                    'borderWidth': '2px', 'borderRadius': '8px', 'overflow': 'hidden'
                }, children=[
                    dbc.CardHeader(html.H6(id='titulo-card-algo', children="⚙️ Execução",
                                   className="fw-bold m-0 text-center", style={'color': "#080808"})),

                    dbc.CardBody(className="p-3", children=[
                        html.Div(id='texto-narracao-algo', className="text-dark fw-bold mb-3 text-center",
                                 style={'fontSize': '14px', 'fontStyle': 'italic', 'minHeight': '42px'}),

                        html.Div(id='texto-variaveis-algo')
                    ])
                ]),

                html.Div(id='player-flutuante', className='player card flex-column shadow-lg p-3 border-0', style={'display': 'none', 'backgroundColor': 'rgba(255, 255, 255, 0.95)'}, children=[

                    html.Div(className='d-flex justify-content-between mb-3 w-100 px-3', children=[
                        html.Button(
                            id='btn-stop-algo', style={'backgroundImage': 'url(assets/icons/stop.svg)'}),
                        html.Button(
                            id='btn-inicio-algo', style={'backgroundImage': 'url(assets/icons/fast-backward.svg)'}),
                        html.Button(
                            id='btn-prev-algo', style={'backgroundImage': 'url(assets/icons/previous.svg)'}),
                        html.Button(
                            id='btn-play-algo', style={'backgroundImage': 'url(assets/icons/play.svg)'}),
                        html.Button(
                            id='btn-step-algo', style={'backgroundImage': 'url(assets/icons/next.svg)'}),
                        html.Button(
                            id='btn-fim-algo', style={'backgroundImage': 'url(assets/icons/fast-forward.svg)'}),
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

            # LADO DIREITO: O PAINEL
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

                        dbc.Button('Deletar Selecionado', id='delete-selected-button',
                                   disabled=True, color="danger", className='w-100 fw-bold mb-2'),

                        dbc.Button('Limpar Tudo', id='clear-all-button',
                                   color="danger", outline=True, className='w-100 fw-bold')
                    ]),

                    # CARTÃO 4: Configurações
                    html.Div(className='card shadow-sm border-0 p-3', children=[
                        html.H6("Configurações",
                                className="fw-bold mb-3 text-center"),
                        dcc.RadioItems(id='toggle-direcao', options=[{'label': ' Não Orientado', 'value': 'nao_orientado'}, {'label': ' Orientado', 'value': 'orientado'}],
                                       value=tipo_dir_val, labelStyle={'display': 'block', 'textAlign': 'left', 'marginBottom': '5px'}, className="text-secondary"), 
                        html.Hr(className="my-2"),
                        dcc.RadioItems(id='toggle-peso', options=[{'label': ' Com Peso', 'value': 'com_peso'}, {
                                       'label': ' Sem Peso', 'value': 'sem_peso'}], value=tipo_peso_val, labelStyle={'display': 'block', 'textAlign': 'left'}, className="text-secondary")  
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
            'minHeight': '30px',
            'pointerEvents': 'none',
            'fontWeight': 'bold',
            'color': '#111',  
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
    Output('toggle-peso', 'value'),
    Input('add-vertex-button', 'n_clicks'),
    Input('delete-selected-button', 'n_clicks'),
    Input('clear-all-button', 'n_clicks'),
    Input('upload-data', 'contents'),
    Input('cytoscape-graph', 'tapNodeData'),
    Input('cytoscape-graph', 'tapEdgeData'),
    Input('btn-salvar-peso', 'n_clicks'),
    Input('btn-hidden-center', 'n_clicks'),
    Input('toggle-direcao', 'value'),
    Input('toggle-peso', 'value'),
    Input('btn-salvar-rotulo', 'n_clicks'),
    Input('shift-click-coords', 'value'),
    Input('btn-auto-save-pos', 'n_clicks'),
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
    add_v, del_s, clear_all, upload_contents, tapped_node_data, tapped_edge_data, btn_salvar_peso, btn_hidden_center, toggle_direcao, toggle_peso, btn_salvar_rotulo, shift_click_data, btn_auto_save,
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
    peso_output = dash.no_update

    if prop_id == 'add-vertex-button.n_clicks':
        if snaps:
            msg = html.Span(
                "Bloqueado: Não é possível adicionar vértices durante a animação.", style={'color': 'red'})
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
            msg = html.Span(f"Vértice {new_id} adicionado.", style={
                            'color': 'green'})
            graph_changed = True

            add_v_val = add_v if add_v else 0
            layout_output = {
                'name': 'preset',
                'fit': True,
                'padding': 30,
                'animate': True,
                'animationDuration': 100,
                'refresh_trigger': f"fit_add_{add_v_val}"
            }

    elif prop_id == 'shift-click-coords.value':
        if snaps:
            msg = html.Span(
                "Bloqueado: Não é possível adicionar vértices durante a animação.", style={'color': 'red'})
        elif modal_is_open or modal_rotulo_is_open:
            msg = dash.no_update
        elif shift_click_data:
            partes = shift_click_data.split(',')
            if len(partes) >= 2:
                try:
                    pos_x = float(partes[0])
                    pos_y = float(partes[1])

                    node_ids = {int(n) for n in G.nodes if str(n).isdigit()}
                    new_id = 0
                    while new_id in node_ids:
                        new_id += 1

                    G.add_node(str(new_id), position={'x': pos_x, 'y': pos_y})

                    msg = html.Span(f"Vértice {new_id} adicionado.", style={
                                    'color': 'green'})
                    graph_changed = True
                except ValueError:
                    msg = dash.no_update

    elif prop_id == 'btn-auto-save-pos.n_clicks':
        _update_node_positions(cyto_elements)
        
        save_graph_data(toggle_peso == 'com_peso')
     
        raise PreventUpdate

    elif prop_id == 'cytoscape-graph.tapNodeData':
        if connect_mode_on:
            if tapped_node_data:
                target_node_id = tapped_node_data['id']
                if not source_node_id:
                    new_source_node = target_node_id
                    msg = html.Span(f"Vértice de origem {target_node_id} selecionado.", style={
                                    'color': '#f5a442'})
                elif source_node_id == target_node_id:
                    if G.has_edge(source_node_id, target_node_id):
                        msg = html.Span("Laço já existe neste vértice.", style={
                                        'color': 'orange'})
                    else:
                        G.add_edge(source_node_id, target_node_id, label='1')
                        G.edges[source_node_id,
                                target_node_id]['real_source'] = source_node_id
                        G.edges[source_node_id,
                                target_node_id]['real_target'] = target_node_id
                        msg = html.Span(f"Laço criado no vértice {source_node_id}.", style={
                                        'color': 'green'})
                        graph_changed = True
                    new_source_node = None
                else:
                    if G.has_edge(source_node_id, target_node_id):
                        msg = html.Span("Aresta já existe.",
                                        style={'color': 'orange'})
                    else:
                        G.add_edge(source_node_id, target_node_id, label='1')
                        sep = "->" if G.is_directed() else "-"
                        msg = html.Span(f"Aresta {source_node_id}{sep}{target_node_id} criada.", style={
                                        'color': 'green'})
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

            sep = "->" if G.is_directed() else "-"

            msg = html.Span(f"Aresta {source}{sep}{target} selecionada.")

    elif prop_id == 'delete-selected-button.n_clicks':
        if snaps:
            msg = html.Span(
                "Bloqueado: Não é possível deletar durante a animação.", style={'color': 'red'})
        elif modal_is_open or modal_rotulo_is_open:
            msg = dash.no_update
        elif not connect_mode_on and (sel_nodes or sel_edges):
            nodes_to_remove = {n['id']
                               for n in sel_nodes} if sel_nodes else set()
            edges_to_remove = [(e['source'], e['target'])
                               for e in sel_edges] if sel_edges else []
            G.remove_nodes_from(nodes_to_remove)
            G.remove_edges_from(edges_to_remove)
            msg = html.Span("Elemento(s) removido(s).",
                            style={'color': 'green'})
            graph_changed = True
            if source_node_id in nodes_to_remove:
                new_source_node = None

    elif prop_id == 'clear-all-button.n_clicks':
        if snaps:
            msg = html.Span(
                "Bloqueado: Não é possível limpar a tela durante a animação.", style={'color': 'red'})
        elif modal_is_open or modal_rotulo_is_open:
            msg = dash.no_update
        elif not G.nodes:
            msg = html.Span(f"O grafo já está vazio.", style={
                            'color': 'orange'})
        else:
            G.clear()
            msg = html.Span(f"Grafo limpo.", style={
                            'color': 'green'})
            graph_changed = True
            new_source_node = None
        empty_msg = "" if G.nodes else "Grafo vazio. Adicione um vértice para começar."

    elif prop_id == 'btn-salvar-peso.n_clicks':
        if aresta_edit_store_data and modal_input_value is not None:
            src = aresta_edit_store_data['source']
            tgt = aresta_edit_store_data['target']
            novo_peso_str = str(modal_input_value).strip()

            try:
                novo_peso_int = int(novo_peso_str)

                if G.has_edge(src, tgt):
                    G.edges[src, tgt]['label'] = str(novo_peso_int)
                    msg = html.Span(f"Peso atualizado para {novo_peso_int}", style={
                                    'color': 'green'})
                    graph_changed = True
            except ValueError:
                msg = html.Span(
                    "Erro: O peso deve ser um número inteiro.", style={'color': 'red'})

    elif prop_id == 'btn-salvar-rotulo.n_clicks':
        if vertex_edit_store_data and modal_input_rotulo is not None:
            old_id = str(vertex_edit_store_data['id'])
            novo_id = str(modal_input_rotulo).strip()

            try:
                novo_id_int = int(novo_id)
                if novo_id_int < 0:
                    msg = html.Span(
                        "Erro: O ID deve ser positivo.", style={'color': 'red'})
                elif novo_id == old_id:
                    msg = dash.no_update
                elif G.has_node(novo_id):
                    msg = html.Span(f"Erro: O vértice {novo_id} já existe!", style={
                                    'color': 'red', 'fontWeight': 'bold'})
                elif G.has_node(old_id):
                    nx.relabel_nodes(G, {old_id: novo_id}, copy=False)

                    arestas_incidentes = []
                    if G.is_directed():
                        arestas_incidentes.extend(
                            G.out_edges(novo_id, data=True))
                        arestas_incidentes.extend(
                            G.in_edges(novo_id, data=True))
                    else:
                        arestas_incidentes.extend(G.edges(novo_id, data=True))

                    for u, v, data in arestas_incidentes:
                        if data.get('real_source') == old_id:
                            data['real_source'] = novo_id
                        if data.get('real_target') == old_id:
                            data['real_target'] = novo_id

                    msg = html.Span(f"Vértice {old_id} alterado para {novo_id}.", style={
                                    'color': 'green'})
                    graph_changed = True

                    if source_node_id == old_id:
                        new_source_node = novo_id

            except ValueError:
                msg = html.Span(
                    "Erro: O ID deve ser um número inteiro.", style={'color': 'red'})

    elif prop_id == 'toggle-direcao.value':
        is_directed = (toggle_direcao == 'orientado')

        if is_directed and not G.is_directed():
            novo_G = nx.DiGraph()
            novo_G.add_nodes_from(G.nodes(data=True))
            for u, v, attrs in G.edges(data=True):

                attrs_ida = attrs.copy()
                attrs_ida['real_source'] = u
                attrs_ida['real_target'] = v
                novo_G.add_edge(u, v, **attrs_ida)

                if u != v:
                    attrs_volta = attrs.copy()
                    attrs_volta['real_source'] = v
                    attrs_volta['real_target'] = u
                    novo_G.add_edge(v, u, **attrs_volta)

            G = novo_G
            msg = html.Span("Grafo alterado para Orientado.", style={
                            'color': 'blue'})
            graph_changed = True

        elif not is_directed and G.is_directed():
            conflito = False
            for u, v, data in G.edges(data=True):
                if u != v and G.has_edge(v, u):
                    peso_ida = data.get('label', '1')
                    peso_volta = G.edges[v, u].get('label', '1')
                    if peso_ida != peso_volta:
                        conflito = True
                        break

            if conflito:
                msg = html.Span("Erro: Pesos divergentes em arestas de ida e volta. Unifique os pesos antes de converter.", style={
                                'color': 'red', 'fontWeight': 'bold'})
                direcao_output = 'orientado'
            else:
                novo_G = nx.Graph()
                novo_G.add_nodes_from(G.nodes(data=True))
                for u, v, data in G.edges(data=True):
                    if not novo_G.has_edge(u, v):
                        data_limpa = data.copy()
                        data_limpa['real_source'] = u
                        data_limpa['real_target'] = v
                        novo_G.add_edge(u, v, **data_limpa)
                G = novo_G
                msg = html.Span("Grafo alterado para Não Orientado.", style={
                                'color': 'blue'})
                graph_changed = True

    elif prop_id == 'toggle-peso.value':
        for u, v, data in G.edges(data=True):
            data['label'] = '1'

        if toggle_peso == 'sem_peso':
            msg = html.Span("Grafo alterado para Não Ponderado.",
                            style={'color': 'blue'})
        else:
            msg = html.Span("Grafo alterado para Ponderado.",
                            style={'color': 'blue'})

        graph_changed = True

    elif prop_id == 'upload-data.contents':
        if upload_contents:
            _, content_string = upload_contents.split(',')
            decoded = base64.b64decode(content_string).decode('utf-8')

            linhas = [linha.strip()
                      for linha in decoded.splitlines() if linha.strip()]

            arquivo_valido = True
            msg_erro = ""
            vertices_unicos = set()
            qtd_arestas_reais = 0
            v_header = 0
            e_header = 0
            qtd_com_peso = 0
            qtd_sem_peso = 0

            arestas_lidas = {}

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

                    arestas_lidas[(str(u), str(v))] = peso_str

            if arquivo_valido:
                if qtd_arestas_reais != e_header:
                    arquivo_valido, msg_erro = False, f"Inconsistência: Cabeçalho diz {e_header} arestas, mas há {qtd_arestas_reais} lidas."
                elif len(vertices_unicos) > v_header:
                    arquivo_valido, msg_erro = False, f"Inconsistência: Cabeçalho diz {v_header} vértices, mas arestas usam {len(vertices_unicos)} distintos."
                elif qtd_com_peso > 0 and qtd_sem_peso > 0:
                    arquivo_valido, msg_erro = False, "Inconsistência: Mistura de arestas COM e SEM peso no mesmo arquivo."

            if arquivo_valido:
                is_symmetric = True
                for (u, v), peso in arestas_lidas.items():
                    if u == v:
                        continue
                    if (v, u) not in arestas_lidas or arestas_lidas[(v, u)] != peso:
                        is_symmetric = False
                        break

                with open(GRAPH_FILE_PATH, 'w') as f:
                    f.write(decoded)

                if is_symmetric and qtd_arestas_reais > 0:
                    G = nx.Graph()
                    direcao_output = 'nao_orientado'
                    msg_dir = "Não Orientado"
                else:
                    G = nx.DiGraph()
                    direcao_output = 'orientado'
                    msg_dir = "Orientado"

                if qtd_com_peso > 0:
                    peso_output = 'com_peso'
                    msg_peso = "Ponderado"
                elif qtd_sem_peso > 0:
                    peso_output = 'sem_peso'
                    msg_peso = "Não Ponderado"
                else:
                    msg_peso = ""
                    G = nx.DiGraph()
                    direcao_output = 'orientado'
                    msg_dir = "Orientado"

                msg = html.Span(f"Grafo {msg_dir} e {msg_peso} carregado!", style={
                                'color': 'green'})

                load_graph_data(from_upload=True)
                nodes = list(G.nodes())
                n_nodes = len(nodes)
                if n_nodes > 0:
                    raio = max(150, n_nodes * 25) 
                    centro_x, centro_y = 400, 300
                    
                    for i, node in enumerate(nodes):
                        angulo = 2 * math.pi * i / n_nodes
                        G.nodes[node]['position'] = {
                            'x': centro_x + raio * math.cos(angulo),
                            'y': centro_y + raio * math.sin(angulo)
                        }
                layout_output = {'name': 'preset','padding': 50,
                                 'animate': True, 'animationDuration': 500}
                new_source_node = None
                graph_changed = True
            else:
                msg = html.Span(
                    f"Falha ao carregar: {msg_erro}", style={'color': 'red'})

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
        tipo_peso_final = peso_output if peso_output != dash.no_update else toggle_peso
        is_weighted = (tipo_peso_final == 'com_peso')
        save_graph_data(is_weighted)

        new_elements = nx_to_cytoscape(G)
        empty_msg = "" if G.nodes else "Grafo vazio. Adicione um vértice para começar."

        if not G.nodes:
            layout_output = {'name': 'preset'}
        elif layout_output == dash.no_update:
            layout_output = {'name': 'preset', 'animate': True,
                             'fit': False, 'animationDuration': 100}
    else:
        new_elements = dash.no_update
        empty_msg = dash.no_update

    tipo_peso_final = peso_output if peso_output != dash.no_update else toggle_peso
    tipo_dir = "Orientado" if G.is_directed() else "Não Orientado"
    tipo_peso_tela = "Não Ponderado" if tipo_peso_final == 'sem_peso' else "Ponderado"
    propriedades_atuais = obter_propriedades_grafo(G)
    
    if G.is_directed():
        soma_in = sum([d for n, d in G.in_degree()])
        soma_out = sum([d for n, d in G.out_degree()])
        graus_text = [
            html.B("Soma dos Graus (Entrada): "), f"{soma_in}", html.Br(),
            html.B("Soma dos Graus (Saída): "), f"{soma_out}", html.Br()
        ]
    else:
        graus_text = [
            html.B("Soma dos Graus: "), f"{sum([d for n, d in G.degree()])}", html.Br()
        ]

    info_texto = [
        html.B("Vértices: "), f"{G.number_of_nodes()}", html.Br(),
        html.B("Arestas: "), f"{G.number_of_edges()}", html.Br()
    ] + graus_text + [
        html.B("Direção: "), tipo_dir, html.Br(),
        html.B("Peso: "), tipo_peso_tela, html.Br(),
        html.B("Propriedades: "), propriedades_atuais
    ]

    return new_elements, msg, layout_output, new_source_node, empty_msg, direcao_output, upload_reset, info_texto, peso_output


@app.callback(
    Output('connect-mode-store', 'data'),
    Output('connect-mode-button', 'children'),
    Output('connect-mode-help-text', 'children'),
    Output('source-node-store', 'data', allow_duplicate=True),
    Output('action-output-message', 'children',
           allow_duplicate=True),
    Output('connect-mode-button', 'className'),
    Input('connect-mode-button', 'n_clicks'),
    State('connect-mode-store', 'data'),
    State('snapshots-store', 'data'),       
    State('modal-editar-peso', 'is_open'),  
    State('modal-editar-rotulo', 'is_open'),  
    prevent_initial_call=True
)
def toggle_connect_mode(n_clicks, is_on, snaps, modal_is_open, modal_editar_rotulo_is_open):
    if snaps or modal_is_open or modal_editar_rotulo_is_open:
        raise PreventUpdate

    new_mode_is_on = not is_on

    if new_mode_is_on:
        button_text = "Modo: Conexão"
        help_text = "(Clique na Origem, depois no Destino)"
        btn_class = "btn btn-warning text-dark w-100 fw-bold mb-2"
        msg = html.Span("Modo de Conexão Ativado. Selecione o vértice de origem.", style={
                        'color': '#d97706'})
    else:
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
    Input('current-frame-store', 'data'),  
    State('snapshots-store', 'data')      
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

    if connect_mode_on:
        stylesheet.append(
            {'selector': ':selected', 'style': {'overlay-opacity': 0}})
        if source_node_id:
            stylesheet.append({'selector': f'node[id = "{source_node_id}"]', 'style': {
                              'border-width': 4, 'border-color': '#f5a442', 'background-color': "#ffaf4d"}})

    if snaps and current_frame is not None and current_frame < len(snaps):
        quadro = snaps[current_frame]
        cores = quadro.get('c', {})
        pi_dict = quadro.get('pi', {})
        aresta_atual = quadro.get('aresta_atual')

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

        for filho, pai in pi_dict.items():
            if pai is not None:
                if direcao == 'orientado':
                    seletor = f'edge[source = "{pai}"][target = "{filho}"]'
                else:
                    seletor = f'edge[source = "{pai}"][target = "{filho}"], edge[source = "{filho}"][target = "{pai}"]'

                stylesheet.append({
                    'selector': seletor,
                    'style': {'line-color': '#FF9800', 'width': 4, 'target-arrow-color': '#FF9800'}
                })

        if aresta_atual:
            u, v = aresta_atual
            if direcao == 'orientado':
                seletor_atual = f'edge[source = "{u}"][target = "{v}"]'
            else:
                seletor_atual = f'edge[source = "{u}"][target = "{v}"], edge[source = "{v}"][target = "{u}"]'

            stylesheet.append({
                'selector': seletor_atual,
                'style': {
                    'line-color': "#a71233",
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
    Input('snapshots-store', 'data')  
)
def toggle_delete_button(nodes, edges, connect_mode_on, snaps):
    if snaps:
        return True
    if connect_mode_on:
        return True
    return not (nodes or edges)


@app.callback(
    Output('cytoscape-graph', 'layout', allow_duplicate=True), 
    Input('home-button', 'n_clicks'),
    State('toggle-peso', 'value'), 
    prevent_initial_call=True
)
def reset_layout(n_clicks, toggle_peso):
    if not n_clicks:
        raise PreventUpdate
    
    nodes = list(G.nodes())
    n_nodes = len(nodes)
    
    pos_dict = {} 
    
    if n_nodes > 0:
        raio = max(150, n_nodes * 45) 
        centro_x, centro_y = 400, 300
        
        for i, node in enumerate(nodes):
            angulo = 2 * math.pi * i / n_nodes
            nova_pos = {
                'x': centro_x + raio * math.cos(angulo),
                'y': centro_y + raio * math.sin(angulo)
            }
            G.nodes[node]['position'] = nova_pos
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
        'width': '300px', 'height': '85vh', 'padding': '0',
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

        conteudo.extend([
            html.H6(html.B("Vértice Selecionado:"), className="fw mb-2"),
            html.B("Rótulo: "), f"{node_id}", html.Br()
        ])

        has_loop = G.has_edge(node_id, node_id)
        conteudo.extend([
            html.B("Laço: "), f"{'Sim' if has_loop else 'Não'}", html.Br()
        ])

        if is_directed:
            in_edges = [f"{u}→{v}" for u, v in G.in_edges(node_id)]
            out_edges = [f"{u}→{v}" for u, v in G.out_edges(node_id)]
            todas_arestas = list(set(in_edges + out_edges))
        else:
            todas_arestas = [f"{u}-{v}" for u, v in G.edges(node_id)]

        conteudo.extend([
            html.B("Arestas Incidentes: "), f"{', '.join(todas_arestas) if todas_arestas else 'Nenhuma'}", html.Br()
        ])

        if is_directed:
            in_deg = G.in_degree(node_id)
            out_deg = G.out_degree(node_id)
            preds = list(G.predecessors(node_id))
            succs = list(G.successors(node_id))

            conteudo.extend([
                html.B("Grau de Entrada: "), f"{in_deg}", html.Br(),
                html.B("Grau de Saída: "), f"{out_deg}", html.Br(),
                html.B("Antecessores: "), f"{', '.join(preds) if preds else 'Nenhum'}", html.Br(),
                html.B("Sucessores: "), f"{', '.join(succs) if succs else 'Nenhum'}", html.Br()
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
                html.B("Grau: "), f"{deg}", html.Br(),
                html.B("Vizinho(s): "), f"{', '.join(vizinhos) if vizinhos else 'Nenhum'}", html.Br()
            ])

            # Classificação Não Orientada
            if deg == 0:
                tipo = "Isolado"
            elif deg == 1:
                tipo = "Folha"
            else:
                tipo = "Comum"

        conteudo.extend([
            html.B("Classificação: "), f"{tipo}"
        ])

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

        if G.is_directed():
            conteudo.extend([
                html.H6(html.B("Aresta Selecionada:"), className="fw mb-2"),
                html.B("Conexão: "), f"{src} -> {tgt}", html.Br(),
                html.B("Origem: "), f"{src}", html.Br(),
                html.B("Destino: "), f"{tgt}", html.Br()
            ])
        else:
            conteudo.extend([
                html.H6(html.B("Aresta Selecionada:"), className="fw mb-2"),
                html.B("Conexão: "), f"{src} - {tgt}", html.Br(),
                html.B("Extremidades: "), f"{src} e {tgt}", html.Br()
            ])

        if modo_peso != 'sem_peso':
            conteudo.extend([
                html.B("Peso: "), f"{peso}", html.Br()
            ])
        
        conteudo.extend([
            html.B("Tipo: "), f"{tipo}"
        ])
    else:
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
    State('dropdown-source', 'value'),
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
            "Execução cancelada.", style={'color': 'blue'})
        return None, 0, False, msg_stop, dash.no_update, dash.no_update

    if prop_id == 'btn-carregar-algo.n_clicks':
        if not algo:
            return dash.no_update, dash.no_update, dash.no_update, html.Span("Erro: Escolha um algoritmo primeiro!", style={'color': 'red', 'fontWeight': 'bold'}), dash.no_update, dash.no_update

        if source is None or str(source) == "":
            return dash.no_update, dash.no_update, dash.no_update, html.Span("Erro: Selecione um Vértice de Origem!", style={'color': 'red', 'fontWeight': 'bold'}), dash.no_update, dash.no_update

        if algo == 'bfs':
            snaps = bfs_snapshots(G, str(source))
        else:
            snaps = dfs_snapshots(G, str(source))

        msg = html.Span(f"Algoritmo {algo.upper()} carregado!", style={
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
    Input('btn-inicio-algo', 'n_clicks'),
    Input('btn-fim-algo', 'n_clicks'),  
    Input('animation-interval', 'n_intervals'),
    Input('slider-velocidade', 'value'),
    State('is-playing-store', 'data'),
    State('current-frame-store', 'data'),
    State('snapshots-store', 'data'),
    prevent_initial_call=True
)
def controlar_player(btn_play, btn_step, btn_prev, btn_inicio, btn_fim, n_ints, velocidade_idx, is_playing, current_frame, snaps):
    ctx = dash.callback_context
    if not ctx.triggered or not snaps:
        raise PreventUpdate

    prop_id = ctx.triggered[0]['prop_id']
    total_frames = len(snaps)
    max_frame = total_frames - 1

    mapa_ms = {0: 4000, 1: 2000, 2: 1000, 3: 667, 4: 500}
    intervalo_ms = mapa_ms.get(velocidade_idx, 1000)
    
    if current_frame is None:
        current_frame = 0

    if prop_id == 'slider-velocidade.value':
        return current_frame, is_playing, not is_playing, intervalo_ms

    if prop_id == 'btn-play-algo.n_clicks':
        novo_status_play = not is_playing
        if novo_status_play and current_frame >= max_frame:
            return 0, True, False, intervalo_ms
        return current_frame, novo_status_play, not novo_status_play, intervalo_ms

    elif prop_id == 'btn-step-algo.n_clicks':
        proximo_frame = min(current_frame + 1, max_frame)
        return proximo_frame, False, True, intervalo_ms

    elif prop_id == 'btn-prev-algo.n_clicks':
        quadro_anterior = max(current_frame - 1, 0)
        return quadro_anterior, False, True, intervalo_ms

    elif prop_id == 'btn-inicio-algo.n_clicks':
        return 0, False, True, intervalo_ms
        
    elif prop_id == 'btn-fim-algo.n_clicks':
        return max_frame, False, True, intervalo_ms

    elif prop_id == 'animation-interval.n_intervals':
        if is_playing:
            proximo_frame = current_frame + 1
            if proximo_frame >= total_frames:
                return current_frame, False, True, intervalo_ms
            return proximo_frame, True, False, intervalo_ms

    return current_frame, is_playing, not is_playing, intervalo_ms


@app.callback(
    Output('card-execucao-algo', 'style'),
    Output('titulo-card-algo', 'children'), 
    Output('texto-narracao-algo', 'children'),
    Output('texto-variaveis-algo', 'children'),
    Input('current-frame-store', 'data'),
    State('snapshots-store', 'data'),
    State('card-execucao-algo', 'style'),
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
        fila_atual = quadro['Q']
        if fila_atual:
            str_fila = ", ".join([str(v) for v in fila_atual])
            texto_fila = f"[{str_fila}]"
        else:
            texto_fila = "[ Ø ]"
            
        elementos_globais.append(html.Div([
            html.B("Fila Q: ",  style={'color': "#080808"}),
            html.Span(texto_fila, className="fw-bold")
        ], className="mb-2 text-center", style={'fontSize': '14px'}))

    if algo == 'dfs':
        infos_dfs = []
        
        if 'tempo' in quadro:
            infos_dfs.append(html.Span([
                html.B("Tempo: ",  style={'color': "#080808"}),
                html.Span(f"{quadro['tempo']}", className="fw-bold me-3")
            ]))
   
        if 'pilha' in quadro:
            pilha_atual = quadro['pilha']
            if pilha_atual:
                str_pilha = ", ".join(reversed([str(v) for v in pilha_atual]))
                texto_pilha = f"[Topo -> {str_pilha}]"
            else:
                texto_pilha = "[ Ø ]"
                
            infos_dfs.append(html.Span([
                html.B("Pilha: ",  style={'color': "#080808"}),
                html.Span(texto_pilha, className="fw-bold") 
            ]))

        if infos_dfs:
            elementos_globais.append(html.Div(
                infos_dfs, className="mb-2 text-center", style={'fontSize': '14px'}
            ))

    # 2. CONSTRUÇÃO DA TABELA DE VÉRTICES
    cores_dict = quadro.get('c', {})
    d_dict = quadro.get('d', {})
    pi_dict = quadro.get('pi', {})
    f_dict = quadro.get('f', {})

    vertices = sorted(list(cores_dict.keys()),
                      key=lambda x: int(x) if str(x).isdigit() else x)

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

    tbody_rows = []
    for v in vertices:
        cor_nome = cores_dict.get(v, "Branco")
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

    tabela_completa = html.Div(
        style={'maxHeight': '250px', 'overflowY': 'auto'},
        children=[
            html.Table(className="table table-sm table-bordered table-striped mb-0", style={'fontSize': '12px'}, children=[
                html.Thead(html.Tr(thead_cols), className="table-light"),
                html.Tbody(tbody_rows)
            ])
        ]
    )

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
        s_player['display'] = 'flex'
        estilo_painel['transform'] = 'translateX(100%)'
        seta = '◀'
        s_top['pointerEvents'] = 'none'
        s_top['opacity'] = '0.5'
        travar_painel = True
    else:
        s_player['display'] = 'none'
        s_top['pointerEvents'] = 'auto'
        s_top['opacity'] = '1'
        travar_painel = False

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
    novo_estilo = estilo_atual.copy() if estilo_atual else {}

    if is_playing:
        novo_estilo['backgroundImage'] = 'url(assets/icons/pause.svg)'
    else:
        novo_estilo['backgroundImage'] = 'url(assets/icons/play.svg)'

    return novo_estilo

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
        'tpl-arvore': 'arvore',
        'tpl-casa': 'casa',
        'tpl-estrela': 'estrela',
        'tpl-hipercubo': 'hipercubo',
        'tpl-triangulo': 'trianguloCompleto',
        'tpl-k33': 'k33',
        'tpl-zedografo': 'zeDoGrafo'
    }
    
    nome_base = mapa_arquivos.get(prop_id)
    if not nome_base:
        raise PreventUpdate
        
    caminho_txt_origem = f'templates/{nome_base}.txt'
    caminho_json_origem = f'templates/{nome_base}.json'

    os.makedirs('templates', exist_ok=True)

    if os.path.exists(caminho_txt_origem):
        shutil.copy(caminho_txt_origem, 'data/graph.txt')
    else:
        return dash.no_update, dash.no_update, html.Span(f"Erro: Arquivo {caminho_txt_origem} não encontrado!", style={'color': 'red'}), dash.no_update, dash.no_update

    if os.path.exists(caminho_json_origem):
        shutil.copy(caminho_json_origem, 'data/config.json')
    else:
        if os.path.exists('data/config.json'):
            os.remove('data/config.json')
    
    config = load_graph_data(from_upload=False)
    novos_elementos = nx_to_cytoscape(G)
    
    layout = {'name': 'preset', 'animate': True, 'animationDuration': 500, 'fit': True, 'padding': 40}
    msg = html.Span(f"Modelo '{nome_base}' carregado com sucesso!", style={'color': 'green'})
    
    dir_val = 'orientado' if config.get('is_directed', False) else 'nao_orientado'
    peso_val = 'com_peso' if config.get('is_weighted', True) else 'sem_peso'
    
    return novos_elementos, layout, msg, dir_val, peso_val, ""

@app.callback(
    Output("modal-ajuda", "is_open"),
    [Input("btn-abrir-ajuda", "n_clicks"), 
     Input("btn-fechar-ajuda", "n_clicks")],
    [State("modal-ajuda", "is_open")],
    prevent_initial_call=True
)
def alternar_modal_ajuda(n_abrir, n_fechar, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
   
    return not is_open

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
            el.style.animation = 'none';
            el.offsetHeight;
            el.style.animation = 'fadeOutMsg 5.0s forwards';
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output('keyboard-listener-dummy',
           'data-fade'),
    Input('action-output-message', 'children'),
    prevent_initial_call=True
)

app.clientside_callback(
    """
    function(zoom, pan) {
        // Proteção contra o "undefined" no carregamento inicial da página!
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


@server.route('/download/graph.txt')
def download_graph_file():
    return send_file(GRAPH_FILE_PATH, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
