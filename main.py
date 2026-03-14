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
# 1. Backend: NetworkX e Configurações
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
            'label': 'data(label)', 'color': 'black', 'font-weight': '800',
            'text-margin-y': '-15px', 
        }
    },
    {
        'selector': ':selected',
        'style': {
            'border-width': 3, 'border-color': '#42a5f5'
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

app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

def serve_layout():
    os.makedirs(os.path.dirname(GRAPH_FILE_PATH), exist_ok=True)
    load_graph_data()
    initial_elements = nx_to_cytoscape(G)

    tipo_dir_init = "Orientado" if G.is_directed() else "Não Orientado"
    # Como o valor padrão definido no RadioItems de peso é 'com_peso':
    tipo_peso_init = "Ponderado" 
    
    initial_info_children = [
        html.B("Vértices: "), f"{G.number_of_nodes()}", html.Br(),
        html.B("Arestas: "), f"{G.number_of_edges()}", html.Br(),
        html.B("Direção: "), tipo_dir_init, html.Br(),
        html.B("Peso: "), tipo_peso_init
    ]

    return html.Div([
        dcc.Store(id='source-node-store', data=None),
        dcc.Store(id='connect-mode-store', data=False),
        dcc.Store(id='aresta-edit-store', data=None),
        dcc.Store(id='edge-edit-store', data=None),

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
        html.Div([
            html.H1("Editor de Grafo Interativo", style={'paddingLeft': '10px','paddingRight': '20px'}),
            html.Div([
                html.Button(id='home-button'),
            ], className='image-container'),
            html.Div([
                html.A(html.Button(style={'backgroundImage': 'url(assets/download.png)','backgroundPositionX': '1px','backgroundPositionY': '7px'}), id="download-link", href="/download/graph.txt"),
            ], className='image-container'),
            html.Div(children=[
                dcc.Upload(id='upload-data', children=html.Button(style={'backgroundImage': 'url(assets/upload.png)','backgroundPositionX': '-1px','marginTop':'13px'})),
            ], className='image-container')
        ],style={'display':'flex','justifyContent':'start'}),

        html.Div(style={'display': 'flex', 'flexDirection': 'row', 'height': '90vh', 'width': '100%'}, children=[

            # LADO ESQUERDO: O GRAFO (flex: 1 faz ele ocupar todo o espaço)
            html.Div(style={'flex': '1','position': 'relative', 'border': '1px solid #ccc', 'borderRadius': '8px', 'marginLeft': '2px', 'backgroundColor': '#fff'}, children=[
                cyto.Cytoscape(
                    id='cytoscape-graph',
                    elements=initial_elements,
                    stylesheet=BASE_STYLESHEET,
                    style={'width': '100%', 'height': '100%'},
                    layout={'name': 'circle', 'animate': True, 'animationDuration': 500},
                    wheelSensitivity=0.1
                ),
                html.Div(id='empty-graph-message', style={'position': 'absolute', 'top': '10px', 'width': '100%', 'textAlign': 'center', 'pointerEvents': 'none'}),
                html.Div(id='action-output-message', style={'position': 'absolute', 'bottom': '0px', 'width': '100%', 'textAlign': 'center', 'pointerEvents': 'none', 'fontWeight': 'bold'}),
                html.Div(id='keyboard-listener-dummy', style={'display': 'none'}),
                html.Button(id='btn-hidden-center', n_clicks=0, style={'display': 'none'}),

                html.Div([
                    html.Button(id='btn-info-grafo', n_clicks=0)
                ], className='info'),
                html.Div(id='card-info-grafo', className='card-info', style={'display': 'none'}, children=[
                    html.H4("Informações Gerais", style={'marginTop': '0', 'marginBottom': '10px', 'color': '#333'}),
                    html.Div(id='texto-info-grafo', children=initial_info_children, style={'fontSize': '14px', 'lineHeight': '1.6', 'color': '#444'})
                ])
            ]),

            # LADO DIREITO: SETA + PAINEL VERTICAL
            html.Div(style={'display': 'flex', 'flexDirection': 'row', 'height': '80vh', 'position': 'absolute', 'right': '0', 'top': '12vh', 'padding': '6px'}, children=[

                html.Div(style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'}, children=[
                    html.Button('◀', id='toggle-painel-btn', n_clicks=0, style={
                        'background': '#e0e0e0', 'color': 'black', 'border': 'none',
                        'fontSize': '22px', 'cursor': 'pointer', 'padding': '0', 'height': '10%','borderRadius': '10px 0 0 10px','width': '31px'
                    })
                ]),

                html.Div(id='conteudo-paineis', className='container-paineis', style={'display': 'none'}, children=[

                    html.Div(className='cartao-painel', style={'margin': '0 auto', 'width': '89%', 'marginBottom': '10px'}, children=[
                        html.H3("Configurações", style={'marginTop': '0', 'fontSize': '16px'}),
                        dcc.RadioItems(
                            id='toggle-direcao',
                            options=[
                                {'label': ' Não Orientado', 'value': 'nao_orientado'},
                                {'label': ' Orientado', 'value': 'orientado'}
                            ],
                            value='nao_orientado',
                            labelStyle={'display': 'block', 'textAlign': 'left', 'marginBottom': '5px'}
                        ),
                        html.Hr(style={'margin': '5px 0', 'border': '0.5px solid #ccc'}),
                        dcc.RadioItems(
                            id='toggle-peso',
                            options=[
                                {'label': ' Com Peso', 'value': 'com_peso'},
                                {'label': ' Sem Peso', 'value': 'sem_peso'}
                            ],
                            value='com_peso',
                            labelStyle={'display': 'block', 'textAlign': 'left'}
                        )
                    ]),

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
    prevent_initial_call=True
)
def main_callback(
    add_v, del_s, upload_contents, tapped_node_data, tapped_edge_data, btn_salvar_peso, btn_hidden_center, toggle_direcao,
    sel_nodes, sel_edges, filename, cyto_elements, source_node_id, connect_mode_on,
    aresta_edit_store_data, modal_input_value, toggle_peso
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
                    new_source_node = None
                    msg = html.Span("Modo de conexão cancelado.", style={'color': 'grey'})
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
        if not connect_mode_on and (sel_nodes or sel_edges):
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
    
    info_texto = [
        html.B("Vértices: "), f"{G.number_of_nodes()}", html.Br(),
        html.B("Arestas: "), f"{G.number_of_edges()}", html.Br(),
        html.B("Direção: "), tipo_dir, html.Br(),
        html.B("Peso: "), tipo_peso
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
    Input('toggle-direcao', 'value'), # NOVO GATILHO
    Input('toggle-peso', 'value')     # NOVO GATILHO
)
def update_stylesheet(source_node_id, connect_mode_on, direcao, peso):
    # Precisamos fazer uma cópia profunda manual para não alterar a constante BASE_STYLESHEET
    stylesheet = []
    for s in BASE_STYLESHEET:
        novo_s = s.copy()
        novo_s['style'] = s['style'].copy()
        stylesheet.append(novo_s)
        
    # Aplicando as regras de Direção e Peso
    for style in stylesheet:
        if style['selector'] == 'edge':
            if direcao == 'orientado':
                style['style']['target-arrow-shape'] = 'triangle'
                style['style']['curve-style'] = 'bezier' # Necessário para a seta aparecer bem
                
            if peso == 'sem_peso':
                style['style']['label'] = '' # Esconde o texto
            else:
                style['style']['label'] = 'data(label)' # Mostra o texto

    if connect_mode_on:
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
    prevent_initial_call=True
)
def alternar_modal(edge_data, cancel_clicks, save_clicks, current_style, modo_peso):
    ctx = dash.callback_context
    if not ctx.triggered: raise PreventUpdate
    prop_id = ctx.triggered[0]['prop_id']

    novo_estilo = current_style.copy()

    if prop_id == 'edge-edit-store.data' and edge_data:
        if modo_peso == 'sem_peso':
            return novo_estilo, dash.no_update, dash.no_update
    
        novo_estilo['display'] = 'flex'
        return novo_estilo, edge_data.get('label', ''), edge_data
    
    novo_estilo['display'] = 'none'
    return novo_estilo, dash.no_update, dash.no_update
    
@app.callback(
    Output('conteudo-paineis', 'style'),
    Output('toggle-painel-btn', 'children'),
    Input('toggle-painel-btn', 'n_clicks'),
    prevent_initial_call=True
)
def alternar_painel_inteiro(n_clicks):
    estilo_base = {
        'flexDirection': 'column', 'width': '250px',
        'backgroundColor': '#e0e0e0', 'borderRadius': '10px 0 0 10px', 'marginRight': '0px'
    }
    
    if n_clicks % 2 == 0:
        estilo_base['display'] = 'none' 
        return estilo_base, '◀'  
    else:
        estilo_base['display'] = 'flex' 
        return estilo_base, '▶'
    
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