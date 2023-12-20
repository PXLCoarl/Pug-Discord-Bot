from dotenv import load_dotenv
import os
from flask import Flask, render_template, send_from_directory, request
from waitress import serve
import glob

load_dotenv()
app = Flask(__name__)

@app.route('/')
def index():
    files = glob.glob("api/*.json")
    return render_template('index.html', files=files)

@app.route('/pug/demos', methods=['POST'])
def receive_demos():
    if 'file' not in request.files:
        return 'No file', 400
    file = request.files['file']
    file.save('Demos/' + file.filename)
    
    return 'Demo received', 200


@app.route('/api/v1/<path:filename>', methods=['GET'])
def serve_api(filename):
    api_dir = os.path.join(os.getcwd(), 'api')
    file_path = os.path.join(api_dir, filename)

    if os.path.isfile(file_path):
        return send_from_directory(api_dir, filename)
    else:
        return "File not found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=31777)
