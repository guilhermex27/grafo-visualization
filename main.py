import os
from flask import send_file

from app import app, server

from layouts.main_layout import serve_layout
from utils.graph_logic import GRAPH_FILE_PATH

from callbacks.cb_interacoes import registrar_callbacks_interacoes
from callbacks.cb_algoritmos import registrar_callbacks_algoritmos
from callbacks.cb_geral import registrar_callbacks_geral
from callbacks.cb_clientside import registrar_clientside_callbacks

app.layout = serve_layout

registrar_callbacks_interacoes(app)
registrar_callbacks_algoritmos(app)
registrar_callbacks_geral(app)
registrar_clientside_callbacks(app)

@server.route('/download/graph.txt')
def download_graph_file():
    return send_file(GRAPH_FILE_PATH, as_attachment=True)

if __name__ == '__main__':
    porta = int(os.environ.get('PORT', 8080))
    app.run(debug=True, host='0.0.0.0', port=porta)