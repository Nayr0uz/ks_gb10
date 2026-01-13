import os
import asyncio
import json
from datetime import datetime
import re
import math
from typing import List, Optional, Dict, Any
from shared.database import get_database
from ollama import Client
import logging

logger = logging.getLogger(__name__)

class UnifiedLLMClient:
    """Wrapper to support both Ollama and OpenAI-compatible backends"""
    def __init__(self, host: str):
        self.host = host
        self.backend_type = os.getenv("LLM_BACKEND_TYPE", "ollama").lower()
        
        if self.backend_type == "openai":
            from openai import OpenAI
            # Ensure host ends with /v1 if not present
            base_url = os.getenv("LLM_OPENAI_BASE_URL", host)
            if not base_url.endswith("/v1"):
                base_url = f"{base_url}/v1"
            self.client = OpenAI(base_url=base_url, api_key="sk-no-key-required")
            logger.info(f"Initialized UnifiedLLMClient with OpenAI backend at {base_url}")
        else:
            self.client = Client(host=host)
            logger.info(f"Initialized UnifiedLLMClient with Ollama backend at {host}")

    def generate(self, model: str, prompt: str, format: str = None) -> Dict[str, Any]:
        """Unified generate method that mimics Ollama's response format"""
        if self.backend_type == "openai":
            try:
                # Map 'json' format to response_format param if supported
                response_format = {"type": "json_object"} if format == "json" else None
                
                messages = [{"role": "user", "content": prompt}]
                
                # Check for system prompt in prompt (if manual formatting was used)
                # Ideally prompts should be split, but for this wrapper we'll send it as user message 
                # or try to split if it follows a pattern.
                # For compatibility, just sending as user message usually works fine with smart models.
                
                kwargs = {
                    "model": model,
                    "messages": messages,
                    "temperature": 0.7,
                }
                if response_format:
                    kwargs["response_format"] = response_format

                response = self.client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content
                return {"response": content}
            except Exception as e:
                logger.error(f"OpenAI backend error: {e}")
                raise
        else:
            # Pass through to Ollama client
            return self.client.generate(model=model, prompt=prompt, format=format)

# ==========================#
# SCOPE: Smart Document & Topic Selection
# ==========================#
class PresentationScope:
    """Smart scope handling inspired by Dina's approach"""
    
    WHOLE_DOCUMENT = "whole_document"
    SPECIFIC_TOPICS = "specific_topics"
    
    @staticmethod
    def is_valid(scope: str) -> bool:
        return scope in [PresentationScope.WHOLE_DOCUMENT, PresentationScope.SPECIFIC_TOPICS]

# ==========================#
# STAGE 1: ADVANCED TOPIC EXTRACTION (STRONGER METHODS)
# ==========================#

async def _extract_topics_with_multiple_methods(
    client: Any,
    model_name: str,
    document_chunks: List[str],
    document_title: str
) -> List[str]:
    """
    Extract topics using a single comprehensive LLM prompt.
    Combines all 5 methods (structural, headings, keywords, sections, clustering) in one call.
    Much faster (1 LLM call instead of 5) and more coherent.
    """
    print("📌 UNIFIED TOPIC EXTRACTION (All Methods in One Prompt)")
    
    if not document_chunks:
        return []
    
    # Prepare document excerpt for analysis
    sample_chunks = document_chunks[:15]
    combined_text = "\n\n".join(sample_chunks)
    
    prompt = f"""You are a financial document analyzer. Extract COMPREHENSIVE list of topics from this document using ALL of these approaches:

DOCUMENT TITLE: {document_title}

DOCUMENT CONTENT:
---
{combined_text[:5000]}
---

EXTRACTION TASK - Use ALL 5 methods simultaneously:
1. STRUCTURAL ANALYSIS: Identify main topics from document structure and sections
2. HEADINGS ANALYSIS: Extract topics from section titles and headers
3. KEYWORD EXTRACTION: Find important financial terms and product names
4. SECTION PATTERNS: Look for numbered items, bullet sections, and organized topics
5. SEMANTIC CLUSTERING: Group related topics and remove duplicates automatically

OUTPUT REQUIREMENTS:
- Extract 12-15 UNIQUE topics (not names, actual topics/products/services)
- Each topic should be distinct and important
- Remove ALL duplicates (if "Loan" and "Loans" appear, keep only one)
- Rank by importance/frequency - put most important first
- Be specific: "Solar Panel Loans" not "Energy Finance"
- Focus on financial products, services, features, and key concepts from the document

RETURN FORMAT:
Return ONLY a numbered list (no other text):
1. Topic Name
2. Topic Name
3. Topic Name
...and so on

Topics must be EXACT or VERY CLOSE to how they appear in the document."""
    
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: client.generate(model=model_name, prompt=prompt))
        response_text = resp["response"].strip()
        topics = []
        
        for line in response_text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Remove numbering (e.g., "1. Topic" -> "Topic")
            if line and line[0].isdigit():
                # Remove leading numbers and punctuation
                parts = line.split('.', 1)
                if len(parts) > 1:
                    topic = parts[1].strip()
                else:
                    topic = line
            else:
                topic = line
            
            # Clean up and validate
            topic = topic.strip()
            if topic and len(topic) > 2:
                topics.append(topic)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_topics = []
        for topic in topics:
            topic_lower = topic.lower().strip()
            if topic_lower not in seen and len(topic_lower) > 2:
                unique_topics.append(topic)
                seen.add(topic_lower)
        
        final_topics = unique_topics[:20]  # Return top 20
        print(f"   ✓ Extracted {len(final_topics)} unique topics in 1 LLM call")
        print(f"✅ FINAL: {len(final_topics)} unique topics extracted")
        return final_topics
        
    except Exception as e:
        logger.error(f"Error in unified topic extraction: {e}")
        return []


# ==========================#
# STAGE 2: VECTOR SEARCH FOR SMART DOCUMENT MATCHING
# ==========================#

async def _find_best_document_by_embedding(
    title: str,
    db_manager
) -> Optional[Dict[str, Any]]:
    """
    Use flexible document matching with multiple strategies.
    Matches any keyword token to handle fuzzy queries like "Loans types" -> "Loan Types"
    """
    if not title or len(title.strip()) < 2:
        return None
    
    print(f"🔍 Starting document search for: '{title}'")
    
    try:
        # Normalize title for flexible matching
        normalized = re.sub(r"[^0-9A-Za-z]+", " ", title).strip().lower()
        tokens = [t for t in re.findall(r"\w+", normalized) if len(t) >= 2]
        
        if not tokens:
            print("     ❌ No valid search tokens")
            return None
        
        # STRATEGY 1: Try matching ANY token (more flexible) - "Loans types" matches "Loan" OR "Types"
        print(f"  1️⃣ Searching for ANY of these keywords: {tokens}")
        params = {}
        conds = []
        for i, tok in enumerate(tokens, start=1):
            param_name = f"token{i}"
            params[param_name] = tok
            conds.append(f"(d.title CONTAINS ${param_name} OR d.file_name CONTAINS ${param_name})")
        
        # Use OR instead of AND for flexible matching
        where_clause = " OR ".join(conds)
        query = f"""MATCH (d:Document) WHERE {where_clause}
                    RETURN d.id as id, d.title as title, d.file_name as file_name
                    ORDER BY d.created_at DESC LIMIT 1"""
        
        doc = await db_manager.fetch_one(query, params)
        if doc:
            print(f"     ✅ Found document: {doc['title']}")
            return doc
        
        # STRATEGY 2: Try partial match
        print(f"  2️⃣ Trying exact partial match...")
        doc = await db_manager.fetch_one(
            """MATCH (d:Document) WHERE d.title CONTAINS $title OR d.file_name CONTAINS $title
               RETURN d.id as id, d.title as title, d.file_name as file_name
               ORDER BY d.created_at DESC LIMIT 1""",
            {"title": title}
        )
        if doc:
            print(f"     ✅ Found document: {doc['title']}")
            return doc
        
        # STRATEGY 3: Try single token match with first major word
        print(f"  3️⃣ Trying first token match...")
        if tokens:
            first_token = tokens[0]
            doc = await db_manager.fetch_one(
                """MATCH (d:Document) WHERE d.title CONTAINS $token OR d.file_name CONTAINS $token
                   RETURN d.id as id, d.title as title, d.file_name as file_name
                   ORDER BY d.created_at DESC LIMIT 1""",
                {"token": first_token}
            )
            if doc:
                print(f"     ✅ Found document: {doc['title']}")
                return doc
        
        # STRATEGY 4: Return most recent document as fallback
        print(f"  4️⃣ No match found, using most recent document...")
        doc = await db_manager.fetch_one(
            """MATCH (d:Document) RETURN d.id as id, d.title as title, d.file_name as file_name
               ORDER BY d.created_at DESC LIMIT 1"""
        )
        
        if doc:
            print(f"     ⚠️  Using: {doc['title']}")
            print(f"     💡 For better matching, use keywords from document titles")
            return doc
        
        print("     ❌ No documents in database")
        return None
        
    except Exception as e:
        logger.error(f"Error in document search: {e}")
        # Fallback to most recent document
        try:
            doc = await db_manager.fetch_one(
                """MATCH (d:Document) RETURN d.id as id, d.title as title, d.file_name as file_name
                   ORDER BY d.created_at DESC LIMIT 1"""
            )
            return doc
        except:
            return None


# ==========================#
# STAGE 3: OUTLINE GENERATION WITH SMART SOURCE MATCHING
# ==========================#

async def _create_presentation_outline(
    client: Any,
    model_name: str,
    source_text: str,
    source_title: str,
    detail_level: str = "detailed"
) -> List[Dict[str, Any]]:
    """Generate structured outline STRICTLY from source document - NO HALLUCINATIONS"""
    
    # Adjust prompt based on detail level
    detail_instructions = {
        "beginner": "Focus on main concepts and key points. Use simple language and avoid technical jargon.",
        "intermediate": "Provide moderate depth with context. Balance technical terms with explanations.",
        "professional": "Use professional terminology and provide comprehensive detail and examples."
    }
    
    detail_guide = detail_instructions.get(detail_level, detail_instructions["intermediate"])
    
    prompt = f"""
# ROLE: You are a Financial Content Analyzer. Extract ONLY factual information from the provided document.

# **CRITICAL INSTRUCTION - TITLES MUST BE EXACT**: 
You MUST ONLY extract information that explicitly appears in the document below.
DO NOT invent, assume, or hallucinate any facts.
DO NOT add common banking practices that aren't mentioned.
DO NOT rename or rephrase titles - USE EXACT TITLES FROM THE DOCUMENT.
If information is not in the document, do not include it.

# DETAIL LEVEL: {detail_level.upper()}
{detail_guide}

# CONTEXT
- The presentation is about: "{source_title}"
- The document contains details about different products, services, or topics.
- Extract only what is actually stated in the text below.
- **IMPORTANT**: Topic titles must be EXACT matches from the document - do not generalize or rename them
- **IMPORTANT**: Extract ALL related facts and information for each topic - do not leave anything out

# SOURCE DOCUMENT (COMPLETE TEXT)
---
{source_text}
---

# YOUR TASK
1. Identify all distinct topics/products/services that are EXPLICITLY MENTIONED in the document
2. For EACH topic, use the EXACT title as it appears in the document - do NOT rename it
3. Extract ALL key points that are DIRECTLY STATED in the source text for that topic
4. Be comprehensive - include ALL relevant facts, features, terms, conditions, requirements, benefits, etc.
5. Do NOT omit any information about a topic that appears in the document
6. IMPORTANT: Only include facts that appear in the document above
7. Maximum 7-8 key points per topic (quality over quantity) - but prioritize COMPLETENESS over brevity
8. Output ONLY valid JSON

# CRITICAL TITLE RULES:
- If the document says "Solar Panel Loans", use EXACTLY "Solar Panel Loans"
- If the document says "Current Account", use EXACTLY "Current Account"
- Do NOT create new titles like "Renewable Energy and Insurance" when the actual title is "Solar Panel Loans"
- Match the EXACT wording from the document section headers

# CRITICAL FACT EXTRACTION RULES:
- Extract EVERY fact mentioned about each topic in the document section
- Do NOT skip information thinking it's "obvious" or "common knowledge"
- Include: amounts, rates, periods, conditions, eligibility, features, benefits, documents needed, fees, etc.
- If the topic mentions multiple things, extract ALL of them
- Example: If a loan mentions "up to 7 years", "4% interest", AND "includes insurance" - include ALL three facts
- Do NOT prioritize - include everything, just ensure each fact is clear and complete

# JSON OUTPUT RULES
- Root key: "topics"
- Array of objects with "title" and "key_points" (array of strings)
- title MUST be the exact title as it appears in the document
- key_points must include ALL specific facts that appear in the source document for that topic
- Do NOT include assumptions or common knowledge
- Response must be ONLY valid JSON - no other text

# EXAMPLE (if source document talks about these)
{{
  "topics": [
    {{
      "title": "Personal Loans",
      "key_points": [
        "Loan amount range: EGP 10,000 to 500,000",
        "Repayment period: up to 7 years",
        "Interest rates offered",
        "Life insurance included",
        "Quick processing",
        "Eligibility: Individuals and companies",
        "Required documents: ID, income proof"
      ]
    }}
  ]
}}

IMPORTANT: 
- Output ONLY JSON. 
- No explanations. 
- Every fact must be in the source document.
- TITLES MUST BE EXACT MATCHES FROM THE DOCUMENT.
- EXTRACT ALL FACTS - do not omit any information about each topic.
- Be comprehensive and complete in the key_points for each topic.
"""
    
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: client.generate(model=model_name, prompt=prompt, format="json"))
        response_text = resp["response"]
        outline = json.loads(response_text)
        
        if "topics" in outline and isinstance(outline["topics"], list):
            # Additional validation: limit key points to 5 per topic max
            validated_topics = []
            for topic in outline["topics"]:
                if topic.get("key_points"):
                    # Limit to max 5 key points per topic to prevent hallucination
                    topic["key_points"] = topic["key_points"][:5]
                validated_topics.append(topic)
            return validated_topics
        
        logger.warning("Invalid outline format returned")
        return []
    except Exception as e:
        logger.error(f"Error during outline generation: {e}")
        return []


# ==========================#
# STAGE 3b: TOPIC EXPANSION
# ==========================#

async def _expand_topics(
    client: Any,
    model_name: str,
    topics: List[Dict[str, Any]],
    requested_slides: int
) -> List[Dict[str, Any]]:
    """
    Expand limited topics into more subtopics for richer presentation.
    Used when we have too few topics but need more slides.
    """
    if not topics or len(topics) == 0 or requested_slides <= 0:
        return topics
    
    # Calculate how many more topics we need
    current_count = len(topics)
    content_slides_needed = requested_slides - 2  # Exclude title and conclusion
    needed = content_slides_needed - current_count
    
    if needed <= 0:
        return topics
    
    print(f"   📊 Expanding {current_count} topics into ~{content_slides_needed} topics...")
    
    # Take all key points and use them as basis for new subtopics
    all_key_points = []
    for topic in topics:
        all_key_points.extend(topic.get("key_points", [])[:5])
    
    if len(all_key_points) < needed:
        print(f"   ⚠️  Not enough key points to expand further")
        return topics
    
    prompt = f"""You have a list of key facts about a financial service. Break these into {needed} distinct subtopics, each with 3-4 related facts.

Key Facts:
{chr(10).join(f'- {p}' for p in all_key_points[:15])}

Output ONLY valid JSON with exactly {needed} subtopics:
{{
  "subtopics": [
    {{"title": "Subtopic 1", "key_points": ["fact1", "fact2", "fact3"]}},
    {{"title": "Subtopic 2", "key_points": ["fact1", "fact2"]}}
  ]
}}

Make each subtopic title distinct and specific."""
    
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: client.generate(model=model_name, prompt=prompt, format="json"))
        response_text = resp["response"]
        result = json.loads(response_text)
        
        expanded = []
        for subtopic in result.get("subtopics", [])[:needed]:
            expanded.append({
                "title": subtopic.get("title", f"Topic {len(expanded) + 1}"),
                "key_points": subtopic.get("key_points", ["Additional details"])
            })
        
        print(f"   ✅ Expanded to {len(expanded)} subtopics")
        return topics + expanded
    except Exception as e:
        logger.warning(f"Topic expansion failed: {e}, continuing with original topics")
        return topics


# ==========================#
# STAGE 4: OUTLINE CLEANING
# ==========================#

def _cleanup_outline(topics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Programmatically deduplicate key points across all topics"""
    seen_points = set()
    cleaned_topics = []
    
    for topic in topics:
        unique_key_points = []
        
        if "key_points" not in topic or not isinstance(topic["key_points"], list):
            logger.warning(f"Topic '{topic.get('title')}' has invalid key_points")
            continue
        
        for point in topic["key_points"]:
            point_normalized = point.strip().lower()
            
            if point_normalized not in seen_points and point_normalized:
                unique_key_points.append(point)
                seen_points.add(point_normalized)
        
        if unique_key_points:
            cleaned_topics.append({
                "title": topic.get("title", "Untitled"),
                "key_points": unique_key_points
            })
        else:
            logger.warning(f"Removing topic '{topic.get('title')}' - no unique key points")
    
    print(f"✅ Cleaned outline: {len(cleaned_topics)} topics with {len(seen_points)} unique points")
    return cleaned_topics


# ==========================#
# STAGE 5: SLIDE GENERATION (MERGED APPROACH)
# ==========================#

def _smart_group_bullets(points: List[str], max_count: int) -> List[str]:
    """
    Smart grouping of bullet points to keep under max_count.
    If there are more than max, intelligently combines related points using | separator.
    This allows multiple facts in a single bullet while staying under max count.
    """
    if len(points) <= max_count:
        return points
    
    # We need to reduce points to max_count
    excess = len(points) - max_count
    grouped = []
    i = 0
    
    while i < len(points):
        current = points[i]
        
        # If we still need to reduce and there's a next point, try combining
        if excess > 0 and i + 1 < len(points):
            next_point = points[i + 1]
            
            # Remove bullet markers for cleaner combining
            current_clean = current.lstrip('• ').strip()
            next_clean = next_point.lstrip('• ').strip()
            
            # Combine with | separator
            combined = f"{current_clean} | {next_clean}"
            
            # Only combine if result isn't too long (under 120 chars for readability)
            if len(combined) <= 120:
                grouped.append(combined)
                i += 2
                excess -= 1
                continue
        
        # Otherwise, add as-is (make sure it has a bullet)
        if current.startswith('•'):
            grouped.append(current)
        else:
            grouped.append(f"• {current}")
        i += 1
    
    return grouped[:max_count]

def _wrap_text(text: str, width: int = 75) -> str:
    """
    Wrap text to specified width, preserving word boundaries.
    For bullet points, keeps them short without wrapping.
    """
    import textwrap
    
    text = text.strip()
    
    # If it's already a short bullet point, don't wrap it
    if text.startswith('•') and len(text) <= 90:
        return text
    
    # If it's a header/bold text, just return cleaned
    if '**' in text:
        return text.replace('**', '').strip()
    
    # For long lines that aren't bullets, wrap them
    if len(text) > 85:
        lines = textwrap.wrap(text, width=width, break_long_words=False, break_on_hyphens=False)
        
        if not lines:
            return text
        
        # Return as properly formatted bullets
        wrapped = [f"• {lines[0]}"]
        wrapped.extend([f"  {line}" for line in lines[1:]])
        return "\n".join(wrapped)
    
    return text

# ==========================#
# STAGE 5: SLIDE GENERATION (MERGED APPROACH)
# ==========================#

async def _generate_slide_from_outline(
    client: Any,
    model_name: str,
    topics_for_slide: List[Dict[str, Any]],
    user_requested_slides: int,
    detail_level: str = "detailed"
) -> str:
    """Generate a professional slide from grouped topics - one topic per slide max"""
    
    # For each topic in the slide group, create a formatted section
    # But we'll only use the FIRST topic per call since each topic should get its own slide
    # If multiple topics exist, the orchestrator should handle splitting them
    
    if not topics_for_slide:
        return "No content available"
    
    # Use the first topic (orchestrator handles one topic per slide)
    topic = topics_for_slide[0]
    slide_title = topic.get("title", "Untitled")
    key_points = topic.get("key_points", [])
    
    # Limit to maximum 8 bullet points per slide (reduced to ensure under limit)
    max_bullets = 8
    if len(key_points) > max_bullets:
        # Smart grouping: combine bullets if needed
        key_points = _smart_group_bullets(key_points, max_bullets)
    
    # Format points with proper formatting - keep bullets short and clean
    formatted_points = []
    for p in key_points:
        if p:
            p = str(p).strip()
            # Add bullet if not already there
            if not p.startswith('•'):
                formatted_points.append(f"• {p}")
            else:
                formatted_points.append(p)
    
    points_str = "\n".join(formatted_points)
    
    # Adjust prompt based on detail level
    detail_instructions = {
        "beginner": "Use simple, clear language. Explain technical terms. Keep content easy to understand.",
        "intermediate": "Use professional language with context. Balance detail with clarity.",
        "professional": "Use technical terminology. Include comprehensive details and examples."
    }
    
    detail_guide = detail_instructions.get(detail_level, detail_instructions["intermediate"])
    
    prompt = f"""
# ROLE: Presentation slide formatter for banking services

# **CRITICAL - MINIMAL HALLUCINATION ALLOWED**:
You MUST use the key points provided below as the foundation.
Do NOT invent or create facts that don't exist in any source material.
However, if the provided bullet points are very few (less than 3), you MAY add 1-2 extra related facts from the document context to make the slide look professionally filled.
These extra points MUST be derived from the document and be directly related to the main topic.

# DETAIL LEVEL: {detail_level.upper()}
{detail_guide}

# CONTEXT
User requested {user_requested_slides} total slides. This is ONE slide with ONE product/service.
Each slide focuses on a single topic with maximum 8 bullet points.
Use the facts provided below, and optionally add 1-2 related document facts if the slide looks too sparse.

# SLIDE CONTENT TO FORMAT
Product/Service Name: "{slide_title}"

Key Points (USE THESE AS PRIMARY):
{points_str}

# YOUR TASK - FORMATTING + OPTIONAL ENRICHMENT
1) First line: Main slide title (exactly: "{slide_title}")
2) Second line: Empty line
3) Third line: Subtitle in BOLD format using **text** (e.g., "**{slide_title}**")
4) Fourth line: Empty line
5) Then: Use the bullet points provided above, formatted with • prefix
6) If you have fewer than 3 bullet points, you MAY add 1-2 extra related facts from the document that fit the topic
7) All points must be factual and document-derived - NO invented facts
8) Do NOT reword the provided points, keep them as-is
9) Just clean up formatting if bullet marker is missing
10) NO narrative text beyond bullets - ONLY formatted facts

# FORMATTING EXAMPLE
{slide_title}

**{slide_title}**

• For ages 15+
• Professional benefits and features
• Special rates available
• Document-derived additional info (if applicable)

Output the formatted slide now. Keep it professional and well-balanced, not sparse.
"""
    
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(
            None, lambda: client.generate(model=model_name, prompt=prompt)
        )
        content = resp["response"].strip()
        
        # Process the content: preserve formatting with bold text
        lines = content.split('\n')
        
        # Clean up and preserve structure
        processed_lines = []
        for line in lines:
            # Keep line as-is, just remove trailing whitespace
            processed_lines.append(line.rstrip())
        
        # Remove leading/trailing empty lines
        while processed_lines and not processed_lines[0].strip():
            processed_lines.pop(0)
        while processed_lines and not processed_lines[-1].strip():
            processed_lines.pop()
        
        # Ensure bold formatting is preserved (**text**)
        final_content = '\n'.join(processed_lines)
        return final_content
    except Exception as e:
        logger.error(f"Error generating slide: {e}")
        return f"{slide_title}\n\n**{slide_title}**\n\n• Error generating content"


# ==========================#
# SMART SLIDE COUNTING & DISTRIBUTION
# ==========================#

def _calculate_optimal_slides(
    num_topics: int,
    requested_slides: int
) -> tuple:
    """
    Calculate optimal slide distribution.
    IMPORTANT: Respects requested slide count - each topic gets its own slide (max).
    """
    # Minimum 3 slides (title + content + conclusion)
    user_requested_slides = max(requested_slides, 3)
    
    # Calculate how many content slides we can have
    num_content_slides = user_requested_slides - 2  # Exclude title and conclusion
    
    if num_topics == 0:
        # No topics: single placeholder slide
        topic_groups = [[]]
        total_slides = 3
    else:
        # Create one group per topic
        topic_groups = [[i] for i in range(num_topics)]
        
        # IMPORTANT: LIMIT topic_groups to requested content slides
        if len(topic_groups) > num_content_slides:
            print(f"⚠️  Limiting {num_topics} topics to {num_content_slides} content slides")
            topic_groups = topic_groups[:num_content_slides]  # Trim to match requested slides
        
        # Total slides = content slides + title + conclusion
        total_slides = len(topic_groups) + 2
    
    return topic_groups, total_slides


# ==========================#
# MAIN ORCHESTRATOR
# ==========================#

async def generate_presentation_content_streaming(
    presentation_id: int,
    *,
    callback=None
) -> Dict[str, Any]:
    """
    Main entry point for presentation generation.
    Combines strong topic extraction with smart document matching.
    """
    print(f"\n{'='*60}")
    print(f"🎯 STARTING PRESENTATION GENERATION (ID: {presentation_id})")
    print(f"{'='*60}")
    
    db_manager = get_database()
    
    # Initialize Unified LLM client
    ollama_client = UnifiedLLMClient(host=os.getenv("OLLAMA_BASE_URL", "http://llm-inference:8080"))
    model_name = os.getenv("PRESENTATION_MODEL_NAME", "gpt-oss-120b")
    
    # Fetch presentation config
    row = await db_manager.fetch_one(
        """MATCH (p:Presentation {id: $id}) 
           RETURN p.id as id, p.title as title, p.scope as scope, p.topic as topic,
                  p.detail_level as detail_level, p.difficulty as difficulty,
                  p.slide_style as slide_style, p.num_slides as num_slides,
                  p.include_diagrams as include_diagrams, p.include_code_examples as include_code_examples,
                  p.status as status, p.output_file_path as output_file_path,
                  p.content as content, p.created_at as created_at""",
        {"id": str(presentation_id)}
    )
    
    if not row:
        logger.error(f"Presentation {presentation_id} not found")
        return {"error": "Presentation not found"}
    
    print(f"\n📋 Presentation Config:")
    print(f"   Title: {row['title']}")
    print(f"   Detail Level: {row.get('detail_level', 'detailed')}")
    print(f"   Requested Slides: {row.get('num_slides', 10)}")
    print(f"   Using Ollama model: {model_name}")
    
    detail_level = row.get('detail_level', 'detailed')
    
    # STEP 1: Find best matching document
    print(f"\n{'='*60}")
    print(f"STEP 1: Finding best matching document")
    print(f"{'='*60}")
    
    best_doc = await _find_best_document_by_embedding(row['title'], db_manager)
    
    if not best_doc:
        logger.error("No documents found in database - cannot generate presentation")
        # Update database to indicate failure
        try:
            async with db_manager.get_connection() as conn:
                await conn.execute(
                    """MATCH (p:Presentation {id: $1})
                       SET p.status = $2, p.content = $3
                       RETURN p""",
                    presentation_id,
                    "failed",
                    "Error: No documents found in database. Please upload a document first.",
                )
        except Exception as e:
            logger.error(f"Failed to update presentation status: {e}")
        return {"error": "No documents found. Please upload a document first."}
    
    print(f"✅ Selected document: {best_doc['title']}")
    
    # STEP 2: Fetch document content
    print(f"\n{'='*60}")
    print(f"STEP 2: Retrieving document content")
    print(f"{'='*60}")
    
    async with db_manager.get_connection() as conn:
        chunks = await conn.fetch(
            """MATCH (d:Document {id: $1})-[:HAS_CHUNK]->(c:Chunk)
               RETURN c.content as content
               ORDER BY c.created_at ASC LIMIT $2""",
            best_doc['id'],
            int(os.getenv("PRESENTATION_MAX_CHUNKS", "30"))
        )
    
    if not chunks:
        logger.error(f"No content chunks found for document {best_doc['id']}")
        return {"error": "No content found in document"}
    
    chunk_texts = [c['content'] for c in chunks]
    full_content = "\n\n".join(chunk_texts)
    print(f"✅ Retrieved {len(chunk_texts)} chunks ({len(full_content)} characters)")
    
    # STEP 3: Advanced topic extraction
    print(f"\n{'='*60}")
    print(f"STEP 3: Advanced topic extraction (5 methods)")
    print(f"{'='*60}")
    
    topics = await _extract_topics_with_multiple_methods(
        ollama_client,
        model_name,
        chunk_texts,
        best_doc['title']
    )
    
    # STEP 4: Generate outline
    print(f"\n{'='*60}")
    print(f"STEP 4: Generating presentation outline")
    print(f"{'='*60}")
    
    outline_topics = await _create_presentation_outline(
        ollama_client,
        model_name,
        full_content,
        best_doc['title'],
        detail_level
    )
    
    if not outline_topics:
        logger.warning("No outline topics generated, using extracted topics as fallback")
        outline_topics = [{"title": t, "key_points": ["Key information available"]} for t in topics]
    
    print(f"✅ Outline generated with {len(outline_topics)} topics")
    
    # STEP 5: Clean outline
    print(f"\n{'='*60}")
    print(f"STEP 5: Cleaning and deduplicating outline")
    print(f"{'='*60}")
    
    cleaned_topics = _cleanup_outline(outline_topics)
    
    # STEP 5b: Expand topics if needed
    print(f"\n{'='*60}")
    print(f"STEP 5b: Expanding topics if necessary")
    print(f"{'='*60}")
    
    requested_slides = row.get('num_slides', 10)
    content_slides_needed = requested_slides - 2  # Exclude title and conclusion
    
    if len(cleaned_topics) < content_slides_needed and len(cleaned_topics) > 0:
        print(f"⚠️  Have {len(cleaned_topics)} topics, need ~{content_slides_needed} slides")
        print(f"🔄 Expanding topics into subtopics...")
        
        expanded_topics = await _expand_topics(
            ollama_client,
            model_name,
            cleaned_topics,
            requested_slides
        )
        
        cleaned_topics = expanded_topics
        print(f"✅ Now have {len(cleaned_topics)} topics")
    elif len(cleaned_topics) < content_slides_needed:
        print(f"⚠️  No topics to expand (empty result). Creating placeholder slide.")
    
    # STEP 6: Calculate optimal slides
    print(f"\n{'='*60}")
    print(f"STEP 6: Calculating optimal slide distribution")
    print(f"{'='*60}")
    
    topic_groups, total_slides = _calculate_optimal_slides(
        len(cleaned_topics),
        requested_slides
    )
    
    print(f"✅ Will create {total_slides} total slides ({len(topic_groups)} content slides + title + conclusion)")
    
    # STEP 7: Generate slides
    print(f"\n{'='*60}")
    print(f"STEP 7: Generating presentation slides")
    print(f"{'='*60}")
    
    slides = []
    
    # Title slide
    slides.append(f"{row['title']}\nProfessional Banking Services Overview")
    if callback:
        await callback(1, slides[-1])
    print(f"   Slide 1/1: Title Slide")
    
    # Content slides
    for i, group_indices in enumerate(topic_groups):
        slide_num = i + 2
        
        if not group_indices:
            slide_content = "Additional Insights\nThis slide provides space for additional examples or expansion on key points.\n• Content can be customized based on audience needs"
        else:
            # Get topics for this slide
            topics_for_slide = [cleaned_topics[idx] for idx in group_indices if idx < len(cleaned_topics)]
            
            slide_content = await _generate_slide_from_outline(
                ollama_client,
                model_name,
                topics_for_slide,
                total_slides,
                detail_level
            )
        
        slides.append(slide_content)
        if callback:
            await callback(slide_num, slide_content)
        print(f"   Slide {slide_num}/{total_slides}: Content Slide")
    
    # Conclusion slide
    conclusion_points = [t["title"] for t in cleaned_topics if t.get("title")]
    conclusion_parts = [
        "Conclusion",
        "Key Topics Covered:",
    ]
    
    # Format conclusion points with wrapping
    for p in conclusion_points[:8]:  # Limit to 8 points
        if len(p) > 75:
            wrapped = _wrap_text(f"• {p}", width=70)
            conclusion_parts.append(wrapped)
        else:
            conclusion_parts.append(f"• {p}")
    
    slides.append("\n".join(conclusion_parts))
    if callback:
        await callback(total_slides, slides[-1])
    print(f"   Slide {total_slides}/{total_slides}: Conclusion Slide")
    
    # STEP 8: Finalize and save
    print(f"\n{'='*60}")
    print(f"STEP 8: Saving presentation")
    print(f"{'='*60}")
    
    content_str = "\n\n---SLIDE_SEPARATOR---\n\n".join(slides)
    public_url = None
    
    # Save to file
    base_dir = os.path.abspath(os.path.dirname(__file__))
    output_dir = os.path.join(base_dir, "saved_presentations")
    os.makedirs(output_dir, exist_ok=True)
    
    file_name = f'{row["title"].replace(" ", "_")}_{datetime.now().strftime("%Y%m%d%H%M%S")}.txt'
    local_path = os.path.join(output_dir, file_name)
    
    readable_content = content_str.replace("\n\n---SLIDE_SEPARATOR---\n\n", "\n\n---\n\n")
    
    try:
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(readable_content)
        print(f"✅ Presentation saved to: {local_path}")
        
        public_base = os.getenv("PRESENTATION_PUBLIC_BASE", "http://localhost:8003")
        public_url = f"{public_base}/saved_presentations/{file_name}"
    except (IOError, OSError) as e:
        logger.error(f"Failed to save presentation file: {e}")
        public_url = None
    
    # Update database and create relationships
    try:
        async with db_manager.get_connection() as conn:
            # 1️⃣ Update presentation status
            await conn.execute(
                """MATCH (p:Presentation {id: $1})
                   SET p.status = $2, p.output_file_path = $3, p.content = $4
                   RETURN p""",
                presentation_id,
                "completed",
                public_url,
                content_str,
            )
            
            # 2️⃣ Create GENERATED_FROM relationship with Document
            await conn.execute(
                """MATCH (p:Presentation {id: $1}), (d:Document {id: $2})
                   MERGE (p)-[:GENERATED_FROM]->(d)""",
                presentation_id,
                best_doc['id']
            )
            
            # 3️⃣ Detect and create relationship with ServiceCategory
            # Determine category based on document title
            doc_title_lower = best_doc['title'].lower()
            category_id = 9  # Default: General Information
            
            if 'loan' in doc_title_lower:
                category_id = 2  # Loans
            elif 'card' in doc_title_lower or 'debit' in doc_title_lower or 'credit' in doc_title_lower:
                category_id = 3  # Cards
            elif 'account' in doc_title_lower or 'saving' in doc_title_lower or 'deposit' in doc_title_lower:
                category_id = 1  # Accounts & Savings
            elif 'invest' in doc_title_lower or 'fund' in doc_title_lower:
                category_id = 4  # Investments
            elif 'business' in doc_title_lower or 'corporate' in doc_title_lower:
                category_id = 5  # Business & Corporate Banking
            elif 'insur' in doc_title_lower:
                category_id = 6  # Insurance
            elif 'digital' in doc_title_lower or 'mobile' in doc_title_lower or 'online' in doc_title_lower:
                category_id = 7  # Digital & E-Banking
            elif 'payroll' in doc_title_lower or 'salary' in doc_title_lower:
                category_id = 8  # Payroll Services
            
            await conn.execute(
                """MATCH (p:Presentation {id: $1}), (sc:ServiceCategory {id: $2})
                   MERGE (p)-[:BELONGS_TO_CATEGORY]->(sc)""",
                presentation_id,
                category_id
            )
        
        print(f"✅ Database updated")
        print(f"✅ Created GENERATED_FROM relationship with Document: {best_doc['id']}")
        print(f"✅ Created BELONGS_TO_CATEGORY relationship with ServiceCategory: {category_id}")
    except Exception as e:
        logger.error(f"Database update failed: {e}")
    
    print(f"\n{'='*60}")
    print(f"✅ PRESENTATION GENERATION COMPLETE")
    print(f"{'='*60}\n")
    
    return {
        "id": presentation_id,
        "status": "completed",
        "output_file_path": public_url,
        "content": content_str,
        "total_slides": total_slides,
        "document_id": best_doc['id'],
        "document_title": best_doc['title'],
    }


async def generate_presentation_content(
    presentation_id: int,
    *,
    return_content: bool = False
) -> Dict[str, Any]:
    """Wrapper for non-streaming generation"""
    return await generate_presentation_content_streaming(presentation_id, callback=None)
