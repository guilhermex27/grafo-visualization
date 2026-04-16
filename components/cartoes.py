import dash_bootstrap_components as dbc
from dash import html, dcc

def criar_cartao_info_grafo(initial_info_children):
    return html.Div(className='info-container', children=[
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
    ])

def criar_cartao_execucao():
    return dbc.Card(id='card-execucao-algo', className="card shadow border-success p-0", style={
        'display': 'none', 'position': 'absolute', 'top': '10px', 'right': '0px', 'zIndex': 105,
        'backgroundColor': 'rgba(255, 255, 255, 0.95)', 'minWidth': '320px', 'maxWidth': '320px',
        'borderWidth': '2px', 'borderRadius': '8px', 'overflow': 'hidden'
    }, children=[
        dbc.CardHeader(html.H6(id='titulo-card-algo', children="⚙️ Execução",
                       className="fw-bold m-0 text-center", style={'color': "#080808"})),

        dbc.CardBody(className="p-3", children=[
            html.Div(id='texto-narracao-algo', className="text-dark fw-bold mb-3 text-center",
                     style={'fontSize': '14px', 'fontStyle': 'italic', 'minHeight': '42px'}),

            html.Div(id='texto-variaveis-algo'),
            
            html.Div(className="d-grid mt-1 mb-1", children=[
                dbc.Button("Mostrar Tabela ▼", id="btn-toggle-tabela", color="black", size="sm", 
                           className="text-muted border-0 fw-bold", style={'fontSize': '11px', 'boxShadow': 'none', 'backgroundColor': 'transparent'}),
            ]),
            
            dbc.Collapse(
                id="collapse-tabela-exec",
                is_open=False, 
                children=[
                    html.Div(id='tabela-estados-algo') 
                ]
            )
        ])
    ])

def criar_player_flutuante():
    return html.Div(id='player-flutuante', className='player card flex-column shadow-lg p-3 border-0', style={'display': 'none', 'backgroundColor': 'rgba(255, 255, 255, 0.95)'}, children=[

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
    ])