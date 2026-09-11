# codegen.py
# ----------------------------------------------------------------------
# Generador de Código LLVM para B-Minor 
# Se ejecuta usando el comando --codegen en bminor.py

from llvmlite import ir
from model import *
from model import Visitor

class LLVMCodeGenerator(Visitor):
    '''
    Clase visitante para generar el IR de LLVM.
    Hereda de tu 'model.Visitor'.
    '''
    def __init__(self):
        # Módulo principal de LLVM
        self.module = ir.Module(name='bminor')

        # Definición de tipos LLVM
        self.int_type = ir.IntType(64)      # B-Minor: integer es i64
        self.float_type = ir.DoubleType()   # B-Minor: float es double (IEEE 754)
        self.bool_type = ir.IntType(1)      # B-Minor: boolean es i1
        self.char_type = ir.IntType(8)      # B-Minor: char es i8
        self.string_type = self.char_type.as_pointer()  # B-Minor: string es i8*
        self.void_type = ir.VoidType()

        # Mapa de tipos: de nombre de tipo de bminor (string) a tipo LLVM
        self.typemap = {
            'integer': self.int_type,
            'float': self.float_type,
            'boolean': self.bool_type,
            'char': self.char_type,
            'string': self.string_type,
            'void': self.void_type,
        }

        # --- Tabla de Símbolos de LLVM ---
        # Mapea nombres de variables/funciones a sus punteros/funciones
        self.vars = {}
        self.functions = {}  # Diccionario de funciones LLVM

        # --- Contexto de función actual ---
        self.current_function = None
        self.builder = None

        # --- Contador para strings literales ---
        self.string_counter = 0

        # --- Declarar Funciones de Runtime ---
        self._declare_runtime_functions()

    def _declare_runtime_functions(self):
        """Declara funciones de runtime para print"""
        
        # void _print_integer(i64)
        print_int_type = ir.FunctionType(self.void_type, [self.int_type])
        self._print_integer = ir.Function(self.module, print_int_type, name='_print_integer')
        
        # void _print_float(double)
        print_float_type = ir.FunctionType(self.void_type, [self.float_type])
        self._print_float = ir.Function(self.module, print_float_type, name='_print_float')
        
        # void _print_boolean(i1)
        print_bool_type = ir.FunctionType(self.void_type, [self.bool_type])
        self._print_boolean = ir.Function(self.module, print_bool_type, name='_print_boolean')
        
        # void _print_char(i8)
        print_char_type = ir.FunctionType(self.void_type, [self.char_type])
        self._print_char = ir.Function(self.module, print_char_type, name='_print_char')
        
        # void _print_string(i8*)
        print_string_type = ir.FunctionType(self.void_type, [self.string_type])
        self._print_string = ir.Function(self.module, print_string_type, name='_print_string')

        # Declarar pow() para exponenciación de floats
        # double @llvm.pow.f64(double, double)
        pow_type = ir.FunctionType(self.float_type, [self.float_type, self.float_type])
        self._pow_float = ir.Function(self.module, pow_type, name='llvm.pow.f64')

    # =====================================================================
    # Utilidades de Conversión de Tipos
    # =====================================================================

    def _get_llvm_type(self, bminor_type):
        """Convierte un tipo de B-Minor a tipo LLVM"""
        if isinstance(bminor_type, str):
            return self.typemap.get(bminor_type)
        elif isinstance(bminor_type, ArrayType):
            # Arrays se representan como punteros al tipo de elemento
            element_type = self._get_llvm_type(bminor_type.element_type.name)
            return element_type.as_pointer()
        return None

    def _push_scope(self):
        """Guarda el scope actual de variables (para bloques anidados)"""
        # Crear una copia del diccionario actual
        return dict(self.vars)

    def _pop_scope(self, saved_vars):
        """Restaura el scope anterior"""
        self.vars = saved_vars

    # =====================================================================
    # Nodos de Programa y Bloques
    # =====================================================================

    def visit(self, n: Program):
        '''
        Punto de entrada. Primero declara todas las funciones,
        luego las define.
        '''
        # FASE 1: Declarar todas las funciones (forward declarations)
        for stmt in n.body:
            if isinstance(stmt, FuncDecl):
                self._declare_function(stmt)
        
        # FASE 2: Definir funciones con cuerpo
        for stmt in n.body:
            if isinstance(stmt, FuncDecl):
                if stmt.body:  # Solo si tiene cuerpo
                    self.visit(stmt)
            else:
                pass

    def _declare_function(self, n: FuncDecl):
        """Declara una función (prototipo) sin definir su cuerpo"""
        func_name = n.name
        
        # Obtener tipo de retorno
        return_type = self._get_llvm_type(n.sym_type)
        
        # Obtener tipos de parámetros
        param_types = []
        for param in n.params:
            if isinstance(param.type, SimpleType):
                param_types.append(self._get_llvm_type(param.type.name))
            elif isinstance(param.type, ArrayType):
                # Arrays como parámetros son punteros
                elem_type = self._get_llvm_type(param.type.element_type.name)
                param_types.append(elem_type.as_pointer())
        
        # Crear tipo de función
        func_type = ir.FunctionType(return_type, param_types)
        
        # Crear función en el módulo
        func = ir.Function(self.module, func_type, name=func_name)
        
        # Nombrar los argumentos
        for i, param in enumerate(n.params):
            func.args[i].name = param.name
        
        # Guardar en tabla de funciones
        self.functions[func_name] = func

    def visit(self, n: BlockStmt):
        '''
        Visita una secuencia de sentencias dentro de un bloque.
        '''
        # Guardar scope actual
        saved_vars = self._push_scope()
        
        for stmt in n.statements:
            self.visit(stmt)
        
        # Restaurar scope
        self._pop_scope(saved_vars)

    # =====================================================================
    # Nodos de Declaraciones
    # =====================================================================

    def visit(self, n: VarDecl):
        '''
        Genera código para una declaración de variable.
        '''
        var_name = n.name
        
        # Usar el tipo anotado por el 'checker'
        var_type_bminor = n.sym_type 
        var_type_llvm = self.typemap[var_type_bminor]

        # --- Patrón 'alloca' ---
        # 1. Reservar espacio en el stack (alloca)
        #    'goto_entry_block' se encarga automáticamente de 
        #    posicionar el 'alloca' en el bloque de entrada.   
        with self.builder.goto_entry_block():
            var_ptr = self.builder.alloca(var_type_llvm, name=var_name)
        
        # 2. Guardar el puntero en nuestra tabla de símbolos de LLVM
        self.vars[var_name] = var_ptr

        # 3. Si hay un valor inicial, generar 'store'
        if n.value:
            init_val = self.visit(n.value)
            self.builder.store(init_val, var_ptr)
        else:
            # Inicializar con valor por defecto (0, 0.0, false)
            if var_type_bminor == 'integer':
                default_val = ir.Constant(self.int_type, 0)
            elif var_type_bminor == 'float':
                default_val = ir.Constant(self.float_type, 0.0)
            elif var_type_bminor == 'boolean':
                default_val = ir.Constant(self.bool_type, 0)
            elif var_type_bminor == 'char':
                default_val = ir.Constant(self.char_type, 0)
            else:
                default_val = ir.Constant(var_type_llvm, 0)
            self.builder.store(default_val, var_ptr)

    def visit(self, n: ArrayDecl):
        '''
        Genera código para una declaración de array.
        Ej: arr: array [5] integer;
        '''
        var_name = n.name
        
        # Obtener tipo de elemento
        element_type_llvm = self._get_llvm_type(n.type.element_type.name)
        
        # Evaluar el tamaño (puede ser una expresión)
        if n.type.size:
            size_val = self.visit(n.type.size)
            # Asegurar que es i64
            if size_val.type != self.int_type:
                size_val = self.builder.sext(size_val, self.int_type)
        else:
            # Si no tiene tamaño, es un error (ya debería haber sido detectado por checker)
            size_val = ir.Constant(self.int_type, 0)
        
        # Allocar array en el stack
        with self.builder.goto_entry_block():
            array_ptr = self.builder.alloca(element_type_llvm, size_val, name=var_name)
        
        # Guardar puntero
        self.vars[var_name] = array_ptr
        
        # Inicializar si hay valores
        if n.value:
            for i, val_node in enumerate(n.value):
                val = self.visit(val_node)
                # Calcular puntero al elemento
                idx = ir.Constant(self.int_type, i)
                elem_ptr = self.builder.gep(array_ptr, [idx], inbounds=True)
                self.builder.store(val, elem_ptr)

    def visit(self, n: FuncDecl):
        '''
        Define una función (genera su cuerpo).
        '''
        func_name = n.name
        func = self.functions[func_name]
        
        # Guardar contexto anterior
        old_function = self.current_function
        old_builder = self.builder
        old_vars = self.vars
        
        # Nuevo contexto
        self.current_function = func
        self.vars = {}
        
        # Crear bloque de entrada
        entry_block = func.append_basic_block('entry')
        self.builder = ir.IRBuilder(entry_block)
        
        # Crear allocas para los parámetros y copiar valores
        for i, param in enumerate(n.params):
            param_name = param.name
            
            # Determinar tipo del parámetro
            if isinstance(param.type, SimpleType):
                param_type = self._get_llvm_type(param.type.name)
            elif isinstance(param.type, ArrayType):
                # Arrays como parámetros son punteros
                elem_type = self._get_llvm_type(param.type.element_type.name)
                param_type = elem_type.as_pointer()
            
            # Crear alloca
            param_ptr = self.builder.alloca(param_type, name=param_name)
            self.vars[param_name] = param_ptr
            
            # Copiar argumento al alloca
            self.builder.store(func.args[i], param_ptr)
        
        # Generar cuerpo de la función
        if n.body:
            self.visit(n.body)
        
        # Asegurar que la función termina con return
        if not self.builder.block.is_terminated:
            if n.sym_type == 'void':
                self.builder.ret_void()
            else:
                # Retornar valor por defecto
                return_type = self._get_llvm_type(n.sym_type)
                if n.sym_type == 'integer':
                    self.builder.ret(ir.Constant(return_type, 0))
                elif n.sym_type == 'float':
                    self.builder.ret(ir.Constant(return_type, 0.0))
                elif n.sym_type == 'boolean':
                    self.builder.ret(ir.Constant(return_type, 0))
                elif n.sym_type == 'char':
                    self.builder.ret(ir.Constant(return_type, 0))
        
        # Restaurar contexto
        self.current_function = old_function
        self.builder = old_builder
        self.vars = old_vars

    # =====================================================================
    # Nodos de Sentencias
    # =====================================================================

    def visit(self, n: Assignment):
        '''
        Genera código para una asignación.
        Ej: x = 10;
        '''
        # Visita la parte derecha (RHS) para obtener el valor LLVM
        value_llvm = self.visit(n.value)

        # Para VarLocation
        if isinstance(n.location, VarLocation):
            var_name = n.location.name
            var_ptr = self.vars[var_name]
            self.builder.store(value_llvm, var_ptr)
        
        # Para ArraySubscript
        elif isinstance(n.location, ArraySubscript):
            # Obtener puntero base del array
            base_location = n.location.location
            if isinstance(base_location, VarLocation):
                array_ptr = self.vars[base_location.name]
            else:
                # Arrays anidados: visitar recursivamente
                array_ptr = self.visit(base_location)
            
            # Obtener índice
            index_val = self.visit(n.location.index)
            
            # GEP para obtener puntero al elemento
            elem_ptr = self.builder.gep(array_ptr, [index_val], inbounds=True)
            self.builder.store(value_llvm, elem_ptr)

    def visit(self, n: PrintStmt):
        '''
        Genera código para print.
        Ej: print x, 10, true, "hello";
        '''
        for value_node in n.values:
            # Visita la expresión para obtener el valor LLVM
            value_llvm = self.visit(value_node)
            
            # Lee el tipo anotado por el 'checker'
            node_type = value_node.type 

            # Llama a la función de runtime correcta
            if node_type == 'integer':
                self.builder.call(self._print_integer, [value_llvm])
            elif node_type == 'float':
                self.builder.call(self._print_float, [value_llvm])
            elif node_type == 'boolean':
                self.builder.call(self._print_boolean, [value_llvm])
            elif node_type == 'char':
                self.builder.call(self._print_char, [value_llvm])
            elif node_type == 'string':
                self.builder.call(self._print_string, [value_llvm])

    def visit(self, n: ReturnStmt):
        '''
        Genera código para return.
        '''
        if n.value:
            # Return con valor
            return_val = self.visit(n.value)
            self.builder.ret(return_val)
        else:
            # Return void
            self.builder.ret_void()

    def visit(self, n: IfStmt):
        '''
        Genera código para if/else.
        
        Estructura:
            br cond, then_block, else_block
        then_block:
            ...
            br merge_block
        else_block:
            ...
            br merge_block
        merge_block:
            ...
        '''
        # Evaluar condición
        cond_val = self.visit(n.condition)
        
        # Crear bloques
        then_block = self.current_function.append_basic_block('if.then')
        merge_block = self.current_function.append_basic_block('if.end')
        
        if n.false_body:
            else_block = self.current_function.append_basic_block('if.else')
            self.builder.cbranch(cond_val, then_block, else_block)
        else:
            self.builder.cbranch(cond_val, then_block, merge_block)
        
        # Generar bloque then
        self.builder.position_at_end(then_block)
        self.visit(n.true_body)
        if not self.builder.block.is_terminated:
            self.builder.branch(merge_block)
        
        # Generar bloque else (si existe)
        if n.false_body:
            self.builder.position_at_end(else_block)
            self.visit(n.false_body)
            if not self.builder.block.is_terminated:
                self.builder.branch(merge_block)
        
        # Continuar en merge_block
        self.builder.position_at_end(merge_block)

    def visit(self, n: WhileStmt):
        '''
        Genera código para while.
        
        Estructura:
            br cond_block
        cond_block:
            cond = ...
            br cond, body_block, end_block
        body_block:
            ...
            br cond_block
        end_block:
            ...
        '''
        cond_block = self.current_function.append_basic_block('while.cond')
        body_block = self.current_function.append_basic_block('while.body')
        end_block = self.current_function.append_basic_block('while.end')
        
        # Saltar a evaluar condición
        self.builder.branch(cond_block)
        
        # Generar bloque de condición
        self.builder.position_at_end(cond_block)
        cond_val = self.visit(n.condition)
        self.builder.cbranch(cond_val, body_block, end_block)
        
        # Generar cuerpo
        self.builder.position_at_end(body_block)
        self.visit(n.body)
        if not self.builder.block.is_terminated:
            self.builder.branch(cond_block)
        
        # Continuar después del while
        self.builder.position_at_end(end_block)

    def visit(self, n: DoWhileStmt):
        '''
        Genera código para do-while.
        
        Estructura:
            br body_block
        body_block:
            ...
            br cond_block
        cond_block:
            cond = ...
            br cond, body_block, end_block
        end_block:
            ...
        '''
        body_block = self.current_function.append_basic_block('do.body')
        cond_block = self.current_function.append_basic_block('do.cond')
        end_block = self.current_function.append_basic_block('do.end')
        
        # Saltar al cuerpo
        self.builder.branch(body_block)
        
        # Generar cuerpo
        self.builder.position_at_end(body_block)
        self.visit(n.body)
        if not self.builder.block.is_terminated:
            self.builder.branch(cond_block)
        
        # Generar bloque de condición
        self.builder.position_at_end(cond_block)
        cond_val = self.visit(n.condition)
        self.builder.cbranch(cond_val, body_block, end_block)
        
        # Continuar después del do-while
        self.builder.position_at_end(end_block)

    def visit(self, n: ForStmt):
        '''
        Genera código para for.
        
        for (init; cond; update) body
        
        Estructura:
            init
            br cond_block
        cond_block:
            cond = ...
            br cond, body_block, end_block
        body_block:
            ...
            br update_block
        update_block:
            update
            br cond_block
        end_block:
            ...
        '''
        # Inicialización
        if n.init:
            self.visit(n.init)
        
        cond_block = self.current_function.append_basic_block('for.cond')
        body_block = self.current_function.append_basic_block('for.body')
        update_block = self.current_function.append_basic_block('for.update')
        end_block = self.current_function.append_basic_block('for.end')
        
        # Saltar a condición
        self.builder.branch(cond_block)
        
        # Generar bloque de condición
        self.builder.position_at_end(cond_block)
        if n.condition:
            cond_val = self.visit(n.condition)
            self.builder.cbranch(cond_val, body_block, end_block)
        else:
            # Sin condición = bucle infinito
            self.builder.branch(body_block)
        
        # Generar cuerpo
        self.builder.position_at_end(body_block)
        self.visit(n.body)
        if not self.builder.block.is_terminated:
            self.builder.branch(update_block)
        
        # Generar actualización
        self.builder.position_at_end(update_block)
        if n.update:
            self.visit(n.update)
        self.builder.branch(cond_block)
        
        # Continuar después del for
        self.builder.position_at_end(end_block)

    # =====================================================================
    # Nodos de Expresiones - Literales
    # =====================================================================

    def visit(self, n: Integer):
        '''Genera un literal de entero constante (i64)'''
        return ir.Constant(self.int_type, n.value)

    def visit(self, n: Float):
        '''Genera un literal de float constante (double)'''
        return ir.Constant(self.float_type, n.value)

    def visit(self, n: Boolean):
        '''Genera un literal de booleano constante (i1)'''
        return ir.Constant(self.bool_type, int(n.value))

    def visit(self, n: Char):
        '''Genera un literal de char constante (i8)'''
        return ir.Constant(self.char_type, ord(n.value))

    def visit(self, n: String):
        '''
        Genera un literal de string constante (i8*).
        Crea una variable global para la cadena.
        '''
        # Crear array de bytes con terminador nulo
        string_bytes = bytearray(n.value.encode('utf-8') + b'\x00')
        string_len = len(string_bytes)
        
        # Tipo del array
        string_array_type = ir.ArrayType(self.char_type, string_len)
        
        # Crear variable global
        string_name = f'.str.{self.string_counter}'
        self.string_counter += 1
        
        global_string = ir.GlobalVariable(self.module, string_array_type, name=string_name)
        global_string.linkage = 'internal'
        global_string.global_constant = True
        global_string.initializer = ir.Constant(string_array_type, string_bytes)
        
        # Obtener puntero al primer elemento (i8*)
        zero = ir.Constant(self.int_type, 0)
        string_ptr = self.builder.gep(global_string, [zero, zero], inbounds=True)
        
        return string_ptr

    # =====================================================================
    # Nodos de Expresiones - Variables y Arrays
    # =====================================================================

    def visit(self, n: VarLocation):
        '''
        Genera código para leer (cargar) una variable.
        Es inteligente: si es un array, pasa el puntero;
        si es un tipo simple, carga el valor.
        '''
        var_name = n.name
        var_ptr = self.vars[var_name] 

        # El checker (checker.py) anotó el nodo con su tipo B-Minor.
        # n.type será 'integer', 'float', o una instancia de ArrayType.
        
        # Si el tipo del nodo es ArrayType, estamos pasándolo como argumento.
        if isinstance(n.type, ArrayType):
            
            # Caso 1: Array local (e.g. numeros: array[5] integer)
            # var_ptr es i64* (puntero al primer elemento)
            if isinstance(var_ptr.type.pointee, (ir.IntType, ir.DoubleType, ir.IntType, ir.IntType)):
                return var_ptr # Retorna i64* o double*
            
            # Caso 2: Array como parámetro (e.g. arr: array[] integer)
            # var_ptr es i64** (puntero a un puntero)
            elif isinstance(var_ptr.type.pointee, ir.PointerType):
                return self.builder.load(var_ptr, name=f"{var_name}_ptr") # Carga para obtener i64*

        # Si no es un array, es un tipo simple. Cargar el valor.
        return self.builder.load(var_ptr, name=var_name + "_val")

    def visit(self, n: ArraySubscript):
        '''
        Genera código para acceder a un elemento de array.
        Ej: arr[5]
        '''
        # Obtener puntero base del array
        base_location = n.location
        if isinstance(base_location, VarLocation):
            array_ptr_or_ptr_ptr = self.vars[base_location.name]
        else:
            array_ptr_or_ptr_ptr = self.visit(base_location)
            
        array_ptr = array_ptr_or_ptr_ptr
        if isinstance(array_ptr.type.pointee, ir.PointerType):
            array_ptr = self.builder.load(array_ptr, name="array_ptr")
            
        # Obtener índice
        index_val = self.visit(n.index)
        
        # GEP para obtener puntero al elemento
        elem_ptr = self.builder.gep(array_ptr, [index_val], inbounds=True)
        
        # Cargar valor
        return self.builder.load(elem_ptr, name='array_elem')

    def visit(self, n: FuncCall):
        '''
        Genera código para llamada a función.
        '''
        func_name = n.name
        
        # Obtener función
        if func_name not in self.functions:
            raise RuntimeError(f"Función '{func_name}' no declarada")
        
        func = self.functions[func_name]
        
        # Evaluar argumentos
        args = []
        for arg_node in n.args:
            arg_val = self.visit(arg_node)
            args.append(arg_val)
        
        # Llamar función
        return self.builder.call(func, args, name=f'call_{func_name}')

    # =====================================================================
    # Nodos de Expresiones - Operaciones Binarias
    # =====================================================================

    def visit(self, n: BinOper):
        '''
        Genera código para operaciones binarias.
        Soporta todos los operadores de B-Minor.
        '''
        # Visita recursivamente los hijos
        left_val = self.visit(n.left)
        right_val = self.visit(n.right)

        # Lee el tipo (anotado por el checker)
        op_type = n.left.type
        op = n.op

        # ============ OPERACIONES ARITMÉTICAS ============
        
        if op_type == 'integer':
            # Operaciones aritméticas de enteros
            if op == '+':
                return self.builder.add(left_val, right_val, name='add')
            elif op == '-':
                return self.builder.sub(left_val, right_val, name='sub')
            elif op == '*':
                return self.builder.mul(left_val, right_val, name='mul')
            elif op == '/':
                return self.builder.sdiv(left_val, right_val, name='div')
            elif op == '%':
                return self.builder.srem(left_val, right_val, name='mod')
            elif op == '^':
                # Exponenciación para enteros: convertir a float, pow, convertir de vuelta
                left_float = self.builder.sitofp(left_val, self.float_type)
                right_float = self.builder.sitofp(right_val, self.float_type)
                result_float = self.builder.call(self._pow_float, [left_float, right_float])
                return self.builder.fptosi(result_float, self.int_type, name='pow')
            
            # Comparaciones de enteros (retornan i1)
            elif op == '<':
                return self.builder.icmp_signed('<', left_val, right_val, name='lt')
            elif op == '<=':
                return self.builder.icmp_signed('<=', left_val, right_val, name='le')
            elif op == '>':
                return self.builder.icmp_signed('>', left_val, right_val, name='gt')
            elif op == '>=':
                return self.builder.icmp_signed('>=', left_val, right_val, name='ge')
            elif op == '==':
                return self.builder.icmp_signed('==', left_val, right_val, name='eq')
            elif op == '!=':
                return self.builder.icmp_signed('!=', left_val, right_val, name='ne')
        
        elif op_type == 'float':
            # Operaciones aritméticas de floats
            if op == '+':
                return self.builder.fadd(left_val, right_val, name='fadd')
            elif op == '-':
                return self.builder.fsub(left_val, right_val, name='fsub')
            elif op == '*':
                return self.builder.fmul(left_val, right_val, name='fmul')
            elif op == '/':
                return self.builder.fdiv(left_val, right_val, name='fdiv')
            elif op == '%':
                return self.builder.frem(left_val, right_val, name='fmod')
            elif op == '^':
                # Exponenciación de floats
                return self.builder.call(self._pow_float, [left_val, right_val], name='fpow')
            
            # Comparaciones de floats (retornan i1)
            elif op == '<':
                return self.builder.fcmp_ordered('<', left_val, right_val, name='flt')
            elif op == '<=':
                return self.builder.fcmp_ordered('<=', left_val, right_val, name='fle')
            elif op == '>':
                return self.builder.fcmp_ordered('>', left_val, right_val, name='fgt')
            elif op == '>=':
                return self.builder.fcmp_ordered('>=', left_val, right_val, name='fge')
            elif op == '==':
                return self.builder.fcmp_ordered('==', left_val, right_val, name='feq')
            elif op == '!=':
                return self.builder.fcmp_ordered('!=', left_val, right_val, name='fne')
        
        elif op_type == 'boolean':
            # Operaciones lógicas
            if op == '&&':
                return self.builder.and_(left_val, right_val, name='and')
            elif op == '||':
                return self.builder.or_(left_val, right_val, name='or')
            elif op == '==':
                return self.builder.icmp_signed('==', left_val, right_val, name='beq')
            elif op == '!=':
                return self.builder.icmp_signed('!=', left_val, right_val, name='bne')
        
        elif op_type == 'char':
            # Comparaciones de caracteres
            if op == '<':
                return self.builder.icmp_unsigned('<', left_val, right_val, name='clt')
            elif op == '<=':
                return self.builder.icmp_unsigned('<=', left_val, right_val, name='cle')
            elif op == '>':
                return self.builder.icmp_unsigned('>', left_val, right_val, name='cgt')
            elif op == '>=':
                return self.builder.icmp_unsigned('>=', left_val, right_val, name='cge')
            elif op == '==':
                return self.builder.icmp_unsigned('==', left_val, right_val, name='ceq')
            elif op == '!=':
                return self.builder.icmp_unsigned('!=', left_val, right_val, name='cne')
        
        elif op_type == 'string':
            # Concatenación de strings (requiere función de runtime)
            if op == '+':
                # Aun no implementado
                raise NotImplementedError("Concatenación de strings requiere runtime especial")

        # Si llegamos aquí, operación no soportada
        raise NotImplementedError(f"Operación '{op}' no implementada para tipo '{op_type}'")

    # =====================================================================
    # Nodos de Expresiones - Operaciones Unarias
    # =====================================================================

    def visit(self, n: UnaryOper):
        '''
        Genera código para operaciones unarias.
        Soporta: +, -, !
        '''
        operand_val = self.visit(n.expr)
        operand_type = n.expr.type
        
        if n.op == '-':
            # Negación aritmética
            if operand_type == 'integer':
                zero = ir.Constant(self.int_type, 0)
                return self.builder.sub(zero, operand_val, name='neg')
            elif operand_type == 'float':
                return self.builder.fneg(operand_val, name='fneg')
        
        elif n.op == '+':
            # Unario más (no hace nada)
            return operand_val
        
        elif n.op == '!':
            # Negación lógica (para boolean)
            if operand_type == 'boolean':
                return self.builder.not_(operand_val, name='not')
        
        # Si llegamos aquí, operación no soportada
        raise NotImplementedError(f"Operación unaria '{n.op}' no implementada para tipo '{operand_type}'")

    def visit(self, n: PreInc):
        '''Pre-incremento: ++x'''
        return self._handle_increment_decrement(n, is_pre=True, is_increment=True)
    
    def visit(self, n: PreDec):
        '''Pre-decremento: --x'''
        return self._handle_increment_decrement(n, is_pre=True, is_increment=False)
    
    def visit(self, n: PostInc):
        '''Post-incremento: x++'''
        return self._handle_increment_decrement(n, is_pre=False, is_increment=True)
    
    def visit(self, n: PostDec):
        '''Post-decremento: x--'''
        return self._handle_increment_decrement(n, is_pre=False, is_increment=False)

    def _handle_increment_decrement(self, n, is_pre, is_increment):
        '''
        Maneja ++/-- tanto pre como post.
        Pre: incrementa/decrementa y retorna nuevo valor
        Post: retorna valor actual, luego incrementa/decrementa
        '''
        # Solo funciona con VarLocation
        if not isinstance(n.expr, VarLocation):
            raise NotImplementedError("++/-- solo soportado para variables simples")
        
        var_name = n.expr.name
        var_ptr = self.vars[var_name]
        
        # Cargar valor actual
        current_val = self.builder.load(var_ptr, name=f'{var_name}_val')
        
        # Calcular nuevo valor
        var_type = n.expr.type
        if var_type == 'integer':
            one = ir.Constant(self.int_type, 1)
            if is_increment:
                new_val = self.builder.add(current_val, one, name='inc')
            else:
                new_val = self.builder.sub(current_val, one, name='dec')
        elif var_type == 'float':
            one = ir.Constant(self.float_type, 1.0)
            if is_increment:
                new_val = self.builder.fadd(current_val, one, name='finc')
            else:
                new_val = self.builder.fsub(current_val, one, name='fdec')
        else:
            raise NotImplementedError(f"++/-- no soportado para tipo '{var_type}'")
        
        # Almacenar nuevo valor
        self.builder.store(new_val, var_ptr)
        
        # Retornar según pre/post
        return new_val if is_pre else current_val
    
def generate_code(ast):
    '''
    Genera código LLVM IR desde un AST de B-Minor.
    
    Args:
        ast: Nodo Program del AST (ya verificado por checker)
    
    Returns:
        str: Código LLVM IR como string
    '''
    generator = LLVMCodeGenerator()
    generator.visit(ast)
    return str(generator.module)