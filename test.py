import random
import psycopg2

conn = psycopg2.connect(dbname='user_20_db', user='user_20', password='123', host='159.69.151.133', port='5056')
cursor = conn.cursor()

sql_query = """CREATE VIEW temp AS
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
                        WHERE user_id = 2;"""
cursor.execute(sql_query)
conn.commit()

sql_query = """select * from temp"""
cursor.execute(sql_query)
conn.commit()
res_ = cursor.fetchone()

sql_query = """drop view temp"""
cursor.execute(sql_query)
conn.commit()

if res_ is None:
    print('ouch!')
else:
    print(res_[0])
