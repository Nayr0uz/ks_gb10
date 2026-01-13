import asyncio
import sys
sys.path.append('/app/shared')
from database import DatabaseManager

async def check():
    db = DatabaseManager('neo4j://neo4j:enbd_password@neo4j:7687')
    await db.initialize()
    
    categories = await db.execute_query('MATCH (sc:ServiceCategory) RETURN count(*) as count')
    cat_count = categories[0]['count'] if categories else 0
    print(f'Categories: {cat_count}')
    
    documents = await db.execute_query('MATCH (d:Document) RETURN count(*) as count')
    doc_count = documents[0]['count'] if documents else 0
    print(f'Documents: {doc_count}')
    
    # Check both Chunk and DocumentChunk labels
    chunks_data = await db.execute_query('MATCH (c:Chunk) RETURN count(*) as total, sum(CASE WHEN c.embedding IS NOT NULL THEN 1 ELSE 0 END) as with_emb')
    if chunks_data:
        print(f'Chunks (Chunk label): {chunks_data[0]["total"]}, With embeddings: {chunks_data[0]["with_emb"]}')
    
    doc_chunks = await db.execute_query('MATCH (dc:DocumentChunk) RETURN count(*) as total')
    if doc_chunks:
        print(f'DocumentChunk nodes: {doc_chunks[0]["total"]}')
    
    # Show a sample document
    doc = await db.execute_query('MATCH (d:Document) RETURN d.id, d.title LIMIT 1')
    if doc:
        print(f'\nSample Document: {doc[0]["d.id"]} - {doc[0]["d.title"]}')
    
    # Show chunk content
    chunk = await db.execute_query('MATCH (c:Chunk) RETURN c.id, c.content LIMIT 1')
    if chunk:
        print(f'\nSample Chunk: {chunk[0]["c.id"]}')
        print(f'Content: {chunk[0]["c.content"][:100]}...')
    
    await db.close()

asyncio.run(check())

