import random
from flask import Flask, request, jsonify, abort
from jinja2 import Template
import psycopg2
import uuid
import re
import redis
import datetime
from flask_swagger_ui import get_swaggerui_blueprint
import bcrypt
import  git
from git import Repo

repository = Repo('~/server/Course')
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


def user_exists_by_id(user_id):
    if conn:
        sql_query = "SELECT user_id FROM users WHERE email = '{0}'".format(user_id)
        cursor.execute(sql_query)
        conn.commit()
        usr_id_ = cursor.fetchone()
        # cursor.close()

        if usr_id_:
            return True
    return False


def vehicle_exist(u_veh_id):
    sql_query = """SELECT user_id FROM user_vehicle WHERE u_veh_id = '{0}'""".format(u_veh_id)
    cursor.execute(sql_query)
    conn.commit()
    res_ = cursor.fetchone()
    # cursor.close()

    if res_:
        return True
    return False


def storage_order_exist(st_ord_id):
    sql_query = """SELECT user_id FROM storage_orders WHERE st_ord_id = '{0}';""".format(st_ord_id)
    cursor.execute(sql_query)
    conn.commit()
    res_ = cursor.fetchone()
    # cursor.close()

    if res_:
        return True
    return False


def tire_service_order_exist(serv_order_id):
    sql_query = """SELECT user_id FROM tire_service_order WHERE serv_order_id = '{0}';""".format(serv_order_id)
    cursor.execute(sql_query)
    conn.commit()
    res_ = cursor.fetchone()
    # cursor.close()

    if res_:
        return True
    return False


def token_exist(email, token):
    if token == r.get(email):
        return True
    return False


def get_user_id(email):
    if conn:
        sql_query = "SELECT user_id FROM users WHERE email = '{0}'".format(email)
        cursor.execute(sql_query)
        conn.commit()
        usr_id_ = cursor.fetchone()
        # cursor.close()

        return usr_id_[0]


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


def password_is_valid(salt, password, password_db):
    if str.encode(password_db) == bcrypt.hashpw(str.encode(password), str.encode(salt)):
        return True
    return False


def save_password_to_file(email, password, reason):
    separator = '(separator)'
    with open('user_auth.txt', 'a+') as file_user_auth:
        stroka = email + separator + reason + separator + password + '\n'
        file_user_auth.write(stroka)


def generate_password_hash(password):
    salt = bcrypt.gensalt(5)
    password = bcrypt.hashpw(str.encode(password), salt)
    return password.decode(), salt.decode()


def push_user_auth():
    repository.git.add('user_auth.txt')
    repository.git.commit(m='update user_auth.txt')
    repository.git.push()