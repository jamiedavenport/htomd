#[rustfmt::skip]
mod data { include!("entities_data.rs"); }
const WINDOWS_1252: [u32; 32] = [
    0x20ac, 0x81, 0x201a, 0x192, 0x201e, 0x2026, 0x2020, 0x2021, 0x2c6, 0x2030, 0x160, 0x2039,
    0x152, 0x8d, 0x17d, 0x8f, 0x90, 0x2018, 0x2019, 0x201c, 0x201d, 0x2022, 0x2013, 0x2014, 0x2dc,
    0x2122, 0x161, 0x203a, 0x153, 0x9d, 0x17e, 0x178,
];
pub fn decode(input: &str, attribute: bool) -> String {
    let mut output = String::new();
    let mut pos = 0;
    let b = input.as_bytes();
    while pos < input.len() {
        if b[pos] != b'&' {
            let c = input[pos..].chars().next().expect("nonempty UTF-8 suffix");
            output.push(c);
            pos += c.len_utf8();
            continue;
        }
        let start = pos;
        let mut end = pos + 1;
        if b.get(end) == Some(&b'#') {
            end += 1;
            let hex = matches!(b.get(end), Some(b'x' | b'X'));
            if hex {
                end += 1;
            }
            let digits = end;
            while end < b.len()
                && (if hex {
                    b[end].is_ascii_hexdigit()
                } else {
                    b[end].is_ascii_digit()
                })
            {
                end += 1;
            }
            if end > digits {
                let mut value = u32::from_str_radix(&input[digits..end], if hex { 16 } else { 10 })
                    .unwrap_or(0xfffd);
                if b.get(end) == Some(&b';') {
                    end += 1;
                }
                if (0x80..=0x9f).contains(&value) {
                    value = WINDOWS_1252[(value - 0x80) as usize];
                }
                if value == 0 {
                    value = 0xfffd;
                }
                if !((1..=8).contains(&value)
                    || value == 11
                    || (14..=31).contains(&value)
                    || value == 127
                    || (0xfdd0..=0xfdef).contains(&value)
                    || value & 0xffff >= 0xfffe)
                {
                    output.push(char::from_u32(value).unwrap_or('\u{fffd}'));
                }
                pos = end;
                continue;
            }
        } else {
            while end < b.len() && b[end].is_ascii_alphanumeric() {
                end += 1;
            }
            if b.get(end) == Some(&b';') {
                end += 1;
            }
            let mut found = None;
            for length in (start + 2..=end).rev() {
                let name = &input[start + 1..length];
                if let Ok(i) = data::NAMED.binary_search_by_key(&name, |(n, _)| *n) {
                    if attribute
                        && !name.ends_with(';')
                        && b.get(length)
                            .is_some_and(|c| c.is_ascii_alphanumeric() || *c == b'=')
                    {
                        break;
                    }
                    found = Some((length, data::NAMED[i].1));
                    break;
                }
            }
            if let Some((end, value)) = found {
                output.push_str(value);
                pos = end;
                continue;
            }
        }
        output.push('&');
        pos = start + 1;
    }
    output
}
