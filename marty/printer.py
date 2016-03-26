import sys
import subprocess
import tempfile


DEFAULT_TAGS = {'b': (lambda **attrs: '\x1b[1m',
                      lambda: '\x1b[21m'),
                'inv': (lambda **attrs: '\x1b[37;7m',
                        lambda: '\x1b[27;39m'),
                'dim': (lambda **attrs: '\x1b[2m',
                        lambda: '\x1b[22m'),
                'u': (lambda **attrs: '\x1b[4m',
                      lambda: '\x1b[24m'),
                '_reset': (None, lambda: '\x1b[0m')}


class ColorHandler(object):

    COLOR_CODE = '\x1b[%dm'
    COLOR_RESET_FG = 39
    COLOR_RESET_BG = 49

    COLORS = {'black': (30, 40),
              'red': (31, 41),
              'green': (32, 42),
              'yellow': (33, 43),
              'blue': (34, 44),
              'magenta': (35, 45),
              'cyan': (36, 46),
              'light_gray': (37, 47),
              'dark_gray': (90, 100),
              'light_red': (91, 101),
              'light_green': (92, 102),
              'light_yellow': (93, 103),
              'light_blue': (94, 104),
              'light_magenta': (95, 105),
              'light_cyan': (96, 106),
              'white': (97, 107)}

    def __init__(self):
        self._last_colors = []

    def open(self, **attrs):
        fg = self.COLORS.get(attrs.get('fg'), [None, None])[0]
        bg = self.COLORS.get(attrs.get('bg'), [None, None])[1]
        self._last_colors.append((fg, bg))
        output = ''
        if fg is not None:
            output += self.COLOR_CODE % fg
        if bg is not None:
            output += self.COLOR_CODE % bg
        return output

    def close(self):
        if self._last_colors:
            self._last_colors.pop()  # Remove colors from our opening tag
            if self._last_colors:
                last_fg, last_bg = self._last_colors[-1]
            else:
                last_fg, last_bg = [None, None]
            if last_fg is None:
                last_fg = self.COLOR_RESET_FG
            if last_bg is None:
                last_bg = self.COLOR_RESET_BG
            output = ''
            output += self.COLOR_CODE % last_fg
            output += self.COLOR_CODE % last_bg
            return output
        else:
            return ''


class ConsoleFormatter(object):

    """ Convert an XML-Like markup to VT100 control codes.
    """

    def __init__(self, tags={}, reset=None):
        self.tags = tags
        self.reset = reset

    def parse(self, text, strip=False):
        output = ''
        open_tags = []
        for token_type, raw_text, tag_name, attrs in self._lexer(text):
            if token_type == 'text':
                output += raw_text
            elif token_type == 'open':
                open_tags.append(tag_name)
                if not strip:
                    output += self.tags[tag_name][0](**attrs)
            elif token_type == 'close':
                # Close the actually closed tag, and any other tag opened
                # after and not closed:
                while open_tags:
                    closing_tag = open_tags.pop()
                    if not strip:
                        output += self.tags[closing_tag][1]()
                    if closing_tag == tag_name:
                        break
        if not strip:
            output += self.tags.get('_reset', lambda: '')[1]()
        return output

    def _lexer(self, data):
        while data:
            start = data.find('<')
            if start != -1:
                # Found data before a starting tag
                if start:
                    yield 'text', data[:start], None, None
                    data = data[start:]
                end = data.find('>')
                recheck = data.find('<', 1)
                if recheck > 0 and recheck < end:
                    yield 'text', data[:recheck], None, None
                    data = data[recheck:]
                elif end > 0:
                    tag = data[1:end]
                    # Parse a tag
                    if tag[0] == '/':
                        token_type = 'close'
                        tag = tag[1:]
                    else:
                        token_type = 'open'

                    tag_components = tag.split()
                    if tag_components and tag_components[0] in self.tags:
                        tag_name = tag_components[0]
                        opts = {}
                        for cmpt in tag_components[1:]:
                            if '=' in cmpt:
                                key, value = cmpt.split('=', 1)
                                opts[key] = value
                            else:
                                opts[cmpt] = True
                        yield token_type, data[:end + 1], tag_name, opts
                    else:
                        yield 'text', data[:end + 1], None, None

                    data = data[end + 1:]
                else:
                    break
            else:
                break
        if data:
            yield 'text', data, None, None


def option(option, text, **kwargs):
    """ Simple shortcut to construct an option for the MartyPrinter.choices method.
    """
    return option, text, kwargs


class MartyPrinter(object):

    """ Handle print and user interactions.
    """

    def __init__(self, output=sys.stdout, err=sys.stderr, verbose=False, debug=False, encoding='utf8', editor=None):
        self._output = output
        self._err = err
        self._verbose = verbose
        self._debug = debug
        self._encoding = encoding
        self._editor = editor
        tags = DEFAULT_TAGS.copy()
        color_handler = ColorHandler()
        tags['color'] = (color_handler.open, color_handler.close)
        self.formatter = ConsoleFormatter(tags)

    @property
    def output(self):
        return self._output

    def _print(self, *args, **kwargs):
        sep = kwargs.pop('sep', ' ')
        end = kwargs.pop('end', '\n')
        err = kwargs.pop('err', False)
        markup = kwargs.pop('markup', True)
        text = sep.join(str(x) for x in args).format(**kwargs) + end
        if markup:
            text = self.formatter.parse(text)
        if err:
            self._err.write(text)
        else:
            self._output.write(text)

    def configure(self, output=None, verbose=None, debug=None, encoding=None, editor=None):
        if output is not None:
            self._output = output
        if verbose is not None:
            self._verbose = verbose
        if debug is not None:
            self._debug = debug
        if encoding is not None:
            self._encoding = encoding
        if editor is not None:
            self._editor = editor

    def debug(self, *args, **kwargs):
        if self._debug:
            args = ('[debug]',) + args
            self._print(*args, err=True, **kwargs)

    def verbose(self, *args, **kwargs):
        if self._verbose or self._debug:
            self._print(*args, **kwargs)

    def p(self, *args, **kwargs):
        self._print(*args, **kwargs)

    def choice(self, choices):
        for i, (option, text, args) in enumerate(choices):
            self.p('[{indice}] ' + text, indice=i + 1, **args)
        self.p('')
        while True:
            chosen = input('Choice [1-{0}]? '.format(len(choices)))
            if chosen.isdigit() and 1 <= int(chosen) <= len(choices):
                return choices[int(chosen) - 1][0]

    def input(self, prompt, default=None):
        if default is None:
            default_text = ''
        else:
            default_text = ' [{0}]'.format(default)
        prompt = '{0}{1}? '.format(prompt, default_text)
        answer = input(prompt).rstrip('\n').decode(self._encoding)
        if not answer:
            answer = default
        return answer

    def ask(self, question, default=False):
        """ Ask a y/n question to the user.
        """
        choices = '[%s/%s]' % ('Y' if default else 'y', 'n' if default else 'N')
        while True:
            response = input('%s %s' % (question, choices)).strip()
            if not response:
                return default
            elif response in 'yYoO':
                return True
            elif response in 'nN':
                return False

    def edit(self, text):
        """ Edit a text using an external editor.
        """
        if isinstance(text, str):
            text = text.encode(self._encoding)
        if self._editor is None:
            printer.p('Warning: no editor found, skipping edit')
            return text
        with tempfile.NamedTemporaryFile(mode='w+', suffix='marty-edit') as ftmp:
            ftmp.write(text)
            ftmp.flush()
            subprocess.Popen([self._editor, ftmp.name]).wait()
            ftmp.seek(0)
            edited = ftmp.read()
            return edited

    def table(self, lines, fixed_width=None, center=False):
        if fixed_width:  # Fixed width column side mode:
            number_of_columns = max(len(x) for x in lines)
            column_size = int(fixed_width // number_of_columns)
            columns = [column_size] * number_of_columns
        else:  # Real size column size mode:
            columns = []
            for line in lines:
                for i, cell in enumerate(line):
                    size = len(self.formatter.parse(cell, strip=True)) + 1
                    try:
                        columns[i] = max(columns[i], size)
                    except IndexError:
                        columns.append(size)

        for line in lines:
            output = ''
            for size, cell in zip(columns, line):
                cell_raw_size = len(self.formatter.parse(cell, strip=True))
                if center:
                    padding = (size - cell_raw_size) // 2
                    output += '%s%s%s' % (' ' * padding,
                                          cell,
                                          ' ' * (padding if cell_raw_size % 2 == 0 else padding + 1))
                else:
                    padding = size - cell_raw_size
                    output += '%s%s' % (cell, ' ' * padding)

            self.p(output)

    def hr(self):
        """ Display an horizontal rule.
        """
        printer.p()
        printer.p('-' * 80)
        printer.p()

# Instanciate the default printer:
printer = MartyPrinter()
