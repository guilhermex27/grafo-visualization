import networkx as nx

def bfs_snapshots(G, s):
    s = str(s) # Blindagem de tipo
    c = {}
    d = {}
    pi = {}
    snapshots = [] 

    for u in G.nodes():
        c[u] = "Branco"
        d[u] = None
        pi[u] = None

    c[s] = "Cinza"
    d[s] = 0
    pi[s] = None
    Q = [s]

    snapshots.append({
        'acao': 'Inicio',
        'u': s,
        'c': c.copy(),
        'd': d.copy(),
        'pi': pi.copy(),
        'Q': list(Q),
        'descricao': f"Iniciando Busca em Largura (BFS) a partir do vértice {s}."
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
                
                # INSERIDO A ARESTA ATUAL AQUI
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
                # Feedback visual de aresta ignorada no BFS
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
            'descricao': f"Vértice {u} totalmente explorado (Ficou Preto)."
        })

    return snapshots