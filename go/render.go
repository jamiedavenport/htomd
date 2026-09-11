package htomd

import (
	"fmt"
	"math/big"
	"regexp"
	"strings"
	"unicode"
	"unicode/utf8"
)

var emphasis = map[string]string{"em": "*", "i": "*", "strong": "**", "b": "**", "s": "~~", "del": "~~", "strike": "~~"}
var literalTags = set("pre code kbd samp")
var blocks = set("p div article main section header footer figure figcaption address details summary dl")
var blockNeighbors = set("p div article main section header footer figure figcaption address details summary dl h1 h2 h3 h4 h5 h6 ul ol pre table blockquote hr li")
var blockMarker = regexp.MustCompile(`^(#{1,6}|[-+]|[0-9]+[.)]|[=~-]{3,})([\t\n\r\f ]|$)`)
var listStart = regexp.MustCompile(`^[+-]?[0-9]+$`)
var listValue = regexp.MustCompile(`^-?[0-9]{1,9}$`)

func escape(value string) string {
	value = strings.NewReplacer("&", "&amp;", "<", "&lt;", ">", "&gt;", "\\", "\\\\", "`", "\\`", "*", "\\*", "_", "\\_", "~", "\\~", "[", "\\[", "]", "\\]").Replace(value)
	lines := strings.Split(value, "\n")
	for i, line := range lines {
		trimmed := strings.TrimLeftFunc(line, isSpace)
		m := blockMarker.FindStringSubmatch(trimmed)
		if m == nil {
			continue
		}
		marker := m[1]
		if m[2] == "" && !(len(marker) >= 3 && strings.ContainsAny(marker, "=~-") && strings.Trim(marker, string(marker[0])) == "") {
			continue
		}
		escaped := "\\" + marker
		if marker[0] >= '0' && marker[0] <= '9' {
			escaped = marker[:len(marker)-1] + "\\" + marker[len(marker)-1:]
		}
		lines[i] = line[:len(line)-len(trimmed)] + escaped + trimmed[len(marker):]
	}
	return strings.Join(lines, "\n")
}
func longestRun(s string, ch rune) int {
	longest, current := 0, 0
	for _, c := range s {
		if c == ch {
			current++
			longest = max(longest, current)
		} else {
			current = 0
		}
	}
	return longest
}
func inlineCode(n *node) string {
	value := strings.NewReplacer("\r\n", " ", "\r", " ", "\n", " ").Replace(textContent(n, false))
	if value == "" {
		return ""
	}
	delimiter := strings.Repeat("`", longestRun(value, '`')+1)
	padding := ""
	if strings.HasPrefix(value, "`") || strings.HasSuffix(value, "`") || strings.HasPrefix(value, " ") && strings.HasSuffix(value, " ") && strings.TrimSpace(value) != "" {
		padding = " "
	}
	return delimiter + padding + value + padding + delimiter
}
func validLanguage(s string) bool {
	if s == "" {
		return false
	}
	for _, c := range s {
		if !unicode.IsLetter(c) && !unicode.IsNumber(c) && !strings.ContainsRune("_.+#-", c) {
			return false
		}
	}
	return true
}
func codeLanguage(n *node) string {
	candidates := append([]*node{n}, elements(n)...)
	if n.parent != nil {
		candidates = append(candidates, n.parent)
	}
	for _, c := range candidates {
		for _, token := range strings.Fields(c.attrs["class"]) {
			if strings.HasPrefix(token, "language-") || strings.HasPrefix(token, "lang-") || strings.HasPrefix(token, "highlight-") {
				value := strings.SplitN(token, "-", 2)[1]
				if validLanguage(value) {
					return value
				}
			}
		}
		if value := c.attrs["data-language"]; validLanguage(value) {
			return value
		}
	}
	return ""
}
func fencedCode(n *node) string {
	value := strings.NewReplacer("\r\n", "\n", "\r", "\n").Replace(textContent(n, false))
	fence := strings.Repeat("`", max(3, longestRun(value, '`')+1))
	ending := ""
	if !strings.HasSuffix(value, "\n") {
		ending = "\n"
	}
	return "\n\n" + fence + codeLanguage(n) + "\n" + value + ending + fence + "\n\n"
}
func joinParts(parts []string) string {
	result := []string{}
	for _, part := range parts {
		if part == "" {
			continue
		}
		if len(result) > 0 && strings.HasSuffix(result[len(result)-1], "\n") && strings.HasPrefix(part, "\n") {
			result[len(result)-1] = strings.TrimRight(result[len(result)-1], "\n")
			part = "\n\n" + strings.TrimLeft(part, "\n")
		}
		result = append(result, part)
	}
	return strings.Join(result, "")
}
func wrapInline(body, marker string) string {
	content := strings.TrimSpace(body)
	if content == "" {
		return body
	}
	leading, trailing := "", ""
	first, _ := utf8.DecodeRuneInString(body)
	last, _ := utf8.DecodeLastRuneInString(body)
	if isSpace(first) {
		leading = " "
	}
	if isSpace(last) {
		trailing = " "
	}
	return leading + marker + content + marker + trailing
}
func renderList(n *node, rendered map[*node]string) string {
	number := big.NewInt(1)
	start := strings.TrimSpace(n.attrs["start"])
	if listStart.MatchString(start) {
		number.SetString(start, 10)
	}
	items := []string{}
	for _, child := range elements(n) {
		if child.tag != "li" {
			continue
		}
		if n.tag == "ol" && listValue.MatchString(child.attrs["value"]) {
			number.SetString(child.attrs["value"], 10)
		}
		marker := "- "
		if n.tag == "ol" {
			marker = number.String() + ". "
		}
		body := strings.TrimSpace(rendered[child])
		if body != "" {
			lines := strings.Split(body, "\n")
			for i := 1; i < len(lines); i++ {
				if lines[i] != "" {
					lines[i] = strings.Repeat(" ", len(marker)) + lines[i]
				}
			}
			lines[0] = marker + lines[0]
			items = append(items, strings.Join(lines, "\n"))
		}
		number.Add(number, big.NewInt(1))
	}
	if len(items) == 0 {
		return ""
	}
	return "\n" + strings.Join(items, "\n") + "\n"
}
func tableRows(n *node) []*node {
	rows := []*node{}
	children := elements(n)
	stack := []*node{}
	for i := len(children) - 1; i >= 0; i-- {
		stack = append(stack, children[i])
	}
	for len(stack) > 0 {
		c := stack[len(stack)-1]
		stack = stack[:len(stack)-1]
		if c.tag == "tr" {
			rows = append(rows, c)
		} else if c.tag == "thead" || c.tag == "tbody" || c.tag == "tfoot" {
			children = elements(c)
			for i := len(children) - 1; i >= 0; i-- {
				stack = append(stack, children[i])
			}
		}
	}
	return rows
}
func renderTable(n *node, rendered map[*node]string) string {
	rows := [][]*node{}
	for _, row := range tableRows(n) {
		cells := []*node{}
		for _, c := range elements(row) {
			if c.tag == "th" || c.tag == "td" {
				cells = append(cells, c)
			}
		}
		rows = append(rows, cells)
	}
	captions := []string{}
	for _, c := range elements(n) {
		if c.tag == "caption" {
			captions = append(captions, strings.TrimSpace(rendered[c]))
		}
	}
	simple := len(rows) > 0 && len(rows[0]) > 0
	for _, row := range rows {
		if len(row) != len(rows[0]) {
			simple = false
		}
		for _, c := range row {
			for _, a := range []string{"colspan", "rowspan"} {
				if value, ok := c.attrs[a]; ok && value != "1" {
					simple = false
				}
			}
			for _, child := range elements(c) {
				if set("table pre ul ol p")[child.tag] {
					simple = false
				}
			}
		}
	}
	lines := []string{}
	if !simple {
		for i, row := range rows {
			values := []string{}
			for _, c := range row {
				values = append(values, strings.ReplaceAll(strings.TrimSpace(rendered[c]), "\n", " "))
			}
			lines = append(lines, fmt.Sprintf("%d. %s", i+1, strings.Join(values, " — ")))
		}
	} else {
		values := [][]string{}
		header := false
		for _, c := range rows[0] {
			header = header || c.tag == "th"
		}
		if !header {
			values = append(values, make([]string, len(rows[0])))
		}
		for _, row := range rows {
			cells := []string{}
			for _, c := range row {
				cells = append(cells, strings.NewReplacer("|", "\\|", "\n", " ").Replace(strings.TrimSpace(rendered[c])))
			}
			values = append(values, cells)
		}
		separator := make([]string, len(rows[0]))
		for i := range separator {
			separator[i] = "---"
		}
		values = append(values[:1], append([][]string{separator}, values[1:]...)...)
		for _, row := range values {
			lines = append(lines, "| "+strings.Join(row, " | ")+" |")
		}
	}
	return "\n\n" + strings.Join(append(captions, strings.Join(lines, "\n")), "\n\n") + "\n\n"
}
func serialize(n *node, body string, rendered map[*node]string, base *string) string {
	tag := n.tag
	trimmed := strings.TrimSpace(body)
	if headings[tag] {
		if trimmed == "" {
			return ""
		}
		return "\n\n" + strings.Repeat("#", int(tag[1]-'0')) + " " + trimmed + "\n\n"
	}
	if marker, ok := emphasis[tag]; ok {
		return wrapInline(body, marker)
	}
	switch tag {
	case "code", "kbd", "samp":
		return inlineCode(n)
	case "pre":
		return fencedCode(n)
	case "a":
		href := safeURL(n.attrs["href"], base)
		if href == nil || *href == "" || trimmed == "" {
			return body
		}
		return "[" + trimmed + "](" + destination(*href) + ")"
	case "img":
		alt := escape(strings.TrimSpace(normalize(n.attrs["alt"])))
		source := safeURL(n.attrs["src"], base)
		if source == nil || *source == "" || n.attrs["src"] == "" {
			return alt
		}
		return "![" + alt + "](" + destination(*source) + ")"
	case "ul", "ol":
		return renderList(n, rendered)
	case "table":
		return renderTable(n, rendered)
	case "blockquote":
		lines := []string{}
		if trimmed != "" {
			for _, line := range strings.Split(trimmed, "\n") {
				if line == "" {
					lines = append(lines, ">")
				} else {
					lines = append(lines, "> "+line)
				}
			}
		}
		return "\n\n" + strings.Join(lines, "\n") + "\n\n"
	case "br":
		return "  \n"
	case "hr":
		return "\n\n---\n\n"
	case "dt":
		return "\n\n" + wrapInline(trimmed, "**") + "\n"
	case "dd":
		return "\n" + trimmed + "\n\n"
	}
	if blocks[tag] {
		if trimmed == "" {
			return ""
		}
		return "\n\n" + trimmed + "\n\n"
	}
	return body
}
func render(selected []*node, base *string) string {
	output := []string{}
	for _, root := range selected {
		// Visit each node once; literal serializers read their original descendants.
		order := []*node{}
		stack := []*node{root}
		for len(stack) > 0 {
			n := stack[len(stack)-1]
			stack = stack[:len(stack)-1]
			order = append(order, n)
			if !literalTags[n.tag] {
				stack = append(stack, elements(n)...)
			}
		}
		rendered := map[*node]string{}
		for i := len(order) - 1; i >= 0; i-- {
			n := order[i]
			parts := []string{}
			if !literalTags[n.tag] {
				for j, c := range n.children {
					if c.tag != "" {
						parts = append(parts, rendered[c])
						continue
					}
					if strings.TrimSpace(c.text) == "" && c.text != "" {
						if j > 0 && blockNeighbors[n.children[j-1].tag] || j+1 < len(n.children) && blockNeighbors[n.children[j+1].tag] {
							continue
						}
					}
					parts = append(parts, escape(normalize(c.text)))
				}
			}
			rendered[n] = serialize(n, joinParts(parts), rendered, base)
		}
		output = append(output, rendered[root])
	}
	result := strings.TrimSpace(joinParts(output))
	if result != "" {
		result += "\n"
	}
	return result
}
