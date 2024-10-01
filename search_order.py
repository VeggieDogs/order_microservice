from flask import Flask, request, jsonify
import pymysql

app = Flask(__name__)

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
    
    if not order_id:
        return jsonify({"error": "order_id parameter is required"}), 400

    query = f"SELECT * FROM Orders WHERE order_id = {order_id}"

    results = fetch_from_db(query)

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

    return jsonify(result_list), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8888, debug=True)
