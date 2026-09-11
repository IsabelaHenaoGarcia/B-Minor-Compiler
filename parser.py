# parser.py
import logging
import sly
from rich import print

from bminor_lexer import Lexer
from errors import error, errors_detected
from model import *

def _L(node, lineno):
    if node:
        node.lineno = lineno
    return node

class Parser(sly.Parser):
    log = logging.getLogger()
    log.setLevel(logging.ERROR)
    debugfile = 'parser.log'

    tokens = Lexer.tokens

    # parser.py
    @_("opt_stmt_list")
    def prog(self, p):
        return Program(p.opt_stmt_list)

    @_("decl decl_list")
    def decl_list(self, p):
        return [p.decl] + p.decl_list if p.decl else p.decl_list
    @_("empty")
    def decl_list(self, p):
        return []

    # Declaraciones
    @_("ID ':' type_simple ';'")
    def decl(self, p):
        return _L(VarDecl(p.ID, p.type_simple), p.lineno)
    @_("ID ':' type_array_sized ';'")
    def decl(self, p):
        return _L(ArrayDecl(p.ID, p.type_array_sized), p.lineno)

    @_("ID ':' type_func ';'")
    def decl(self, p):
        func_decl = p.type_func
        func_decl.name = p.ID
        return _L(func_decl, p.lineno)

    @_("decl_init")
    def decl(self, p):
        return p.decl_init
    
    # Declaraciones con Inicialización
    @_("ID ':' type_simple '=' expr ';'")
    def decl_init(self, p):
        return _L(VarDecl(p.ID, p.type_simple, p.expr), p.lineno)
    @_("ID ':' type_array_sized '=' '{' opt_expr_list '}' ';'")
    def decl_init(self, p):
        return _L(ArrayDecl(p.ID, p.type_array_sized, value=p.opt_expr_list), p.lineno)

    @_("ID ':' type_func '=' '{' opt_stmt_list '}'")
    def decl_init(self, p):
        func_decl = p.type_func
        func_decl.name = p.ID
        func_decl.body = _L(BlockStmt(p.opt_stmt_list), p.lineno)
        return _L(func_decl, p.lineno)

    # Sentencias
    @_("stmt_list")
    def opt_stmt_list(self, p):
        return p.stmt_list
    @_("empty")
    def opt_stmt_list(self, p):
        return []

    @_("stmt stmt_list")
    def stmt_list(self, p):
        return [p.stmt] + p.stmt_list
    @_("stmt")
    def stmt_list(self, p):
        return [p.stmt]

    @_("open_stmt", "closed_stmt")
    def stmt(self, p):
        return p[0]
    @_("WHILE '(' expr ')' stmt")
    def stmt(self, p):
        return _L(WhileStmt(p.expr, p.stmt), p.lineno)
    @_("DO stmt WHILE '(' expr ')' ';'")
    def stmt(self, p):
        return _L(DoWhileStmt(p.stmt, p.expr), p.lineno)

    @_("if_stmt_closed", "for_stmt_closed", "simple_stmt")
    def closed_stmt(self, p):
        return p[0]
    @_("if_stmt_open", "for_stmt_open")
    def open_stmt(self, p):
        return p[0]

    @_("IF '(' expr ')' closed_stmt ELSE closed_stmt")
    def if_stmt_closed(self, p):
        return _L(IfStmt(p.expr, p.closed_stmt0, p.closed_stmt1), p.lineno)
    @_("IF '(' expr ')' stmt")
    def if_stmt_open(self, p):
        return _L(IfStmt(p.expr, p.stmt), p.lineno)
    @_("IF '(' expr ')' closed_stmt ELSE open_stmt")
    def if_stmt_open(self, p):
        return _L(IfStmt(p.expr, p.closed_stmt, p.open_stmt), p.lineno)

    @_("FOR '(' opt_expr ';' opt_expr ';' opt_expr ')' open_stmt")
    def for_stmt_open(self, p):
        return _L(ForStmt(p.opt_expr0, p.opt_expr1, p.opt_expr2, p.open_stmt), p.lineno)
    @_("FOR '(' opt_expr ';' opt_expr ';' opt_expr ')' closed_stmt")
    def for_stmt_closed(self, p):
        return _L(ForStmt(p.opt_expr0, p.opt_expr1, p.opt_expr2, p.closed_stmt), p.lineno)

    @_("print_stmt", "return_stmt", "block_stmt", "decl", "expr ';'")
    def simple_stmt(self, p):
        return p[0]
    @_("PRINT expr_list ';'")
    def print_stmt(self, p):
        return _L(PrintStmt(p.expr_list), p.lineno)
    @_("RETURN expr ';'")
    def return_stmt(self, p):
        return _L(ReturnStmt(p.expr), p.lineno)
    @_("RETURN ';'")
    def return_stmt(self, p):
        return _L(ReturnStmt(), p.lineno)
    @_("'{' opt_stmt_list '}'")
    def block_stmt(self, p):
        return _L(BlockStmt(p.opt_stmt_list), p.lineno)

    # Expresiones (Reglas de precedencia)
    @_("expr1")
    def expr(self, p): return p.expr1
    @_("lval '=' expr1")
    def expr1(self, p): return _L(Assignment(p.lval, p.expr1), p.lineno)
    @_("expr2")
    def expr1(self, p): return p.expr2
    @_("expr2 LOR expr3")
    def expr2(self, p): return _L(BinOper('||', p.expr2, p.expr3), p.lineno)
    @_("expr3")
    def expr2(self, p): return p.expr3
    @_("expr3 LAND expr4")
    def expr3(self, p): return _L(BinOper('&&', p.expr3, p.expr4), p.lineno)
    @_("expr4")
    def expr3(self, p): return p.expr4
    @_("expr4 EQ expr5", "expr4 NE expr5", "expr4 LT expr5", "expr4 LE expr5", "expr4 GT expr5", "expr4 GE expr5")
    def expr4(self, p): return _L(BinOper(p[1], p.expr4, p.expr5), p.lineno)
    @_("expr5")
    def expr4(self, p): return p.expr5
    @_("expr5 '+' expr6", "expr5 '-' expr6")
    def expr5(self, p): return _L(BinOper(p[1], p.expr5, p.expr6), p.lineno)
    @_("expr6")
    def expr5(self, p): return p.expr6
    @_("expr6 '*' expr7", "expr6 '/' expr7", "expr6 '%' expr7")
    def expr6(self, p): return _L(BinOper(p[1], p.expr6, p.expr7), p.lineno)
    @_("expr7")
    def expr6(self, p): return p.expr7
    @_("expr7 '^' expr8")
    def expr7(self, p): return _L(BinOper('^', p.expr7, p.expr8), p.lineno)
    @_("expr8")
    def expr7(self, p): return p.expr8
    
    # Expresiones Unarias y de Incremento/Decremento
    @_("'-' expr8", "'!' expr8")
    def expr8(self, p): return _L(UnaryOper(p.expr8, p[0]), p.lineno)
    @_("INC expr9")
    def expr8(self, p): return _L(PreInc(expr=p.expr9), p.lineno)
    @_("DEC expr9")
    def expr8(self, p): return _L(PreDec(expr=p.expr9), p.lineno)
    @_("expr9")
    def expr8(self, p): return p.expr9
    @_("expr9 INC")
    def expr9(self, p): return _L(PostInc(expr=p.expr9), p.lineno)
    @_("expr9 DEC")
    def expr9(self, p): return _L(PostDec(expr=p.expr9), p.lineno)
    @_("group")
    def expr9(self, p): return p.group

    # Expresiones Agrupadas y Factores
    @_("'(' expr ')'")
    def group(self, p): return p.expr
    @_("ID '(' opt_expr_list ')'")
    def group(self, p): return _L(FuncCall(p.ID, p.opt_expr_list), p.lineno)
    @_("lval")
    def group(self, p): return p.lval
    @_("factor")
    def group(self, p): return p.factor

    @_("ID")
    def lval(self, p): return _L(VarLocation(p.ID), p.lineno)
    @_("lval '[' expr ']'")
    def lval(self, p): return _L(ArraySubscript(p.lval, p.expr), p.lineno)

    @_("INTEGER_LITERAL")
    def factor(self, p): return _L(Integer(p[0]), p.lineno)
    @_("FLOAT_LITERAL")
    def factor(self, p): return _L(Float(p[0]), p.lineno)
    @_("CHAR_LITERAL")
    def factor(self, p): return _L(Char(p[0]), p.lineno)
    @_("STRING_LITERAL")
    def factor(self, p): return _L(String(p[0]), p.lineno)
    @_("TRUE")
    def factor(self, p): return _L(Boolean(True), p.lineno)
    @_("FALSE")
    def factor(self, p): return _L(Boolean(False), p.lineno)

    # Listas
    @_("expr_list")
    def opt_expr_list(self, p): return p.expr_list
    @_("empty")
    def opt_expr_list(self, p): return []
    @_("expr ',' expr_list")
    def expr_list(self, p): return [p.expr] + p.expr_list
    @_("expr")
    def expr_list(self, p): return [p.expr]

    @_("param_list")
    def opt_param_list(self, p): return p.param_list
    @_("empty")
    def opt_param_list(self, p): return []
    @_("param_list ',' param")
    def param_list(self, p): return p.param_list + [p.param]
    @_("param")
    def param_list(self, p): return [p.param]
    @_("ID ':' type_simple")
    def param(self, p): return _L(Param(p.ID, p.type_simple), p.lineno)
    @_("ID ':' type_array")
    def param(self, p): return _L(Param(p.ID, p.type_array), p.lineno)
    @_("ID ':' type_array_sized")
    def param(self, p): return _L(Param(p.ID, p.type_array_sized), p.lineno)

    # Tipos
    @_("INTEGER", "FLOAT", "BOOLEAN", "CHAR", "STRING", "VOID")
    def type_simple(self, p): 
        return _L(SimpleType(p[0]), p.lineno)
    
    @_("ARRAY '[' ']' type_simple")
    def type_array(self, p): 
        return _L(ArrayType(p.type_simple), p.lineno)
    
    @_("ARRAY '[' expr ']' type_simple")
    def type_array_sized(self, p): 
        return _L(ArrayType(p.type_simple, p.expr), p.lineno)
    
    # Regla nueva: Arrays anidados con tamaño
    @_("ARRAY '[' expr ']' type_array_sized")
    def type_array_sized(self, p):
        return _L(ArrayType(p.type_array_sized, p.expr), p.lineno)
    
    @_("FUNCTION type_simple '(' opt_param_list ')'")
    def type_func(self, p):
        return FuncDecl(name=None, type=p.type_simple, params=p.opt_param_list)

    @_("empty")
    def opt_expr(self, p): return None
    @_("expr")
    def opt_expr(self, p): return p.expr
    @_("")
    def empty(self, p): pass

    def error(self, p):
        if p:
            error(f"Error de sintaxis en '{p.value}'", p.lineno)
        else:
            error("Error de sintaxis al final del archivo (EOF)")

def parse(txt):
    l = Lexer()
    p = Parser()
    return p.parse(l.tokenize(txt))