package htomd

import (
	"encoding/json"
	"io"
	"strings"
)

var articleTypes = set("Article NewsArticle BlogPosting TechArticle ScholarlyArticle MedicalScholarlyArticle Report AnalysisNewsArticle OpinionNewsArticle ReviewNewsArticle BackgroundNewsArticle APIReference LiveBlogPosting")

func optional(s string) *string {
	s = strings.TrimSpace(s)
	if s == "" {
		return nil
	}
	return &s
}
func first(values ...*string) *string {
	for _, v := range values {
		if v != nil && *v != "" {
			return v
		}
	}
	return nil
}
func jsonString(v any) *string {
	s, ok := v.(string)
	if !ok {
		return nil
	}
	return optional(s)
}
func authorName(v any) *string {
	switch a := v.(type) {
	case string:
		return optional(a)
	case map[string]any:
		return jsonString(a["name"])
	case []any:
		names := []string{}
		for _, entry := range a {
			if n := authorName(entry); n != nil {
				names = append(names, *n)
			}
		}
		return optional(strings.Join(names, ", "))
	}
	return nil
}
func jsonArticle(n *node) map[string]any {
	if strings.ToLower(n.attrs["type"]) != "application/ld+json" {
		return nil
	}
	var value any
	decoder := json.NewDecoder(strings.NewReader(textContent(n, false)))
	decoder.UseNumber()
	if decoder.Decode(&value) != nil {
		return nil
	}
	var trailing any
	if decoder.Decode(&trailing) != io.EOF {
		return nil
	}
	stack := []any{value}
	for len(stack) > 0 {
		item := stack[len(stack)-1]
		stack = stack[:len(stack)-1]
		switch v := item.(type) {
		case []any:
			for i := len(v) - 1; i >= 0; i-- {
				stack = append(stack, v[i])
			}
		case map[string]any:
			kinds, ok := v["@type"].([]any)
			if !ok {
				kinds = []any{v["@type"]}
			}
			for _, kind := range kinds {
				if s, ok := kind.(string); ok {
					parts := strings.Split(s, "/")
					if articleTypes[parts[len(parts)-1]] {
						return v
					}
				}
			}
			switch graph := v["@graph"].(type) {
			case []any:
				stack = append(stack, graph)
			case map[string]any:
				stack = append(stack, graph)
			}
		}
	}
	return nil
}
func readMetadata(root *node, source, base *string) Metadata {
	fields := map[string]*string{}
	var article map[string]any
	var title, language, canonical *string
	for _, n := range walk(root) {
		switch n.tag {
		case "meta":
			key, ok := n.attrs["property"]
			if !ok {
				key = n.attrs["name"]
			}
			key = strings.ToLower(key)
			if content := optional(n.attrs["content"]); content != nil && fields[key] == nil {
				fields[key] = content
			}
		case "title":
			if title == nil {
				title = optional(textContent(n, true))
			}
		case "html":
			language = first(optional(n.attrs["lang"]), optional(n.attrs["xml:lang"]))
		case "link":
			if set(strings.ToLower(n.attrs["rel"]))["canonical"] {
				canonical = first(canonical, safeURL(n.attrs["href"], base))
			}
		case "script":
			if len(article) == 0 {
				article = jsonArticle(n)
			}
		}
	}
	var sourceCopy *string
	if source != nil {
		s := *source
		sourceCopy = &s
	}
	return Metadata{first(fields["og:title"], title, jsonString(article["headline"])), first(fields["author"], authorName(article["author"])), first(fields["description"], fields["og:description"], jsonString(article["description"])), first(language, jsonString(article["inLanguage"]), fields["og:locale"]), first(fields["article:published_time"], fields["date"], jsonString(article["datePublished"])), sourceCopy, canonical}
}
func refineMetadata(m *Metadata, selected []*node) {
	var heading *string
	author, published := m.Author, m.PublishedTime
	for _, root := range selected {
		for _, n := range walk(root) {
			if n.tag == "h1" && heading == nil {
				heading = optional(textContent(n, true))
			}
			tokens := set(strings.ToLower(n.attrs["class"]))
			if author == nil && (n.attrs["itemprop"] == "author" || set(n.attrs["rel"])["author"] || tokens["byline"] || tokens["author"] || tokens["p-author"]) {
				author = optional(textContent(n, true))
			}
			if published == nil && n.tag == "time" && n.attrs["itemprop"] != "dateModified" {
				published = first(optional(n.attrs["datetime"]), optional(textContent(n, true)))
			}
		}
	}
	m.Title = first(heading, m.Title)
	m.Author = first(m.Author, author)
	m.PublishedTime = first(m.PublishedTime, published)
}
