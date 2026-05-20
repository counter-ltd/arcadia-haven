import arcadia

arcadia.register_module(
    name="syntax-explorer-icons",
    version="0.1.0",
    description="File icons in the explorer driven by loaded syntax extensions.",
    tags=["stable", "code-editor"],
)

# Maps language id (as registered by highlight providers) to file extensions.
# Add entries here to support future syntax extensions automatically.
LANG_TO_EXTENSIONS = {
    "rust":        ["rs"],
    "python":      ["py", "pyw"],
    "javascript":  ["js", "mjs", "cjs"],
    "typescript":  ["ts", "mts", "cts"],
    "jsx":         ["jsx"],
    "tsx":         ["tsx"],
    "go":          ["go"],
    "java":        ["java"],
    "c":           ["c", "h"],
    "cpp":         ["cpp", "cc", "cxx", "hpp", "hxx"],
    "csharp":      ["cs"],
    "ruby":        ["rb"],
    "php":         ["php"],
    "swift":       ["swift"],
    "kotlin":      ["kt", "kts"],
    "lua":         ["lua"],
    "dart":        ["dart"],
    "elixir":      ["ex", "exs"],
    "html":        ["html", "htm"],
    "css":         ["css"],
    "scss":        ["scss", "sass"],
    "toml":        ["toml"],
    "yaml":        ["yaml", "yml"],
    "json":        ["json"],
    "sql":         ["sql"],
    "shell":       ["sh", "bash", "zsh"],
    "markdown":    ["md", "mdx"],
    "r":           ["r"],
}


def _build_map():
    """Build file-extension → icon-key map from currently loaded highlight providers."""
    result = {}
    for lang, ext_id in arcadia.list_highlight_providers():
        for file_ext in LANG_TO_EXTENSIONS.get(lang, []):
            result[file_ext] = f"extension-icon/{ext_id}"
    return result


def file_icon_provider(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return _build_map().get(ext)


arcadia.register_file_icon_provider("syntax-explorer-icons", file_icon_provider)
