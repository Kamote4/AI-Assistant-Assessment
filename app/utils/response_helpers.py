from flask import jsonify


def success_response(data: dict, status_code: int = 200):
    """Return a standardised success JSON response."""
    return jsonify({"status": "ok", "data": data}), status_code


def error_response(message: str, status_code: int = 400):
    """Return a standardised error JSON response."""
    return jsonify({"status": "error", "message": message}), status_code
