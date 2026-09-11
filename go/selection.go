package htomd

import (
	"fmt"
	"math"
	"regexp"
	"strings"
	"unicode/utf8"
)

var inert = set("head title meta link base script style template noscript iframe object embed svg canvas nav button input select textarea dialog")
var navRoles = set("navigation banner contentinfo menu menubar dialog")
var structures = set("ul ol dl table blockquote pre")
var containers = set("article main section div body #document")
var evidence = set("p pre li dt dd td th blockquote")
var headings = set("h1 h2 h3 h4 h5 h6")
var negative = set("advertisement ads advert promo promotion related share sharing social cookie consent newsletter comments comment sidebar breadcrumb breadcrumbs pagination toolbar footer banner dropdown catlinks menu pager teaser toc well")
var positive = set("article content main post entry story text documentation")
var references = set("footnotes references endnotes bibliography")
var camelCase = regexp.MustCompile(`([a-z])([A-Z])`)
var hintWords = regexp.MustCompile(`[a-z0-9]+`)
var hiddenStyle = regexp.MustCompile(`(?i)(?:^|;)\s*(?:display\s*:\s*none|visibility\s*:\s*(?:hidden|collapse))\s*(?:!important\s*)?(?:;|$)`)

func hints(n *node) map[string]bool {
	value := camelCase.ReplaceAllString(n.attrs["class"]+" "+n.attrs["id"], "${1} ${2}")
	return set(strings.Join(hintWords.FindAllString(strings.ToLower(value), -1), " "))
}
func intersects(a, b map[string]bool) bool {
	for key := range a {
		if b[key] {
			return true
		}
	}
	return false
}

type stats struct{ characters, linked, punctuation, blocks, headings, code, cells, images, controls int }

func (s stats) density() float64 { return float64(s.linked) / float64(max(1, s.characters)) }
func excluded(n *node, local bool) bool {
	_, hidden := n.attrs["hidden"]
	if inert[n.tag] || hidden || strings.ToLower(n.attrs["aria-hidden"]) == "true" || hiddenStyle.MatchString(n.attrs["style"]) {
		return true
	}
	if n.tag == "a" && hints(n)["headerlink"] {
		return strings.HasPrefix(n.attrs["href"], "#")
	}
	if navRoles[strings.ToLower(n.attrs["role"])] {
		return true
	}
	return (n.tag == "header" || n.tag == "footer") && !local
}
func visibleTree(root *node) {
	type entry struct {
		n     *node
		local bool
	}
	stack := []entry{{root, false}}
	for len(stack) > 0 {
		e := stack[len(stack)-1]
		stack = stack[:len(stack)-1]
		local := e.local || e.n.tag == "article" || e.n.tag == "main" || e.n.attrs["role"] == "main"
		kept := []*node{}
		for _, c := range e.n.children {
			if c.tag != "" {
				if excluded(c, local) {
					continue
				}
				stack = append(stack, entry{c, local})
			}
			kept = append(kept, c)
		}
		e.n.children = kept
	}
}
func statistics(root *node) map[*node]stats {
	result := map[*node]stats{}
	nodes := walk(root)
	for i := len(nodes) - 1; i >= 0; i-- {
		n := nodes[i]
		s := stats{}
		for _, c := range n.children {
			if c.tag == "" {
				s.characters += utf8.RuneCountInString(strings.TrimSpace(c.text))
				for _, ch := range c.text {
					if strings.ContainsRune(",.;:!?。，；：！？،؛", ch) {
						s.punctuation++
					}
				}
			} else {
				o := result[c]
				s.characters += o.characters
				s.linked += o.linked
				s.punctuation += o.punctuation
				s.blocks += o.blocks
				s.headings += o.headings
				s.code += o.code
				s.cells += o.cells
				s.images += o.images
				s.controls += o.controls
			}
		}
		if evidence[n.tag] && s.characters > 0 {
			s.blocks++
		}
		if headings[n.tag] && s.characters > 0 {
			s.headings++
		}
		if n.tag == "pre" {
			s.code++
		}
		if n.tag == "td" || n.tag == "th" {
			s.cells++
		}
		if n.tag == "img" && n.attrs["src"] != "" {
			s.images++
		}
		if set("form button input select textarea")[n.tag] {
			s.controls++
		}
		if n.tag == "a" {
			s.linked = s.characters
		}
		result[n] = s
	}
	return result
}
func clutter(n *node, s stats) bool {
	if set("#document html body main article")[n.tag] {
		return false
	}
	tokens := hints(n)
	if intersects(tokens, references) || n.attrs["role"] == "note" {
		return false
	}
	if !intersects(tokens, negative) || evidence[n.tag] || headings[n.tag] {
		return false
	}
	if s.density() > 0.35 || s.controls > 0 {
		return true
	}
	if tokens["footer"] && s.density() > 0.15 {
		return true
	}
	if n.tag == "aside" && s.code == 0 && s.cells == 0 {
		return true
	}
	if s.blocks == 0 && s.characters < 180 {
		return true
	}
	if tokens["comments"] || tokens["comment"] {
		count := 0
		for _, c := range elements(n) {
			t := hints(c)
			if t["comment"] || t["reply"] {
				count++
			}
		}
		return count >= 2
	}
	return false
}
func plausible(n *node, s stats, semantic bool) bool {
	if s.characters == 0 {
		return semantic && s.images > 0
	}
	if s.code > 0 || s.cells > 0 {
		return true
	}
	if n.tag == "p" && s.characters > s.linked {
		return true
	}
	if s.density() >= 0.8 {
		return semantic && s.headings > 0 && s.blocks > 0
	}
	return containers[n.tag] || evidence[n.tag] || headings[n.tag] || structures[n.tag] || semantic
}
func scores(root *node, all map[*node]stats, relaxed bool) map[*node]float64 {
	result := map[*node]float64{}
	for _, n := range walk(root) {
		s := all[n]
		if !containers[n.tag] || !plausible(n, s, false) {
			continue
		}
		t := hints(n)
		score := math.Sqrt(float64(s.characters)) + float64(min(s.blocks, 30))*2
		score += float64(min(s.punctuation, 40))*0.25 + float64(min(s.code+s.cells, 12))*2
		if intersects(t, positive) {
			score += 8
		}
		if !relaxed && intersects(t, negative) {
			score -= 18
		}
		result[n] = score * math.Pow(1-s.density(), 2)
	}
	for _, n := range walk(root) {
		if !evidence[n.tag] {
			continue
		}
		hasEvidence := false
		for _, c := range elements(n) {
			hasEvidence = hasEvidence || evidence[c.tag]
		}
		if hasEvidence {
			continue
		}
		s := all[n]
		support := (1 + math.Min(float64(s.characters)/100, 3)) * (1 - s.density())
		ancestor := n.parent
		for _, weight := range []float64{1, 0.5, 0.25} {
			if ancestor == nil {
				break
			}
			if _, ok := result[ancestor]; ok {
				result[ancestor] += support * weight
			}
			ancestor = ancestor.parent
		}
	}
	return result
}
func winner(nodes []*node, ranked map[*node]float64) *node {
	var best *node
	for _, n := range nodes {
		if best == nil || ranked[n] > ranked[best] {
			best = n
		}
	}
	return best
}
func selectContent(root *node) ([]*node, Diagnostics) {
	visibleTree(root)
	all := statistics(root)
	removed := 0
	cleanup := []*node{root}
	for len(cleanup) > 0 {
		n := cleanup[len(cleanup)-1]
		cleanup = cleanup[:len(cleanup)-1]
		kept := []*node{}
		for _, c := range n.children {
			if c.tag != "" && clutter(c, all[c]) {
				removed++
			} else {
				kept = append(kept, c)
			}
		}
		n.children = kept
		children := elements(n)
		for i := len(children) - 1; i >= 0; i-- {
			cleanup = append(cleanup, children[i])
		}
	}
	if removed > 0 {
		all = statistics(root)
	}
	ranked := scores(root, all, false)
	notes := []string{}
	if removed > 0 {
		notes = append(notes, fmt.Sprintf("Removed %d conditionally identified clutter blocks.", removed))
	}
	candidates, landmarks := []*node{}, []*node{}
	for _, n := range walk(root) {
		landmark := n.tag == "main" || n.attrs["role"] == "main"
		if !(landmark || n.tag == "article") || !plausible(n, all[n], true) || clutter(n, all[n]) || hints(n)["teaser"] && all[n].density() > 0.1 {
			continue
		}
		candidates = append(candidates, n)
		if landmark {
			landmarks = append(landmarks, n)
		}
	}
	if len(landmarks) > 0 {
		candidates = landmarks
	}
	if best := winner(candidates, ranked); best != nil {
		return []*node{best}, Diagnostics{Semantic, notes}
	}
	rankedCandidates := func() []*node {
		out := []*node{}
		for _, n := range walk(root) {
			if _, ok := ranked[n]; ok && n.tag != "body" && n.tag != "#document" {
				out = append(out, n)
			}
		}
		return out
	}
	best := winner(rankedCandidates(), ranked)
	if best == nil || ranked[best] < 5 {
		notes = append(notes, "Retried selection once with relaxed class penalties.")
		ranked = scores(root, all, true)
		best = winner(rankedCandidates(), ranked)
	}
	if best != nil && ranked[best] >= 5 {
		selected := []*node{best}
		if best.parent != nil {
			selected = []*node{}
			threshold := math.Max(5, ranked[best]*0.18)
			for _, sibling := range elements(best.parent) {
				s := all[sibling]
				if clutter(sibling, s) {
					continue
				}
				if sibling == best || ranked[sibling] >= threshold && s.density() < 0.5 || headings[sibling.tag] && s.density() < 0.5 || sibling.tag == "p" && s.density() < 0.25 && s.characters > 0 {
					selected = append(selected, sibling)
				}
			}
		}
		return selected, Diagnostics{Scored, notes}
	}
	selected := []*node{}
	stack := []*node{root}
	for len(stack) > 0 && len(selected) < 256 {
		n := stack[len(stack)-1]
		stack = stack[:len(stack)-1]
		s := all[n]
		if clutter(n, s) {
			continue
		}
		children := elements(n)
		if (evidence[n.tag] || headings[n.tag] || structures[n.tag]) && plausible(n, s, false) || len(children) == 0 && s.characters > 0 && s.density() < 0.5 {
			selected = append(selected, n)
		} else {
			for i := len(children) - 1; i >= 0; i-- {
				stack = append(stack, children[i])
			}
		}
	}
	strategy := Fallback
	if len(selected) > 0 {
		notes = append(notes, "Recovered plausible blocks.")
	} else {
		notes = append(notes, "No relevant visible content found.")
	}
	return selected, Diagnostics{strategy, notes}
}
