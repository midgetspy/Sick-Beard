
class RangeError(Exception): pass


class NumberPrototype:
    def toString():
        # fuck this radix thing
        if this.Class!='Number':
            raise this.MakeError('TypeError', 'Number.prototype.valueOf is not generic')
        return this.value

    def valueOf():
        if this.Class!='Number':
            raise this.MakeError('TypeError', 'Number.prototype.valueOf is not generic')
        return this.value

    def toLocaleString():
        return this.to_string()

    def toFixed (fractionDigits):
        if this.Class!='Number':
            raise this.MakeError('TypeError', 'Number.prototype.toFixed called on incompatible receiver')
        digs = fractionDigits.to_int()
        if digs<0 or digs>20:
            raise this.MakeError('RangeError', 'toFixed() digits argument must be between 0 and 20')
        elif this.is_infinity():
            return 'Infinity' if this.value>0 else '-Infinity'
        elif this.is_nan():
            return 'NaN'
        return format(this.value, '-.%df'%digs)


    def toExponential (fractionDigits):
        if this.Class!='Number':
            raise this.MakeError('TypeError', 'Number.prototype.toExponential called on incompatible receiver')
        digs = fractionDigits.to_int()
        if digs<0 or digs>20:
            raise this.MakeError('RangeError', 'toFixed() digits argument must be between 0 and 20')
        elif this.is_infinity():
            return 'Infinity' if this.value>0 else '-Infinity'
        elif this.is_nan():
            return 'NaN'
        return format(this.value, '-.%de'%digs)

    def toPrecision (precision):
        if this.Class!='Number':
            raise this.MakeError('TypeError', 'Number.prototype.toPrecision called on incompatible receiver')
        if precision.is_undefined():
            return this.to_String()
        prec = precision.to_int()
        if this.is_nan():
            return 'NaN'
        elif this.is_infinity():
            return 'Infinity' if this.value>0 else '-Infinity'
        digs = prec - len(str(int(this.value)))
        if digs>=0:
            return format(this.value, '-.%df'%digs)
        else:
            return format(this.value, '-.%df'%(prec-1))



