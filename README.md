# hroff
runoff-style to html

HTML (and most markup languages) require highly verbose boilerplate.  This is annoying, and typos cost a lot during the debug cycle.

I (meaning me) need to quickly generate HTML mockups/wireframes/etc. and don't want to screw around forever indenting, matching angle brackets, etc.;

hroff takes an exceedingly simple runoff (troff, etc.) style input and outputs HTML, ie:
~~~
; <comment> -- Doesn't appear in html
!<hroff-directive> <args> -- include <file>, css <file> [inline], js <file> [inline]
@<varname> [expression]
.<section type> <string> -- start a section, ie: <p>, <div>, etc.;
..<section type> -- end a section, ie: </p>, </div>
#<emitted html comment> <text>
~~~

Normally, the doctype, head, body, and html sections are emitted.

The command line syntax looks like:
~~~
% hroff <input-file> [<output-file>]
~~~
