#!/bin/env python3
"""
hroff -- a lightweight file to generate HTML for markups, etc.;
"""

if True:
    from   collections import OrderedDict
    import datetime
    import os
    from   pprint import pprint
    import re
    import sys
    from   typing import AnyStr, Dict, List


class Components(dict):
    PREFACES = [ ';', '.', '#', '!', ',' ]
    PARENT_PARTS = re.compile(r'\s*::\s*')
    SLASHED = re.compile(r'\s*//\s*')
    UNTYPE = re.compile(r'^(\.[\w+\.]+)\s+(.*)')
    WORDS = re.compile(r'\s+')

    def __init__(self, ln: str):
        self['line'] = ln
        self['type'] = 'text'
        self.parse(ln)

    @staticmethod
    def atomize(ln: str):
        return WORDS.split(ln)

    def parse(self, ln: AnyStr) -> None:
        """Parse an hroff input line into it's critical components"""
        if not ln:
            return
        atoms = self['atoms'] = Components.WORDS.split(ln)
        a0 = atoms[0]

        if a0.startswith('..'):
            self['type'] = 'end'
            self['name'] = atoms[0][2:]
            self['args'] = atoms[1:]

        if a0.startswith('.'):
            self['type'] = 'start'
            self['name'] = atoms[0][1:]
            self['args'] = atoms[1:]

        if '//' in atoms:
            fields = self['fields'] = Components.SLASHED.split(ln)
            f0 = fields[0]
            mtch = Components.UNTYPE.match(f0)
            if mtch:
                f0 = mtch.groups()[-1]
                fields[0] = f0

        if ln[0] not in Components.PREFACES:
            return

        # WORST PARSER EVER BELOW!
        # All these type strings should be enums tho...
        if self['type'] in [ 'start', 'end' ]:
            return
        elif atoms[0].startswith('!'):
            self['type'] = 'directive'
            self['name'] = atoms[0][1:]
            self['args'] = atoms[1:]
        elif atoms[0].startswith(';'):
            self['type'] = 'hroff comment'
            self['args'] = [ ln[1:] ] # Shouldn't ever be seen, eh?
        elif atoms[0].startswith('#'):
            self['type'] = 'html comment'
            self['args'] = [ ln[1:] ]
        elif atoms[0].startswith(','):
            self['type'] = 'continuation'
            self['args'] = [ ln[1:] ]
        return

    def parse_subterms(self) -> None:
        parent, kids = Components.PARENT_PARTS.split(self.argString, 1)
        parent = dict(base=parent)
        parent['opts'] = " ".join([word for word in Components.WORDS.split(parent['base']) if '=' in word])
        if not '//' in kids:
            return # ?
        parent['children'] = [ ]
        kids = Components.SLASHED.split(kids)
        for kid in kids:
            child = dict(base=kid)
            if '::' in kid:
                child['opts'], child['args'] = Components.PARENT_PARTS.split(kid, 1)
            else:
                child['opts'], child['args'] = "", kid
            parent['children'].append(child)
        self['subterms'] = parent
        # pprint(parent)
        return

    @property
    def args(self) -> List:
        return self.get('args', None)

    @property
    def argString(self) -> AnyStr:
        return " ".join(self.args)

    @property
    def atoms(self) -> List:
        return self.get('atoms', None)

    @property
    def fields(self) -> List:
        return self.get('fields', None)

    @property
    def line(self) -> AnyStr:
        return self.get('line', None)
    
    @property
    def name(self) -> AnyStr:
        return self.get('name', None)

    @property
    def optionless(self) -> List:
        optionless = [ arg for arg in self.args if '=' not in arg ]
        return optionless
    
    @property
    def options(self) -> List:
        options = [ opt for opt in self.args if '=' in opt ]
        return options

    @property
    def type(self) -> AnyStr:
        return self.get('type', None)

    @property
    def withopts(self):
        if not 'subterms' in self:
            self.parse_subterms()
        if self['subterms']['opts']:
            return f"<{self.name} {self['subterms']['opts']}>"
        return f"<{self.name}>"
    
    

class HROFFFile():
    SIMPLE = [ 'table', 'br', 'p', 'div' ]
    SIMPLE_WRAP = [ 'h1', 'h2', 'h3', 'h4', 'h5', 'caption' ]
    def __init__(self, fn: str, **kwa: dict) -> None:
        self._fn = fn
        self._header = OrderedDict(title=None, css=[], js=[]) # DO NOT REORDER!
        self._wrapper = [ "<!doctype html>", "</html>" ]
        self._body = [ ]
        self._head = [ ]
        HROFFFile.GEN_HANDLERS = dict(title=self._gen_title, css=self._gen_css,
                                      tr=self._gen_row, td=self._gen_row_data, th=self._gen_row_header,
                                      select=self._gen_select)
        # Cheap (temporary?) hack
        self._end_segment = self._end_simple
        rc = self._load(fn)
        # self._html = [  ]
        self._ibuf = self._load(fn)
        self._input_len = len(self._ibuf)
        self._indent = 0
        return

    def __len__(self):
        return len(self._html)

    def _add_comment(self, comment: str) -> None:
        self.append(f"<!-- {comment} -->")

    def append(self, s) -> None: # s: AnyStr | s: List ?
        if type(s) == type(""):
            self._body.append(s)
        elif type(s) == type([ ]):
            self._body += s
        elif type(s) == tuple:
            self._body += list(s)
        elif type(s) in [ int, float ]:
            self._body.append(str(s))
        else:
            raise TypeError(f"Type of {type(s)} not supported for append")

    def append_indented(s: str) -> None:
        self._body.append(f"{' ' * self._indent}{s}")

    def _assemble(self) -> List:
        html = [ self._wrapper[0] ]
        hdr = self._header
        output_hdr = [ ]
        keys = list(hdr.keys())
        if any([ hdr[field] for field in keys ]): # Fix this to use a single def of keys;
            output_hdr.insert(0, "<head>")
            for k in keys:
                if hdr[k]:
                    output_hdr.append(self._expand_header(k, hdr))
            output_hdr.append("</head>")
            html += output_hdr
        body = [ "<body>" ] + self._body + [ "</body>" ]
        html +=  body 
        html.append(self._wrapper[-1])
        return html

    def _end_simple(self, components: dict) -> None:
        self.append(f"</{components.name}>")

    def _expand_header(self, k: AnyStr, hdr_dict: Dict) -> AnyStr:
        if k == 'title':
            return f"    <{k}>{hdr_dict[k]}</title>"
        if k == 'css':
            # Need to add support for INLINE operator
            # <link href="css/bootstrap.css" rel="stylesheet">
            output_css = ""
            for css in hdr_dict[k]:
                output_css += f'    <link href="{css}" rel="stylesheet">\n'
                return output_css[:-1]  # Lose last newline;
        return f"<!-- unknown header {k} value {hdr_dict[k]} -->"

    def extend_last(self, s: str) -> None:
        self._body[-1] += s

    def _gen_css(self, components: Components) -> None:
        css_entry = components.argString
        self._header['css'].append(css_entry)

    def _gen_row(self, components: Components) -> None:
        # Sketchy
        # Support .tr data0 // data1 // data2 // data... (initially)
        # Next add .tr key=val key=val key=val data0 // data1 // ...
        # Next add .tr key=val key=val key=val \n .td key=val key=val key=val data_string
        olist = [ "<tr>" ]
        args = components.get('args', None)
        argString = components.argString
        # kv_pairs = [arg for arg in args if '=' in arg]
        # args = [arg for arg in args if '=' not in arg]
        # data_str = " ".join(args)
        if '//' in argString:
            data_fields = components.fields
            for row_data in data_fields:
                olist.append(f"    <td>{row_data}</td>")
            olist.append("</tr>")
        self.append(olist)
        return

    # UNTESTED ****
    def gen_one_or_many(self, components: Components) -> None:
        components.parse_subterms()
        olist = [ ]
        for each in components.fields:
            olist.append(components.withopts)
            olist.append(each)
        olist.append(f"</{components.name}>")
        self.append(olist)

        return

    def gen_row_header(self, components: Components) -> None:
        olist = []
        argString = components.argString
        header_fields = components.fields
        if not argString:
            self.append("<th>")
            return
        if '//' not in argString:
            self.append("<th>")
            return
        for hdr_data in header_fields:
            olist.append(f"<th>{hdr_data}</th>")
        self.append(olist)
        return

    def _gen_encapsulated_entry(self, components: Components) -> None:
        # parse subterms;
        nm, argString, fields = components.name, components.argString, components.fields
        if '//' in argString:
            for field in fields:
                self.append(f"<{nm}>{field}</{nm}>")
            return
        # Add support for // in argString
        # print("components: {components}") ; sys.exit(1)
        self.append(f"<{nm}>{argString}</{nm}>")

    def _gen_row_data(self, components: Components) -> None:
        self._gen_encapsulated_entry(components)

    def _gen_row_header(self, components: Components) -> None:
        self._gen_encapsulated_entry(components)

    # def _gen_with_subfields(self, outer_nm: AnyStr, inner_nm: AnyStr, components: Components) -> None:
    def _gen_select(self, components: Components) -> None:
        """ <select name="live_shpp" id="live_shpp_sel">
              <option value="Baseline">Baseline</option>
              <option value="1.2">1.2<option>
              <option value="1.1">1.1</option>
              <option value="1.0">1</option>
            </select>
        .select [key=val key=val] :: [optkey=val optkey=val] str // [optkey=val optkey=val] str // ...
        """
        components.parse_subterms()
        olist = [ ]
        subterms = components['subterms']
        # pprint(subterms) ; sys.exit(1)
        children = subterms['children']
        opts = subterms['opts'] # nm = components.name; sub_nm (from call params);
        s = f"<select {opts}>" if opts else "<select>" # use <{nm}>
        olist.append(s)
        for child in children:
            child_opts = child['opts']
            label = child['args']
            s = f'<option value="{child_opts}">{label}</option>' # <{sub_nm}...>{label != None}</{sub_nm}>
            olist.append(s)
        olist.append("</select>") # </{nm}>
        self.append(olist)
        # self._add_comment(components.line)
        return

    def _gen_simple(self, components: Components) -> None:
        nm, options, argString = components.name, " ".join(components.options), " ".join(components.optionless)
        if options:
            if argString:
                ostr = f"<{nm} {options}> {argString}"
            else:
                ostr = f"<{nm} {options}>"
        else:
            if argString:
                ostr = f"<{nm}> {argString}"
            else:
                ostr = f"<{nm}>"
        self.append(ostr)
        return

    def _gen_simple_wrap(self, components: Components) -> None:
        nm = components.name
        options = components.options
        s = " ".join(components.optionless)
        if options:
            ostr = f"<{nm} {options}>{s}</{nm}>"
        else:
            ostr = f"<{nm}>{s}</{nm}>"
        self.append(ostr)

    def _gen_title(self, components: Components) -> None:
        self._header['title'] = components.argString

    def _load(self, fn: str) -> str:
        if not os.path.isfile(fn):
            print(f"No such file {fn}")
            return False
        with open(fn, 'r') as ifd:
            ibuf = [ln[:-1] for ln in ifd] # strip EOL BUT NOTHING ELSE!
            ibuf = [ln for ln in ibuf if not ln.startswith(';')]
        return ibuf

    def run(self) -> None:
        for ln in self._ibuf:
            components = Components(ln)
            if components.type == 'hroff comment':
                continue
            if components.type == 'start':
                self._start_segment(components)
                continue
            if components.type == 'end':
                if components.name in HROFFFile.SIMPLE:
                    self._end_simple(components)
                    continue
                self._end_segment(components)
                continue
            if components.type == 'html comment':
                self._add_comment(components.line)
                continue
            if components.type == 'directive':
                self._run_directive(components.line)
                continue
            if components.type == 'continuation':
                self.extend_last(components.args)
                continue
            self._body.append(ln)

    def save(self, fn = None) -> None:
        if not fn:
            prefix, ext = os.path.splitext(self._fn)
            fn = f"{prefix}.html"
        html = self._html = self._assemble()
        ostr = "\n".join(html)
        ofd = open(fn, 'w')
        ofd.write(ostr)
        rc = ofd.close()

    def _start_segment(self, components: Components) -> None:
        name = components.get('name', None)
        if name in HROFFFile.SIMPLE:
            self._gen_simple(components)
            return
        if name in HROFFFile.SIMPLE_WRAP:
            self._gen_simple_wrap(components)
            return
        if name not in HROFFFile.GEN_HANDLERS:
            self._add_comment(f"Unknown command {components.name}: {components.line}")
            return
        HROFFFile.GEN_HANDLERS[name](components)
        return

if __name__ == "__main__":

    pname, *args = sys.argv[:]
    args = list(args)

    if not args:
        print(f"No filename provided on command line")
        sys.exit(1)
    args = list(args)
    ifn = args.pop(0)
    hroff = HROFFFile(ifn)
    hroff.run()
    ofn = None if not args else args.pop(0)
    hroff.save(ofn)
    sys.exit(0)




