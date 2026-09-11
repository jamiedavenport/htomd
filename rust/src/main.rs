use htomd::Options;
use std::{
    env,
    io::{self, Read, Write},
    process::ExitCode,
};
const USAGE: &str = "usage: htomd {convert,extract,help,version} [--url URL]";
fn write(output: &str) -> u8 {
    if let Err(error) = io::stdout().lock().write_all(output.as_bytes()) {
        if error.kind() != io::ErrorKind::BrokenPipe {
            eprintln!("htomd: {error}");
        }
        return 1;
    }
    0
}
fn help() -> u8 {
    write(&format!(
        "{USAGE}\n\nRead UTF-8 HTML from stdin. No file arguments or fetching.\n"
    ))
}
fn bad() -> u8 {
    eprintln!("{USAGE}");
    2
}
fn negative_number(value: &str) -> bool {
    let Some(value) = value.strip_prefix('-') else {
        return false;
    };
    if let Some((left, right)) = value.split_once('.') {
        left.bytes().all(|c| c.is_ascii_digit())
            && !right.is_empty()
            && right.bytes().all(|c| c.is_ascii_digit())
    } else {
        !value.is_empty() && value.bytes().all(|c| c.is_ascii_digit())
    }
}
fn run() -> u8 {
    let args = match env::args_os()
        .skip(1)
        .map(|s| s.into_string())
        .collect::<Result<Vec<_>, _>>()
    {
        Ok(args) => args,
        Err(_) => return bad(),
    };
    if args.is_empty() {
        return help();
    }
    match args[0].as_str() {
        "version" | "--version" => {
            if args[0] == "version"
                && args.len() == 2
                && matches!(args[1].as_str(), "--help" | "-h")
            {
                return help();
            }
            return if args.len() == 1 {
                write(concat!("htomd ", env!("CARGO_PKG_VERSION"), "\n"))
            } else {
                bad()
            };
        }
        "help" | "--help" | "-h" => {
            return if args.len() <= 2
                && (args.len() != 2
                    || args[0] != "help"
                    || matches!(
                        args[1].as_str(),
                        "convert" | "extract" | "help" | "version" | "--help" | "-h"
                    ))
            {
                help()
            } else {
                bad()
            };
        }
        "convert" | "extract" => {}
        _ => return bad(),
    }
    let mut url = None;
    let mut i = 1;
    while i < args.len() {
        let arg = &args[i];
        if arg == "--help" || arg == "-h" {
            return help();
        }
        if let Some(value) = arg.strip_prefix("--url=") {
            url = Some(value);
        } else if arg == "--url" {
            i += 1;
            if i == args.len()
                || (args[i].starts_with('-') && args[i] != "-" && !negative_number(&args[i]))
            {
                return bad();
            }
            url = Some(args[i].as_str());
        } else {
            return bad();
        }
        i += 1;
    }
    let mut html = String::new();
    if let Err(error) = io::stdin().read_to_string(&mut html) {
        eprintln!("htomd: {error}");
        return 1;
    }
    let html = html.strip_prefix('\u{feff}').unwrap_or(&html);
    let document = htomd::extract(html, Options { url });
    let output = if args[0] == "convert" {
        document.markdown
    } else {
        match serde_json::to_string_pretty(&document) {
            Ok(value) => value + "\n",
            Err(error) => {
                eprintln!("htomd: {error}");
                return 1;
            }
        }
    };
    write(&output)
}
fn main() -> ExitCode {
    ExitCode::from(run())
}
