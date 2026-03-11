import hashlib
import json
import mimetypes
import secrets
import sqlite3
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "crm.db"
STATIC_DIR = BASE_DIR / "static"
SESSIONS = {}
ALLOWED_PRODUCT_TYPES = {"eshik", "deraza", "padagolnik", "portichka", "pena"}
ALLOWED_COLORS = {"oq", "karishniy", "karishniviy"}
DOOR_SIZES = {
    "120x240",
    "120x230",
    "120x220",
    "110x230",
    "110x240",
    "110x220",
    "90x240",
    "90x230",
    "90x220",
    "90x210",
    "90x200",
    "90x190",
    "80x200",
    "80x190",
    "80x180",
    "70x200",
    "70x190",
    "70x140",
    "70x170",
}
WINDOW_SIZES = {
    "90x140",
    "90x150",
    "90x160",
    "90x170",
    "100x120",
    "100x140",
    "100x150",
    "100x160",
    "100x170",
    "110x140",
    "110x150",
    "110x160",
    "110x170",
    "120x140",
    "120x150",
    "120x160",
    "120x170",
    "130x140",
    "130x150",
    "130x160",
    "130x170",
    "140x140",
    "140x150",
    "140x160",
    "140x170",
    "150x160",
    "150x170",
    "160x160",
    "180x160",
    "200x150",
    "200x160",
    "200x170",
    "200x180",
}
PORTICHKA_SIZES = {
    "40x40",
    "40x50",
    "40x60",
    "40x70",
    "40x80",
    "40x90",
    "40x100",
    "50x50",
    "50x60",
    "50x70",
    "50x80",
    "50x90",
    "50x100",
    "50x120",
    "50x130",
    "50x140",
    "50x150",
    "60x60",
    "60x70",
    "60x80",
    "60x90",
    "60x100",
    "60x120",
}
PENA_TYPES = {"1050 gr", "600 gr"}


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = db_conn()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            unit TEXT NOT NULL,
            stock_qty REAL NOT NULL DEFAULT 0,
            avg_cost REAL NOT NULL DEFAULT 0,
            sale_price REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            sale_id INTEGER,
            movement_type TEXT NOT NULL,
            qty REAL NOT NULL,
            unit_price REAL NOT NULL,
            total_amount REAL NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(product_id) REFERENCES products(id),
            FOREIGN KEY(sale_id) REFERENCES sales(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            qty REAL NOT NULL,
            sale_price REAL NOT NULL,
            revenue_total REAL NOT NULL,
            cost_total REAL NOT NULL,
            profit_total REAL NOT NULL,
            customer_name TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            amount REAL NOT NULL,
            comment TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    # Migration for existing databases.
    try:
        cur.execute("ALTER TABLE stock_movements ADD COLUMN sale_id INTEGER")
    except sqlite3.OperationalError:
        pass

    admin_password = "admin123"
    cur.execute(
        """
        INSERT OR IGNORE INTO users(username, password_hash, role)
        VALUES (?, ?, ?)
        """,
        ("admin", hash_password(admin_password), "admin"),
    )

    conn.commit()
    conn.close()


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def format_product_name(product_type: str, color: str, size: str) -> str:
    labels = {
        "eshik": "Eshik",
        "deraza": "Deraza",
        "padagolnik": "Padagolnik",
        "portichka": "Portichka",
        "pena": "Pena",
    }
    base = labels.get(product_type, product_type.capitalize())
    if product_type in {"eshik", "deraza", "portichka"}:
        return f"{base} {color} {size}"
    if product_type == "padagolnik":
        return f"{base} {color}"
    if product_type == "pena":
        return f"{base} {size}"
    return base


def auth_user(handler) -> int | None:
    auth_header = handler.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:].strip()
    return SESSIONS.get(token)


class CRMHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, file_path: Path, status: HTTPStatus = HTTPStatus.OK) -> None:
        if not file_path.exists() or not file_path.is_file():
            self._send_json({"error": "Fayl topilmadi"}, HTTPStatus.NOT_FOUND)
            return

        content = file_path.read_bytes()
        mime, _ = mimetypes.guess_type(str(file_path))
        if not mime:
            mime = "application/octet-stream"
        self.send_response(status.value)
        self.send_header("Content-Type", f"{mime}; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _read_json(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length) if content_length > 0 else b"{}"
        return json.loads(raw.decode("utf-8") or "{}")

    def _require_auth(self) -> int | None:
        user_id = auth_user(self)
        if not user_id:
            self._send_json({"error": "Avtorizatsiya talab qilinadi"}, HTTPStatus.UNAUTHORIZED)
            return None
        return user_id

    def _parse_entity_id(self, path: str, prefix: str) -> int | None:
        raw = path.replace(prefix, "", 1).strip("/")
        if not raw or "/" in raw:
            return None
        try:
            return int(raw)
        except ValueError:
            return None

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT.value)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        page_routes = {
            "/": "index.html",
            "/index": "index.html",
            "/index.html": "index.html",
            "/sotuv": "sotuv.html",
            "/sotuv.html": "sotuv.html",
            "/chiqim": "chiqim.html",
            "/chiqim.html": "chiqim.html",
            "/mahsulot": "mahsulot.html",
            "/mahsulot.html": "mahsulot.html",
        }

        if path in page_routes:
            self._send_file(BASE_DIR / page_routes[path])
            return
        if path.startswith("/assets/"):
            rel = path.replace("/assets/", "", 1)
            self._send_file(STATIC_DIR / rel)
            return
        if path == "/api/products":
            if not self._require_auth():
                return
            self.handle_products_list()
            return
        if path == "/api/sales":
            if not self._require_auth():
                return
            self.handle_sales_list()
            return
        if path == "/api/expenses":
            if not self._require_auth():
                return
            self.handle_expenses_list()
            return
        if path == "/api/dashboard":
            if not self._require_auth():
                return
            self.handle_dashboard()
            return

        self._send_json({"error": "Sahifa topilmadi"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/login":
            self.handle_login()
            return
        if path == "/api/products":
            if not self._require_auth():
                return
            self.handle_create_product()
            return
        if path == "/api/products/quick-add":
            if not self._require_auth():
                return
            self.handle_quick_add_product()
            return
        if path == "/api/products/incoming":
            if not self._require_auth():
                return
            self.handle_product_incoming()
            return
        if path == "/api/sales":
            if not self._require_auth():
                return
            self.handle_create_sale()
            return
        if path == "/api/expenses":
            if not self._require_auth():
                return
            self.handle_create_expense()
            return
        if path == "/api/logout":
            if not self._require_auth():
                return
            self.handle_logout()
            return

        self._send_json({"error": "Endpoint topilmadi"}, HTTPStatus.NOT_FOUND)

    def do_PUT(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if not self._require_auth():
            return

        if path.startswith("/api/sales/"):
            sale_id = self._parse_entity_id(path, "/api/sales/")
            if sale_id is None:
                self._send_json({"error": "Sale ID xato"}, HTTPStatus.BAD_REQUEST)
                return
            self.handle_update_sale(sale_id)
            return

        if path.startswith("/api/expenses/"):
            expense_id = self._parse_entity_id(path, "/api/expenses/")
            if expense_id is None:
                self._send_json({"error": "Expense ID xato"}, HTTPStatus.BAD_REQUEST)
                return
            self.handle_update_expense(expense_id)
            return

        if path.startswith("/api/products/"):
            product_id = self._parse_entity_id(path, "/api/products/")
            if product_id is None:
                self._send_json({"error": "Product ID xato"}, HTTPStatus.BAD_REQUEST)
                return
            self.handle_update_product(product_id)
            return

        self._send_json({"error": "Endpoint topilmadi"}, HTTPStatus.NOT_FOUND)

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if not self._require_auth():
            return

        if path.startswith("/api/sales/"):
            sale_id = self._parse_entity_id(path, "/api/sales/")
            if sale_id is None:
                self._send_json({"error": "Sale ID xato"}, HTTPStatus.BAD_REQUEST)
                return
            self.handle_delete_sale(sale_id)
            return

        if path.startswith("/api/expenses/"):
            expense_id = self._parse_entity_id(path, "/api/expenses/")
            if expense_id is None:
                self._send_json({"error": "Expense ID xato"}, HTTPStatus.BAD_REQUEST)
                return
            self.handle_delete_expense(expense_id)
            return

        if path.startswith("/api/products/"):
            product_id = self._parse_entity_id(path, "/api/products/")
            if product_id is None:
                self._send_json({"error": "Product ID xato"}, HTTPStatus.BAD_REQUEST)
                return
            self.handle_delete_product(product_id)
            return

        self._send_json({"error": "Endpoint topilmadi"}, HTTPStatus.NOT_FOUND)

    def handle_login(self) -> None:
        try:
            body = self._read_json()
            username = (body.get("username") or "").strip()
            password = (body.get("password") or "").strip()
            if not username or not password:
                self._send_json({"error": "Login va parol talab qilinadi"}, HTTPStatus.BAD_REQUEST)
                return

            conn = db_conn()
            cur = conn.cursor()
            cur.execute(
                "SELECT id, username, role, password_hash FROM users WHERE username = ?",
                (username,),
            )
            user = cur.fetchone()
            conn.close()

            if not user or user["password_hash"] != hash_password(password):
                self._send_json({"error": "Noto'g'ri login yoki parol"}, HTTPStatus.UNAUTHORIZED)
                return

            token = secrets.token_hex(24)
            SESSIONS[token] = user["id"]
            self._send_json(
                {
                    "token": token,
                    "user": {
                        "id": user["id"],
                        "username": user["username"],
                        "role": user["role"],
                    },
                }
            )
        except json.JSONDecodeError:
            self._send_json({"error": "JSON formati xato"}, HTTPStatus.BAD_REQUEST)

    def handle_logout(self) -> None:
        auth_header = self.headers.get("Authorization", "")
        token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else ""
        if token in SESSIONS:
            del SESSIONS[token]
        self._send_json({"ok": True})

    def handle_create_product(self) -> None:
        try:
            body = self._read_json()
            name = (body.get("name") or "").strip()
            unit = (body.get("unit") or "").strip() or "dona"
            sale_price = float(body.get("sale_price") or 0)
            if not name:
                self._send_json({"error": "Mahsulot nomi kerak"}, HTTPStatus.BAD_REQUEST)
                return
            if sale_price < 0:
                self._send_json({"error": "Sotuv narxi manfiy bo'lmaydi"}, HTTPStatus.BAD_REQUEST)
                return

            conn = db_conn()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO products(name, unit, sale_price, created_at)
                VALUES(?, ?, ?, ?)
                """,
                (name, unit, sale_price, now_iso()),
            )
            conn.commit()
            product_id = cur.lastrowid
            conn.close()
            self._send_json({"ok": True, "product_id": product_id}, HTTPStatus.CREATED)
        except sqlite3.IntegrityError:
            self._send_json({"error": "Bunday mahsulot allaqachon mavjud"}, HTTPStatus.CONFLICT)
        except ValueError:
            self._send_json({"error": "Raqamli maydonlar xato"}, HTTPStatus.BAD_REQUEST)
        except json.JSONDecodeError:
            self._send_json({"error": "JSON formati xato"}, HTTPStatus.BAD_REQUEST)

    def handle_quick_add_product(self) -> None:
        try:
            body = self._read_json()
            product_type = (body.get("product_type") or "").strip().lower()
            color = (body.get("color") or "").strip().lower()
            size = (body.get("size") or "").strip().lower()
            unit = (body.get("unit") or "").strip() or "dona"
            incoming_qty = float(body.get("incoming_qty"))
            incoming_price = float(body.get("incoming_price"))

            if product_type not in ALLOWED_PRODUCT_TYPES:
                self._send_json({"error": "Mahsulot turi noto'g'ri"}, HTTPStatus.BAD_REQUEST)
                return
            if incoming_qty <= 0 or incoming_price < 0:
                self._send_json({"error": "Soni > 0 va kelish narxi >= 0 bo'lishi kerak"}, HTTPStatus.BAD_REQUEST)
                return

            if product_type == "eshik":
                if color not in ALLOWED_COLORS or size not in DOOR_SIZES:
                    self._send_json({"error": "Eshik uchun rang yoki o'lcham noto'g'ri"}, HTTPStatus.BAD_REQUEST)
                    return
            elif product_type == "deraza":
                if color not in ALLOWED_COLORS or size not in WINDOW_SIZES:
                    self._send_json({"error": "Deraza uchun rang yoki o'lcham noto'g'ri"}, HTTPStatus.BAD_REQUEST)
                    return
            elif product_type == "padagolnik":
                if color not in ALLOWED_COLORS:
                    self._send_json({"error": "Padagolnik uchun rang noto'g'ri"}, HTTPStatus.BAD_REQUEST)
                    return
                size = ""
            elif product_type == "portichka":
                if color not in ALLOWED_COLORS or size not in PORTICHKA_SIZES:
                    self._send_json({"error": "Portichka uchun rang yoki o'lcham noto'g'ri"}, HTTPStatus.BAD_REQUEST)
                    return
            elif product_type == "pena":
                size = size.replace("гр", "gr")
                if size not in PENA_TYPES:
                    self._send_json({"error": "Pena uchun o'lcham noto'g'ri"}, HTTPStatus.BAD_REQUEST)
                    return
                color = ""
            else:
                color = ""
                size = ""

            name = format_product_name(product_type, color, size)

            conn = db_conn()
            cur = conn.cursor()
            cur.execute("SELECT id, stock_qty, avg_cost FROM products WHERE name = ?", (name,))
            existing = cur.fetchone()
            created = False

            if existing:
                product_id = int(existing["id"])
                old_qty = float(existing["stock_qty"])
                old_avg_cost = float(existing["avg_cost"])
            else:
                cur.execute(
                    """
                    INSERT INTO products(name, unit, sale_price, created_at)
                    VALUES(?, ?, 0, ?)
                    """,
                    (name, unit, now_iso()),
                )
                product_id = int(cur.lastrowid)
                old_qty = 0.0
                old_avg_cost = 0.0
                created = True

            new_qty = old_qty + incoming_qty
            new_avg_cost = (
                ((old_qty * old_avg_cost) + (incoming_qty * incoming_price)) / new_qty if new_qty > 0 else 0
            )
            total_amount = incoming_qty * incoming_price

            cur.execute(
                """
                UPDATE products
                SET stock_qty = ?, avg_cost = ?
                WHERE id = ?
                """,
                (new_qty, new_avg_cost, product_id),
            )
            cur.execute(
                """
                INSERT INTO stock_movements(product_id, movement_type, qty, unit_price, total_amount, notes, created_at)
                VALUES (?, 'IN', ?, ?, ?, ?, ?)
                """,
                (product_id, incoming_qty, incoming_price, total_amount, "quick-add", now_iso()),
            )
            conn.commit()
            conn.close()

            self._send_json(
                {
                    "ok": True,
                    "product_id": product_id,
                    "created": created,
                    "name": name,
                },
                HTTPStatus.CREATED if created else HTTPStatus.OK,
            )
        except (TypeError, ValueError):
            self._send_json({"error": "Maydonlar noto'g'ri kiritilgan"}, HTTPStatus.BAD_REQUEST)
        except json.JSONDecodeError:
            self._send_json({"error": "JSON formati xato"}, HTTPStatus.BAD_REQUEST)

    def handle_products_list(self) -> None:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, name, unit, stock_qty, avg_cost, sale_price, created_at
            FROM products
            ORDER BY name
            """
        )
        products = [dict(row) for row in cur.fetchall()]
        conn.close()
        self._send_json({"products": products})

    def handle_update_product(self, product_id: int) -> None:
        try:
            body = self._read_json()
            name = (body.get("name") or "").strip()
            unit = (body.get("unit") or "").strip() or "dona"
            stock_qty = float(body.get("stock_qty"))
            avg_cost = float(body.get("avg_cost"))

            if not name:
                self._send_json({"error": "Mahsulot nomi kerak"}, HTTPStatus.BAD_REQUEST)
                return
            if stock_qty < 0 or avg_cost < 0:
                self._send_json({"error": "Qoldiq va tannarx manfiy bo'lmaydi"}, HTTPStatus.BAD_REQUEST)
                return

            conn = db_conn()
            cur = conn.cursor()
            cur.execute("SELECT id FROM products WHERE id = ?", (product_id,))
            existing = cur.fetchone()
            if not existing:
                conn.close()
                self._send_json({"error": "Mahsulot topilmadi"}, HTTPStatus.NOT_FOUND)
                return

            cur.execute(
                """
                UPDATE products
                SET name = ?, unit = ?, stock_qty = ?, avg_cost = ?
                WHERE id = ?
                """,
                (name, unit, stock_qty, avg_cost, product_id),
            )
            conn.commit()
            conn.close()
            self._send_json({"ok": True})
        except sqlite3.IntegrityError:
            self._send_json({"error": "Bunday nomdagi mahsulot allaqachon bor"}, HTTPStatus.CONFLICT)
        except (TypeError, ValueError):
            self._send_json({"error": "Maydonlar noto'g'ri kiritilgan"}, HTTPStatus.BAD_REQUEST)
        except json.JSONDecodeError:
            self._send_json({"error": "JSON formati xato"}, HTTPStatus.BAD_REQUEST)

    def handle_delete_product(self, product_id: int) -> None:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("SELECT id FROM products WHERE id = ?", (product_id,))
        product = cur.fetchone()
        if not product:
            conn.close()
            self._send_json({"error": "Mahsulot topilmadi"}, HTTPStatus.NOT_FOUND)
            return

        cur.execute("DELETE FROM stock_movements WHERE product_id = ?", (product_id,))
        cur.execute("DELETE FROM sales WHERE product_id = ?", (product_id,))
        cur.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()
        conn.close()
        self._send_json({"ok": True})

    def handle_product_incoming(self) -> None:
        try:
            body = self._read_json()
            product_id = int(body.get("product_id"))
            qty = float(body.get("qty"))
            unit_price = float(body.get("unit_price"))
            notes = (body.get("notes") or "").strip()

            if qty <= 0 or unit_price < 0:
                self._send_json({"error": "Miqdor > 0 va narx >= 0 bo'lishi kerak"}, HTTPStatus.BAD_REQUEST)
                return

            conn = db_conn()
            cur = conn.cursor()
            cur.execute("SELECT stock_qty, avg_cost FROM products WHERE id = ?", (product_id,))
            product = cur.fetchone()
            if not product:
                conn.close()
                self._send_json({"error": "Mahsulot topilmadi"}, HTTPStatus.NOT_FOUND)
                return

            old_qty = float(product["stock_qty"])
            old_avg_cost = float(product["avg_cost"])
            new_qty = old_qty + qty
            new_avg_cost = (
                ((old_qty * old_avg_cost) + (qty * unit_price)) / new_qty if new_qty > 0 else 0
            )
            total_amount = qty * unit_price

            cur.execute(
                """
                UPDATE products
                SET stock_qty = ?, avg_cost = ?
                WHERE id = ?
                """,
                (new_qty, new_avg_cost, product_id),
            )
            cur.execute(
                """
                INSERT INTO stock_movements(product_id, movement_type, qty, unit_price, total_amount, notes, created_at)
                VALUES (?, 'IN', ?, ?, ?, ?, ?)
                """,
                (product_id, qty, unit_price, total_amount, notes, now_iso()),
            )
            conn.commit()
            conn.close()
            self._send_json({"ok": True})
        except (TypeError, ValueError):
            self._send_json({"error": "Maydonlar noto'g'ri kiritilgan"}, HTTPStatus.BAD_REQUEST)
        except json.JSONDecodeError:
            self._send_json({"error": "JSON formati xato"}, HTTPStatus.BAD_REQUEST)

    def handle_sales_list(self) -> None:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT s.id, s.product_id, p.name AS product_name, s.qty, s.sale_price, s.revenue_total, s.cost_total,
                   s.profit_total, s.customer_name, s.created_at
            FROM sales s
            JOIN products p ON p.id = s.product_id
            ORDER BY s.id DESC
            """
        )
        sales = [dict(row) for row in cur.fetchall()]
        conn.close()
        self._send_json({"sales": sales})

    def handle_create_sale(self) -> None:
        try:
            body = self._read_json()
            product_id = int(body.get("product_id"))
            qty = float(body.get("qty"))
            sale_price = float(body.get("sale_price"))
            customer_name = (body.get("customer_name") or "").strip()

            if qty <= 0 or sale_price < 0:
                self._send_json({"error": "Miqdor > 0 va narx >= 0 bo'lishi kerak"}, HTTPStatus.BAD_REQUEST)
                return

            conn = db_conn()
            cur = conn.cursor()
            cur.execute("SELECT stock_qty, avg_cost FROM products WHERE id = ?", (product_id,))
            product = cur.fetchone()
            if not product:
                conn.close()
                self._send_json({"error": "Mahsulot topilmadi"}, HTTPStatus.NOT_FOUND)
                return

            stock_qty = float(product["stock_qty"])
            avg_cost = float(product["avg_cost"])
            if stock_qty < qty:
                conn.close()
                self._send_json({"error": "Omborda yetarli qoldiq yo'q"}, HTTPStatus.BAD_REQUEST)
                return

            new_qty = stock_qty - qty
            revenue_total = qty * sale_price
            cost_total = qty * avg_cost
            profit_total = revenue_total - cost_total

            sale_created_at = now_iso()
            cur.execute(
                """
                INSERT INTO sales(product_id, qty, sale_price, revenue_total, cost_total, profit_total, customer_name, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product_id,
                    qty,
                    sale_price,
                    revenue_total,
                    cost_total,
                    profit_total,
                    customer_name,
                    sale_created_at,
                ),
            )
            sale_id = int(cur.lastrowid)

            cur.execute(
                "UPDATE products SET stock_qty = ? WHERE id = ?",
                (new_qty, product_id),
            )
            cur.execute(
                """
                INSERT INTO stock_movements(product_id, sale_id, movement_type, qty, unit_price, total_amount, notes, created_at)
                VALUES (?, ?, 'OUT', ?, ?, ?, ?, ?)
                """,
                (
                    product_id,
                    sale_id,
                    qty,
                    avg_cost,
                    cost_total,
                    customer_name,
                    sale_created_at,
                ),
            )

            conn.commit()
            conn.close()
            self._send_json({"ok": True})
        except (TypeError, ValueError):
            self._send_json({"error": "Maydonlar noto'g'ri kiritilgan"}, HTTPStatus.BAD_REQUEST)
        except json.JSONDecodeError:
            self._send_json({"error": "JSON formati xato"}, HTTPStatus.BAD_REQUEST)

    def handle_update_sale(self, sale_id: int) -> None:
        try:
            body = self._read_json()
            product_id = int(body.get("product_id"))
            qty = float(body.get("qty"))
            sale_price = float(body.get("sale_price"))
            customer_name = (body.get("customer_name") or "").strip()

            if qty <= 0 or sale_price < 0:
                self._send_json({"error": "Miqdor > 0 va narx >= 0 bo'lishi kerak"}, HTTPStatus.BAD_REQUEST)
                return

            conn = db_conn()
            cur = conn.cursor()
            cur.execute("SELECT id, product_id, qty FROM sales WHERE id = ?", (sale_id,))
            existing_sale = cur.fetchone()
            if not existing_sale:
                conn.close()
                self._send_json({"error": "Sotuv topilmadi"}, HTTPStatus.NOT_FOUND)
                return

            old_product_id = int(existing_sale["product_id"])
            old_qty = float(existing_sale["qty"])

            cur.execute("SELECT stock_qty FROM products WHERE id = ?", (old_product_id,))
            old_product = cur.fetchone()
            if not old_product:
                conn.close()
                self._send_json({"error": "Eski mahsulot topilmadi"}, HTTPStatus.NOT_FOUND)
                return

            restored_old_qty = float(old_product["stock_qty"]) + old_qty
            cur.execute(
                "UPDATE products SET stock_qty = ? WHERE id = ?",
                (restored_old_qty, old_product_id),
            )
            cur.execute("DELETE FROM stock_movements WHERE sale_id = ? AND movement_type = 'OUT'", (sale_id,))

            cur.execute("SELECT stock_qty, avg_cost FROM products WHERE id = ?", (product_id,))
            new_product = cur.fetchone()
            if not new_product:
                conn.rollback()
                conn.close()
                self._send_json({"error": "Mahsulot topilmadi"}, HTTPStatus.NOT_FOUND)
                return

            stock_qty = float(new_product["stock_qty"])
            avg_cost = float(new_product["avg_cost"])
            if stock_qty < qty:
                conn.rollback()
                conn.close()
                self._send_json({"error": "Omborda yetarli qoldiq yo'q"}, HTTPStatus.BAD_REQUEST)
                return

            new_qty = stock_qty - qty
            revenue_total = qty * sale_price
            cost_total = qty * avg_cost
            profit_total = revenue_total - cost_total

            cur.execute(
                """
                UPDATE sales
                SET product_id = ?, qty = ?, sale_price = ?, revenue_total = ?, cost_total = ?, profit_total = ?, customer_name = ?
                WHERE id = ?
                """,
                (
                    product_id,
                    qty,
                    sale_price,
                    revenue_total,
                    cost_total,
                    profit_total,
                    customer_name,
                    sale_id,
                ),
            )
            cur.execute(
                "UPDATE products SET stock_qty = ? WHERE id = ?",
                (new_qty, product_id),
            )
            cur.execute(
                """
                INSERT INTO stock_movements(product_id, sale_id, movement_type, qty, unit_price, total_amount, notes, created_at)
                VALUES (?, ?, 'OUT', ?, ?, ?, ?, ?)
                """,
                (product_id, sale_id, qty, avg_cost, cost_total, customer_name, now_iso()),
            )

            conn.commit()
            conn.close()
            self._send_json({"ok": True})
        except (TypeError, ValueError):
            self._send_json({"error": "Maydonlar noto'g'ri kiritilgan"}, HTTPStatus.BAD_REQUEST)
        except json.JSONDecodeError:
            self._send_json({"error": "JSON formati xato"}, HTTPStatus.BAD_REQUEST)

    def handle_delete_sale(self, sale_id: int) -> None:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("SELECT product_id, qty FROM sales WHERE id = ?", (sale_id,))
        sale = cur.fetchone()
        if not sale:
            conn.close()
            self._send_json({"error": "Sotuv topilmadi"}, HTTPStatus.NOT_FOUND)
            return

        product_id = int(sale["product_id"])
        qty = float(sale["qty"])

        cur.execute("SELECT stock_qty FROM products WHERE id = ?", (product_id,))
        product = cur.fetchone()
        if product:
            restored_qty = float(product["stock_qty"]) + qty
            cur.execute("UPDATE products SET stock_qty = ? WHERE id = ?", (restored_qty, product_id))

        cur.execute("DELETE FROM stock_movements WHERE sale_id = ? AND movement_type = 'OUT'", (sale_id,))
        cur.execute("DELETE FROM sales WHERE id = ?", (sale_id,))
        conn.commit()
        conn.close()
        self._send_json({"ok": True})

    def handle_create_expense(self) -> None:
        try:
            body = self._read_json()
            name = (body.get("name") or "").strip()
            amount = float(body.get("amount"))
            comment = (body.get("comment") or "").strip()

            if not name:
                self._send_json({"error": "Chiqim nomi kerak"}, HTTPStatus.BAD_REQUEST)
                return
            if amount <= 0:
                self._send_json({"error": "Summa 0 dan katta bo'lishi kerak"}, HTTPStatus.BAD_REQUEST)
                return

            conn = db_conn()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO expenses(name, amount, comment, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (name, amount, comment, now_iso()),
            )
            conn.commit()
            conn.close()
            self._send_json({"ok": True}, HTTPStatus.CREATED)
        except (TypeError, ValueError):
            self._send_json({"error": "Maydonlar noto'g'ri kiritilgan"}, HTTPStatus.BAD_REQUEST)
        except json.JSONDecodeError:
            self._send_json({"error": "JSON formati xato"}, HTTPStatus.BAD_REQUEST)

    def handle_expenses_list(self) -> None:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, name, amount, comment, created_at
            FROM expenses
            ORDER BY id DESC
            """
        )
        expenses = [dict(row) for row in cur.fetchall()]
        conn.close()
        self._send_json({"expenses": expenses})

    def handle_update_expense(self, expense_id: int) -> None:
        try:
            body = self._read_json()
            name = (body.get("name") or "").strip()
            amount = float(body.get("amount"))
            comment = (body.get("comment") or "").strip()

            if not name:
                self._send_json({"error": "Chiqim nomi kerak"}, HTTPStatus.BAD_REQUEST)
                return
            if amount <= 0:
                self._send_json({"error": "Summa 0 dan katta bo'lishi kerak"}, HTTPStatus.BAD_REQUEST)
                return

            conn = db_conn()
            cur = conn.cursor()
            cur.execute("SELECT id FROM expenses WHERE id = ?", (expense_id,))
            existing = cur.fetchone()
            if not existing:
                conn.close()
                self._send_json({"error": "Chiqim topilmadi"}, HTTPStatus.NOT_FOUND)
                return

            cur.execute(
                """
                UPDATE expenses
                SET name = ?, amount = ?, comment = ?
                WHERE id = ?
                """,
                (name, amount, comment, expense_id),
            )
            conn.commit()
            conn.close()
            self._send_json({"ok": True})
        except (TypeError, ValueError):
            self._send_json({"error": "Maydonlar noto'g'ri kiritilgan"}, HTTPStatus.BAD_REQUEST)
        except json.JSONDecodeError:
            self._send_json({"error": "JSON formati xato"}, HTTPStatus.BAD_REQUEST)

    def handle_delete_expense(self, expense_id: int) -> None:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        if cur.rowcount == 0:
            conn.close()
            self._send_json({"error": "Chiqim topilmadi"}, HTTPStatus.NOT_FOUND)
            return
        conn.commit()
        conn.close()
        self._send_json({"ok": True})

    def handle_dashboard(self) -> None:
        conn = db_conn()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
              COALESCE(SUM(revenue_total), 0) AS total_income,
              COALESCE(SUM(cost_total), 0) AS total_cost
            FROM sales
            """
        )
        sales_summary = dict(cur.fetchone())

        cur.execute(
            """
            SELECT COALESCE(SUM(total_amount), 0) AS total_purchase
            FROM stock_movements
            WHERE movement_type = 'IN'
            """
        )
        purchases = dict(cur.fetchone())

        cur.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS misc_expense
            FROM expenses
            """
        )
        expenses_total = dict(cur.fetchone())

        total_income = float(sales_summary["total_income"])
        total_cost = float(sales_summary["total_cost"])
        misc_expense = float(expenses_total["misc_expense"])
        total_expense = misc_expense
        net_profit = total_income - (total_cost + misc_expense)
        summary = {
            "total_income": total_income,
            "total_expense": total_expense,
            "net_profit": net_profit,
            "goods_cost": total_cost,
            "other_expense": misc_expense,
        }

        cur.execute(
            """
            SELECT id, name, unit, stock_qty, avg_cost, sale_price,
                   ROUND(stock_qty * avg_cost, 2) AS stock_value
            FROM products
            ORDER BY stock_qty ASC, name ASC
            """
        )
        products = [dict(row) for row in cur.fetchall()]

        cur.execute(
            """
            SELECT s.id, p.name AS product_name, s.qty, s.sale_price, s.revenue_total, s.profit_total, s.customer_name, s.created_at
            FROM sales s
            JOIN products p ON p.id = s.product_id
            ORDER BY s.id DESC
            LIMIT 10
            """
        )
        recent_sales = [dict(row) for row in cur.fetchall()]

        cur.execute(
            """
            SELECT m.id, p.name AS product_name, m.qty, m.unit_price, m.total_amount, m.notes, m.created_at
            FROM stock_movements m
            JOIN products p ON p.id = m.product_id
            WHERE m.movement_type = 'IN'
            ORDER BY m.id DESC
            LIMIT 10
            """
        )
        recent_incoming = [dict(row) for row in cur.fetchall()]

        cur.execute(
            """
            SELECT id, name, amount, comment, created_at
            FROM expenses
            ORDER BY id DESC
            LIMIT 15
            """
        )
        recent_expenses = [dict(row) for row in cur.fetchall()]

        conn.close()

        self._send_json(
            {
                "summary": summary,
                "purchases": purchases,
                "products": products,
                "recent_sales": recent_sales,
                "recent_incoming": recent_incoming,
                "recent_expenses": recent_expenses,
            }
        )


def run() -> None:
    init_db()
    server = ThreadingHTTPServer(("0.0.0.0", 8080), CRMHandler)
    print("CRM server ishladi: http://localhost:8080")
    print("Admin login: admin")
    print("Admin parol: admin123")
    server.serve_forever()


if __name__ == "__main__":
    run()
