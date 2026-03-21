import networkx as nx

def dfs_snapshots(G, source=None):
    c = {}
    pi = {}
    d = {}
    f = {}
    snapshots = []
    
    for u in G.nodes():
        c[u] = "Branco"
        pi[u] = None
        d[u] = None
        f[u] = None
        
    tempo = 0

    def dfs_visit(u):
        nonlocal tempo
        tempo += 1
        d[u] = tempo
        c[u] = "Cinza"
        
        snapshots.append({
            'acao': 'Descobrindo',
            'u': u,
            'c': c.copy(),
            'pi': pi.copy(),
            'd': d.copy(),
            'f': f.copy(),
            'tempo': tempo,
            'descricao': f"Descobriu o vértice {u} no tempo {tempo}. (Ficou Cinza)"
        })

        for v in G.adj[u]:
            if c[v] == "Branco":
                pi[v] = u
                
                snapshots.append({
                    'acao': 'Avançando',
                    'u': u,
                    'v': v,
                    'aresta_atual': (u, v), 
                    'c': c.copy(),
                    'pi': pi.copy(),
                    'd': d.copy(),
                    'f': f.copy(),
                    'tempo': tempo,
                    'descricao': f"Avançando do vértice {u} para o vizinho {v}."
                })
                dfs_visit(v)
            else:
                snapshots.append({
                    'acao': 'Retorno',
                    'u': u,
                    'v': v,
                    'aresta_atual': (u, v),
                    'c': c.copy(),
                    'pi': pi.copy(),
                    'd': d.copy(),
                    'f': f.copy(),
                    'tempo': tempo,
                    'descricao': f"Aresta ignorada: Vértice {v} já foi visitado."
                })

        c[u] = "Preto"
        tempo += 1
        f[u] = tempo
        
        snapshots.append({
            'acao': 'Finalizando',
            'u': u,
            'c': c.copy(),
            'pi': pi.copy(),
            'd': d.copy(),
            'f': f.copy(),
            'tempo': tempo,
            'descricao': f"Retornou para {u}. Vizinhos esgotados no tempo {tempo}. (Ficou Preto)"
        })

    nodes_to_visit = list(G.nodes())
    if source is not None and str(source) in nodes_to_visit:
        nodes_to_visit.remove(str(source))
        nodes_to_visit.insert(0, str(source))

    for u in nodes_to_visit:
        if c[u] == "Branco":
            snapshots.append({
                'acao': 'Nova_Arvore',
                'u': u,
                'c': c.copy(),
                'pi': pi.copy(),
                'd': d.copy(),
                'f': f.copy(),
                'tempo': tempo,
                'descricao': f"Iniciando nova árvore de busca a partir de {u}."
            })
            dfs_visit(u)

    return snapshots