from flask import jsonify

from package import app


@app.errorhandler(400)
def bad_request(e):
    return jsonify(error=str(e)), 400


@app.errorhandler(404)
def not_found(e):
    return jsonify(error=str(e)), 404


@app.errorhandler(405)
def wrong_method(e):
    return jsonify(error=str(e)), 405


@app.errorhandler(403)
def forbidden(e):
    return jsonify(error=str(e)), 403


@app.errorhandler(401)
def unauthorized(e):
    return jsonify(error=str(e)), 401


@app.errorhandler(503)
def db_conn_error(e):
    return jsonify(error=str(e)), 503