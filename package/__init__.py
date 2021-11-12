import redis
from flask import Flask
from flask_swagger_ui import get_swaggerui_blueprint
from git import Repo

from package.db import conn

app = Flask(__name__)

SWAGGER_URL = '/swagger'
API_URL = '/static/swagger.yaml'
swaggerui_blueprint = get_swaggerui_blueprint(SWAGGER_URL, API_URL, config={'app_name': "Service_Station"})

app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

repository = Repo('~/PetProject_Service_Station')
# logging

r = redis.StrictRedis(host='localhost', port=6379, db=0, charset="utf-8", decode_responses=True)
cursor = conn.cursor()
