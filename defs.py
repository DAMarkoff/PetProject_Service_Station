from flask import Flask, request, jsonify, abort
import psycopg2
import re
import redis
import datetime
import bcrypt
import  git
from git import Repo
import random

repository = Repo('~/server/Course')
r = redis.StrictRedis(host='localhost', port=6379, db=0, charset="utf-8", decode_responses=True)
conn = psycopg2.connect(dbname='user_20_db', user='user_20', password='123', host='159.69.151.133', port='5056')
cursor = conn.cursor()

def user_exists(where: str, email: str) -> bool:
    """Checks that the user with this email is already registered"""
    if conn:
        sql_query = "SELECT user_id FROM users WHERE {0} = '{1}'".format(where, email)
        cursor.execute(sql_query)
        conn.commit()
        usr_id_ = cursor.fetchone()

        if not usr_id_:
            return False
    return True


def vehicle_exists(user_vehicle_id: str) -> bool:
    """Checks if the vehicle with this vehicle_id exists"""
    sql_query = """SELECT user_id FROM user_vehicle WHERE user_vehicle_id = '{0}'""".format(user_vehicle_id)
    cursor.execute(sql_query)
    conn.commit()
    res_ = cursor.fetchone()

    if res_:
        return True
    return False


def storage_order_exists(storage_order_id):
    sql_query = """SELECT user_id FROM storage_orders WHERE storage_order_id = '{0}';""".format(storage_order_id)
    cursor.execute(sql_query)
    conn.commit()
    res_ = cursor.fetchone()

    if res_:
        return True
    return False


def tire_service_order_exists(service_order_id):
    sql_query = """SELECT user_id FROM tire_service_order WHERE service_order_id = '{0}';""".format(service_order_id)
    cursor.execute(sql_query)
    conn.commit()
    res_ = cursor.fetchone()

    if res_:
        return True
    return False


def get_user_id(email):
    if conn:
        sql_query = "SELECT user_id FROM users WHERE email = '{0}'".format(email)
        cursor.execute(sql_query)
        conn.commit()
        usr_id_ = cursor.fetchone()

        return usr_id_[0]


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


def validate_names(name_type: str, name: str) -> dict:
    """Validate name - returns a dict with a bool(result) of validation and a str(text) with an error message if exists
    :type: object
    """
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
    return return_val


def validate(name: str) -> bool:
    """Validate name - match the name to the pattern"""
    valid_pattern = re.compile("^[a-z ,.'-]+$", re.I)
    return bool(valid_pattern.match(name))


def user_active(email: str) -> bool:
    sql_query = """SELECT active FROM users WHERE email = '{0}'""".format(email)
    cursor.execute(sql_query)
    conn.commit()
    res_ = cursor.fetchone()
    if res_[0]:
        return True
    return False


def get_value_from_table(select: str, from_db: str, where: str, what):
    if conn:
        sql_query = """SELECT {0} FROM {1} WHERE {2} = '{3}'""".format(select, from_db, where, what)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()

        if not res_:
            return None
        return res_[0]


def user_authorization(email, token):
    return_val = {'result': True, 'text': ''}
    if not user_exists('email', email):
        return_val['result'] = False
        return_val['text'] = 'The user does not exist. Please, register'
    else:
        if not (token == r.get(email)):
            return_val['result'] = False
            return_val['text'] = 'The token is invalid, please log in'
    return return_val


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


def generate_password_hash(password):
    salt = bcrypt.gensalt(5)
    password = bcrypt.hashpw(str.encode(password), salt)
    return password.decode(), salt.decode()


def choose_a_manager(date_to_query):
    return_val = {'result': True, 'manager_id': ''}
    # =========================================================================================================
    # Select a manager
    # someone who does not have a service order on the required order date
    sql_query = """SELECT manager_id FROM managers WHERE manager_id NOT IN 
                (SELECT DISTINCT manager_id FROM tire_service_order WHERE DATE(start_datetime) = '{0}')""" \
                    .format(date_to_query)
    cursor.execute(sql_query)
    conn.commit()
    res_ = cursor.fetchall()

    if res_:
        rand_id = random.randint(0, len(res_) - 1)
        manager_id = res_[rand_id][0]
        return_val['result'] = True
        return_val['manager_id'] = manager_id
    else:
        # someone who has the minimum number of service orders on the required order date
        sql_query = """WITH managers_load AS(
                            SELECT manager_id, count(manager_id) AS load_ FROM tire_service_order 
                            WHERE date(start_datetime) = '{0}' GROUP BY manager_id)

                            SELECT manager_id FROM managers_load
                            WHERE load_ in (SELECT MIN(load_) FROM managers_load)""".format(date_to_query)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchall()

        if res_:
            rand_id = random.randint(0, len(res_) - 1)
            manager_id = res_[rand_id][0]
            return_val['result'] = True
            return_val['manager_id'] = manager_id
        else:
            return_val['result'] = False
            return_val['manager_id'] = {'confirmation': 'There are no managers for the required time'}
    return return_val


def duration_of_service(tire_repair, tire_change, removing_installing_wheels, balancing,
                                                    wheel_alignment, camera_repair, numbers_of_wheels):
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
                                ) AS duration FROM tasks""".\
                            format(tire_repair, tire_change, removing_installing_wheels, balancing, camera_repair)
    cursor.execute(sql_query)
    conn.commit()
    res_ = cursor.fetchone()
    service_duration = numbers_of_wheels * res_[0]

    sql_query = """SELECT SUM
                    (
                        CASE 
                            WHEN task_name = '{0}' THEN task_duration 
                            ELSE '00:00:00'
                        END
                    ) AS duration
                    FROM tasks""".format(wheel_alignment)
    cursor.execute(sql_query)
    conn.commit()
    res_ = cursor.fetchone()

    service_duration += res_[0]

    return service_duration


def choose_a_worker_and_insert_the_tasks(user_id, order_date, end_time, user_vehicle_id, manager_id,
                                         tasks, numbers_of_wheels, order_type, service_duration, service_type_id):
    return_val = {'result': True, 'value': ''}
    # Запрос на свободных работяг в нужное время
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
    res_ = cursor.fetchall()
    if res_:
        rand_id = random.randint(0, len(res_) - 1)
        worker_id = res_[rand_id][0]
        created = datetime.datetime.now()
        sql_query = """INSERT INTO tire_service_order 
                    (user_id, start_datetime, stop_datetime, user_vehicle_id, manager_id, service_type_id, created)
                    VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}');""".\
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
        res_ = cursor.fetchone()
        service_order_id = res_[0]

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
                       SELECT first_name, last_name, email, phone FROM managers WHERE manager_id = '{1}';""".\
                format(worker_id, manager_id)
        cursor.execute(sql_query)
        conn.commit()
        res_cost = cursor.fetchall()

        worker_first_name, worker_last_name, worker_email, worker_phone = res_cost[0]
        manager_first_name, manager_last_name, manager_email, manager_phone = res_cost[1]

        # get service order cost
        if service_order_tasks == []:
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