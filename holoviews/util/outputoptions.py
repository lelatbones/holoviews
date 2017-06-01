
from collections import defaultdict
from ..core import OrderedDict
from ..core import Store
from ..core.util import basestring

class KeywordOptions(object):
    """
    Base class for magics that are used to specified collections of
    keyword options.
    """
    # Dictionary from keywords to allowed bounds/values
    allowed = {'charwidth'   : (0, float('inf'))}
    defaults = OrderedDict([('charwidth'   , 80)])  # Default keyword values.
    options =  OrderedDict(defaults.items()) # Current options

    # Callables accepting (value, keyword, allowed) for custom exceptions
    custom_exceptions = {}

    # Hidden. Options that won't tab complete (for backward compatibility)
    hidden = {}


    @classmethod
    def update_options(cls, options, items):
        """
        Allows updating options depending on class attributes
        and unvalidated options.
        """
        pass

    @classmethod
    def get_options(cls, line, options, linemagic, warnfn):
        "Given a keyword specification line, validated and compute options"
        items = cls._extract_keywords(line, OrderedDict())
        options = cls.update_options(options, items)
        for keyword in cls.defaults:
            if keyword in items:
                value = items[keyword]
                allowed = cls.allowed[keyword]
                if isinstance(allowed, set):  pass
                elif isinstance(allowed, dict):
                    if not isinstance(value, dict):
                        raise ValueError("Value %r not a dict type" % value)
                    disallowed = set(value.keys()) - set(allowed.keys())
                    if disallowed:
                        raise ValueError("Keywords %r for %r option not one of %s"
                                         % (disallowed, keyword, allowed))
                    wrong_type = {k: v for k, v in value.items()
                                  if not isinstance(v, allowed[k])}
                    if wrong_type:
                        errors = []
                        for k,v in wrong_type.items():
                            errors.append("Value %r for %r option's %r attribute not of type %r" %
                                          (v, keyword, k, allowed[k]))
                        raise ValueError('\n'.join(errors))
                elif isinstance(allowed, list) and value not in allowed:
                    if keyword in cls.custom_exceptions:
                        cls.custom_exceptions[keyword](value, keyword, allowed)
                    else:
                        raise ValueError("Value %r for key %r not one of %s"
                                         % (value, keyword, allowed))
                elif isinstance(allowed, tuple):
                    if not (allowed[0] <= value <= allowed[1]):
                        info = (keyword,value)+allowed
                        raise ValueError("Value %r for key %r not between %s and %s" % info)
                options[keyword] = value
        return cls._validate(options, items, linemagic, warnfn)

    @classmethod
    def _validate(cls, options, items, linemagic, warnfn):
        "Allows subclasses to check options are valid."
        raise NotImplementedError("KeywordOptions is an abstract base class.")

    @classmethod
    def pprint(cls):
        """
        Pretty print the current element options with a maximum width of
        cls.pprint_width.
        """
        current, count = '', 0
        for k,v in cls.options.items():
            keyword = '%s=%r' % (k,v)
            if len(current) + len(keyword) > cls.options['charwidth']:
                print((cls.magic_name if count==0 else '      ')  + current)
                count += 1
                current = keyword
            else:
                current += ' '+ keyword
        else:
            print((cls.magic_name if count==0 else '      ')  + current)


    @classmethod
    def _extract_keywords(cls, line, items):
        """
        Given the keyword string, parse a dictionary of options.
        """
        unprocessed = list(reversed(line.split('=')))
        while unprocessed:
            chunk = unprocessed.pop()
            key = None
            if chunk.strip() in cls.allowed:
                key = chunk.strip()
            else:
                raise SyntaxError("Invalid keyword: %s" % chunk.strip())
            # The next chunk may end in a subsequent keyword
            value = unprocessed.pop().strip()
            if len(unprocessed) != 0:
                # Check if a new keyword has begun
                for option in cls.allowed:
                    if value.endswith(option):
                        value = value[:-len(option)].strip()
                        unprocessed.append(option)
                        break
                else:
                    raise SyntaxError("Invalid keyword: %s" % value.split()[-1])
            keyword = '%s=%s' % (key, value)
            try:
                items.update(eval('dict(%s)' % keyword))
            except:
                raise SyntaxError("Could not evaluate keyword: %s" % keyword)
        return items



def list_backends():
    backends = []
    for backend in Store.renderers:
        backends.append(backend)
        renderer = Store.renderers[backend]
        modes = [mode for mode in renderer.params('mode').objects if mode  != 'default']
        backends += ['%s:%s' % (backend, mode) for mode in modes]
    return backends


def list_formats(format_type, backend=None):
    """
    Returns list of supported formats for a particular
    backend.
    """
    if backend is None:
        backend = Store.current_backend
        mode = Store.renderers[backend].mode if backend in Store.renderers else None
    else:
        split = backend.split(':')
        backend, mode = split if len(split)==2 else (split[0], 'default')

    if backend in Store.renderers:
        return Store.renderers[backend].mode_formats[format_type][mode]
    else:
        return []



class OutputOptions(KeywordOptions):
    """
    Magic for easy customising of display options.
    Consult %%output? for more information.
    """

    magic_name = '%output'

    # Lists: strict options, Set: suggested options, Tuple: numeric bounds.
    allowed = {'backend'     : list_backends(),
               'fig'         : list_formats('fig'),
               'holomap'     : list_formats('holomap'),
               'widgets'     : ['embed', 'live'],
               'fps'         : (0, float('inf')),
               'max_frames'  : (0, float('inf')),
               'max_branches': {None},            # Deprecated
               'size'        : (0, float('inf')),
               'dpi'         : (1, float('inf')),
               'charwidth'   : (0, float('inf')),
               'filename'    : {None},
               'info'        : [True, False],
               'css'         : {k: basestring
                                for k in ['width', 'height', 'padding', 'margin',
                                          'max-width', 'min-width', 'max-height',
                                          'min-height', 'outline', 'float']}}

    defaults = OrderedDict([('backend'     , None),
                            ('fig'         , None),
                            ('holomap'     , None),
                            ('widgets'     , None),
                            ('fps'         , None),
                            ('max_frames'  , 500),
                            ('size'        , None),
                            ('dpi'         , None),
                            ('charwidth'   , 80),
                            ('filename'    , None),
                            ('info'        , False),
                            ('css'         , None)])

    # Defines the options the OutputOptions remembers. All other options
    # are held by the backend specific Renderer.
    remembered = ['max_frames', 'charwidth', 'info', 'filename']

    # Remaining backend specific options renderer options
    render_params = ['fig', 'holomap', 'size', 'fps', 'dpi', 'css', 'widget_mode', 'mode']

    options = OrderedDict()
    _backend_options = defaultdict(dict)

    # Used to disable info output in testing
    _disable_info_output = False

    #==========================#
    # Backend state management #
    #==========================#

    last_backend = None
    backend_list = [] # List of possible backends

    def missing_dependency_exception(value, keyword, allowed):
        raise Exception("Format %r does not appear to be supported." % value)

    def missing_backend_exception(value, keyword, allowed):
        if value in OutputOptions.backend_list:
            raise ValueError("Backend %r not available. Has it been loaded with the notebook_extension?" % value)
        else:
            raise ValueError("Backend %r does not exist" % value)

    custom_exceptions = {'holomap':missing_dependency_exception,
                         'backend': missing_backend_exception}

    # Counter for nbagg figures
    nbagg_counter = 0

    @classmethod
    def _generate_docstring(cls):
        renderer = Store.renderers[Store.current_backend]
        intro = ["Magic for setting HoloViews display options.",
                 "Arguments are supplied as a series of keywords in any order:", '']
        backend = "backend      : The backend used by HoloViews %r"  % cls.allowed['backend']
        fig =     "fig          : The static figure format %r" % cls.allowed['fig']
        holomap = "holomap      : The display type for holomaps %r" % cls.allowed['holomap']
        widgets = "widgets      : The widget mode for widgets %r" % renderer.widget_mode
        fps =    ("fps          : The frames per second for animations (default %r)"
                  % renderer.fps)
        frames=  ("max_frames   : The max number of frames rendered (default %r)"
                  % cls.defaults['max_frames'])
        size =   ("size         : The percentage size of displayed output (default %r)"
                  % renderer.size)
        dpi =    ("dpi          : The rendered dpi of the figure (default %r)"
                  % renderer.dpi)
        chars =  ("charwidth    : The max character width for displaying the output magic (default %r)"
                  % cls.defaults['charwidth'])
        fname =  ("filename    : The filename of the saved output, if any (default %r)"
                  % cls.defaults['filename'])
        page =  ("info    : The information to page about the displayed objects (default %r)"
                  % cls.defaults['info'])
        css =   ("css     : Optional css style attributes to apply to the figure image tag")

        descriptions = [backend, fig, holomap, widgets, fps, frames, size, dpi, chars, fname, page, css]
        return '\n'.join(intro + descriptions)


    @classmethod
    def _validate(cls, options, items, linemagic, warnfn):
        "Validation of edge cases and incompatible options"

        if 'html' in Store.display_formats:
            pass
        elif 'fig' in items and items['fig'] not in Store.display_formats:
            msg = ("Output magic requesting figure format %r " % items['fig']
                   + "not in display formats %r" % Store.display_formats)
            if warnfn is None:
                print('Warning: {msg}'.format(msg=msg))
            else:
                warnfn(msg)

        backend = Store.current_backend
        return Store.renderers[backend].validate(options)


    @classmethod
    def output(cls, line, cell=None, cell_runner=None, warnfn=None):
        line = line.split('#')[0].strip()
        if line == '':
            cls.pprint()
            print("\nFor help with the %output magic, call %output?")
            return

        # Make backup of previous options
        prev_backend = Store.current_backend
        prev_renderer = Store.renderers[prev_backend]
        prev_backend_spec = prev_backend+':'+prev_renderer.mode
        prev_params = {k: v for k, v in prev_renderer.get_param_values()
                       if k in cls.render_params}
        prev_restore = dict(OutputOptions.options)
        try:
            # Process magic
            new_options = cls.get_options(line, {}, cell is None, warnfn)

            # Make backup of options on selected renderer
            if 'backend' in new_options:
                backend_spec = new_options['backend']
                if ':' not in backend_spec:
                    backend_spec += ':default'
            else:
                backend_spec = prev_backend_spec
            renderer = Store.renderers[backend_spec.split(':')[0]]
            render_params = {k: v for k, v in renderer.get_param_values()
                             if k in cls.render_params}

            # Set options on selected renderer and set display hook options
            OutputOptions.options = new_options
            cls._set_render_options(new_options, backend_spec)
        except Exception as e:
            # If setting options failed ensure they are reset
            OutputOptions.options = prev_restore
            cls.set_backend(prev_backend)
            print('Error: %s' % str(e))
            print("For help with the %output magic, call %output?\n")
            return

        if cell is not None:
            if cell_runner: cell_runner(cell)
            # After cell magic restore previous options and restore
            # temporarily selected renderer
            OutputOptions.options = prev_restore
            cls._set_render_options(render_params, backend_spec)
            if backend_spec.split(':')[0] != prev_backend:
                cls.set_backend(prev_backend)
                cls._set_render_options(prev_params, prev_backend_spec)


    @classmethod
    def update_options(cls, options, items):
        """
        Switch default options and backend if new backend
        is supplied in items.
        """
        # Get new backend
        backend_spec = items.get('backend', Store.current_backend)
        split = backend_spec.split(':')
        backend, mode = split if len(split)==2 else (split[0], 'default')
        if ':' not in backend_spec:
            backend_spec += ':default'

        if 'max_branches' in items:
            print('Warning: The max_branches option is now deprecated. Ignoring.')
            del items['max_branches']

        # Get previous backend
        prev_backend = Store.current_backend
        renderer = Store.renderers[prev_backend]
        prev_backend_spec = prev_backend+':'+renderer.mode

        # Update allowed formats
        for p in ['fig', 'holomap']:
            cls.allowed[p] = list_formats(p, backend_spec)

        # Return if backend invalid and let validation error
        if backend not in Store.renderers:
            options['backend'] = backend_spec
            return options

        # Get backend specific options
        backend_options = dict(cls._backend_options[backend_spec])
        cls._backend_options[prev_backend_spec] = {k: v for k, v in cls.options.items()
                                                   if k in cls.remembered}

        # Fill in remembered options with defaults
        for opt in cls.remembered:
            if opt not in backend_options:
                backend_options[opt] = cls.defaults[opt]

        # Switch format if mode does not allow it
        for p in ['fig', 'holomap']:
            if backend_options.get(p) not in cls.allowed[p]:
                backend_options[p] = cls.allowed[p][0]

        # Ensure backend and mode are set
        backend_options['backend'] = backend_spec
        backend_options['mode'] = mode

        return backend_options


    @classmethod
    def initialize(cls, backend_list):
        cls.backend_list = backend_list
        backend = cls.options.get('backend', Store.current_backend)
        if backend in Store.renderers:
            cls.options = dict({k: cls.defaults[k] for k in cls.remembered})
            cls.set_backend(backend)
        else:
            cls.options['backend'] = None
            cls.set_backend(None)


    @classmethod
    def set_backend(cls, backend):
        cls.last_backend = Store.current_backend
        Store.current_backend = backend


    @classmethod
    def _set_render_options(cls, options, backend=None):
        """
        Set options on current Renderer.
        """
        if backend:
            backend = backend.split(':')[0]
        else:
            backend = Store.current_backend

        cls.set_backend(backend)
        if 'widgets' in options:
            options['widget_mode'] = options['widgets']
        renderer = Store.renderers[backend]
        render_options = {k: options[k] for k in cls.render_params if k in options}
        renderer.set_param(**render_options)
