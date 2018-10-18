#!/usr/bin/env python3
import sys
from os.path import basename

from graphviz import Digraph


class Message(object):
    def __init__(self, fname, name, attrs):
        self.fname = basename(fname)
        self.name = name
        if len(attrs) == 0:
            raise ValueError("message '%s' has no attributes" % name)
        t = attrs[0][0]
        if t in ["start", "end", "auxstart", "auxend", "embed", "ignore"]:
            self.typ = t
            attrs = attrs[1:]
        elif t == "next":
            self.typ = "normal"
            attrs = attrs
        else:
            raise ValueError("wrong message type in message '%s'" % name)
        self.next = []
        for a in attrs:
            if a[0] == "next":
                self.next.append(a[1])

    def __repr__(self):
        return '%s(type=%s, fname="%s", next=%s)' % (
            self.name,
            self.typ,
            self.fname,
            self.next,
        )


def generate_messages(files):
    attrs = []
    msgs = {}
    for f in files:
        for line in open(f, "rt").readlines():
            line = line.rstrip()
            if line.startswith(" * @"):
                attrs.append(line[4:].split(" "))
            elif line.startswith("message "):
                name = line[8:-2]
                msgs[name] = Message(f, name, attrs)
                attrs = []
    return msgs


def generate_graph(msgs, fn):
    dot = Digraph()
    dot.attr(rankdir="LR")
    for m in msgs.values():
        if m.typ == "start":
            dot.node(m.name, shape="box", color="blue")
        elif m.typ == "end":
            dot.node(m.name, shape="box", color="green3")
        elif m.typ == "auxstart":
            dot.node(m.name, shape="diamond", color="blue")
        elif m.typ == "auxend":
            dot.node(m.name, shape="diamond", color="green3")
        elif m.typ == "normal":
            dot.node(m.name)

    for m in msgs.values():
        for n in m.next:
            dot.edge(m.name, n)
    dot.render(fn)


def main():
    proto_files = sys.argv

    msgs = generate_messages(proto_files)
    generate_graph(msgs, "proto.gv")


if __name__ == "__main__":
    main()
