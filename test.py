import random
import psycopg2
# from file_read_backwards import FileReadBackwards
import os
import bcrypt
import git
from git import Repo
from os import path
import datetime
from datetime import date
# from defs import *
import re
# from defs import get_value_from_table
from jinja2 import Template


conn = psycopg2.connect(dbname='user_20_db', user='user_20', password='123', host='159.69.151.133', port='5056')
cursor = conn.cursor()

def qwe():
    with open('user_auth.txt', 'r+') as file_user_auth:
        for line in file_user_auth:
            r = line.split('(separator)')
            separator = '(separator)'

            email = r[0]
            user = 'user'
            password = r[2] + str(random.randint(1, 10))
            stroka = email + separator + user + separator + password
            file_user_auth.write(stroka)
            file_user_auth.write('\n')

def users_from_db():
    separator = '(separator)'
    if conn:
        sql_query = "SELECT user_id, email, pass FROM users"
        cursor.execute(sql_query)
        conn.commit()
        r_ = cursor.fetchall()
        print(r_)
        # cursor.close()
        with open('user_auth.txt', 'r+') as file_user_auth:
            for i in range(len(r_)):
                user_id = str(r_[i][0])
                user_email = str(r_[i][1])
                user_password = str(r_[i][2])
                timestamp_now = str(datetime.datetime.now())[:22] + str(datetime.datetime.now().astimezone())[26:]
                stroka = timestamp_now + separator + user_id + separator + user_email + separator + 'user-registered' + separator + user_password + '\n'
                file_user_auth.write(stroka)

def auth(email):
    with FileReadBackwards('user_auth.txt', encoding='utf-8') as file_user_auth:
        for line in file_user_auth:
            #
            # user_email = line.split('(separator)')[0]
            if email in line.split('(separator)')[0]:
                return line.split('(separator)')[2]

def salt_to_base():
    sql_query = "SELECT email, pass FROM users"
    cursor.execute(sql_query)
    conn.commit()
    r_ = cursor.fetchall()

    for i in range(len(r_)):
        email = r_[i][0]
        passw = r_[i][1]
        salt = bcrypt.gensalt(5)
        password = bcrypt.hashpw(str.encode(passw), salt)
        sql_query = """UPDATE users SET salt = '{0}', password = '{1}' WHERE email = '{2}'""".format(salt.decode(), password.decode(), email)
        cursor.execute(sql_query)
        conn.commit()

def gen_reg(email, password):
    separator = '(separator)'

    with open('user_auth.txt', 'a+') as file_user_auth:
        stroka = email + separator + 'user' + separator + password + '\n'
        print(stroka)
        file_user_auth.write(stroka)

def generate_password_hash_and_salt(password, salt):
    if salt is None:
        salt = bcrypt.gensalt(5)
    password = bcrypt.hashpw(str.encode(password), salt)
    return password.decode(), salt.decode()

repository = Repo('/QA/Git/Course')
def push():
    repository.git.add('user_auth.txt')
    repository.git.commit(m='update user_auth.txt')
    repository.git.push()

def wh():
    sql_query = """SELECT shelf_id, size_id, available FROM warehouse WHERE available = 'False'
                                                    AND size_id = '{0}'""".format(1)
    cursor.execute(sql_query)
    conn.commit()
    res_ = cursor.fetchall()

    print(res_)

    if res_:
        print('None')
    else:
        print('Not None')

def user_exists(where, email):
    sql_query = """SELECT user_id FROM users WHERE {0} = '{1}'""".format(where, email)
    cursor.execute(sql_query)
    conn.commit()
    usr_id_ = cursor.fetchone()
    # cursor.close()

    if usr_id_:
        print(usr_id_)
        return True
    return False

def vehicle_exists(u_veh_id):
    sql_query = """SELECT user_id FROM user_vehicle WHERE u_veh_id = '{0}'""".format(u_veh_id)
    cursor.execute(sql_query)
    conn.commit()
    res_ = cursor.fetchone()
    # cursor.close()

    if res_:
        return True
    return False


def test_managers_no_mat_view():
    sql_query = """SELECT worker_id, COUNT(manager_id) FROM staff AS s LEFT JOIN tire_service_order AS tso
                    ON tso.manager_id = s.worker_id WHERE available = True AND position_id = 2
                    GROUP BY worker_id HAVING COUNT(manager_id) < 5"""
    cursor.execute(sql_query)
    conn.commit()
    res_ = cursor.fetchall()
    # cursor.close()

    if not res_:
        result = 'Sorry, all managers are busy'
    else:
        result = 'There is some available managers'
    return result

def test_managers_mat_view():
    sql_query = """SELECT manager_id, COUNT(manager_id) FROM managers LEFT JOIN tire_service_order 
                    USING (manager_id) WHERE available = True GROUP BY manager_id HAVING COUNT(manager_id) < 5"""
    cursor.execute(sql_query)
    conn.commit()
    res_ = cursor.fetchall()

    sql_query = """SELECT manager_id, serv_order_id FROM managers LEFT JOIN tire_service_order 
                        USING (manager_id)"""  # WHERE available = True  HAVING COUNT(manager_id) < 5"""
    cursor.execute(sql_query)
    conn.commit()
    res_2 = cursor.fetchall()

    # cursor.close()
    print(res_)
    print(res_2)
    if not res_:
        result = 'Sorry, all managers are busy'
    else:
        result = 'There is some available managers'
    return result


def size_one_by_var(select, where, what):
    if conn:
        sql_query = """SELECT {0} FROM sizes WHERE {1} = '{2}'""".format(select, where, what)
        cursor.execute(sql_query)
        conn.commit()
        res_ = cursor.fetchone()
        # cursor.close()

        if not res_:
            return None
        return res_[0]


def validate_names(name_type, name):
    valid_pattern = re.compile("^[a-z ,.'-]+$", re.I)
    return_val = {'result': True, 'text': 'Ok'}
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


def validate(name: str)->bool:
    valid_pattern = re.compile("^[a-z ,.'-]+$", re.I)
    return bool(valid_pattern.match(name))

# print(validate("test_test"))
# f_name = 'test_test'
# check_first_name = validate_names('first name', f_name)
# # if not check_first_name['result']:
# if not check_first_name['result']:
#     print(check_first_name['text'])
# new_size_id = size_one_by_var('size_id', 'size_name', '25')
# if not new_size_id:
#     print('Unknown tire size, add the tire size data to the sizes DB')
# else:
#     print('Ok')


# new_order_date = '2021-09-30 14:00:00'
# if datetime.datetime.strptime(new_order_date[:10], '%Y-%m-%d') < datetime.datetime.strptime(str(datetime.datetime.now())[:10], '%Y-%m-%d'):
#     print('Date before today')
# else:
#     print('Ok')

# regex = ^([a-zA-Z]{2,}\s[a-zA-Z]{1,}'?-?[a-zA-Z]{2,}\s?([a-zA-Z]{1,})?)
#
# if not any(char in regex for char in password):
#     print('The password must contain at least one digit')

# valid_pattern = re.compile("^[a-z ,.'-]+$", re.I)
# print(bool(valid_pattern.match('name')))

#
# print(validate("John"))

# print(test_managers_mat_view())
# if user_exists('email', 'test@test3.ru'):
#     # print(user_exists('email', 'test@test33.ru'))
#     print('Yes')
# else:
#     print("No")

# print(datetime.datetime.now(tz))
# print(str(datetime.datetime.now().astimezone())[26:])
# print(vehicle_exists(1))

# wh()
# push()
# gen_reg('test_gen@test.ru', 'WqqwW3q')
# salt_to_base()
# email = 'dam@io.as3'
# print(auth(email))
# users_from_db()

# my_str = "hello world"
# my_str_as_bytes = str.encode(my_str)
# print(my_str_as_bytes) # ensure it is byte representation
# my_decoded_str = my_str_as_bytes.decode()
# print(my_decoded_str)

# password = 'qwe'
# salt = None
# hash_password, salt = generate_password_hash_and_salt(password, salt)
# print(password, hash_password, salt)



# print(res[0][0])


# task_number = 19
# sql_query = """SELECT work_id FROM list_of_works WHERE serv_order_id = {0}""".format(2)
# cursor.execute(sql_query)
#
# res = cursor.fetchall()
#
# flag = False
# for i in res:
#     if task_number == i[0]:
#         flag = True
#         break
#
# if not flag:
#     print('Not ok')
# else:
#     print('Ok')

# print(date(datetime.datetime.now().year + 1, datetime.datetime.now().month, datetime.datetime.now().day))

# source = [(1,2), (2,3), (3,4)]
# result = [id[0] for id in source]
# print(result)

# sql_query = """SELECT user_id, first_name, last_name, phone
#                 FROM users WHERE email = '{0}';""".format('test@test5.test')
# cursor.execute(sql_query)
# conn.commit()
# res_ = cursor.fetchone()
#
# user_id_db, f_name_db, l_name_db, phone_db = [data for data in res_]
# print(user_id_db, f_name_db, l_name_db, phone_db)

# res = ['3', '2', '1', '5', '7']
# # shelves = []
# # for i in res:
# #     shelves.append(i[0])
# #
# # shelf_id = min(shelves)
# shelf_id = min[shelves for shelves in res]
# print(shelf_id)


# tire_change = 'yes'
# tire_repair = 'yes'
# wheel_balancing = 'yes'
# numbers = 4
#
# if tire_change == 'yes':
#     tire_change = 'tire_change'
# if tire_repair == 'yes':
#     tire_repair = 'tire_repair'
# if wheel_balancing == 'yes':
#     wheel_balancing = 'wheel_balancing'
#
# sql_query = """select sum
#                 (
#                     case
# 	                    when task_name = '{0}' then task_duration
# 	                    when task_name = '{1}' then task_duration
# 	                    when task_name = '{2}' then task_duration
# 	                    else '00:00:00'
# 	                end
#                 ) as summ
#                 from tasks""".format(tire_change, tire_repair, wheel_balancing)
# cursor.execute(sql_query)
# conn.commit()
# res_ = cursor.fetchone()
# service_duration = numbers * res_[0]
# print(service_duration)


# sql_query = """WITH dates_intersection AS (
#                             SELECT DISTINCT worker_id FROM tire_service_order WHERE
#                                 (
#                                     start_date BETWEEN '{0}' AND '{1}'
#                                     OR
#                                     stop_date BETWEEN '{0}' AND '{1}'
#                                     OR
#                                     '{0}' BETWEEN start_date AND stop_date
#                                     OR
#                                     '{1}' BETWEEN start_date AND stop_date
#                                 )
#                             AND size_id = {2})
#
#                             SELECT shelf_id FROM storage_orders WHERE shelf_id NOT IN
#                             (SELECT shelf_id FROM dates_intersection) AND size_id = {2}""". \
#     format(start_date, stop_date, size_id)
# cursor.execute(sql_query)
# res_ = cursor.fetchall()


# sql_query = """CREATE OR REPLACE VIEW temp AS
#                                 SELECT
#                                     service_order_id,
#                                     user_id,
#                                     start_datetime,
#                                     user_vehicle_id,
#                                     tso.manager_id,
#                                     task_id,
#                                     task_name,
#                                     task_cost,
#                                     task_duration,
#                                     low.worker_id,
#                                     p.position_id,
#                                     position_name,
#                                     s.first_name,
#                                     s.last_name
#                                 FROM tire_service_order AS tso
#                                 LEFT JOIN list_of_works AS low USING (service_order_id)
#                                 LEFT JOIN tasks AS t USING (task_id)
#                                 LEFT JOIN staff AS s USING (worker_id)
#                                 LEFT JOIN positions AS p USING (position_id)
#                                 LEFT JOIN staff AS st ON st.worker_id = tso.manager_id
#                                 WHERE user_id = '{0}';""".format(2)
# cursor.execute(sql_query)
# conn.commit()
#
# sql_query = """SELECT SUM(task_cost) FROM temp
#                                 WHERE service_order_id = '{0}'""".format(22)
# cursor.execute(sql_query)
# conn.commit()
# res_cost = cursor.fetchone()
#
# summ = get_value_from_table('SUM(task_cost', 'temp', 'service_order_id', 22)
#
# print(res_cost)
# print(summ)

# first = ''
# second = 'adsfsd'
# third = None
#
# print('Ok') if any((first, second, third)) else print('Not Ok')

# email = 'cds'
# password = 'q'
# open = '231'
# datep = '2021-10-13'
# numbers = None
#
# fields = {
#     'email': email,
#     'password': password,
#     'open': open,
#     'datep': datep,
#     'numbers': numbers
# }
# if not all(fields.values()):
#     text = 'The {{ name }} are required!'
#     template = Template(text)
#     name = ', '.join(map(str, fields))
#     print(template.render(name=name))
# else:
#     print( 'All ok' )

# sql_query = """SELECT DISTINCT vehicle_name FROM vehicle;"""
# cursor.execute(sql_query)
# conn.commit()
#
# res_ = list(veh[0] for veh in cursor.fetchall())
# print(res_)
#
# name = 'car'
# if name not in res_:
#     print('Not in')
# else:
#     print('In')

# size_id = 7
# sql_query = """SELECT w.shelf_id FROM storage_orders RIGHT JOIN warehouse AS w USING(shelf_id) WHERE
#                         storage_order_id IS NULL AND active = True AND w.size_id = {0};""".format(size_id)
# cursor.execute(sql_query)
# # res = cursor.fetchall()
# res = list(veh[0] for veh in cursor.fetchall())
# # Если есть:
# if res:
#     # Если таких несколько, выбираем меньшую по ИД
#     print(res)
#     print(min(res))
#     s = min(res)
#     print(s)


# start_date = '2021-11-02 14:05'
# start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d %H:%M')
# ops = str(start_date.date())
# print(int(start_date.hour))
# print(ops)
# date_w = date(datetime.date.today().year, datetime.date.today().month, datetime.date.today().day)
# if start_date > date_w:
#     print('more')
# else:
#     print('less')

# order_type = 1
# sql_query = """SELECT DISTINCT service_type_name FROM tire_service_order_type;"""
# cursor.execute(sql_query)
# conn.commit()
# order_types = list(types[0] for types in cursor.fetchall())
#
# try:
#     order_type = order_type.lower()
# except AttributeError:
#     print('The <active_only> should be string')
# else:
#     if order_type not in order_types:
#         str_order_types = ''
#         for types in order_types:
#             str_order_types += '<' + str(types) + '>' + ' or '
#         print('The <active_only> should be ' + str_order_types[:len(str_order_types) - 4])
#     else:
#         print('All ok')
# print(order_type)

# sql_query = """SELECT DISTINCT service_type_name FROM tire_service_order_type;"""
# cursor.execute(sql_query)
# conn.commit()

# for size in range(1, 8):
#     for _ in range(10):
#         sql_query = """INSERT INTO warehouse (size_id, active) VALUES ('{0}', True);""".format(size)
#         cursor.execute(sql_query)
#         conn.commit()

# worker_id = 1
# dur = '00:30'
# dur = datetime.datetime.strptime(dur, '%H:%M').hour * 60 + datetime.datetime.strptime(dur, '%H:%M').minute
# sql_query = """SELECT hour_cost FROM staff WHERE worker_id = '{0}'""".format(worker_id)
# cursor.execute(sql_query)
# conn.commit()
# hour_cost = cursor.fetchone()[0]
#
# cost = hour_cost * dur / 60
# print(hour_cost)
# print(dur)
# print(cost)

sql_query = """DELETE FROM tire_service_order WHERE service_order_id = 45"""
cursor.execute(sql_query)
conn.commit()