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

def user_exists(where, email):
    if conn:
        sql_query = "SELECT user_id FROM users WHERE {0} = '{1}'".format(where, email)
        cursor.execute(sql_query)
        conn.commit()
        usr_id_ = cursor.fetchone()

        if not usr_id_:
            return False
    return True


def vehicle_exists(user_vehicle_id):
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


# def shelf_avail(size_name):
#     if conn:
#         sql_query = """SELECT shelf_id FROM warehouse WHERE size_id = '{0}'
#                         AND available = 'True'""".format(size_one_by_var('size_id', 'size_name', size_name))
#         cursor.execute(sql_query)
#         conn.commit()
#         avail = cursor.fetchone()
#
#         if avail:
#             return True
#     return False


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
    return bool(res_)


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


def push_user_auth():
    repository.git.add('user_auth.txt')
    repository.git.commit(m='update user_auth.txt')
    repository.git.push()


def get_tire_service_order():
    """Get all data on user's """

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