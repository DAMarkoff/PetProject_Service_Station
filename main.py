import random
from flask import Flask, request, jsonify, abort
from jinja2 import Template
import psycopg2
import uuid
import re
import redis
import datetime
from flask_swagger_ui import get_swaggerui_blueprint
from defs import *
import bcrypt
import  git
from git import Repo

app = Flask(__name__)

SWAGGER_URL = '/swagger'
API_URL = '/static/swagger.yaml'
swaggerui_blueprint = get_swaggerui_blueprint(SWAGGER_URL, API_URL, config={'app_name':"Service_Station"})

app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

repository = Repo('~/server/Course')
#log

r = redis.StrictRedis(host='localhost', port=6379, db=0, charset="utf-8", decode_responses=True)
conn = psycopg2.connect(dbname='user_20_db', user='user_20', password='123', host='159.69.151.133', port='5056')
cursor = conn.cursor()


@app.errorhandler(400)
def bad_request(e):
    return jsonify(error=str(e)), 400


@app.errorhandler(405)
def wrong_method(e):
    return jsonify(error=str(e)), 405


@app.errorhandler(403)
def forbidden(e):
    return jsonify(error=str(e)), 403


@app.errorhandler(401)
def unauthorized(e):
    return jsonify(error=str(e)), 401


@app.errorhandler(503)
def unauthorized(e):
    return jsonify(error=str(e)), 503


@app.route("/users", methods=['GET', 'POST', 'PUT', 'DELETE'])  # request a short data/register/change data/delete
def users():
    # request a short data about all/one of the users
    if request.method == 'GET':
        user_id = request.args.get('user_id')
        if not conn:
            abort(503, description='There is no connection to the database')

        if user_id is None:
            sql_query = "SELECT user_id, first_name, last_name, phone, email, active FROM users"
            cursor.execute(sql_query)
            conn.commit()
            res = cursor.fetchall()
            # cursor.close()

            if res is not None:
                result = []
                for i in range(len(res)):
                    result.append({
                        "ID": res[i][0],
                        "f_name": res[i][1],
                        "l_name": res[i][2],
                        "phone": res[i][3],
                        "email": res[i][4],
                        "active": res[i][5]
                    })
            else:
                result = {
                    'confirmation': 'There are no users in the DB'
                }
        else:
            if not str(user_id).isdigit():
                abort(400, description='The user_id must contain only digits')

            if not user_exists('user_id', user_id):
                abort(400, description='The user does not exist')

            sql_query = """SELECT user_id, first_name, last_name, phone, email, active FROM users
                            WHERE user_id = '{0}'""".format(user_id)
            cursor.execute(sql_query)
            conn.commit()
            res = cursor.fetchone()
            # cursor.close()

            if res is not None:
                result = []
                result.append({
                    "ID": res[0],
                    "f_name": res[1],
                    "l_name": res[2],
                    "phone": res[3],
                    "email": res[4],
                    "active": res[5]
                })
            else:
                result = {
                    'confirmation': 'There is no user ID ' + user_id + ' in the DB'
                }
        return jsonify(result)
    # register a new user
    elif request.method == 'POST':
        f_name = request.form.get('first_name')
        l_name = request.form.get('last_name')
        password = request.form.get('password')
        phone = request.form.get('phone')
        email = request.form.get('email')

        if f_name is None or l_name is None or password is None or phone is None or email is None:
            abort(400, description='The f_name, l_name, password, phone and email data are required')

        if user_exists('email', email):
            abort(400, description="The user with this email already exists")

        # making sure that the password is strong enough 8-32 chars,
        # min one digit, min one upper and min one lower letter, min one special char
        check_password = validate_password(password)
        if not check_password['result']:
            abort(400, description=check_password['text'])

        # the email must contain @ and .
        check_email = validate_email(email)
        if not check_email['result']:
            abort(400, description=check_email['text'])

        active = True
        if not conn:
            abort(503, description='There is no connection to the database')

        hash_password, salt = generate_password_hash(password)

        sql_query = """INSERT INTO users (first_name, last_name, password, phone, email, active, salt) VALUES ('{0}', 
                '{1}', '{2}', '{3}', '{4}', '{5}', '{6}')""".format(f_name, l_name, hash_password,
                                                                  phone, email, active, salt)
        cursor.execute(sql_query)
        conn.commit()
        # cursor.close()

        sql_query = """SELECT user_id FROM users WHERE email = '{0}'""".format(email)
        cursor.execute(sql_query)
        res = cursor.fetchone()
        conn.commit()
        # cursor.close()
        user_id = res[0]

        save_to_file(user_id, email, password, 'user-registered')

        result = {
            "ID": user_id,
            "f_name": f_name,
            "l_name": l_name,
            "phone": phone,
            "hash_password": hash_password,
            "salt": salt,
            "active": active,
            "email": email
        }

        push_user_auth()
        return jsonify(result)
    # change a user's data
    elif request.method == 'PUT':
        token = request.form.get('token')
        email = request.form.get('email')
        f_name = request.form.get('f_name')
        l_name = request.form.get('l_name')
        phone = request.form.get('phone')
        new_email = request.form.get('new_email')

        if token is None or email is None:
            abort(400, description='The email and token are required')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

       # if f_name is None and l_name is None and phone is None and new_email is None:
       #     abort(400, description='Ok. Nothing needs to be changed :)')

        if not conn:
            abort(503, description='There is no connection to the database')

        # get the initial user's data
        sql_query = """SELECT user_id, first_name, last_name, phone 
                        FROM users WHERE email = '{0}';""".format(email)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        # cursor.close()

        user_id_db, f_name_db, l_name_db, phone_db = res_[0], res_[1], res_[2], res_[3]

        if (f_name == f_name_db and l_name == l_name_db and phone == phone_db and new_email is None) or \
                (f_name is None and l_name is None and phone is None and new_email is None):
            abort(400, description='Ok. Nothing needs to be changed :)')

        flag_relogin = False
        # what data should be changed
        if f_name is None or f_name == f_name_db:
            f_name = 'The first name has not been changed'
            f_name_to_db = f_name_db
        else:
            f_name_to_db = f_name
        if l_name is None or l_name == l_name_db:
            l_name = 'The last name has not been changed'
            l_name_to_db = l_name_db
        else:
            l_name_to_db = l_name
        if phone is None or phone == phone_db:
            phone = 'The phone number has not been changed'
            new_phone_to_db = phone_db
        else:
            new_phone_to_db = phone
        # change password
        # if password is None:
        #     password = password_db
        # else:
        #     check_password = validate_password(password)
        #     if not check_password['result']:
        #         abort(400, description=check_password['text'])
        #     flag_relogin = True
        if new_email is None or new_email == email:
            new_email = 'The email has not been changed'
            new_email_to_db = email
        else:
            if user_exists('email', new_email):
                abort(400, description="The user with this email already exists")
            check_email = validate_email(new_email)
            if not check_email['result']:
                abort(400, description=check_email['text'])
            save_to_file(user_id_db, email + '->' + new_email, '!password!', 'user-changed-email')
            new_email_to_db = new_email
            flag_relogin = True
            push_user_auth()

        # if the pass and/or email have been changed - the user must log in again
        if flag_relogin:
            r.delete(email)

        # update the data in the users table
        sql_query = """UPDATE users SET first_name = '{0}', last_name = '{1}', email = '{2}', phone = '{3}'
                     WHERE user_id = '{4}';""".format(f_name_to_db, l_name_to_db, new_email_to_db,
                                                      new_phone_to_db, user_id_db)
        cursor.execute(sql_query)
        conn.commit()
        # cursor.close()

        result = {
            'user_id': user_id_db,
            'new first name': f_name,
            'old first name': f_name_db,
            'new last name': l_name,
            'old last name': l_name_db,
            'new email': new_email,
            'old email': email,
            'new phone': phone,
            'old phone': phone_db
        }

        return jsonify(result)
    # delete a user
    elif request.method == 'DELETE':
        email = request.form.get('email')
        token = request.form.get('token')
        sure = request.form.get('ARE_YOU_SURE?')
        admin = request.form.get('admin_password')

        if token is None or email is None or sure is None:
            abort(400, description='The token, email and sure data are required')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        if sure != 'True':
            abort(400, description='АHA! Changed your mind?')

        if admin != 'Do Not Do That!!!':
            abort(400, description='admin password?')

        if not conn:
            abort(503, description='There is no connection to the database')

        sql_query = """SELECT first_name, last_name, user_id FROM users WHERE email = '{0}'""".format(email)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        # cursor.close()

        first_name, last_name, user_id = res_[0], res_[1], res_[2]

        sql_query = """DELETE FROM users WHERE email = '{0}'""".format(email)
        cursor.execute(sql_query)
        conn.commit()
        # cursor.close()

        save_to_file(user_id, email, '!password!', 'user-deleted-himself')

        text = 'R.I.P {{ name }}, i will miss you :('
        template = Template(text)
        result = {
            'confirmation': template.render(name=first_name + ' ' + last_name)
        }

        push_user_auth()
        return jsonify(result)
    else:
        abort(405)


@app.route("/users/user_info", methods=['POST'])  # get all info about the logged user
def user_info():
    if request.method == 'POST':
        token = request.form.get('token')
        email = request.form.get('email')

        if token is None or email is None:
            abort(400, description='The token and email data are required')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        if not conn:
            abort(503, description='There is no connection to the database')

        # collecting the user's personal data from the users db
        sql_query = """SELECT user_id, first_name, last_name, email, phone 
                        FROM users WHERE email = '{0}'""".format(email)
        cursor.execute(sql_query)
        conn.commit()
        res = cursor.fetchone()
        # cursor.close()

        result_users = ({
            "ID": res[0],
            "f_name": res[1],
            "l_name": res[2],
            "email": res[3],
            "phone": res[4]
        })

        user_id = get_user_id(email)
        # collecting the user's storage orders data from the storage_orders db
        sql_query = "SELECT * FROM storage_orders WHERE user_id = '{0}'".format(user_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchall()
        # cursor.close()

        empty_result = []
        if res_ == empty_result:
            result_order = 'You do not have any storage orders'
        else:
            result_order = []
            for i in range(len(res_)):  # does the user need the size_id or size_name data?
                result_order.append({
                    "storage_order_id": res_[i][0],
                    "start_date": res_[i][2],
                    "stop_date": res_[i][3],
                    "order cost": res_[i][5],
                    "shelf_id": res_[i][6]
                })

        # collecting data about the user's vehicles from the user_vehicle, vehicle and sizes db's
        sql_query = """SELECT u_veh_id, vehicle_name, size_name FROM user_vehicle 
                    JOIN vehicle USING (vehicle_id)
                    JOIN sizes USING (size_id) 
                    WHERE user_id = '{0}'""".format(user_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchall()
        # cursor.close()

        empty_result = []
        if res_ == empty_result:
            result_vehicle = 'You do not have any vehicles'
        else:
            result_vehicle = []
            for i in range(len(res_)):
                result_vehicle.append({
                    'vehicle_id': res_[i][0],
                    'vehicle_type': res_[i][1],
                    'tire size': res_[i][2]
                })

        sql_query = """CREATE OR REPLACE VIEW temp AS
                                SELECT 
                                    serv_order_id,
                                    user_id,
                                    serv_order_date,
                                    u_veh_id,
                                    tso.manager_id,
                                    task_id,
                                    task_name,
                                    task_cost,
                                    task_duration,
                                    t.worker_id,
                                    p.position_id,
                                    position_name,
                                    s.first_name,
                                    s.last_name
                                FROM tire_service_order AS tso
                                LEFT JOIN list_of_works USING (serv_order_id)
                                LEFT JOIN tasks AS t USING (task_id)
                                LEFT JOIN staff AS s USING (worker_id)
                                LEFT JOIN positions AS p USING (position_id)
                                LEFT JOIN staff AS st ON st.worker_id = tso.manager_id
                                WHERE user_id = '{0}';""".format(user_id)
        cursor.execute(sql_query)
        conn.commit()
        # cursor.close()

        sql_query = """SELECT DISTINCT serv_order_id, serv_order_date, manager_id, u_veh_id FROM temp"""
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchall()
        # cursor.close()

        empty_result = []
        if res_ == empty_result:
            result_tire_service_order = 'You do not have any tire service orders'
        else:
            result_tire_service_order = []
            for i in range(len(res_)):
                serv_order_id = res_[i][0]

                sql_query = """SELECT SUM(task_cost) FROM temp 
                                WHERE serv_order_id = '{0}'""".format(serv_order_id)
                cursor.execute(sql_query)
                conn.commit()
                res_cost = cursor.fetchone()
                # cursor.close()

                if res_cost[0] is None:
                    tire_service_order_cost = 'Error! Sum is None!'
                else:
                    tire_service_order_cost = res_cost[0]

                sql_query = """SELECT task_name, worker_id, task_cost FROM temp 
                                WHERE serv_order_id = '{0}'""".format(serv_order_id)
                cursor.execute(sql_query)
                conn.commit()
                res_task = cursor.fetchall()
                # cursor.close()

                empty_result_1 = []
                if res_task == empty_result_1:
                    result_tire_service_order_tasks = 'You do not have any tasks in your tire service order.'
                else:
                    result_tire_service_order_tasks = []
                    for j in range(len(res_task)):
                        result_tire_service_order_tasks.append({
                            'task_name': res_task[j][0],
                            'worker_id': res_task[j][1],
                            'task cost': res_task[j][2]
                        })

                result_tire_service_order.append({
                    'serv_order_id': serv_order_id,
                    'serv_order_date': res_[i][1],
                    'manager_id': res_[i][2],
                    'vehicle_id': res_[i][3],
                    'tire service order cost': tire_service_order_cost,
                    'tasks': result_tire_service_order_tasks
                })

        sql_query = """drop view temp"""
        cursor.execute(sql_query)
        conn.commit()

        result = (
            {"your info": result_users},
            {"storage orders info:": result_order},
            {"your vehicle(s)": result_vehicle},
            {"tire service order(s)": result_tire_service_order}
        )
        return jsonify(result)
    else:
        abort(405)


@app.route("/users/login", methods=['POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if password is None or email is None:
            abort(400, description='The pass and email data are required')

        if not user_exists('email', email):
            abort(400, description="The user does not exist. Please, register")

        if not user_active(email):
            abort(400, description='User is deactivated')

        if not conn:
            abort(503, description='There is no connection to the database')

        sql_query = "SELECT salt, user_id, first_name, last_name, password FROM users WHERE email = '{0}'".format(email)
        cursor.execute(sql_query)
        conn.commit()
        res = cursor.fetchone()
        # cursor.close()

        salt, password_db = res[0], res[4]
        if password_is_valid(salt, password, password_db):  # если пароль верен
        # if password == res[0]:
            if r.exists(email) == 0:  # если токена нет в redis db
                token = str(uuid.uuid4())  # генерация токена
                r.set(email, token, ex=600)  # запись токена в redis bd, срок - 600 сек.
            else:
                token = r.get(email)  # возврат токена
                r.set(email, token, ex=600)  # пролонгация токена, срок - 600 сек.

            # генерация Hello message (For fun :)
            text = 'Hello, {{ name }}!'
            template = Template(text)

            result = {
                        "hello_message": template.render(name=res[2]+" "+res[3]),
                        "token": token,
                        "email": email,
                        "user_id": res[1]
            }
            return jsonify(result)
        else:
            abort(401, description='you shall not pass :) password is invalid')
    else:
        abort(405)


@app.route("/users/deactivate_user", methods=['POST'])  # mark the user as inactive (this can be done by the user itself)
def deactivate_user():
    if request.method == 'POST':
        email = request.form.get('email')
        token = request.form.get('token')
        sure = request.form.get('ARE_YOU_SURE?')

        if token is None or email is None or sure is None:
            abort(400, description='The token, email and sure data are required')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        if not user_active(email):
            abort(400, description='User is already deactivated')

        if sure != 'True':
            abort(400, description='АHA! Changed your mind?')

        if not conn:
            abort(503, description='There is no connection to the database')

        sql_query = """UPDATE users SET active = 'False' WHERE email = '{0}'""".format(email)
        cursor.execute(sql_query)
        conn.commit()
        # cursor.close()

        sql_query = """SELECT first_name, last_name FROM users WHERE email = '{0}'""".format(email)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        # cursor.close()

        text = 'User {{ name }} has been successfully deactivated'
        template = Template(text)
        result = {
            'confirmation': template.render(name=res_[0] + ' ' + res_[1])
        }

        return jsonify(result)
    else:
        abort(405)


@app.route("/users/activate_user", methods=['POST'])  # mark the user as active (this can be done only by the admin)
def activate_user():
    if request.method == 'POST':
        email = request.form.get('email')
        admin_password = request.form.get('admin_password')

        if admin_password is None or email is None:
            abort(400, description='The admin_password and email are required')

        if not user_exists('email', email):
            abort(400, description='The user is not exist')

        if admin_password != 'admin':
            abort(400, description='Wrong admin password!')

        if not conn:
            abort(503, description='There is no connection to the database')

        sql_query = """UPDATE users SET active = 'True' WHERE email = '{0}'""".format(email)
        cursor.execute(sql_query)
        conn.commit()
        # cursor.close()

        sql_query = """SELECT first_name, last_name FROM users WHERE email = '{0}'""".format(email)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        # cursor.close()

        text = 'User {{ name }} has been successfully activated'
        template = Template(text)
        result = {
            'confirmation': template.render(name=res_[0] + ' ' + res_[1])
        }

        return jsonify(result)
    else:
        abort(405)


@app.route("/vehicle", methods=['POST', 'PUT', 'DELETE'])  # add new/change/delete user's vehicle
def users_vehicle():
    if request.method == 'POST':
        token = request.form.get('token')
        email = request.form.get('email')
        vehicle_name = request.form.get('vehicle_name')
        size_name = request.form.get('size_name')

        if token is None or email is None or vehicle_name is None or size_name is None:
            abort(400, description='The token, email, vehicle_name and size_name data are required')

        # get needed data
        user_id = get_user_id(email)
        size_id = size_one_by_var('size_id', 'size_name', size_name)
        vehicle_id = vehicle_one_by_var('vehicle_id', 'vehicle','vehicle_name', vehicle_name)

        if size_id is None:
            abort(400, description='Unknown tire size, add the tire size data to the sizes DB')

        if vehicle_id is None:
            abort(400, description='Unknown type of the vehicle, add the vehicle type data to the vehicle DB')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        if not conn:
            abort(503, description='There is no connection to the database')

        sql_query = """INSERT INTO user_vehicle (user_id, vehicle_id, size_id) 
                        VALUES ('{0}', '{1}', '{2}');""".format(user_id, vehicle_id, size_id)
        cursor.execute(sql_query)
        conn.commit()
        # cursor.close()

        sql_query = """SELECT MAX(u_veh_id) FROM user_vehicle WHERE user_id = '{0}'""".format(user_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        # cursor.close()

        result = {
            'new_vehicle_id': res_[0],
            'vehicle_name': vehicle_name,
            'tire_size': size_name
        }
        return jsonify(result)
    elif request.method == 'PUT':
        email = request.form.get('email')
        token = request.form.get('token')
        u_veh_id = request.form.get('user vehicle id')
        new_vehicle_name = request.form.get('new vehicle name')
        new_size_name = request.form.get('new size name')

        if token is None or email is None or u_veh_id is None:
            abort(400, description='The token, email and user vehicle id are required')

        if not vehicle_exists(u_veh_id):
            abort(400, description='The vehicle does not exist')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        if not conn:
            abort(503, description='There is no connection to the database')

        sql_query = """SELECT user_id, vehicle_id, size_id FROM user_vehicle WHERE u_veh_id = '{0}'""".format(u_veh_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        # cursor.close()

        user_id_db, vehicle_id_db, size_id_db = res_[0], res_[1], res_[2]

        if user_id_db != get_user_id(email):
            abort(403, description='It is not your vehicle! Somebody call the police!')

        vehicle_name_db = vehicle_one_by_var('vehicle_name', 'vehicle', 'vehicle_id', vehicle_id_db)
        size_name_db = str(size_one_by_var('size_name', 'size_id', size_id_db))

        if (new_vehicle_name is None and new_size_name is None) or \
                (new_vehicle_name == vehicle_name_db and new_size_name == size_name_db):
            abort(400, description='Ok. Nothing needs to be changed :)')

        if new_vehicle_name is None or new_vehicle_name == vehicle_name_db:
            new_vehicle_id = vehicle_id_db
            new_vehicle_name = 'The vehicle name has not been changed'
        else:
            new_vehicle_id = vehicle_one_by_var('vehicle_id', 'vehicle','vehicle_name', new_vehicle_name)
            if not new_vehicle_id:
                abort(400, description='Unknown vehicle_name')

        if new_size_name is None or new_size_name == size_name_db:
            new_size_id = size_id_db
            new_size_name = 'The size name has not been changed'
        else:
            new_size_id = size_one_by_var('size_id', 'size_name', new_size_name)
            if not new_size_id:
                abort(400, description='Unknown size_name')

        sql_query = """UPDATE user_vehicle SET vehicle_id = '{0}', size_id = '{1}' 
                        WHERE u_veh_id = '{2}'""".format(new_vehicle_id, new_size_id, u_veh_id)
        cursor.execute(sql_query)
        conn.commit()
        # cursor.close()

        result = {
            'vehicle_id': u_veh_id,
            'old_vehicle_name': vehicle_name_db,
            'new_vehicle_name': new_vehicle_name,
            'old_size_name': size_name_db,
            'new_size_name': new_size_name
        }

        return jsonify(result)
    elif request.method == 'DELETE':
        email = request.form.get('email')
        token = request.form.get('token')
        u_veh_id = request.form.get('user_vehicle_id')

        if token is None or email is None or u_veh_id is None:
            abort(400, description='The token, email and user_vehicle_id are required')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        if not conn:
            abort(503, description='There is no connection to the database')

        if not vehicle_exists(u_veh_id):
            abort(400, description='The vehicle does not exist')

        user_id = vehicle_one_by_var('user_id', 'user_vehicle','u_veh_id', u_veh_id)

        if get_user_id(email) != user_id:
            abort(403, description='It is not your vehicle! Somebody call the police!')
        else:

            sql_query = """DELETE FROM user_vehicle WHERE u_veh_id = '{0}'""".format(u_veh_id)
            cursor.execute(sql_query)
            conn.commit()
            # cursor.close()
            result = {
                'confirmation': 'User vehicle ID ' + u_veh_id + ' has been deleted'
            }
            return jsonify(result)
    else:
        abort(405)


@app.route("/warehouse", methods=['GET'])  # shows shelves in the warehouse (availability depends on the request params)
def available_storage():
    if request.method == 'GET':
        size_name = request.args.get('size_name')
        available_only = request.args.get('available_only')

        # if size_name is None - show all sizes
        # if available_only.lower() = 'yes' - show only free shelves
        # if available_only.lower() = 'no' - show only occupied shelves
        # if available_only.lower() != 'yes' and != 'no' - show all free shelves
        if available_only is None:
            available_only = 'undefined'

        if not conn:
            abort(503, description='There is no connection to the database')

        if size_name is None:
            if available_only.lower() == 'yes':

                sql_query = """SELECT shelf_id, size_id, available FROM warehouse 
                                WHERE available = 'True'"""
                cursor.execute(sql_query)
                conn.commit()
                res_ = cursor.fetchall()
                # cursor.close()

            elif available_only.lower() == 'no':

                sql_query = """SELECT shelf_id, size_id, available FROM warehouse 
                                                WHERE available = 'False'"""
                cursor.execute(sql_query)
                conn.commit()
                res_ = cursor.fetchall()
                # cursor.close()

            else:

                sql_query = """SELECT shelf_id, size_id, available FROM warehouse"""
                cursor.execute(sql_query)
                conn.commit()
                res_ = cursor.fetchall()
                # cursor.close()

            if res_:
                result = []
                for i in range(len(res_)):
                    result.append({
                        'shelf_id': res_[i][0],
                        'size_id': res_[i][1],
                        'size_name': size_one_by_var('size_name', 'size_id', res_[i][1]),
                        'available': res_[i][2]
                    })
            else:
                result = {
                    'confirmation': 'Unfortunately, we do not have available storage shelves you need'
                }
        else:
            size_id = size_one_by_var('size_id', 'size_name', size_name)

            if available_only.lower() == 'yes':

                sql_query = """SELECT shelf_id, size_id, available FROM warehouse WHERE available = 'True'
                                AND size_id = '{0}'""".format(size_id)
                cursor.execute(sql_query)
                conn.commit()
                res_ = cursor.fetchall()
                # cursor.close()

            elif available_only.lower() == 'no':

                sql_query = """SELECT shelf_id, size_id, available FROM warehouse WHERE available = 'False'
                                                AND size_id = '{0}'""".format(size_id)
                cursor.execute(sql_query)
                conn.commit()
                res_ = cursor.fetchall()
                # cursor.close()

            else:

                sql_query = """SELECT shelf_id, size_id, available FROM warehouse 
                                WHERE size_id = '{0}'""".format(size_id)
                cursor.execute(sql_query)
                conn.commit()
                res_ = cursor.fetchall()
                # cursor.close()

            if res_:
                result = []
                for i in range(len(res_)):
                    result.append({
                        'shelf_id': res_[i][0],
                        'size_id': res_[i][1],
                        'size_name': size_name,
                        'available': res_[i][2]
                    })
            else:
                result = {
                    'confirmation': 'Unfortunately, we do not have storage shelves you need'
                }
        return jsonify(result)
    else:
        abort(405)


@app.route("/storage_order", methods=['POST', 'PUT', 'DELETE'])  # add new/change/delete the user's storage order
def storage_order():
    if request.method == 'POST':
        token = request.form.get('token')
        email = request.form.get('email')
        start_date = request.form.get('start_date')
        stop_date = request.form.get('stop_date')
        size_name = request.form.get('size_name')
        u_veh_id = request.form.get('user_vehicle_id')

        if token is None or email is None or start_date is None or stop_date is None:
            abort(400, description='The token, email, start_date, stop_date and size_name data are required')

        if size_name is None or u_veh_id is None:
            abort(400, description='The size_name OR user_vehicle_id is required')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        user_id = get_user_id(email)

        if u_veh_id is not None:
            if vehicle_one_by_var('user_id', 'user_vehicle', 'u_veh_id', u_veh_id) != user_id:
                abort(403, description='It is not your vehicle! Somebody call the police!')
            size_name = size_one_by_var('size_name', 'size_id', vehicle_one_by_var('size_id', 'user_vehicle','u_veh_id', u_veh_id))

        # is there the necessary free storage space
        if not shelf_avail(size_name):
            abort(400, description="Sorry, we do not have the storage you need")

        shelf_id = shelf_id_by_size(size_name)

        if not conn:
            abort(503, description='There is no connection to the database')

        size_id_by = size_one_by_var('size_id', 'size_name', size_name)
        if size_id_by is None:
            abort(400, description='Unknown size_name')

        # create storage order
        sql_query = """INSERT INTO storage_orders (user_id, start_date, stop_date, size_id, shelf_id, 
                    st_ord_cost) VALUES('{0}', '{1}', '{2}', '{3}', '{4}', '{5}');""".\
                    format(user_id, start_date, stop_date, size_id_by, shelf_id, 1000)
        cursor.execute(sql_query)
        conn.commit()
        # cursor.close()

        # get the new storage order id
        sql_query = """SELECT st_ord_id FROM storage_orders WHERE shelf_id = '{0}';""".format(shelf_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        # cursor.close()

        new_st_ord_id = res_[0]

        # set the shelf_id as not available
        sql_query = """UPDATE warehouse SET available = False WHERE shelf_id = '{0}';""".format(shelf_id)
        cursor.execute(sql_query)
        conn.commit()
        # cursor.close()

        return jsonify({'shelf_id': shelf_id, 'storage order id': new_st_ord_id})
    elif request.method == 'PUT':
        st_ord_id = request.form.get('st_ord_id')
        token = request.form.get('token')
        email = request.form.get('email')
        start_date = request.form.get('start_date')
        stop_date = request.form.get('stop_date')
        st_ord_cost = request.form.get('st_ord_cost')
        size_name = request.form.get('size_name')

        if token is None or email is None or st_ord_id is None:
            abort(400, description='The token, email, st_ord_id data are required')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        if not conn:
            abort(503, description='There is no connection to the database')

        if not storage_order_exists(st_ord_id):
            abort(400, description='The storage order does not exists')

        size_id = size_one_by_var('size_id', 'size_name', size_name)

        # get the initial data of the storage order
        sql_query = """SELECT start_date, stop_date, size_id, st_ord_cost, shelf_id, user_id 
                        FROM storage_orders WHERE st_ord_id = '{0}';""".format(st_ord_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        # cursor.close()

        start_date_db, stop_date_db, size_id_db, st_ord_cost_db, shelf_id_db, user_id_db, shelf_id = \
            res_[0], res_[1], res_[2], res_[3], res_[4], res_[5], 0

        # verify, that the storage order is created by user
        if get_user_id(email) != user_id_db:
            abort(403, description='Ouch! This is not your storage order!')

        # what data should be changed
        # check dates
        if start_date is not None and stop_date is not None:
            if start_date > stop_date:
                abort(400, description='The start date can not be greater than the stop date')
            if stop_date < start_date:
                abort(400, description='The stop date can not be less than the start date')

        if start_date is not None and stop_date is None:
            if datetime.datetime.strptime(start_date, '%Y-%m-%d') > datetime.datetime.strptime(str(stop_date_db), '%Y-%m-%d'):
                abort(400, description='The start date can not be greater than the stop date')

        if start_date is None and stop_date is not None:
            if datetime.datetime.strptime(stop_date, '%Y-%m-%d') < datetime.datetime.strptime(str(start_date_db), '%Y-%m-%d'):
                abort(400, description='The stop date can not be less than the start date')

        if start_date is None:
            start_date = start_date_db
        if stop_date is None:
            stop_date = stop_date_db
        if st_ord_cost is None:
            st_ord_cost = st_ord_cost_db
        if size_id is None:
            size_id = size_id_db
        else:
            # if the tire size data needs to be changed
            if int(size_id) != size_id_db:
                sql_query = """SELECT MIN(shelf_id) FROM warehouse WHERE available = 'True' 
                                AND size_id = '{0}';""".format(size_id)
                cursor.execute(sql_query)
                conn.commit()
                shelf_avail_ = cursor.fetchone()
                # cursor.close()

                # if there is available storage
                if shelf_avail is not None:
                    shelf_id = shelf_avail_[0]

                    # update changed storage places
                    sql_query = """UPDATE warehouse SET available = 'True' 
                                    WHERE shelf_id = '{0}';""".format(shelf_id_db)
                    cursor.execute(sql_query)
                    conn.commit()
                    # cursor.close()

                    sql_query = """UPDATE warehouse SET available = 'False' 
                                    WHERE shelf_id = '{0}';""".format(shelf_id)
                    cursor.execute(sql_query)
                    conn.commit()
                    # cursor.close()

                else:
                    abort(400, description='Sorry, we do not have the storage you need')

        if shelf_id == 0:
            shelf_id = shelf_id_db

        # update data in the DB

        sql_query = """UPDATE storage_orders SET start_date = '{0}', stop_date = '{1}', size_id = '{2}',
                    st_ord_cost = '{3}', shelf_id = '{4}' WHERE st_ord_id = '{5}';""".\
                    format(start_date, stop_date, size_id, st_ord_cost, shelf_id, st_ord_id)
        cursor.execute(sql_query)
        conn.commit()
        # cursor.close()

        result = {
            'storage_order': st_ord_id,
            'start_date': start_date,
            'stop_date': stop_date,
            'size_id_new': size_id,
            'size_id_old': size_id_db,
            'storage_order_cost': st_ord_cost,
            'shelf_id_new': shelf_id,
            'shelf_id_old': shelf_id_db
        }

        return jsonify(result)
    elif request.method == 'DELETE':
        email = request.form.get('email')
        token = request.form.get('token')
        st_ord_id = request.form.get('storage_order_id')

        if token is None or email is None or st_ord_id is None:
            abort(400, description='The token, email and storage_order_id are required')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        if not conn:
            abort(503, description='There is no connection to the database')

        if not storage_order_exists(st_ord_id):
            abort(400, description='The storage order does not exist')

        sql_query = """SELECT user_id, shelf_id FROM storage_orders WHERE st_ord_id = '{0}'""".format(st_ord_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        # cursor.close()

        shelf_id = res_[1]

        if get_user_id(email) != res_[0]:
            abort(403, description='It is not your storage order!')

        sql_query = """DELETE FROM storage_orders WHERE st_ord_id = '{0}'""".format(st_ord_id)
        cursor.execute(sql_query)
        conn.commit()
        # cursor.close()

        # set the shelf_id as available
        sql_query = """UPDATE warehouse SET available = True WHERE shelf_id = '{0}';""".format(shelf_id)
        cursor.execute(sql_query)
        conn.commit()
        # cursor.close()

        result = {
            'confirmation': 'Storage order ID ' + st_ord_id + ' has been deleted'
        }
        return jsonify(result)
    else:
        abort(405)


@app.route("/tire_service_order", methods=['POST', 'PUT', 'DELETE'])  # add new/change/delete the user's service order
def tire_service_order():
    if request.method == 'POST':
        email = request.form.get('email')
        token = request.form.get('token')
        order_date = request.form.get('order_date')
        u_veh_id = request.form.get('user_vehicle_id')

        if token is None or email is None or order_date is None or u_veh_id is None:
            abort(400, description='The token, email, order_date and user_vehicle_id are required')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        if not conn:
            abort(503, description='There is no connection to the database')

        # get the initial data about user's vehicle
        sql_query = """SELECT user_id, vehicle_id, size_id FROM user_vehicle 
                        WHERE u_veh_id = '{0}';""".format(u_veh_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        # cursor.close()

        user_id, vehicle_id, size_id = res_[0], res_[1], res_[2]

        if get_user_id(email) != user_id:
            abort(403, description='It is not your vehicle!')

        sql_query = """SELECT manager_id, COUNT(manager_id) FROM managers LEFT JOIN tire_service_order 
                    USING (manager_id) WHERE available = True GROUP BY manager_id HAVING COUNT(manager_id) < 5"""
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchall()
        # cursor.close()

        if not res_:
            abort(400, description='Sorry, all managers are busy')

        rand_id = random.randint(0, len(res_) - 1)

        manager_id, manager_load = res_[rand_id][0], res_[rand_id][1]

        if manager_load == 4:
            sql_query = """UPDATE staff SET available = False WHERE worker_id = '{0}'""".format(manager_id)
            cursor.execute(sql_query)
            conn.commit()
            # cursor.close()

        sql_query = """INSERT INTO tire_service_order (user_id, serv_order_date, u_veh_id, manager_id)
                        VALUES ('{0}', '{1}', '{2}', '{3}')""".format(user_id, order_date, u_veh_id, manager_id)
        cursor.execute(sql_query)
        conn.commit()
        # cursor.close()

        sql_query = """SELECT MAX(serv_order_id) FROM tire_service_order WHERE user_id = '{0}'""".format(user_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        # cursor.close()

        serv_order_id = res_[0]

        sql_query = """SELECT first_name, last_name, phone, email FROM managers 
                        WHERE manager_id = '{0}'""".format(manager_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        # cursor.close()

        manager_first_name, manager_last_name, manager_phone, manager_email = res_[0], res_[1], res_[2], res_[3]

        result = {
            'service_order_id': serv_order_id,
            'date': order_date,
            'manager_id': manager_id,
            'manager_first_name': manager_first_name,
            'manager_last_name': manager_last_name,
            'manager_phone': manager_phone,
            'manager_email': manager_email
        }
        return jsonify(result)
    elif request.method == 'PUT':
        email = request.form.get('email')
        token = request.form.get('token')
        serv_order_id = request.form.get('service order id')
        new_order_date = request.form.get('new order date')
        new_u_veh_id = request.form.get('new user vehicle id')

        # if token is None or email is None or serv_order_id is None:
        #     abort(400, description='The token, email, service order id are required')

        if not token or not email or not serv_order_id:
            abort(400, description='The token, email, service order id are required')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        if not conn:
            abort(503, description='There is no connection to the database')

        if not tire_service_order_exists(serv_order_id):
            abort(400, description='The tire service order does not exist')

        # get the initial data about the tire_service_order
        sql_query = """SELECT user_id, u_veh_id, serv_order_date FROM tire_service_order 
                            WHERE serv_order_id = '{0}';""".format(serv_order_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        # cursor.close()

        user_id, u_veh_id_db, serv_order_date_db = res_[0], res_[1], res_[2]

        if get_user_id(email) != user_id:
            abort(403, description='It is not your tire service order!')

        if (new_order_date is None and new_u_veh_id is None) or \
                (new_order_date == serv_order_date_db and new_u_veh_id == u_veh_id_db):
            abort(400, description='Ok. Nothing needs to be changed :)')

        if not new_order_date or new_order_date == serv_order_date_db:
            order_date_to_db = serv_order_date_db
            new_order_date = 'The tire service date has not been changed'
        else:
            order_date_to_db = new_order_date
            if datetime.datetime.strptime(new_order_date[:10], '%Y-%m-%d') < \
                    datetime.datetime.strptime(str(datetime.datetime.now())[:10], '%Y-%m-%d'):
                abort(400, description='The new tire service date can not be earlier than today')

        if not new_u_veh_id or new_u_veh_id == u_veh_id_db:
            u_veh_id_to_db = u_veh_id_db
            new_u_veh_id = 'The vehicle id has not been changed'
        else:
            u_veh_id_to_db = new_u_veh_id

        sql_query = """UPDATE tire_service_order SET serv_order_date = '{0}', u_veh_id = '{1}'
                                WHERE serv_order_id = '{2}'""".format(order_date_to_db, u_veh_id_to_db, serv_order_id)
        cursor.execute(sql_query)
        conn.commit()
        # cursor.close()

        result = {
            'tire service order': serv_order_id,
            'old_vehicle_id': u_veh_id_db,
            'new_vehicle_id': new_u_veh_id,
            'old_order_date': serv_order_date_db,
            'new_order_date': new_order_date
        }

        return jsonify(result)
    elif request.method == 'DELETE':
        email = request.form.get('email')
        token = request.form.get('token')
        serv_order_id = request.form.get('service_order_id')

        if token is None or email is None or serv_order_id is None:
            abort(400, description='The token, email, service_order_id are required')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        if not conn:
            abort(503, description='There is no connection to the database')

        if not tire_service_order_exists(serv_order_id):
            abort(400, description='The tire service order does not exist')

        # get the initial data about the tire_service_order
        sql_query = """SELECT user_id, u_veh_id, manager_id FROM tire_service_order 
                        WHERE serv_order_id = '{0}';""".format(serv_order_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        # cursor.close()

        user_id, u_veh_id, manager_id = res_[0], res_[1], res_[2]

        if get_user_id(email) != user_id:
            abort(403, description='It is not your tire service order!')

        sql_query = """SELECT manager_id, COUNT(manager_id) FROM managers JOIN tire_service_order
                    USING (manager_id) WHERE manager_id = '{0}' GROUP BY manager_id""".format(manager_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        # cursor.close()

        manager_id, manager_load = res_[0], res_[1]

        # if the manager's load becomes less than 5 when the order is deleted, mark it as available
        if manager_load == 5:
            sql_query = """UPDATE staff SET available = True WHERE worker_id = '{0}'""".format(manager_id)
            cursor.execute(sql_query)
            conn.commit()
            # cursor.close()

        sql_query = """DELETE FROM tire_service_order WHERE serv_order_id = '{0}'""".format(serv_order_id)
        cursor.execute(sql_query)
        conn.commit()
        # cursor.close()

        text = 'Tire service order ID {{ name }} has been deleted'
        template = Template(text)

        result = {
            "confirmation": template.render(name=serv_order_id),
        }

        return jsonify(result)
    else:
        abort(405)


@app.route("/tire_service_order/task", methods=['POST']) # add new/change/delete a task to the user's service order
def task():
    # add a task to the list_of_works
    if request.method == 'POST':
        email = request.form.get('email')
        token = request.form.get('token')
        serv_order_id = request.form.get('service_order_id')
        task_name = request.form.get('task_name')
        numbers_of_task = request.form.get('numbers_of_tasks')

        if token is None or email is None or serv_order_id is None or task_name is None:
            abort(400, description='The token, email, service_order_id and task_name are required')

        if not numbers_of_task.isdigit():
            abort(400, description='Please, provide a numbers of tasks in digits')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        if not conn:
            abort(503, description='There is no connection to the database')

        sql_query = """SELECT user_id FROM tire_service_order WHERE serv_order_id = '{0}';""".format(serv_order_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        # cursor.close()

        if get_user_id(email) != res_[0]:
            abort(403, description='It is not your tire service order!')

        sql_query = """SELECT task_id FROM tasks WHERE task_name = '{0}';""".format(task_name)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        # cursor.close()

        if res_ is None:
            abort(400, description='Sorry, we do not offer this service')

        task_id = res_[0]

        for _ in range(int(numbers_of_task)):

            sql_query = """INSERT INTO list_of_works (serv_order_id, task_id)
                            VALUES ('{0}', '{1}');""".format(serv_order_id, task_id)
            cursor.execute(sql_query)
            conn.commit()

        if int(numbers_of_task) == 1:
            result = {
                'confirmation': 'The ' + task_name + ' task is successfully added to your tire_service_order ID ' \
                                + serv_order_id
            }
        else:
            result = {
                'confirmation': 'tasks for ' + task_name + ' in the amount of ' + numbers_of_task + \
                     ' have been successfully added to your tire_service_order ID ' + serv_order_id
            }

        return jsonify(result)
    else:
        abort(405)


if __name__ == '__main__':
    app.run()
