#!/usr/bin/env python3
"""
Inspect Neo4j nodes and relationships to understand the graph structure.
"""
import asyncio
from neo4j import AsyncGraphDatabase

async def inspect_graph():
    """Inspect all nodes and relationships in Neo4j"""
    
    uri = "neo4j://localhost:7687"
    driver = AsyncGraphDatabase.driver(uri, auth=("neo4j", "enbd_password"))
    
    try:
        async with driver.session() as session:
            print("=" * 80)
            print("NEO4J GRAPH INSPECTION")
            print("=" * 80)
            
            # Count nodes by label
            print("\n📊 NODE COUNTS BY LABEL:")
            result = await session.run("MATCH (n) RETURN labels(n) as labels, count(*) as count")
            records = await result.data()
            for record in records:
                labels = record['labels'][0] if record['labels'] else 'Unknown'
                count = record['count']
                print(f"  {labels}: {count}")
            
            # Show ServiceCategory nodes
            print("\n📁 SERVICE CATEGORIES:")
            result = await session.run("MATCH (sc:ServiceCategory) RETURN sc.id, sc.name ORDER BY sc.id")
            records = await result.data()
            for record in records:
                print(f"  [{record['sc.id']}] {record['sc.name']}")
            
            # Show Document nodes
            print("\n📄 DOCUMENTS:")
            result = await session.run("""
                MATCH (d:Document)
                RETURN d.id, d.title, d.file_hash LIMIT 10
            """)
            records = await result.data()
            for record in records:
                print(f"  ID: {record['d.id']}")
                print(f"    Title: {record['d.title']}")
                print(f"    Hash: {record['d.file_hash']}")
            
            # Show DocumentChunk nodes
            print("\n✂️ DOCUMENT CHUNKS:")
            result = await session.run("""
                MATCH (dc:DocumentChunk)
                RETURN count(*) as count, 
                       sum(CASE WHEN dc.embedding IS NOT NULL THEN 1 ELSE 0 END) as with_embeddings
            """)
            records = await session.data()
            for record in records:
                print(f"  Total chunks: {record['count']}")
                print(f"  Chunks with embeddings: {record['with_embeddings']}")
            
            # Show relationships
            print("\n🔗 RELATIONSHIPS:")
            result = await session.run("""
                MATCH (n)-[r]->(m)
                RETURN type(r) as rel_type, count(*) as count
                GROUP BY type(r)
            """)
            records = await result.data()
            for record in records:
                print(f"  {record['rel_type']}: {record['count']}")
            
            # Show all properties in Document nodes
            print("\n🔍 DOCUMENT NODE PROPERTIES:")
            result = await session.run("""
                MATCH (d:Document)
                RETURN properties(d) as props LIMIT 1
            """)
            record = await session.single(result)
            if record:
                for key, value in record['props'].items():
                    print(f"  {key}: {type(value).__name__}")
            
            # Show all properties in DocumentChunk nodes
            print("\n🔍 DOCUMENT CHUNK NODE PROPERTIES:")
            result = await session.run("""
                MATCH (dc:DocumentChunk)
                RETURN properties(dc) as props LIMIT 1
            """)
            record = await session.single(result)
            if record:
                for key, value in record['props'].items():
                    val_type = type(value).__name__
                    if key == 'embedding':
                        if value:
                            print(f"  {key}: list[{len(value)} floats]")
                        else:
                            print(f"  {key}: None")
                    else:
                        print(f"  {key}: {val_type}")
            
            print("\n" + "=" * 80)
            
    finally:
        await driver.close()

if __name__ == "__main__":
    asyncio.run(inspect_graph())
