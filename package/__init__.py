import psycopg2
import redis
from flask import Flask
from flask_swagger_ui import get_swaggerui_blueprint
from git import Repo

app = Flask(__name__)

SWAGGER_URL = '/static/'
API_URL = '/static/swagger.yaml'
swaggerui_blueprint = get_swaggerui_blueprint(SWAGGER_URL, API_URL, config={'app_name': "Service_Station"})

app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

repository = Repo('~/PetProject_Service_Station')
# logging

r = redis.StrictRedis(host='localhost', port=6379, db=0, charset="utf-8", decode_responses=True)
conn = psycopg2.connect(dbname='user_20_db', user='user_20', password='123', host='159.69.151.133', port='5056')
cursor = conn.cursor()