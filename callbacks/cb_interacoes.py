import dash
from dash import html
from dash import dcc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import networkx as nx
import base64
import random
import os
import json
import math

import utils.graph_logic as gl
from utils.graph_logic import save_graph_data, load_graph_data, nx_to_cytoscape, obter_propriedades_grafo, obter_matriz_adjacencia

def registrar_callbacks_interacoes(app):

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
        Output('texto-info-grafo-matriz-cartao', 'children'), 
        Output('texto-info-grafo-matriz-modal', 'children'),
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
        Input('auto-save-data', 'value'),
        Input('btn-confirmar-geracao', 'n_clicks'),
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
        State('gen-vertices', 'value'),
        State('gen-arestas', 'value'),
        State('gen-direcao', 'value'),
        State('gen-peso', 'value'),
        prevent_initial_call=True
    )
    def main_callback(
        add_v, del_s, clear_all, upload_contents, tapped_node_data, tapped_edge_data, btn_salvar_peso, btn_hidden_center, toggle_direcao, toggle_peso, btn_salvar_rotulo, shift_click_data, auto_save_data, btn_confirmar_geracao,
        sel_nodes, sel_edges, filename, cyto_elements, source_node_id, connect_mode_on,
        aresta_edit_store_data, modal_input_value, snaps, modal_is_open, modal_rotulo_is_open, modal_input_rotulo, vertex_edit_store_data, v_gen, e_gen, dir_gen, peso_gen
    ):
        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate
        prop_id = ctx.triggered[0]['prop_id']
        
        if cyto_elements:
            gl.atualizar_posicoes_no_grafo(cyto_elements)

        msg = dash.no_update
        layout_output = dash.no_update
        new_source_node = source_node_id
        graph_changed = False
        direcao_output = dash.no_update
        upload_reset = dash.no_update
        peso_output = dash.no_update
        nos_adicionados = []

        if prop_id == 'add-vertex-button.n_clicks':
            if snaps:
                msg = html.Span("Bloqueado: Não é possível adicionar vértices durante a animação.", style={'color': 'red'})
            elif modal_is_open or modal_rotulo_is_open:
                msg = dash.no_update
            else:
                node_ids = {int(n) for n in gl.G.nodes if str(n).isdigit()}
                new_id = 0
                while new_id in node_ids:
                    new_id += 1

                coluna = new_id % 8
                linha = new_id // 8
                pos_x = 80 + (coluna * 70)
                pos_y = 80 + (linha * 70)

                gl.G.add_node(str(new_id), position={'x': pos_x, 'y': pos_y})
                nos_adicionados.append(str(new_id))
                msg = html.Span(f"Vértice {new_id} adicionado.", style={'color': 'black'})
                graph_changed = True

                add_v_val = add_v if add_v else 0
                layout_output = {
                    'name': 'preset', 'fit': True, 'padding': 30, 'animate': True,
                    'animationDuration': 100, 'refresh_trigger': f"fit_add_{add_v_val}"
                }

        elif prop_id == 'shift-click-coords.value':
            if snaps:
                msg = html.Span("Bloqueado: Não é possível adicionar vértices durante a animação.", style={'color': 'red'})
            elif modal_is_open or modal_rotulo_is_open:
                msg = dash.no_update
            elif shift_click_data:
                partes = shift_click_data.split(',')
                if len(partes) >= 2:
                    try:
                        pos_x = float(partes[0])
                        pos_y = float(partes[1])
                        node_ids = {int(n) for n in gl.G.nodes if str(n).isdigit()}
                        new_id = 0
                        while new_id in node_ids:
                            new_id += 1
                        gl.G.add_node(str(new_id), position={'x': pos_x, 'y': pos_y})
                        nos_adicionados.append(str(new_id))
                        msg = html.Span(f"Vértice {new_id} adicionado.", style={'color': 'black'})
                        graph_changed = True
                    except ValueError:
                        msg = dash.no_update
        
        elif prop_id == 'auto-save-data.value':
            if auto_save_data:
                try:
                    data_package = json.loads(auto_save_data)
                    pos_dict = data_package.get('posicoes', {})
                    
                    for n_id, pos in pos_dict.items():
                        if gl.G.has_node(n_id):
                            gl.G.nodes[n_id]['position'] = pos
                    
                    gl.save_graph_data(toggle_peso == 'com_peso')
                    
                    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
                except Exception as e:
                    raise PreventUpdate
            raise PreventUpdate

        elif prop_id == 'cytoscape-graph.tapNodeData':
            if connect_mode_on:
                if tapped_node_data:
                    target_node_id = tapped_node_data['id']
                    if not source_node_id:
                        new_source_node = target_node_id
                        msg = html.Span(f"Vértice de origem {target_node_id} selecionado.", style={'color': 'black'})
                    elif source_node_id == target_node_id:
                        if gl.G.has_edge(source_node_id, target_node_id):
                            msg = html.Span("Laço já existe neste vértice.", style={'color': 'black'})
                        else:
                            gl.G.add_edge(source_node_id, target_node_id, label='1')
                            gl.G.edges[source_node_id, target_node_id]['real_source'] = source_node_id
                            gl.G.edges[source_node_id, target_node_id]['real_target'] = target_node_id
                            msg = html.Span(f"Laço criado no vértice {source_node_id}.", style={'color': 'black'})
                            graph_changed = True
                        new_source_node = None
                    else:
                        if gl.G.has_edge(source_node_id, target_node_id):
                            msg = html.Span("Aresta já existe.", style={'color': 'black'})
                        else:
                            gl.G.add_edge(source_node_id, target_node_id, label='1')
                            sep = "->" if gl.G.is_directed() else "-"
                            msg = html.Span(f"Aresta {source_node_id}{sep}{target_node_id} criada.", style={'color': 'black'})
                            graph_changed = True
                        new_source_node = None
            else:
                if tapped_node_data:
                    node_id = tapped_node_data['id']
                    msg = html.Span(f"Vértice {node_id} selecionado.", style={'color': 'black'})

        elif prop_id == 'cytoscape-graph.tapEdgeData':
            if not connect_mode_on and tapped_edge_data:
                source = tapped_edge_data['source']
                target = tapped_edge_data['target']
                sep = "->" if gl.G.is_directed() else "-"
                msg = html.Span(f"Aresta {source}{sep}{target} selecionada.", style={'color': 'black'})
                
        elif prop_id == 'btn-confirmar-geracao.n_clicks':
            if btn_confirmar_geracao:
                try:
                    v = int(v_gen)
                    e = int(e_gen)
                except (ValueError, TypeError):
                    msg = html.Span("Erro: Preencha vértices e arestas com números válidos.", style={'color': 'red', 'fontWeight': 'bold'})
                    return dash.no_update, msg, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

                if v < 1:
                    msg = html.Span("Erro: O grafo precisa ter pelo menos 1 vértice.", style={'color': 'red', 'fontWeight': 'bold'})
                    return dash.no_update, msg, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
                    
                if e < 0:
                    msg = html.Span("Erro: O número de arestas não pode ser negativo.", style={'color': 'red', 'fontWeight': 'bold'})
                    return dash.no_update, msg, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

                is_dir = (dir_gen == 'orientado')
                is_w = (peso_gen == 'com_peso')
                
                gl.gerar_grafo_aleatorio(v, e, is_directed=is_dir, is_weighted=is_w)
                
                direcao_output = dir_gen
                peso_output = peso_gen
                
                msg = html.Span("Grafo aleatório gerado com sucesso!", style={'color': 'black'})
                nos_adicionados.extend(list(gl.G.nodes()))
                
                new_source_node = None
                graph_changed = True

        elif prop_id == 'delete-selected-button.n_clicks':
            if snaps:
                msg = html.Span("Bloqueado: Não é possível deletar durante a animação.", style={'color': 'red'})
            elif modal_is_open or modal_rotulo_is_open:
                msg = dash.no_update
            elif not connect_mode_on and (sel_nodes or sel_edges):
                nodes_to_remove = {n['id'] for n in sel_nodes} if sel_nodes else set()
                edges_to_remove = [(e['source'], e['target']) for e in sel_edges] if sel_edges else []
                gl.G.remove_nodes_from(nodes_to_remove)
                gl.G.remove_edges_from(edges_to_remove)
                msg = html.Span("Elemento(s) removido(s).", style={'color': 'black'})
                graph_changed = True
                if source_node_id in nodes_to_remove:
                    new_source_node = None

        elif prop_id == 'clear-all-button.n_clicks':
            if snaps:
                msg = html.Span("Bloqueado: Não é possível limpar a tela durante a animação.", style={'color': 'red'})
            elif modal_is_open or modal_rotulo_is_open:
                msg = dash.no_update
            elif not gl.G.nodes:
                msg = html.Span(f"O grafo já está vazio.", style={'color': 'black'})
            else:
                gl.G.clear()
                msg = html.Span(f"Grafo limpo.", style={'color': 'black'})
                graph_changed = True
                new_source_node = None
            empty_msg = "" if gl.G.nodes else "Grafo vazio. Adicione um vértice para começar."

        elif prop_id == 'btn-salvar-peso.n_clicks':
            if aresta_edit_store_data and modal_input_value is not None:
                src = aresta_edit_store_data['source']
                tgt = aresta_edit_store_data['target']
                novo_peso_str = str(modal_input_value).strip()
                try:
                    novo_peso_int = int(novo_peso_str)
                    if gl.G.has_edge(src, tgt):
                        gl.G.edges[src, tgt]['label'] = str(novo_peso_int)
                        msg = html.Span(f"Peso atualizado para {novo_peso_int}", style={'color': 'black'})
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
                    elif gl.G.has_node(novo_id):
                        msg = html.Span(f"Erro: O vértice {novo_id} já existe!", style={'color': 'red', 'fontWeight': 'bold'})
                    elif gl.G.has_node(old_id):
                        nx.relabel_nodes(gl.G, {old_id: novo_id}, copy=False)
                        arestas_incidentes = []
                        if gl.G.is_directed():
                            arestas_incidentes.extend(gl.G.out_edges(novo_id, data=True))
                            arestas_incidentes.extend(gl.G.in_edges(novo_id, data=True))
                        else:
                            arestas_incidentes.extend(gl.G.edges(novo_id, data=True))

                        for u, v, data in arestas_incidentes:
                            if data.get('real_source') == old_id:
                                data['real_source'] = novo_id
                            if data.get('real_target') == old_id:
                                data['real_target'] = novo_id

                        msg = html.Span(f"Vértice {old_id} alterado para {novo_id}.", style={'color': 'black'})
                        graph_changed = True
                        if source_node_id == old_id:
                            new_source_node = novo_id
                except ValueError:
                    msg = html.Span("Erro: O ID deve ser um número inteiro.", style={'color': 'red'})

        elif prop_id == 'toggle-direcao.value':
            is_directed = (toggle_direcao == 'orientado')
            if is_directed and not gl.G.is_directed():
                novo_G = nx.DiGraph()
                novo_G.add_nodes_from(gl.G.nodes(data=True))
                for u, v, attrs in gl.G.edges(data=True):
                    attrs_ida = attrs.copy()
                    attrs_ida['real_source'] = u
                    attrs_ida['real_target'] = v
                    novo_G.add_edge(u, v, **attrs_ida)
                    if u != v:
                        attrs_volta = attrs.copy()
                        attrs_volta['real_source'] = v
                        attrs_volta['real_target'] = u
                        novo_G.add_edge(v, u, **attrs_volta)
                gl.G = novo_G
                msg = html.Span("Grafo alterado para Orientado.", style={'color': 'black'})
                graph_changed = True
            elif not is_directed and gl.G.is_directed():
                conflito = False
                for u, v, data in gl.G.edges(data=True):
                    if u != v and gl.G.has_edge(v, u):
                        peso_ida = data.get('label', '1')
                        peso_volta = gl.G.edges[v, u].get('label', '1')
                        if peso_ida != peso_volta:
                            conflito = True
                            break
                if conflito:
                    msg = html.Span("Erro: Pesos divergentes em arestas de ida e volta. Unifique os pesos antes de converter.", style={'color': 'red', 'fontWeight': 'bold'})
                    direcao_output = 'orientado'
                else:
                    novo_G = nx.Graph()
                    novo_G.add_nodes_from(gl.G.nodes(data=True))
                    for u, v, data in gl.G.edges(data=True):
                        if not novo_G.has_edge(u, v):
                            data_limpa = data.copy()
                            data_limpa['real_source'] = u
                            data_limpa['real_target'] = v
                            novo_G.add_edge(u, v, **data_limpa)
                    gl.G = novo_G
                    msg = html.Span("Grafo alterado para Não Orientado.", style={'color': 'black'})
                    graph_changed = True

        elif prop_id == 'toggle-peso.value':
            for u, v, data in gl.G.edges(data=True):
                data['label'] = '1'
            if toggle_peso == 'sem_peso':
                msg = html.Span("Grafo alterado para Não Ponderado.", style={'color': 'black'})
            else:
                msg = html.Span("Grafo alterado para Ponderado.", style={'color': 'black'})
            graph_changed = True

        elif prop_id == 'upload-data.contents':
            if upload_contents:
                # --- PRECAUÇÃO 1: Barrar extensões diferentes de .txt ---
                if not filename.lower().endswith('.txt'):
                    msg = html.Span("Erro: Apenas arquivos .txt são permitidos.", style={'color': 'red', 'fontWeight': 'bold'})
                    return dash.no_update, msg, dash.no_update, dash.no_update, dash.no_update, dash.no_update, None, dash.no_update, dash.no_update, dash.no_update, dash.no_update

                _, content_string = upload_contents.split(',')
                decoded = base64.b64decode(content_string).decode('utf-8')
                
                # Normaliza quebras de linha (evita bugs entre Windows/Linux)
                decoded = decoded.replace('\r\n', '\n')

                # --- PRECAUÇÃO 2: Verificar o separador '---' ---
                partes_arquivo = decoded.split('\n---\n')
                texto_grafo = partes_arquivo[0]
                texto_json = partes_arquivo[1] if len(partes_arquivo) > 1 else None

                linhas = [linha.strip() for linha in texto_grafo.splitlines() if linha.strip()]

                arquivo_valido = True
                msg_erro = ""
                vertices_unicos = set()
                qtd_arestas_reais = 0
                v_header = e_header = qtd_com_peso = qtd_sem_peso = 0
                arestas_lidas = {}

                # 1. Validação do TXT (Grafo)
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

                # --- PRECAUÇÃO 3: Validação do JSON ---
                config_json = None
                if arquivo_valido and texto_json:
                    try:
                        config_json = json.loads(texto_json.strip())
                        
                        if not isinstance(config_json.get('is_directed'), bool):
                            raise ValueError("'is_directed' deve ser booleano.")
                        if not isinstance(config_json.get('is_weighted'), bool):
                            raise ValueError("'is_weighted' deve ser booleano.")
                        if 'positions' not in config_json or not isinstance(config_json['positions'], dict):
                            raise ValueError("Falta o dicionário de 'positions'.")
                            
                        if len(config_json['positions']) != v_header:
                            raise ValueError(f"Quantidade de posições ({len(config_json['positions'])}) não bate com os {v_header} vértices declarados.")
                            
                    except json.JSONDecodeError:
                        arquivo_valido, msg_erro = False, "O JSON de posições está mal formatado ou corrompido."
                    except Exception as e:
                        arquivo_valido, msg_erro = False, f"Erro nas configurações: {str(e)}"

                if arquivo_valido:
                    with open(gl.GRAPH_FILE_PATH, 'w') as f:
                        f.write(texto_grafo)
                        
                    if config_json:
                        with open('data/config.json', 'w') as f:
                            f.write(texto_json.strip())
                            
                        gl.G = nx.DiGraph() if config_json['is_directed'] else nx.Graph()
                        direcao_output = 'orientado' if config_json['is_directed'] else 'nao_orientado'
                        msg_dir = "Orientado" if config_json['is_directed'] else "Não Orientado"
                        
                        peso_output = 'com_peso' if config_json['is_weighted'] else 'sem_peso'
                        msg_peso = "Ponderado" if config_json['is_weighted'] else "Não Ponderado"
                        
                    else:
                        if os.path.exists('data/config.json'):
                            os.remove('data/config.json')
                            
                        is_symmetric = True
                        for (u, v), peso in arestas_lidas.items():
                            if u == v:
                                continue
                            if (v, u) not in arestas_lidas or arestas_lidas[(v, u)] != peso:
                                is_symmetric = False
                                break

                        if is_symmetric and qtd_arestas_reais > 0:
                            gl.G = nx.Graph()
                            direcao_output = 'nao_orientado'
                            msg_dir = "Não Orientado"
                        else:
                            gl.G = nx.DiGraph()
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
                            if not (is_symmetric and qtd_arestas_reais > 0):
                                gl.G = nx.DiGraph()
                                direcao_output = 'orientado'
                                msg_dir = "Orientado"

                    gl.G.add_nodes_from(vertices_unicos)
                    for (u, v), peso in arestas_lidas.items():
                        gl.G.add_edge(u, v, label=peso, real_source=u, real_target=v)

                    msg = html.Span(f"Grafo {msg_dir} e {msg_peso} carregado!", style={'color': 'black'})
                    
                    nodes = list(gl.G.nodes())
                    n_nodes = len(nodes)
          
                    if config_json and 'positions' in config_json:
                        pos_dict = config_json['positions']
                        for node in nodes:
                            if node in pos_dict:
                                gl.G.nodes[node]['position'] = pos_dict[node]
                                
                        layout_output = {
                            'name': 'preset', 'padding': 50, 'animate': True, 'animationDuration': 500, 
                            'refresh_trigger': f"pos_json_{random.randint(0, 99999)}"
                        }
                    elif n_nodes > 0:
                        raio = max(150, n_nodes * 25) 
                        centro_x, centro_y = 400, 300
                        for i, node in enumerate(nodes):
                            angulo = 2 * math.pi * i / n_nodes
                            gl.G.nodes[node]['position'] = {
                                'x': centro_x + raio * math.cos(angulo),
                                'y': centro_y + raio * math.sin(angulo)
                            }
                            
                        layout_output = {
                            'name': 'preset', 'padding': 50, 'animate': True, 'animationDuration': 500, 
                            'refresh_trigger': f"pos_circ_{random.randint(0, 99999)}"
                        }
                    else:
                        layout_output = {'name': 'preset'}

                    nos_adicionados.extend(nodes)
                    new_source_node = None
                    graph_changed = True
                    upload_reset = None
                else:
                    msg = html.Span(f"Falha ao carregar: {msg_erro}", style={'color': 'red'})

                upload_reset = dash.no_update

        elif prop_id == 'btn-hidden-center.n_clicks':
            if btn_hidden_center:
                layout_output = {
                    'name': 'preset', 'fit': True, 'padding': 30, 'animate': True,
                    'animationDuration': 500, 'refresh_trigger': f"zoom_{btn_hidden_center}"
                }

        if graph_changed:
            tipo_peso_final = peso_output if peso_output != dash.no_update else toggle_peso
            is_weighted = (tipo_peso_final == 'com_peso')
            
            save_graph_data(is_weighted)

            new_elements = gl.nx_to_cytoscape(gl.G, manter_posicoes=True, novos_nos=nos_adicionados)
            empty_msg = "" if gl.G.nodes else "Grafo vazio. Adicione um vértice para começar."

            if not gl.G.nodes:
                layout_output = {'name': 'preset'}
            elif layout_output == dash.no_update:
                layout_output = {'name': 'preset', 'animate': True, 'fit': False, 'animationDuration': 100}
        else:
            new_elements = dash.no_update
            empty_msg = dash.no_update
            if not gl.G.nodes:
                layout_output = {'name': 'preset'}
            elif layout_output == dash.no_update:
                layout_output = {'name': 'preset', 'animate': True, 'fit': False, 'animationDuration': 100}

        tipo_peso_final = peso_output if peso_output != dash.no_update else toggle_peso
        tipo_dir = "Orientado" if gl.G.is_directed() else "Não Orientado"
        tipo_peso_tela = "Não Ponderado" if tipo_peso_final == 'sem_peso' else "Ponderado"
        propriedades_atuais = obter_propriedades_grafo(gl.G)
        
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

        info_texto = [
            html.B("Vértices: "), f"{gl.G.number_of_nodes()}", html.Br(),
            html.B("Arestas: "), f"{gl.G.number_of_edges()}", html.Br()
        ] + graus_text + [
            html.B("Direção: "), tipo_dir, html.Br(),
            html.B("Peso: "), tipo_peso_tela, html.Br(),
            html.B("Propriedades: "), propriedades_atuais
        ]
     
        indices, data_rows = obter_matriz_adjacencia(gl.G)
        
        m_top = [ html.Th("V", title="Vértices", className="text-center") ] + [html.Th(f"{n}", title=f"Vértice {n}",className="text-center") for n in indices]
        
        tbody_rows = []
        for idx, row_data in zip(indices, data_rows):
           
            table_row = [html.Th(idx, className="text-center")]
           
            table_row.extend([html.Td(cell, className="text-center") for cell in row_data])
            
            tbody_rows.append(html.Tr(table_row))
        
        info_matriz = html.Div(
            children=[
                html.Table(className="table table-sm table-bordered table-striped mb-0", style={'fontSize': '12px'}, children=[
                    html.Thead(html.Tr(m_top), className="table-light"),
                    html.Tbody(tbody_rows)
                ])
            ]
        )

        return new_elements, msg, layout_output, new_source_node, empty_msg, direcao_output, upload_reset, info_texto, peso_output, info_matriz, info_matriz

    @app.callback(
        Output('connect-mode-store', 'data'),
        Output('connect-mode-button', 'children'),
        Output('connect-mode-help-text', 'children'),
        Output('source-node-store', 'data', allow_duplicate=True),
        Output('action-output-message', 'children', allow_duplicate=True),
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
            msg = html.Span("Modo de Conexão Ativado.", style={'color': '#d97706'})
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
        for s in gl.BASE_STYLESHEET:
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
            stylesheet.append({'selector': ':selected', 'style': {'overlay-opacity': 0}})
            if source_node_id:
                stylesheet.append({'selector': f'node[id = "{source_node_id}"]', 'style': {
                                  'border-width': 4, 'border-color': '#f5a442', 'background-color': "#ffaf4d"}})

        if snaps and current_frame is not None and current_frame < len(snaps):
            quadro = snaps[current_frame]
            
            # --- LÓGICA DE CORES PARA BFS/DFS ---
            cores = quadro.get('c', {})
            for no_id, cor in cores.items():
                if cor == "Cinza":
                    stylesheet.append({
                        'selector': f'node[id = "{no_id}"]',
                        'style': {'background-color': '#999998', 'border-width': 4, 'border-color': "#858582", 'color': '#222', 'text-outline-color': '#222'}
                    })
                elif cor == "Preto":
                    stylesheet.append({
                        'selector': f'node[id = "{no_id}"]',
                        'style': {'background-color': '#212121', 'color': 'white', 'text-outline-color': 'white', 'border-color': '#212121'}
                    })
                    
            # --- NOVA LÓGICA DE CORES PARA SCC (TARJAN) ---
            if 'index' in quadro:
                visitados = quadro.get('index', {}).keys()
                sccs = quadro.get('sccs', [])
                scc_formada = quadro.get('scc_formada', None)
                pi_caminho = quadro.get('pi', {})

                paleta = [
                    ('#166534', '#14532d'), # Verde
                    ('#6b21a8', '#581c87'), # Roxo
                    ('#b45309', '#78350f'), # Laranja
                    ('#be185d', '#831843'), # Rosa
                    ('#0f766e', '#115e59'), # Teal
                    ('#1d4ed8', '#1e3a8a'), # Azul
                    ('#b91c1c', '#7f1d1d'), # Vermelho
                ]

                for v in visitados:
                    stylesheet.append({
                        'selector': f'node[id = "{v}"]',
                        'style': {'background-color': '#999998', 'border-color': '#858582'}
                    })

                for filho, pai in pi_caminho.items():
                    if pai is not None:
                        if direcao == 'orientado':
                            seletor_caminho = f'edge[source = "{pai}"][target = "{filho}"]'
                        else:
                            seletor_caminho = f'edge[source = "{pai}"][target = "{filho}"], edge[source = "{filho}"][target = "{pai}"]'

                        stylesheet.append({
                            'selector': seletor_caminho,
                            'style': {
                                'line-color': '#0284c7',
                                'target-arrow-color': '#0284c7',
                                'width': 4,
                                'line-style': 'solid', 
                                'z-index': 50 
                            }
                        })
                    
                for i, conjunto_scc in enumerate(sccs):
                    cor_fundo, cor_borda = paleta[i % len(paleta)]
                    
                    for v in conjunto_scc:
                        stylesheet.append({
                            'selector': f'node[id = "{v}"]',
                            'style': {'background-color': cor_fundo, 'border-color': cor_borda, 'color': 'white', 'text-outline-color': 'white'}
                        })
                        
                    for u in conjunto_scc:
                        for v in conjunto_scc:
                            if direcao == 'orientado':
                                seletor_aresta_scc = f'edge[source = "{u}"][target = "{v}"]'
                            else:
                                seletor_aresta_scc = f'edge[source = "{u}"][target = "{v}"], edge[source = "{v}"][target = "{u}"]'
                                
                            stylesheet.append({
                                'selector': seletor_aresta_scc,
                                'style': {
                                    'line-color': cor_fundo, 
                                    'target-arrow-color': cor_fundo, 
                                    'width': 4,
                                    'line-style': 'solid',
                                    'z-index': 100 
                                }
                            })
                            
                if scc_formada and quadro.get('acao') == 'Formando SCC':
                    for v in scc_formada:
                        stylesheet.append({
                            'selector': f'node[id = "{v}"]',
                            'style': {'background-color': cor_fundo, 'border-color': cor_borda, 'border-width': 5}
                        })

            # --- ARESTAS DO BFS/DFS ---
            pi_dict = quadro.get('pi', {})
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

            # --- ARESTA DE AÇÃO ATUAL ---
            aresta_atual = quadro.get('aresta_atual') 
            if not aresta_atual and 'v' in quadro and 'w' in quadro:
                 aresta_atual = (quadro['v'], quadro['w'])

            if aresta_atual:
                u, v = aresta_atual
                if direcao == 'orientado':
                    seletor_atual = f'edge[source = "{u}"][target = "{v}"]'
                else:
                    seletor_atual = f'edge[source = "{u}"][target = "{v}"], edge[source = "{v}"][target = "{u}"]'

                stylesheet.append({
                    'selector': seletor_atual,
                    'style': {'line-color': "#a71233", 'width': 4, 'target-arrow-color': '#a71233', 'z-index': 9999}
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
        if snaps or connect_mode_on:
            return True
        return not (nodes or edges)

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
        novo_estilo = current_style.copy()

        if not sel_nodes and not sel_edges:
            novo_estilo['display'] = 'none'
            return dash.no_update, novo_estilo

        novo_estilo['display'] = 'block'
        is_directed = (direcao == 'orientado')
        conteudo = []

        if sel_nodes and len(sel_nodes) == 1:
            node_id = str(sel_nodes[0]['id'])
            if not gl.G.has_node(node_id):
                novo_estilo['display'] = 'none'
                return dash.no_update, novo_estilo

            conteudo.extend([
                html.H6(html.B("Vértice Selecionado:"), className="fw mb-2"),
                html.B("Rótulo: "), f"{node_id}", html.Br()
            ])

            has_loop = gl.G.has_edge(node_id, node_id)
            conteudo.extend([
                html.B("Laço: "), f"{'Sim' if has_loop else 'Não'}", html.Br()
            ])

            if is_directed:
                in_edges = [f"{u}→{v}" for u, v in gl.G.in_edges(node_id)]
                out_edges = [f"{u}→{v}" for u, v in gl.G.out_edges(node_id)]
                todas_arestas = list(set(in_edges + out_edges))
            else:
                todas_arestas = [f"{u}-{v}" for u, v in gl.G.edges(node_id)]

            conteudo.extend([
                html.B("Arestas Incidentes: "), f"{', '.join(todas_arestas) if todas_arestas else 'Nenhuma'}", html.Br()
            ])

            if is_directed:
                in_deg = gl.G.in_degree(node_id)
                out_deg = gl.G.out_degree(node_id)
                preds = list(gl.G.predecessors(node_id))
                succs = list(gl.G.successors(node_id))

                conteudo.extend([
                    html.B("Grau de Entrada: "), f"{in_deg}", html.Br(),
                    html.B("Grau de Saída: "), f"{out_deg}", html.Br(),
                    html.B("Antecessores: "), f"{', '.join(preds) if preds else 'Nenhum'}", html.Br(),
                    html.B("Sucessores: "), f"{', '.join(succs) if succs else 'Nenhum'}", html.Br()
                ])

                if in_deg == 0 and out_deg > 0: tipo = "Fonte"
                elif out_deg == 0 and in_deg > 0: tipo = "Sumidouro"
                elif in_deg == 0 and out_deg == 0: tipo = "Isolado"
                else: tipo = "Comum"
            else:
                deg = gl.G.degree(node_id)
                vizinhos = list(gl.G.neighbors(node_id))

                conteudo.extend([
                    html.B("Grau: "), f"{deg}", html.Br(),
                    html.B("Vizinho(s): "), f"{', '.join(vizinhos) if vizinhos else 'Nenhum'}", html.Br()
                ])

                if deg == 0: tipo = "Isolado"
                elif deg == 1: tipo = "Folha"
                else: tipo = "Comum"

            conteudo.extend([html.B("Classificação: "), f"{tipo}"])

        elif sel_edges and len(sel_edges) == 1:
            edge = sel_edges[0]
            src = str(edge['source'])
            tgt = str(edge['target'])

            if not gl.G.has_edge(src, tgt):
                novo_estilo['display'] = 'none'
                return dash.no_update, novo_estilo

            peso = gl.G.edges[src, tgt].get('label', '1')
            tipo = "Laço" if src == tgt else "Simples"

            if gl.G.is_directed():
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
                conteudo.extend([html.B("Peso: "), f"{peso}", html.Br()])
            
            conteudo.extend([html.B("Tipo: "), f"{tipo}"])
        else:
            novo_estilo['display'] = 'none'
            return dash.no_update, novo_estilo

        return conteudo, novo_estilo
    
    @app.callback(
        Output("download-graph-data", "data"),
        [Input("btn-download-padrao", "n_clicks"),
         Input("btn-download-posicoes", "n_clicks")],
        State('toggle-peso', 'value'),
        prevent_initial_call=True,
    )
    def processar_download(n_padrao, n_posicoes, toggle_peso):
        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate
            
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        is_weighted = (toggle_peso == 'com_peso')
        
        incluir = (button_id == "btn-download-posicoes")
        
        conteudo = gl.gerar_conteudo_download(is_weighted=is_weighted, incluir_posicoes=incluir)
        
        return dict(content=conteudo, filename="grafo.txt")
    
    @app.callback(
        Output("modal-gerar-grafo", "is_open"),
        [Input("btn-abrir-modal-gerar", "n_clicks"),
         Input("btn-cancelar-geracao", "n_clicks"),
         Input("btn-confirmar-geracao", "n_clicks")],
        State("modal-gerar-grafo", "is_open"),
        prevent_initial_call=True
    )
    def gerenciar_modal_gerar(n_abrir, n_cancel, n_confirm, is_open):
        if n_abrir or n_cancel or n_confirm:
            return not is_open
        return is_open