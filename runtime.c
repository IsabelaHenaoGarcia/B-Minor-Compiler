#include <stdio.h>
#include <stdbool.h>

// Funciones de runtime para print
void _print_integer(long long x) {
    printf("%lld", x);
}

void _print_float(double x) {
    printf("%g", x);
}

void _print_boolean(bool x) {
    printf("%s", x ? "true" : "false");
}

void _print_char(char x) {
    printf("%c", x);
}

void _print_string(const char* x) {
    printf("%s", x);
}
