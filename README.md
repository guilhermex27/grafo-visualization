# Visualizador de Grafos usando NetworkX e Flask

ocultar menu
separar menu em dados do grafo, controles e algoritmos
nao redefinir posiçoes ao excluir um elemento
nao renomear nos, usar lista na memoria para armazenar posiçoes, depois gravar no arquivo com base nessas posiçoes, e depois ler e interpretar o arquivo de acordo.


add no info

1. Identificação (ID) do vértice
Cada vértice pode ter um rótulo ou identificador único (ex: nome, número), essencial para diferenciá-lo de outros, especialmente em grafos rotulados.

2. Lista de arestas incidentes
São as arestas (ou arcos, em grafos direcionados) conectadas ao vértice.
Em grafos direcionados, separa-se em:
Arestas de saída (arco sai do vértice).
Arestas de entrada (arco chega ao vértice). 

3. Lista de vértices adjacentes
Vértices diretamente conectados ao vértice em questão por uma aresta.
Em grafos direcionados, distingue-se:
Sucessores (vértices alcançáveis diretamente).
Antecessores (vértices que apontam para ele). 

4. Possui laço (loop)?
Um laço é uma aresta que conecta o vértice a ele mesmo. 
A presença de laços afeta o cálculo do grau (é contado duas vezes em grafos não direcionados). 

5. Grau do vértice
Grau = número total de arestas incidentes.

Em grafos direcionados:
Grau de entrada = número de arestas que chegam.
Grau de saída = número de arestas que saem.

Tipos especiais:
Vértice isolado: grau 0.
Vértice folha (pendente): grau 1.
Fonte: grau de entrada = 0 (em grafos direcionados).
Sumidouro: grau de saída = 0.

por aresta

1. Orientação (dirigida ou não?)
Em grafos não direcionados, a aresta conecta dois vértices sem sentido definido (ex: A–B). 
Em grafos direcionados, a aresta é um arco com sentido: tem um vértice de origem e um de destino (ex: A → B). 
2. Vértices conectados (extremos)
Toda aresta liga dois vértices (não necessariamente distintos).
Se os dois extremos forem o mesmo vértice, trata-se de um laço (loop). 
3. Peso ou valor (em grafos valorados)
Arestas podem ter pesos (ex: distância, custo, capacidade), usados em algoritmos como Dijkstra ou Prim. 
4. Tipo de aresta
Arestas paralelas: duas ou mais arestas ligam os mesmos vértices. 
Laço (loop): aresta que conecta um vértice a ele mesmo. 
Um grafo sem laços nem arestas paralelas é chamado de grafo simples.