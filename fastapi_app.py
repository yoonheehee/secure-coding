from fastapi import FastAPI, HTTPException
from typing import List, Optional
import sqlite3

app = FastAPI()

def create_connection():
    conn = sqlite3.connect('shopping_mall.db')
    return conn

def create_tables(conn):
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT,
            full_name TEXT,
            address TEXT,
            payment_info TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            name TEXT,
            category TEXT,
            price REAL,
            thumbnail_url TEXT
        )
    ''')
    # 구매내역 정보 ( 구매자 아이디, 구매 상품 아이디, 구매 시간, 결제완료 여부, 구매자 주소) 추가
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS purchases_history (
                id INTEGER PRIMARY KEY,
                buyer_id INTEGER,
                product_id INTEGER,
                purchase_time TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                payment_complete BOOLEAN DEFAULT FALSE,
                buyer_address TEXT,
                FOREIGN KEY (buyer_id) REFERENCES users (id),
                FOREIGN KEY (product_id) REFERENCES products (id)
            );

        ''')
    conn.commit()

def add_user(conn, username, password, role, full_name, address, payment_info):
    cursor = conn.cursor()
    cursor.execute(f'INSERT INTO users (username, password, role, full_name, address, payment_info) VALUES (?, ?, ?, ?, ?, ?)',
                   (username, password, role, full_name, address, payment_info))
    conn.commit()
    user = {"username": username, "password": password, "role": role, "full_name": full_name, "address": address, "payment_info": payment_info}
    return {"message": "User created successfully!", "user": user}

def register_admin(conn, username, password, full_name):
    cursor = conn.cursor()
    cursor.execute('INSERT INTO users (username, password, role, full_name) VALUES (?, ?, ?, ?)',
                   (username, password, 'admin', full_name))
    conn.commit()
    user = {"username": username, "password": password, "role": 'admin', "full_name": full_name}
    return {"message": "Admin registered successfully!", "user": user}

def authenticate_user(conn, username, password):
    cursor = conn.cursor()
    cursor.execute(f'SELECT * FROM users WHERE username = "{username}" AND password = "{password}"')
    user = cursor.fetchone()
    if user:
        user_info = {"username": user[1], "password": user[2], "role": user[3], "full_name": user[4], "address": user[5], "payment_info": user[6]}
        return {"message": f"Welcome back, {username}!", "user": user_info}
    else:
        raise HTTPException(status_code=401, detail="Invalid username or password")

def get_all_products(conn):
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products')
    products = cursor.fetchall()
    return [{"name": product[1], "category": product[2], "price": product[3], "thumbnail_url": product[4]} for product in products]

def add_product(conn, name, category, price, thumbnail_url):
    cursor = conn.cursor()
    cursor.execute('INSERT INTO products (name, category, price, thumbnail_url) VALUES (?, ?, ?, ?)', (name, category, price, thumbnail_url))
    conn.commit()
    return {"message": "Product added successfully!"}

def update_user_info(conn, username, full_name, address, payment_info):
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET full_name = ?, address = ?, payment_info = ? WHERE username = ?', (full_name, address, payment_info, username))
    conn.commit()
    return {"message": "User information updated successfully!"}

def get_user_by_username(conn, username):
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    return cursor.fetchone()

def add_purchase(conn, username, product_name, buyer_address):
    cursor = conn.cursor()
    cursor.execute('SELECT id, price FROM products WHERE name = ?',(product_name,))
    products = cursor.fetchone()
    cursor.execute('SELECT id FROM users WHERE username = ?',(username,))
    users = cursor.fetchone()
    cursor.execute('INSERT INTO purchases_history (buyer_id, product_id, buyer_address) VALUES (?, ?, ?)',
                    (users[0],products[0],buyer_address))
    conn.commit()

def get_purchase_history_by_username(conn, username):
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
    users = cursor.fetchone()
    # 구매 이력과 상품 정보를 함께 가져오기
    query = '''
        SELECT ph.id, ph.purchase_time, ph.payment_complete, ph.buyer_address, p.name, p.category, p.price, p.thumbnail_url
        FROM purchases_history ph
        JOIN products p ON ph.product_id = p.id
        WHERE ph.buyer_id = ?
        '''
    cursor.execute(query, (users[0],))
    purchases_historys = cursor.fetchall()
    return [{"product_name": purchases_history[4], "product_price": purchases_history[6], "product_thumbnail_url": purchases_history[7], "purchase_time": purchases_history[1], "payment_complete": purchases_history[2], "buyer_address": purchases_history[3]} for purchases_history
            in purchases_historys]


def get_purchase_history_by_admin(conn):
    cursor = conn.cursor()
    # 모든 구매 이력과 관련된 정보 및 구매자의 이름을 함께 가져오기
    query = '''
    SELECT ph.id, ph.purchase_time, ph.payment_complete, ph.buyer_address,
           p.name, p.category, p.price, p.thumbnail_url,
           u.username
    FROM purchases_history ph
    JOIN products p ON ph.product_id = p.id
    JOIN users u ON ph.buyer_id = u.id
    '''
    cursor.execute(query)
    purchases_historys = cursor.fetchall()

    # 결과를 딕셔너리로 변환하여 반환
    return [{
        "product_name": purchases_history[4],
        "product_price": purchases_history[6],
        "product_thumbnail_url": purchases_history[7],
        "purchase_time": purchases_history[1],
        "payment_complete": purchases_history[2],
        "buyer_address": purchases_history[3],
        "buyer_username": purchases_history[8]
    } for purchases_history in purchases_historys]


@app.on_event("startup")
async def startup_event():
    conn = create_connection()
    create_tables(conn)
    if not get_user_by_username(conn, "admin"):
        register_admin(conn, "admin", "admin", "Admin User")
    conn.close()

@app.get("/register")
async def register_user(username: str, password: str, role: str, full_name: str, address: Optional[str] = None, payment_info: Optional[str] = None):
    conn = create_connection()
    result = add_user(conn, username, password, role, full_name, address, payment_info)
    conn.close()
    return result

@app.get("/login")
async def login(username: str, password: str):
    conn = create_connection()
    result = authenticate_user(conn, username, password)
    conn.close()
    return result

@app.get("/products", response_model=List[dict])
async def get_products():
    conn = create_connection()
    products = get_all_products(conn)
    conn.close()
    return products

@app.get("/add_product")
async def add_new_product(name: str, category: str, price: float, thumbnail_url: str):
    conn = create_connection()
    result = add_product(conn, name, category, price, thumbnail_url)
    conn.close()
    return result

@app.get("/update_user_info")
async def update_user_info_endpoint(username: str, full_name: str, address: str, payment_info: str):
    conn = create_connection()
    result = update_user_info(conn, username, full_name, address, payment_info)
    conn.close()
    return result

@app.get("/add_purchase")
async def add_purchase_endpoint(username: str, product_name:str, buyer_address: str):
    # pass
    conn = create_connection()
    result = add_purchase(conn, username, product_name, buyer_address)
    conn.close()
    return result

@app.get("/get_my_purchase")
async def get_my_purchase_endpoint(username: str):
    # pass
    conn = create_connection()
    result = get_purchase_history_by_username(conn, username)
    conn.close()
    return result


@app.get("/get_all_purchase")
async def get_all_purchase_endpoint(username: str):
    # pass
    conn = create_connection()
    result = get_purchase_history_by_admin(conn)
    conn.close()
    return result