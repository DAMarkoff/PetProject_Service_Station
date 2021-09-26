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

def get_user_id(email):
    if conn:

    #get user_id from DB on email
        p_query = "SELECT user_id FROM users WHERE email = '{0}'".format(email)
        cursor.execute(p_query)
        conn.commit()
        usr_id_  = cursor.fetchone()
        cursor.close        

    return usr_id_[0]

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

def shelf_avail(size_name):
    if conn:

        p_query = "SELECT shelf_id FROM warehouse WHERE size_id = '{0}' AND available = 'True'".format(size_id_by_name(size_name))
        cursor.execute(p_query)
        conn.commit()
        avail  = cursor.fetchone()
        cursor.close

        if avail is not None:
            return True
    return False 

def shelf_id_by_size(size_name):
    if conn:

        p_query = "SELECT MIN(shelf_id) FROM warehouse WHERE size_id = '{0}' AND available = 'True'".format(size_id_by_name(size_name))
        cursor.execute(p_query)
        conn.commit()
        shelf_id_ = cursor.fetchone()
        cursor.close

        return shelf_id_[0]

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


        if usr_id_ is not None:
            return "The user with this email is already exists" #note that the email exists and redirect to /reg
        else:
            p_query = "INSERT INTO users (first_name, last_name, pass, phone, email) VALUES ({0}, {1}, {2}, {3}, {4})".format(f_name, l_name, passw, phone, email)
            cursor.execute(p_query)
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


@app.route("/add_users", methods=['POST']) #reg many users at once - to do
def add_users():
    pass


@app.route("/cl", methods=['POST']) #clear users DB
def cl():
    if request.method == 'POST':
        passw = request.form.get('pass')
    
    if passw == 'He_He_Boy!':
        if conn:
            p_query = "DELETE FROM users"
            cursor.execute(p_query)
            conn.commit()
            cursor.close

    return jsonify({'result':'OK or not OK?'})


@app.route("/all", methods=['GET']) #get a list of all users
def all():

    if conn:
        p_query = "SELECT user_id, first_name, last_name, phone, email, pass FROM users"
        cursor.execute(p_query)
        conn.commit()
        res  = cursor.fetchall()
        cursor.close
        
        if res is not None:
            result = []
            for i in range(len(res)):
                result.append({"ID": res[i][0],
                            "f_name": res[i][1],
                            "l_name": res[i][2],
                            "phone": res[i][3],
                            "email": res[i][4],
                            "passw": res[i][5]})
        else:
            return 'There are no users in the DB'
        
    return jsonify(result)


@app.route("/login", methods=['POST']) #login :) suddenly
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        passw = request.form.get('passw')

    if conn:

        #if user does not exist
        if not user_exist(email):
            return "The user does not exist. Please, register"

        #if user exists
        else:      
            p_query = "SELECT pass, user_id, first_name, last_name FROM users WHERE email = '{0}'".format(email)
            cursor.execute(p_query)
            conn.commit()
            res  = cursor.fetchone()
            cursor.close
            
            token = ""
            if passw == res[0]: #если пароль верен
                if r.exists(email) == 0: #если токена нет в redis db
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
                return 'you shall not pass :) password is invalid' #неверный пароль. перелогиньтесь, товарищ майор ;)


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

            #collecting the user's personal data from the users db
            p_query = "SELECT user_id, first_name, last_name, email, phone, pass FROM users WHERE email = '{0}'".format(email)
            cursor.execute(p_query)
            conn.commit()
            res  = cursor.fetchone()
            cursor.close

            result_users = ({"ID": res[0],
                             "f_name": res[1],
                             "l_name": res[2],
                             "email": res[3],
                             "phone": res[4],
                             "passw": res[5]})
            

            #collecting the user's storage orders data from the storage_orders db
            p_query = "SELECT * FROM storage_orders WHERE user_id = '{0}'".format(get_user_id(email))
            cursor.execute(p_query)
            conn.commit()
            res_  = cursor.fetchall()
            cursor.close

            if res_ is None:
                result_order = 'There are no orders for storage from the user'
            else:
                result_order = []
                for i in range(len(res_)):
                    result_order.append({"storage_order_id": res_[i][0],
                                        "start_date": res_[i][2],
                                        "stop_date": res_[i][3],
                                        "order cost": "not implemented by now, please, come back later",
                                        "shelf_id": res_[i][6]
                                        })
            
            
            #collecting data about the user's vehicles from the user_vehicle, vehicle and sizes db's
            p_query = """SELECT u_veh_id, vehicle_name, size_name FROM user_vehicle 
                         JOIN vehicle USING (vehicle_id)
                         JOIN sizes USING (size_id) 
                         WHERE user_id = '{0}'""".format(2)
            cursor.execute(p_query)
            conn.commit()
            res_  = cursor.fetchall()
            cursor.close

            empty_result = []
            if res_ == empty_result:
                result_vehicle = 'The user does not have a vehicle. BUT! If suddenly the user wants to get a vehicle, call 8-800-THIS-IS-NOT-A-SCAM right now!'
            else:
                result_vehicle = []
                for i in range(len(res_)):
                    result_vehicle.append({'vehicle_id': res_[i][0],
                                           'vehicle_type': res_[i][1],
                                           'tire size': res_[i][2]
                                          })

            return jsonify({'user info': result_users}, {'storage orders info:': result_order}, {"user's vehicle": result_vehicle})
        
        #if token does not exist in redis db    
        else:
            return "The token is invalid, please log in" #redirect to /login


@app.route("/new_storage_order", methods=['POST']) #create new storage order
def new_st_ord():
    if request.method == 'POST':
        token = request.form.get('token')
        email = request.form.get('email')
        start_date = request.form.get('start_date')
        stop_date = request.form.get('stop_date')
        size_name = request.form.get('size_name')

    #if user exists
    if not user_exist(email):
            return "The user does not exist. Please, register"
    else:    
        #if token exists in redis db
        if token_exist(email, token):

            #is there the necessary free storage space
            if shelf_avail(size_name):
                shelf_id = shelf_id_by_size(size_name)
                
                if conn:

                    #create storage order
                    p_query = """INSERT INTO storage_orders (user_id, start_date, stop_date, size_id, shelf_id) 
                                VALUES('{0}', '{1}', '{2}', '{3}', '{4}');""".format(get_user_id(email), start_date, stop_date, size_id_by_name(size_name), shelf_id)
                    cursor.execute(p_query)
                    conn.commit()
                    cursor.close

                    #set shelf_id as not available
                    p_query = """UPDATE warehouse SET available = False WHERE shelf_id = '{0}';""".format(shelf_id)
                    cursor.execute(p_query)
                    conn.commit()
                    cursor.close

                else: 
                    return 'Sorry, no connection with the DB'

            else:
                return "Sorry, we do not have the storage you need"
        else:
            return "The token is invalid, please log in" #redirect to /login

    return jsonify({'shelf_id': shelf_id})


@app.route("/change_storage_order", methods=['PATCH']) #change info in the storage order
def change_storage_order():
    if request.method == 'PATCH':
        st_ord_id = request.form.get('st_ord_id')
        token = request.form.get('token')
        email = request.form.get('email')
        start_date = request.form.get('start_date')
        stop_date = request.form.get('stop_date')
        st_ord_cost = request.form.get('cost')
        size_id = request.form.get('size_id')
    else:
        return 'Ouch! Not allowed method!'

    #if user exists
    if not user_exist(email):
        return "The user does not exist. Please, register"
    else:    
        #if token exists in redis db
        if token_exist(email, token):

            p_query = """SELECT start_date, stop_date, size_id, st_ord_cost, shelf_id FROM storage_orders WHERE st_ord_id = '{0}';""".format(st_ord_id)
            cursor.execute(p_query)
            conn.commit()
            res_ = cursor.fetchone()
            cursor.close

            start_date_db, stop_date_db, size_id_db, st_ord_cost_db, shelf_id_db, shelf_id = res_[0], res_[1], res_[2], res_[3], res_[4], 0

            if start_date is None:
                start_date = start_date_db
            if stop_date is None:
                stop_date = stop_date_db
            if st_ord_cost is None:
                st_ord_cost = st_ord_cost_db
            if size_id is None:
                size_id = size_id_db
            else:
                if conn:

                    p_query = """SELECT shelf_id FROM warehouse WHERE available = 'True' AND size_id = '{0}';""".format(size_id)
                    cursor.execute(p_query)
                    conn.commit()
                    shelf_avail = cursor.fetchone()
                    cursor.close

                    if shelf_avail is not None:
                        shelf_id = shelf_avail[0]
                    else:
                        return 'Sorry, we do not have the storage you need'
                    
                else: 
                    return 'Sorry, no connection with the DB'

            if shelf_id == 0:
                shelf_id = shelf_id_db

            #update data in the DB
            if conn:

                p_query = """UPDATE storage_orders SET start_date = '{0}', stop_date = '{1}', size_id = '{2}', st_ord_cost = '{3}', shelf_id = '{4}' 
                             WHERE st_ord_id = '{5}';""".format(start_date, stop_date, size_id, st_ord_cost, shelf_id, st_ord_id)
                cursor.execute(p_query)
                conn.commit()
                cursor.close
            
            else: 
                return 'Sorry, no connection with the DB'

            #get new date from the DB
            if conn:

                p_query = """SELECT start_date, stop_date, size_id, st_ord_cost, shelf_id FROM srotage_orders WHERE st_ord_id = '{0}';""".format(st_ord_id)
                cursor.execute(p_query)
                conn.commit()
                res_ = cursor.fetchone()
                cursor.close
            
            else: 
                return 'Sorry, no connection with the DB'

            result = ({'storage_order': st_ord_id, 'start_date': res_[0], 'stop_date': res_[1], 'size_id': res_[2], 'storage_order_cost': res_[3], 'shelf_id': res_[4]})
        
        
        else:
            return "The token is invalid, please log in" #redirect to /login    

    # result = ({'st_ord_id': st_ord_id, 'email': email})
    # result = ({'st_ord_id': st_ord_id, 'email': email, {start_date}: start_date, 'stop_date': stop_date, 'cost': cost, 'shelf_id': shelf_id, 'size_id': size_id})
    # print(st_ord_id, email, start_date, stop_date, cost, shelf_id, size_id)
    return jsonify(result)

if __name__ == '__main__':
    app.run()