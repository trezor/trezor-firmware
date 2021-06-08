#!/usr/bin/env python3
import json
import sys


if len(sys.argv) < 2:
    print("""\
USAGE: ./analyze-memory-dump.py somefile.json

Where "somefile.json" was produced by using `trezor.utils.mem_dump("somefile.json")`
somewhere in emulator source code.

Outputs a memory dump similar to `micropython.mem_info(True)`, except with complete
(hopefully :) ) understanding of concrete objects at given memory addresses. Also
outputs `memorymap.html`, which is a clickable memory dump with cross-references
between the objects, for detailed examination of what is going on.

The "inferred name" feature works by looking up the closest dict containing the object
as a value, with a string key. This sometimes works amazingly and sometimes not so much.

Certain kinds of objects have a separately allocated storage space. Such storage space
is given an "owner" backreference that will point you back to the object that you
actually care about.

Modules are nothing but a link to a globals dict. The dict must be examined separately.

Generators and closures are painful :(
""")



with open(sys.argv[1]) as f:
    MEMMAP = json.load(f)


# filter out notices and comments
MEMMAP = [m for m in MEMMAP if isinstance(m, dict)]

MEMORY = {}


def is_ptr(maybe_ptr):
    return isinstance(maybe_ptr, str) and maybe_ptr.startswith("0x")


def is_gc_ptr(maybe_ptr):
    return is_ptr(maybe_ptr) and maybe_ptr.startswith("0x7f")


def ptr_or_shortval(maybe_ptr):
    if is_ptr(maybe_ptr):
        return maybe_ptr
    else:
        assert isinstance(maybe_ptr, dict), f"maybe_ptr is {type(maybe_ptr)}"
        assert "shortval" in maybe_ptr, f"maybe_ptr does not have shortval: {maybe_ptr}"
        return maybe_ptr["shortval"]


def is_ignored_ptr(ptr):
    return (ptr == "(nil)" or ptr.startswith("0x5") or ptr.startswith("0x6"))


def deref_or_shortval(maybe_ptr):
    if is_ptr(maybe_ptr) and maybe_ptr in MEMORY:
        return MEMORY[maybe_ptr]
    else:
        return ptr_or_shortval(maybe_ptr)


class Item:
    def __init__(self, item):
        self.item = item
        self.backlinks = []
        self.dict = {}
        self.visited = False
        self.type = item["type"]
        self.ptr = item["ptr"]

    def backlinkify(self):
        if "children" in self.item:
            for child in self.item["children"]:
                key_str = ptr_or_shortval(child["key"])
                value_deref = deref_or_shortval(child["value"])
                self.dict[key_str] = value_deref

        for ptr in self.find_pointers():
            if ptr not in MEMORY:
                continue
            MEMORY[ptr].backlinks.append(self)

    def find_pointers(self):
        if "children" in self.item:
            for child in self.item["children"]:
                if is_ptr(child["key"]):
                    yield child["key"]
                if is_ptr(child["value"]):
                    yield child["value"]

        for k, v in self.item.items():
            if k in ("ptr", "owner", "children"):
                continue
            if not v:
                continue
            if isinstance(v, list):
                yield from (p for p in v if is_ptr(p))
            if is_ptr(v):
                yield v

    def __getattr__(self, key):
        if key not in self.item:
            raise AttributeError
        return self.item[key]

    def find_modules(self):
        return [it for it in self.backlinks if it.type == "module"]

    def name(self):
        if "__name__" in self.dict:
            return self.dict["__name__"]

        if "__qualname__" in self.dict:
            return self.dict["__module__"] + "::" + self.dict["__qualname__"]

        if self.type == "type":
            return MEMORY[self.item["locals"]].name()

        if self.type == "instance":
            return MEMORY[self.item["base"]].name() + "()"

        if self.type == "module":
            return MEMORY[self.item["globals"]].name()

        if self.type == "generator":
            return MEMORY[self.item["function"]].name()

        for item in self.backlinks:
            if item.type == "dict":
                for k, v in item.dict.items():
                    if v == self:
                        return k

        return None

    def ptrval(self):
        return int(self.ptr[2:], 16)


for item_data in MEMMAP:
    item = Item(item_data)
    MEMORY[item.ptr] = item

for item in MEMORY.values():
    item.backlinkify()


allobjs = list(MEMORY.values())
allobjs.sort(key=lambda x: x.ptr)
min_ptr = min(
    item.ptrval()
    for item in allobjs
    if not is_ignored_ptr(item.ptr)
)
max_ptr = max(item.ptrval() for item in allobjs if item.ptr != "(nil)")


types = {
    "anystr": "S",
    "strdata": "s",
    "array": "A",
    "arrayitems": "a",
    "closure": "c",
    "dict": "D",
    "function": "B",
    "generator": "G",
    "instance": "I",
    "list": "L",
    "listitems": "l",
    "mapitems": "m",
    "method": "C",
    "module": "M",
    "object": "o",
    "set": "E",
    "setitems": "e",
    "staticmethod": "C",
    "trezor": "t",
    "tuple": "T",
    "type": "y",
    "unknown": "h",
    "trezor-webusb": "t",
    "trezor-vcp": "t",
    "trezor-hid": "t",
    "rawbuffer": "R",
    "qstrpool": "Q",
    "qstrdata": "q",
    "protomsg": "P",
    "protodef": "p",
    "uilayout": "U",
    "uilayoutinner": "u",
}

pixels_per_line = len(
    "................................................................"
)
pixelsize = 0x800 // pixels_per_line
maxline = ((max_ptr - min_ptr) & ~0x7FF) + (0x800 * 2)
pixelmap = [None] * (maxline // pixelsize)


def pixel_index(ptrval):
    ptridx = ptrval - min_ptr
    # assert ptridx >= 0
    return ptridx // pixelsize


for item in MEMORY.values():
    if item.alloc == 0:
        continue
    if is_ignored_ptr(item.ptr):
        continue
    ptridx = pixel_index(item.ptrval())
    assert ptridx >= 0, item.item
    for i in range(ptridx, ptridx + item.alloc):
        pixelmap[i] = item

for item in MEMORY.values():
    if item.alloc > 0:
        continue
    if is_ignored_ptr(item.ptr):
        continue
    ptridx = pixel_index(item.ptrval())
    if ptridx < 0:
        continue
    for i in range(ptridx, ptridx + item.alloc):
        pixelmap[i] = item

ctr = 0
newline = True
previtem = None
for pixel in pixelmap:
    if ctr % pixels_per_line == 0:
        print()
        print(f"{ctr * pixelsize:05x}: ", end="")
    if pixel is None:
        c = "."
    elif pixel is previtem:
        c = "="
    else:
        c = types[pixel.type]
    print(c, end="")
    ctr += 1
    previtem = pixel
print()


import dominate
import dominate.tags as t

doc = dominate.document(title="memory map")
with doc.head:
    t.meta(charset="utf-8")
    t.style(
        """\
span, a {
    font-family: monospace;
    color: black;
    text-decoration: none;
    margin: 0;
}

a {
    color: darkblue;
}

.entry a:target {
    display: block;
    background-color: navy;
}

#memorymap a:target {
    color: red;
}

span.leadin {
    margin-right: 1rem;
}

dl { border-left: 1px solid grey; padding-left: 0.4rem; }
dt { font-weight: bold }

div.
"""
    )

ctr = 0
newline = True
previtem = None
container = t.div(id="memorymap")
doc.add(container)
line = t.div()
for pixel in pixelmap:
    if ctr % pixels_per_line == 0:
        container.add(line)
        line = t.div()
        line.add(t.span(f"{ctr * pixelsize:05x}: ", cls="leadin"))
    if pixel is None:
        line.add(t.span("."))
    elif pixel is previtem:
        line.add(t.a("=", href=f"#{pixel.ptr}"))
    else:
        c = types[pixel.type]
        line.add(t.a(c, href=f"#{pixel.ptr}", name=f"mapentry-{pixel.ptr}"))
    ctr += 1
    previtem = pixel


def text_or_ptr(s):
    if s.startswith("0x7"):
        sp = t.span()
        sp.add(t.a(s, href=f"#{s}"))
        sp.add(" (")
        sp.add(t.a("M", href=f"#mapentry-{s}"))
        sp.add(")")
        return sp
    else:
        return t.span(s)


def dump_single_val(value):
    if isinstance(value, str):
        return text_or_ptr(value)
    elif isinstance(value, dict):
        if value.get("shortval"):
            return value["shortval"]
        elif value.get("type") == "romdata":
            return "romdata"
        sdl = t.dl()
        dump_dict(sdl, value)
        return sdl
    elif isinstance(value, list):
        ul = t.ul()
        for subval in value:
            ul.add(t.li(dump_single_val(subval)))
        return ul
    else:
        return str(value)


def dump_dict(dl, d):
    for key, value in d.items():
        dl.add(t.dt(key))
        dl.add(t.dd(dump_single_val(value)))


for item in allobjs:
    div = t.div(cls="entry")
    div.add(t.a("{", name=item.ptr))
    dl = t.dl()
    dl.add(t.dt("Inferred name:"))
    dl.add(t.dd(str(item.name())))
    dl.add(t.dt("Backrefs:"))
    refs = t.dd()
    for backref in item.backlinks:
        refs.add(text_or_ptr(backref.ptr))
        refs.add(", ")
    dl.add(refs)
    dump_dict(dl, item.item)
    div.add(dl)
    doc.add(div)

print("Writing to memorymap.html...")
with open("memorymap.html", "w") as f:
    f.write(doc.render(pretty=False))
