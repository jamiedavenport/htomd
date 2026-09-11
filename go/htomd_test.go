package htomd_test

import (
	"encoding/json"
	"os"
	"strings"
	"testing"

	"github.com/jamiedavenport/htomd/go"
)

func TestSynthetic(t *testing.T) {
	data, err := os.ReadFile("../tests/fixtures/synthetic/cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var cases []struct {
		ID       string  `json:"id"`
		HTML     string  `json:"html"`
		URL      *string `json:"url"`
		Markdown string  `json:"markdown"`
	}
	if err = json.Unmarshal(data, &cases); err != nil {
		t.Fatal(err)
	}
	for _, c := range cases {
		t.Run(c.ID, func(t *testing.T) {
			d, err := htomd.Extract(c.HTML, htomd.Options{URL: c.URL})
			if err != nil {
				t.Fatal(err)
			}
			if d.Markdown != c.Markdown {
				t.Fatalf("got %q, want %q", d.Markdown, c.Markdown)
			}
			converted, err := htomd.Convert(c.HTML, htomd.Options{URL: c.URL})
			if err != nil || converted != d.Markdown {
				t.Fatal("convert differs from extract", err)
			}
			if (d.Markdown == "") != (d.Diagnostics.Strategy == htomd.None) {
				t.Fatal("invalid empty strategy")
			}
		})
	}
}
func TestOwnedOptionalValues(t *testing.T) {
	url := ""
	d, err := htomd.Extract("<h1>Tea</h1>", htomd.Options{URL: &url})
	if err != nil {
		t.Fatal(err)
	}
	url = "changed"
	if d.Metadata.URL == nil || *d.Metadata.URL != "" {
		t.Fatal("URL aliased or lost")
	}
	*d.Metadata.Title = "changed"
	d.Diagnostics.Notes = append(d.Diagnostics.Notes, "changed")
	next, err := htomd.Extract("<h1>Tea</h1>", htomd.Options{})
	if err != nil || next.Metadata.URL != nil || *next.Metadata.Title != "Tea" {
		t.Fatal("results are not independent")
	}
}
func TestInvalidUTF8(t *testing.T) {
	bad := string([]byte{255})
	for _, input := range []struct {
		html    string
		options htomd.Options
	}{{bad, htomd.Options{}}, {"", htomd.Options{URL: &bad}}} {
		if _, err := htomd.Extract(input.html, input.options); err == nil {
			t.Fatal("accepted invalid UTF-8")
		}
	}
}
func TestDeepPipeline(t *testing.T) {
	output, err := htomd.Convert("<article>"+strings.Repeat("<div>", 3000)+"Text."+strings.Repeat("</div>", 3000)+"</article>", htomd.Options{})
	if err != nil || output != "Text.\n" {
		t.Fatal(output, err)
	}
}
func TestLargeCounters(t *testing.T) {
	output, err := htomd.Convert("<ol start='999999999999999999999999999'><li>A<li>B</ol>", htomd.Options{})
	if err != nil || output != "999999999999999999999999999. A\n1000000000000000000000000000. B\n" {
		t.Fatal(output, err)
	}
}
func TestMetadataPrecedence(t *testing.T) {
	d, err := htomd.Extract(`<meta property="og:title" content="Social"><meta name="author" content="First"><meta name="author" content="Second"><article><h1>Chosen</h1><time datetime="Today">Date</time><p>Tea</p></article>`, htomd.Options{})
	if err != nil || *d.Metadata.Title != "Chosen" || *d.Metadata.Author != "First" || *d.Metadata.PublishedTime != "Today" {
		t.Fatal(d, err)
	}
}
