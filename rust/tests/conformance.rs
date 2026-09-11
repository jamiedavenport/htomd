use htomd::{Options, Strategy};
#[test]
fn synthetic() {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../tests/fixtures/synthetic/cases.json");
    let cases: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(path).expect("shared fixtures must exist"))
            .unwrap();
    for case in cases.as_array().unwrap() {
        let html = case["html"].as_str().unwrap();
        let options = Options {
            url: case["url"].as_str(),
        };
        let document = htomd::extract(html, options);
        assert_eq!(
            document.markdown,
            case["markdown"].as_str().unwrap(),
            "{}",
            case["id"]
        );
        assert_eq!(htomd::convert(html, options), document.markdown);
        assert_eq!(
            document.markdown.is_empty(),
            document.diagnostics.strategy == Strategy::None
        );
    }
}
