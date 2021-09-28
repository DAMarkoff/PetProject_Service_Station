from os import curdir
from flask import Flask, request, jsonify
from jinja2 import Template
import psycopg2
import uuid
import re
import redis
import datetime

app = Flask(__name__)
r = redis.StrictRedis(host='localhost', port=6379, db=0, charset="utf-8", decode_responses=True)
conn = psycopg2.connect(dbname='user_20_db', user='user_20', password='123', host='159.69.151.133', port='5056')
cursor = conn.cursor()

def user_exist(email):
    if conn:

    #get user_id from DB on email
        sql_query = "SELECT user_id FROM users WHERE email = '{0}'".format(email)
        cursor.execute(sql_query)
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
        sql_query = "SELECT user_id FROM users WHERE email = '{0}'".format(email)
        cursor.execute(sql_query)
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

        sql_query = "SELECT size_id FROM sizes WHERE size_name = '{0}'".format(size_name)
        cursor.execute(sql_query)
        conn.commit()
        size_id_  = cursor.fetchone()
        cursor.close

        if size_id_ is None:
            return 'Unknown'
        return size_id_[0]   

def vehicle_id_by_name(vehicle_name):
    if conn:

        sql_query = "SELECT vehicle_id FROM vehicle WHERE vehicle_name = '{0}'".format(vehicle_name)
        cursor.execute(sql_query)
        conn.commit()
        vehicle_id_  = cursor.fetchone()
        cursor.close

        if vehicle_id_ is None:
            return 'Unknown'
        return vehicle_id_[0]             

def shelf_avail(size_name):
    if conn:

        sql_query = "SELECT shelf_id FROM warehouse WHERE size_id = '{0}' AND available = 'True'".format(size_id_by_name(size_name))
        cursor.execute(sql_query)
        conn.commit()
        avail  = cursor.fetchone()
        cursor.close

        if avail is not None:
            return True
    return False 

def shelf_id_by_size(size_name):
    if conn:

        sql_query = "SELECT MIN(shelf_id) FROM warehouse WHERE size_id = '{0}' AND available = 'True'".format(size_id_by_name(size_name))
        cursor.execute(sql_query)
        conn.commit()
        shelf_id_ = cursor.fetchone()
        cursor.close

        return shelf_id_[0]

def validate_password(passw):
    SpecialSym=['$','@','#', '!', '%']
    return_val = {'result': True, 'text': ''}
    if len(passw) < 8:
        return_val['text'] = 'The password must be at least 8 characters long'
        return_val['result'] = False
    if len(passw) > 32:
        return_val['text'] = 'the password length should not exceed 32 chars'
        return_val['result'] = False
    if not any(char.isdigit() for char in passw):
        return_val['text'] = 'The password must contain at least one digit'
        return_val['result'] = False
    if not any(char.isupper() for char in passw):
        return_val['text'] = 'The password must contain at least one uppercase letter'
        return_val['result'] = False
    if not any(char.islower() for char in passw):
        return_val['text'] = 'The password must contain at least one lowercase letter'
        return_val['result'] = False
    if not any(char in SpecialSym for char in passw):
        return_val['text'] = 'The password must contain at least one of the symbols $@#!%'
        return_val['result'] = False
    return return_val

def validate_email(email):
    return_val = {'result': True, 'text': ''}
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return_val['result'] = False
        return_val['text'] = 'Please provide a valid email address'
    return return_val

def user_active(email):
    if conn:

        sql_query = """SELECT active FROM users WHERE email = '{0}'""".format(email)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        cursor.close

        if res_[0]:
            return True
        return False

@app.route("/reg", methods=['POST']) #reg new user
def reg():
    if request.method == 'POST':
        f_name = request.form.get('f_name')
        l_name = request.form.get('l_name')
        passw = request.form.get('passw')
        phone = request.form.get('phone')
        email = request.form.get('email')

    if f_name is None or l_name is None or passw is None or phone is None or email is None:
        return 'The f_name, l_name, passw, phone and email data are required'

    #making sure that the password is strong enough 8-32 chars, min one digit, min one upper and min one lower letter, min one special char
    check_passw = validate_password(passw)
    if not check_passw['result']:
        return check_passw['text']

    #the email must contain @ and .
    check_email = validate_email(email)
    if not check_email['result']:
        return check_email['text']

    if user_exist(email):
            return "the user with this email already exists"
    else:   

        active = True
        if not conn:
            return 'Sorry, no connection with the DB'
        else: 
            sql_query = """INSERT INTO users (first_name, last_name, pass, phone, email,active) 
                            VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', {5})""".format(f_name, l_name, passw, phone, email, active)
            cursor.execute(sql_query)
            conn.commit()
            cursor.close

            sql_query = "SELECT user_id, first_name, last_name, email, phone, pass, active FROM users WHERE email = '{0}'".format(email)
            cursor.execute(sql_query)
            res  = cursor.fetchone()
            conn.commit()
            cursor.close

            result = ({"ID": res[0],
                    "f_name": res[1],
                    "l_name": res[2],
                    "email": res[3],
                    "phone": res[4],
                    "passw": res[5],
                    "active": res[6]})        

    return jsonify(result)


@app.route("/cl", methods=['POST']) #clear users DB
def cl():
    if request.method == 'POST':
        passw = request.form.get('pass')
    
    if passw == 'He_He_Boy!':
        if conn:
            sql_query = "DELETE FROM users"
            cursor.execute(sql_query)
            conn.commit()
            cursor.close

    return jsonify({'result':'OK or not OK?'})


@app.route("/all", methods=['GET']) #get a list of all users
def all():

    if conn:
        sql_query = "SELECT user_id, first_name, last_name, phone, email, pass FROM users"
        cursor.execute(sql_query)
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

    if passw is None or email is None:
        return 'The pass and email data are required'         

    if conn:

        #if user does not exist
        if not user_exist(email):
            return "The user does not exist. Please, register"

        #if user exists
        else: 

            sql_query = "SELECT pass, user_id, first_name, last_name FROM users WHERE email = '{0}'".format(email)
            cursor.execute(sql_query)
            conn.commit()
            res  = cursor.fetchone()
            cursor.close
            
            if not user_active(email):
                return 'User is deactivated'
            else:
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
    
    if token is None or email is None:
        return 'The token and email data are required'    

    if not user_exist(email):
            return "user does not exist"
    else:    
        #if token exists in redis db
        if not token_exist(email, token):
            return "The token is invalid, please log in" #redirect to /login
        else:

            if conn:

                #collecting the user's personal data from the users db
                sql_query = "SELECT user_id, first_name, last_name, email, phone, pass FROM users WHERE email = '{0}'".format(email)
                cursor.execute(sql_query)
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
                sql_query = "SELECT * FROM storage_orders WHERE user_id = '{0}'".format(get_user_id(email))
                cursor.execute(sql_query)
                conn.commit()
                res_  = cursor.fetchall()
                cursor.close

                if res_ is None:
                    result_order = 'There are no orders for storage from the user'
                else:
                    result_order = []
                    for i in range(len(res_)): #does the user need the size_id or size_name data?
                        result_order.append({"storage_order_id": res_[i][0],
                                            "start_date": res_[i][2],
                                            "stop_date": res_[i][3],
                                            "order cost": res_[i][5],
                                            "shelf_id": res_[i][6]
                                            })
                
                
                #collecting data about the user's vehicles from the user_vehicle, vehicle and sizes db's
                sql_query = """SELECT u_veh_id, vehicle_name, size_name FROM user_vehicle 
                            JOIN vehicle USING (vehicle_id)
                            JOIN sizes USING (size_id) 
                            WHERE user_id = '{0}'""".format(get_user_id(email))
                cursor.execute(sql_query)
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

            else: 
                return 'Sorry, no connection with the DB'
            

@app.route("/new_storage_order", methods=['POST']) #create new storage order
def new_st_ord():
    if request.method == 'POST':
        token = request.form.get('token')
        email = request.form.get('email')
        start_date = request.form.get('start_date')
        stop_date = request.form.get('stop_date')
        size_name = request.form.get('size_name')

    if token is None or email is None or start_date is None or stop_date is None or size_name is None:
        return 'The token, email, start_date, stop_date and size_name data are required'
  
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
                    sql_query = """INSERT INTO storage_orders (user_id, start_date, stop_date, size_id, shelf_id, st_ord_cost) 
                                VALUES('{0}', '{1}', '{2}', '{3}', '{4}', '{5}');""".format(get_user_id(email), start_date, stop_date, size_id_by_name(size_name), shelf_id, 1000)
                    cursor.execute(sql_query)
                    conn.commit()
                    cursor.close

                    #set shelf_id as not available
                    sql_query = """UPDATE warehouse SET available = False WHERE shelf_id = '{0}';""".format(shelf_id)
                    cursor.execute(sql_query)
                    conn.commit()
                    cursor.close

                else: 
                    return 'Sorry, no connection with the DB'

            else:
                return "Sorry, we do not have the storage you need"
        else:
            return "The token is invalid, please log in" #redirect to /login

    return jsonify({'shelf_id': shelf_id})


@app.route("/change_storage_order", methods=['PATCH']) #change the data in the storage order
def change_storage_order():
    if request.method == 'PATCH':
        st_ord_id = request.form.get('st_ord_id')
        token = request.form.get('token')
        email = request.form.get('email')
        start_date = request.form.get('start_date')
        stop_date = request.form.get('stop_date')
        st_ord_cost = request.form.get('st_ord_cost')
        size_id = request.form.get('size_id')

    if token is None or email is None or st_ord_id is None:
        return 'The token, email, st_ord_id data are required'

    #if user exists
    if not user_exist(email):
        return "The user does not exist. Please, register"
    else:    
        #if token exists in redis db
        if not token_exist(email, token):
            return "The token is invalid, please log in" #redirect to /login
        else:

            if not conn:
                return 'Could not connect to the DB'
            else:
                #get the initial data of the storage order
                sql_query = """SELECT start_date, stop_date, size_id, st_ord_cost, shelf_id, user_id FROM storage_orders WHERE st_ord_id = '{0}';""".format(st_ord_id)
                cursor.execute(sql_query)
                conn.commit()
                res_ = cursor.fetchone()
                cursor.close

                start_date_db, stop_date_db, size_id_db, st_ord_cost_db, shelf_id_db, user_id_db, shelf_id = res_[0], res_[1], res_[2], res_[3], res_[4], res_[5], 0 

                #verify, that the storage order is created by user
                if get_user_id(email) != user_id_db:
                    return 'Ouch! This is not your storage order!'
                else:
                    
                    #what data should be changed
                    #check dates
                    if start_date is not None and stop_date is not None:
                        if start_date > stop_date:
                            return 'The start date can not be greater than the stop date'
                        if stop_date < start_date:
                            return 'The stop date can not be less than the start date'

                    if start_date is not None and stop_date is None:
                        if datetime.datetime.strptime(start_date, '%Y-%m-%d') > datetime.datetime.strptime(str(stop_date_db), '%Y-%m-%d'):
                            return 'The start date can not be greater than the stop date'

                    if start_date is None and stop_date is not None:        
                        if datetime.datetime.strptime(stop_date, '%Y-%m-%d') < datetime.datetime.strptime(str(start_date_db), '%Y-%m-%d'):
                            return 'The stop date can not be less than the start date'                        

                    if start_date is None:
                        start_date = start_date_db
                    if stop_date is None:
                        stop_date = stop_date_db
                    if st_ord_cost is None:
                        st_ord_cost = st_ord_cost_db
                    if size_id is None:
                        size_id = size_id_db
                    else:
                        #if the tire size data needs to be changed
                        if int(size_id) != size_id_db:
                            sql_query = """SELECT MIN(shelf_id) FROM warehouse WHERE available = 'True' AND size_id = '{0}';""".format(size_id)
                            cursor.execute(sql_query)
                            conn.commit()
                            shelf_avail = cursor.fetchone()
                            cursor.close

                            #if there is available storage
                            if shelf_avail is not None:
                                shelf_id = shelf_avail[0]

                                #update changed storage places
                                sql_query = """UPDATE warehouse SET available = 'True' WHERE shelf_id = '{0}';""".format(shelf_id_db)
                                cursor.execute(sql_query)
                                conn.commit()
                                cursor.close

                                sql_query = """UPDATE warehouse SET available = 'False' WHERE shelf_id = '{0}';""".format(shelf_id)
                                cursor.execute(sql_query)
                                conn.commit()
                                cursor.close

                            else:
                                return 'Sorry, we do not have the storage you need'

                    if shelf_id == 0:   
                        shelf_id = shelf_id_db

                    #update data in the DB

                    sql_query = """UPDATE storage_orders SET start_date = '{0}', stop_date = '{1}', size_id = '{2}', st_ord_cost = '{3}', shelf_id = '{4}' 
                                    WHERE st_ord_id = '{5}';""".format(start_date, stop_date, size_id, st_ord_cost, shelf_id, st_ord_id)
                    cursor.execute(sql_query)
                    conn.commit()
                    cursor.close

                    result = ({'storage_order': st_ord_id, 'start_date': start_date, 'stop_date': stop_date, 'size_id_new': size_id, 'size_id_old': size_id_db,
                               'storage_order_cost': st_ord_cost, 'shelf_id_new': shelf_id, 'shelf_id_old': shelf_id_db})

    return jsonify(result)


@app.route("/change_user_info", methods=['PATCH']) #change the data of the logged user
def change_user_info():
    if request.method == 'PATCH':
        token = request.form.get('token')
        email = request.form.get('email')
        f_name = request.form.get('f_name')
        l_name = request.form.get('l_name')
        phone = request.form.get('phone')
        new_email = request.form.get('new_email')
        passw = request.form.get('passw')

    if token is None or email is None:
        return 'The token, email are required'
    
    #if user exists
    if not user_exist(email):
        return "The user does not exist. Please, register"
    else:    

        #if token exists in redis db
        if not token_exist(email, token):
            return "The token is invalid, please log in" #redirect to /login
        else:        

            if not conn:
                return 'Could not connect to the DB'
            else:
                
                #get the initial data of the storage order
                sql_query = """SELECT user_id, first_name, last_name, phone, pass FROM users WHERE email = '{0}';""".format(email)
                cursor.execute(sql_query)
                conn.commit()
                res_ = cursor.fetchone()
                cursor.close 
                
                user_id_db, f_name_db, l_name_db, phone_db, passw_db = res_[0], res_[1], res_[2], res_[3], res_[4]

                flag_relogin = False
                #what data should be changed
                if f_name is None:
                    f_name = f_name_db
                if l_name is None:
                    l_name = l_name_db
                if phone is None:
                    phone = phone_db
                if passw is None:
                    passw = passw_db
                else:
                    check_passw = validate_password(passw)
                    if not check_passw['result']:
                        return check_passw['text']
                    flag_relogin = True
                if new_email is None:
                    new_email = email
                else:
                    check_email = validate_email(email)
                    if not check_email['result']:
                        return check_email['text']
                    flag_relogin = True

                #if the pass and/or email have been changed - the user must log in again
                if flag_relogin:
                    r.delete(email)

                #update data in the DB
                sql_query = """UPDATE users SET first_name = '{0}', last_name = '{1}', email = '{2}', phone = '{3}', pass = '{4}' 
                                WHERE user_id = '{5}';""".format(f_name, l_name, new_email, phone, passw, user_id_db)
                cursor.execute(sql_query)
                conn.commit()
                cursor.close

                result = ({'user_id': user_id_db, 'f_name_new': f_name, 'f_name_old': f_name_db, 'l_name_new': l_name, 
                           'l_name_old': l_name_db, 'email_new': new_email, 'email_old': email, 'phone_new': phone,
                           'phone_old': phone_db, 'passw_new': passw, 'passw_old': passw_db})

    return jsonify(result) 


@app.route("/new_user_vehicle", methods=['POST']) #add new user vehicle :)
def new_user_vehicle():
    if request.method == 'POST':
        token = request.form.get('token')
        email = request.form.get('email')
        vehicle_name = request.form.get('vehicle_name')
        size_name = request.form.get('size_name')

    if token is None or email is None or vehicle_name is None or size_name is None:
        return 'The token, email, vehicle_name and size_name data are required'

    #get needed data
    user_id = get_user_id(email)
    size_id = size_id_by_name(size_name)
    vehicle_id = vehicle_id_by_name(vehicle_name)

    if size_id == 'Unknown':
        return 'Attention!!! Unknown tire size, add the tire size data to the sizes DB'

    if vehicle_id == 'Unknown':
        return 'Attention!!! Unknown type of the vehicle, add the vehicle type data to the sizes DB'

    
    #if user exists
    if not user_exist(email):
        return 'The user does not exist. Please, register'
    else:
        #if token exists in redis db
        if not token_exist(email, token):
            return 'The token is invalid, please log in' #redirect to /login    
        else:

            if not conn:
                return 'Could not connect to the DB'
            else:
                sql_query = """INSERT INTO user_vehicle (user_id, vehicle_id, size_id) VALUES ('{0}', '{1}', '{2}');""".format(user_id, vehicle_id, size_id)
                cursor.execute(sql_query)
                conn.commit()
                cursor.close

                sql_query = """SELECT MAX(u_veh_id) FROM user_vehicle WHERE user_id = '{0}'""".format(user_id)
                cursor.execute(sql_query)
                conn.commit()
                res_ = cursor.fetchone()
                cursor.close

    return {'new_vehicle_id': res_[0], 'vehicle_name': vehicle_name, 'tire_size': size_name}


@app.route("/delete_user", methods=['DELETE']) #How dare you?
def delete_user():
    if request.method == 'DELETE':
        email = request.form.get('email')
        token = request.form.get('token')
        sure = request.form.get('ARE_YOU_SURE?')

        if not user_exist(email):
            return 'The user does not exist. Please, register'
        else:
            if not token_exist(email):
                return 'The token is invalid, please log in' #redirect to /login
            else:

                if sure: 

                    if not conn:
                        return 'Could not connect to the DB'
                    else:

                        sql_query = """SELECT first_name, last_name FROM users WHERE email = '{0}'""".format(email)
                        cursor.execute(sql_query)
                        conn.commit()
                        res_ = cursor.fetchone()
                        cursor.close
                        
                        sql_query = """DELETE FROM users WHERE email = '{0}'""".format(email)
                        cursor.execute(sql_query)
                        conn.commit()
                        cursor.close

                        text = 'R.I.P {{ name }}, i will miss you :('
                        template = Template(text)

                        return template.render(name = res_[0] + ' ' + res_[1])






if __name__ == '__main__':
    app.run()