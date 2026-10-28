# B-Minor Compiler

A complete compiler implementation written in Python for the **B-Minor** programming language. This project transforms B-Minor source code through lexical analysis, parsing, type checking, abstract syntax tree (AST) generation, and target code generation.

## Features

- **Lexical Analysis (Lexer):** Tokenizes B-Minor source code using regular expressions.
- **Syntactic Analysis (Parser):** Builds an Abstract Syntax Tree (AST) following language grammar rules.
- **Semantic Analysis & Type Checking:** Verifies type safety, scope rules, and symbol declarations using a symbol table.
- **Code Generation:** Compiles B-Minor programs into target code executable alongside the C runtime environment.
- **AST Visualization:** Utility module to pretty-print or inspect generated AST structures.

## File Structure

```
Compilador-b-minor/
│
├── bminor.py          # Main driver / CLI entry point for the compiler
├── bminor_lexer.py    # Lexical analyzer (Scanner)
├── parser.py          # Syntactic analyzer (Parser)
├── model.py           # AST node definitions and data structures
├── astprint.py        # Utility module for printing/formatting ASTs
├── symtab.py          # Symbol table implementation for scope management
├── typesys.py         # Type system definitions and type checking logic
├── checker.py         # Semantic checker component
├── codegen.py         # Target code generator
├── errors.py          # Error handling and reporting utilities
├── test_parse.py      # Test script for parsing verification
└── runtime.c          # C runtime library supporting program execution
```

## Prerequisites

- **Python 3.8+**
- A C compiler (e.g., `gcc` or `clang`) for compiling the runtime support module (`runtime.c`).

## Usage

Run the main compiler entry point passing the target B-Minor source file:

```bash
python bminor.py <path_to_source_file.bminor>
```

To run the parser test suite:

```bash
python test_parse.py
```

## Compilation Pipeline

1. **Tokenization (`bminor_lexer.py`):** Converts raw character streams into lexical tokens.
2. **Parsing (`parser.py` & `model.py`):** Parses tokens into AST nodes defined in `model.py`.
3. **Semantic Checking (`checker.py`, `symtab.py`, `typesys.py`):** Ensures identifiers are declared and types match across operations.
4. **Code Generation (`codegen.py`):** Produces machine/intermediate code linked with `runtime.c`.

## License

This project is created for educational purposes as part of a compiler design curriculum.
