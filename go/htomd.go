// Package htomd extracts Markdown and metadata from decoded HTML without fetching.
package htomd

import (
	"errors"
	"unicode/utf8"
)

const Version = "0.1.1"

// Options supplies source context. A nil URL differs from an explicitly empty URL.
type Options struct{ URL *string }

// Metadata contains explicit document metadata; nil fields mean absent values.
type Metadata struct {
	Title         *string `json:"title"`
	Author        *string `json:"author"`
	Description   *string `json:"description"`
	Language      *string `json:"language"`
	PublishedTime *string `json:"published_time"`
	URL           *string `json:"url"`
	CanonicalURL  *string `json:"canonical_url"`
}

// Strategy identifies how relevant content was selected.
type Strategy string

const (
	Semantic Strategy = "semantic"
	Scored   Strategy = "scored"
	Fallback Strategy = "fallback"
	None     Strategy = "none"
)

// Diagnostics explains content selection and recovery.
type Diagnostics struct {
	Strategy Strategy `json:"strategy"`
	Notes    []string `json:"notes"`
}

// Document owns its output; callers may modify it without affecting other calls.
type Document struct {
	Markdown    string      `json:"markdown"`
	Metadata    Metadata    `json:"metadata"`
	Diagnostics Diagnostics `json:"diagnostics"`
}

// Extract recovers malformed HTML best-effort. Only invalid UTF-8 inputs fail.
func Extract(html string, options Options) (Document, error) {
	if !utf8.ValidString(html) {
		return Document{}, errors.New("html must be decoded UTF-8")
	}
	if options.URL != nil && !utf8.ValidString(*options.URL) {
		return Document{}, errors.New("url must be decoded UTF-8")
	}
	root, notes := parse(html)
	base := documentBase(root, options.URL)
	metadata := readMetadata(root, options.URL, base)
	selected, diagnostics := selectContent(root)
	refineMetadata(&metadata, selected)
	markdown := render(selected, base)
	diagnostics.Notes = append(notes, diagnostics.Notes...)
	if markdown == "" {
		diagnostics.Strategy = None
	}
	return Document{markdown, metadata, diagnostics}, nil
}

// Convert returns the Markdown produced by Extract.
func Convert(html string, options Options) (string, error) {
	d, err := Extract(html, options)
	return d.Markdown, err
}
