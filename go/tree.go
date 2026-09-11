package htomd

import "strings"

type node struct {
	tag      string
	attrs    map[string]string
	children []*node
	parent   *node
	text     string
}

func set(words string) map[string]bool {
	m := map[string]bool{}
	for _, w := range strings.Fields(words) {
		m[w] = true
	}
	return m
}
func normalize(s string) string {
	// Fields would discard boundary whitespace, which inline rendering needs.
	var b strings.Builder
	space := false
	for _, c := range s {
		if isSpace(c) {
			if !space {
				b.WriteByte(' ')
			}
			space = true
		} else {
			b.WriteRune(c)
			space = false
		}
	}
	return b.String()
}
func walk(root *node) []*node {
	result := []*node{}
	stack := []*node{root}
	for len(stack) > 0 {
		n := stack[len(stack)-1]
		stack = stack[:len(stack)-1]
		if n.tag == "" {
			continue
		}
		result = append(result, n)
		for i := len(n.children) - 1; i >= 0; i-- {
			stack = append(stack, n.children[i])
		}
	}
	return result
}
func elements(n *node) []*node {
	result := []*node{}
	for _, c := range n.children {
		if c.tag != "" {
			result = append(result, c)
		}
	}
	return result
}
func textContent(n *node, normalized bool) string {
	var b strings.Builder
	stack := []*node{n}
	for len(stack) > 0 {
		c := stack[len(stack)-1]
		stack = stack[:len(stack)-1]
		if c.tag == "" {
			b.WriteString(c.text)
		} else {
			for i := len(c.children) - 1; i >= 0; i-- {
				stack = append(stack, c.children[i])
			}
		}
	}
	if normalized {
		return strings.TrimSpace(normalize(b.String()))
	}
	return b.String()
}
