# Unified Retrieval and Generation System

## Overview

This implementation fixes the retrieval→generation wiring issues by creating a unified system that:

1. **Creates a shared ResponseContext** with proper chunk formatting
2. **Enforces dependency ordering** (retrieve → generate in parallel)
3. **Uses grounded prompt templates** to prevent hallucination
4. **Unifies Quick Summary & Long Answer inputs** using the same context

## Key Components

### 1. ResponseContext (`src/core/response_context.py`)
- **Chunk**: Represents a text chunk with ID, title, PMID/DOI, section, text, and score
- **ResponseContext**: Shared context for a single request with request_id, query, selected_chunks
- **ResponseContextManager**: Manages contexts for concurrent requests with cleanup

### 2. RetrievalService (`src/core/retrieval_service.py`)
- Handles retrieval from the search API
- Formats raw results into standardized Chunk objects
- Creates ResponseContext with selected_chunks (max 12)
- Returns context with request_id for subsequent generation calls

### 3. GenerationService (`src/core/generation_service.py`)
- **Grounded system prompt**: "Use ONLY the provided passages. If a claim is not directly supported, respond with 'Unknown based on provided sources.'"
- **Citation format**: Every factual sentence must be cited with [ID]
- **InsufficientEvidenceError**: Thrown when no chunks are available
- **Template responses**: For cases with insufficient evidence

### 4. UnifiedController (`src/core/unified_controller.py`)
- **Dependency ordering**: `await retrieve()` → parallel generation
- **Error handling**: Catches InsufficientEvidenceError and returns templates
- **Response formatting**: Formats results for UI consumption

### 5. Unified Routes (`src/routes/unified_routes.py`)
- `/api/unified-search`: Main endpoint that handles retrieval + generation
- `/api/quick-summary`: Generate summary using existing context
- `/api/detailed-answer`: Generate answer using existing context

## Key Features

### ✅ Shared ResponseContext
- After retrieval + reranking, builds `selected_chunks: Array<{id, title, pmidOrDoi, section, text}>` (12 max)
- Stores context transiently by requestId (UUID) for concurrent calls
- Same exact set of chunks used for both summary and answer generation

### ✅ Dependency Ordering
- Controller: `await retrieve()` → returns `{ requestId, selected_chunks }`
- In parallel: `generateQuickSummary({ requestId, selected_chunks, query })` and `generateLongAnswer({ requestId, selected_chunks, query })`
- Rejects generation calls without non-empty selected_chunks array

### ✅ Grounded Prompt Templates
- **System**: "You are a scientific assistant. Use ONLY the provided passages. If a claim is not directly supported, respond with 'Unknown based on provided sources.' Cite every factual sentence with [ID] from the provided citations array. Do not invent citations."
- **Citations format**: `[1] Title (PMID: 12345) - abstract\nText content...`
- **Response validation**: Every claim must be supported by provided sources

### ✅ Error Handling
- **InsufficientEvidenceError**: Thrown when no chunks available
- **Template responses**: "Based on the available sources, there is insufficient evidence..."
- **Graceful degradation**: System continues to work even with retrieval failures

## Usage

### Frontend Integration
The frontend now uses `/api/unified-search` which returns:
```json
{
  "success": true,
  "request_id": "uuid",
  "query": "user query",
  "summary": "3-5 sentence summary",
  "answer": "detailed answer with citations",
  "citations": [...],
  "retrieval_latency_ms": 150,
  "summary_latency_ms": 800,
  "answer_latency_ms": 1200,
  "total_chunks": 8,
  "chunks_used_summary": 8,
  "chunks_used_answer": 8
}
```

### Testing
Run the test script to verify the system:
```bash
python test_unified_system.py
```

## Benefits

1. **No more irrelevant content**: LLM can only use provided passages
2. **Consistent citations**: Both summary and answer use the same sources
3. **Proper dependency ordering**: Retrieval happens before generation
4. **Concurrent generation**: Summary and answer generated in parallel
5. **Error resilience**: Graceful handling of insufficient evidence
6. **Performance tracking**: Detailed latency measurements
7. **Memory management**: Automatic cleanup of old contexts

## Migration

The old `/explain-research` endpoint is still available for backward compatibility, but the new system uses `/api/unified-search` which provides better grounding and consistency.
