from os import curdir
from flask import Flask, request, jsonify
import psycopg2
import uuid
import json
import redis

app = Flask(__name__)
r = redis.StrictRedis(host='localhost', port=6379, db=0, charset="utf-8", decode_responses=True)


conn = psycopg2.connect(dbname='user_20_db', user='user_20', password='123', host='159.69.151.133', port='5056')
cursor = conn.cursor()

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

    return jsonify({"f_name": f_name,
                    "l_name": l_name,
                    "pass": passw,
                    "phone": phone,
                    "email": email})


@app.route("/add_users", methods=['POST'])
def add_users():
    if request.method == 'POST':
        params = request.form.get('file')
    data = json.loads(params)

#    print(params)
#    print(data)
#    print(data[])
    return jsonify({"result": "OK"})
#    if conn:
#
#        print('CONN =======')
#
#        base_data = (f_name, l_name, passw, phone, email)
#        p_query = "INSERT INTO users (first_name, last_name, password, phone, email) VALUES (%s, %s, %s, %s, %s)"
#        cursor.execute(p_query, base_data)
#        conn.commit()
#        cursor.close
#
#    return jsonify({"f_name": f_name,
#                    "l_name": l_name,
#                    "pass": passw,
#                    "phone": phone,
#                    "email": email})


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
        res  = cursor.fetchall()
        result = []
        for i in range(len(res)):
            result.append({"ID": res[i][0],
                        "f_name": res[i][1],
                        "l_name": res[i][2],
                        "phone": res[i][3],
                        "email": res[i][4],
                        "passw": res[i][5]})
        
        cursor.close
    return jsonify(result)


@app.route("/login", methods=['POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        passw = request.form.get('passw')

    if conn:

        print('CONN =======')

        p_query = "SELECT pass, user_id FROM users WHERE email = '{0}'".format(email)
        cursor.execute(p_query)
        conn.commit()
        res  = cursor.fetchone()
        cursor.close
        
        token = ""
        if passw == res[0]:
            print(r.exists(res[1]))
            if r.exists(res[1]) == 0:
                token = str(uuid.uuid4()) #установить срок токена
                r.set(res[1], token)
            else:
                token = r.get(res[1]) #пролонгация токена    
        else:
            print('pass not')

    return jsonify({"token": token, "email": email, "user_id": res[1]})


@app.route("/user_info", methods=['POST'])
def user_info():
    if request.method == 'POST':
        token = request.form.get('token')
        email = request.form.get('email')
    

    if conn:

        print('CONN =======')

        
        p_query = "SELECT user_id, first_name, last_name, email, phone, pass FROM users WHERE email = '{0}'".format(email)
        cursor.execute(p_query)
        conn.commit()
        res  = cursor.fetchone()
        cursor.close
        
        if token == r.get(res[0]):
            print(res)
        else:
            print('pass not')

    return jsonify(res)

if __name__ == '__main__':
    app.run()
