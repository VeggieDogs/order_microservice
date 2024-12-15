import os
import threading
import redis
import pymysql
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint
from flask import Flask, request, jsonify, send_from_directory
import logging
from datetime import datetime

app = Flask(__name__)
redis_client = redis.StrictRedis(host='localhost', port=6379, decode_responses=True)
CORS(app, origins="http://localhost:3000", methods=["GET", "POST"])
logging.basicConfig(level=logging.INFO)

@app.before_request
def before_request_logging():
    request.start_time = datetime.now()
    logging.info(f"Incoming request: {request.method} {request.path}")

@app.after_request
def after_request_logging(response):
    duration = datetime.now() - request.start_time
    duration_ms = int(duration.total_seconds() * 1000)
    logging.info(
        f"Completed request: {request.method} {request.path} "
        f"Status: {response.status_code} Duration: {duration_ms}ms"
    )
    return response
CORS(app)

SWAGGER_URL = '/docs'
API_URL = '/openapi.yaml'
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={'app_name': "Order API"}
)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

@app.route('/openapi.yaml')
def serve_openapi_spec():
    return send_from_directory(os.getcwd(), 'openapi.yaml')

db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME'),
    'port': int(os.getenv('DB_PORT', 3306))
}

def fetch_from_db(query, params=None):
    try:
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        return results
    except pymysql.MySQLError as err:
        return f"Error: {err}"
    finally:
        if conn:
            cursor.close()
            conn.close()
            
def insert_into_db(query, params):
    try:
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return "Success"
    except pymysql.MySQLError as err:
        return f"Error: {err}"
    finally:
        if conn:
            cursor.close()
            conn.close()

@app.route('/search_order', methods=['GET'])
def search_product():
    order_id = request.args.get('order_id')
    query = f"SELECT * FROM Orders WHERE order_id = {order_id}" if order_id else "SELECT * FROM Orders"
    results = fetch_from_db(query)
    
    if isinstance(results, str):
        return jsonify({"error": results}), 500
    if not results:
        return jsonify({"message": "No order found"}), 404
    
    result_list = []
    for row in results:
        result_list.append({
            "order_id": row[0],
            "quantity": row[1],
            "total_price": row[2],
            "purchase_time": row[3].strftime('%Y-%m-%d %H:%M:%S'),
            "status": row[4],
            "seller_id": row[5],
            "buyer_id": row[6],
            "product_id": row[7],
            "created_at": row[8].strftime('%Y-%m-%d %H:%M:%S'),
            "_links": {
                "self": {"href": f"/search_order?order_id={row[0]}"},
                "all_orders": {"href": "/search_order"},
                "create_order": {"href": "/post_order"},
                "orders_by_user": {"href": "/search_orders_by_id"}
            }
        })
    if not order_id:
        return jsonify({
            "message": "No order_id provided, returning all orders",
            "orders": result_list,
            "_links": {
                "self": {"href": "/search_order"},
                "create_order": {"href": "/post_order"},
                "orders_by_user": {"href": "/search_orders_by_id"}
            }
        }), 200
    return jsonify({"orders": result_list}), 200

@app.route('/search_orders_by_id', methods=['GET'])
def search_orders_by_id():
    user_id = request.args.get('user_id')
    role = request.args.get('role')
    
    if not user_id:
        return jsonify({"error": "user_id parameter is required"}), 400
    
    if role == 'seller':
        query = "SELECT * FROM Orders WHERE seller_id = %s"
    elif role == 'buyer':
        query = "SELECT * FROM Orders WHERE buyer_id = %s"
    else:
        query = """
            (SELECT * FROM Orders WHERE seller_id = %s)
            UNION
            (SELECT * FROM Orders WHERE buyer_id = %s)
        """
    params = (user_id,) if role in ['seller', 'buyer'] else (user_id, user_id)
    results = fetch_from_db(query, params)
    
    if isinstance(results, str):
        return jsonify({"error": results}), 500
    if not results:
        return jsonify({"message": "No orders found for this user ID"}), 404

    result_list = []
    for row in results:
        result_list.append({
            "order_id": row[0],
            "quantity": row[1],
            "total_price": float(row[2]),
            "purchase_time": row[3].strftime('%Y-%m-%d %H:%M:%S') if row[3] else None,
            "status": row[4],
            "seller_id": row[5],
            "buyer_id": row[6],
            "product_id": row[7],
            "created_at": row[8].strftime('%Y-%m-%d %H:%M:%S') if row[8] else None,
            "_links": {
                "self": {"href": f"/search_order?order_id={row[0]}"},
                "all_orders": {"href": "/search_order"},
                "create_order": {"href": "/post_order"}
            }
        })
    return jsonify({
        "orders": result_list,
        "_links": {
            "self": {"href": f"/search_orders_by_id?user_id={user_id}&role={role}"},
            "all_orders": {"href": "/search_order"},
            "create_order": {"href": "/post_order"}
        }
    }), 200

@app.route('/post_order', methods=['POST'])
def post_order():
    data = request.json
    required_fields = ["quantity", "total_price", "status", "seller_id", "buyer_id", "product_id"]
    
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    query = """
    INSERT INTO Orders (quantity, total_price, status, seller_id, buyer_id, product_id)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    params = (
        data["quantity"],
        data["total_price"],
        data["status"],
        data["seller_id"],
        data["buyer_id"],
        data["product_id"]
    )

    result = insert_into_db(query, params)
    if result == "Success":
        return jsonify({
            "message": "New order created",
            "_links": {
                "self": {"href": "/post_order"},
                "all_orders": {"href": "/search_order"},
                "orders_by_user": {"href": "/search_orders_by_id"}
            }
        }), 201
    else:
        return jsonify({"error": result}), 500

# A simple function to process received messages
def handle_message(message):
    print(f"Received message: {message['data']} on channel: {message['channel']}")

# Subscriber thread
def subscriber_thread():
    pubsub = redis_client.pubsub()
    pubsub.subscribe('order_created')  # Subscribe to the "order_created" channel
    print("Subscribed to 'order_created' channel")

    for message in pubsub.listen():
        if message['type'] == 'message':
            handle_message(message)

@app.before_first_request
def start_subscriber():
    # Start the subscriber in a separate thread
    thread = threading.Thread(target=subscriber_thread)
    thread.daemon = True
    thread.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8890, debug=True)
