import re
import arcadia

arcadia.register_module(
    name="python-syntax",
    version="0.1.0",
    description="Python syntax highlighting for the code editor.",
    tags=["stable", "code-editor"],
)

arcadia.register_tokens("python-syntax", [
    {"key": "keyword",   "label": "Keyword",          "kind": "color", "default": "#569cd6"},
    {"key": "string",    "label": "String",            "kind": "color", "default": "#ce9178"},
    {"key": "comment",   "label": "Comment",           "kind": "color", "default": "#6a9955"},
    {"key": "type_name", "label": "Type / class",      "kind": "color", "default": "#4ec9b0"},
    {"key": "number",    "label": "Number literal",    "kind": "color", "default": "#b5cea8"},
    {"key": "decorator", "label": "Decorator @…",      "kind": "color", "default": "#c586c0"},
    {"key": "builtin",   "label": "Built-in function", "kind": "color", "default": "#dcdcaa"},
    {"key": "fstring",   "label": "f-string prefix",   "kind": "color", "default": "#d7ba7d"},
])

KEYWORDS = {
    "def", "class", "import", "from", "return", "if", "elif", "else",
    "for", "while", "try", "except", "finally", "with", "as", "pass",
    "break", "continue", "raise", "yield", "lambda", "and", "or", "not",
    "in", "is", "True", "False", "None", "async", "await", "global",
    "nonlocal", "del", "assert",
}

BUILTINS = {
    "print", "len", "range", "enumerate", "zip", "map", "filter",
    "sorted", "reversed", "list", "dict", "set", "tuple", "str", "int",
    "float", "bool", "bytes", "type", "isinstance", "issubclass",
    "hasattr", "getattr", "setattr", "delattr", "callable", "iter",
    "next", "open", "super", "object", "property", "staticmethod",
    "classmethod", "abs", "all", "any", "bin", "chr", "dir", "divmod",
    "format", "hash", "hex", "id", "input", "max", "min", "oct", "ord",
    "pow", "repr", "round", "sum", "vars", "eval", "exec", "compile",
    "globals", "locals", "breakpoint",
}

# Patterns tried in order; first match wins per position.
PATTERNS = [
    # Triple-quoted f-strings (prefix captured separately isn't needed — mark whole span as fstring)
    (re.compile(r'[fF]""".*?"""', re.DOTALL), "fstring"),
    (re.compile(r"[fF]'''.*?'''", re.DOTALL), "fstring"),
    (re.compile(r'[fF]"(?:[^"\\]|\\.)*"'), "fstring"),
    (re.compile(r"[fF]'(?:[^'\\]|\\.)*'"), "fstring"),
    # Triple-quoted strings
    (re.compile(r'""".*?"""', re.DOTALL), "string"),
    (re.compile(r"'''.*?'''", re.DOTALL), "string"),
    # Single-line strings
    (re.compile(r'"(?:[^"\\\n]|\\.)*"'), "string"),
    (re.compile(r"'(?:[^'\\\n]|\\.)*'"), "string"),
    # Comments
    (re.compile(r'#[^\n]*'), "comment"),
    # Decorators
    (re.compile(r'@[\w.]+'), "decorator"),
    # Numbers: hex, bin, oct, float, int (with underscore separators)
    (re.compile(r'\b0[xX][\da-fA-F][\da-fA-F_]*\b'), "number"),
    (re.compile(r'\b0[bB][01][01_]*\b'), "number"),
    (re.compile(r'\b0[oO][0-7][0-7_]*\b'), "number"),
    (re.compile(r'\b\d[\d_]*\.[\d_]*(?:[eE][+-]?\d+)?\b'), "number"),
    (re.compile(r'\b\d[\d_]*(?:[eE][+-]?\d+)?\b'), "number"),
    # PascalCase identifiers → type/class
    (re.compile(r'\b[A-Z][A-Za-z0-9_]*\b'), "type_name"),
]

KEYWORD_RE = re.compile(r'\b(' + '|'.join(re.escape(k) for k in KEYWORDS) + r')\b')
BUILTIN_RE = re.compile(r'\b(' + '|'.join(re.escape(b) for b in BUILTINS) + r')\b')


def _char_to_byte_offsets(text):
    offsets = []
    b = 0
    for ch in text:
        offsets.append(b)
        b += len(ch.encode('utf-8'))
    offsets.append(b)
    return offsets


def highlight(text):
    tokens = arcadia.read_tokens("python-syntax")
    color_map = {
        "keyword":   tokens.get("keyword",   "#569cd6"),
        "string":    tokens.get("string",    "#ce9178"),
        "comment":   tokens.get("comment",   "#6a9955"),
        "type_name": tokens.get("type_name", "#4ec9b0"),
        "number":    tokens.get("number",    "#b5cea8"),
        "decorator": tokens.get("decorator", "#c586c0"),
        "builtin":   tokens.get("builtin",   "#dcdcaa"),
        "fstring":   tokens.get("fstring",   "#d7ba7d"),
    }

    char_to_byte = _char_to_byte_offsets(text)
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

    # High-priority: strings, comments, decorators, numbers, type names
    for pattern, token_key in PATTERNS:
        for m in pattern.finditer(text):
            add(m.start(), m.end(), token_key)

    # Built-ins before keywords (both low-priority)
    for m in BUILTIN_RE.finditer(text):
        add(m.start(), m.end(), "builtin")

    for m in KEYWORD_RE.finditer(text):
        add(m.start(), m.end(), "keyword")

    spans.sort(key=lambda s: s[0])
    return spans


arcadia.register_highlight_provider("python-syntax", "python", highlight)
