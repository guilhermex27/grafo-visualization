import os
import networkx as nx
import json

G = nx.Graph()
GRAPH_FILE_PATH = 'data/graph.txt'

BASE_STYLESHEET = [
    {
        'selector': 'node',
        'style': {
            'label': 'data(label)',
            'width': 40, 'height': 40,
            'text-valign': 'center', 'color': '#222',
            'text-outline-color': '#222', 'text-outline-width': '1px',
            'background-color': 'white', 'border-width': 4, 'border-color': '#222',
            'transition-property': 'background-color, border-width, border-color, width, height',
            'transition-duration': '0.2s',
        }
    },
    {
        'selector': 'edge',
        'style': {
            'label': 'data(label)', 
            'color': '#222',
            'line-color': '#222',    
            'target-arrow-color': '#222',
            'arrow-scale': 1.5,
            'text-background-color': '#ffffff',
            'text-background-opacity': 1,
            'text-background-shape': 'roundrectangle',
            'text-background-padding': '5px',
            'text-wrap': 'wrap',
            'text-outline-color': '#222', 'text-outline-width': '0.6px',
            'transition-property': 'line-color, width, target-arrow-color',
            'transition-duration': '0.2s',
            'curve-style': 'unbundled-bezier', 
            'control-point-step-size': '70px',
        }
    },
    {
        'selector': 'node:selected',
        'style': {
            'border-width': 4, 'border-color': '#42a5f5',
            'background-color': '#64b5f6',
            'color': '#ffffff',
            'text-outline-color': '#ffffff',
            'z-index': 9999
        }
    },
    {
        'selector': 'edge:selected', 
        'style': {
            'z-index': 9999,
            'line-color': '#42a5f5',
            'target-arrow-color': '#42a5f5',
            'text-outline-color': '#42a5f5', 'text-outline-width': '0.6px',
            'color': '#42a5f5',
            'width': '3px'        
        }
    },
]

def nx_to_cytoscape(graph_obj):
    cy_elements = []
    for node, attrs in graph_obj.nodes(data=True):
        label_atual = attrs.get('label', str(node))
        cy_node = {'data': {'id': str(node), 'label': str(label_atual)}}
        if 'position' in attrs:
            cy_node['position'] = attrs['position']
        cy_elements.append(cy_node)
    for source, target, attrs in graph_obj.edges(data=True):
        s = attrs.get('real_source', source)
        t = attrs.get('real_target', target)
        cy_edge = {'data': {'source': str(s), 'target': str(t)}}
        if attrs.get('label'):
            cy_edge['data']['label'] = attrs['label']
        cy_elements.append(cy_edge)
    return cy_elements

def obter_propriedades_grafo(graph_obj):
    if graph_obj.number_of_nodes() == 0:
        return "Vazio"
    props = []
    tem_lacos = nx.number_of_selfloops(graph_obj) > 0
    if tem_lacos:
        props.append("Pseudografo")
    else:
        props.append("Simples")

    if graph_obj.is_directed():
        if nx.is_strongly_connected(graph_obj):
            props.append("Fortemente Conexo")
        elif nx.is_weakly_connected(graph_obj):
            props.append("Fracamente Conexo")
        else:
            props.append("Desconexo")

        if nx.is_directed_acyclic_graph(graph_obj):
            props.append("DAG (Acíclico)")
            
        if nx.is_tree(graph_obj):
            props.append("Árvore")
        elif nx.is_forest(graph_obj):
            props.append("Floresta")
    else:
        if nx.is_connected(graph_obj):
            props.append("Conexo")
        else:
            props.append("Desconexo")

        if nx.is_tree(graph_obj):
            props.append("Árvore")
        elif nx.is_forest(graph_obj):
            props.append("Floresta")

    if nx.is_bipartite(graph_obj):
        props.append("Bipartido")

    if graph_obj.is_directed():
        degre_in = [d for n, d in graph_obj.in_degree()]
        degre_out = [d for n, d in graph_obj.out_degree()]
        if degre_in and degre_out:
            graus_distintos_in = len(set(degre_in))
            graus_distintos_out = len(set(degre_out))
            if graus_distintos_in == 1 and graus_distintos_out == 1 and degre_in[0] == degre_out[0]:
                props.append("Regular")
            else:
                props.append("Irregular")
    else:
        graus = [d for n, d in graph_obj.degree()]
        if graus:
            qtd_graus_distintos = len(set(graus))
            if qtd_graus_distintos == 1:
                props.append("Regular")
            else:
                props.append("Irregular")

    n = graph_obj.number_of_nodes()
    e = graph_obj.number_of_edges()
    if n > 1 and not tem_lacos:
        max_edges = n * (n - 1) if graph_obj.is_directed() else n * (n - 1) // 2
        if e == max_edges:
            props.append("Completo")
            
    is_planar, _ = nx.check_planarity(graph_obj)
    if is_planar:
        props.append("Planar")
    else:
        props.append("Não Planar")

    return ", ".join(props)

def load_graph_data(from_upload=False):
    global G
    config = {'is_directed': False, 'is_weighted': True, 'positions': {}}

    if os.path.exists('data/config.json'):
        try:
            with open('data/config.json', 'r') as f:
                config = json.load(f)
        except Exception:
            pass

    if not from_upload:
        G = nx.DiGraph() if config.get('is_directed', False) else nx.Graph()

    if not os.path.exists(GRAPH_FILE_PATH) or os.path.getsize(GRAPH_FILE_PATH) == 0:
        return config

    with open(GRAPH_FILE_PATH, 'r') as f:
        lines = [line.strip() for line in f.read().splitlines() if line.strip()]

    if not lines:
        return config

    try:
        header = lines.pop(0).split()
        num_nodes_header = int(header[0])
        for line in lines:
            parts = line.split()
            if len(parts) >= 2:
                source, target = parts[0], parts[1]
                weight = parts[2] if len(parts) > 2 else '1'

                if G.is_directed() or not G.has_edge(source, target):
                    G.add_edge(source, target, label=weight, real_source=source, real_target=target)

        nodes_to_add_count = num_nodes_header - len(G.nodes)
        if nodes_to_add_count > 0:
            i = 0
            while nodes_to_add_count > 0:
                node_id = str(i)
                if not G.has_node(node_id):
                    G.add_node(node_id)
                    nodes_to_add_count -= 1
                i += 1

        if not from_upload:
            pos_dict = config.get('positions', {})
            for node_id in G.nodes():
                if node_id in pos_dict:
                    G.nodes[node_id]['position'] = pos_dict[node_id]
    except Exception as e:
        print(f"Erro ao processar: {e}")
        G.clear()

    return config

def save_graph_data(is_weighted=True):
    linhas_arestas = []
    for source, target, data in G.edges(data=True):
        s = data.get('real_source', source)
        t = data.get('real_target', target)
        peso = data.get('label', '1')

        if is_weighted:
            linhas_arestas.append(f"{s} {t} {peso}")
        else:
            linhas_arestas.append(f"{s} {t}")

        if not G.is_directed() and s != t:
            if is_weighted:
                linhas_arestas.append(f"{t} {s} {peso}")
            else:
                linhas_arestas.append(f"{t} {s}")

    with open(GRAPH_FILE_PATH, 'w') as f:
        f.write(f"{G.number_of_nodes()} {len(linhas_arestas)}\n")
        for linha in linhas_arestas:
            f.write(linha + "\n")

    config = {
        'is_directed': G.is_directed(),
        'is_weighted': is_weighted,
        'positions': {str(n): G.nodes[n].get('position', {'x': 0, 'y': 0}) for n in G.nodes}
    }
    with open('data/config.json', 'w') as f:
        json.dump(config, f)