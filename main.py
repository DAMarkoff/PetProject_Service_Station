from flask import Flask, request, jsonify
import psycopg2
#from werkzeug.wrappers import request
app = Flask(__name__)

#conn = psycopg2.connect(dbname='test', user='postgres', password='qwe', host='localhost', port='5432')
#cursor = conn.cursor()

@app.route("/")
def hello():
    return "Hello World!"

@app.route("/home", methods=['POST'])
def home():
    if request.method == 'POST':
        name = request.form.get('name')
        age = request.form.get('age')

    resp = {'Name': name + ' Pop',
            'Age': int(age) * 3}

    return jsonify(resp)

@app.route("/db", methods=['POST'])
def db():
    if request.method == 'POST':
        id = request.form.get(int('id'))

    result = {'ID': id}

    if conn:

        print('CONN =======')

        base_data = (id)

        p_query = "INSET INTO first (id) VALUES (%s)"
        cursor.execute(p_query, base_data)
        conn.commit()
        cursor.close

    return jsonify(result)

if __name__ == '__main__':
    app.run()
