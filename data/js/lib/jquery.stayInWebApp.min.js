/*!
 * jQuery stayInWebApp Plugin
 * version: 0.4 (2012-06-19)
 */
(function($){$.extend({stayInWebApp:function(b){"standalone"in window.navigator&&window.navigator.standalone&&(b||(b="a"),$("body").delegate(b,"click",function(b){if($(this).attr("target")==void 0||$(this).attr("target")==""||$(this).attr("target")=="_self"){var c=$(this).attr("href");if(!c.match(/^http(s?)/g))b.preventDefault(),self.location=c}}))}})})(jQuery);