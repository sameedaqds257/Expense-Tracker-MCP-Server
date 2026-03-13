from fastmcp import FastMCP
import os
import aiosqlite
import tempfile

# Use temporary directory which should be writable
TEMP_DIR = tempfile.gettempdir()
DB_PATH = os.path.join(TEMP_DIR, "expenses.db")

CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

print(f"Database path: {DB_PATH}")

mcp = FastMCP("ExpenseTracker")

def init_db():  # Keep as sync for initialization
    try:
        # Use synchronous sqlite3 just for initialization
        import sqlite3
        with sqlite3.connect(DB_PATH) as c:
            c.execute("PRAGMA journal_mode=WAL")
            
            # Create users table
            c.execute("""
                CREATE TABLE IF NOT EXISTS users(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone_number TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create expenses table with user_id reference
            c.execute("""
                CREATE TABLE IF NOT EXISTS expenses(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT DEFAULT '',
                    note TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """)
            
            # Create index for faster queries
            c.execute("CREATE INDEX IF NOT EXISTS idx_expenses_user_id ON expenses(user_id)")
            
            print("Database initialized successfully with user support")
    except Exception as e:
        print(f"Database initialization error: {e}")
        raise

# Initialize database synchronously at module load
init_db()

@mcp.tool()
async def add_expense(phone_number: str, date: str, amount: float, category: str, subcategory: str = "", note: str = ""):
    '''Add a new expense entry for a specific user (phone number).'''
    try:
        async with aiosqlite.connect(DB_PATH) as c:
            # Get or create user
            await c.execute(
                "INSERT OR IGNORE INTO users(phone_number) VALUES (?)",
                (phone_number,)
            )
            
            # Get user_id
            cur = await c.execute("SELECT id FROM users WHERE phone_number = ?", (phone_number,))
            user = await cur.fetchone()
            user_id = user[0]
            
            # Insert expense
            cur = await c.execute(
                "INSERT INTO expenses(user_id, date, amount, category, subcategory, note) VALUES (?,?,?,?,?,?)",
                (user_id, date, amount, category, subcategory, note)
            )
            expense_id = cur.lastrowid
            await c.commit()
            
            return {"status": "success", "id": expense_id, "user_id": user_id, "message": "Expense added successfully"}
    except Exception as e:
        if "readonly" in str(e).lower():
            return {"status": "error", "message": "Database is in read-only mode."}
        return {"status": "error", "message": f"Database error: {str(e)}"}
    
@mcp.tool()
async def list_expenses(phone_number: str, start_date: str, end_date: str):
    '''List expense entries for a specific user within a date range.'''
    try:
        async with aiosqlite.connect(DB_PATH) as c:
            # Get user_id from phone_number
            cur = await c.execute("SELECT id FROM users WHERE phone_number = ?", (phone_number,))
            user = await cur.fetchone()
            
            if not user:
                return {"status": "error", "message": f"User with phone {phone_number} not found"}
            
            user_id = user[0]
            
            # Get expenses for this user only
            cur = await c.execute(
                """
                SELECT id, date, amount, category, subcategory, note
                FROM expenses
                WHERE user_id = ? AND date BETWEEN ? AND ?
                ORDER BY date DESC, id DESC
                """,
                (user_id, start_date, end_date)
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in await cur.fetchall()]
    except Exception as e:
        return {"status": "error", "message": f"Error listing expenses: {str(e)}"}

@mcp.tool()
async def summarize(phone_number: str, start_date: str, end_date: str, category: str = None):
    '''Summarize expenses by category for a specific user.'''
    try:
        async with aiosqlite.connect(DB_PATH) as c:
            # Get user_id
            cur = await c.execute("SELECT id FROM users WHERE phone_number = ?", (phone_number,))
            user = await cur.fetchone()
            
            if not user:
                return {"status": "error", "message": f"User with phone {phone_number} not found"}
            
            user_id = user[0]
            
            query = """
                SELECT category, SUM(amount) AS total_amount, COUNT(*) as count
                FROM expenses
                WHERE user_id = ? AND date BETWEEN ? AND ?
            """
            params = [user_id, start_date, end_date]

            if category:
                query += " AND category = ?"
                params.append(category)

            query += " GROUP BY category ORDER BY total_amount DESC"

            cur = await c.execute(query, params)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in await cur.fetchall()]
    except Exception as e:
        return {"status": "error", "message": f"Error summarizing expenses: {str(e)}"}

@mcp.resource("expense:///categories", mime_type="application/json")
def categories():
    try:
        # Provide default categories if file doesn't exist
        default_categories = {
            "categories": [
                "Food & Dining",
                "Transportation",
                "Shopping",
                "Entertainment",
                "Bills & Utilities",
                "Healthcare",
                "Travel",
                "Education",
                "Business",
                "Other"
            ]
        }
        
        try:
            with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            import json
            return json.dumps(default_categories, indent=2)
    except Exception as e:
        return f'{{"error": "Could not load categories: {str(e)}"}}'

# Start the server
if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8081)