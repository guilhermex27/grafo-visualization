def scc_snapshots(G, s):
    s = str(s)
    index = 0  
    stack = []
    lowlink = {}
    index_map = {}
    on_stack = []
    sccs = []
    snapshots = []
    
    def strongconnect(v):
        nonlocal index
        index_map[v] = index
        lowlink[v] = index
        index += 1
        stack.append(v)
        on_stack.append(v)

        snapshots.append({
            'acao': 'Visitando',
            'v': v,
            'index': index_map.copy(),
            'lowlink': lowlink.copy(),
            'stack': list(stack),
            'on_stack': list(on_stack),
            'sccs': list(sccs),
            'descricao': f"Visitando o vértice {v}."
        })

        for w in G.adj[v]:
            if w not in index_map:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
                
                snapshots.append({
                    'acao': 'Atualizando Lowlink',
                    'v': v,
                    'w': w,
                    'index': index_map.copy(),
                    'lowlink': lowlink.copy(),
                    'stack': list(stack),
                    'on_stack': list(on_stack),
                    'sccs': list(sccs),
                    'descricao': f"Atualizando lowlink de {v} após visitar {w}."
                })
            elif w in on_stack:
                lowlink[v] = min(lowlink[v], index_map[w])
                
                snapshots.append({
                    'acao': 'Encontrando Arestas de retorno',
                    'v': v,
                    'w': w,
                    'index': index_map.copy(),
                    'lowlink': lowlink.copy(),
                    'stack': list(stack),
                    'on_stack': list(on_stack),
                    'sccs': list(sccs),
                    'descricao': f"Encontrada aresta de retorno de {v} para {w}, atualizando lowlink."
                })

        if lowlink[v] == index_map[v]:
            scc = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                scc.append(w)
                if w == v:
                    break
            sccs.append(scc)
            
            snapshots.append({
                'acao': 'Formando SCC',
                'scc_formada': scc,
                'index': index_map.copy(),
                'lowlink': lowlink.copy(),
                'stack': list(stack),
                'on_stack': list(on_stack),
                'sccs': list(sccs),
                'descricao': f"Formada a componente fortemente conectada: {scc}."
            })

    if s in G.nodes() and s not in index_map:
        strongconnect(s)

    for node in G.nodes():
        if node not in index_map:
            strongconnect(node)
    
    snapshots.append({
        'acao': 'Finalizado',
        'index': index_map.copy(),
        'lowlink': lowlink.copy(),
        'stack': list(stack),
        'on_stack': list(on_stack),
        'sccs': list(sccs),
        'descricao': f"Algoritmo finalizado! Foram encontradas {len(sccs)} Componentes Fortemente Conexas (SCCs)."
    })

    return snapshots