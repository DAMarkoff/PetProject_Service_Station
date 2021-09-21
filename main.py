from os import curdir
from flask import Flask, request, jsonify
import psycopg2

app = Flask(__name__)

conn = psycopg2.connect(dbname='user_20_db', user='user_20', password='123', host='159.69.151.133', port='5056')
cursor = conn.cursor()

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
        f_name = request.form.get('f_name')
        l_name = request.form.get('l_name')
        passw = request.form.get('passw')
        phone = request.form.get('phone')
        email = request.form.get('email')

    if conn:

        print('CONN =======')

        base_data = (f_name, l_name, passw, phone, email)
        p_query = "INSERT INTO users (first_name, last_name, password, phone, email) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(p_query, base_data)
        conn.commit()
        cursor.close

        #base_data = (f_name)
        #p_query = "SELECT id FROM users WHERE first_name = %s"
        #cursor.execute(p_query, base_data)
        #id_d = cursor.fetchone()
        #result = {'ID': id_d}
    return jsonify({"result":"OK"})

@app.route("/cl", methods=['GET'])
def cl():

    if conn:
        p_query = "DELETE FROM users"
        cursor.execute(p_query)
        conn.commit()
        cursor.close

    result = {'result':'OK'}
    return jsonify(result)

@app.route("/all", methods=['GET'])
def all():

    if conn:
        p_query = "SELECT * FROM users"
        cursor.execute(p_query)
        conn.commit()
        result = cursor.fetchone()
        cursor.close
    return result

if __name__ == '__main__':
    app.run()
