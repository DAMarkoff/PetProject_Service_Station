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