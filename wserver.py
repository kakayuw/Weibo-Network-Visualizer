import time

from flask import Flask
from flask import render_template, send_from_directory, current_app, g
import os
from werkzeug.utils import secure_filename

from SpiderController import SpiderController

UPLOAD_FOLDER = os.path.dirname(os.getcwd()) + "\\Weibo-Network-Visualizer\\templates\\"
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'json'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.before_request
def init():
    WEIBO_FOLDER = os.path.dirname(os.getcwd()) + "\\Weibo-Network-Visualizer\\weibo\\"
    g.cxt = SpiderController(WEIBO_FOLDER)
    g.start = time.time()


@app.after_request
def after_request(response):
    diff = time.time() - g.start
    print("request response time:", diff)
    return response


@app.route('/')
def hello_world():
    return 'Hello, World!'


@app.route('/index')
def hello():
    return render_template('index.html')


@app.route('/<uuid>')
def layer2(uuid=None):
    return render_template('layer2.html', uuid=uuid)


@app.route('/resources/<path:filename>')
def get_json(filename):
    print("filename is ", filename, app.config['UPLOAD_FOLDER'])
    return send_from_directory(directory=app.config['UPLOAD_FOLDER'], filename=filename)


# getting layer 1 network
@app.route('/cluster/<int:wbid>')
def get_cluster_json(wbid):
    wbid = g.cxt.run_spider()
    return g.cxt.format_layer1_json(wbid)


# getting layer 2 network
@app.route('/double/<int:wbid>')
def get_layer2_json(wbid):
    return g.cxt.format_layer2_json(wbid)

