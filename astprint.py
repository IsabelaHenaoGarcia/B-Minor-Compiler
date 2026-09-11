# astprint.py

from graphviz import Digraph
from rich import print
import os  

from model import *

class ASTPrinter(Visitor):
    node_defaults = {
        'shape': 'box',
        'color': 'deepskyblue',
        'style': 'filled',
        'fontname': 'Helvetica'
    }
    edge_defaults = {
        'arrowhead': 'none'
    }

    def __init__(self):
        self.dot = Digraph('AST')
        self.dot.attr('node', **self.node_defaults)
        self.dot.attr('edge', **self.edge_defaults)
        self._seq = 0

    @property
    def name(self):
        """Genera un ID único para cada nodo del gráfico."""
        self._seq += 1
        return f'n{self._seq:02d}'

    @classmethod
    def render(cls, n: Node, filename: str = 'ast.pdf'):
        """
        Método de clase para renderizar el AST.
        Genera un archivo PDF y lo abre.
        """
        dot_visitor = cls()
        if n:
            n.accept(dot_visitor)
        
        try:
            dot_visitor.dot.render(filename, view=True, cleanup=True, format='pdf')
            print(f"[bold green] AST renderizado y guardado como '{filename}.pdf'[/bold green]")
        except Exception as e:
            print(f"[bold red] Error al renderizar con Graphviz:[/bold red]")
            print(dot_visitor.dot.source)

    def visit(self, n: Program):
        name = self.name
        self.dot.node(name, label='Program')
        for stmt in n.body:
            child_name = stmt.accept(self)
            self.dot.edge(name, child_name)
        return name

    def visit(self, n: VarDecl):
        name = self.name
        type_name = n.type.name if isinstance(n.type, SimpleType) else 'array'
        self.dot.node(name, label=f'VarDecl\n{n.name}: {type_name}')
        if n.value:
            self.dot.edge(name, n.value.accept(self))
        return name

    def visit(self, n: FuncDecl):
        name = self.name
        return_type = n.type.name if isinstance(n.type, SimpleType) else 'array'
        self.dot.node(name, label=f'FuncDecl\n{n.name}(): {return_type}')
        if n.params:
            for param in n.params:
                self.dot.edge(name, param.accept(self))
        if n.body:
            self.dot.edge(name, n.body.accept(self), label='body')
        return name

    def visit(self, n: Param):
        name = self.name
        type_name = n.type.name if isinstance(n.type, SimpleType) else 'array'
        self.dot.node(name, label=f'Param\n{n.name}: {type_name}', shape='ellipse')
        return name

    def visit(self, n: BlockStmt):
        name = self.name
        self.dot.node(name, label='Block')
        for stmt in n.statements:
            self.dot.edge(name, stmt.accept(self))
        return name

    def visit(self, n: IfStmt):
        name = self.name
        self.dot.node(name, label='If')
        self.dot.edge(name, n.condition.accept(self), label='cond')
        self.dot.edge(name, n.true_body.accept(self), label='true')
        if n.false_body:
            self.dot.edge(name, n.false_body.accept(self), label='false')
        return name

    def visit(self, n: WhileStmt):
        name = self.name
        self.dot.node(name, label='While')
        self.dot.edge(name, n.condition.accept(self), label='cond')
        self.dot.edge(name, n.body.accept(self), label='body')
        return name
        
    def visit(self, n: DoWhileStmt):
        name = self.name
        self.dot.node(name, label='DoWhile')
        self.dot.edge(name, n.body.accept(self), label='body')
        self.dot.edge(name, n.condition.accept(self), label='cond')
        return name

    def visit(self, n: ForStmt):
        name = self.name
        self.dot.node(name, label='For')
        if n.init:
            self.dot.edge(name, n.init.accept(self), label='init')
        if n.condition:
            self.dot.edge(name, n.condition.accept(self), label='cond')
        if n.update:
            self.dot.edge(name, n.update.accept(self), label='update')
        self.dot.edge(name, n.body.accept(self), label='body')
        return name
        
    def visit(self, n: ReturnStmt):
        name = self.name
        self.dot.node(name, label='Return')
        if n.value:
            self.dot.edge(name, n.value.accept(self))
        return name

    def visit(self, n: PrintStmt):
        name = self.name
        self.dot.node(name, label='Print')
        for value in n.values:
            self.dot.edge(name, value.accept(self))
        return name
        
    def visit(self, n: BinOper):
        name = self.name
        self.dot.node(name, label=f'{n.op}', shape='circle', color='lightcoral')
        self.dot.edge(name, n.left.accept(self))
        self.dot.edge(name, n.right.accept(self))
        return name

    def visit(self, n: UnaryOper):
        name = self.name
        op_label = f"pre-{n.op}" if isinstance(n, (PreInc, PreDec)) else f"post-{n.op}" if isinstance(n, (PostInc, PostDec)) else n.op
        self.dot.node(name, label=op_label, shape='circle', color='lightcoral')
        self.dot.edge(name, n.expr.accept(self))
        return name

    def visit(self, n: Assignment):
        name = self.name
        self.dot.node(name, label='=', shape='circle', color='lightcoral')
        self.dot.edge(name, n.location.accept(self))
        self.dot.edge(name, n.value.accept(self))
        return name
        
    def visit(self, n: FuncCall):
        name = self.name
        self.dot.node(name, label=f'Call\n{n.name}()')
        for arg in n.args:
            self.dot.edge(name, arg.accept(self), label='arg')
        return name
        
    def visit(self, n: VarLocation):
        name = self.name
        self.dot.node(name, label=f'Var: {n.name}', shape='ellipse')
        return name
        
    def visit(self, n: ArraySubscript):
        name = self.name
        self.dot.node(name, label='[]')
        self.dot.edge(name, n.location.accept(self), label='array')
        self.dot.edge(name, n.index.accept(self), label='index')
        return name

    def visit(self, n: Literal):
        name = self.name
        type_name = n.__class__.__name__
        self.dot.node(name, label=f'{type_name}\n{repr(n.value)}', color='mediumseagreen')
        return name


if __name__ == '__main__':
    import sys
    from parser import parse
    if len(sys.argv) != 2:
        raise SystemExit("Uso: python astprint.py <nombre_archivo.bminor>")
    filepath = sys.argv[1]
    try:
        txt = open(filepath, encoding='utf-8').read()
        ast = parse(txt)
        output_filename = os.path.basename(filepath)
        if ast:
            ASTPrinter.render(ast, filename=output_filename)    
    except FileNotFoundError:
        print(f"[red]Error: Archivo no encontrado '{filepath}'[/red]")