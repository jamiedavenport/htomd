// Command htomd converts UTF-8 HTML on stdin into Markdown or extraction JSON.
package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"os/signal"
	"regexp"
	"strings"
	"syscall"

	"github.com/jamiedavenport/htomd/go"
)

func run(args []string) int {
	help := func() int {
		fmt.Println("usage: htomd {convert,extract,help,version} [--url URL]\n\nRead UTF-8 HTML from stdin. No file arguments or fetching.")
		return 0
	}
	bad := func() int {
		fmt.Fprintln(os.Stderr, "usage: htomd {convert,extract,help,version} [--url URL]")
		return 2
	}
	if len(args) == 0 {
		return help()
	}
	if args[0] == "--version" || args[0] == "version" {
		if len(args) == 2 && (args[1] == "--help" || args[1] == "-h") && args[0] == "version" {
			return help()
		}
		if len(args) != 1 {
			return bad()
		}
		fmt.Println("htomd " + htomd.Version)
		return 0
	}
	if args[0] == "--help" || args[0] == "-h" || args[0] == "help" {
		if len(args) > 2 || len(args) == 2 && args[0] == "help" && !strings.Contains("|convert|extract|help|version|--help|-h|", "|"+args[1]+"|") {
			return bad()
		}
		return help()
	}
	if args[0] != "convert" && args[0] != "extract" {
		return bad()
	}
	options := htomd.Options{}
	for i := 1; i < len(args); i++ {
		arg := args[i]
		if arg == "--help" || arg == "-h" {
			return help()
		}
		if strings.HasPrefix(arg, "--url=") {
			value := strings.TrimPrefix(arg, "--url=")
			options.URL = &value
		} else if arg == "--url" {
			i++
			if i == len(args) || (strings.HasPrefix(args[i], "-") && args[i] != "-" && !regexp.MustCompile(`^-(?:[0-9]+|[0-9]*\.[0-9]+)$`).MatchString(args[i])) {
				return bad()
			}
			value := args[i]
			options.URL = &value
		} else {
			return bad()
		}
	}
	input, err := io.ReadAll(os.Stdin)
	if err != nil {
		fmt.Fprintln(os.Stderr, "htomd:", err)
		return 1
	}
	input = bytes.TrimPrefix(input, []byte{0xef, 0xbb, 0xbf})
	document, err := htomd.Extract(string(input), options)
	if err != nil {
		fmt.Fprintln(os.Stderr, "htomd:", err)
		return 1
	}
	var output []byte
	if args[0] == "convert" {
		output = []byte(document.Markdown)
	} else {
		var buffer bytes.Buffer
		encoder := json.NewEncoder(&buffer)
		encoder.SetEscapeHTML(false)
		encoder.SetIndent("", "  ")
		if err = encoder.Encode(document); err != nil {
			fmt.Fprintln(os.Stderr, "htomd:", err)
			return 1
		}
		output = buffer.Bytes()
	}
	if _, err = os.Stdout.Write(output); err != nil {
		if !errors.Is(err, syscall.EPIPE) {
			fmt.Fprintln(os.Stderr, "htomd:", err)
		}
		return 1
	}
	return 0
}
func main() { signal.Ignore(syscall.SIGPIPE); os.Exit(run(os.Args[1:])) }
