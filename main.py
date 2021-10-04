import random
from flask import Flask, json, request, jsonify, abort
from jinja2 import Template
import psycopg2
import uuid
import re
import redis
import datetime
from flask_swagger_ui import get_swaggerui_blueprint

app = Flask(__name__)

SWAGGER_URL = '/swagger'
API_URL = '/static/swagger.yaml'
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={'app_name':"Seans-Python-Flask-REST-Boilerpate"}
)

app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

#log

r = redis.StrictRedis(host='localhost', port=6379, db=0, charset="utf-8", decode_responses=True)
conn = psycopg2.connect(dbname='user_20_db', user='user_20', password='123', host='159.69.151.133', port='5056')
cursor = conn.cursor()



def user_exist(email):
    if conn:
        sql_query = "SELECT user_id FROM users WHERE email = '{0}'".format(email)
        cursor.execute(sql_query)
        conn.commit()
        usr_id_ = cursor.fetchone()
        # cursor.close()

        if usr_id_ is None:
            return False
    return True


def get_user_id(email):
    if conn:
        sql_query = "SELECT user_id FROM users WHERE email = '{0}'".format(email)
        cursor.execute(sql_query)
        conn.commit()
        usr_id_ = cursor.fetchone()
        # cursor.close()        

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
        size_id_ = cursor.fetchone()
        # cursor.close()

        if size_id_ is None:
            return None
        return size_id_[0]   


def shelf_avail(size_name):
    if conn:
        sql_query = """SELECT shelf_id FROM warehouse WHERE size_id = '{0}' 
                        AND available = 'True'""".format(size_id_by_name(size_name))
        cursor.execute(sql_query)
        conn.commit()
        avail = cursor.fetchone()
        # cursor.close()

        if avail is not None:
            return True
    return False 


def shelf_id_by_size(size_name):
    if conn:
        sql_query = """SELECT MIN(shelf_id) FROM warehouse WHERE size_id = '{0}' 
                        AND available = 'True'""".format(size_id_by_name(size_name))
        cursor.execute(sql_query)
        conn.commit()
        shelf_id_ = cursor.fetchone()
        # cursor.close()

        return shelf_id_[0]


def validate_password(password):
    special_sym = ['$', '@', '#', '!', '%']
    return_val = {'result': True, 'text': ''}
    if len(password) < 8:
        return_val['text'] = 'The password must be at least 8 characters long'
        return_val['result'] = False
    if len(password) > 32:
        return_val['text'] = 'the password length should not exceed 32 chars'
        return_val['result'] = False
    if not any(char.isdigit() for char in password):
        return_val['text'] = 'The password must contain at least one digit'
        return_val['result'] = False
    if not any(char.isupper() for char in password):
        return_val['text'] = 'The password must contain at least one uppercase letter'
        return_val['result'] = False
    if not any(char.islower() for char in password):
        return_val['text'] = 'The password must contain at least one lowercase letter'
        return_val['result'] = False
    if not any(char in special_sym for char in password):
        return_val['text'] = 'The password must contain at least one of the symbols $@#!%'
        return_val['result'] = False
    return return_val


def validate_email(email):
    return_val = {'result': True, 'text': ''}
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return_val['result'] = False
        return_val['text'] = 'The email must contain @ and . chars'
    return return_val


def user_active(email):
    if conn:
        sql_query = """SELECT active FROM users WHERE email = '{0}'""".format(email)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        # cursor.close()

        if res_[0]:
            return True
        return False


def size_name_by_id(size_id):
    if conn:
        sql_query = """SELECT size_name FROM sizes WHERE size_id = '{0}'""".format(size_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        # cursor.close()

        if res_ is None:
            return None
        return res_[0]


def vehicle_name_by_id(vehicle_id):
    if conn:
        sql_query = """SELECT vehicle_name FROM vehicle WHERE vehicle_id = '{0}'""".format(vehicle_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        # cursor.close()

        if res_ is None:
            return None
        return res_[0]


def vehicle_id_by_name(vehicle_name):
    if conn:
        sql_query = """SELECT vehicle_id FROM vehicle WHERE vehicle_name = '{0}'""".format(vehicle_name)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        # cursor.close()

        if res_ is None:
            return None
        return res_[0]


def vehicle_one_by_var(select, where, what):
    if conn:
        sql_query = """SELECT '{0}' FROM vehicle WHERE '{1}' = '{2}'""".format(select, where, what)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        # cursor.close()

        if res_ is None:
            return None
        return res_[0]


def user_authorization(email, token):
    return_val = {'result': True, 'text': ''}
    if not user_exist(email):
        return_val['result'] = False
        return_val['text'] = 'The user does not exist. Please, register'
    else:
        if not token_exist(email, token):
            return_val['result'] = False
            return_val['text'] = 'The token is invalid, please log in'
    return return_val


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


@app.route("/reg", methods=['POST'])  # reg new user
def reg():
    if request.method == 'POST':
        f_name = request.form.get('first_name')
        l_name = request.form.get('last_name')
        password = request.form.get('password')
        phone = request.form.get('phone')
        email = request.form.get('email')

        if f_name is None or l_name is None or password is None or phone is None or email is None:
            abort(400, description='The f_name, l_name, password, phone and email data are required')

        if user_exist(email):
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
            return 'Sorry, there is no connection to the database'

        sql_query = """INSERT INTO users (first_name, last_name, pass, phone, email,active) VALUES ('{0}', 
                    '{1}', '{2}', '{3}', '{4}', {5})""".format(f_name, l_name, password, phone, email, active)
        cursor.execute(sql_query)
        conn.commit()
        # cursor.close()

        sql_query = """SELECT user_id FROM users WHERE email = '{0}'""".format(email)
        cursor.execute(sql_query)
        res = cursor.fetchone()
        conn.commit()
        # cursor.close()

        result = {
            "ID": res[0],
            "f_name": f_name,
            "l_name": l_name,
            "phone": phone,
            "password": password,
            "active": active
        }

        return jsonify(result)
    else:
        abort(405)


@app.route("/cl", methods=['POST'])  # clear users DB
def cl():
    if request.method == 'POST':
        password = request.form.get('password')
    
        if password == 'He_He_Boy!':
            if not conn:
                return 'Sorry, there is no connection to the database'

            sql_query = "DELETE FROM users"
            cursor.execute(sql_query)
            conn.commit()
            # cursor.close()

            return 'All users have been deleted'
        else:
            return 'Check your password!'
    else:
        abort(405)


@app.route("/all", methods=['GET'])  # get a list of all users
def show_all_users():
    if request.method == 'GET':
        user_id = request.args.get('user_id')
        if not conn:
            return 'Sorry, there is no connection to the database'

        result = {}
        if user_id is None:
            sql_query = "SELECT user_id, first_name, last_name, phone, email, pass, active FROM users"
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
                        "password": res[i][5],
                        "active": res[i][6]
                    })
            else:
                result = {
                    'confirmation': 'There are no users in the DB'
                }
        else:
            if not str(user_id).isdigit():
                abort(400, description='The user_id must contain only digits')
            sql_query = """SELECT user_id, first_name, last_name, phone, email, pass, active FROM users
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
                    "password": res[5],
                    "active": res[6]
                })
            else:
                result = {
                    'confirmation': 'There is no user ID ' + user_id + ' in the DB'
                }
        return jsonify(result)
    else:
        error(405)


@app.route("/login", methods=['POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if password is None or email is None:
            abort(400, description='The pass and email data are required')

        if not user_exist(email):
            abort(400, description="The user does not exist. Please, register")

        if not user_active(email):
            abort(400, description='User is deactivated')

        if not conn:
            return 'Sorry, there is no connection to the database'

        sql_query = "SELECT pass, user_id, first_name, last_name FROM users WHERE email = '{0}'".format(email)
        cursor.execute(sql_query)
        conn.commit()
        res = cursor.fetchone()
        # cursor.close()

        if password == res[0]:  # если пароль верен
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


@app.route("/user_info", methods=['POST'])  # get all info about the logged user
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
            return 'Sorry, there is no connection to the database'

        # collecting the user's personal data from the users db
        sql_query = """SELECT user_id, first_name, last_name, email, phone, pass 
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
                            "phone": res[4],
                            "password": res[5]
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
            result_order = 'There are no orders for storage from the user'
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
            result_vehicle = 'The user does not have a vehicle. BUT! If the user wants to get a vehicle, ' \
                             'call 8-800-THIS-IS-NOT-A-SCAM right now!'
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
            result_tire_service_order = 'You do not have a tire service order(s).'
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


@app.route("/new_storage_order", methods=['POST'])
def new_st_ord():
    if request.method == 'POST':
        token = request.form.get('token')
        email = request.form.get('email')
        start_date = request.form.get('start_date')
        stop_date = request.form.get('stop_date')
        size_name = request.form.get('size_name')

        if token is None or email is None or start_date is None or stop_date is None or size_name is None:
            abort(400, description='The token, email, start_date, stop_date and size_name data are required')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        # is there the necessary free storage space
        if not shelf_avail(size_name):
            abort(400, description="Sorry, we do not have the storage you need")

        shelf_id = shelf_id_by_size(size_name)

        if not conn:
            return 'Sorry, there is no connection to the database'

        size_id_by = size_id_by_name(size_name)
        if size_id_by is None:
            abort(400, description='Unknown size_name')

        # create storage order
        sql_query = """INSERT INTO storage_orders (user_id, start_date, stop_date, size_id, shelf_id, 
                    st_ord_cost) VALUES('{0}', '{1}', '{2}', '{3}', '{4}', '{5}');""".\
                    format(get_user_id(email), start_date, stop_date, size_id_by, shelf_id, 1000)
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
    else:
        abort(405)


@app.route("/change_storage_order", methods=['PUT'])
def change_storage_order():
    if request.method == 'PUT':
        st_ord_id = request.form.get('st_ord_id')
        token = request.form.get('token')
        email = request.form.get('email')
        start_date = request.form.get('start_date')
        stop_date = request.form.get('stop_date')
        st_ord_cost = request.form.get('st_ord_cost')
        size_id = request.form.get('size_id')

        if token is None or email is None or st_ord_id is None:
            abort(400, description='The token, email, st_ord_id data are required')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        if not conn:
            return 'Sorry, there is no connection to the database'

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
    else:
        abort(405)


@app.route("/change_user_info", methods=['PUT'])
def change_user_info():
    if request.method == 'PUT':
        token = request.form.get('token')
        email = request.form.get('email')
        f_name = request.form.get('f_name')
        l_name = request.form.get('l_name')
        phone = request.form.get('phone')
        new_email = request.form.get('new_email')
        password = request.form.get('password')

        if token is None or email is None:
            abort(400, description='The token, email are required')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        if f_name is None and l_name is None and phone is None and new_email is None and password is None:
            abort(400, description='Ok. Nothing needs to be changed :)')

        if not conn:
            return 'Sorry, there is no connection to the database'

        # get the initial data of the storage order
        sql_query = """SELECT user_id, first_name, last_name, phone, pass 
                        FROM users WHERE email = '{0}';""".format(email)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        # cursor.close()

        user_id_db, f_name_db, l_name_db, phone_db, password_db = res_[0], res_[1], res_[2], res_[3], res_[4]

        flag_relogin = False
        # what data should be changed
        if f_name is None:
            f_name = f_name_db
        if l_name is None:
            l_name = l_name_db
        if phone is None:
            phone = phone_db
        if password is None:
            password = password_db
        else:
            check_password = validate_password(password)
            if not check_password['result']:
                abort(400, description=check_password['text'])
            flag_relogin = True
        if new_email is None:
            new_email = email
        else:
            check_email = validate_email(email)
            if not check_email['result']:
                abort(400, description=check_email['text'])
            flag_relogin = True

        # if the pass and/or email have been changed - the user must log in again
        if flag_relogin:
            r.delete(email)

        # update data in the DB
        sql_query = """UPDATE users SET first_name = '{0}', last_name = '{1}', email = '{2}', phone = '{3}', 
                    pass = '{4}' WHERE user_id = '{5}';""".format(f_name, l_name, new_email, phone, password, user_id_db)
        cursor.execute(sql_query)
        conn.commit()
        # cursor.close()

        result = {
            'user_id': user_id_db,
            'f_name_new': f_name,
            'f_name_old': f_name_db,
            'l_name_new': l_name,
            'l_name_old': l_name_db,
            'email_new': new_email,
            'email_old': email,
            'phone_new': phone,
            'phone_old': phone_db,
            'password_new': password,
            'password_old': password_db
        }

        return jsonify(result)
    else:
        abort(405)


@app.route("/new_user_vehicle", methods=['POST'])
def new_user_vehicle():
    if request.method == 'POST':
        token = request.form.get('token')
        email = request.form.get('email')
        vehicle_name = request.form.get('vehicle_name')
        size_name = request.form.get('size_name')

        if token is None or email is None or vehicle_name is None or size_name is None:
            abort(400, description='The token, email, vehicle_name and size_name data are required')

        # get needed data
        user_id = get_user_id(email)
        size_id = size_id_by_name(size_name)
        vehicle_id = vehicle_id_by_name(vehicle_name)

        if size_id is None:
            abort(400, description='Unknown tire size, add the tire size data to the sizes DB')

        if vehicle_id is None:
            abort(400, description='Unknown type of the vehicle, add the vehicle type data to the vehicle DB')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        if not conn:
            return 'Sorry, there is no connection to the database'

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
    else:
        abort(405)


@app.route("/delete_user", methods=['DELETE'])  # How dare you?
def delete_user():
    if request.method == 'DELETE':
        email = request.form.get('email')
        token = request.form.get('token')
        sure = request.form.get('ARE_YOU_SURE?')

        if token is None or email is None or sure is None:
            abort(400, description='The token, email and sure data are required')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        if sure != 'True':
            abort(400, description='АHA! Changed your mind?')

        if not conn:
            return 'Sorry, there is no connection to the database'

        sql_query = """SELECT first_name, last_name FROM users WHERE email = '{0}'""".format(email)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        # cursor.close()

        sql_query = """DELETE FROM users WHERE email = '{0}'""".format(email)
        cursor.execute(sql_query)
        conn.commit()
        # cursor.close()

        text = 'R.I.P {{ name }}, i will miss you :('
        template = Template(text)
        result = {
            'confirmation': template.render(name=res_[0] + ' ' + res_[1])
        }
        return jsonify(result)
    else:
        abort(405)


@app.route("/deactivate_user", methods=['POST'])
def deactivate_user():
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
        return 'Sorry, there is no connection to the database'

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


@app.route("/activate_user", methods=['POST'])
def activate_user():
    email = request.form.get('email')
    admin_password = request.form.get('admin_password')

    if admin_password is None or email is None:
        abort(400, description='The admin_password and email are required')

    if not user_exist(email):
        abort(400, description='The user is not exist')

    if admin_password != 'admin':
        abort(400, description='Wrong admin password!')

    if not conn:
        return 'Sorry, there is no connection to the database'

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


@app.route("/delete_user_vehicle", methods=['DELETE'])
def delete_user_vehicle():
    if request.method == 'DELETE':
        email = request.form.get('email')
        token = request.form.get('token')
        u_veh_id = request.form.get('user_vehicle_id')

        if token is None or email is None or u_veh_id is None:
            abort(400, description='The token, email and user_vehicle_id are required')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        if not conn:
            return 'Sorry, there is no connection to the database'

        sql_query = """SELECT user_id FROM user_vehicle WHERE u_veh_id = '{0}'""".format(u_veh_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        # cursor.close()

        if get_user_id(email) != res_[0]:
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


@app.route("/delete_storage_order", methods=['DELETE'])
def delete_storage_order():
    if request.method == 'DELETE':
        email = request.form.get('email')
        token = request.form.get('token')
        st_ord_id = request.form.get('storage_order_id')

        if token is None or email is None or st_ord_id is None:
            abort(400, description='The token, email and storage_order_id are required')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        if not conn:
            return 'Sorry, there is no connection to the database'

        sql_query = """SELECT user_id, shelf_id FROM storage_orders WHERE st_ord_id = '{0}'""".format(st_ord_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        # cursor.close()

        shelf_id = res_[1]

        if get_user_id(email) != res_[0]:
            abort(403, description='It is not your storage order! Somebody call the police!')

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


@app.route("/change_user_vehicle", methods=['PUT'])
def change_user_vehicle():
    if request.method == 'PUT':
        email = request.form.get('email')
        token = request.form.get('token')
        u_veh_id = request.form.get('user_vehicle_id')
        new_vehicle_name = request.form.get('new_vehicle_name')
        new_size_name = request.form.get('new_size_name')

        if token is None or email is None or u_veh_id is None:
            abort(400, description='The token, email and user_vehicle_id are required')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        if not conn:
            return 'Sorry, there is no connection to the database'

        sql_query = """SELECT user_id, vehicle_id, size_id FROM user_vehicle WHERE u_veh_id = '{0}'""".format(u_veh_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        # cursor.close()

        user_id_db, vehicle_id_db, size_id_db = res_[0], res_[1], res_[2]

        old_vehicle_name = vehicle_name_by_id(vehicle_id_db)
        old_size_name = str(size_name_by_id(size_id_db))

        if user_id_db != get_user_id(email):
            abort(403, description='It is not your vehicle! Somebody call the police!')

        if (new_vehicle_name is None and new_size_name is None) or \
                (new_vehicle_name == old_vehicle_name and new_size_name == old_size_name):
            abort(400, description='Ok. Nothing needs to be changed :)')

        # new_vehicle_id, new_size_id = 0, 0

        if new_vehicle_name is None:
            new_vehicle_id = vehicle_id_db
        else:
            vehicle_id_by = vehicle_id_by_name(new_vehicle_name)
            if vehicle_id_by is not None:
                new_vehicle_id = vehicle_id_by
            else:
                abort(400, description='Unknown vehicle_name')

        if new_size_name is None:
            new_size_id = size_id_db
        else:
            size_id_by = size_id_by_name(new_size_name)
            if size_id_by is not None:
                new_size_id = size_id_by
            else:
                abort(400, description='Unknown size_name')

        sql_query = """UPDATE user_vehicle SET vehicle_id = '{0}', size_id = '{1}' 
                        WHERE u_veh_id = '{2}'""".format(new_vehicle_id, new_size_id, u_veh_id)
        cursor.execute(sql_query)
        conn.commit()
        # cursor.close()

        result = {
            'vehicle_id': u_veh_id,
            'old_vehicle_name': old_vehicle_name,
            'new_vehicle_name': new_vehicle_name,
            'old_size_name': old_size_name,
            'new_size_name': new_size_name
        }

        return jsonify(result)
    else:
        abort(405)


@app.route("/available_storage", methods=['GET'])  # shows available free storage places in the warehouse
def available_storage():
    if request.method != 'GET':
        abort(405)

    size_id = int(request.args.get('size_id'))
    if not conn:
        return 'Sorry, there is no connection to the database'

    if size_id is None:
        sql_query = """SELECT shelf_id, size_id FROM warehouse WHERE available = 'True'"""
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchall()
        # cursor.close()

        if res_ is not None:
            result = []
            for i in range(len(res_)):
                result.append({
                    'shelf_id': res_[i][0],
                    'size_id': res_[i][1],
                    'size_name': size_name_by_id(res_[i][1])
                })
        else:
            result = {
                'confirmation': 'Unfortunately, we do not have available storage shelves'
            }
    else:
        sql_query = """SELECT shelf_id, size_id FROM warehouse WHERE available = 'True'
                        AND size_id = '{0}'""".format(size_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        # cursor.close()

        if res_ is not None:
            result = []
            result.append({
                'shelf_id': res_[0],
                'size_id': res_[1],
                'size_name': size_name_by_id(res_[1])
            })
        else:
            result = {
                'confirmation': 'Unfortunately, we do not have available storage shelf'
            }
    return jsonify(result)


@app.route("/create_tire_service_order", methods=['POST'])
def create_tire_service_order():
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
            return 'Sorry, there is no connection to the database'

        sql_query = """SELECT user_id, vehicle_id, size_id FROM user_vehicle 
                        WHERE u_veh_id = '{0}';""".format(u_veh_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        # cursor.close()

        user_id, vehicle_id, size_id = res_[0], res_[1], res_[2]

        if get_user_id(email) != user_id:
            abort(403, description='It is not your vehicle!')

        sql_query = """SELECT worker_id, COUNT(manager_id) FROM staff AS s LEFT JOIN tire_service_order AS tso
                        ON tso.manager_id = s.worker_id WHERE available = True AND position_id = 2
                        GROUP BY worker_id HAVING COUNT(manager_id) < 5"""
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchall()
        # cursor.close()

        if len(res_) == 0:
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

        sql_query = """SELECT first_name, last_name, phone, email FROM staff 
                        WHERE worker_id = '{0}'""".format(manager_id)
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
    else:
        abort(405)


@app.route("/delete_tire_service_order", methods=['DELETE'])
def delete_tire_service_order():
    if request.method == 'DELETE':
        email = request.form.get('email')
        token = request.form.get('token')
        serv_order_id = request.form.get('service_order_id')

        if token is None or email is None or serv_order_id is None:
            abort(400, description='The token, email, service_order_id are required')

        user_auth = user_authorization(email, token)
        if not user_auth['result']:
            abort(401, description=user_auth['text'])

        if not conn:
            return 'Sorry, there is no connection to the database'

        sql_query = """SELECT user_id, u_veh_id, manager_id FROM tire_service_order 
                        WHERE serv_order_id = '{0}';""".format(serv_order_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        # cursor.close()

        user_id, u_veh_id, manager_id = res_[0], res_[1], res_[2]

        if get_user_id(email) != user_id:
            abort(403, description='It is not your tire service order!')

        sql_query = """SELECT worker_id, COUNT(manager_id) FROM staff AS s JOIN tire_service_order AS tso
                    ON tso.manager_id = s.worker_id WHERE worker_id = '{0}' group by worker_id""".format(manager_id)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        # cursor.close()

        manager_id, manager_load = res_[0], res_[1]

        if manager_load == 5:
            sql_query = """UPDATE staff SET available = True WHERE worker_id = '{0}'""".format(manager_id)
            cursor.execute(sql_query)
            conn.commit()
            # cursor.close()

        sql_query = """DELETE FROM tire_service_order WHERE serv_order_id = '{0}'""".format(serv_order_id)
        cursor.execute(sql_query)
        conn.commit()
        # cursor.close()

        result = {
            'confirmation': 'Tire service order ID ' + serv_order_id + ' has been deleted'
        }
        return jsonify(result)
    else:
        abort(405)


@app.route("/add_task_to_list_of_works", methods=['POST'])
def add_task_to_list_of_works():
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
            return 'Sorry, there is no connection to the database'

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
