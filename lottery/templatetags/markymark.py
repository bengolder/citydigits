# -*- coding: utf-8 -*
import markdown2 as md
from pygments import highlight
from pygments.lexers import PythonLexer, get_lexer_by_name
from pygments.formatters import HtmlFormatter
import string
import cgi
from BeautifulSoup import BeautifulSoup as BeSoup
from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

def code_markup(raw_code, code_type=None, **kwargs):
    """Processes text that is meant as code with pygments. Returns the
    formatted html.
    """
    if not code_type:
        lexer = PythonLexer()
    else:
        lexer = get_lexer_by_name(code_type)()
    processed_code = highlight(raw_code,
            lexer,
            HtmlFormatter(
                #linenos='table',
                #lineanchors='aline',
                #anchorlinenos=True,
                )
            )
    #print HtmlFormatter().get_style_defs('.highlight')
    return processed_code

@register.filter
@stringfilter
def pygmentify(html):
    soup = BeSoup(html, convertEntities=BeSoup.HTML_ENTITIES)
    # get code blocks
    code_bits = soup.findAll('pre')
    for code in code_bits:
        pre = code.contents[0]
        replace_me = ''.join([k.__unicode__() for k in pre.contents])
        code.replaceWith(code_markup(replace_me))
    return soup.__unicode__()

def is_parent(parent_list, element):
    p = element.parent
    if p:
        # look for shit
        if p.name in parent_list:
            return True
        else:
            return is_parent(parent_list, p)
    else:
        return False

def soup_escape(soup, tag='pre'):
    """
    <pre>
        <code>
        blah blah <entity>
        </code>
    </pre>
    """
    codez = soup.findAll(tag)
    for prez in codez:
        codez = prez.contents[0]
        escape_me = ''.join([k.__str__() for k in codez.contents])
        escaped = cgi.escape(escape_me)
        codez.replaceWith('<code>%s</code>' % escaped)
    return soup

@register.filter
@stringfilter
def punctilify(html):
    soup = BeSoup(html, convertEntities=BeSoup.HTML_ENTITIES)
    all_text = soup.findAll(text=True)
    donotwrap = ['pre',]
    for t in all_text:
        if not is_parent(donotwrap, t):
            # replace the punctuation
            t.replaceWith(highlight_punctuation(t.string))
    return soup_escape(soup)

def highlight_punctuation(text):
    new_chars = []
    punct = string.punctuation + u'–—¿¡‘“’”«»…€$£'
    wrap = '<span class="punct">%s</span>'
    for c in text:
        if c in punct:
            new_chars.append(wrap % c)
        else:
            new_chars.append(c)
    return ''.join(new_chars)

def zipchainjoin(iter1, iter2):
    # ['a','b','c'], ['g','h']
    # get the longest length
    count = range(max([len(iter1), len(iter2)]))
    new_list = []
    for i in count:
        try:
            new_list.append(iter1[i])
        except:
            pass
        try:
            new_list.append(iter2[i])
        except:
            pass
    return '\n'.join(new_list)

def is_line_of_code(line, previous_line, previous_is_code):
    """Returns a boolean deciding whether or not a given line is a line of code
    or not.
    """
    has_prefix = (line[:4] == '    ')
    has_code_signal = (line[:3] == '```')
    if not (has_prefix or has_code_signal):
        return False, None
    if has_code_signal: # start or end of code section
        code_type = line[2:].strip() # try to find a code type string
        return True, code_type
    if (has_prefix and previous_is_code):
        return True, None
    previous_empty = (previous_line.strip() == '')
    if (has_prefix and previous_empty):
        return True, None
    return False, None

def chop_out_code(raw_text, **kwargs):
    """This should separate out all the bits of code in the text.
    There are two main cases:
        1. the code is separated from paragraphs by newlines and indented at
        least 4 spaces.
        2. the code is separated from paragraphs by ```/``` possibly including
        a string after the first ``` that designates the code syntax.
    """
    bodystrings = []
    codestrings = []
    code_types = []
    line_buffer = []
    all_lines = raw_text.split('\n')
    was_code = False
    linenos = range(len(all_lines))
    for i in linenos:
        line = all_lines[i]
        if i == 0: # first line
            is_code, code_type = is_line_of_code(line, '', False)
            # this will determine the order of the zipping ...
            code_first = is_code
        else: # not first line
            previous_line = all_lines[i-1]
            is_code, code_type = is_line_of_code(line, previous_line, was_code)
        if is_code != was_code: # we just switched modes
            if is_code: # we switched to code
                code_types.append(code_type)
                if i: # not the first line
                    bodystrings.append('\n'.join(line_buffer))
            else: # we switched to body
                codestrings.append('\n'.join(line_buffer))
            # clear the buffer
            line_buffer = []
        if code_type == None: # If it is not a line with the code signal
            line_buffer.append(line)
        was_code = is_code
    if is_code: # code was last
        codestrings.append('\n'.join(line_buffer))
    else: # body was last
        bodystrings.append('\n'.join(line_buffer))
    code_bits = zip(codestrings, code_types)
    processed_code_strings = [code_markup(c,t) for (c,t) in code_bits]
    #processed_bodystrings = [highlight_punctuation(b) for b in bodystrings]
    if code_first:
        return processed_code_strings, bodystrings
    else:
        return bodystrings, processed_code_strings

@register.filter
@stringfilter
def markymarkup(raw_text):
    # first, separate the code from the other
    marked = md.markdown(raw_text, extras=['smarty-pants', 'wiki-tables'])
    return marked



