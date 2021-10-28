from flask import jsonify, abort
import psycopg2
import re
import redis
import datetime
import bcrypt
import random
from jinja2 import Template

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
            abort(400, description='The user does not exist')


def check_vehicle_exists(user_vehicle_id: int):
    """Checks that the vehicle with this vehicle_id exists"""
    if not get_value_from_table('user_id', 'user_vehicle', 'user_vehicle_id', user_vehicle_id):
        abort(400, description='The vehicle does not exist')


def check_storage_order_exists(storage_order_id: int):
    """Checks that the vehicle with this vehicle_id exists"""
    if not get_value_from_table('user_id', 'storage_orders', 'storage_order_id', storage_order_id):
        abort(400, description='The storage order does not exist')


def check_tire_service_order_exists(service_order_id: int):
    """Checks that the service order exists"""
    if not get_value_from_table('user_id', 'tire_service_order', 'service_order_id', service_order_id):
        abort(400, description='The tire service order does not exist')


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
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        abort(400, description='The email must contain @ and . chars')


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
    if not (token == r.get(email)):
        abort(401, description='The token is invalid, please log in')


def password_is_valid(salt, password, password_db):
    if str.encode(password_db) == bcrypt.hashpw(str.encode(password), str.encode(salt)):
        return True
    return False


def save_to_file(user_id, email, password, reason):
    separator = '/'
    with open('user_auth.txt', 'a+') as file_user_auth:
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
            abort(400, description='There are no managers for the required time')


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
               tasks['balancing'], tasks['camera_repair'])
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
        abort(400, description='There are no workers for the required time')


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


def create_tasks_for_the_service_order(tasks: dict, order_id: int, worker_id: int) -> int and list:
    service_order_tasks, service_order_cost = [], 0
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
            task_cost = get_value_from_table('task_cost', 'tasks', 'task_id', task_id)
            service_order_cost += int(task_cost)
            service_order_tasks.append({
                'task_name': task_name,
                'task_cost': task_cost
            })
    return service_order_cost, service_order_tasks


def get_employee_data(employee_id: int, employee_position: str) -> dict:
    employee_position_id = employee_position + '_id'
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


def choose_a_worker_and_insert_the_tasks(user_id, order_date, end_time, user_vehicle_id, manager_id,
                                         tasks, numbers_of_wheels, order_type, service_duration, service_type_id):
    return_val = {'result': True, 'value': ''}
    # Search for a worker without work
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
        worker_id = random.choice(res_) # -----------------------------------------------------------
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
        service_order_id = cursor.fetchone()[0]

        service_order_tasks, service_order_cost = [], 0
        for task in tasks:
            if task in ('tire_repair', 'camera_repair', 'tire_change', 'wheel_removal_installation', 'wheel_balancing'):
                count_tasks = numbers_of_wheels
            else:
                count_tasks = 1
            for _ in range(count_tasks):
                task_id = get_value_from_table('task_id', 'tasks', 'task_name', task)

                sql_query = """INSERT INTO list_of_works (service_order_id, task_id, worker_id)
                                VALUES ('{0}', '{1}', '{2}');""".format(service_order_id, task_id, worker_id)
                cursor.execute(sql_query)
                conn.commit()

                task_name = get_value_from_table('task_name', 'tasks', 'task_id', task_id)
                task_cost = get_value_from_table('task_cost', 'tasks', 'task_id', task_id)
                service_order_cost += int(task_cost)
                service_order_tasks.append({
                    'task_name': task_name,
                    'task_cost': task_cost
                })

        # get the manager's and worker's first and last names
        sql_query = """SELECT first_name, last_name, email, phone FROM staff WHERE worker_id = '{0}'
                       UNION ALL 
                       SELECT first_name, last_name, email, phone FROM managers WHERE manager_id = '{1}';""". \
            format(worker_id, manager_id)
        cursor.execute(sql_query)
        conn.commit()
        res_cost = cursor.fetchall()

        worker_first_name, worker_last_name, worker_email, worker_phone = res_cost[0]
        manager_first_name, manager_last_name, manager_email, manager_phone = res_cost[1]

        # get service order cost
        if not service_order_tasks:
            service_order_tasks.append({'confirmation': 'really strange situation, no tasks in order'})

        if service_order_tasks == 0:
            service_order_cost = 'Error! Sum is None!'

        result = ({
            'service_order_id': service_order_id,
            'user_vehicle_id': user_vehicle_id,
            'manager:': {
                'manager_id': manager_id,
                'manager_name': manager_first_name + ' ' + manager_last_name,
                'manager_email': manager_email,
                'manager_phone': manager_phone
            },
            'worker:': {
                'worker_id': worker_id,
                'worker_name': worker_first_name + ' ' + worker_last_name,
                'worker_email': worker_email,
                'worker_phone': worker_phone
            },
            'service order type': order_type,
            'order datetime': str(order_date),
            'estimated service duration': str(service_duration),
            'estimated end of service datetime': str(end_time),
            'service order cost': service_order_cost,
            'tasks': service_order_tasks
        })
        return_val['result'] = True
        return_val['value'] = jsonify(result)
    else:
        return_val['result'] = False
        return_val['value'] = jsonify({'confirmation': 'There are no workers for the required time'})

    return return_val
