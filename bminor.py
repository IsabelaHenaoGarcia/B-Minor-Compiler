import sys
import argparse
import pandas as pd
from tabulate import tabulate
from rich import print

from bminor_lexer import Lexer
from parser import parse
from errors import errors_detected, clear_errors
from checker import Check
from codegen import generate_code

def scan_file(filepath):
    """Realiza el análisis léxico de un archivo y muestra los tokens."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
    except FileNotFoundError:
        print(f"Error: El archivo '{filepath}' no fue encontrado.")
        sys.exit(1)

    lexer = Lexer()
    tokens_list = []
    errors_list = []

    # Captura de errores léxicos
    def lexer_error(t):
        error_message = f"Error Léxico: Carácter ilegal '{t.value[0]}' en la línea {t.lineno}"
        errors_list.append(error_message)
        lexer.index += 1
    lexer.error = lexer_error

    # Tokenización
    for tok in lexer.tokenize(code):
        if tok.type == 'ERROR':
            errors_list.append(tok.value)
        else:
            tokens_list.append(tok)

    if errors_list:
        for error in errors_list:
            print(error)
    
    if not tokens_list and not errors_list:
        print("Análisis léxico completado: no se encontraron tokens.")
        return

    if tokens_list:
        line_starts = [0] + [i + 1 for i, char in enumerate(code) if char == '\n']
        
        table_data = []
        for tok in tokens_list:
            line_start_index = line_starts[tok.lineno - 1]
            columna = tok.index - line_start_index + 1
            table_data.append([tok.type, repr(tok.value), tok.lineno, columna])
                
        df = pd.DataFrame(table_data, columns=["TIPO", "VALOR", "LINEA", "COLUMNA"])
        df.index = range(1, len(df) + 1)
        print(tabulate(df, headers='keys', tablefmt='fancy_grid', stralign='left', showindex="TOKEN #"))

def parse_file(filepath):
    """Realiza el análisis sintáctico de un archivo y muestra el AST."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
    except FileNotFoundError:
        print(f"Error: El archivo '{filepath}' no fue encontrado.")
        sys.exit(1)

    clear_errors()
    
    ast = parse(code)
    
    if not errors_detected():
        print("[bold green]Análisis sintáctico completado sin errores.[/bold green]")
        if ast:
            print("[bold blue]Mostrando Árbol de Sintaxis Abstracta (AST):[/bold blue]")
            tree_vis = ast.pretty()
            print(tree_vis)
    else:
        print(f"[bold red]Se encontraron {errors_detected()} errores de sintaxis.[/bold red]")

def check_file(filepath):
    """Realiza el análisis sintáctico y semántico de un archivo."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
    except FileNotFoundError:
        print(f"Error: El archivo '{filepath}' no fue encontrado.")
        sys.exit(1)

    clear_errors()
    
    ast = parse(code)
    
    # Detenerse si hay errores de sintaxis antes de continuar
    if errors_detected():
        print(f"[bold red]Se encontraron {errors_detected()} errores de sintaxis. No se puede continuar con el análisis semántico.[/bold red]")
        return
        
    print("[bold blue]Análisis sintáctico completado. Iniciando análisis semántico...[/bold blue]")
    
    # Iniciar el análisis semántico
    global_env = Check.checker(ast)
    
    if not errors_detected():
        print("[bold green]Análisis semántico completado sin errores.[/bold green]")
        print("[bold blue]Mostrando Tablas de Símbolos:[/bold blue]")
        global_env.print()
    else:
        print(f"[bold red]Se encontraron {errors_detected()} errores en total.[/bold red]")

def codegen_file(filepath):
    """
    Realiza el pipeline completo: Parse, Check y Generación de Código.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
    except FileNotFoundError:
        print(f"Error: El archivo '{filepath}' no fue encontrado.")
        sys.exit(1)

    clear_errors()
    
    # 1. Fase de Parseo
    print("Fase 1: Análisis Léxico y Sintáctico...")
    ast = parse(code)
    if errors_detected():
        print(f"[bold red]Se encontraron {errors_detected()} errores de sintaxis. No se puede continuar.[/bold red]")
        return
    print("Análisis sintáctico completado sin errores.\n")

    # 2. Fase de Chequeo
    print("Fase 2: Análisis Semántico...")
    global_env = Check.checker(ast)
    if errors_detected():
        print(f"[bold red]Se encontraron {errors_detected()} errores semánticos. No se puede continuar.[/bold red]")
        return
    print("Análisis semántico completado sin errores.\n")

    # 3. Fase de Generación de Código
    print("Fase 3: Generación de Código LLVM...")
    try:
        ir_code = generate_code(ast)  # Llama a la función importada
        
        output_filename = "output.ll"
        with open(output_filename, 'w') as f:
            f.write(ir_code)
        
        print(f"Código LLVM IR generado exitosamente y guardado en '{output_filename}'")

    except Exception as e:
        print(f"Error durante la generación de código:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

def main():
    parser = argparse.ArgumentParser(description="Compilador para el lenguaje B-Minor 2025.")  
    parser.add_argument('--scan', action='store_true', help='Realiza el análisis léxico del archivo.')
    parser.add_argument('--parse', action='store_true', help='Realiza el análisis sintáctico del archivo.')
    parser.add_argument('--check', action='store_true', help='Realiza el análisis sintáctico y semántico del archivo.')
    parser.add_argument('--codegen', action='store_true', help='Genera el código LLVM IR (.ll) del archivo.')
    
    parser.add_argument('filepath', type=str, help='El archivo .bminor a procesar.')
    args = parser.parse_args()

    if args.scan:
        scan_file(args.filepath)
    elif args.parse:
        parse_file(args.filepath)
    elif args.check:
        check_file(args.filepath)
    elif args.codegen:
        codegen_file(args.filepath)
    else:
        print("Acción no especificada. Debes usar --scan, --parse, --check, o --codegen.")
        parser.print_help()
        sys.exit(1)

if __name__ == '__main__':
    main()