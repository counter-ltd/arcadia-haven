import arcadia

def greet(args):
    name = args[0] if args else "world"
    return f"Hello, {name}! Greeting from a Python extension."

def info(args):
    return arcadia.execute("shell.execute", ["uname", "-a"])

def version(args):
    import sys
    return f"Python {sys.version} running inside Arcadia."

arcadia.register_module(
    name="hello",
    version="0.1.0",
    description="Demo Python extension — hello world",
    tags=["demo"],
)
arcadia.register_command("hello.greet", "Greet by name: hello.greet [name]", greet)
arcadia.register_command("hello.info", "System info via shell module", info)
arcadia.register_command("hello.version", "Report Python runtime version", version)
