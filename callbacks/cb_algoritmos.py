import dash
from dash import html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

import utils.graph_logic as gl
from algorithms.bfs import bfs_snapshots
from algorithms.dfs import dfs_snapshots
from algorithms.strongly_connected import scc_snapshots

def registrar_callbacks_algoritmos(app):

    @app.callback(
        Output('dropdown-source', 'options'),
        Input('cytoscape-graph', 'elements')
    )
    def atualizar_opcoes_origem(elements):
        if not elements:
            return []
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
        State('dropdown-source', 'value'),
        prevent_initial_call=True
    )
    def gerenciar_fita_algoritmo(click_carregar, click_stop, algo, source):
        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate
        prop_id = ctx.triggered[0]['prop_id']

        if prop_id == 'btn-stop-algo.n_clicks':
            msg_stop = html.Span("Execução cancelada.", style={'color': 'black'})
            return None, 0, False, msg_stop, dash.no_update, dash.no_update

        if prop_id == 'btn-carregar-algo.n_clicks':
            if not algo:
                return dash.no_update, dash.no_update, dash.no_update, html.Span("Erro: Escolha um algoritmo primeiro!", style={'color': 'red', 'fontWeight': 'bold'}), dash.no_update, dash.no_update
            if source is None or str(source) == "":
                return dash.no_update, dash.no_update, dash.no_update, html.Span("Erro: Selecione um Vértice de Origem!", style={'color': 'red', 'fontWeight': 'bold'}), dash.no_update, dash.no_update

            if algo == 'bfs':
                snaps = bfs_snapshots(gl.G, str(source))
            elif algo == 'dfs':
                snaps = dfs_snapshots(gl.G, str(source))
            elif algo == 'scc':
                snaps = scc_snapshots(gl.G, str(source))

            msg = html.Span(f"Algoritmo {algo.upper()} carregado!", style={'color': 'black'})
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
        Output('tabela-estados-algo', 'children'),
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
            return novo_estilo, dash.no_update, "", [], []

        novo_estilo['display'] = 'block'
        quadro = snaps[current_frame]
        narracao = quadro.get('descricao', '')

        titulo = "BFS (Largura)" if algo == 'bfs' else "DFS (Profundidade)" if algo == 'dfs' else "SCC (Componentes Fortemente Conexas)"
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
                infos_dfs.append(html.Br())
       
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

        if algo == 'scc':
            infos_scc = []
            
            # --- 1. LÓGICA DA MAIOR SCC ---
            sccs_atuais = quadro.get('sccs', [])
            if sccs_atuais:
                maior_scc = max(sccs_atuais, key=len)
                str_maior = ", ".join([str(v) for v in maior_scc])
                texto_maior_scc = f"{{ {str_maior} }}"
            else:
                texto_maior_scc = "{ Ø }"
                
            infos_scc.append(html.Span([
                html.B("Maior SCC: ", style={'color': "#080808"}),
                html.Span(texto_maior_scc, className="fw-bold me-3") 
            ]))
            infos_scc.append(html.Br())

            # --- 2. LÓGICA DA PILHA ---
            if 'stack' in quadro:
                pilha_atual = quadro['stack']
                if pilha_atual:
                    str_pilha = ", ".join(reversed([str(v) for v in pilha_atual]))
                    texto_pilha = f"[Topo -> {str_pilha}]"
                else:
                    texto_pilha = "[ Ø ]"
                    
                infos_scc.append(html.Span([
                    html.B("Pilha: ",  style={'color': "#080808"}),
                    html.Span(texto_pilha, className="fw-bold") 
                ]))

            if infos_scc:
                elementos_globais.append(html.Div(
                    infos_scc, className="mb-2 text-center", style={'fontSize': '14px'}
                ))
        
        cores_dict = quadro.get('c', {})
        d_dict = quadro.get('d', {})
        pi_dict = quadro.get('pi', {})
        f_dict = quadro.get('f', {})
        
        # Variáveis exclusivas do Tarjan (SCC)
        index_dict = quadro.get('index', {})
        lowlink_dict = quadro.get('lowlink', {})
        on_stack = quadro.get('on_stack', set())

        todos_vertices_vistos = set(cores_dict.keys()) | set(index_dict.keys())
        vertices = sorted(list(todos_vertices_vistos), key=lambda x: int(x) if str(x).isdigit() else x)

        thead_cols = [
            html.Th("V", title="Vértice", className="text-center")
        ]
        
        if algo == 'bfs':
            thead_cols.extend([
                html.Th("Cor", className="text-center"),
                html.Th("d", title="Distância", className="text-center"),
                html.Th("π", title="Predecessor", className="text-center")
            ])
        elif algo == 'dfs':
            thead_cols.extend([
                html.Th("Cor", className="text-center"),
                html.Th("d", title="Descoberta", className="text-center"),
                html.Th("f", title="Finalização", className="text-center"),
                html.Th("π", title="Predecessor", className="text-center")
            ])
        elif algo == 'scc':
            thead_cols.extend([
                html.Th("d", title="Descoberta", className="text-center"),
                html.Th("low", title="Lowlink (Menor alcance)", className="text-center"),
                html.Th("Pilha", title="Está na Pilha?", className="text-center")
            ])

        tbody_rows = []
        for v in vertices:
            row_cols = [html.Td(v, className="fw-bold text-center align-middle")]

            if algo in ['bfs', 'dfs']:
                cor_nome = cores_dict.get(v, "Branco")
                cor_badge = "⚪" if cor_nome == "Branco" else ("🔘" if cor_nome == "Cinza" else "⚫")
                pi_v = pi_dict.get(v, "-")
                if pi_v is None: pi_v = "-"
                d_v = d_dict.get(v, "-")
                if d_v is None or d_v == float('inf'): d_v = "∞"
                
                row_cols.append(html.Td(cor_badge, className="text-center align-middle"))

            if algo == 'bfs':
                row_cols.extend([
                    html.Td(str(d_v), className="text-center align-middle"),
                    html.Td(str(pi_v), className="text-center align-middle")
                ])
            elif algo == 'dfs':
                f_v = f_dict.get(v, "-") if f_dict else "-"
                row_cols.extend([
                    html.Td(str(d_v), className="text-center align-middle text-success fw-bold"),
                    html.Td(str(f_v), className="text-center align-middle text-danger fw-bold"),
                    html.Td(str(pi_v), className="text-center align-middle")
                ])
            elif algo == 'scc':
                idx_v = index_dict.get(v, "-")
                low_v = lowlink_dict.get(v, "-")
                na_pilha = "Sim" if v in on_stack else "Não"
                cor_texto_pilha = "fw-bold" if na_pilha == "Sim" else "text-danger fw-bold"

                row_cols.extend([
                    html.Td(str(idx_v), className="text-center align-middle fw-bold"),
                    html.Td(str(low_v), className="text-center align-middle fw-bold"),
                    html.Td(na_pilha, className=f"text-center align-middle {cor_texto_pilha}")
                ])

            tbody_rows.append(html.Tr(row_cols))

        tabela_completa = html.Div(
            style={'height': '250px', 'overflowY': 'auto'},
            children=[
                html.Table(className="table table-sm table-bordered table-striped mb-0", style={'fontSize': '12px'}, children=[
                    html.Thead(html.Tr(thead_cols), className="table-light"),
                    html.Tbody(tbody_rows)
                ])
            ]
        )

        return novo_estilo, titulo, narracao, elementos_globais, tabela_completa

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
            'width': '300px', 'height': '88vh', 'padding': '0', 'zIndex': 100
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
        Output("collapse-tabela-exec", "is_open"),
        Output("btn-toggle-tabela", "children"),
        Input("btn-toggle-tabela", "n_clicks"),
        State("collapse-tabela-exec", "is_open"),
        prevent_initial_call=True
    )
    def alternar_tabela_execucao(n_clicks, is_open):
        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate
        novo_estado = not is_open
        texto_btn = "Ocultar Tabela ▲" if novo_estado else "Mostrar Tabela ▼"
        return novo_estado, texto_btn