import dash_bootstrap_components as dbc
from dash import html

def criar_modal_peso():
    return dbc.Modal([
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
    ], id='modal-editar-peso', is_open=False, centered=True)


def criar_modal_rotulo():
    return dbc.Modal([
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
    ], id='modal-editar-rotulo', is_open=False, centered=True)


def criar_modal_ajuda():
    return dbc.Modal([
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
    
def criar_modal_matriz(info_matriz):
    return dbc.Modal([
        dbc.ModalHeader(
            dbc.ModalTitle("Matriz de Adjacência", className="fw-bold"), 
            close_button=True
        ),
        dbc.ModalBody([
            html.Div(id="texto-info-grafo-matriz-modal", children=info_matriz, style={'maxHeight': '600px', 'overflowY': 'auto'})
        ]),
        dbc.ModalFooter(
            dbc.Button("Baixar Matriz", id="btn-exportar", className="ms-auto", n_clicks=0, color="primary")
        ),
    ], id="modal-matriz", is_open=False, size="lg", centered=True)
    
def criar_modal_gerar_grafo():
    return dbc.Modal([
        dbc.ModalHeader(
            dbc.ModalTitle("Gerar Grafo Aleatório", className="fw-bold"), 
            close_button=True
        ),
        dbc.ModalBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Vértices:", className="fw-bold", style={'fontSize': '14px'}),
                    dbc.Input(id="gen-vertices", type="number", min=1, max=100, value=1)
                ], width=6),
                dbc.Col([
                    html.Label("Arestas:", className="fw-bold", style={'fontSize': '14px'}),
                    dbc.Input(id="gen-arestas", type="number", min=0, max=9900, value=1)
                ], width=6),
            ], className="mb-3"),
            
            dbc.Row([
                dbc.Col([
                    html.Label("Direção:", className="fw-bold", style={'fontSize': '14px'}),
                    dbc.Select(id="gen-direcao", options=[
                        {"label": "Não Orientado", "value": "nao_orientado"},
                        {"label": "Orientado", "value": "orientado"}
                    ], value="nao_orientado")
                ], width=6),
                dbc.Col([
                    html.Label("Peso:", className="fw-bold", style={'fontSize': '14px'}),
                    dbc.Select(id="gen-peso", options=[
                        {"label": "Não Ponderado", "value": "sem_peso"},
                        {"label": "Ponderado", "value": "com_peso"}
                    ], value="sem_peso")
                ], width=6),
            ], className="mb-3"),
        ]),
        dbc.ModalFooter([
            dbc.Button("Cancelar", id="btn-cancelar-geracao", color="secondary"),
            dbc.Button("Gerar Grafo", id="btn-confirmar-geracao", color="success", className="fw-bold ms-2"),
        ]),
    ], id="modal-gerar-grafo", is_open=False, size="md", centered=True)