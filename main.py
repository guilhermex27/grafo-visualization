import os
import networkx as nx
import matplotlib.pyplot as plt
from flask import Flask, send_file, render_template, request, redirect, url_for

app = Flask(__name__)

GRAPH_FILE_PATH = 'data/graph.txt'

if not os.path.exists('static'):
    os.makedirs('static')
if not os.path.exists('data'):
    os.makedirs('data')

def generate_graph_image():
    try:
        with open(GRAPH_FILE_PATH, 'r') as f:
            lines = f.readlines()
        
        G = nx.parse_edgelist(lines[1:])

        plt.figure(figsize=(8, 6))
        nx.draw(G, with_labels=True, node_color='skyblue', node_size=2000, edge_color='gray', font_size=15)
        
        img_path = 'static/graph.png'
        plt.savefig(img_path)
        plt.close()
    except Exception as e:
        print(f"Erro ao gerar imagem do grafo: {e}")

@app.route('/')
def index():
    generate_graph_image()
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'Nenhum arquivo enviado!', 400
    
    file = request.files['file']
    
    if file.filename == '':
        return 'Nenhum arquivo selecionado!', 400
    
    if file:
        file.save(GRAPH_FILE_PATH)

        return redirect(url_for('index'))

@app.route('/download')
def download_file():
    """Permite o download do arquivo de grafo atual."""
    return send_file(GRAPH_FILE_PATH, as_attachment=True)

def main():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)

if __name__ == "__main__":
    main()
