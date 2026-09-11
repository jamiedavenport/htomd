package htomd

import (
	"fmt"
	"net/url"
	"strings"
)

var safeSchemes = set("http https mailto tel ftp")

func checkedURL(value string) string {
	return strings.Map(func(c rune) rune {
		if c <= 32 || c == 127 {
			return -1
		}
		return c
	}, value)
}
func safeURL(value string, base *string) *string {
	value = strings.TrimSpace(value)
	parsed, err := url.Parse(checkedURL(value))
	if err != nil || (parsed.Scheme != "" && !safeSchemes[strings.ToLower(parsed.Scheme)]) {
		return nil
	}
	if parsed.Scheme != "" {
		return &value
	}
	if base != nil && *base != "" {
		b, err := url.Parse(*base)
		if err != nil {
			return nil
		}
		r, err := url.Parse(value)
		if err != nil {
			return nil
		}
		value = b.ResolveReference(r).String()
	}
	parsed, err = url.Parse(checkedURL(value))
	if err != nil || (parsed.Scheme != "" && !safeSchemes[strings.ToLower(parsed.Scheme)]) {
		return nil
	}
	return &value
}
func documentBase(root *node, source *string) *string {
	var base *string
	if source != nil && *source != "" {
		base = safeURL(*source, nil)
	}
	for _, n := range walk(root) {
		href, ok := n.attrs["href"]
		if n.tag != "base" || !ok {
			continue
		}
		candidate := safeURL(href, base)
		if candidate != nil && *candidate != "" {
			u, e := url.Parse(*candidate)
			if e == nil && (u.Scheme == "http" || u.Scheme == "https") && u.Host != "" {
				return candidate
			}
		}
	}
	return base
}
func destination(value string) string {
	var b strings.Builder
	for _, c := range []byte(value) {
		if c >= 'a' && c <= 'z' || c >= 'A' && c <= 'Z' || c >= '0' && c <= '9' || strings.ContainsRune("/:?#@!$&'*+,;=%[]~_-.", rune(c)) {
			b.WriteByte(c)
		} else {
			fmt.Fprintf(&b, "%%%02X", c)
		}
	}
	return b.String()
}
