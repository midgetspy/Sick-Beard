# coding=utf-8
""" This module is still experimental!
"""
from .translators.translator import translate_js, dbg, DEFAULT_HEADER
import sys
import time
import json
__all__  = ['EvalJs', 'translate_js', 'import_js', 'eval_js']

def import_js(path, lib_name, globals):
    """Imports from javascript source file.
      globals is your globals()"""
    with open(path, 'rb') as f:
        js = f.read()
    e = EvalJs()
    e.execute(js)
    var = e.context['var']
    globals[lib_name] = var.to_python()

def eval_js(js):
    """Just like javascript eval. Translates javascript to python,
       executes and returns python object.
       js is javascript source code

       EXAMPLE:
        >>> import js2py
        >>> add = js2py.eval_js('function add(a, b) {return a + b}')
        >>> add(1, 2) + 3
        6
        >>> add('1', 2, 3)
        u'12'
        >>> add.constructor
        function Function() { [python code] }

       NOTE: For Js Number, String, Boolean and other base types returns appropriate python BUILTIN type.
       For Js functions and objects, returns Python wrapper - basically behaves like normal python object.
       If you really want to convert object to python dict you can use to_dict method.
       """
    e = EvalJs()
    return e.eval(js)



class EvalJs(object):
    """This class supports continuous execution of javascript under same context.

        >>> js = EvalJs()
        >>> js.execute('var a = 10;function f(x) {return x*x};')
        >>> js.f(9)
        81
        >>> js.a
        10
       You can run interactive javascript console with console method!"""
    def __init__(self, context=None):
        self.__dict__['_context'] = {}
        exec DEFAULT_HEADER in self._context
        self.__dict__['_var'] = self._context['var'].to_python()

    def execute(self, js):
        """executes javascript js in current context"""
        code = translate_js(js, '')
        exec code in self._context

    def eval(self, expression):
        """evaluates expression in current context and returns its value"""
        code = 'PyJsEvalResult = eval(%s)'%json.dumps(expression)
        self.execute(code)
        return self['PyJsEvalResult']

    def __getattr__(self, var):
        return getattr(self._var, var)

    def __getitem__(self, var):
        return getattr(self._var, var)

    def __setattr__(self, var, val):
        return setattr(self._var, var, val)

    def __setitem__(self, var, val):
        return setattr(self._var, var, val)

    def console(self):
        """starts to interact (starts interactive console) Something like code.InteractiveConsole"""
        while True:
            code = raw_input('>>> ')
            try:
                print self.eval(code)
            except KeyboardInterrupt:
                break
            except Exception as e:
                import traceback
                if DEBUG:
                    sys.stderr.write(traceback.format_exc())
                else:
                    sys.stderr.write('EXCEPTION: '+str(e)+'\n')
                time.sleep(0.01)



x = r'''
var return;
'''.replace('\n','\n').decode('unicode-escape')

#print x

DEBUG = True

if __name__=='__main__':
    #with open('C:\Users\Piotrek\Desktop\esprima.js', 'rb') as f:
    #    x = f.read()
    e = EvalJs()
    #e.execute(x)
    e.console()

