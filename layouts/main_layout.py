import os
import dash_bootstrap_components as dbc
from dash import html, dcc
import dash_cytoscape as cyto

import utils.graph_logic as gl

from components.modals import criar_modal_peso, criar_modal_rotulo, criar_modal_ajuda
from components.cabecalho import criar_cabecalho
from components.cartoes import criar_cartao_info_grafo, criar_cartao_execucao, criar_player_flutuante
from components.painel_lateral import criar_painel_lateral


def serve_layout():
    os.makedirs(os.path.dirname(gl.GRAPH_FILE_PATH), exist_ok=True)
    config = gl.load_graph_data()  
    initial_elements = gl.nx_to_cytoscape(gl.G)

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

    tipo_dir_init = "Orientado" if gl.G.is_directed() else "Não Orientado"
    tipo_peso_init = "Com Peso" if any(
        'label' in data for _, _, data in gl.G.edges(data=True)) else "Sem Peso"

    propriedades_init = gl.obter_propriedades_grafo(gl.G)
    
    if gl.G.is_directed():
        soma_in = sum([d for n, d in gl.G.in_degree()])
        soma_out = sum([d for n, d in gl.G.out_degree()])
        graus_text = [
            html.B("Soma dos Graus (Entrada): "), f"{soma_in}", html.Br(),
            html.B("Soma dos Graus (Saída): "), f"{soma_out}", html.Br()
        ]
    else:
        graus_text = [
            html.B("Soma dos Graus: "), f"{sum([d for n, d in gl.G.degree()])}", html.Br()
        ]

    initial_info_children = [
        html.B("Vértices: "), f"{gl.G.number_of_nodes()}", html.Br(),
        html.B("Arestas: "), f"{gl.G.number_of_edges()}", html.Br()
    ] + graus_text + [
        html.B("Direção: "), tipo_dir_init, html.Br(),
        html.B("Peso: "), tipo_peso_init, html.Br(),
        html.B("Propriedades: "), propriedades_init
    ]
    
    indices, data_rows = gl.obter_matriz_adjacencia(gl.G)
    
    m_top = [ html.Th("V", title="Vértices", className="text-center") ] + [html.Th(f"{n}", title=f"Vértice {n}",className="text-center") for n in indices]
        
    tbody_rows = []
    for idx, row_data in zip(indices, data_rows):
       
        table_row = [html.Th(idx, className="text-center")]
       
        table_row.extend([html.Td(cell, className="text-center") for cell in row_data])
        
        tbody_rows.append(html.Tr(table_row))
    
    info_matriz = html.Div(
        style={'maxHeight': '250px', 'overflowY': 'auto'},
        children=[
            html.H6(html.B("Matriz de Adjacência:"), className="fw mb-2"),
            html.Br(),
            html.Table(className="table table-sm table-bordered table-striped mb-0", style={'fontSize': '12px'}, children=[
                html.Thead(html.Tr(m_top), className="table-light"),
                html.Tbody(tbody_rows)
            ])
        ]
    )
    
    initial_matriz_children = info_matriz

    return dbc.Container(fluid=True, style={'overflowX': 'hidden'}, children=[
        
        # STORES
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

        # MODAIS
        criar_modal_peso(),
        criar_modal_rotulo(),
        criar_modal_ajuda(),

        # LINHA 1: CABEÇALHO
        criar_cabecalho(),

        # LINHA 2: GRAFO E PAINEL
        dbc.Row(style={'margin': '0', 'position': 'relative', 'overflowX': 'hidden'}, children=[

            # LADO ESQUERDO: O GRAFO 
            dbc.Col(id='coluna-grafo', width=12, style={'position': 'relative', 'border': '1px solid #ccc', 'backgroundColor': '#fff', 'height': '88vh', 'padding': '0'}, children=[
                cyto.Cytoscape(
                    id='cytoscape-graph', elements=initial_elements, stylesheet=gl.BASE_STYLESHEET,
                    style={'width': '100%', 'height': '100%'},
                    layout={'name': 'preset', 'animate': True,
                            'animationDuration': 500},
                    wheelSensitivity=0.1
                ),

                dcc.Input(id='shift-click-coords', type='text',
                          style={'display': 'none'}, value=""),
                dcc.Store(id='camera-tracker-dummy'),
                dcc.Input(id='auto-save-data', type='text', style={'display': 'none'}, value=""),

                html.Div("" if gl.G.nodes else "Grafo vazio. Adicione um vértice para começar.", id='empty-graph-message', style={'position': 'absolute', 'top': '50%', 'left': '50%', 'transform': 'translate(-50%, -50%)', 'fontSize': '24px', 'color': '#888','fontWeight': 'bold',
                         'width': '100%', 'textAlign': 'center', 'pointerEvents': 'none'}),
                html.Div(id='keyboard-listener-dummy',
                         style={'display': 'none'}),
                html.Button(id='btn-hidden-center', n_clicks=0,
                            style={'display': 'none'}),

                criar_cartao_info_grafo(initial_info_children, initial_matriz_children),
                criar_cartao_execucao(),
                criar_player_flutuante(),
            ]),

            # LADO DIREITO: O PAINEL
            criar_painel_lateral(tipo_dir_val, tipo_peso_val)
        ]),
        
        # MENSAGEM OUTPUT
        html.Div(id='action-output-message', className="w-100 text-center mt-2", style={
            'minHeight': '30px',
            'pointerEvents': 'none',
            'fontWeight': 'bold',
            'color': '#111',  
            'fontSize': '15px',
            'whiteSpace': 'nowrap'
        })
    ])