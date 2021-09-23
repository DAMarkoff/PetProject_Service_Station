from os import curdir
from flask import Flask, request, jsonify
from jinja2 import Template
import psycopg2
import uuid
import json
import redis

app = Flask(__name__)
r = redis.StrictRedis(host='localhost', port=6379, db=0, charset="utf-8", decode_responses=True)


conn = psycopg2.connect(dbname='user_20_db', user='user_20', password='123', host='159.69.151.133', port='5056')
cursor = conn.cursor()

def user_exist(email):
    if conn:

    #get user_id from DB on email
        p_query = "SELECT user_id FROM users WHERE email = '{0}'".format(email)
        cursor.execute(p_query)
        conn.commit()
        usr_id_  = cursor.fetchone()
        cursor.close        

    #if user_id does not exist
        if usr_id_ is None:
            return False
    return True

def token_exist(email, token):
    if token == r.get(email):
        return True
    return False

def size_id_by_name(size_name):
    if conn:

        p_query = "SELECT size_id FROM sizes WHERE size_name = '{0}'".format(size_name)
        cursor.execute(p_query)
        conn.commit()
        size_id_  = cursor.fetchone()
        cursor.close

        return size_id_[0]        


def shelf_exist(size_name):
    if conn:

        p_query = "SELECT available FROM warehouse WHERE size_id = '{0}'".format(size_id_by_name(size_name))
        cursor.execute(p_query)
        conn.commit()
        avail  = cursor.fetchone()
        cursor.close

        if avail[0] == True:
            return True
        return False    

@app.route("/home", methods=['POST']) #for fun :)
def home():
    if request.method == 'POST':
        name = request.form.get('name')
        age = request.form.get('age')

    resp = {'Name': name + ' Pop',
            'Age': int(age) * 3}

    return jsonify(resp)

@app.route("/reg", methods=['POST']) #reg new user
def reg():
    if request.method == 'POST':
        f_name = request.form.get('f_name')
        l_name = request.form.get('l_name')
        passw = request.form.get('passw')
        phone = request.form.get('phone')
        email = request.form.get('email')

    if conn:

        print('CONN =======')

        p_query = "SELECT user_id FROM users WHERE email = '{0}'".format(email)
        cursor.execute(p_query)
        conn.commit()
        usr_id_  = cursor.fetchone()
        cursor.close        

        #print(usr_id_[0])
        if usr_id_ is not None:
            return "email exists" #note that the email exists and redirect to /reg
        else:
            base_data = (f_name, l_name, passw, phone, email)
            p_query = "INSERT INTO users (first_name, last_name, pass, phone, email) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(p_query, base_data)
            conn.commit()
            cursor.close

            p_query = "SELECT user_id, first_name, last_name, email, phone, pass FROM users WHERE email = '{0}'".format(email)
            cursor.execute(p_query)
            res  = cursor.fetchone()
            conn.commit()
            cursor.close

            result = ({"ID": res[0],
                    "f_name": res[1],
                    "l_name": res[2],
                    "email": res[3],
                    "phone": res[4],
                    "passw": res[5]})        

        return jsonify(result)


@app.route("/add_users", methods=['POST']) #reg many users - to do
def add_users():
    pass


@app.route("/cl", methods=['GET']) #clear users DB
def cl():

    if conn:
        p_query = "DELETE FROM users"
        cursor.execute(p_query)
        conn.commit()
        cursor.close

    result = {'result':'OK'}
    return jsonify(result)

@app.route("/all", methods=['GET']) #get a list of all users
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


@app.route("/login", methods=['POST']) #login :)
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        passw = request.form.get('passw')

    if conn:

        print('CONN =======')

        #get user_id from DB on email
        p_query = "SELECT user_id FROM users WHERE email = '{0}'".format(email)
        cursor.execute(p_query)
        conn.commit()
        usr_id_  = cursor.fetchone()
        cursor.close  

        #if user does not exist
        if usr_id_ is None:
            return "user does not exist"

        #if user exists in redis db
        else:      
            p_query = "SELECT pass, user_id, first_name, last_name FROM users WHERE email = '{0}'".format(email)
            cursor.execute(p_query)
            conn.commit()
            res  = cursor.fetchone()
            cursor.close
            
            token = ""
            if passw == res[0]: #если пароль верен
                if r.exists(email) == 0: #если токен уже выдан
                    token = str(uuid.uuid4()) #генерация токена
                    r.set(email, token, ex=600) #запись токена в redis bd, срок - 600 сек.
                else:
                    token = r.get(email) #возврат токена
                    r.set(email, token, ex=600) #пролонгация токена, срок - 600 сек.
                
                #генерация Hello message (For fun :)
                text = 'Hello {{ name }}!'
                template = Template(text)
            
                return jsonify({"result":template.render(name=res[2]+" "+res[3]), "token": token, "email": email, "user_id": res[1]})                           
            else:
                return 'you shall not pass :) password is not valid' #неверный пароль, перелогинтесь

@app.route("/user_info", methods=['POST']) #get info about the logged user
def user_info():
    if request.method == 'POST':
        token = request.form.get('token')
        email = request.form.get('email')
    

    if not user_exist(email):
            return "user does not exist"
    else:    
        #if token exists in redis db
        if token_exist(email, token):
            p_query = "SELECT user_id, first_name, last_name, email, phone, pass FROM users WHERE email = '{0}'".format(email)
            cursor.execute(p_query)
            conn.commit()
            res  = cursor.fetchone()
            cursor.close

            result = ({"ID": res[0],
                    "f_name": res[1],
                    "l_name": res[2],
                    "email": res[3],
                    "phone": res[4],
                    "passw": res[5]})
            
            
            return jsonify(result)
        
        #if token does not exist in redis db    
        else:
            return "token does not valid, please login" #redirect to /login


@app.route("/new_storage_order", methods=['POST'])
def new_st_ord():
    if request.method == 'POST':
        token = request.form.get('token')
        email = request.form.get('email')
        start_date = request.form.get('start_date')
        stop_date = request.form.get('stop_date')
        size_name = request.form.get('size_name')

    if not user_exist(email):
            return "user does not exist"
    else:    
        #if token exists in redis db
        if token_exist(email, token):
            
            # if conn:
                
            #     p_query = "SELECT availabe FROM warehouse WHERE size_id = '{0}'".format(size_id_by_name(size_name))
            #     cursor.execute(p_query)
            #     conn.commit()
            #     avail  = cursor.fetchone()
            #     cursor.close                
            return size_id_by_name(size_name)


            
        else:
            return "token does not valid, please login" #redirect to /login

if __name__ == '__main__':
    app.run()