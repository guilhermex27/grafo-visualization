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

    # Função recursiva aninhada para gravar os snapshots facilmente
    def dfs_visit(u):
        nonlocal tempo
        tempo += 1
        d[u] = tempo
        c[u] = "Cinza"
        
        # Foto: Descobriu o nó
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
                
                # Foto: Indo para o vizinho mais fundo
                snapshots.append({
                    'acao': 'Avançando',
                    'u': u,
                    'v': v,
                    'c': c.copy(),
                    'pi': pi.copy(),
                    'd': d.copy(),
                    'f': f.copy(),
                    'tempo': tempo,
                    'descricao': f"Avançando do vértice {u} para o vizinho {v}."
                })
                dfs_visit(v)

        c[u] = "Preto"
        tempo += 1
        f[u] = tempo
        
        # Foto: Voltou (backtracking) e fechou o nó
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

    # Prepara a ordem de visita priorizando o nó escolhido pelo usuário
    nodes_to_visit = list(G.nodes())
    if source is not None and str(source) in nodes_to_visit:
        nodes_to_visit.remove(str(source))
        nodes_to_visit.insert(0, str(source))

    for u in nodes_to_visit:
        if c[u] == "Branco":
            # Foto: Nova raiz
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