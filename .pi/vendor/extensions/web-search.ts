import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

const schema = Type.Object({
  query: Type.String({ description: "The web search query" }),
});

type SearchResult = { title: string; url: string; snippet: string; published?: string };

function decodeXml(value: string): string {
  return value.replace(/&(#x[\da-f]+|#\d+|amp|lt|gt|quot|apos);/gi, (entity, code: string) => {
    if (code[0] === "#") {
      const hex = code[1]?.toLowerCase() === "x";
      const point = Number.parseInt(code.slice(hex ? 2 : 1), hex ? 16 : 10);
      try { return String.fromCodePoint(point); } catch { return entity; }
    }
    return ({ amp: "&", lt: "<", gt: ">", quot: '"', apos: "'" } as Record<string, string>)[code.toLowerCase()] ?? entity;
  });
}

function tagText(xml: string, tag: string): string {
  const match = xml.match(new RegExp(`<${tag}(?:\\s[^>]*)?>([\\s\\S]*?)<\\/${tag}>`, "i"));
  if (!match) return "";
  const raw = match[1].replace(/^\s*<!\[CDATA\[([\s\S]*?)\]\]>\s*$/, "$1");
  return decodeXml(raw.replace(/<[^>]*>/g, " ")).replace(/\s+/g, " ").trim();
}

function parseRss(xml: string): SearchResult[] {
  const results: SearchResult[] = [];
  for (const match of xml.matchAll(/<item\b[^>]*>([\s\S]*?)<\/item>/gi)) {
    const item = match[1];
    const title = tagText(item, "title");
    const url = tagText(item, "link");
    const snippet = tagText(item, "description");
    const published = tagText(item, "pubDate");
    try {
      const parsed = new URL(url);
      if (!/^https?:$/.test(parsed.protocol) || !title) continue;
      results.push({ title, url: parsed.href, snippet, ...(published ? { published } : {}) });
    } catch { /* Ignore malformed feed entries. */ }
  }
  return results;
}

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "web_search",
    label: "Web Search",
    description: "Search the public web and return real Bing search results with source URLs and snippets.",
    promptSnippet: "Search the web for current information; cite the returned source URLs.",
    promptGuidelines: [
      "Use web_search for questions requiring current information or external sources.",
      "Base claims on its returned search results and cite their URLs; say when the results do not support an answer.",
    ],
    parameters: schema,
    async execute(_toolCallId, params, signal) {
      const url = new URL("https://www.bing.com/search");
      url.searchParams.set("format", "rss");
      url.searchParams.set("q", params.query);
      const response = await fetch(url, {
        headers: { "User-Agent": "Mozilla/5.0 (compatible; PiWebSearch/1.0)" },
        signal,
      });
      if (!response.ok) throw new Error(`Bing search failed: HTTP ${response.status}`);
      const results = parseRss(await response.text());
      if (results.length === 0) throw new Error("Bing returned no parseable search results; no answer is being presented as searched.");
      const text = results.map((result, index) => {
        const date = result.published ? `\n   Bing feed timestamp: ${result.published}` : "";
        return `${index + 1}. ${result.title}\n   ${result.url}${result.snippet ? `\n   ${result.snippet}` : ""}${date}`;
      }).join("\n\n");
      return {
        content: [{ type: "text", text: `Bing web results for: ${params.query}\n\n${text}` }],
        details: { provider: "Bing RSS", query: params.query, resultCount: results.length, sources: results },
      };
    },
  });
}
