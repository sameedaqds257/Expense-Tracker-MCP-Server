"""
Expense Tracker MCP Server - Simple Version
Connected to Supabase (PostgreSQL)
Features: Add, List, Edit, Delete expenses with User ID isolation
UPDATED: Now accepts and ignores extra parameters passed by AI Agent
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
async def add_expense(
    phone_number: str,
    date: str,
    amount: float,
    category: str,
    note: str = "",
    **kwargs  # Accept and ignore any extra parameters passed by AI Agent
):
    """Add a new expense. User ID isolates data."""
    # Log and ignore any extra parameters
    if kwargs:
        print(f"⚠ Ignoring extra parameters: {list(kwargs.keys())}")
    
    try:
        conn = await get_conn()
        try:
            expense_id = await conn.fetchval(
                """INSERT INTO expenses(phone_number, date, amount, category, note)
                   VALUES($1, $2, $3, $4, $5) RETURNING id""",
                phone_number, date, amount, category, note
            )
            return {"status": "success", "id": expense_id, "message": "Expense added"}
        finally:
            await db_pool.release(conn)
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def list_expenses(phone_number: str,
                         start_date: str = None,
                           end_date: str = None,
                           **kwargs):
    """List all expenses for a user. Filtered by date if provided."""
    try:
        conn = await get_conn()
        try:
            if start_date and end_date:
                rows = await conn.fetch(
                    """SELECT id, date, amount, category, note FROM expenses
                       WHERE phone_number = $1 AND date BETWEEN $2 AND $3
                       ORDER BY date DESC""",
                    phone_number, start_date, end_date
                )
            else:
                rows = await conn.fetch(
                    """SELECT id, date, amount, category, note FROM expenses
                       WHERE phone_number = $1 ORDER BY date DESC""",
                    phone_number
                )
            return [dict(row) for row in rows]
        finally:
            await db_pool.release(conn)
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def edit_expense(phone_number: str, expense_id: int, amount: float = None, 
                      category: str = None, note: str = None, **kwargs):
    """Edit an expense (only if owned by user)."""
    if kwargs:
        print(f"⚠ Ignoring extra parameters: {list(kwargs.keys())}")
    
    try:
        conn = await get_conn()
        try:
            # Verify ownership
            owner = await conn.fetchval(
                "SELECT phone_number FROM expenses WHERE id = $1",
                expense_id
            )
            if owner != phone_number:
                return {"status": "error", "message": "Not authorized"}
            
            # Build update query
            updates = []
            params = [expense_id]
            param_num = 2
            
            if amount is not None:
                updates.append(f"amount = ${param_num}")
                params.append(amount)
                param_num += 1
            if category is not None:
                updates.append(f"category = ${param_num}")
                params.append(category)
                param_num += 1
            if note is not None:
                updates.append(f"note = ${param_num}")
                params.append(note)
                param_num += 1
            
            if not updates:
                return {"status": "error", "message": "No fields to update"}
            
            query = f"UPDATE expenses SET {', '.join(updates)} WHERE id = $1"
            await conn.execute(query, *params)
            
            return {"status": "success", "message": "Expense updated"}
        finally:
            await db_pool.release(conn)
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def delete_expense(phone_number: str, expense_id: int, **kwargs):
    """Delete an expense (only if owned by user)."""
    if kwargs:
        print(f"⚠ Ignoring extra parameters: {list(kwargs.keys())}")
    
    try:
        conn = await get_conn()
        try:
            # Verify ownership
            owner = await conn.fetchval(
                "SELECT phone_number FROM expenses WHERE id = $1",
                expense_id
            )
            if owner != phone_number:
                return {"status": "error", "message": "Not authorized"}
            
            await conn.execute("DELETE FROM expenses WHERE id = $1", expense_id)
            return {"status": "success", "message": "Expense deleted"}
        finally:
            await db_pool.release(conn)
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def get_summary(phone_number: str, start_date: str = None, end_date: str = None, **kwargs):
    """Get expense summary by category."""
    if kwargs:
        print(f"⚠ Ignoring extra parameters: {list(kwargs.keys())}")
    
    try:
        conn = await get_conn()
        try:
            if start_date and end_date:
                rows = await conn.fetch(
                    """SELECT category, SUM(amount) as total, COUNT(*) as count
                       FROM expenses
                       WHERE phone_number = $1 AND date BETWEEN $2 AND $3
                       GROUP BY category ORDER BY total DESC""",
                    phone_number, start_date, end_date
                )
            else:
                rows = await conn.fetch(
                    """SELECT category, SUM(amount) as total, COUNT(*) as count
                       FROM expenses WHERE phone_number = $1
                       GROUP BY category ORDER BY total DESC""",
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

if _name_ == "_main_":
    print("Starting Expense Tracker MCP Server")
    mcp.run(transport="http", host="0.0.0.0", port=8081)