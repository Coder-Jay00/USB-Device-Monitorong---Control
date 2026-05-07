import os
import markdown
from flask import Flask, render_template

app = Flask(__name__)

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README_PATH = os.path.join(BASE_DIR, 'README.md')

@app.route('/')
def index():
    content = ""
    if os.path.exists(README_PATH):
        with open(README_PATH, 'r', encoding='utf-8') as f:
            content = markdown.markdown(f.read(), extensions=['fenced_code', 'tables'])
    
    return render_template('index.html', content=content, title="USB Device Monitoring - Project Report")

if __name__ == '__main__':
    app.run(debug=True, port=5003)
