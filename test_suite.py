#!/usr/bin/env python3
"""
Comprehensive Test Suite for MCP Database Server
Combines functionality from all individual test files into one unified test suite.
"""

import asyncio
import os
import sys
import json
import logging
from pathlib import Path
from sqlalchemy import text
from typing import Dict, List, Any, Optional

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent / 'app'))

from db import DatabaseManager
from nl_to_sql import NLToSQLConverter

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MCPTestSuite:
    """Comprehensive test suite for MCP Database Server"""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize test suite with optional database URL"""
        self.database_url = database_url or 'sqlite+aiosqlite:///test_suite.db'
        self.db_manager = None
        self.nl_converter = None
        self.test_results = {}
        
    async def setup(self):
        """Set up test environment and components"""
        print("Setting up test environment...")
        
        # Set environment variable
        os.environ['DATABASE_URL'] = self.database_url
        
        # Initialize components
        self.db_manager = DatabaseManager()
        self.nl_converter = NLToSQLConverter()
        
        # Test initial connection
        if not await self.db_manager.test_connection():
            raise Exception(f"Failed to connect to database: {self.database_url}")
        
        print(f"Connected to {self.db_manager.database_type} database")
        return True
    
    async def create_test_data(self):
        """Create comprehensive test database with realistic data"""
        print("Creating test database with sample data...")
        
        try:
            # Get database type to use appropriate SQL syntax
            db_type = self.db_manager.database_type
            
            async with self.db_manager.engine.begin() as conn:
                # Create customers table (database-specific syntax)
                if db_type == 'postgresql':
                    await conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS customers (
                            id SERIAL PRIMARY KEY,
                            first_name VARCHAR(255) NOT NULL,
                            last_name VARCHAR(255) NOT NULL,
                            email VARCHAR(255) UNIQUE NOT NULL,
                            phone VARCHAR(255),
                            address TEXT,
                            city VARCHAR(255),
                            state VARCHAR(255),
                            zip_code VARCHAR(255)
                        )
                    """))
                else:
                    await conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS customers (
                            id INTEGER PRIMARY KEY,
                            first_name VARCHAR(255) NOT NULL,
                            last_name VARCHAR(255) NOT NULL,
                            email VARCHAR(255) UNIQUE NOT NULL,
                            phone VARCHAR(255),
                            address TEXT,
                            city VARCHAR(255),
                            state VARCHAR(255),
                            zip_code VARCHAR(255)
                        )
                    """))
                
                # Create products table (database-specific syntax)
                if db_type == 'postgresql':
                    await conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS products (
                            id SERIAL PRIMARY KEY,
                            name VARCHAR(255) NOT NULL,
                            description TEXT,
                            price DECIMAL(10,2) NOT NULL,
                            category VARCHAR(255),
                            stock_quantity INTEGER DEFAULT 0
                        )
                    """))
                else:
                    await conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS products (
                            id INTEGER PRIMARY KEY,
                            name VARCHAR(255) NOT NULL,
                            description TEXT,
                            price DECIMAL(10,2) NOT NULL,
                            category VARCHAR(255),
                            stock_quantity INTEGER DEFAULT 0
                        )
                    """))
                
                # Create orders table (database-specific syntax)
                if db_type == 'postgresql':
                    await conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS orders (
                            id SERIAL PRIMARY KEY,
                            customer_id INTEGER,
                            total_amount DECIMAL(10,2),
                            status VARCHAR(255) DEFAULT 'pending'
                        )
                    """))
                else:
                    await conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS orders (
                            id INTEGER PRIMARY KEY,
                            customer_id INTEGER,
                            total_amount DECIMAL(10,2),
                            status VARCHAR(255) DEFAULT 'pending'
                        )
                    """))
                
                # Create order_items table (database-specific syntax)
                if db_type == 'postgresql':
                    await conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS order_items (
                            id SERIAL PRIMARY KEY,
                            order_id INTEGER,
                            product_id INTEGER,
                            quantity INTEGER,
                            unit_price DECIMAL(10,2)
                        )
                    """))
                else:
                    await conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS order_items (
                            id INTEGER PRIMARY KEY,
                            order_id INTEGER,
                            product_id INTEGER,
                            quantity INTEGER,
                            unit_price DECIMAL(10,2)
                        )
                    """))
                
                # Insert sample customers (database-specific approach)
                customers_data = [
                    ('John', 'Doe', 'john.doe@email.com', '555-0101', 'New York', 'NY'),
                    ('Jane', 'Smith', 'jane.smith@email.com', '555-0102', 'Los Angeles', 'CA'),
                    ('Bob', 'Johnson', 'bob.johnson@email.com', '555-0103', 'Chicago', 'IL'),
                    ('Alice', 'Brown', 'alice.brown@email.com', '555-0104', 'Houston', 'TX'),
                    ('Charlie', 'Wilson', 'charlie.wilson@email.com', '555-0105', 'Phoenix', 'AZ'),
                    ('Eva', 'Davis', 'eva.davis@email.com', '555-0106', 'Philadelphia', 'PA'),
                    ('Frank', 'Miller', 'frank.miller@email.com', '555-0107', 'San Antonio', 'TX'),
                    ('Grace', 'Lee', 'grace.lee@email.com', '555-0108', 'San Diego', 'CA'),
                    ('Henry', 'Garcia', 'henry.garcia@email.com', '555-0109', 'Dallas', 'TX'),
                    ('Iris', 'Martinez', 'iris.martinez@email.com', '555-0110', 'San Jose', 'CA')
                ]
                
                for customer in customers_data:
                    try:
                        if db_type == 'postgresql':
                            # PostgreSQL with SERIAL (auto-increment) - don't specify id
                            await conn.execute(text("""
                                INSERT INTO customers (first_name, last_name, email, phone, city, state) 
                                VALUES (:first_name, :last_name, :email, :phone, :city, :state)
                            """), {
                                'first_name': customer[0], 'last_name': customer[1],
                                'email': customer[2], 'phone': customer[3], 'city': customer[4], 'state': customer[5]
                            })
                        else:
                            # SQLite with explicit IDs
                            await conn.execute(text("""
                                INSERT INTO customers (id, first_name, last_name, email, phone, city, state) 
                                VALUES (:id, :first_name, :last_name, :email, :phone, :city, :state)
                            """), {
                                'id': customers_data.index(customer) + 1, 'first_name': customer[0], 'last_name': customer[1],
                                'email': customer[2], 'phone': customer[3], 'city': customer[4], 'state': customer[5]
                            })
                    except Exception as e:
                        print(f"Warning: Failed to insert customer {customer[0]} {customer[1]}: {e}")
                        pass  # Ignore duplicate key errors
                
                # Insert sample products (database-specific approach)
                products_data = [
                    ('Laptop Pro', 'High-performance laptop', 1299.99, 'Electronics', 50),
                    ('Wireless Mouse', 'Ergonomic wireless mouse', 29.99, 'Electronics', 100),
                    ('Mechanical Keyboard', 'RGB mechanical keyboard', 79.99, 'Electronics', 75),
                    ('Office Chair', 'Ergonomic office chair', 199.99, 'Furniture', 25),
                    ('Standing Desk', 'Adjustable standing desk', 399.99, 'Furniture', 15),
                    ('Coffee Mug', 'Ceramic coffee mug', 12.99, 'Kitchen', 200),
                    ('Water Bottle', 'Stainless steel water bottle', 24.99, 'Kitchen', 150),
                    ('Notebook', 'Spiral notebook', 5.99, 'Office', 300),
                    ('Pen Set', '12-pack ballpoint pens', 8.99, 'Office', 250),
                    ('USB Cable', 'USB-C charging cable', 15.99, 'Electronics', 80)
                ]
                
                for product in products_data:
                    try:
                        if db_type == 'postgresql':
                            # PostgreSQL with SERIAL (auto-increment) - don't specify id
                            await conn.execute(text("""
                                INSERT INTO products (name, description, price, category, stock_quantity) 
                                VALUES (:name, :description, :price, :category, :stock_quantity)
                            """), {
                                'name': product[0], 'description': product[1], 'price': product[2],
                                'category': product[3], 'stock_quantity': product[4]
                            })
                        else:
                            # SQLite with explicit IDs
                            await conn.execute(text("""
                                INSERT INTO products (id, name, description, price, category, stock_quantity) 
                                VALUES (:id, :name, :description, :price, :category, :stock_quantity)
                            """), {
                                'id': products_data.index(product) + 1, 'name': product[0], 'description': product[1], 
                                'price': product[2], 'category': product[3], 'stock_quantity': product[4]
                            })
                    except Exception as e:
                        print(f"Warning: Failed to insert product {product[0]}: {e}")
                        pass
                
                # Insert sample orders (simplified for database compatibility)
                orders_data = [
                    (1329.98, 'completed'), (109.98, 'completed'), (199.99, 'pending'),
                    (24.99, 'completed'), (479.98, 'completed'), (37.98, 'pending'),
                    (1315.98, 'completed'), (14.98, 'completed'), (399.99, 'pending'),
                    (15.99, 'completed'), (79.99, 'completed'), (29.99, 'pending'),
                    (200.98, 'completed'), (12.99, 'completed'), (1299.99, 'pending')
                ]
                
                for i, order in enumerate(orders_data):
                    try:
                        customer_id = (i % 10) + 1  # Assign to customers 1-10 cyclically
                        if db_type == 'postgresql':
                            # PostgreSQL with SERIAL - don't specify id, use LIMIT for customer_id
                            await conn.execute(text("""
                                INSERT INTO orders (customer_id, total_amount, status) 
                                VALUES (:customer_id, :total_amount, :status)
                            """), {
                                'customer_id': min(customer_id, 3),  # Only reference first 3 customers to be safe
                                'total_amount': order[0], 'status': order[1]
                            })
                        else:
                            # SQLite with explicit IDs
                            await conn.execute(text("""
                                INSERT INTO orders (id, customer_id, total_amount, status) 
                                VALUES (:id, :customer_id, :total_amount, :status)
                            """), {
                                'id': i + 1, 'customer_id': customer_id,
                                'total_amount': order[0], 'status': order[1]
                            })
                    except Exception as e:
                        print(f"Warning: Failed to insert order {i + 1}: {e}")
                        pass
                
                # Insert a few sample order items (simplified to avoid foreign key issues)
                simple_order_items = [
                    (1, 1, 1, 1299.99), (1, 2, 1, 29.99), (2, 3, 1, 79.99), 
                    (2, 2, 1, 29.99), (3, 1, 1, 199.99)
                ]
                
                for item in simple_order_items:
                    try:
                        if db_type == 'postgresql':
                            # PostgreSQL with SERIAL - don't specify id
                            await conn.execute(text("""
                                INSERT INTO order_items (order_id, product_id, quantity, unit_price) 
                                VALUES (:order_id, :product_id, :quantity, :unit_price)
                            """), {
                                'order_id': item[0], 'product_id': item[1], 
                                'quantity': item[2], 'unit_price': item[3]
                            })
                        else:
                            # SQLite with explicit IDs
                            await conn.execute(text("""
                                INSERT INTO order_items (id, order_id, product_id, quantity, unit_price) 
                                VALUES (:id, :order_id, :product_id, :quantity, :unit_price)
                            """), {
                                'id': simple_order_items.index(item) + 1, 'order_id': item[0], 'product_id': item[1], 
                                'quantity': item[2], 'unit_price': item[3]
                            })
                    except Exception as e:
                        print(f"Warning: Failed to insert order item: {e}")
                        pass
            
            print("Test database created successfully")
            return True
            
        except Exception as e:
            print(f"ERROR: Error creating test data: {e}")
            return False
    
    async def test_async_fix(self):
        """Test that the async bug is fixed (no await on synchronous method)"""
        print("\nTesting Async Bug Fix...")
        
        try:
            # Get table schemas for context
            tables = await self.db_manager.list_tables()
            table_schemas = {}
            for table in tables:
                columns = await self.db_manager.describe_table(table['table_name'])
                table_schemas[table['table_name']] = columns
            
            # Test the FIXED line (no await on non-async method)
            query = "show me all customers"
            sql_query = self.nl_converter.convert_to_sql(query, table_schemas)  # FIXED: No await
            
            # Execute the generated query
            results = await self.db_manager.execute_safe_query(sql_query, limit=3)
            
            print(f"   Async fix verified: '{query}' -> '{sql_query}'")
            print(f"   Query executed successfully: {len(results)} rows returned")
            
            return True, "Async bug fix working correctly"
            
        except Exception as e:
            print(f"   Async fix test failed: {e}")
            return False, f"Async fix error: {str(e)}"
    
    async def test_database_operations(self):
        """Test core database operations"""
        print("\nTesting Database Operations...")
        
        tests_passed = 0
        total_tests = 0
        errors = []
        
        # Test 1: Connection test
        total_tests += 1
        try:
            connection_ok = await self.db_manager.test_connection()
            if connection_ok:
                print("    Database connection test passed")
                tests_passed += 1
            else:
                print("    Database connection test failed")
                errors.append("Database connection failed")
        except Exception as e:
            print(f"    Connection test error: {e}")
            errors.append(f"Connection test error: {str(e)}")
        
        # Test 2: List tables
        total_tests += 1
        try:
            tables = await self.db_manager.list_tables()
            if len(tables) >= 4:  # We created 4 tables
                print(f"   List tables passed: {len(tables)} tables found")
                print(f"      Tables: {[t['table_name'] for t in tables]}")
                tests_passed += 1
            else:
                print(f"   List tables failed: Expected >= 4 tables, got {len(tables)}")
                errors.append(f"Expected >= 4 tables, got {len(tables)}")
        except Exception as e:
            print(f"   List tables error: {e}")
            errors.append(f"List tables error: {str(e)}")
        
        # Test 3: Describe table
        total_tests += 1
        try:
            columns = await self.db_manager.describe_table('customers')
            if len(columns) >= 5:  # customers table has many columns
                print(f"    Describe table passed: {len(columns)} columns in customers table")
                tests_passed += 1
            else:
                print(f"    Describe table failed: Expected >= 5 columns, got {len(columns)}")
                errors.append(f"Expected >= 5 columns, got {len(columns)}")
        except Exception as e:
            print(f"    Describe table error: {e}")
            errors.append(f"Describe table error: {str(e)}")
        
        # Test 4: Execute safe query
        total_tests += 1
        try:
            results = await self.db_manager.execute_safe_query("SELECT COUNT(*) as total FROM customers")
            if results and len(results) > 0 and results[0]['total'] == 10:
                print("    Execute safe query passed: Correct customer count")
                tests_passed += 1
            else:
                print(f"    Execute safe query failed: Expected 10 customers, got {results}")
                errors.append(f"Expected 10 customers, got {results}")
        except Exception as e:
            print(f"    Execute safe query error: {e}")
            errors.append(f"Execute safe query error: {str(e)}")
        
        success = tests_passed == total_tests
        summary = f"{tests_passed}/{total_tests} database operation tests passed"
        
        return success, summary, errors
    
    async def test_natural_language_queries(self):
        """Test natural language to SQL conversion and execution"""
        print("\nTesting Natural Language Queries...")
        
        # Get table schemas for context
        tables = await self.db_manager.list_tables()
        table_schemas = {}
        for table in tables:
            columns = await self.db_manager.describe_table(table['table_name'])
            table_schemas[table['table_name']] = columns
        
        test_queries = [
            ("show me all customers", "Basic customer query"),
            ("count all orders", "Count orders"),
            ("list products with price over 50", "Price filter query"),
            ("show top 5 customers", "Limit query"),
            ("find orders with status pending", "Status filter"),
            ("get total revenue from completed orders", "Aggregation query")
        ]
        
        tests_passed = 0
        total_tests = len(test_queries)
        errors = []
        
        for nl_query, description in test_queries:
            try:
                sql_query = self.nl_converter.convert_to_sql(nl_query, table_schemas)
                results = await self.db_manager.execute_safe_query(sql_query, limit=10)
                
                print(f"    '{description}': {len(results)} rows returned")
                print(f"      NL: '{nl_query}'")
                print(f"      SQL: '{sql_query}'")
                
                tests_passed += 1
                
            except Exception as e:
                print(f"    '{description}' failed: {str(e)}")
                errors.append(f"{description}: {str(e)}")
        
        success = tests_passed == total_tests
        summary = f"{tests_passed}/{total_tests} NL query tests passed"
        
        return success, summary, errors
    
    async def test_security_features(self):
        """Test security and safety features"""
        print("\n Testing Security Features...")
        
        dangerous_queries = [
            ("DROP TABLE customers", "Table deletion"),
            ("DELETE FROM customers", "Mass deletion"), 
            ("UPDATE customers SET email = 'hacked'", "Mass update"),
            ("INSERT INTO customers VALUES (999, 'Hacker', 'McHack', 'hack@evil.com', '', '', '', '', '', '')", "Unauthorized insert"),
            ("ALTER TABLE customers ADD COLUMN backdoor TEXT", "Schema modification"),
            ("CREATE TABLE malicious (id INT, data TEXT)", "Table creation")
        ]
        
        tests_passed = 0
        total_tests = len(dangerous_queries)
        errors = []
        
        for dangerous_query, description in dangerous_queries:
            try:
                await self.db_manager.execute_safe_query(dangerous_query)
                print(f"   SECURITY BREACH: {description} was allowed!")
                errors.append(f"Security breach: {description}")
            except ValueError as e:
                if "unsafe operations" in str(e).lower():
                    print(f"    {description} blocked correctly")
                    tests_passed += 1
                else:
                    print(f"    {description} blocked with unexpected error: {str(e)[:50]}...")
                    # Still count as success since it was blocked
                    tests_passed += 1
            except Exception as e:
                print(f"    {description} caused unexpected error: {str(e)[:50]}...")
                errors.append(f"{description}: Unexpected error")
        
        success = tests_passed == total_tests
        summary = f"{tests_passed}/{total_tests} security tests passed"
        
        return success, summary, errors
    
    async def test_container_compatibility(self):
        """Test Docker container compatibility"""
        print("\n Testing Container Compatibility...")
        
        try:
            # Test environment variables
            db_url = os.getenv('DATABASE_URL', 'Not set')
            python_version = sys.version
            working_dir = os.getcwd()
            
            print(f"    Environment check:")
            print(f"      Python: {python_version.split()[0]}")
            print(f"      Working Dir: {working_dir}")
            print(f"      Database URL: {db_url}")
            print(f"      Database Type: {self.db_manager.database_type}")
            
            # Test basic functionality that would work in container
            tables = await self.db_manager.list_tables()
            result = await self.db_manager.execute_safe_query("SELECT 1 as test_value")
            
            if result and result[0]['test_value'] == 1:
                print("    Container compatibility test passed")
                return True, "Container compatibility verified"
            else:
                return False, "Container compatibility test failed"
                
        except Exception as e:
            print(f"    Container test error: {e}")
            return False, f"Container test error: {str(e)}"
    
    async def run_comprehensive_test_suite(self):
        """Run all tests and generate comprehensive report"""
        print("Starting Comprehensive MCP Database Server Test Suite")
        print("=" * 70)
        
        # Setup test environment
        try:
            await self.setup()
            await self.create_test_data()
        except Exception as e:
            print(f" Test setup failed: {e}")
            return False
        
        # Run all test categories
        test_categories = [
            ("Async Bug Fix", self.test_async_fix),
            ("Database Operations", self.test_database_operations),
            ("Natural Language Queries", self.test_natural_language_queries),
            ("Security Features", self.test_security_features),
            ("Container Compatibility", self.test_container_compatibility)
        ]
        
        overall_results = {}
        total_passed = 0
        total_tests = len(test_categories)
        
        for category_name, test_func in test_categories:
            try:
                if category_name == "Async Bug Fix" or category_name == "Container Compatibility":
                    # These return (success, message)
                    success, message = await test_func()
                    overall_results[category_name] = {
                        'passed': success,
                        'summary': message,
                        'errors': [] if success else [message]
                    }
                else:
                    # These return (success, summary, errors)
                    success, summary, errors = await test_func()
                    overall_results[category_name] = {
                        'passed': success,
                        'summary': summary,
                        'errors': errors
                    }
                
                if success:
                    total_passed += 1
                    
            except Exception as e:
                print(f" Test category '{category_name}' failed with error: {e}")
                overall_results[category_name] = {
                    'passed': False,
                    'summary': f"Test failed with error: {str(e)}",
                    'errors': [str(e)]
                }
        
        # Generate final report
        print("\n" + "=" * 70)
        print(" COMPREHENSIVE TEST RESULTS REPORT")
        print("=" * 70)
        
        for category, results in overall_results.items():
            status = "PASS" if results['passed'] else "FAIL"
            print(f"{category:<30} {status}")
            print(f"   {results['summary']}")
            
            if results['errors']:
                print(f"   Errors: {', '.join(results['errors'][:2])}{'...' if len(results['errors']) > 2 else ''}")
            print()
        
        print(f"Overall Score: {total_passed}/{total_tests} test categories passed")
        
        if total_passed == total_tests:
            print("\n ALL TESTS PASSED! MCP Database Server is fully functional!")
            success = True
        else:
            print(f"\n {total_tests - total_passed} test category(ies) failed.")
            success = False
        
        # Store results for external access
        self.test_results = overall_results
        self.test_results['overall'] = {
            'passed': total_passed,
            'total': total_tests,
            'success': success
        }
        
        # Cleanup
        if self.db_manager and self.db_manager.engine:
            await self.db_manager.engine.dispose()
        
        print("=" * 70)
        return success

async def main():
    """Main test runner function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='MCP Database Server Test Suite')
    parser.add_argument('--database-url', help='Database URL to test against')
    parser.add_argument('--quiet', action='store_true', help='Reduce output verbosity')
    
    args = parser.parse_args()
    
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    # Run tests
    test_suite = MCPTestSuite(database_url=args.database_url)
    success = await test_suite.run_comprehensive_test_suite()
    
    # Return appropriate exit code
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)