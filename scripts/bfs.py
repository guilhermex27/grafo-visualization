import networkx as nx

def bfs_snapshots(G, s):
    c = {}
    d = {}
    pi = {}
    snapshots = [] # A nossa "fita de filme"

    for u in G.nodes():
        c[u] = "Branco"
        d[u] = None
        pi[u] = None

    c[s] = "Cinza"
    d[s] = 0
    pi[s] = None
    Q = [s]

    # Foto Inicial
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
        
        # Foto: Tirou da fila
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
                
                # Foto: Achou um vizinho branco
                snapshots.append({
                    'acao': 'Descobrindo',
                    'u': u,
                    'v': v,
                    'c': c.copy(),
                    'd': d.copy(),
                    'pi': pi.copy(),
                    'Q': list(Q),
                    'descricao': f"Vértice {v} descoberto! Adicionado à fila com distância {d[v]}."
                })

        c[u] = "Preto"
        
        # Foto: Terminou o nó
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