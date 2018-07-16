#!/usr/bin/env python3
import sys

from graphviz import Digraph


class Message(object):
    def __init__(self, name, attrs):
        self.name = name
        self.attrs = attrs


def generate_messages(files):
    attrs = []
    msgs = []
    for f in files:
        for line in open(f, "rt").readlines():
            line = line.rstrip()
            if line.startswith(" * @"):
                attrs.append(line[4:].split(" "))
            elif line.startswith("message "):
                name = line[8:-2]
                msgs.append(Message(name, attrs))
                attrs = []
    return msgs


def generate_graph(msgs, fn):
    dot = Digraph(format="png")
    dot.attr(rankdir="LR")
    for m in msgs:
        typ = m.attrs[0][0]
        if typ == "start":
            dot.node(m.name, shape="box", color="blue")
        elif typ == "end":
            dot.node(m.name, shape="box", color="green3")
        elif typ == "auxstart":
            dot.node(m.name, shape="diamond", color="blue")
        elif typ == "auxend":
            dot.node(m.name, shape="diamond", color="green3")
        elif typ == "next":
            dot.node(m.name)  # no attrs
        elif typ in ["embed", "ignore"]:
            continue
        else:
            raise ValueError("wrong message type in message '%s'" % m.name)
    for m in msgs:
        for a in m.attrs:
            if a[0] == "next":
                dot.edge(m.name, a[1])
    dot.render(fn)


msgs = generate_messages(sys.argv)
generate_graph(msgs, "graph.gv")
