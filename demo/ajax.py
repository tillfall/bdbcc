from flask import Flask, render_template
from datetime import datetime

app = Flask(__name__)

@app.route('/', methods=['GET','POST'])
def index():
    return render_template('ajax.html')
    
@app.route('/ajax', methods=['GET','POST'])
def req():
    return str(datetime.now())
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6789)