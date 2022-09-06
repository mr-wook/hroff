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
    CAN_RENDER = [ 'directive', 'end', 'directive', 'hroff comment', 'html comment', 'test-start', 'text' ]
    CAN_RENDER_START = [ 'select', 'tdlabel', 'tdselect', 'textarea' ]
    EXTENDED_RENDER = dict(select='option', tdselect='option')
    PREFACES = [ ';', '.', '#', '!', ',', '@' ]
    PARENT_PARTS = re.compile(r'\s*::\s*')
    SLASHED = re.compile(r'\s*//\s*')
    UNTYPE = re.compile(r'^(\.[\w+\.]+)\s+(.*)')
    WORDS = re.compile(r'\s+')

    def __init__(self, ln: str, **kwa: dict) -> None:
        self['line'] = ln
        self['type'] = 'text'
        self.parse(ln)

    @staticmethod
    def atomize(ln: str):
        return WORDS.split(ln)

    def parse(self, ln: AnyStr, **kwa: dict) -> None:
        """Parse an hroff input line into it's critical components"""
        if not ln:
            # self.parse_subterms() # Shouldn't need this call for null lines;
            return
        atoms = self['atoms'] = Components.WORDS.split(ln)
        a0 = atoms[0]
        self['args'] = atoms[1:]

        if a0.startswith('.'):
            self['type'] = 'start'
            self['name'] = atoms[0][1:]
            # if kwa('forgiving', False):
            #   if self.name.endswith('>'): self['name'] = self['name'][:-1]
        if a0.startswith('..'):
            self['type'] = 'end'
            self['name'] = atoms[0][2:]

        self.parse_subterms()
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
        args = self.args
        self['subterms'] = dict(base=args, opts="", children=[])

        # Handle baseline expressions;
        # This isn't handling .select v0=k0 v1=k1 :: x // y // z (which should be obvious from if/elif terms);
        if ( "::" not in args) and ( "//" not in args ): # Does this handle case of non-fields but args for top level?
            return
        elif "::" in args:
            parent_base, kid_base = Components.PARENT_PARTS.split(self.argString, 1)
            opts = " ".join([word for word in Components.WORDS.split(parent_base) if '=' in word])
            self['subterms'] = dict(base=parent_base, opts=opts)
            children = [ ]
            kids = Components.SLASHED.split(kid_base)
            # kid is a string, child is a dict;
            for kid in kids:
                if "::" in kid:
                    child_opt_str, child_arg_str = Components.PARENT_PARTS.split(kid, 1)
                else:
                    child_opt_str, child_arg_str = "", kid
                children.append(dict(base=kid, opts=child_opt_str, args=child_arg_str))
            self['subterms']['children'] = children
            # Evil bit here: Should remove opts from args and '::'
            sep = self['args'].index('::') + 1
            self['args'] = self['args'][sep:]
            return
        else:
            # Need to add children[0] args?
            return
        return

    def render_nested(self, outer_tag: AnyStr) -> List:
        if outer_tag not in Components.EXTENDED_RENDER:
            return [ ] 
        inner_tag = Components.EXTENDED_RENDER[outer_tag]
        olist = [ ]
        subterms = self['subterms']
        olist.append(f"<{outer_tag} {subterms['opts']}>")
        for child in subterms['children']:
            olist.append(f"<{inner_tag} {child['opts']}>{child['args']}</{inner_tag}>")
        olist.append(f"</{outer_tag}>")
        return olist

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
    def end(self):
        return f"</{self.name}>"
    
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
    def render(self) -> AnyStr:
        """Simple Renderer for simple cases"""
        # In over 35 years of OOP, I have never written this function (render), which has appeared as a contrived
        # example in so many texts (even though I'm writing it as a property);
        # Replace the following with match once we are using >=3.10;
        type_ = self.type
        if type_ == 'directive':
            return ""
        if type_ == 'end':
            return f"</{self.name}>"
        if type_ == 'hroff comment':
            return ""
        if type_ == 'html comment':
            return f"<!-- {self.line[1:].strip()} -->"
        if type_ == 'text':
            return self.line
        if type_ == 'start':
            nm = self['name']
            if nm not in Components.CAN_RENDER_START:
                return f'<!-- not in CAN_RENDER_START: {repr(self)} -->'
            if nm == 'select':
                olist = self.render_nested('select')
                return "\n".join(olist)
            if nm == 'tdselect':
                joint = '\n'
                ostr = '\n'.join(self.render_nested('select'))
                s = f"<td>{ostr}</td>"
                return s
            if nm == 'tdlabel':
                s = f"<td>{self.withopts}{self.argString}{self.end}</td>"
                return s
            if nm == 'textarea':
                # <textarea id="w3review" name="w3review" rows="4" cols="50">At w3schools.com you will learn how to make a website. They offer free tutorials in all web development technologies.</textarea>
                s = f'{self.withopts}{self.argString}{self.end}'
                return s

        if type_ == 'test':
            # start_method, *args = self.determine_complexity()
            # rs = start_method(*args) # ie: render_nested(outer, inner)
            # return rs
            if self.name == 'select':
                return self.render_nested('select')
            return ""
        return f"<!-- unsuppored type {type_} -->"

    @property
    def start(self):
        return f"<{self.name}>"
    
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
    SIMPLE_WRAP = [ 'caption', 'h1', 'h2', 'h3', 'h4', 'h5', 'label' ]
    def __init__(self, fn: str, **kwa: dict) -> None:
        self._fn = fn
        HROFFFile.GEN_HANDLERS = dict(title=self._gen_title, css=self._gen_css, 
                                      image=self._gen_image, img=self._gen_img, link=self._gen_link,
                                      tr=self._gen_row, td=self._gen_row_data, th=self._gen_row_header)
        self._header = OrderedDict(title=None, css=[], js=[]) # DO NOT REORDER!
        self._wrapper = [ "<!doctype html>", "</html>" ]
        self._body = [ ]
        self._head = [ ]
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
        self.append(components.start)

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

    def _gen_image(self, components: Components) -> None:
        # Generate an image link from: .link <url>, as opposed to <img param=v param=v...> which would be .img
        url = components.args[-1]
        preopts = components['subterms'].get('opts', "")
        self.append(f'<img {preopts} src="{url}"/>')

    def _gen_img(self, components: Components) -> None:
        components.parse_subterms()
        html = f'<img {" ".join(components.options)}/>'
        self.append(html)

    def _gen_link(self, components: Components) -> None:
        url, *text = components.args # url, text
        text = " ".join(text)
        ostr = f'<a href="{url}">{text}</a>'
        self.append(ostr)

    def _gen_row(self, components: Components) -> None:
        # Sketchy
        # Next add .tr key=val key=val key=val \n .td key=val key=val key=val data_string
        olist = [ components.start ]
        args = components.get('args', None)
        argString = components.argString
        if '//' in argString:
            data_fields = components.fields
            for row_data in data_fields:
                olist.append(f"    <td>{row_data}</td>")
            olist.append(components.end)
        self.append(olist)
        return

    # UNTESTED ****
    def gen_one_or_many(self, components: Components) -> None:
        olist = [ ]
        olist.append(components.withopts)
        for each in components.fields:
            olist.append(each)
        olist.append(components.end)
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
        self.append(f"<{nm}>{argString}</{nm}>")

    def _gen_row_data(self, components: Components) -> None:
        self._gen_encapsulated_entry(components)

    def _gen_row_header(self, components: Components) -> None:
        self._gen_encapsulated_entry(components)

    # def _gen_with_subfields(self, outer_nm: AnyStr, inner_nm: AnyStr, components: Components) -> None:
    def _gen_select(self, components: Components) -> None:
        s = components.render
        return self.append(s)

    def _gen_simple(self, components: Components) -> None:
        nm, options, argString = components.name, " ".join(components.options), " ".join(components.optionless)
        if options:
            if argString:
                ostr = f"{components.withopts} {argString}"
            else:
                ostr = components.withopts
        else:
            if argString:
                ostr = f"<{nm}> {argString}"
            else:
                ostr = components.start
        self.append(ostr)
        return

    if False:
        def _gl(self, components: Components) -> None:
            self._gen_simple_wrap(components)
            return

    def _gen_simple_wrap(self, components: Components) -> None:
        components.parse_subterms()
        ostr = f"{components.withopts}{components.argString}{components.end}"
        self.append(ostr)

    def _gen_pp(self, outer_tag, inner_tag, components):
        base_opts = components['subterms']['base']
        olist = [ f'<{outer_tag}>' ]
        s = f'<{inner_tag} {base_opts}>' if base_opts else f"<{inner_tag}>"
        olist.append(s)
        children = components['subterms']['children']
        children = [ child['base'] for child in children ]
        olist += children
        olist.append(f"</{inner_tag}></td>")
        ostr = "".join(olist)
        pprint(components) ; print(ostr) ; sys.exit(1)
        return self.append(ostr)

    def _gen_td_select(self, components: Components) -> None:
        # selector = self._gen_pp("select", "option", components)
        selector = components.render
        self.append(selector)

    def _gen_td_label(self, components: Components) -> None:
        label = components.render
        self.append(label)
        return
        
        # return self._gen_pp("td", "label", components)
        base_opts = components['subterms']['base']
        olist = [ '<td>' ]
        s = f'<label {base_opts}>' if base_opts else "<label>"
        olist.append(s)
        children = components['subterms']['children']
        children = [ child['base'] for child in children ]
        olist.append(" ".join(children)) # this CANNOT be right...
        olist.append("</label></td>")
        ostr = "".join(olist)
        # pprint(components) ; print(ostr) ; sys.exit(1)
        self.append(ostr)
        return

    if False:
        def _gen_textarea(self, components: Components) -> None:
            textarea = components.render
            self.append(textarea)
            return

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
        test_string = "" # '.select name="select_name" id="select_id" :: Option_1 // Option Two // Option_3'
        if test_string:
            components = Components(test_string)
            components['type'] = 'test'
            pprint(components)
            print(components.render)
            sys.exit(1)
        for ln in self._ibuf:
            components = Components(ln)
            type_ = components.type
            if type_ in Components.CAN_RENDER:
                self.append(components.render)
                continue
            if components.type == 'start':
                self._start_segment(components)
                continue

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
        if name in Components.CAN_RENDER_START:
            self.append(components.render)
            return
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




