import random
from flask import Flask, request, jsonify, abort
from jinja2 import Template
import psycopg2
import uuid
import re
import redis
import datetime
from datetime import date
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
        active = request.args.get('active')

        if not conn:
            abort(503, description='There is no connection to the database')

        if not active:
            active = ''

        if not user_id:
            if active.lower() == 'yes':
                sql_query = "SELECT user_id, first_name, last_name, phone, email FROM users WHERE active = True"
            elif active.lower() == 'no':
                sql_query = "SELECT user_id, first_name, last_name, phone, email FROM users WHERE active = False"
            else:
                sql_query = "SELECT user_id, first_name, last_name, phone, email FROM users"
            cursor.execute(sql_query)
            conn.commit()
            res = cursor.fetchall()

            if res:
                result = []
                for i in range(len(res)):
                    result.append({
                        "ID": res[i][0],
                        "f_name": res[i][1],
                        "l_name": res[i][2],
                        "phone": res[i][3],
                        "email": res[i][4]
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

            if active.lower() == 'yes' or active.lower() == 'no':
                if not user_active(get_value_from_table('email', 'users', 'user_id', user_id)):
                    abort(400, description='User is deactivated')

            sql_query = """SELECT user_id, first_name, last_name, phone, email, active FROM users
                            WHERE user_id = '{0}'""".format(user_id)
            cursor.execute(sql_query)
            conn.commit()
            res = cursor.fetchone()


            if res is not None:
                result = []
                result.append({
                    "ID": res[0],
                    "f_name": res[1],
                    "l_name": res[2],
                    "phone": res[3],
                    "email": res[4]
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

        if not f_name or not l_name or not password or not phone or not email:
            abort(400, description='The f_name, l_name, password, phone and email data are required')

        if user_exists('email', email):
            abort(400, description="The user with this email already exists")

        #The names can only include the ' '(space) and '.,- chars
        #The {0} must be at least 1 characters long and not exceed 30 chars
        check_first_name = validate_names('first name', f_name)
        if not check_first_name['result']:
            abort(400, description=check_first_name['text'])

        check_last_name = validate_names('last name', l_name)
        if not check_last_name['result']:
            abort(400, description=check_last_name['text'])

        # make sure that the password is strong enough: 8-32 chars,
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

        sql_query = """SELECT user_id FROM users WHERE email = '{0}'""".format(email)
        cursor.execute(sql_query)
        res = cursor.fetchone()
        conn.commit()

        user_id = res[0]

        save_to_file(user_id, email, password, 'user-registered')

        result = {
            "ID": user_id,
            "f_name": f_name,
            "l_name": l_name,
            "phone": phone,
            "email": email
        }

        # push_user_auth()
        return jsonify(result)
    # change a user's data
    elif request.method == 'PUT':
        token = request.form.get('token')
        email = request.form.get('email')
        f_name = request.form.get('f_name')
        l_name = request.form.get('l_name')
        phone = request.form.get('phone')
        new_email = request.form.get('new_email')

        if not token or not email:
            abort(400, description='The email and token are required')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        r.expire(email, 600)

        if not conn:
            abort(503, description='There is no connection to the database')

        # get the initial user's data
        sql_query = """SELECT user_id, first_name, last_name, phone 
                        FROM users WHERE email = '{0}';""".format(email)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()

        user_id_db, f_name_db, l_name_db, phone_db = res_

        if (f_name == f_name_db and l_name == l_name_db and phone == phone_db and not new_email) or \
                (not f_name and not l_name and not phone and not new_email):
            abort(400, description='Ok. Nothing needs to be changed :)')

        # what data should be changed
        if not f_name or f_name == f_name_db:
            f_name = 'The first name has not been changed'
            f_name_to_db = f_name_db
        else:
            f_name_to_db = f_name

        if not l_name or l_name == l_name_db:
            l_name = 'The last name has not been changed'
            l_name_to_db = l_name_db
        else:
            l_name_to_db = l_name

        if not phone or phone == phone_db:
            phone = 'The phone number has not been changed'
            new_phone_to_db = phone_db
        else:
            new_phone_to_db = phone

        if not new_email or new_email == email:
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
            r.delete(email)
            # push_user_auth()

        # update the data in the users table
        sql_query = """UPDATE users SET first_name = '{0}', last_name = '{1}', email = '{2}', phone = '{3}'
            WHERE user_id = '{4}';""".format(f_name_to_db, l_name_to_db, new_email_to_db, new_phone_to_db, user_id_db)
        cursor.execute(sql_query)
        conn.commit()

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

        if not token or not email or not sure or not admin:
            abort(400, description='The token, email, answer and admin password data are required')

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

        first_name, last_name, user_id = res_

        sql_query = """DELETE FROM users WHERE email = '{0}'""".format(email)
        cursor.execute(sql_query)
        conn.commit()

        save_to_file(user_id, email, '!password!', 'user-deleted-himself')

        text = 'R.I.P {{ name }}, i will miss you :('
        template = Template(text)
        result = {
            'confirmation': template.render(name=first_name + ' ' + last_name)
        }

        # push_user_auth()
        return jsonify(result)
    else:
        abort(405)


@app.route("/users/user_info", methods=['POST'])  # get all info about the logged user
def user_info():
    if request.method == 'POST':
        token = request.form.get('token')
        email = request.form.get('email')

        if not token or not email:
            abort(400, description='The token and email data are required')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        r.expire(email, 600)

        if not conn:
            abort(503, description='There is no connection to the database')

        # collecting the user's personal data from the users db
        sql_query = """SELECT user_id, first_name, last_name, email, phone 
                        FROM users WHERE email = '{0}'""".format(email)
        cursor.execute(sql_query)
        conn.commit()
        res = cursor.fetchone()

        result_users = ({
            "ID": res[0],
            "first_name": res[1],
            "last_name": res[2],
            "email": res[3],
            "phone": res[4]
        })

        user_id = get_user_id(email)
        # collecting the user's storage orders data from the storage_orders db
        sql_query = """SELECT storage_order_id, start_date, stop_date, storage_order_cost, shelf_id 
                                                FROM storage_orders WHERE user_id = '{0}'""".format(user_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchall()

        empty_result = []
        if res_ == empty_result:
            result_order = 'You do not have any storage orders'
        else:
            result_order = []
            for i in res_:  # does the user need the size_id or size_name data?
                result_order.append({
                    "storage_order_id": i[0],
                    "start_date": i[1],
                    "stop_date": i[2],
                    "order cost": i[3],
                    "shelf_id": i[4]
                })

        # collecting data about the user's vehicles from the user_vehicle, vehicle and sizes db's
        sql_query = """SELECT user_vehicle_id, vehicle_name, size_name FROM user_vehicle 
                    JOIN vehicle USING (vehicle_id)
                    JOIN sizes USING (size_id) 
                    WHERE user_id = '{0}'""".format(user_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchall()

        if not res_:
            result_vehicle = 'You do not have any vehicles'
        else:
            result_vehicle = []
            for i in res_:
                result_vehicle.append({
                    'vehicle_id': i[0],
                    'vehicle_name': i[1],
                    'size_name': i[2]
                })

        sql_query = """CREATE OR REPLACE VIEW temp AS
                                SELECT 
                                    service_order_id,
                                    user_id,
                                    service_order_date,
                                    user_vehicle_id,
                                    tso.manager_id,
                                    task_id,
                                    task_name,
                                    task_cost,
                                    task_duration,
                                    low.worker_id,
                                    p.position_id,
                                    position_name,
                                    s.first_name,
                                    s.last_name
                                FROM tire_service_order AS tso
                                LEFT JOIN list_of_works AS low USING (service_order_id)
                                LEFT JOIN tasks AS t USING (task_id)
                                LEFT JOIN staff AS s USING (worker_id)
                                LEFT JOIN positions AS p USING (position_id)
                                LEFT JOIN staff AS st ON st.worker_id = tso.manager_id
                                WHERE user_id = '{0}';""".format(user_id)
        cursor.execute(sql_query)
        conn.commit()

        sql_query = """SELECT DISTINCT service_order_id, service_order_date, manager_id, user_vehicle_id FROM temp"""
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchall()

        if not res_:
            result_tire_service_order = 'You do not have any tire service orders'
        else:
            result_tire_service_order = []
            for i in res_:
                service_order_id = i[0]

                sql_query = """SELECT SUM(task_cost) FROM temp 
                                WHERE service_order_id = '{0}'""".format(service_order_id)
                cursor.execute(sql_query)
                conn.commit()
                res_cost = cursor.fetchone()

                if not res_cost[0]:
                    tire_service_order_cost = 'Error! Sum is None!'
                else:
                    tire_service_order_cost = res_cost[0]

                sql_query = """SELECT task_name, worker_id, task_cost FROM temp 
                                WHERE service_order_id = '{0}'""".format(service_order_id)
                cursor.execute(sql_query)
                conn.commit()
                res_task = cursor.fetchall()

                if not res_task[0][0]:
                    result_tire_service_order_tasks = 'You do not have any tasks in your tire service order.'
                else:
                    result_tire_service_order_tasks = []
                    for j in res_task:
                        result_tire_service_order_tasks.append({
                            'task_name': j[0],
                            'worker_id': j[1],
                            'task cost': j[2]
                        })

                result_tire_service_order.append({
                    'service_order_id': service_order_id,
                    'service_order_date': i[1],
                    'manager_id': i[2],
                    'vehicle_id': i[3],
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

        if not password or not email:
            abort(400, description='The pass and email data are required')

        if not user_exists('email', email):
            abort(400, description="The user does not exist. Please, register")

        if not user_active(email):
            abort(400, description='The user is deactivated')

        if not conn:
            abort(503, description='There is no connection to the database')

        sql_query = "SELECT salt, user_id, first_name, last_name, password FROM users WHERE email = '{0}'".format(email)
        cursor.execute(sql_query)
        conn.commit()
        res = cursor.fetchone()

        salt, user_id, first_name, last_name, password_db = res

        if password_is_valid(salt, password, password_db):
            if r.exists(email) == 0:
                token = str(uuid.uuid4())
                r.set(email, token, ex=600)
            else:
                token = r.get(email)
                r.expire(email, 600)

            # Hello message (For fun :)
            text = 'Hello, {{ name }}!'
            template = Template(text)

            result = {
                        "hello_message": template.render(name=first_name + " " + last_name),
                        "token": token,
                        "email": email,
                        "user_id": user_id
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

        if not token or not email or not sure:
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

        sql_query = """SELECT first_name, last_name FROM users WHERE email = '{0}'""".format(email)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()

        first_name, last_name = res_

        text = 'User {{ name }} has been successfully deactivated'
        template = Template(text)
        result = {
            'confirmation': template.render(name=first_name + ' ' + last_name)
        }

        r.delete(email)
        return jsonify(result)
    else:
        abort(405)


@app.route("/users/activate_user", methods=['POST'])  # mark the user as active (this can be done only by the admin)
def activate_user():
    if request.method == 'POST':
        email = request.form.get('email')
        admin_password = request.form.get('admin_password')

        if not admin_password or not email:
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

        sql_query = """SELECT first_name, last_name FROM users WHERE email = '{0}'""".format(email)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()

        first_name, last_name = res_

        text = 'User {{ name }} has been successfully activated'
        template = Template(text)
        result = {
            'confirmation': template.render(name=first_name + ' ' + last_name)
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

        if not token or not email or not vehicle_name or not size_name:
            abort(400, description='The token, email, vehicle_name and size_name data are required')

        # get needed data
        user_id = get_user_id(email)
        size_id = get_value_from_table('size_id', 'sizes', 'size_name', size_name)
        vehicle_id = get_value_from_table('vehicle_id', 'vehicle','vehicle_name', vehicle_name)

        if not size_id:
            abort(400, description='Unknown tire size, add the tire size data to the sizes DB')

        if not vehicle_id:
            abort(400, description='Unknown type of the vehicle, add the vehicle type data to the vehicle DB')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        r.expire(email, 600)

        if not conn:
            abort(503, description='There is no connection to the database')

        sql_query = """INSERT INTO user_vehicle (user_id, vehicle_id, size_id) 
                        VALUES ('{0}', '{1}', '{2}');""".format(user_id, vehicle_id, size_id)
        cursor.execute(sql_query)
        conn.commit()

        sql_query = """SELECT MAX(user_vehicle_id) FROM user_vehicle WHERE user_id = '{0}'""".format(user_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()

        result = {
            'new_vehicle_id': res_[0],
            'vehicle_name': vehicle_name,
            'size_name': size_name
        }
        return jsonify(result)
    elif request.method == 'PUT':
        email = request.form.get('email')
        token = request.form.get('token')
        user_vehicle_id = request.form.get('user_vehicle_id')
        new_vehicle_name = request.form.get('new_vehicle_name')
        new_size_name = request.form.get('new_size_name')

        if not token or not email or not user_vehicle_id:
            abort(400, description='The token, email and user vehicle id are required')

        if not vehicle_exists(user_vehicle_id):
            abort(400, description='The vehicle does not exist')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        r.expire(email, 600)

        if not conn:
            abort(503, description='There is no connection to the database')

        sql_query = """SELECT user_id, vehicle_id, size_id FROM user_vehicle WHERE user_vehicle_id = '{0}'""".format(user_vehicle_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()

        user_id_db, vehicle_id_db, size_id_db = res_

        if user_id_db != get_user_id(email):
            abort(403, description='It is not your vehicle! Somebody call the police!')

        vehicle_name_db = get_value_from_table('vehicle_name', 'vehicle', 'vehicle_id', vehicle_id_db)
        size_name_db = str(get_value_from_table('size_name', 'sizes', 'size_id', size_id_db))

        if (not new_vehicle_name and not new_size_name) or \
                (new_vehicle_name == vehicle_name_db and new_size_name == size_name_db):
            abort(400, description='Ok. Nothing needs to be changed :)')

        if not new_vehicle_name or new_vehicle_name == vehicle_name_db:
            new_vehicle_id = vehicle_id_db
            new_vehicle_name = 'The vehicle name has not been changed'
        else:
            new_vehicle_id = get_value_from_table('vehicle_id', 'vehicle','vehicle_name', new_vehicle_name)
            if not new_vehicle_id:
                abort(400, description='Unknown vehicle_name')

        if not new_size_name or new_size_name == size_name_db:
            new_size_id = size_id_db
            new_size_name = 'The size name has not been changed'
        else:
            new_size_id = get_value_from_table('size_id', 'sizes', 'size_name', new_size_name)
            if not new_size_id:
                abort(400, description='Unknown size_name')

        sql_query = """UPDATE user_vehicle SET vehicle_id = '{0}', size_id = '{1}' 
                        WHERE user_vehicle_id = '{2}'""".format(new_vehicle_id, new_size_id, user_vehicle_id)
        cursor.execute(sql_query)
        conn.commit()

        result = {
            'vehicle_id': user_vehicle_id,
            'old_vehicle_name': vehicle_name_db,
            'new_vehicle_name': new_vehicle_name,
            'old_size_name': size_name_db,
            'new_size_name': new_size_name
        }

        return jsonify(result)
    elif request.method == 'DELETE':
        email = request.form.get('email')
        token = request.form.get('token')
        user_vehicle_id = request.form.get('user_vehicle_id')

        if not token or not email or not user_vehicle_id:
            abort(400, description='The token, email and user_vehicle_id are required')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        r.expire(email, 600)

        if not conn:
            abort(503, description='There is no connection to the database')

        if not vehicle_exists(user_vehicle_id):
            abort(400, description='The vehicle does not exist')

        user_id = get_value_from_table('user_id', 'user_vehicle','user_vehicle_id', user_vehicle_id)

        if get_user_id(email) != user_id:
            abort(403, description='It is not your vehicle! Somebody call the police!')
        else:

            sql_query = """DELETE FROM user_vehicle WHERE user_vehicle_id = '{0}'""".format(user_vehicle_id)
            cursor.execute(sql_query)
            conn.commit()

            result = {
                'confirmation': 'User vehicle ID ' + user_vehicle_id + ' has been deleted'
            }
            return jsonify(result)
    else:
        abort(405)


@app.route("/warehouse", methods=['GET'])  # shows shelves in the warehouse (availability depends on the request params)
def active_storage():
    if request.method == 'GET':
        size_name = request.args.get('size_name')
        active_only = request.args.get('active_only')

        # if size_name is None - show all sizes
        # if active_only.lower() = 'yes' - show only free shelves
        # if active_only.lower() = 'no' - show only occupied shelves
        # if active_only.lower() != 'yes' and != 'no' - show all free shelves
        if not active_only:
            active_only = 'undefined'

        if not conn:
            abort(503, description='There is no connection to the database')

        if not size_name:
            if active_only.lower() == 'yes':

                sql_query = """SELECT shelf_id, size_id, active FROM warehouse 
                                WHERE active = 'True'"""
                cursor.execute(sql_query)
                conn.commit()
                res_ = cursor.fetchall()

            elif active_only.lower() == 'no':

                sql_query = """SELECT shelf_id, size_id, active FROM warehouse 
                                                WHERE active = 'False'"""
                cursor.execute(sql_query)
                conn.commit()
                res_ = cursor.fetchall()

            else:

                sql_query = """SELECT shelf_id, size_id, active FROM warehouse"""
                cursor.execute(sql_query)
                conn.commit()
                res_ = cursor.fetchall()

            if res_:
                result = []
                for i in res_:
                    result.append({
                        'shelf_id': i[0],
                        'size_id': i[1],
                        'size_name': get_value_from_table('size_name', 'sizes', 'size_id', i[1]),
                        'active': i[2]
                    })
            else:
                result = {
                    'confirmation': 'Unfortunately, we do not have active storage shelves you need'
                }
        else:
            size_id = get_value_from_table('size_id', 'sizes', 'size_name', size_name)

            if active_only.lower() == 'yes':

                sql_query = """SELECT shelf_id, size_id, active FROM warehouse WHERE active = 'True'
                                AND size_id = '{0}'""".format(size_id)
                cursor.execute(sql_query)
                conn.commit()
                res_ = cursor.fetchall()

            elif active_only.lower() == 'no':

                sql_query = """SELECT shelf_id, size_id, active FROM warehouse WHERE active = 'False'
                                                AND size_id = '{0}'""".format(size_id)
                cursor.execute(sql_query)
                conn.commit()
                res_ = cursor.fetchall()

            else:

                sql_query = """SELECT shelf_id, size_id, active FROM warehouse 
                                WHERE size_id = '{0}'""".format(size_id)
                cursor.execute(sql_query)
                conn.commit()
                res_ = cursor.fetchall()

            if res_:
                result = []
                for i in res_:
                    result.append({
                        'shelf_id': i[0],
                        'size_id': i[1],
                        'size_name': size_name,
                        'active': i[2]
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
        user_vehicle_id = request.form.get('user_vehicle_id')

        if not token or not email or not start_date or not stop_date:
            abort(400, description='The token, email, start_date, stop_date and size_name data are required')

        if (not size_name and not user_vehicle_id) or (size_name and user_vehicle_id):
            abort(400, description='The size_name OR user_vehicle_id is required')

        if start_date < str(datetime.datetime.now()):
            abort(400, description='The start_date can not be less than today')

        if stop_date > str(date(datetime.datetime.now().year + 2, datetime.datetime.now().month,
                                datetime.datetime.now().day)):
            abort(400, description='The stop_date can not exceed +2 year from today')

        if start_date > stop_date:
            abort(400, description='The start date can not be greater than the stop date')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        r.expire(email, 600)

        if not conn:
            abort(503, description='There is no connection to the database')

        user_id = get_user_id(email)

        if user_vehicle_id:
            if get_value_from_table('user_id', 'user_vehicle', 'user_vehicle_id', user_vehicle_id) != user_id:
                abort(403, description='It is not your vehicle! Somebody call the police!')
            size_name = get_value_from_table('size_name', 'sizes', 'size_id',
                                get_value_from_table('size_id', 'user_vehicle','user_vehicle_id', user_vehicle_id))

        size_id = get_value_from_table('size_id', 'sizes', 'size_name', size_name)

        #set the storage order cost 1000, the calculation will be implemented after some time. May be....
        storage_order_cost = 1000

        shelf_id = 0
        # Проверяем, вдруг есть полка нужного размера вообще без заказов
        sql_query = """SELECT w.shelf_id FROM storage_orders RIGHT JOIN warehouse AS w USING(shelf_id) WHERE
                        storage_order_id IS NULL AND w.size_id = {0}""".format(size_id)
        cursor.execute(sql_query)
        res = cursor.fetchall()

        # Если есть:
        if res:
            # Если таких несколько, выбираем меньшую по ИД
            shelf_id = min(res)

            # create storage order
            sql_query = """INSERT INTO storage_orders (user_id, start_date, stop_date, size_id, shelf_id, 
                                            storage_order_cost) VALUES('{0}', '{1}', '{2}', '{3}', '{4}', '{5}');""". \
                format(user_id, start_date, stop_date, size_id, shelf_id, storage_order_cost)
            cursor.execute(sql_query)
            conn.commit()

        # Если нет, проверить что даты не пересекаются с существующими:
        else:
                # Запрос на полки, у которых нет пересечений по датам
            sql_query = """WITH dates_intersection AS (
                            SELECT DISTINCT shelf_id FROM storage_orders WHERE 
                                (
                                    start_date BETWEEN '{0}' AND '{1}'
                                    OR
                                    stop_date BETWEEN '{0}' AND '{1}'
                                    OR
                                    '{0}' BETWEEN start_date AND stop_date 
                                    OR
                                    '{1}' BETWEEN start_date AND stop_date
                                )	
                            AND size_id = {2})
    
                            SELECT shelf_id FROM storage_orders WHERE shelf_id NOT IN 
                            (SELECT shelf_id FROM dates_intersection) AND size_id = {2}""".\
                            format(start_date, stop_date, size_id)
            cursor.execute(sql_query)
            res_ = cursor.fetchall()

            # Если есть, то записываем заказ на нее
            if res_:
                # Если таких несколько, выбираем меньшую по ИД
                shelf_id = min(res_)

                # create storage order
                sql_query = """INSERT INTO storage_orders (user_id, start_date, stop_date, size_id, shelf_id, 
                                    storage_order_cost) VALUES('{0}', '{1}', '{2}', '{3}', '{4}', '{5}');""". \
                    format(user_id, start_date, stop_date, size_id, shelf_id, storage_order_cost)
                cursor.execute(sql_query)
                conn.commit()

            else:
                # Если пересекаются, отправляем контакты менеджера
                # Внедрить: рекомендации по ближайшим свободным датам
                abort(400, description='We do not have storage place on the dates you need')
                # Если незанятых полок нужного размера нет, сверяем даты
                # Выбираем полки с необходимым размером и минимальной дельтой от необходимых дат
                # предоставляем информацию о дельтах дат и перенаправляем на ресепшн

        if shelf_id == 0:
            abort(400, description='Shef_id is undefined')
        # get the new storage order id
        sql_query = """SELECT storage_order_id FROM storage_orders WHERE 
                            shelf_id = '{0}' AND
                            start_date = '{1}' AND
                            stop_date = '{2}' AND
                            user_id = '{3}';""".format(shelf_id, start_date, stop_date, user_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()

        new_storage_order_id = res_[0]

        result = {
            'storage order id': new_storage_order_id,
            'shelf_id': shelf_id,
            'start_date': start_date,
            'stop_date': stop_date,
            'storage_order_cost': storage_order_cost
        }
        return jsonify(result)
    elif request.method == 'PUT':
        return 'Temporarily closed for maintenance'
#======================================================================================================================
#                                           ON MAINTENANCE
#======================================================================================================================

        # storage_order_id = request.form.get('storage_order_id')
        # token = request.form.get('token')
        # email = request.form.get('email')
        # start_date = request.form.get('start_date')
        # stop_date = request.form.get('stop_date')
        # storage_order_cost = request.form.get('storage_order_cost')
        # size_name = request.form.get('size_name')
        #
        # if not token or not email or not storage_order_id:
        #     abort(400, description='The token, email, storage_order_id data are required')
        #
        # user_auth = user_authorization(email, token)
        # if not user_auth['result']:
        #     abort(401, description=user_auth['text'])
        #
        # r.expire(email, 600)
        #
        # if not conn:
        #     abort(503, description='There is no connection to the database')
        #
        # if not storage_order_exists(storage_order_id):
        #     abort(400, description='The storage order does not exists')
        #
        # # get the initial data of the storage order
        # sql_query = """SELECT start_date, stop_date, size_id, storage_order_cost, shelf_id, user_id
        #                 FROM storage_orders WHERE storage_order_id = '{0}';""".format(storage_order_id)
        # cursor.execute(sql_query)
        # conn.commit()
        # res_ = cursor.fetchone()
        #
        # start_date_db, stop_date_db, size_id_db, storage_order_cost_db, shelf_id_db, user_id_db, shelf_id = \
        #     res_[0], res_[1], res_[2], res_[3], res_[4], res_[5], 0
        #
        # # verify, that the storage order is created by user
        # if get_user_id(email) != user_id_db:
        #     abort(403, description='Ouch! This is not your storage order!')
        #
        # # what data should be changed
        # # check dates
        # if start_date and stop_date:
        #     if start_date > stop_date:
        #         abort(400, description='The start date can not be greater than the stop date')
        #     if stop_date < start_date:
        #         abort(400, description='The stop date can not be less than the start date')
        #
        # if start_date and not stop_date:
        #     if datetime.datetime.strptime(start_date, '%Y-%m-%d') > datetime.datetime.strptime(str(stop_date_db), '%Y-%m-%d'):
        #         abort(400, description='The start date can not be greater than the stop date')
        #
        # if not start_date and stop_date:
        #     if datetime.datetime.strptime(stop_date, '%Y-%m-%d') < datetime.datetime.strptime(str(start_date_db), '%Y-%m-%d'):
        #         abort(400, description='The stop date can not be less than the start date')
        #
        # if not start_date:
        #     start_date = start_date_db
        # if not stop_date:
        #     stop_date = stop_date_db
        # if not storage_order_cost:
        #     storage_order_cost = storage_order_cost_db
        # if not size_name:
        #     size_id = size_id_db
        # else:
        #     # if the tire size data needs to be changed
        #     size_id = get_value_from_table('size_id', 'sizes', 'size_name', size_name)
        #     if int(size_id) != size_id_db:
        #         sql_query = """SELECT MIN(shelf_id) FROM warehouse WHERE available = 'True'
        #                         AND size_id = '{0}';""".format(size_id)
        #         cursor.execute(sql_query)
        #         conn.commit()
        #         shelf_avail_ = cursor.fetchone()
        #
        #         # if there is available storage
        #         if shelf_avail:
        #             shelf_id = shelf_avail_[0]
        #
        #             # update changed storage places
        #             sql_query = """UPDATE warehouse SET available = 'True'
        #                             WHERE shelf_id = '{0}';""".format(shelf_id_db)
        #             cursor.execute(sql_query)
        #             conn.commit()
        #
        #             sql_query = """UPDATE warehouse SET available = 'False'
        #                             WHERE shelf_id = '{0}';""".format(shelf_id)
        #             cursor.execute(sql_query)
        #             conn.commit()
        #
        #         else:
        #             abort(400, description='Sorry, we do not have the storage you need')
        #
        # if shelf_id == 0:
        #     shelf_id = shelf_id_db
        #
        # # update data in the DB
        #
        # sql_query = """UPDATE storage_orders SET start_date = '{0}', stop_date = '{1}', size_id = '{2}',
        #             storage_order_cost = '{3}', shelf_id = '{4}' WHERE storage_order_id = '{5}';""".\
        #             format(start_date, stop_date, size_id, storage_order_cost, shelf_id, storage_order_id)
        # cursor.execute(sql_query)
        # conn.commit()
        #
        # result = {
        #     'storage_order': storage_order_id,
        #     'new_start_date': start_date,
        #     'new_stop_date': stop_date,
        #     'new_size_id': size_id,
        #     'old_size_id': size_id_db,
        #     'storage_order_cost': storage_order_cost,
        #     'new_shelf_id': shelf_id,
        #     'old_shelf_id': shelf_id_db
        # }
        #
        # return jsonify(result)
    elif request.method == 'DELETE':
        email = request.form.get('email')
        token = request.form.get('token')
        storage_order_id = request.form.get('storage_order_id')

        if not token or not email or not storage_order_id:
            abort(400, description='The token, email and storage_order_id are required')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        r.expire(email, 600)

        if not conn:
            abort(503, description='There is no connection to the database')

        if not storage_order_exists(storage_order_id):
            abort(400, description='The storage order does not exist')

        sql_query = """SELECT user_id, shelf_id FROM storage_orders 
                                    WHERE storage_order_id = '{0}'""".format(storage_order_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()

        user_id, shelf_id = res_

        if get_user_id(email) != user_id:
            abort(403, description='It is not your storage order!')

        sql_query = """DELETE FROM storage_orders WHERE storage_order_id = '{0}'""".format(storage_order_id)
        cursor.execute(sql_query)
        conn.commit()

        result = {
            'confirmation': 'Storage order ID ' + storage_order_id + ' has been deleted'
        }
        return jsonify(result)
    else:
        abort(405)


@app.route("/tire_service_order", methods=['POST', 'PUT', 'DELETE'])  # add new/change/delete the user's service order
def tire_service_order():
    if request.method == 'POST':
        email = request.form.get('email')
        token = request.form.get('token')
        order_type = request.form.get('order_type')
        order_date_str = request.form.get('order_date')
        user_vehicle_id = request.form.get('user_vehicle_id')
        numbers_of_wheels = request.form.get('numbers_of_wheels')
        removing_installing_wheels = request.form.get('removing_installing_wheels')
        tubeless = request.form.get('tubeless')
        balancing = request.form.get('balancing')
        wheel_alignment = request.form.get('wheel_alignment')

        if not token or not email or not order_date_str or not user_vehicle_id or not order_type\
                    or not numbers_of_wheels or not removing_installing_wheels \
                    or not tubeless or not balancing or not wheel_alignment:
            abort(400, description='All fields are required')

        if order_type != 'tire change' and order_type != 'tire repair':
            abort(400, description='The order_type must be <tire change> or <tire repair>')

        if not user_vehicle_id.isdigit() or not numbers_of_wheels.isdigit():
            return 'The <user_vehicle_id> and <numbers_of_wheels> should be int'

        order_date = datetime.datetime.strptime(order_date_str, '%y-%m-%d %H:%M')
        if type(order_date) is not datetime.datetime:
            return 'The <order_date> should be in YYYY-MM-DD HH-MM format'

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        r.expire(email, 600)

        if not conn:
            abort(503, description='There is no connection to the database')

        sql_query = """SELECT user_id, vehicle_id, size_id FROM user_vehicle 
                                            WHERE user_vehicle_id = '{0}';""".format(user_vehicle_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()

        user_id, vehicle_id, size_id = res_

        if get_user_id(email) != user_id:
            abort(403, description='It is not your vehicle!')

        if order_type == 'tire change':

            tire_change = 'tire_change'
            if removing_installing_wheels.lower() == 'yes':
                removing_installing_wheels = 'wheel_removal_installation'
            if balancing.lower() == 'yes':
                balancing = 'wheel_balancing'
            if wheel_alignment.lower() == 'yes':
                wheel_alignment = 'wheel_alignment'

            sql_query = """select sum
                            (
                                case 
                                    when task_name = '{0}' then task_duration 
                                    when task_name = '{1}' then task_duration 
                                    when task_name = '{2}' then task_duration 
                                    when task_name = '{3}' then task_duration 
                                    else '00:00:00'
                                end
                            ) as duration
                            from tasks""".format(tire_change, removing_installing_wheels, balancing, wheel_alignment)
            cursor.execute(sql_query)
            conn.commit()
            res_ = cursor.fetchone()
            service_duration = int(numbers_of_wheels) * res_[0]
            # return('Service duration: ' + str(service_duration) + str(type(vehicle_id)))










    elif request.method == 'PUT':
        email = request.form.get('email')
        token = request.form.get('token')
        service_order_id = request.form.get('service order id')
        new_order_date = request.form.get('new order date')
        new_user_vehicle_id = request.form.get('new user vehicle id')

        if not token or not email or not service_order_id:
            abort(400, description='The token, email, service order id are required')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        r.expire(email, 600)

        if not conn:
            abort(503, description='There is no connection to the database')

        if not tire_service_order_exists(service_order_id):
            abort(400, description='The tire service order does not exist')

        # get the initial data about the tire_service_order
        sql_query = """SELECT user_id, user_vehicle_id, service_order_date FROM tire_service_order 
                                                WHERE service_order_id = '{0}';""".format(service_order_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()

        user_id_order, user_vehicle_id_db, service_order_date_db = res_
        user_id = get_user_id(email)

        if user_id_order != user_id:
            abort(403, description='It is not your tire service order!')

        if (new_order_date is None and new_user_vehicle_id is None) or \
                (new_order_date == service_order_date_db and new_user_vehicle_id == user_vehicle_id_db):
            abort(400, description='Ok. Nothing needs to be changed :)')

        if not new_order_date or new_order_date == service_order_date_db:
            order_date_to_db = service_order_date_db
            new_order_date = 'The tire service date has not been changed'
        else:
            if datetime.datetime.strptime(new_order_date[:10], '%Y-%m-%d') < \
                    datetime.datetime.strptime(str(datetime.datetime.now())[:10], '%Y-%m-%d'):
                abort(400, description='The new tire service date can not be earlier than today')
            order_date_to_db = new_order_date

        if not new_user_vehicle_id or new_user_vehicle_id == user_vehicle_id_db:
            user_vehicle_id_to_db = user_vehicle_id_db
            new_user_vehicle_id = 'The vehicle id has not been changed'
        else:
            user_id_vehicle = get_value_from_table('user_id', 'user_vehicle', 'user_vehicle_id', new_user_vehicle_id)
            if user_id_vehicle != user_id:
                abort(403, description='It is not your vehicle! Somebody call the police!')
            user_vehicle_id_to_db = new_user_vehicle_id

        sql_query = """UPDATE tire_service_order SET service_order_date = '{0}', user_vehicle_id = '{1}'
                    WHERE service_order_id = '{2}'""".format(order_date_to_db, user_vehicle_id_to_db, service_order_id)
        cursor.execute(sql_query)
        conn.commit()

        result = {
            'tire service order': service_order_id,
            'old_vehicle_id': user_vehicle_id_db,
            'new_vehicle_id': new_user_vehicle_id,
            'old_order_date': service_order_date_db,
            'new_order_date': new_order_date
        }

        return jsonify(result)
    elif request.method == 'DELETE':
        email = request.form.get('email')
        token = request.form.get('token')
        service_order_id = request.form.get('service_order_id')

        if not token or not email or not service_order_id:
            abort(400, description='The token, email, service_order_id are required')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        r.expire(email, 600)

        if not conn:
            abort(503, description='There is no connection to the database')

        if not tire_service_order_exists(service_order_id):
            abort(400, description='The tire service order does not exist')

        # get the initial data about the tire_service_order
        sql_query = """SELECT user_id, user_vehicle_id, manager_id FROM tire_service_order 
                                        WHERE service_order_id = '{0}';""".format(service_order_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()

        user_id, user_vehicle_id, manager_id = res_

        if get_user_id(email) != user_id:
            abort(403, description='It is not your tire service order!')

        sql_query = """DELETE FROM tire_service_order WHERE service_order_id = '{0}'""".format(service_order_id)
        cursor.execute(sql_query)
        conn.commit()

        text = 'Tire service order ID {{ name }} has been deleted'
        template = Template(text)

        result = {
            "confirmation": template.render(name=service_order_id),
        }

        return jsonify(result)
    else:
        abort(405)


@app.route("/tire_service_order/task", methods=['GET', 'POST', 'DELETE']) # add new/change/delete a task to the user's service order
def task():
    if request.method == 'GET':
        pass
    # add a task to the list_of_works
    elif request.method == 'POST':
        email = request.form.get('email')
        token = request.form.get('token')
        service_order_id = request.form.get('service_order_id')
        task_name = request.form.get('task_name')
        numbers_of_task = request.form.get('numbers_of_tasks')

        if not token or not email or not service_order_id or not task_name or not numbers_of_task:
            abort(400, description='The token, email, service_order_id and task_name are required')

        if not str(numbers_of_task).isdigit() or not str(service_order_id).isdigit():
            abort(400, description='Please, provide a numbers of tasks and service_order_id in digits')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        r.expire(email, 600)

        if not conn:
            abort(503, description='There is no connection to the database')

        sql_query = """SELECT user_id FROM tire_service_order WHERE service_order_id = '{0}';""".format(service_order_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()

        if get_user_id(email) != res_[0]:
            abort(403, description='It is not your tire service order!')

        sql_query = """SELECT task_id FROM tasks WHERE task_name = '{0}';""".format(task_name)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()

        if not res_:
            abort(400, description='Sorry, we do not offer this service')

        task_id = res_[0]

        for _ in range(int(numbers_of_task)):

            sql_query = """INSERT INTO list_of_works (service_order_id, task_id)
                            VALUES ('{0}', '{1}');""".format(service_order_id, task_id)
            cursor.execute(sql_query)
            conn.commit()

        if int(numbers_of_task) == 1:
            result = {
                'confirmation': 'The ' + task_name + ' task is successfully added to your tire_service_order ID ' \
                                + service_order_id
            }
        else:
            result = {
                'confirmation': 'tasks for ' + task_name + ' in the amount of ' + numbers_of_task + \
                     ' have been successfully added to your tire_service_order ID ' + service_order_id
            }

        return jsonify(result)
    elif request.method == 'DELETE':
        email = request.form.get('email')
        token = request.form.get('token')
        service_order_id = request.form.get('service_order_id')
        task_number = request.form.get('task_number')

        if not token or not email or not service_order_id:
            abort(400, description='The token, email, service_order_id are required')

        if not str(service_order_id).isdigit():
            abort(400, description='Please, provide the service_order_id in digits')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        r.expire(email, 600)

        if not conn:
            abort(503, description='There is no connection to the database')

        sql_query = """SELECT user_id FROM tire_service_order WHERE service_order_id = '{0}';""".format(service_order_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()

        if get_user_id(email) != res_[0]:
            abort(403, description='It is not your tire service order!')

        if not task_number:

            sql_query = """SELECT task_name, task_duration, task_cost, s.first_name, s.last_name, 
                        m.first_name, m.last_name, work_id 
                        FROM list_of_works 
                        JOIN tasks USING (task_id) 
                        JOIN staff as s USING (worker_id)
                        JOIN tire_service_order USING (service_order_id)
                        JOIN managers as m USING (manager_id)
                        WHERE service_order_id  = {0}""".format(service_order_id)
            cursor.execute(sql_query)
            conn.commit()
            res = cursor.fetchall()

            result = {}
            for i in res:
                name = 'task № ' + str(i[7])
                result[name] = {
                    'task name': i[0],
                    'task duration': str(i[1]),
                    'task cost': i[2],
                    'worker first name': i[3],
                    'worker last name': i[4],
                    'manager first name': i[5],
                    'manager last name': i[6]
                }
            return jsonify(result)

        else:

            if not str(task_number).isdigit():
                abort(400, description='Please, provide the task_number in digits')

            sql_query = """SELECT work_id FROM list_of_works WHERE service_order_id = {0}""".format(service_order_id)
            cursor.execute(sql_query)
            res = cursor.fetchall()

            flag = False
            for i in res:
                if int(task_number) == i[0]:
                    flag = True
                    break

            if not flag:
                abort(400, description='Incorrect task number')

            sql_query = """DELETE FROM list_of_works WHERE work_id = {0}""". format(task_number)
            cursor.execute(sql_query)
            conn.commit()

            text = 'The task number {{ name }} has been deleted'
            template = Template(text)

            result = {
                "confirmation": template.render(name=task_number),
            }
            return jsonify(result)
    else:
        abort(405)


@app.route("/admin/push_user_auth", methods=['POST'])
def push():
    if request.method == 'POST':
        admin_password = request.form.get('admin password')
        if admin_password == 'push':
            push_user_auth()

if __name__ == '__main__':
    app.run()
