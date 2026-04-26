import dash_bootstrap_components as dbc
from dash import html, dcc

def criar_cabecalho():
    return dbc.Row(id='top-buttons-container', className="align-items-center mb-2 mt-2", style={'transition': 'opacity 0.3s'}, children=[

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
                        
                        dbc.DropdownMenuItem("🌳 Árvore", id="tpl-arvore", style={'width': '240px', 'padding': '10px 15px', 'fontSize': '15px', 'fontWeight': '600'}),
                        dbc.DropdownMenuItem("🏠 Casa", id="tpl-casa", style={'width': '240px', 'padding': '10px 15px', 'fontSize': '15px', 'fontWeight': '600'}),
                        dbc.DropdownMenuItem("⭐ Estrela", id="tpl-estrela", style={'width': '240px', 'padding': '10px 15px', 'fontSize': '15px', 'fontWeight': '600'}),
                        dbc.DropdownMenuItem("🧊 Hipercubo", id="tpl-hipercubo", style={'width': '240px', 'padding': '10px 15px', 'fontSize': '15px', 'fontWeight': '600'}),
                        dbc.DropdownMenuItem("🔺 Triângulo Completo (K4)", id="tpl-triangulo", style={'width': '240px', 'padding': '10px 15px', 'fontSize': '15px', 'fontWeight': '600'}),
                        dbc.DropdownMenuItem("❌ Não Planar (K3,3)", id="tpl-k33", style={'width': '240px', 'padding': '10px 15px', 'fontSize': '15px', 'fontWeight': '600'}),
                        dbc.DropdownMenuItem("🧙 Zé do Grafo", id="tpl-zedografo", style={'width': '240px', 'padding': '10px 15px', 'fontSize': '15px', 'fontWeight': '600'}),
                    ]
                )
            ]),

            html.Div(className='image-container', children=[
                dbc.DropdownMenu(
                    label="", 
                    toggle_style={
                        'backgroundImage': 'url(assets/icons/download.svg)',
                        'backgroundSize': 'contain', 'backgroundColor': 'transparent', 'border': 'none',
                        'width': '40px', 'height': '40px',
                    },
                    caret=False, direction="down", align_end=False, className="menu-templates-espacado",
                    children=[
                        dbc.DropdownMenuItem("Salvar Grafo Padrão", id="btn-download-padrao", style={'width': '240px', 'padding': '10px 15px', 'fontSize': '15px', 'fontWeight': '600'}),
                        dbc.DropdownMenuItem("Salvar com Posições", id="btn-download-posicoes", style={'width': '240px', 'padding': '10px 15px', 'fontSize': '15px', 'fontWeight': '600'}),
                    ]
                ),
                dcc.Download(id="download-graph-data") # Componente que processa o arquivo
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
    ])