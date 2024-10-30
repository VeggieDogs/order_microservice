import os
import pymysql
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)
CORS(app, origins="http://localhost:3000", methods=["GET", "POST"])

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
    'port': int(os.getenv('DB_PORT', 3306))  # Default port is 3306 if not provided
}


def fetch_from_db(query, params=None):
    """
    Connects to the database, executes the given query, and returns the result.
    
    Parameters:
    query (str): The SQL query to execute.
    params (tuple): Parameters to pass into the query (optional).
    
    Returns:
    list: The results of the query execution.
    """
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
    conn = None
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
    
    if order_id:
        query = f"SELECT * FROM Orders WHERE order_id = {order_id}"
    else:
        query = "select * from Orders"


    results = fetch_from_db(query)
    if not results:
        return jsonify({"message": "No order found"}), 404

    if isinstance(results, str):
        return jsonify({"error": results}), 500

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
            "created_at": row[8].strftime('%Y-%m-%d %H:%M:%S')
        })
    if not order_id:
        return jsonify({"message": "No order_id provided, returning all orders", "orders": result_list}), 200
    return jsonify({"orders": result_list}), 200

    
@app.route('/search_orders_by_id', methods=['GET'])
def search_orders_by_id():
    user_id = request.args.get('user_id')
    role = request.args.get('role')
    if not user_id:
        return jsonify({"error": "user_id parameter is required"}), 400
    if role == 'seller':
        query = "SELECT * FROM Orders WHERE seller_id = %s"
        params = (user_id,)
        results = fetch_from_db(query, params)
    elif role == 'buyer':
        query = "SELECT * FROM Orders WHERE buyer_id = %s"
        params = (user_id,)
        results = fetch_from_db(query, params)
    else:
        query = """
            (SELECT * FROM Orders WHERE seller_id = %s)
            UNION
            (SELECT * FROM Orders WHERE buyer_id = %s)
        """
        params = (user_id, user_id)
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
            "created_at": row[8].strftime('%Y-%m-%d %H:%M:%S') if row[8] else None
        })
    return jsonify({'orders': result_list}), 200

@app.route('/post_order', methods=['POST'])
def post_order():
    data = request.json
    required_fields = ["quantity", "total_price", "status", "seller_id", "buyer_id", "product_id"]
    
    # Check if all required fields are provided in the request data
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
        return jsonify({"message": "New order created"}), 201
    else:
        return jsonify({"error": result}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8890, debug=True)
