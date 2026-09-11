import sly  

class Lexer(sly.Lexer):
    # -------------------------------
    # TOKENS
    # -------------------------------
    tokens = {
        # Palabras Reservadas
        ARRAY, AUTO, BOOLEAN, CHAR, ELSE, FALSE, FLOAT, FOR, FUNCTION,
        IF, INTEGER, PRINT, RETURN, STRING, TRUE, VOID, WHILE, DO,

        # Operadores
        INC, DEC, LOR, LAND, EQ, NE, LE, GE, LT, GT,

        # Otros
        ID, INTEGER_LITERAL, FLOAT_LITERAL, STRING_LITERAL, CHAR_LITERAL,
        ERROR
    }

    # Símbolos literales
    literals = '+-*/%^=()[]{}:;,!'

    # Ignorar espacios y tabulaciones
    ignore = ' \t\r'

    # -------------------------------
    # CONTADOR DE LÍNEAS
    # -------------------------------
    @_(r'\n+')
    def ignore_newline(self, t):
        self.lineno += t.value.count('\n')

    # -------------------------------
    # COMENTARIOS
    # -------------------------------
    @_(r'//.*')
    def ignore_cppcomment(self, t):
        pass

    @_(r'/\*(.|\n)*?\*/')
    def ignore_comment(self, t):
        self.lineno += t.value.count('\n')

    # Comentarios multilínea no cerrados
    @_(r'/\*(.|\n)*')
    def unterminated_comment(self, t):
        t.type = 'ERROR'
        t.value = f"Error Léxico: comentario no cerrado en la línea {self.lineno}."
        self.lineno += t.value.count('\n')
        return t

    # -------------------------------
    # LITERALES NUMÉRICOS
    # -------------------------------
    @_(r'\d*\.\d*\.\d+|\d+(\.\d+){2,}')
    def ERROR_FLOAT(self, t):
        t.type = 'ERROR'
        t.value = f"Error Léxico: Flotante mal formado '{t.value}' en la línea {self.lineno}."
        return t

    @_(r'\d+\.(?!\d)')
    def ERROR_INCOMPLETE_FLOAT(self, t):
        t.type = 'ERROR'
        t.value = f"Error Léxico: Flotante sin parte decimal '{t.value}' en la línea {self.lineno}."
        return t

    # Flotantes (con notación científica opcional)
    @_(r'((\d+\.\d*)|(\.\d+))([eE][-+]?\d+)?|\d+[eE][-+]?\d+')
    def FLOAT_LITERAL(self, t):
        t.value = float(t.value)
        return t

    @_(r'\d+[a-zA-Z_]\w*')
    def INVALID_ID(self, t):
        t.type = 'ERROR'
        t.value = f"Error Léxico: Identificador inválido '{t.value}' en la línea {self.lineno}."
        return t

    @_(r'\d+')
    def INTEGER_LITERAL(self, t):
        t.value = int(t.value)
        return t

    # -------------------------------
    # STRINGS
    # -------------------------------
    @_(r'"([^"\\]|\\.)*"')
    def STRING_LITERAL(self, t):
        original_string = t.value
        s = t.value[1:-1]
        try:
            t.value = s.encode().decode('unicode_escape')
        except UnicodeDecodeError:
            t.type = 'ERROR'
            t.value = f"Error Léxico: Secuencia de escape inválida en {original_string} en la línea {self.lineno}"
            return t

        if len(t.value) > 255:
            t.type = 'ERROR'
            t.value = f"Error Léxico: Cadena demasiado larga en la línea {self.lineno}"
            return t
        return t

    # -------------------------------
    # CARACTERES
    # -------------------------------
    @_(r"'([^'\\]|\\.)?'")
    def CHAR_LITERAL(self, t):
        original_char = t.value
        s = t.value[1:-1]

        if not s:
            t.type = 'ERROR'
            t.value = f"Error Léxico: Carácter vacío en la línea {self.lineno}."
            return t

        try:
            val = s.encode().decode('unicode_escape')
        except UnicodeDecodeError:
            t.type = 'ERROR'
            t.value = f"Error Léxico: Carácter inválido {original_char} en la línea {self.lineno}"
            return t

        if len(val) > 1:
            t.type = 'ERROR'
            t.value = f"Error Léxico: Carácter inválido {original_char} en la línea {self.lineno}"
            return t

        t.value = val
        return t

    # -------------------------------
    # IDENTIFICADORES Y PALABRAS RESERVADAS
    # -------------------------------
    @_(r'[_a-zA-Z]\w*')
    def ID(self, t):
        if len(t.value) > 255:
            t.type = 'ERROR'
            t.value = f"Error Léxico: Identificador demasiado largo en la línea {self.lineno}"
            return t

        keywords = {
            'array': 'ARRAY', 'auto': 'AUTO', 'boolean': 'BOOLEAN', 'char': 'CHAR',
            'else': 'ELSE', 'false': 'FALSE', 'float': 'FLOAT', 'for': 'FOR',
            'function': 'FUNCTION', 'if': 'IF', 'integer': 'INTEGER', 'print': 'PRINT',
            'return': 'RETURN', 'string': 'STRING', 'true': 'TRUE', 'void': 'VOID',
            'while': 'WHILE', 'do': 'DO',
        }
        t.type = keywords.get(t.value, 'ID')
        return t

    # -------------------------------
    # OPERADORES
    # -------------------------------
    INC = r'\+\+'
    DEC = r'--'
    LOR = r'\|\|'
    LAND = r'&&'
    EQ = r'=='
    NE = r'!='
    LE = r'<='
    GE = r'>='
    LT = r'<'
    GT = r'>'

    # -------------------------------
    # ERRORES GENERALES
    # -------------------------------
    def error(self, t):
        bad_char = t.value[0]
        self.index += 1
        return self.token('ERROR', f"Error Léxico: Carácter inválido '{bad_char}' en la línea {self.lineno}")

    # -------------------------------
    # MÉTODO AUXILIAR PARA CREAR TOKENS DE ERROR
    # -------------------------------
    def token(self, type_, value):
        from sly.lex import Token
        tok = Token()
        tok.type = type_
        tok.value = value
        tok.lineno = self.lineno
        tok.index = self.index
        return tok


# -------------------------------
# PRUEBA DE TOKENS
# -------------------------------
def tokenize(txt):
    lexer = Lexer()
    for tok in lexer.tokenize(txt):
        print(tok)
