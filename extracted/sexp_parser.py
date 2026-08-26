#!/usr/bin/env python3
"""Minimal S-expression parser for reading back our own .kicad_sch/.kicad_pcb
output during the review pass -- deliberately independent of the generator
scripts, so bugs in generation aren't hidden by reusing the same code path."""

def tokenize(text):
    tokens = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in " \t\r\n":
            i += 1
        elif c == "(":
            tokens.append("(")
            i += 1
        elif c == ")":
            tokens.append(")")
            i += 1
        elif c == '"':
            j = i + 1
            buf = []
            while j < n and text[j] != '"':
                if text[j] == "\\" and j + 1 < n:
                    buf.append(text[j + 1])
                    j += 2
                else:
                    buf.append(text[j])
                    j += 1
            tokens.append(("str", "".join(buf)))
            i = j + 1
        else:
            j = i
            while j < n and text[j] not in " \t\r\n()":
                j += 1
            tokens.append(("atom", text[i:j]))
            i = j
    return tokens

def parse(text):
    tokens = tokenize(text)
    pos = [0]
    def parse_expr():
        tok = tokens[pos[0]]
        if tok == "(":
            pos[0] += 1
            items = []
            while tokens[pos[0]] != ")":
                items.append(parse_expr())
            pos[0] += 1
            return items
        else:
            pos[0] += 1
            if isinstance(tok, tuple):
                return tok[1]
            return tok
    exprs = []
    while pos[0] < len(tokens):
        exprs.append(parse_expr())
    return exprs

def find_all(node, tag):
    """Recursively find all list nodes whose first element == tag."""
    out = []
    if isinstance(node, list):
        if node and node[0] == tag:
            out.append(node)
        for child in node:
            out.extend(find_all(child, tag))
    return out

def get(node, tag, default=None):
    """First immediate-child list starting with tag, or default."""
    if not isinstance(node, list):
        return default
    for child in node:
        if isinstance(child, list) and child and child[0] == tag:
            return child
    return default

def get_all_immediate(node, tag):
    return [c for c in node if isinstance(c, list) and c and c[0] == tag]
