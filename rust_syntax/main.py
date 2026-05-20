import re
import arcadia

arcadia.register_module(
    name="rust-syntax",
    version="0.1.0",
    description="Rust syntax highlighting for the code editor.",
    tags=["stable", "code-editor"],
)

arcadia.register_tokens("rust-syntax", [
    {"key": "keyword",   "label": "Keyword",         "kind": "color", "default": "#569cd6"},
    {"key": "string",    "label": "String / char",   "kind": "color", "default": "#ce9178"},
    {"key": "comment",   "label": "Comment",         "kind": "color", "default": "#6a9955"},
    {"key": "type_name", "label": "Type / struct",   "kind": "color", "default": "#4ec9b0"},
    {"key": "number",    "label": "Number literal",  "kind": "color", "default": "#b5cea8"},
    {"key": "lifetime",  "label": "Lifetime",        "kind": "color", "default": "#d7ba7d"},
    {"key": "macro",     "label": "Macro",           "kind": "color", "default": "#c586c0"},
    {"key": "attribute", "label": "Attribute #[…]", "kind": "color", "default": "#9cdcfe"},
])

KEYWORDS = {
    "fn", "let", "mut", "pub", "use", "mod", "struct", "enum", "impl", "trait",
    "for", "while", "if", "else", "match", "return", "self", "Self", "super",
    "crate", "where", "type", "const", "static", "async", "await", "move",
    "ref", "in", "loop", "break", "continue", "unsafe", "extern", "dyn", "as",
    "true", "false",
}

# Patterns tried in order; first match wins per position.
# Each tuple is (compiled_regex, token_key).
PATTERNS = [
    (re.compile(r'/\*.*?\*/', re.DOTALL), "comment"),
    (re.compile(r'//[^\n]*'), "comment"),
    (re.compile(r'"(?:[^"\\]|\\.)*"'), "string"),
    (re.compile(r"'(?:[^'\\]|\\.){1}'"), "string"),    # char literal
    (re.compile(r'#!?\[.*?\]', re.DOTALL), "attribute"),
    (re.compile(r"'\w+"), "lifetime"),
    (re.compile(r'\b\w+!(?!\w)'), "macro"),
    (re.compile(r'\b\d[\d_]*(?:\.\d[\d_]*)?(?:[uif]\d+)?\b'), "number"),
    (re.compile(r'\b[A-Z][A-Za-z0-9_]*\b'), "type_name"),
]
KEYWORD_RE = re.compile(r'\b(' + '|'.join(re.escape(k) for k in KEYWORDS) + r')\b')


def _char_to_byte_offsets(text):
    """Build a list mapping char index → byte offset for quick lookup."""
    offsets = []
    b = 0
    for ch in text:
        offsets.append(b)
        b += len(ch.encode('utf-8'))
    offsets.append(b)
    return offsets


def highlight(text):
    tokens = arcadia.read_tokens("rust-syntax")
    color_map = {
        "keyword":   tokens.get("keyword",   "#569cd6"),
        "string":    tokens.get("string",    "#ce9178"),
        "comment":   tokens.get("comment",   "#6a9955"),
        "type_name": tokens.get("type_name", "#4ec9b0"),
        "number":    tokens.get("number",    "#b5cea8"),
        "lifetime":  tokens.get("lifetime",  "#d7ba7d"),
        "macro":     tokens.get("macro",     "#c586c0"),
        "attribute": tokens.get("attribute", "#9cdcfe"),
    }

    char_to_byte = _char_to_byte_offsets(text)
    # claimed[char_idx] = True once that char is covered by a span
    claimed = bytearray(len(text))

    spans = []

    def add(char_start, char_end, token_key):
        if any(claimed[char_start:char_end]):
            return
        color = color_map.get(token_key)
        if not color:
            return
        byte_start = char_to_byte[char_start]
        byte_end = char_to_byte[char_end]
        for i in range(char_start, char_end):
            claimed[i] = 1
        spans.append((byte_start, byte_end, color))

    # Apply non-keyword patterns first (comments, strings, etc.)
    for pattern, token_key in PATTERNS:
        for m in pattern.finditer(text):
            add(m.start(), m.end(), token_key)

    # Keywords last (lowest priority)
    for m in KEYWORD_RE.finditer(text):
        add(m.start(), m.end(), "keyword")

    spans.sort(key=lambda s: s[0])
    return spans


arcadia.register_highlight_provider("rust-syntax", "rust", highlight)
