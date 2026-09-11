package htomd

import (
	"html"
	"regexp"
	"strings"
	"unicode"
)

func isSpace(c rune) bool { return unicode.IsSpace(c) }

var voidTags = set("area base br col embed hr img input link meta param source track wbr")
var rawTags = set("script style xmp iframe noembed noframes")
var rcdataTags = set("title textarea")
var pBreakers = set("address article aside blockquote div dl fieldset footer form h1 h2 h3 h4 h5 h6 header hr main nav ol p pre section table ul")
var implied = map[string][2]string{
	"li": {"li", "ul ol"}, "dt": {"dt dd", "dl"}, "dd": {"dt dd", "dl"}, "tr": {"tr", "table tbody thead tfoot"},
	"td": {"td th", "tr table"}, "th": {"td th", "tr table"}, "thead": {"thead tbody tfoot", "table"}, "tbody": {"thead tbody tfoot", "table"}, "tfoot": {"thead tbody tfoot", "table"}, "option": {"option", "select datalist"},
}
var endScopes = map[string]string{"li": "ul ol", "td": "tr table", "th": "tr table", "tr": "table"}
var tagName = regexp.MustCompile(`(?i)^<([a-z][^\t\n\r\f />\x00]*)`)
var endName = regexp.MustCompile(`(?i)^</\s*([a-z][^\s/>]*)`)
var attrName = regexp.MustCompile(`^([^\t\n\r\f />=]+)(?:[\t\n\r\f ]*=+[\t\n\r\f ]*(?:"([^"]*)"|'([^']*)'|([^\t\n\r\f >]*)))?`)
var commentEnd = regexp.MustCompile(`^(?:<!-->|<!--->)|--\s*>|--!>`)
var declarationName = regexp.MustCompile(`(?i)^<!\[([a-z]+)\b`)
var declarationEnd = regexp.MustCompile(`]\s*]\s*>|]\s*>`)

func parse(input string) (*node, []string) {
	root := &node{tag: "#document", attrs: map[string]string{}}
	stack := []*node{root}
	recoveries := 0
	closeScope := func(targets, boundaries string) {
		t, b := set(targets), set(boundaries)
		for i := len(stack) - 1; i > 0; i-- {
			tag := stack[i].tag
			if t[tag] {
				stack = stack[:i]
				recoveries++
				return
			}
			if b[tag] {
				return
			}
		}
	}
	end := func(tag string) {
		if voidTags[tag] {
			return
		}
		boundaries := set(endScopes[tag])
		for i := len(stack) - 1; i > 0; i-- {
			if stack[i].tag == tag {
				stack = stack[:i]
				return
			}
			if boundaries[stack[i].tag] {
				break
			}
		}
		recoveries++
	}
	data := func(s string, raw bool) {
		if s == "" {
			return
		}
		if !raw {
			s = html.UnescapeString(s)
		}
		parent := stack[len(stack)-1]
		parent.children = append(parent.children, &node{text: s, parent: parent})
	}
	for pos := 0; pos < len(input); {
		parent := stack[len(stack)-1]
		rest := input[pos:]
		if parent.tag == "plaintext" {
			data(rest, true)
			break
		}
		if rawTags[parent.tag] || rcdataTags[parent.tag] {
			closeRE := regexp.MustCompile(`(?i)</` + parent.tag + `[\t\n\r\f ]*>`)
			loc := closeRE.FindStringIndex(rest)
			if loc == nil {
				data(rest, rawTags[parent.tag])
				break
			}
			data(rest[:loc[0]], rawTags[parent.tag])
			end(parent.tag)
			pos += loc[1]
			continue
		}
		if rest[0] != '<' {
			next := strings.IndexByte(rest, '<')
			if next < 0 {
				next = len(rest)
			}
			data(rest[:next], false)
			pos += next
			continue
		}
		if strings.HasPrefix(rest, "<!--") {
			loc := commentEnd.FindStringIndex(rest)
			if loc == nil {
				break
			}
			pos += loc[1]
			continue
		}
		if strings.HasPrefix(rest, "<![") {
			name := declarationName.FindStringSubmatch(rest)
			if name == nil || !set("temp cdata ignore include rcdata if else endif")[strings.ToLower(name[1])] {
				recoveries++
				break
			}
			loc := declarationEnd.FindStringIndex(rest)
			if loc == nil {
				break
			}
			recoveries++
			pos += loc[1]
			continue
		}
		if strings.HasPrefix(rest, "<!") || strings.HasPrefix(rest, "<?") {
			next := strings.IndexByte(rest, '>')
			if next < 0 {
				break
			}
			pos += next + 1
			continue
		}
		if strings.HasPrefix(rest, "</") {
			next := strings.IndexByte(rest, '>')
			if next < 0 {
				break
			}
			name := endName.FindStringSubmatch(rest)
			if name != nil {
				end(strings.ToLower(name[1]))
			}
			pos += next + 1
			continue
		}
		name := tagName.FindStringSubmatch(rest)
		if name == nil {
			data("<", false)
			pos++
			continue
		}
		cursor := len(name[0])
		attrs := map[string]string{}
		complete, selfClosing := false, false
		for cursor < len(rest) {
			for cursor < len(rest) && strings.ContainsRune("\t\n\r\f /", rune(rest[cursor])) {
				cursor++
			}
			if cursor < len(rest) && rest[cursor] == '>' {
				selfClosing = rest[cursor-1] == '/'
				cursor++
				complete = true
				break
			}
			attr := attrName.FindStringSubmatch(rest[cursor:])
			if attr == nil || strings.HasPrefix(attr[4], "\"") || strings.HasPrefix(attr[4], "'") {
				break
			}
			value := attr[2]
			if value == "" {
				value = attr[3]
			}
			if value == "" {
				value = attr[4]
			}
			attrs[strings.ToLower(attr[1])] = html.UnescapeString(value)
			cursor += len(attr[0])
		}
		if !complete {
			break
		}
		tag := strings.ToLower(name[1])
		if pBreakers[tag] {
			closeScope("p", "table td th li")
		}
		if rule, ok := implied[tag]; ok {
			closeScope(rule[0], rule[1])
		}
		if tag == "a" {
			closeScope("a", "p div li")
		}
		parent = stack[len(stack)-1]
		n := &node{tag: tag, attrs: attrs, parent: parent}
		parent.children = append(parent.children, n)
		if !voidTags[tag] {
			stack = append(stack, n)
			if selfClosing {
				end(tag)
			}
		}
		pos += cursor
	}
	notes := []string{}
	if recoveries > 0 {
		notes = append(notes, "Recovered malformed or optionally closed HTML.")
	}
	return root, notes
}
