"""
Expense Tracker MCP Server - Simple Version
Connected to Supabase (PostgreSQL)
Features: Add, List, Edit, Delete expenses with User ID isolation
"""

from fastmcp import FastMCP
import os
from dotenv import load_dotenv
import asyncpg

load_dotenv()

mcp = FastMCP("ExpenseTracker")

# Database configuration
DB_URL = "https://mcp.supabase.com/mcp?project_ref=otufqjomotnlnansjtkm"
if not DB_URL:
    raise ValueError("DATABASE_URL not set in .env")

# Global connection pool
db_pool = None

async def init_db():
    """Initialize database connection pool"""
    global db_pool
    if db_pool is None:
        db_pool = await asyncpg.create_pool(DB_URL)
        print("✓ Connected to Supabase")

async def get_conn():
    """Get connection from pool"""
    await init_db()
    return await db_pool.acquire()

# ============================================================================
# TOOLS
# ============================================================================

@mcp.tool()
async def add_expense(user_id: str, date: str, amount: float, category: str, note: str = ""):
async def add_expense(phone_number: str, date: str, amount: float, category: str, note: str = ""):
    """Add a new expense. User ID isolates data."""
    try:
        conn = await get_conn()
        try:
            expense_id = await conn.fetchval(
                """INSERT INTO expenses(user_id, date, amount, category, note)
                """INSERT INTO expenses(phone_number, date, amount, category, note)
                   VALUES($1, $2, $3, $4, $5) RETURNING id""",
                user_id, date, amount, category, note
                phone_number, date, amount, category, note
            )
            return {"status": "success", "id": expense_id, "message": "Expense added"}
        finally:
@@ -55,23 +55,23 @@
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def list_expenses(user_id: str, start_date: str = None, end_date: str = None):
async def list_expenses(phone_number: str, start_date: str = None, end_date: str = None):
    """List all expenses for a user. Filtered by date if provided."""
    try:
        conn = await get_conn()
        try:
            if start_date and end_date:
                rows = await conn.fetch(
                    """SELECT id, date, amount, category, note FROM expenses
                       WHERE user_id = $1 AND date BETWEEN $2 AND $3
                       WHERE phone_number = $1 AND date BETWEEN $2 AND $3
                       ORDER BY date DESC""",
                    user_id, start_date, end_date
                    phone_number, start_date, end_date
                )
            else:
                rows = await conn.fetch(
                    """SELECT id, date, amount, category, note FROM expenses
                       WHERE user_id = $1 ORDER BY date DESC""",
                    user_id
                       WHERE phone_number = $1 ORDER BY date DESC""",
                    phone_number
                )
            return [dict(row) for row in rows]
        finally:
@@ -80,18 +80,18 @@
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def edit_expense(user_id: str, expense_id: int, amount: float = None, 
async def edit_expense(phone_number: str, expense_id: int, amount: float = None, 
                      category: str = None, note: str = None):
    """Edit an expense (only if owned by user)."""
    try:
        conn = await get_conn()
        try:
            # Verify ownership
            owner = await conn.fetchval(
                "SELECT user_id FROM expenses WHERE id = $1",
                "SELECT phone_number FROM expenses WHERE id = $1",
                expense_id
            )
            if owner != user_id:
            if owner != phone_number:
                return {"status": "error", "message": "Not authorized"}

            # Build update query
@@ -125,17 +125,17 @@
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def delete_expense(user_id: str, expense_id: int):
async def delete_expense(phone_number: str, expense_id: int):
    """Delete an expense (only if owned by user)."""
    try:
        conn = await get_conn()
        try:
            # Verify ownership
            owner = await conn.fetchval(
                "SELECT user_id FROM expenses WHERE id = $1",
                "SELECT phone_number FROM expenses WHERE id = $1",
                expense_id
            )
            if owner != user_id:
            if owner != phone_number:
                return {"status": "error", "message": "Not authorized"}

            await conn.execute("DELETE FROM expenses WHERE id = $1", expense_id)
@@ -146,7 +146,7 @@
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def get_summary(user_id: str, start_date: str = None, end_date: str = None):
async def get_summary(phone_number: str, start_date: str = None, end_date: str = None):
    """Get expense summary by category."""
    try:
        conn = await get_conn()
@@ -155,26 +155,26 @@
                rows = await conn.fetch(
                    """SELECT category, SUM(amount) as total, COUNT(*) as count
                       FROM expenses
                       WHERE user_id = $1 AND date BETWEEN $2 AND $3
                       WHERE phone_number = $1 AND date BETWEEN $2 AND $3
                       GROUP BY category ORDER BY total DESC""",
                    user_id, start_date, end_date
                    phone_number, start_date, end_date
                )
            else:
                rows = await conn.fetch(
                    """SELECT category, SUM(amount) as total, COUNT(*) as count
                       FROM expenses WHERE user_id = $1
                       FROM expenses WHERE phone_number = $1
                       GROUP BY category ORDER BY total DESC""",
                    user_id
                    phone_number
                )
            return [dict(row) for row in rows]
        finally:
            await db_pool.release(conn)
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ============================================================================
# START SERVER
# ============================================================================

if __name__ == "__main__":
    print("Starting Expense Tracker MCP Server")