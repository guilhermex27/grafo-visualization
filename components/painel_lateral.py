import dash_bootstrap_components as dbc
from dash import html, dcc

def criar_painel_lateral(tipo_dir_val, tipo_peso_val):
    return html.Div(id='coluna-painel', style={
        'position': 'absolute', 'right': '0', 'top': '0',
        'width': '300px', 'height': '88vh', 'padding': '0',
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
            
           # CARTÃO 4: Gerar Grafo Aleatório
            dbc.Button("Gerar Grafo Aleatório", id="btn-abrir-modal-gerar", color="dark", className="w-100 shadow-sm fw-bold mb-2"),

            # CARTÃO 5: Configurações
            html.Div(className='card shadow-sm border-0 p-3', children=[
                html.H6("Configurações",
                        className="fw-bold mb-3 text-center"),
                dcc.RadioItems(id='toggle-direcao', options=[{'label': ' Não Orientado', 'value': 'nao_orientado'}, {'label': ' Orientado', 'value': 'orientado'}],
                               value=tipo_dir_val, labelStyle={'display': 'block', 'textAlign': 'left', 'marginBottom': '5px'}, className="text-secondary"), 
                html.Hr(className="my-2"),
                dcc.RadioItems(id='toggle-peso', options=[{'label': ' Com Peso', 'value': 'com_peso'}, {
                               'label': ' Sem Peso', 'value': 'sem_peso'}], value=tipo_peso_val, labelStyle={'display': 'block', 'textAlign': 'left'}, className="text-secondary")  
            ]),

            # CARTÃO 6: Algoritmos
            html.Div(className='card shadow-sm border-0 p-3 mb-2', children=[
                html.H6("Algoritmos",
                        className="fw-bold mb-3 text-center"),
                dcc.Dropdown(id='dropdown-algo', options=[{'label': 'BFS (Busca em Largura)', 'value': 'bfs'}, {
                             'label': 'DFS (Busca em Profundidade)', 'value': 'dfs'}, {'label': 'SCC (Componentes Fortemente Conexas)', 'value': 'scc'}], placeholder="Escolha o Algoritmo", className="mb-2", style={'fontSize': '12px'}),
                dcc.Dropdown(id='dropdown-source', placeholder="Vértice de Origem",
                             className="mb-3", style={'fontSize': '12px'}),
                html.Button('Carregar Algoritmo', id='btn-carregar-algo',
                            className="btn btn-dark w-100 fw-bold")
            ])
        ])
    ])