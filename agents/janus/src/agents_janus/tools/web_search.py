"""Web search tool using direct HTTP (no subprocess)."""
import json
import os
import urllib.request
import urllib.parse


def web_search(query: str, num_results: int = 5) -> str:
    """Search the web for information.

    Uses OpenRouter API directly to get search-augmented responses.
    Falls back to a simple message if no API key is available.

    Args:
        query: The search query.
        num_results: Maximum number of results to return.

    Returns:
        Structured search results as a string.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return json.dumps({
            "status": "no_api_key",
            "query": query,
            "message": "OPENROUTER_API_KEY not set. Cannot search.",
        })

    # Use OpenRouter with a web-search-capable model
    try:
        payload = json.dumps({
            "model": "perplexity/sonar",
            "messages": [
                {
                    "role": "user",
                    "content": f"Search for: {query}. Return up to {num_results} findings with sources. Be concise.",
                }
            ],
            "max_tokens": 1000,
        }).encode()

        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            content = data["choices"][0]["message"]["content"]
            return json.dumps({
                "status": "ok",
                "query": query,
                "results": content,
            })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "query": query,
            "message": str(e),
        })
