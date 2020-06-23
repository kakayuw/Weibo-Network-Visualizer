from flask import Flask
from flask import render_template, send_from_directory, current_app
import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = os.path.dirname(os.getcwd()) + "\\Weibo-Network-Visualizer\\templates\\"
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'json'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route('/')
def hello_world():
    return 'Hello, World!'


@app.route('/test')
def hello():
    return render_template('index.html')


@app.route('/resources/<path:filename>')
def get_json(filename):
    print("filename is ", filename, app.config['UPLOAD_FOLDER'])
    return send_from_directory(directory=app.config['UPLOAD_FOLDER'], filename=filename)
