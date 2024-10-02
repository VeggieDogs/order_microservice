from flask import Flask, request, jsonify
import pymysql
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins="http://localhost:3000", methods=["GET", "POST"])

db_config = {
    'host': 'veggie-dogs-db.czrcm8qnf1xc.us-east-1.rds.amazonaws.com',
    'user': 'admin',
    'password': 'dbuserdbuser',
    'database': 'orders',
    'port': 3306
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

    

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8888, debug=True)
