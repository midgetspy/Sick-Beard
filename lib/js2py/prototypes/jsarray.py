def to_arr(this):
    """Returns Python array from Js array"""
    return [this.get(str(e)) for e in xrange(len(this))]


ARR_STACK = set({})

class ArrayPrototype:
    def toString():
        # this function is wrong but I will leave it here fore debugging purposes.
        func = this.get('join')
        if not func.is_callable():
            @this.Js
            def func():
                return '[object %s]'%this.Class
        return func.call(this, ())

    def toLocaleString():
        array = this.to_object()
        arr_len = array.get('length').to_uint32()
        # separator is simply a comma ','
        if not arr_len:
            return ''
        res = []
        for i in xrange(arr_len):
            element = array[str(i)]
            if element.is_undefined() or element.is_null():
                res.append('')
            else:
                cand = element.to_object()
                str_func = element.get('toLocaleString')
                if not str_func.is_callable():
                    raise this.MakeError('TypeError', 'toLocaleString method of item at index %d is not callable'%i)
                res.append(element.callprop('toLocaleString').value)
        return ','.join(res)

    def concat():
        array = this.to_object()
        A = this.Js([])
        items = [array]
        items.extend(to_arr(arguments))
        n = 0
        for E in items:
            if E.Class=='Array':
                k = 0
                e_len = len(E)
                while k<e_len:
                    if E.has_property(str(k)):
                        A.put(str(n), E.get(str(k)))
                    n+=1
                    k+=1
            else:
                A.put(str(n), E)
                n+=1
        return A

    def join(separator):
        ARR_STACK.add(this)
        array = this.to_object()
        arr_len = array.get('length').to_uint32()
        separator = ',' if separator.is_undefined() else separator.to_string().value
        elems = []
        for e in xrange(arr_len):
            elem = array.get(str(e))
            if elem in ARR_STACK:
                s = ''
            else:
                s = elem.to_string().value
            elems.append(s if not (elem.is_undefined() or elem.is_null()) else '')
        res =  separator.join(elems)
        ARR_STACK.remove(this)
        return res

    def pop(): #todo check
        array = this.to_object()
        arr_len = array.get('length').to_uint32()
        if not arr_len:
            array.put('length', this.Js(arr_len))
            return None
        ind = str(arr_len-1)
        element = array.get(ind)
        array.delete(ind)
        array.put('length', this.Js(arr_len-1))
        return element


    def push(item): # todo check
        array = this.to_object()
        arr_len = array.get('length').to_uint32()
        to_put = arguments.to_list()
        i = arr_len
        for i, e in enumerate(to_put, arr_len):
            array.put(str(i), e)
        if to_put:
            i+=1
            array.put('length', this.Js(i))
        return i


    def reverse():
        array = this.to_object() # my own algorithm
        vals = to_arr(array)
        has_props = [array.has_property(str(e)) for e in xrange(len(array))]
        vals.reverse()
        has_props.reverse()
        for i, val in enumerate(vals):
            if has_props[i]:
                array.put(str(i), val)
            else:
                array.delete(str(i))
        return array


    def shift():  #todo check
        array = this.to_object()
        arr_len = array.get('length').to_uint32()
        if not arr_len:
            array.put('length', this.Js(0))
            return None
        first = array.get('0')
        for k in xrange(1, arr_len):
            from_s, to_s = str(k), str(k-1)
            if array.has_property(from_s):
                array.put(to_s, array.get(from_s))
            else:
                array.delete(to)
        array.delete(str(arr_len-1))
        array.put('length', this.Js(str(arr_len-1)))
        return first

    def slice(start, end): # todo check
        array = this.to_object()
        arr_len = array.get('length').to_uint32()
        relative_start = start.to_int()
        k = max((arr_len + relative_start), 0) if relative_start<0 else  min(relative_start, arr_len)
        relative_end = arr_len if end.is_undefined() else end.to_int()
        final =  max((arr_len + relative_end), 0) if relative_end<0 else min(relative_end, arr_len)
        res = []
        n = 0
        while k<final:
            pk = str(k)
            if array.has_property(pk):
                res.append(array.get(pk))
            k += 1
            n += 1
        return res

    def sort(cmpfn):
        if not this.Class in {'Array', 'Arguments'}:
            return this.to_object() # do nothing
        arr = [this.get(str(i)) for i in xrange(len(this))]
        if not arr:
            return this
        if not cmpfn.is_callable():
            cmpfn = None
        cmp = lambda a,b: sort_compare(a, b, cmpfn)
        arr.sort(cmp=cmp)
        for i in xrange(len(arr)):
            this.put(unicode(i), arr[i])
        return this

    def splice(start, deleteCount):
        # 1-8
        array = this.to_object()
        arr_len = array.get('length').to_uint32()
        relative_start = start.to_int()
        actual_start = max((arr_len + relative_start),0) if relative_start<0 else min(relative_start, arr_len)
        actual_delete_count =  min(max(deleteCount.to_int(),0 ), arr_len - actual_start)
        k = 0
        A = this.Js([])
        # 9
        while k<actual_delete_count:
            if array.has_property(str(actual_start+k)):
                A.put(str(k), array.get(str(actual_start+k)))
            k += 1
        # 10-11
        items = to_arr(arguments)[2:]
        items_len = len(items)
        # 12
        if items_len<actual_delete_count:
            k = actual_start
            while k < (arr_len-actual_delete_count):
                fr = str(k+actual_delete_count)
                to = str(k+items_len)
                if array.has_property(fr):
                    array.put(to, array.get(fr))
                else:
                    array.delete(to)
                k += 1
            k = arr_len
            while k > (arr_len - actual_delete_count + items_len):
                array.delete(str(k-1))
                k -= 1
        # 13
        elif items_len>actual_delete_count:
            k = arr_len - actual_delete_count
            while k>actual_start:
                fr = str(k + actual_delete_count - 1)
                to = str(k + items_len - 1)
                if array.has_property(fr):
                    array.put(to, array.get(fr))
                else:
                    array.delete(to)
                k -= 1
        # 14-17
        k = actual_start
        while items:
            E = items.pop(0)
            array.put(str(k), E)
            k += 1
        array.put('length', this.Js(arr_len - actual_delete_count + items_len))
        return A



    def unshift():
        raise NotImplementedError()

    def indexOf(searchElement):
        raise NotImplementedError()

    def lastIndexOf(searchElement):
        raise NotImplementedError()

    def every(callbackfn):
        raise NotImplementedError()

    def some(callbackfn):
        raise NotImplementedError()

    def forEach(callbackfn):
        array = this.to_object()
        arr_len = array.get('length').to_uint32()
        if not callbackfn.is_callable():
            raise this.MakeError('TypeError', 'callbackfn must be a function')
        T = arguments[1]
        k = 0
        while k<arr_len:
            if array.has_property(str(k)):
                kValue = array.get(str(k))
                callbackfn.call(T, (kValue, this.Js(k), array))
            k+=1


    def map(callbackfn):
        raise NotImplementedError()

    def filter(callbackfn):
        raise NotImplementedError()

    def reduce(callbackfn):
        raise NotImplementedError()

    def reduceRight(callbackfn):
        raise NotImplementedError()


def sort_compare(a, b, comp):
    if a is None:
        if b is None:
            return 0
        return 1
    if b is None:
        if a is None:
            return 0
        return -1
    if a.is_undefined():
        if b.is_undefined():
            return 0
        return 1
    if b.is_undefined():
        if a.is_undefined():
            return 0
        return -1
    if comp is not None:
        res = comp.call(a.undefined, (a, b))
        return res.to_int()
    x, y = a.to_string(), b.to_string()
    if x<y:
        return -1
    elif x>y:
        return 1
    return 0





