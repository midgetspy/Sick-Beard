

# todo fix apply and bind

class FunctionPrototype:            
    def toString():
        if not this.is_callable():
            raise TypeError('toString is not generic!')
        args = ', '.join(this.code.__code__.co_varnames[:this.argcount])
        return 'function %s(%s) '%(this.func_name, args)+this.source
    
    def call():
        if not len(arguments):
            obj = this.Js(None)
        else:
            obj = arguments[0]
        if len(arguments)<=1:
            args = () 
        else:
            args = tuple([arguments[e] for e in xrange(1, len(arguments))])
        return this.call(obj, args)
    
    def apply():
        if not len(arguments):
            obj = this.Js(None)
        else:
            obj = arguments[0]
        if len(arguments)<=1:
            args = () 
        else:
            appl = arguments[1]
            try:
                args = tuple([appl[e] for e in xrange(len(appl))])
            except:
                args = ()
        return this.call(obj, args)

    def bind(thisArg):
        if not this.is_callable():
            raise this.MakeError('TypeError', 'this must be callable!')
        to_call = this
        if not len(arguments):
            obj = this.Js(None)
        else:
            obj = arguments[0]
        if len(arguments)<=1:
            args = ()
        else:
            args = tuple([arguments[e] for e in xrange(1, len(arguments))])
        if obj.is_undefined():
            def PyJsLvalInline(this, arguments):
                args2 = args + tuple([arguments[e] for e in xrange(0, len(arguments))])
                return to_call(*args2)
        else:
            def PyJsLvalInline(this, arguments):
                args2 = args + tuple([arguments[e] for e in xrange(0, len(arguments))])
                return to_call.call(obj, args2)
        return PyJsLvalInline  # it will be automatically converted to js function :)



