#!/usr/bin/env python3
"""
Initialize Neo4j database with constraints, indexes, and service categories.
This script should be run after Neo4j is running.
"""
import asyncio
from neo4j import AsyncGraphDatabase
import sys

async def initialize_database():
    """Initialize the Neo4j database with schema and data."""
    
    # Connection parameters
    uri = "neo4j://neo4j:enbd_password@localhost:7687"
    
    driver = AsyncGraphDatabase.driver(uri, auth=("neo4j", "enbd_password"))
    
    try:
        async with driver.session() as session:
            print("🔄 Initializing Neo4j database...")
            
            # Create constraints
            constraints = [
                "CREATE CONSTRAINT user_email IF NOT EXISTS FOR (u:User) REQUIRE u.email IS UNIQUE",
                "CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
                "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
                "CREATE CONSTRAINT service_category_name IF NOT EXISTS FOR (sc:ServiceCategory) REQUIRE sc.name IS UNIQUE",
            ]
            
            for constraint in constraints:
                try:
                    await session.run(constraint)
                    print(f"✅ {constraint.split('IF NOT EXISTS')[0].strip()}")
                except Exception as e:
                    print(f"⚠️  {constraint.split('IF NOT EXISTS')[0].strip()}: {e}")
            
            # Create indexes
            indexes = [
                "CREATE INDEX user_email_idx IF NOT EXISTS FOR (u:User) ON (u.email)",
                "CREATE INDEX user_id_idx IF NOT EXISTS FOR (u:User) ON (u.id)",
                "CREATE INDEX document_title_idx IF NOT EXISTS FOR (d:Document) ON (d.title)",
                "CREATE INDEX service_category_id_idx IF NOT EXISTS FOR (sc:ServiceCategory) ON (sc.id)",
                "CREATE INDEX presentation_id_idx IF NOT EXISTS FOR (p:Presentation) ON (p.id)",
            ]
            
            for index in indexes:
                try:
                    await session.run(index)
                    print(f"✅ {index.split('IF NOT EXISTS')[0].strip()}")
                except Exception as e:
                    print(f"⚠️  {index.split('IF NOT EXISTS')[0].strip()}: {e}")
            
            # Create label indexes
            label_indexes = [
                "CREATE INDEX document_label IF NOT EXISTS FOR (d:Document)",
                "CREATE INDEX user_label IF NOT EXISTS FOR (u:User)",
                "CREATE INDEX presentation_label IF NOT EXISTS FOR (p:Presentation)",
                "CREATE INDEX service_category_label IF NOT EXISTS FOR (sc:ServiceCategory)",
            ]
            
            for idx in label_indexes:
                try:
                    await session.run(idx)
                    print(f"✅ {idx.split('IF NOT EXISTS')[0].strip()}")
                except Exception as e:
                    print(f"⚠️  {idx.split('IF NOT EXISTS')[0].strip()}: {e}")
            
            # Create Service Categories
            print("\n🔄 Creating service categories...")
            categories = [
                (1, 'Accounts & Savings', 'Documents about deposit accounts, current and savings accounts, and related terms.'),
                (2, 'Loans', 'Documents covering personal, mortgage, auto, and business loan products and terms.'),
                (3, 'Cards', 'Information on debit, credit, and prepaid card products and fees.'),
                (4, 'Investments', 'Materials related to investment products, mutual funds, and wealth services.'),
                (5, 'Business & Corporate Banking', 'Services and products tailored for corporate and business customers.'),
                (6, 'Insurance (Bancassurance)', 'Insurance products offered through the bank (bancassurance).'),
                (7, 'Digital & E-Banking', 'Digital channels, mobile and online banking services, and related security guidance.'),
                (8, 'Payroll Services', 'Payroll and salary account services for employers and employees.'),
                (9, 'General Information', 'General bank information, annual reports, and documents that span multiple categories.'),
            ]
            
            for cat_id, name, description in categories:
                query = """
                MERGE (sc:ServiceCategory {id: $id, name: $name})
                SET sc.description = $description, sc.created_at = datetime()
                RETURN sc
                """
                try:
                    result = await session.run(query, id=cat_id, name=name, description=description)
                    record = await result.single()
                    print(f"✅ Category: {name}")
                except Exception as e:
                    print(f"⚠️  Category {name}: {e}")
            
            print("\n✨ Neo4j database initialization completed!")
            
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        await driver.close()

if __name__ == "__main__":
    asyncio.run(initialize_database())
