/**
 * .cookieJar - Cookie Jar Plugin
 *
 * Version: 1.0.1
 * Updated: 2007-08-14
 *
 * Used to store objects, arrays or multiple values in one cookie, under one name
 *
 * Copyright (c) 2007 James Dempster (letssurf@gmail.com, http://www.jdempster.com/category/jquery/cookieJar/)
 *
 * Dual licensed under the MIT (MIT-LICENSE.txt)
 * and GPL (GPL-LICENSE.txt) licenses.
 **/

/**
 * Requirements:
 * - jQuery (John Resig, http://www.jquery.com/)
 * - cookie (Klaus Hartl, http://www.stilbuero.de/2006/09/17/cookie-plugin-for-jquery/)
 * - toJSON (Mark Gibson, http://jollytoad.googlepages.com/json.js)
 **/
(function($) {
    $.cookieJar = function(name, options) {
        if (!$.parseJSON) return false;
        if (!$.toJSON) return false;
        if (!$.cookie) return false;
        return new function() {
            /**
             * @access private
             **/
            function log(s) {
                if (typeof console != 'undefined' && typeof console.log != 'undefined') {
                    console.log('cookiejar:' + self.cookieName + ' ' + s);
                } else {
                    alert(s);
                }
            };

            /**
             * @access private
             **/
            function save() {
                if (self.options.debug) log('save ' + $.toJSON(self.cookieObject));
                return $.cookie(self.cookieName, $.toJSON(self.cookieObject), self.options.cookie);
            };

            /**
             * @access private
             **/
            function load() {
                var cookieJSON = $.cookie(self.cookieName);
                if (typeof cookieJSON == 'string') {
                    if (self.options.debug) log('load ' + cookieJSON);
                    self.cookieObject = $.parseJSON(cookieJSON, true);
                } else {
                    if (self.options.debug) log('load new');
                    self.cookieObject = {};
                    save();
                }
            }

            /**
             * cookieJar.set(name, value)
             *
             * Sets a value in the cookie jar using a name to identify it
             *
             * @access public
             * @param string name value identifier
             * @param mixed value any value, array or object
             * @return bool
             **/
            this.set = function(name, value) {
                if (self.options.debug) log('set ' + name + ' = ' + value);
                self.cookieObject[name] = value;
                return save();
            };

            /**
             * cookieJar.get(name)
             *
             * Gets a value from the cookie jar using a name to identify it
             *
             * @access public
             * @param string name value identifier
             * @return mixed stored value
             **/
            this.get = function(name) {
                if (!self.options.cacheCookie) {
                    load();
                }
                if (self.options.debug) log('get ' + name + ' = ' + self.cookieObject[name]);
                return self.cookieObject[name];
            };

            /**
             * cookieJar.remove([name])
             *
             * Removes a value from the cookie jar using a name to identify it
             * No name will clear the cookie jar of all values
             *
             * @access public
             * @param string name value identifier
             * @return bool
             **/
            this.remove = function(name) {
                if (self.options.debug) log('remove ' + name);
                if (typeof name != 'undefined') {
                    delete(self.cookieObject[name]);
                } else {
                    self.setFromObject({});
                }
                return save();
            };

            /**
             * cookieJar.setFromObject(object)
             *
             * Uses the object as the set of values to store in the cookie jar
             *
             * @access public
             * @param object object new values for the cookie jar
             * @return bool
             **/
            this.setFromObject = function(object) {
                if (typeof object == 'object') {
                    if (self.options.debug) log('setFromObject');
                    self.cookieObject = object;
                    return save();
                }
            };

            /**
             * cookieJar.toObject()
             *
             * Returns the contents of the cookie jar as an object
             *
             * @access public
             * @return object contents of the cookie jar
             **/
            this.toObject = function() {
                if (self.options.debug) log('toObject');
                return self.cookieObject;
            };

            /**
             * cookieJar.toString()
             *
             * Returns the contents of the cookie jar as a JSON encoded string
             *
             * @access public
             * @return string contents of the cookie jar as JSON
             **/
            this.toString = function() {
                if (self.options.debug) log('toString = ' + $.toJSON(self.cookieObject));
                return $.toJSON(self.cookieObject);
            };

            /**
             * cookieJar.destroy()
             *
             * Removes the cookie containing the cookie jar from the server
             *
             * @access public
             * @return bool
             **/
            this.destroy = function() {
                if (self.options.debug) log('destroy');
                self.cookieObject = {};
                return $.cookie(self.cookieName, null, self.options.cookie);
            };

            /**
             * cookieJar(name, [options])
             *
             * loads a cookie jar for the name provided, creates new if none found
             *
             * @param string name
             * @param object options
             * @return object cookieJar
             **/
            this.construct = function(name, options) {
                self.options = $.extend({
                    cookie: {
                        expires: 365,
			path: '/'
                    },
                    cacheCookie:    true,
                    cookiePrefix:   'jqCookieJar_',
                    debug:          false
                }, options);

                self.cookieName     = self.options.cookiePrefix + name;
                load();
                return self;
            };

            var self = this;
            self.construct(name, options);
        };
    };
})(jQuery);
