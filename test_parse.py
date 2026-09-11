# test_parse.py
"""
Sistema completo de pruebas para el analizador sintáctico de B-Minor.
Incluye casos de prueba para todas las construcciones del lenguaje,
manejo de errores, y utilidades de análisis.
"""

import sys
import os
import tempfile
from typing import List, Tuple, Any
from rich import print
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from bminor_lexer import Lexer
from parser import Parser, parse
from errors import error, errors_detected, clear_errors
from model import *

console = Console()

class TestCase:
    """Representa un caso de prueba individual."""
    
    def __init__(self, name: str, code: str, should_pass: bool = True, expected_errors: List[str] = None):
        self.name = name
        self.code = code
        self.should_pass = should_pass
        self.expected_errors = expected_errors or []
        self.result = None
        self.actual_errors = []
        self.ast = None

class TestSuite:
    """Suite completa de pruebas para el parser."""
    
    def __init__(self):
        self.test_cases = []
        self.passed = 0
        self.failed = 0
        
    def add_test(self, name: str, code: str, should_pass: bool = True, expected_errors: List[str] = None):
        """Añade un caso de prueba a la suite."""
        self.test_cases.append(TestCase(name, code, should_pass, expected_errors))
    
    def run_all_tests(self):
        """Ejecuta todos los casos de prueba."""
        console.print("\n[bold blue]🧪 Ejecutando Suite de Pruebas del Parser B-Minor[/bold blue]\n")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task("Ejecutando pruebas...", total=len(self.test_cases))
            
            for i, test_case in enumerate(self.test_cases):
                progress.update(task, completed=i, description=f"Prueba: {test_case.name}")
                self.run_single_test(test_case)
                
            progress.update(task, completed=len(self.test_cases), description="✅ Pruebas completadas")
        
        self.show_results()
    
    def run_single_test(self, test_case: TestCase):
        """Ejecuta un caso de prueba individual."""
        clear_errors()
        
        try:
            # Crear archivo temporal para el código
            with tempfile.NamedTemporaryFile(mode='w', suffix='.bminor', delete=False) as f:
                f.write(test_case.code)
                temp_file = f.name
            
            # Parsear el código
            lexer = Lexer()
            parser = Parser()
            test_case.ast = parser.parse(lexer.tokenize(test_case.code))
            
            # Verificar si hay errores
            has_errors = errors_detected() > 0
            test_case.result = not has_errors if test_case.should_pass else has_errors
            
            # Limpiar archivo temporal
            os.unlink(temp_file)
            
        except Exception as e:
            test_case.result = False
            test_case.actual_errors.append(f"Excepción: {str(e)}")
        
        if test_case.result:
            self.passed += 1
        else:
            self.failed += 1
    
    def show_results(self):
        """Muestra los resultados de las pruebas."""
        table = Table(title="Resultados de las Pruebas")
        table.add_column("Prueba", style="cyan", no_wrap=True)
        table.add_column("Estado", justify="center")
        table.add_column("Esperado", justify="center")
        table.add_column("Descripción", style="dim")
        
        for test_case in self.test_cases:
            status = "✅ PASS" if test_case.result else "❌ FAIL"
            expected = "✅ Éxito" if test_case.should_pass else "❌ Error"
            
            # Truncar nombre si es muy largo
            name = test_case.name if len(test_case.name) <= 30 else test_case.name[:27] + "..."
            
            table.add_row(
                name,
                status,
                expected,
                f"Líneas: {test_case.code.count(chr(10)) + 1}"
            )
        
        console.print(table)
        
        # Resumen final
        total = len(self.test_cases)
        pass_rate = (self.passed / total) * 100 if total > 0 else 0
        
        summary_style = "green" if pass_rate >= 80 else "yellow" if pass_rate >= 60 else "red"
        
        console.print(f"\n[bold {summary_style}]📊 Resumen: {self.passed}/{total} pruebas pasaron ({pass_rate:.1f}%)[/bold {summary_style}]")
        
        if self.failed > 0:
            console.print(f"[red]❌ {self.failed} pruebas fallaron[/red]")
            self.show_failed_tests()
    
    def show_failed_tests(self):
        """Muestra detalles de las pruebas fallidas."""
        console.print("\n[bold red]🔍 Detalles de Pruebas Fallidas:[/bold red]")
        
        for test_case in self.test_cases:
            if not test_case.result:
                panel_content = f"[dim]Código:[/dim]\n{test_case.code[:200]}{'...' if len(test_case.code) > 200 else ''}"
                
                if test_case.actual_errors:
                    panel_content += f"\n\n[dim]Errores:[/dim]\n"
                    panel_content += "\n".join(test_case.actual_errors)
                
                console.print(Panel(
                    panel_content,
                    title=f"❌ {test_case.name}",
                    border_style="red"
                ))

def create_test_suite():
    """Crea la suite completa de pruebas."""
    suite = TestSuite()
    
    # ========== PRUEBAS BÁSICAS ==========
    
    suite.add_test(
        "Programa vacío",
        ""
    )
    
    suite.add_test(
        "Declaración de variable simple",
        "x: integer;"
    )
    
    suite.add_test(
        "Declaración con inicialización",
        "x: integer = 42;"
    )
    
    suite.add_test(
        "Múltiples declaraciones",
        """
        x: integer;
        y: float = 3.14;
        name: string = "B-Minor";
        """
    )
    
    # ========== PRUEBAS DE TIPOS ==========
    
    suite.add_test(
        "Todos los tipos básicos",
        """
        a: integer = 10;
        b: float = 3.14;
        c: boolean = true;
        d: char = 'A';
        e: string = "Hello";
        """
    )
    
    suite.add_test(
        "Arrays con tamaño",
        """
        arr1: array[10] integer;
        arr2: array[5] float = {1.0, 2.0, 3.0, 4.0, 5.0};
        """
    )
    
    suite.add_test(
        "Arrays sin tamaño",
        """
        arr: array[] integer = {1, 2, 3, 4, 5};
        """
    )
    
    # ========== PRUEBAS DE FUNCIONES ==========
    
    suite.add_test(
        "Función simple sin parámetros",
        """
        main: function void() = {
            print "Hello World";
        }
        """
    )
    
    suite.add_test(
        "Función con parámetros",
        """
        add: function integer(a: integer, b: integer) = {
            return a + b;
        }
        """
    )
    
    suite.add_test(
        "Función con arrays como parámetros",
        """
        process: function void(arr: array[] integer, size: integer) = {
            print "Processing array";
        }
        """
    )
    
    suite.add_test(
        "Múltiples funciones",
        """
        factorial: function integer(n: integer) = {
            if (n <= 1) {
                return 1;
            } else {
                return n * factorial(n - 1);
            }
        }
        
        main: function void() = {
            print factorial(5);
        }
        """
    )
    
    # ========== PRUEBAS DE EXPRESIONES ==========
    
    suite.add_test(
        "Expresiones aritméticas",
        """
        main: function void() = {
            x: integer = 2 + 3 * 4;
            y: integer = (2 + 3) * 4;
            z: integer = 10 - 5 / 2;
        }
        """
    )
    
    suite.add_test(
        "Expresiones lógicas",
        """
        main: function void() = {
            a: boolean = true && false;
            b: boolean = true || false;
            c: boolean = !true;
        }
        """
    )
    
    suite.add_test(
        "Expresiones de comparación",
        """
        main: function void() = {
            a: boolean = 5 > 3;
            b: boolean = 2 <= 10;
            c: boolean = 7 == 7;
            d: boolean = 8 != 9;
        }
        """
    )
    
    suite.add_test(
        "Incremento y decremento",
        """
        main: function void() = {
            x: integer = 5;
            ++x;
            x++;
            --x;
            x--;
        }
        """
    )
    
    # ========== PRUEBAS DE SENTENCIAS DE CONTROL ==========
    
    suite.add_test(
        "Sentencia IF simple",
        """
        main: function void() = {
            x: integer = 10;
            if (x > 5) {
                print "x es mayor que 5";
            }
        }
        """
    )
    
    suite.add_test(
        "IF-ELSE completo",
        """
        main: function void() = {
            x: integer = 3;
            if (x > 5) {
                print "Mayor";
            } else {
                print "Menor o igual";
            }
        }
        """
    )
    
    suite.add_test(
        "IF-ELSE anidado",
        """
        main: function void() = {
            x: integer = 10;
            if (x > 0) {
                if (x > 10) {
                    print "Muy grande";
                } else {
                    print "Positivo";
                }
            } else {
                print "No positivo";
            }
        }
        """
    )
    
    suite.add_test(
        "Bucle FOR",
        """
        main: function void() = {
            for (i: integer = 0; i < 10; i++) {
                print i;
            }
        }
        """
    )
    
    suite.add_test(
        "Bucle WHILE",
        """
        main: function void() = {
            i: integer = 0;
            while (i < 5) {
                print i;
                i++;
            }
        }
        """
    )
    
    suite.add_test(
        "Bucle DO-WHILE",
        """
        main: function void() = {
            i: integer = 0;
            do {
                print i;
                i++;
            } while (i < 3);
        }
        """
    )
    
    # ========== PRUEBAS DE ARRAYS ==========
    
    suite.add_test(
        "Acceso a arrays",
        """
        main: function void() = {
            arr: array[5] integer = {1, 2, 3, 4, 5};
            x: integer = arr[0];
            arr[1] = 10;
            print arr[x];
        }
        """
    )
    
    suite.add_test(
        "Arrays multidimensionales",
        """
        main: function void() = {
            matrix: array[3] array[3] integer;
            matrix[0][0] = 1;
            matrix[1][2] = 5;
        }
        """
    )
    
    # ========== PRUEBAS DE LLAMADAS A FUNCIONES ==========
    
    suite.add_test(
        "Llamadas a funciones",
        """
        square: function integer(x: integer) = {
            return x * x;
        }
        
        main: function void() = {
            result: integer = square(5);
            print result;
        }
        """
    )
    
    # ========== PRUEBAS DE ERRORES SINTÁCTICOS ==========
    
    suite.add_test(
        "Punto y coma faltante",
        "x: integer = 5",  # Sin punto y coma
        should_pass=False
    )
    
    suite.add_test(
        "Paréntesis no balanceados",
        """
        main: function void() = {
            if (x > 5 {
                print "error";
            }
        }
        """,
        should_pass=False
    )
    
    suite.add_test(
        "Llaves no balanceadas",
        """
        main: function void() = {
            print "Hello";
        """,
        should_pass=False
    )
    
    suite.add_test(
        "Tipo inválido",
        "x: invalid_type = 5;",
        should_pass=False
    )
    
    # ========== PRUEBAS COMPLEJAS ==========
    
    suite.add_test(
        "Programa completo - Fibonacci",
        """
        fibonacci: function integer(n: integer) = {
            if (n <= 1) {
                return n;
            } else {
                return fibonacci(n - 1) + fibonacci(n - 2);
            }
        }
        
        main: function void() = {
            for (i: integer = 0; i < 10; i++) {
                print "fib(", i, ") = ", fibonacci(i);
            }
        }
        """
    )
    
    suite.add_test(
        "Programa complejo - Ordenamiento",
        """
        swap: function void(arr: array[] integer, i: integer, j: integer) = {
            temp: integer = arr[i];
            arr[i] = arr[j];
            arr[j] = temp;
        }
        
        bubble_sort: function void(arr: array[] integer, n: integer) = {
            for (i: integer = 0; i < n - 1; i++) {
                for (j: integer = 0; j < n - i - 1; j++) {
                    if (arr[j] > arr[j + 1]) {
                        swap(arr, j, j + 1);
                    }
                }
            }
        }
        
        print_array: function void(arr: array[] integer, n: integer) = {
            for (i: integer = 0; i < n; i++) {
                print arr[i], " ";
            }
            print "";
        }
        
        main: function void() = {
            numbers: array[] integer = {64, 34, 25, 12, 22, 11, 90};
            n: integer = 7;
            
            print "Array original: ";
            print_array(numbers, n);
            
            bubble_sort(numbers, n);
            
            print "Array ordenado: ";
            print_array(numbers, n);
        }
        """
    )
    
    return suite

def analyze_ast(ast, show_details=False):
    """Analiza el AST generado y muestra información."""
    if not ast:
        console.print("[red]❌ No se pudo generar el AST[/red]")
        return
    
    console.print("[bold green]✅ AST generado exitosamente[/bold green]")
    
    if show_details:
        console.print("\n[bold]🌳 Estructura del AST:[/bold]")
        tree = ast.pretty()
        console.print(tree)
    
    # Contar nodos
    node_count = count_nodes(ast)
    console.print(f"\n📊 Total de nodos en el AST: {node_count}")

def count_nodes(node):
    """Cuenta el número total de nodos en el AST."""
    if not isinstance(node, Node):
        return 0
    
    count = 1
    for field_name, field_value in node.__dict__.items():
        if field_name == 'lineno':
            continue
        if isinstance(field_value, Node):
            count += count_nodes(field_value)
        elif isinstance(field_value, list):
            for item in field_value:
                if isinstance(item, Node):
                    count += count_nodes(item)
    
    return count

def test_single_file(filepath, show_ast=False):
    """Prueba un archivo individual."""
    console.print(f"\n[bold blue]🔍 Probando archivo: {filepath}[/bold blue]")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        
        clear_errors()
        ast = parse(code)
        
        if errors_detected():
            console.print(f"[red]❌ Se encontraron {errors_detected()} errores[/red]")
        else:
            console.print("[green]✅ Análisis sintáctico exitoso[/green]")
            analyze_ast(ast, show_ast)
            
    except FileNotFoundError:
        console.print(f"[red]❌ Archivo no encontrado: {filepath}[/red]")
    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")

def main():
    """Función principal del programa de pruebas."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Sistema de pruebas para el parser B-Minor")
    parser.add_argument('--suite', action='store_true', 
                       help='Ejecuta la suite completa de pruebas')
    parser.add_argument('--file', type=str, 
                       help='Prueba un archivo específico')
    parser.add_argument('--show-ast', action='store_true',
                       help='Muestra la estructura del AST')
    parser.add_argument('--interactive', action='store_true',
                       help='Modo interactivo para probar código')
    
    args = parser.parse_args()
    
    if args.suite:
        suite = create_test_suite()
        suite.run_all_tests()
    elif args.file:
        test_single_file(args.file, args.show_ast)
    elif args.interactive:
        interactive_mode()
    else:
        parser.print_help()

def interactive_mode():
    """Modo interactivo para probar código."""
    console.print("[bold blue]🎮 Modo Interactivo - Parser B-Minor[/bold blue]")
    console.print("Escribe código B-Minor (Ctrl+D para terminar, 'exit' para salir)")
    
    while True:
        try:
            console.print("\n[dim]>>> Ingresa tu código:[/dim]")
            lines = []
            
            while True:
                try:
                    line = input()
                    if line.strip() == 'exit':
                        return
                    lines.append(line)
                except EOFError:
                    break
            
            code = '\n'.join(lines)
            if not code.strip():
                continue
                
            console.print(f"\n[dim]Código ingresado ({len(lines)} líneas):[/dim]")
            console.print(Panel(code, title="Código B-Minor"))
            
            clear_errors()
            ast = parse(code)
            
            if errors_detected():
                console.print(f"[red]❌ Se encontraron {errors_detected()} errores[/red]")
            else:
                console.print("[green]✅ Análisis sintáctico exitoso[/green]")
                analyze_ast(ast, True)
                
        except KeyboardInterrupt:
            console.print("\n[yellow]👋 ¡Hasta luego![/yellow]")
            break
        except Exception as e:
            console.print(f"[red]❌ Error inesperado: {str(e)}[/red]")

if __name__ == '__main__':
    main()