import psycopg2
import redis
from flask import request, jsonify, Flask
import uuid
from datetime import date
from file_read_backwards import FileReadBackwards
from flask_swagger_ui import get_swaggerui_blueprint
from git import Repo

# from package.defs import *
from package.decorators import *

app = Flask(__name__)

SWAGGER_URL = '/swagger'
API_URL = '/static/swagger.yaml'
swaggerui_blueprint = get_swaggerui_blueprint(SWAGGER_URL, API_URL, config={'app_name': "Service_Station"})

app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

repository = Repo('~/PetProject_Service_Station')
# logging

r = redis.StrictRedis(host='localhost', port=6379, db=0, charset="utf-8", decode_responses=True)
conn = psycopg2.connect(dbname='user_20_db', user='user_20', password='123', host='159.69.151.133', port='5056')
cursor = conn.cursor()

def check_required_fields(required_fields: dict):
    """Checks that all required fields are filled in"""
    if not all(required_fields.values()):
        text = 'The {{ name }} are required!'
        template = Template(text)
        name = ', '.join(map(str, required_fields))
        abort(400, description=template.render(name=name))


def admin_authorization(email: str):
    """Make sure the user has administrator rights"""
    sql_query = """SELECT group_name FROM users_groups JOIN users USING (group_id)
                            WHERE email = '{0}';""".format(email)
    cursor.execute(sql_query)
    conn.commit()
    group_name = cursor.fetchone()[0]

    if group_name != 'admin':
        abort(403, description='This can only be done by an admin')


def check_db_connection():
    if not conn:
        abort(503, description='There is no connection to the database')


def check_user_exists(reason: str, email: str):
    """By <reason> checks:
    The user with this email is already registered.
    There is no registered users with this email."""
    usr_id_ = get_value_from_table('user_id', 'users', 'email', email)
    if not usr_id_:
        if reason == 'already exists':
            abort(400, description="The user with this email already exists")
        elif not reason or reason == 'does not exist':
            abort(404, description='The user does not exist')


def check_vehicle_exists(user_vehicle_id: int):
    """Checks that the vehicle with this vehicle_id exists"""
    if not get_value_from_table('user_id', 'user_vehicle', 'user_vehicle_id', user_vehicle_id):
        abort(404, description='The vehicle does not exist')


def check_storage_order_exists(storage_order_id: int):
    """Checks that the vehicle with this vehicle_id exists"""
    if not get_value_from_table('user_id', 'storage_orders', 'storage_order_id', storage_order_id):
        abort(404, description='The storage order does not exist')


def check_tire_service_order_exists(service_order_id: int):
    """Checks that the service order exists"""
    if not get_value_from_table('user_id', 'tire_service_order', 'service_order_id', service_order_id):
        abort(404, description='The tire service order does not exist')


def get_user_id(email: str) -> str:
    """Returns user_id by email"""
    return get_value_from_table('user_id', 'users', 'email', email)


def validate_password(password: str):
    """The password must be at least 8 chars long and not exceed 32 chars;
    must contain at least one digit, one upper, one lower letter, one special char ['$', '@', '#', '!', '%']"""
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
    if not return_val['result']:
        abort(400, description=return_val['text'])


def validate_email(email: str):
    """The email must contain @ and . symbols"""
    return_val = {'result': True, 'text': ''}
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        abort(400, description='The email must contain @ and . chars')
    if len(email) < 4:
        return_val['text'] = 'The email must be at least 4 characters long'
        return_val['result'] = False
    elif len(email) > 100:
        return_val['text'] = 'The email length should not exceed 100 chars'
        return_val['result'] = False
    if not return_val['result']:
        abort(400, description=return_val['text'])


def validate_phone(phone: str):
    return_val = {'result': True, 'text': ''}
    if len(phone) < 1:
        return_val['text'] = 'The phone must be at least 1 characters long'
        return_val['result'] = False
    elif len(phone) > 30:
        return_val['text'] = 'The phone length should not exceed 30 chars'
        return_val['result'] = False
    if not return_val['result']:
        abort(400, description=return_val['text'])

def validate_names(name_type: str, name: str):
    """Names can only include the ' '(space) and '.,- chars;
    must be at least 1 chars long and not exceed 30 chars"""
    return_val = {'result': True, 'text': ''}
    if len(name) < 1:
        return_val['text'] = 'The {0} must be at least 1 characters long'.format(name_type)
        return_val['result'] = False
    if len(name) > 30:
        return_val['text'] = 'The {0} length should not exceed 30 chars'.format(name_type)
        return_val['result'] = False
    if not validate(name):
        return_val['text'] = """The {0} can only include the ' '(space) and '.,- chars""".format(name_type)
        return_val['result'] = False
    if not return_val['result']:
        abort(400, description=return_val['text'])


def validate(name: str):
    """Validate name - match the name to the pattern"""
    valid_pattern = re.compile("^[a-z ,.'-]+$", re.I)
    return bool(valid_pattern.match(name))


def get_value_from_table(select: str, from_db: str, where: str, what):
    sql_query = """SELECT {0} FROM {1} WHERE {2} = '{3}'""".format(select, from_db, where, what)
    cursor.execute(sql_query)
    conn.commit()
    res_ = cursor.fetchone()

    if not res_:
        return None
    return res_[0]


def user_authentication(email: str, token: str):
    if not token == r.get(email):
        abort(401, description='The token is invalid, please log in')


def password_is_valid(salt, password, password_db) -> bool:
    if str.encode(password_db) == bcrypt.hashpw(str.encode(password), str.encode(salt)):
        return True
    return False


def save_to_file(user_id, email, password, reason):
    separator = '/'
    with open('../user_auth.txt', 'a+') as file_user_auth:
        timestamp_now = str(datetime.datetime.now())[:22] + str(datetime.datetime.now().astimezone())[26:]
        content = timestamp_now + separator + str(user_id) + separator + \
                  email + separator + reason + separator + password + '\n'
        file_user_auth.write(content)


def generate_password_hash(password: str):
    """Generates and returns password hash and salt"""
    salt = bcrypt.gensalt(5)
    password = bcrypt.hashpw(str.encode(password), salt)
    return password.decode(), salt.decode()


def choose_a_manager(date_to_query: str) -> int or dict:
    # =========================================================================================================
    # Select a manager
    # someone who does not have a service order on the required order date
    sql_query = """SELECT manager_id FROM managers WHERE manager_id NOT IN
                (SELECT DISTINCT manager_id FROM tire_service_order WHERE DATE(start_datetime) = '{0}')""" \
        .format(date_to_query)
    cursor.execute(sql_query)
    conn.commit()
    res_ = list(manager[0] for manager in cursor.fetchall())

    if res_:
        manager_id = random.choice(res_)
        return manager_id
    else:
        # someone who has the minimum number of service orders on the required order date
        sql_query = """WITH managers_load AS(
                            SELECT manager_id, count(manager_id) AS load_ FROM tire_service_order 
                            WHERE date(start_datetime) = '{0}' GROUP BY manager_id)

                            SELECT manager_id FROM managers_load
                            WHERE load_ in (SELECT MIN(load_) FROM managers_load)""".format(date_to_query)
        cursor.execute(sql_query)
        conn.commit()
        res_ = list(manager[0] for manager in cursor.fetchall())

        if res_:
            manager_id = random.choice(res_)
            return manager_id
        else:
            # unreachable o_O
            abort(404, description='There are no managers for the required time')


def duration_of_service(tasks: dict) -> datetime:
    sql_query = """SELECT SUM
                                (
                                    CASE 
                                        WHEN task_name = '{0}' THEN task_duration 
                                        WHEN task_name = '{1}' THEN task_duration 
                                        WHEN task_name = '{2}' THEN task_duration
                                        WHEN task_name = '{3}' THEN task_duration
                                        WHEN task_name = '{4}' THEN task_duration  
                                        ELSE '00:00:00'
                                    end
                                ) AS duration FROM tasks""". \
        format(tasks['tire_repair'], tasks['tire_change'], tasks['wheel_removal_installation'],
               tasks['wheel_balancing'], tasks['camera_repair'])
    cursor.execute(sql_query)
    conn.commit()
    res_ = cursor.fetchone()
    service_duration = tasks['numbers_of_wheels'] * res_[0]

    sql_query = """SELECT SUM
                    (
                        CASE 
                            WHEN task_name = '{0}' THEN task_duration 
                            ELSE '00:00:00'
                        END
                    ) AS duration
                    FROM tasks""".format(tasks['wheel_alignment'])
    cursor.execute(sql_query)
    conn.commit()
    res_ = cursor.fetchone()

    service_duration += res_[0]

    return service_duration


def choose_a_worker(order_date: datetime, end_time: datetime) -> int:
    # Search for a worker without a work
    sql_query = """WITH dates_intersection AS (
                        SELECT DISTINCT worker_id FROM tire_service_order JOIN list_of_works USING (service_order_id) 
                        WHERE 
                            (
                                start_datetime BETWEEN '{0}' AND '{1}'
                                OR
                                stop_datetime BETWEEN '{0}' AND '{1}'
                                OR
                                '{0}' BETWEEN start_datetime AND stop_datetime 
                                OR
                                '{1}' BETWEEN start_datetime AND stop_datetime
                            )
                        )	

                    SELECT worker_id FROM staff JOIN positions USING (position_id)
                    WHERE worker_id NOT IN (SELECT worker_id FROM dates_intersection) 
                    AND active = true AND position_name = 'worker'""".format(order_date, end_time)
    cursor.execute(sql_query)
    conn.commit()
    res_ = list(worker[0] for worker in cursor.fetchall())

    if res_:
        return random.choice(res_)  # randomly choose a worker
    else:
        abort(404, description='There are no workers for the required time')


def create_a_service_order(user_id, order_date, end_time, user_vehicle_id, manager_id, service_type_id) -> int:
    created = datetime.datetime.now()
    sql_query = """INSERT INTO tire_service_order
                        (user_id, start_datetime, stop_datetime, user_vehicle_id, manager_id, service_type_id, created)
                        VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}');""". \
        format(user_id, order_date, end_time, user_vehicle_id, manager_id, service_type_id, created)
    cursor.execute(sql_query)
    conn.commit()

    sql_query = """SELECT MAX(service_order_id) FROM tire_service_order WHERE
                                            user_id = '{0}' AND
                                            start_datetime = '{1}' AND
                                            stop_datetime = '{2}' AND
                                            user_vehicle_id = '{3}' AND
                                            manager_id = '{4}' AND
                                            service_type_id = '{5}';""". \
        format(user_id, order_date, end_time, user_vehicle_id, manager_id, service_type_id)
    cursor.execute(sql_query)
    conn.commit()
    return cursor.fetchone()[0]  # The service order_id


def create_tasks_for_the_service_order(tasks: dict, order_id: int, worker_id: int) -> list:
    service_order_tasks= []
    tasks_to_db = ('tire_repair', 'camera_repair', 'tire_change', 'wheel_removal_installation', 'wheel_balancing')
    for key in tasks:
        if tasks[key] in tasks_to_db:
            count_tasks = tasks['numbers_of_wheels']
        elif tasks[key] == 'wheel_alignment':
            count_tasks = 1
        else:
            count_tasks = 0

        for _ in range(count_tasks):
            task_id = get_value_from_table('task_id', 'tasks', 'task_name', tasks[key])

            sql_query = """INSERT INTO list_of_works (service_order_id, task_id, worker_id)
                                    VALUES ('{0}', '{1}', '{2}');""".format(order_id, task_id, worker_id)
            cursor.execute(sql_query)
            conn.commit()

            task_name = get_value_from_table('task_name', 'tasks', 'task_id', task_id)
            worker_data = get_employee_data(worker_id, 'worker')
            service_order_tasks.append({
                'task_name': task_name,
                'worker:': worker_data,
                'task_id': task_id
            })
    return service_order_tasks


def get_employee_data(employee_id: int, employee_position: str) -> dict:
    """Get the employee's first and last names, email and phone"""
    sql_query = """SELECT first_name, last_name, email, phone FROM staff WHERE worker_id = '{0}';""".format(employee_id)
    cursor.execute(sql_query)
    conn.commit()
    first_name, last_name, email, phone = cursor.fetchone()
    result = {
        employee_position + '_id': employee_id,
        employee_position + '_name': first_name + ' ' + last_name,
        employee_position + '_email': email,
        employee_position + '_phone': phone
    }
    return result


@app.route("/users", methods=['GET', 'POST', 'PATCH'])  # request a short data/register a new user/change the user's info
def users():
    # request a short data about all/one of the users
    if request.method == 'GET':
        user_id = request.args.get('user_id')
        active = request.args.get('active')

        check_db_connection()

        if not active:
            active = 'all'
        elif active.lower() not in ('yes', 'no'):
            abort(400, description='The <active> should be <yes>, <no> or blank')
        active = active.lower()

        if not user_id:
            if active == 'yes':
                sql_query = """SELECT user_id, first_name, last_name, phone, email, active, group_name 
                                FROM users_groups JOIN users USING (group_id) WHERE active = True;"""
            elif active == 'no':
                sql_query = """SELECT user_id, first_name, last_name, phone, email, active, group_name 
                                FROM users_groups JOIN users USING (group_id) WHERE active = False;"""
            else:
                sql_query = """SELECT user_id, first_name, last_name, phone, email, active, group_name 
                                FROM users_groups JOIN users USING (group_id);"""

            cursor.execute(sql_query)
            conn.commit()
            res = cursor.fetchall()

            if res:
                result = []
                for user in res:
                    result.append({
                        "ID": user[0],
                        "f_name": user[1],
                        "l_name": user[2],
                        "phone": user[3],
                        "email": user[4],
                        "active": user[5],
                        "group_name": user[6]
                    })
            else:
                result = {
                    'confirmation': 'There are no users in the DB'
                }
        else:
            try:
                user_id = int(user_id)
            except ValueError:
                abort(400, description='The <user_id> should contain only numbers')

            sql_query = """SELECT user_id, first_name, last_name, phone, email, active, group_name 
                            FROM users_groups JOIN users USING (group_id) WHERE user_id = '{0}';""".format(user_id)
            cursor.execute(sql_query)
            conn.commit()
            res = cursor.fetchone()

            result = []
            if res:
                result = [{
                    "ID": res[0],
                    "f_name": res[1],
                    "l_name": res[2],
                    "phone": res[3],
                    "email": res[4],
                    "active": res[5],
                    "group_name": res[6]
                }]
            else:
                abort(404, description='There is no user ID ' + str(user_id) + ' in the DB')

        return jsonify(result)

    # register a new user
    elif request.method == 'POST':
        f_name = request.form.get('first_name')
        l_name = request.form.get('last_name')
        password = request.form.get('password')
        phone = request.form.get('phone')
        email = request.form.get('email')

        required_fields = {
            'first_name': f_name,
            'last_name': l_name,
            'password': password,
            'phone': phone,
            'email': email
        }
        check_required_fields(required_fields)

        check_user_exists('already exists', email)
        validate_names('first name', f_name)
        validate_names('last name', l_name)
        validate_password(password)
        validate_email(email)
        validate_phone(phone)
        group_id = 2

        active = True
        check_db_connection()

        hash_password, salt = generate_password_hash(password)

        created = datetime.datetime.now()
        sql_query = """INSERT INTO users (first_name, last_name, password, phone, email, active, salt, created, group_id) 
                    VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}', '{7}', {8})""". \
            format(f_name, l_name, hash_password, phone, email, active, salt, created, group_id)
        cursor.execute(sql_query)
        conn.commit()

        user_id = get_value_from_table('user_id', 'users', 'email', email)
        save_to_file(user_id, email, password, 'user-registered')

        result = {
            "ID": user_id,
            "first_name": f_name,
            "last_name": l_name,
            "phone": phone,
            "email": email,
            "active": active,
            'group_name': 'users'
        }

        return jsonify(result), 201

    # change the user's info
    elif request.method == 'PATCH':
        token = request.form.get('token')
        email = request.form.get('email')
        f_name = request.form.get('new_first_name')
        l_name = request.form.get('new_last_name')
        phone = request.form.get('new_phone')
        new_email = request.form.get('new_email')

        required_fields = {
            'token': token,
            'email': email
        }
        check_required_fields(required_fields)

        user_authentication(email, token)
        r.expire(email, 600)
        check_db_connection()

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
            validate_names('first name', f_name)
            f_name_to_db = f_name

        if not l_name or l_name == l_name_db:
            l_name = 'The last name has not been changed'
            l_name_to_db = l_name_db
        else:
            validate_names('last name', l_name)
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
            check_user_exists('already exists', email)
            validate_email(new_email)
            save_to_file(user_id_db, email + '->' + new_email, '!password!', 'user-changed-email')
            new_email_to_db = new_email
            r.delete(email)  # log out if the email has been changed

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
    else:
        abort(405)


@app.route("/users/user_info", methods=['POST'])  # get all info about the logged user
def user_info():
    if request.method == 'POST':
        token = request.form.get('token')
        email = request.form.get('email')

        required_fields = {
            'token': token,
            'email': email
        }
        check_required_fields(required_fields)

        user_authentication(email, token)
        r.expire(email, 600)
        check_db_connection()

        # collecting the user's personal data from the users db
        sql_query = """SELECT user_id, first_name, last_name, email, phone, group_name 
                        FROM users JOIN users_groups USING(group_id) WHERE email = '{0}'""".format(email)
        cursor.execute(sql_query)
        conn.commit()
        res = cursor.fetchone()

        result_users = ({
            "ID": res[0],
            "first_name": res[1],
            "last_name": res[2],
            "email": res[3],
            "phone": res[4],
            "group_name": res[5]
        })

        user_id = get_user_id(email)
        # collecting the user's storage orders data from the storage_orders db
        sql_query = """SELECT storage_order_id, start_date, stop_date, storage_order_cost, shelf_id 
                                                FROM storage_orders WHERE user_id = '{0}'""".format(user_id)
        cursor.execute(sql_query)
        conn.commit()
        storage_orders_data = cursor.fetchall()

        # empty_result = []
        # if res_ == empty_result:
        if not storage_orders_data:
            result_order = 'You do not have any storage orders'
        else:
            result_order = []
            for order in storage_orders_data:  # does the user need the size_id or size_name data?
                result_order.append({
                    "storage_order_id": order[0],
                    "start_date": order[1],
                    "stop_date": order[2],
                    "order cost": order[3],
                    "shelf_id": order[4]
                })

        # collecting data about the user's vehicles from the user_vehicle, vehicle and sizes db's
        sql_query = """SELECT user_vehicle_id, vehicle_name, size_name FROM user_vehicle 
                    JOIN vehicle USING (vehicle_id)
                    JOIN sizes USING (size_id) 
                    WHERE user_id = '{0}'""".format(user_id)
        cursor.execute(sql_query)
        conn.commit()
        users_vehicles = cursor.fetchall()

        if not users_vehicles:
            result_vehicle = 'You do not have any vehicles'
        else:
            result_vehicle = []
            for vehicle in users_vehicles:
                result_vehicle.append({
                    'vehicle_id': vehicle[0],
                    'vehicle_name': vehicle[1],
                    'size_name': vehicle[2]
                })

        # get all info about all user's service orders
        sql_query = """CREATE OR REPLACE VIEW temp AS
                                SELECT 
                                    service_order_id,
                                    tso.user_id,
                                    start_datetime,
                                    stop_datetime,
                                    user_vehicle_id,
                                    vehicle_name,
                                    size_name,
                                    tso.manager_id,
                                    tso.created,
                                    task_name,
                                    task_cost,
                                    task_duration,
                                    position_name,
                                    low.worker_id,
                                    s.first_name AS worker_name,
                                    s.last_name AS worker_surname,
                                    m.first_name AS manager_name,
                                    m.last_name AS manager_surname,
                                    service_type_name
                                FROM tire_service_order AS tso
                                LEFT JOIN list_of_works AS low USING (service_order_id)
                                LEFT JOIN tasks AS t USING (task_id)
                                LEFT JOIN staff AS s USING (worker_id)
                                LEFT JOIN positions AS p USING (position_id)
                                LEFT JOIN managers AS m USING (manager_id)
                                LEFT JOIN tire_service_order_type USING (service_type_id)
                                LEFT JOIN user_vehicle USING (user_vehicle_id)
                                LEFT JOIN vehicle USING (vehicle_id)
                                LEFT JOIN sizes USING (size_id)
                                WHERE tso.user_id = '{0}';""".format(user_id)
        cursor.execute(sql_query)
        conn.commit()

        sql_query = """SELECT DISTINCT service_type_name FROM temp"""
        cursor.execute(sql_query)
        conn.commit()
        service_orders_types = cursor.fetchall()

        if not service_orders_types:
            result_tire_service_order = 'You do not have any tire service orders'
        else:
            result_tire_service_order = []
            for types in service_orders_types:
                type_ = types[0]

                sql_query = """SELECT DISTINCT service_order_id FROM temp 
                                            WHERE service_type_name = '{0}';""".format(type_)
                cursor.execute(sql_query)
                conn.commit()
                service_order_data = cursor.fetchall()

                for order in service_order_data:
                    service_order_id = order[0]
                    tire_service_order_cost = \
                        get_value_from_table('SUM(task_cost)', 'temp', 'service_order_id', service_order_id)

                    sql_query = """SELECT task_name, worker_id, task_cost FROM temp 
                                    WHERE service_order_id = '{0}'""".format(service_order_id)
                    cursor.execute(sql_query)
                    conn.commit()
                    tasks_data = cursor.fetchall()

                    if not tasks_data[0][0]:
                        result_tire_service_order_tasks = 'You do not have any tasks in your tire service order.'
                    else:
                        result_tire_service_order_tasks = []
                        for task in tasks_data:
                            worker_data = get_employee_data(task[1], 'worker')
                            result_tire_service_order_tasks.append({
                                'task_name': task[0],
                                'worker:': worker_data,
                                'task_cost': task[2]
                            })

                    sql_query = """SELECT start_datetime, stop_datetime, manager_id, manager_name, manager_surname, 
                                user_vehicle_id, vehicle_name, size_name FROM temp WHERE service_order_id = '{0}'""". \
                        format(service_order_id)
                    cursor.execute(sql_query)
                    conn.commit()
                    # res_info = cursor.fetchone()

                    start_datetime, stop_datetime, manager_id, user_vehicle_id, \
                    vehicle_name, size_name = cursor.fetchone()
                    manager_data = get_employee_data(manager_id, 'manager')

                    result_tire_service_order.append({
                        'service_order_id': service_order_id,
                        'service_order_type': type_,
                        'start_datetime': start_datetime,
                        'stop_datetime': stop_datetime,
                        'manager': manager_data,
                        'vehicle': {
                            'user_vehicle_id': user_vehicle_id,
                            'vehicle_name': vehicle_name,
                            'size_name': size_name
                        },
                        'tire_service_order_cost': tire_service_order_cost,
                        'tasks': result_tire_service_order_tasks
                    })

        sql_query = """drop view temp"""
        cursor.execute(sql_query)
        conn.commit()

        result = (
            {"your_info": result_users},
            {"storage_orders_info:": result_order},
            {"your_vehicle": result_vehicle},
            {"tire_service_order": result_tire_service_order}
        )
        return jsonify(result)
    else:
        abort(405)


@app.route("/users/login", methods=['POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        required_fields = {
            'email': email,
            'password': password
        }
        check_required_fields(required_fields)

        check_user_exists('does not exist', email)
        check_db_connection()

        if not get_value_from_table('active', 'users', 'email', email):
            abort(400, description='The user is deactivated')

        sql_query = "SELECT salt, user_id, first_name, last_name, password FROM users WHERE email = '{0}'".format(email)
        cursor.execute(sql_query)
        conn.commit()
        # res = cursor.fetchone()
        salt, user_id, first_name, last_name, password_db = cursor.fetchone()

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
        are_you_sure = request.form.get('ARE_YOU_SURE?')

        required_fields = {
            'email': email,
            'token': token,
            'ARE_YOU_SURE?': are_you_sure
        }
        check_required_fields(required_fields)

        user_authentication(email, token)
        check_db_connection()

        if are_you_sure.lower() != 'yes':
            abort(400, description='АHA! Changed your mind?')

        sql_query = """UPDATE users SET active = 'False' WHERE email = '{0}'""".format(email)
        cursor.execute(sql_query)
        conn.commit()

        first_name = get_value_from_table('first_name', 'users', 'email', email)
        last_name = get_value_from_table('last_name', 'users', 'email', email)

        text = 'User {{ name }} has been successfully deactivated'
        template = Template(text)
        result = {
            'confirmation': template.render(name=first_name + ' ' + last_name)
        }

        r.delete(email)  # log out if the user has been deactivated
        return jsonify(result)
    else:
        abort(405)


@app.route("/vehicle", methods=['POST', 'PATCH', 'DELETE'])  # add new/change/delete user's vehicle
def users_vehicle():
    # Add new user's vehicle
    if request.method == 'POST':
        token = request.form.get('token')
        email = request.form.get('email')
        vehicle_name = request.form.get('vehicle_name')
        size_name = request.form.get('size_name')

        required_fields = {
            'email': email,
            'token': token,
            'vehicle_name': vehicle_name,
            'size_name': size_name
        }
        check_required_fields(required_fields)

        user_authentication(email, token)
        r.expire(email, 600)
        check_db_connection()

        try:
            size_name = int(size_name)
        except ValueError:
            abort(400, description='The <size_name> should contain only numbers')

        # get needed data
        user_id = get_user_id(email)
        size_id = get_value_from_table('size_id', 'sizes', 'size_name', size_name)
        vehicle_id = get_value_from_table('vehicle_id', 'vehicle', 'vehicle_name', vehicle_name)

        if not size_id:
            abort(404, description='Unknown size_name')

        if not vehicle_id:
            abort(404, description='Unknown vehicle_name')

        created = datetime.datetime.now()
        sql_query = """INSERT INTO user_vehicle (user_id, vehicle_id, size_id, created) 
                        VALUES ('{0}', '{1}', '{2}', '{3}');""".format(user_id, vehicle_id, size_id, created)
        cursor.execute(sql_query)
        conn.commit()

        vehicle_id_new = get_value_from_table('MAX(user_vehicle_id)', 'user_vehicle', 'user_id', user_id)

        result = {
            'new_vehicle_id': vehicle_id_new,
            'vehicle_name': vehicle_name,
            'size_name': size_name
        }
        return jsonify(result), 201

    # Update the user's vehicle data
    elif request.method == 'PATCH':
        email = request.form.get('email')
        token = request.form.get('token')
        user_vehicle_id = request.form.get('user_vehicle_id')
        new_vehicle_name = request.form.get('new_vehicle_name')
        new_size_name = request.form.get('new_size_name')

        required_fields = {
            'email': email,
            'token': token,
            'user_vehicle_id': user_vehicle_id
        }
        check_required_fields(required_fields)

        user_authentication(email, token)
        r.expire(email, 600)
        check_db_connection()

        if not new_vehicle_name and not new_size_name:
            abort(400, description='Ok. Nothing needs to be changed :)')

        try:
            user_vehicle_id = int(user_vehicle_id)
        except ValueError:
            abort(400, description='The <user_vehicle_id> should contain only numbers')
        check_vehicle_exists(user_vehicle_id)

        sql_query = """SELECT user_id, vehicle_id, size_id FROM user_vehicle WHERE user_vehicle_id = '{0}'""". \
            format(user_vehicle_id)
        cursor.execute(sql_query)
        conn.commit()
        user_id_db, vehicle_id_db, size_id_db = cursor.fetchone()

        if user_id_db != get_user_id(email):
            abort(403, description='It is not your vehicle! Somebody call the police!')

        vehicle_name_db = get_value_from_table('vehicle_name', 'vehicle', 'vehicle_id', vehicle_id_db)
        size_name_db = get_value_from_table('size_name', 'sizes', 'size_id', size_id_db)

        if not new_vehicle_name or new_vehicle_name == vehicle_name_db:
            new_vehicle_id = vehicle_id_db
            new_vehicle_name = 'The vehicle name has not been changed'
        else:
            try:
                user_vehicle_id = int(user_vehicle_id)
            except ValueError:
                abort(400, description='The <user_vehicle_id> should contain only numbers')
            new_vehicle_id = get_value_from_table('vehicle_id', 'vehicle', 'vehicle_name', new_vehicle_name)
            if not new_vehicle_id:
                abort(404, description='Unknown vehicle_name')

        if not new_size_name or new_size_name == size_name_db:
            new_size_id = size_id_db
            new_size_name = 'The size name has not been changed'
        else:
            try:
                new_size_name = int(new_size_name)
            except ValueError:
                abort(400, description='The <new_size_name> should contain only numbers')
            new_size_id = get_value_from_table('size_id', 'sizes', 'size_name', new_size_name)
            if not new_size_id:
                abort(404, description='Unknown size_name')

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

    # Delete the user's vehicle from DB
    elif request.method == 'DELETE':
        email = request.form.get('email')
        token = request.form.get('token')
        user_vehicle_id = request.form.get('user_vehicle_id')

        required_fields = {
            'email': email,
            'token': token,
            'user_vehicle_id': user_vehicle_id
        }
        check_required_fields(required_fields)

        user_authentication(email, token)
        r.expire(email, 600)
        check_db_connection()

        try:
            user_vehicle_id = int(user_vehicle_id)
        except ValueError:
            abort(400, description='The <user_vehicle_id> should contain only numbers')
        check_vehicle_exists(user_vehicle_id)

        if get_user_id(email) != get_value_from_table('user_id', 'user_vehicle', 'user_vehicle_id', user_vehicle_id):
            abort(403, description='It is not your vehicle! Somebody call the police!')
        else:
            sql_query = """SELECT vehicle_name FROM user_vehicle JOIN vehicle USING (vehicle_id)
                            WHERE user_vehicle_id = '{0}'""".format(user_vehicle_id)
            cursor.execute(sql_query)
            conn.commit()
            vehicle_name = cursor.fetchone()[0]

            sql_query = """DELETE FROM user_vehicle WHERE user_vehicle_id = '{0}'""".format(user_vehicle_id)
            cursor.execute(sql_query)
            conn.commit()

            text = 'Your {{ type }} ID {{ ID }} has been successfully deleted'
            template = Template(text)
            result = {
                'confirmation': template.render(type=vehicle_name, ID=user_vehicle_id)
            }
            return jsonify(result)
    else:
        abort(405)


@app.route("/warehouse", methods=['GET'])  # shows shelves in the warehouse (availability depends on the request params)
def active_storage():
    # if size_name is None - show all sizes
    # if active_only.lower() = 'yes' - show only free shelves
    # if active_only.lower() = 'no' - show only occupied shelves
    # if active_only.lower() is blank - show all shelves
    # if active_only.lower() != 'yes', 'no' or blank - show an error message
    if request.method == 'GET':
        size_name = request.args.get('size_name')
        active_only = request.args.get('active_only')

        if active_only:
            try:
                active_only = active_only.lower()
            except AttributeError:
                abort(400, description='The <active_only> should be string')
            else:
                if active_only not in ('yes', 'no', ''):
                    abort(400, description='The <active_only> should be <yes>, <no> or blank')
        else:
            active_only = 'undefined'

        check_db_connection()

        if not size_name:
            if active_only == 'yes':

                sql_query = """SELECT shelf_id, size_id, active FROM warehouse 
                                WHERE active = 'True'"""
                cursor.execute(sql_query)
                conn.commit()
                res_ = cursor.fetchall()

            elif active_only == 'no':

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
                for shelf in res_:
                    result.append({
                        'shelf_id': shelf[0],
                        'size_id': shelf[1],
                        'size_name': get_value_from_table('size_name', 'sizes', 'size_id', shelf[1]),
                        'active': shelf[2]
                    })
            else:
                result = {
                    'confirmation': 'Unfortunately, we do not have the storage shelves you requested'
                }
        else:
            try:
                size_name = int(size_name)
            except ValueError:
                abort(400, description='The <size_name> should contain only numbers')

            size_id = get_value_from_table('size_id', 'sizes', 'size_name', size_name)
            if not size_id:
                abort(404, description='Unfortunately, we do not have storage shelves you need')

            if active_only == 'yes':

                sql_query = """SELECT shelf_id, size_id, active FROM warehouse WHERE active = 'True'
                                AND size_id = '{0}'""".format(size_id)
                cursor.execute(sql_query)
                conn.commit()
                res_ = cursor.fetchall()

            elif active_only == 'no':

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
                for shelf in res_:
                    result.append({
                        'shelf_id': shelf[0],
                        'size_id': shelf[1],
                        'size_name': size_name,
                        'active': shelf[2]
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

        required_fields = {
            'email': email,
            'token': token,
            'start_date': start_date,
            'stop_date': stop_date
        }
        check_required_fields(required_fields)

        user_authentication(email, token)
        r.expire(email, 600)
        check_db_connection()

        if (not size_name and not user_vehicle_id) or (size_name and user_vehicle_id):
            abort(400, description='The size_name OR user_vehicle_id is required')

        if size_name:
            try:
                size_name = int(size_name)
            except ValueError:
                abort(400, description='The <size_name> should contain only numbers')

        if user_vehicle_id:
            try:
                user_vehicle_id = int(user_vehicle_id)
            except ValueError:
                abort(400, description='The <user_vehicle_id> should contain only numbers')

        try:
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            abort(400, description='The <start_date> should be in YYYY-MM-DD format')

        try:
            stop_date = datetime.datetime.strptime(stop_date, '%Y-%m-%d').date()
        except ValueError:
            abort(400, description='The <stop_date> should be in YYYY-MM-DD format')

        if start_date < date(datetime.date.today().year, datetime.date.today().month, datetime.date.today().day + 1):
            abort(400, description='The <start_date> cannot be less than tomorrow')

        if stop_date > date(datetime.date.today().year + 2, datetime.date.today().month, datetime.date.today().day):
            abort(400, description='The stop_date can not exceed +2 year from today')

        if start_date > stop_date:
            abort(400, description='The start date can not be greater than the stop date')

        user_id = get_user_id(email)

        if user_vehicle_id:
            if get_value_from_table('user_id', 'user_vehicle', 'user_vehicle_id', user_vehicle_id) != user_id:
                abort(403, description='It is not your vehicle! Somebody call the police!')
            else:
                sql_query = """SELECT size_name FROM sizes JOIN user_vehicle USING (size_id) 
                                WHERE user_vehicle_id = {0};""".format(user_vehicle_id)
                cursor.execute(sql_query)
                size_name = cursor.fetchone()[0]

        size_id = get_value_from_table('size_id', 'sizes', 'size_name', size_name)

        # set the storage order cost 1000, the calculation will be implemented after some time. May be....
        storage_order_cost = 1000

        shelf_id = 0
        # Проверяем, вдруг есть полка нужного размера вообще без заказов
        sql_query = """SELECT w.shelf_id FROM storage_orders RIGHT JOIN warehouse AS w USING(shelf_id) WHERE
                        storage_order_id IS NULL AND active = True AND w.size_id = {0};""".format(size_id)
        cursor.execute(sql_query)
        res = list(shelf[0] for shelf in cursor.fetchall())

        # Если есть:
        if res:
            # Если таких несколько, выбираем меньшую по ИД
            shelf_id = min(res)

            # create storage order
            sql_query = """INSERT INTO storage_orders (user_id, start_date, stop_date, shelf_id, 
                                            storage_order_cost) VALUES('{0}', '{1}', '{2}', '{3}', '{4}');""". \
                format(user_id, start_date, stop_date, shelf_id, storage_order_cost)
            cursor.execute(sql_query)
            conn.commit()

        # Если нет, проверить что даты не пересекаются с существующими:
        else:
            # Запрос на полки, у которых нет пересечений по датам
            sql_query = """WITH dates_intersection AS (
                            SELECT DISTINCT shelf_id FROM storage_orders JOIN warehouse USING (shelf_id) WHERE 
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
    
                            SELECT shelf_id FROM storage_orders JOIN warehouse USING (shelf_id) WHERE shelf_id NOT IN 
                            (SELECT shelf_id FROM dates_intersection) AND active = True AND size_id = {2};""". \
                format(start_date, stop_date, size_id)
            cursor.execute(sql_query)
            res_ = list(shelf[0] for shelf in cursor.fetchall())

            # Если есть, то записываем заказ на нее
            if res_:
                # Если таких несколько, выбираем меньшую по ИД
                shelf_id = min(res_)

                created = datetime.datetime.now()
                # create storage order
                sql_query = """INSERT INTO storage_orders (user_id, start_date, stop_date, shelf_id, 
                            storage_order_cost, created) VALUES('{0}', '{1}', '{2}', '{3}', '{4}', '{5}');""". \
                    format(user_id, start_date, stop_date, shelf_id, storage_order_cost, created)
                cursor.execute(sql_query)
                conn.commit()

            else:
                # Если пересекаются, отправляем контакты менеджера
                # Внедрить: рекомендации по ближайшим свободным датам
                abort(404, description='We do not have available storage place on the dates you need')
                # Если незанятых полок нужного размера нет, сверяем даты
                # Выбираем полки с необходимым размером и минимальной дельтой от необходимых дат
                # предоставляем информацию о дельтах дат и перенаправляем на ресепшн

        if shelf_id == 0:
            abort(404, description='Shelf_id is undefined')
        # get the new storage order id
        new_storage_order_id = get_value_from_table('storage_order_id', 'storage_orders', 'shelf_id', shelf_id)

        result = {
            'storage_order_id': new_storage_order_id,
            'shelf_id': shelf_id,
            'start_date': start_date,
            'stop_date': stop_date,
            'storage_order_cost': storage_order_cost
        }
        return jsonify(result), 201

    elif request.method == 'PUT':
        return 'Temporarily closed for maintenance'
    # ======================================================================================================================
    #                                           ON MAINTENANCE
    # ======================================================================================================================

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
    # user_auth = user_authentication(email, token)
    # if not user_auth['result']:
    #     abort(401, description=user_auth['text'])
    #
    # r.expire(email, 600)
    #
    # check_db_connection()
    #
    # if not storage_order_exists(storage_order_id):
    #     abort(404, description='The storage order does not exists')
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
    #             abort(404, description='Sorry, we do not have the storage you need')
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

        required_fields = {
            'email': email,
            'token': token,
            'storage_order_id': storage_order_id
        }
        check_required_fields(required_fields)

        user_authentication(email, token)
        r.expire(email, 600)
        check_db_connection()

        if storage_order_id:
            try:
                storage_order_id = int(storage_order_id)
            except ValueError:
                abort(400, description='The <storage_order_id> should contain only numbers')

        check_storage_order_exists(storage_order_id)

        sql_query = """SELECT user_id, shelf_id, start_date FROM storage_orders 
                                    WHERE storage_order_id = '{0}';""".format(storage_order_id)
        cursor.execute(sql_query)
        conn.commit()
        user_id, shelf_id, start_date = cursor.fetchone()

        if get_user_id(email) != user_id:
            abort(403, description='It is not your storage order!')

        if start_date < datetime.datetime.now().date():
            abort(400, description='You cannot delete a storage order that has started. Please call us.')

        sql_query = """DELETE FROM storage_orders WHERE storage_order_id = '{0}';""".format(storage_order_id)
        cursor.execute(sql_query)
        conn.commit()

        text = 'Storage order ID {{ storage_order_id }} has been successfully deleted'
        template = Template(text)
        result = {
            'confirmation': template.render(storage_order_id=storage_order_id)
        }
        return jsonify(result)
    else:
        abort(405)


@app.route("/tire_service_order", methods=['POST', 'PUT', 'DELETE'])  # add new/change/delete the user's service order
def tire_service_order():
    if request.method == 'POST':
        email = request.form.get('email')  #
        token = request.form.get('token')  #
        order_type = request.form.get('order_type')  #
        order_date = request.form.get('order_date')  #
        user_vehicle_id = request.form.get('user_vehicle_id')  #
        numbers_of_wheels = request.form.get('numbers_of_wheels')  #
        removing_installing_wheels = request.form.get('removing_installing_wheels')
        tubeless = request.form.get('tubeless')
        balancing = request.form.get('balancing')
        wheel_alignment = request.form.get('wheel_alignment')

        required_fields = {
            'email': email,
            'token': token,
            'order_date': order_date,
            'user_vehicle_id': user_vehicle_id,
            'order_type': order_type,
            'numbers_of_wheels': numbers_of_wheels,
            'removing_installing_wheels': removing_installing_wheels,
            'tubeless': tubeless,
            'balancing': balancing,
            'wheel_alignment': wheel_alignment
        }
        check_required_fields(required_fields)

        user_authentication(email, token)
        r.expire(email, 600)
        check_db_connection()

        try:
            user_vehicle_id = int(user_vehicle_id)
        except ValueError:
            abort(400, description='The <user_vehicle_id> should contain only numbers')

        user_id = get_value_from_table('user_id', 'user_vehicle', 'user_vehicle_id', user_vehicle_id)
        if get_user_id(email) != user_id:
            abort(403, description='It is not your vehicle!')

        try:
            numbers_of_wheels = int(numbers_of_wheels)
        except ValueError:
            abort(400, description='The <numbers_of_wheels> should contain only numbers')

        try:
            order_date = datetime.datetime.strptime(order_date, '%Y-%m-%d %H:%M')
        except ValueError:
            abort(400, description='The <order_date> should be in YYYY-MM-DD HH-MM format')

        if order_date.date() < datetime.datetime.now().date():
            abort(400, description='The <start_date> can not be less than today')

        sql_query = """SELECT DISTINCT service_type_name FROM tire_service_order_type;"""
        cursor.execute(sql_query)
        conn.commit()
        order_types = list(types[0] for types in cursor.fetchall())

        try:
            order_type = order_type.lower()
        except AttributeError:
            abort(400, description='The <order_type> should be string')
        else:
            if order_type not in order_types:
                str_order_types = ''
                for types in order_types:
                    str_order_types += '<' + str(types) + '>' + ' or '
                abort(400, description='The <order_type> should be ' + str_order_types[:len(str_order_types) - 4])

        try:
            tubeless = tubeless.lower()
            balancing = balancing.lower()
            wheel_alignment = wheel_alignment.lower()
        except AttributeError:
            abort(400, description='The <active_only>, <balancing> and <wheel_alignment> should be string')
        else:
            correct_answers = ('yes', 'no')
            if not all([tubeless in correct_answers, balancing in correct_answers, wheel_alignment in correct_answers]):
                abort(400, description='The <active_only>, <balancing> and <wheel_alignment> should be <yes> or <no>')

        delta_db = get_value_from_table('delta_minutes', 'positions', 'position_name', 'worker')
        delta_between_orders = datetime.timedelta(minutes=int(delta_db))
        date_to_query = str(order_date.date())

        if int(order_date.hour) < 8:
            abort(400, description='Sorry, we open at 08:00 am')

        # form the tasks dict based on the order type and service needed
        if order_type.lower() == 'tire change':
            service_type_id = get_value_from_table('service_type_id', 'tire_service_order_type',
                                                   'service_type_name', order_type)
            tasks = {
                'tire_change': 'tire_change',
                'tire_repair': 'no',
                'camera_repair': 'no',
                'numbers_of_wheels': numbers_of_wheels
            }

            tasks['wheel_removal_installation'] = 'wheel_removal_installation' \
                if removing_installing_wheels.lower() == 'yes' else 'no'
            tasks['wheel_balancing'] = 'wheel_balancing' if balancing.lower() == 'yes' else 'no'
            tasks['wheel_alignment'] = 'wheel_alignment' if wheel_alignment.lower() == 'yes' else 'no'


        elif order_type.lower() == 'tire repair':
            service_type_id = get_value_from_table('service_type_id', 'tire_service_order_type',
                                                   'service_type_name', order_type)
            tasks = {
                'tire_change': 'no',
                'tire_repair': 'tire_repair',
                'numbers_of_wheels': numbers_of_wheels
            }

            tasks['camera_repair'] = 'camera_repair' if tubeless.lower() == 'no' else 'no'
            tasks['wheel_removal_installation'] = 'wheel_removal_installation' \
                if removing_installing_wheels.lower() == 'yes' else 'no'
            tasks['wheel_balancing'] = 'wheel_balancing' if balancing.lower() == 'yes' else 'no'
            tasks['wheel_alignment'] = 'wheel_alignment' if wheel_alignment.lower() == 'yes' else 'no'
        else:
            return 'Unreachable situation'

        # =========================================================================================================
        # Calculate the expected duration of tire service
        service_duration = duration_of_service(tasks)
        end_time = order_date + service_duration + delta_between_orders
        if int(end_time.hour) >= 20 and int(end_time.minute) >= 15:
            abort(400, description='Sorry, we close at 08:00 pm. The estimated end time of your order is '
                                   + str(end_time.hour) + ':' + str(end_time.minute))

        # =========================================================================================================
        # Choose a manager
        manager_id = choose_a_manager(date_to_query)

        # =========================================================================================================

        worker_id = choose_a_worker(order_date, end_time)
        order_id = create_a_service_order(user_id, order_date, end_time, user_vehicle_id, manager_id, service_type_id)
        service_order_tasks = create_tasks_for_the_service_order(tasks, order_id, worker_id)
        manager_data = get_employee_data(manager_id, 'manager')

        sql_query = """SELECT SUM(task_cost) FROM tasks
                        JOIN list_of_works USING(task_id) WHERE service_order_id = '{0}';""".format(order_id)
        cursor.execute(sql_query)
        conn.commit()
        service_order_cost = int(cursor.fetchone()[0])

        # =========================================================================================================

        result = ({
            'service_order_id': order_id,
            'user_vehicle_id': user_vehicle_id,
            'manager:': manager_data,
            'service_order_type': order_type,
            'order_datetime': str(order_date),
            'estimated_service_duration': str(service_duration),
            'estimated_end_of_service_datetime': str(end_time),
            'service_order_cost': service_order_cost,
            'tasks': service_order_tasks
        })

        # result = choose_a_worker_and_insert_the_tasks(user_id, order_date, end_time, user_vehicle_id,
        #                                               manager_id,
        #                                               tasks, numbers_of_wheels, order_type, service_duration,
        #                                               service_type_id)
        return result, 201

    elif request.method == 'PUT':
        return 'Temporarily closed for maintenance'
    # ======================================================================================================================
    #                                           ON MAINTENANCE
    # ======================================================================================================================
    #         email = request.form.get('email')
    #         token = request.form.get('token')
    #         service_order_id = request.form.get('service order id')
    #         new_order_date = request.form.get('new order date')
    #         new_user_vehicle_id = request.form.get('new user vehicle id')
    #
    #         if not token or not email or not service_order_id:
    #             abort(400, description='The token, email, service order id are required')
    #
    #         user_authentication(email, token)
    #
    #         r.expire(email, 600)
    #
    #         check_db_connection()
    #
    #         if not tire_service_order_exists(service_order_id):
    #             abort(404, description='The tire service order does not exist')
    #
    #         # get the initial data about the tire_service_order
    #         sql_query = """SELECT user_id, user_vehicle_id, start_datetime FROM tire_service_order
    #                                                 WHERE service_order_id = '{0}';""".format(service_order_id)
    #         cursor.execute(sql_query)
    #         conn.commit()
    #         res_ = cursor.fetchone()
    #
    #         user_id_order, user_vehicle_id_db, start_datetime_db = res_
    #         user_id = get_user_id(email)
    #
    #         if user_id_order != user_id:
    #             abort(403, description='It is not your tire service order!')
    #
    #         if (new_order_date is None and new_user_vehicle_id is None) or \
    #                 (new_order_date == start_datetime_db and new_user_vehicle_id == user_vehicle_id_db):
    #             abort(400, description='Ok. Nothing needs to be changed :)')
    #
    #         if not new_order_date or new_order_date == start_datetime_db:
    #             order_date_to_db = start_datetime_db
    #             new_order_date = 'The tire service date has not been changed'
    #         else:
    #             if datetime.datetime.strptime(new_order_date[:10], '%Y-%m-%d') < \
    #                     datetime.datetime.strptime(str(datetime.datetime.now())[:10], '%Y-%m-%d'):
    #                 abort(400, description='The new tire service date can not be earlier than today')
    #             order_date_to_db = new_order_date
    #
    #         if not new_user_vehicle_id or new_user_vehicle_id == user_vehicle_id_db:
    #             user_vehicle_id_to_db = user_vehicle_id_db
    #             new_user_vehicle_id = 'The vehicle id has not been changed'
    #         else:
    #             user_id_vehicle = get_value_from_table('user_id', 'user_vehicle', 'user_vehicle_id', new_user_vehicle_id)
    #             if user_id_vehicle != user_id:
    #                 abort(403, description='It is not your vehicle! Somebody call the police!')
    #             user_vehicle_id_to_db = new_user_vehicle_id
    #
    #         sql_query = """UPDATE tire_service_order SET start_datetime = '{0}', user_vehicle_id = '{1}'
    #                     WHERE service_order_id = '{2}'""".format(order_date_to_db, user_vehicle_id_to_db, service_order_id)
    #         cursor.execute(sql_query)
    #         conn.commit()
    #
    #         result = {
    #             'tire service order': service_order_id,
    #             'old_vehicle_id': user_vehicle_id_db,
    #             'new_vehicle_id': new_user_vehicle_id,
    #             'old_order_date': start_datetime_db,
    #             'new_order_date': new_order_date
    #         }
    #
    #         return jsonify(result)

    elif request.method == 'DELETE':
        email = request.form.get('email')
        token = request.form.get('token')
        service_order_id = request.form.get('service_order_id')

        required_fields = {
            'email': email,
            'token': token,
            'service_order_id': service_order_id
        }
        check_required_fields(required_fields)

        user_authentication(email, token)
        r.expire(email, 600)
        check_db_connection()

        try:
            service_order_id = int(service_order_id)
        except ValueError:
            abort(400, description='The <service_order_id> should contain only numbers')

        check_tire_service_order_exists(service_order_id)

        # get the initial data about the tire_service_order
        sql_query = """SELECT user_id, user_vehicle_id, manager_id, start_datetime FROM tire_service_order 
                                        WHERE service_order_id = '{0}';""".format(service_order_id)
        cursor.execute(sql_query)
        conn.commit()
        user_id, user_vehicle_id, manager_id, start_datetime = cursor.fetchone()

        if start_datetime < datetime.datetime.now():
            abort(400, description='You cannot delete a service order that has started')

        if get_user_id(email) != user_id:
            abort(403, description='It is not your tire service order!')

        sql_query = """DELETE FROM tire_service_order WHERE service_order_id = '{0}'""".format(service_order_id)
        cursor.execute(sql_query)
        conn.commit()

        text = 'Tire service order ID {{ name }} has been deleted'
        template = Template(text)
        result = {
            "confirmation": template.render(name=service_order_id)
        }
        return jsonify(result)
    else:
        abort(405)


@app.route("/tire_service_order/task",
           methods=['GET', 'POST', 'DELETE'])  # add new/change/delete a task to the user's service order
def task():
    if request.method == 'GET':
        return 'Temporarily closed for maintenance'

    # add a task to the list_of_works
    elif request.method == 'POST':
        return 'Temporarily closed for maintenance'
        # email = request.form.get('email')
        # token = request.form.get('token')
        # service_order_id = request.form.get('service_order_id')
        # task_name = request.form.get('task_name')
        # numbers_of_task = request.form.get('numbers_of_tasks')
        #
        # if not token or not email or not service_order_id or not task_name or not numbers_of_task:
        #     abort(400, description='The token, email, service_order_id and task_name are required')
        #
        # if not str(numbers_of_task).isdigit() or not str(service_order_id).isdigit():
        #     abort(400, description='Please, provide a numbers of tasks and service_order_id in digits')
        #
        # user_authentication(email, token)
        #
        # r.expire(email, 600)
        #
        # check_db_connection()
        # # to delete if ok
        # # sql_query = """SELECT user_id FROM tire_service_order WHERE service_order_id = '{0}';""".format(service_order_id)
        # # cursor.execute(sql_query)
        # # conn.commit()
        # # res_ = cursor.fetchone()
        #
        # if get_user_id(email) != get_value_from_table('user_id', 'tire_service_order', 'service_order_id', service_order_id):
        #     abort(403, description='It is not your tire service order!')
        # # to delete if ok
        # # sql_query = """SELECT task_id FROM tasks WHERE task_name = '{0}';""".format(task_name)
        # # cursor.execute(sql_query)
        # # conn.commit()
        # # res_ = cursor.fetchone()
        # task_id = get_value_from_table('task_id', 'tasks', 'task_name', task_name)
        #
        # if not task_id:
        #     abort(404, description='Sorry, we do not offer this service')
        #
        # for _ in range(int(numbers_of_task)):
        #
        #     sql_query = """INSERT INTO list_of_works (service_order_id, task_id)
        #                     VALUES ('{0}', '{1}');""".format(service_order_id, task_id)
        #     cursor.execute(sql_query)
        #     conn.commit()
        #
        # if int(numbers_of_task) == 1:
        #     result = {
        #         'confirmation': 'The ' + task_name + ' task is successfully added to your tire_service_order ID ' \
        #                         + service_order_id
        #     }
        # else:
        #     result = {
        #         'confirmation': 'tasks for ' + task_name + ' in the amount of ' + numbers_of_task + \
        #              ' have been successfully added to your tire_service_order ID ' + service_order_id
        #     }
        #
        # return jsonify(result)

    elif request.method == 'DELETE':
        return 'Temporarily closed for maintenance'
        # email = request.form.get('email')
        # token = request.form.get('token')
        # service_order_id = request.form.get('service_order_id')
        # task_number = request.form.get('task_number')
        #
        # if not token or not email or not service_order_id:
        #     abort(400, description='The token, email, service_order_id are required')
        #
        # if not str(service_order_id).isdigit():
        #     abort(400, description='Please, provide the service_order_id in digits')
        #
        # user_authentication(email, token)
        # r.expire(email, 600)
        #
        # check_db_connection()
        # # to delete if ok
        # # sql_query = """SELECT user_id FROM tire_service_order WHERE service_order_id = '{0}';""".format(service_order_id)
        # # cursor.execute(sql_query)
        # # conn.commit()
        # # res_ = cursor.fetchone()
        #
        # if get_user_id(email) != get_value_from_table('user_id', 'tire_service_order', 'service_order_id', service_order_id):
        #     abort(403, description='It is not your tire service order!')
        #
        # if not task_number:
        #
        #     sql_query = """SELECT task_name, task_duration, task_cost, s.first_name, s.last_name,
        #                 m.first_name, m.last_name, work_id
        #                 FROM list_of_works
        #                 JOIN tasks USING (task_id)
        #                 JOIN staff as s USING (worker_id)
        #                 JOIN tire_service_order USING (service_order_id)
        #                 JOIN managers as m USING (manager_id)
        #                 WHERE service_order_id  = {0}""".format(service_order_id)
        #     cursor.execute(sql_query)
        #     conn.commit()
        #     res = cursor.fetchall()
        #
        #     result = {}
        #     for i in res:
        #         name = 'task № ' + str(i[7])
        #         result[name] = {
        #             'task name': i[0],
        #             'task duration': str(i[1]),
        #             'task cost': i[2],
        #             'worker first name': i[3],
        #             'worker last name': i[4],
        #             'manager first name': i[5],
        #             'manager last name': i[6]
        #         }
        #     return jsonify(result)
        #
        # else:
        #
        #     if not str(task_number).isdigit():
        #         abort(400, description='Please, provide the task_number in digits')
        #
        #     sql_query = """SELECT work_id FROM list_of_works WHERE service_order_id = {0}""".format(service_order_id)
        #     cursor.execute(sql_query)
        #     res = cursor.fetchall()
        #
        #     flag = False
        #     for i in res:
        #         if int(task_number) == i[0]:
        #             flag = True
        #             break
        #
        #     if not flag:
        #         abort(404, description='Incorrect task number')
        #
        #     sql_query = """DELETE FROM list_of_works WHERE work_id = {0}""". format(task_number)
        #     cursor.execute(sql_query)
        #     conn.commit()
        #
        #     text = 'The task number {{ name }} has been deleted'
        #     template = Template(text)
        #
        #     result = {
        #         "confirmation": template.render(name=task_number),
        #     }
        #     return jsonify(result)
    else:
        abort(405)


@app.route("/admin/push_file", methods=['POST'])
def push():
    if request.method == 'POST':
        email = request.form.get('email')
        token = request.form.get('token')
        file_name = request.form.get('file_name')

        required_fields = {
            'email': email,
            'token': token
        }
        check_required_fields(required_fields)
        user_authentication(email, token)
        r.expire(email, 600)
        admin_authorization(email)
        try:
            repository.git.add(file_name)
            repository.git.commit(m='update' + str(file_name))
            origin = repository.remote(name='origin')
            origin.push()
            return 'pushed', 200
        except:
            return 'error', 500
    else:
        abort(405)


@app.route("/admin/password", methods=['POST', 'PATCH'])
def password():
    # user password recovery (this can only be done by an admin)
    if request.method == 'POST':
        email = request.form.get('email')
        token = request.form.get('token')
        user_email = request.form.get('user_email')

        required_fields = {
            'email': email,
            'token': token,
            'user_email': user_email
        }
        check_required_fields(required_fields)

        user_authentication(email, token)
        r.expire(email, 600)
        check_db_connection()

        admin_authorization(email)
        validate_email(user_email)
        check_user_exists('', user_email)

        with FileReadBackwards("user_auth.txt", encoding="utf-8") as file:
            for line in file:
                line_data = line.split('/')
                if line_data[2] == user_email and line_data[4] != '!password!':
                    user_password = line_data[4]

        result = {
            'user_email': user_email,
            'user_password': user_password
        }
        return jsonify(result)

    # change the user's password
    elif request.method == 'PATCH':
        email = request.form.get('email')
        token = request.form.get('token')
        user_email = request.form.get('user_email')
        new_password = request.form.get('new_password')

        required_fields = {
            'email': email,
            'token': token,
            'user_email': user_email,
            'new_password': new_password
        }
        check_required_fields(required_fields)

        user_authentication(email, token)
        r.expire(email, 600)
        check_db_connection()

        admin_authorization(email)
        validate_email(user_email)
        check_user_exists('', user_email)
        validate_password(new_password)

        hash_password, salt = generate_password_hash(new_password)
        user_id = get_value_from_table('user_id', 'users', 'email', user_email)

        sql_query = """UPDATE users SET password = '{0}', salt = '{1}' WHERE user_id = '{2}';""". \
            format(hash_password, salt, user_id)
        cursor.execute(sql_query)
        conn.commit()

        save_to_file(user_id, user_email, new_password, 'admin_change_password')

        result = {
            "user_id": user_id,
            "email": user_email,
            "confirmation": 'The password has been changed'
        }
        return jsonify(result)
    else:
        abort(405)


@app.route("/admin/user", methods=['PATCH', 'DELETE'])
def user():
    # mark the user as active (this can be done only by the admin)
    if request.method == 'PATCH':
        email = request.form.get('email')
        token = request.form.get('token')
        user_email = request.form.get('user_email')

        required_fields = {
            'email': email,
            'token': token,
            'user_email': user_email
        }
        check_required_fields(required_fields)

        user_authentication(email, token)
        r.expire(email, 600)
        check_db_connection()

        check_user_exists('does not exist', user_email)
        admin_authorization(email)

        sql_query = """UPDATE users SET active = 'True' WHERE email = '{0}'""".format(user_email)
        cursor.execute(sql_query)
        conn.commit()

        sql_query = """SELECT user_id, first_name, last_name FROM users WHERE email = '{0}'""".format(user_email)
        cursor.execute(sql_query)
        conn.commit()
        user_id, first_name, last_name = cursor.fetchone()

        text = 'User {{ name }} (ID {{ id }}) has been successfully activated'
        template = Template(text)
        result = {
            'confirmation': template.render(name=first_name + ' ' + last_name, id=user_id)
        }

        return jsonify(result)

    # delete the user (this can be done only by the admin)
    elif request.method == 'DELETE':
        email = request.form.get('email')
        token = request.form.get('token')
        user_email = request.form.get('user_email')

        required_fields = {
            'token': token,
            'email': email,
            'user_email': user_email
        }
        check_required_fields(required_fields)

        user_authentication(email, token)
        r.expire(email, 600)
        check_db_connection()

        admin_authorization(email)

        sql_query = """SELECT first_name, last_name, user_id FROM users WHERE email = '{0}'""".format(user_email)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()

        first_name, last_name, user_id = res_

        sql_query = """DELETE FROM users WHERE email = '{0}'""".format(user_email)
        cursor.execute(sql_query)
        conn.commit()

        save_to_file(user_id, user_email, '!password!', 'user-deleted-by_admin')

        text = 'R.I.P {{ name }}, i will miss you :('
        template = Template(text)
        result = {
            'confirmation': template.render(name=first_name + ' ' + last_name)
        }

        return jsonify(result)
    else:
        abort(405)

if __name__ == '__main__':
    app.run()
