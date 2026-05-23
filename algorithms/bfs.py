def bfs_snapshots(G, s):
    s = str(s) 
    c = {}
    d = {}
    pi = {}
    snapshots = [] 

    for u in G.nodes():
        c[u] = "Branco"
        d[u] = None
        pi[u] = None

    nodes_to_visit = list(G.nodes())
    if s in nodes_to_visit:
        nodes_to_visit.remove(s)
        nodes_to_visit.insert(0, s)

    for start_node in nodes_to_visit:
        if c[start_node] == "Branco":
            
            c[start_node] = "Cinza"
            d[start_node] = 0
            pi[start_node] = None
            Q = [start_node]

            tipo_acao = 'Inicio' if start_node == s else 'Nova_Arvore'
            msg_inicio = f"Iniciando Busca em Largura (BFS) a partir do vértice {start_node}." if start_node == s else f"Iniciando nova árvore de busca a partir do vértice {start_node}."

            snapshots.append({
                'acao': tipo_acao,
                'u': start_node,
                'c': c.copy(),
                'd': d.copy(),
                'pi': pi.copy(),
                'Q': list(Q),
                'descricao': msg_inicio
            })

            while Q:
                u = Q.pop(0)
                
                snapshots.append({
                    'acao': 'Processando',
                    'u': u,
                    'c': c.copy(),
                    'd': d.copy(),
                    'pi': pi.copy(),
                    'Q': list(Q),
                    'descricao': f"Explorando os vizinhos do vértice {u}..."
                })

                for v in G.adj[u]:
                    if c[v] == "Branco":
                        c[v] = "Cinza"
                        d[v] = d[u] + 1
                        pi[v] = u
                        Q.append(v)
                        
                        snapshots.append({
                            'acao': 'Descobrindo',
                            'u': u,
                            'v': v,
                            'aresta_atual': (u, v),
                            'c': c.copy(),
                            'd': d.copy(),
                            'pi': pi.copy(),
                            'Q': list(Q),
                            'descricao': f"Vértice {v} descoberto! Adicionado à fila."
                        })
                    else:
                        snapshots.append({
                            'acao': 'Ignorando',
                            'u': u,
                            'v': v,
                            'aresta_atual': (u, v),
                            'c': c.copy(),
                            'd': d.copy(),
                            'pi': pi.copy(),
                            'Q': list(Q),
                            'descricao': f"Aresta ignorada: Vértice {v} já foi descoberto."
                        })

                c[u] = "Preto"
                
                snapshots.append({
                    'acao': 'Finalizando',
                    'u': u,
                    'c': c.copy(),
                    'd': d.copy(),
                    'pi': pi.copy(),
                    'Q': list(Q),
                    'descricao': f"Vértice {u} totalmente explorado."
                })

    return snapshots