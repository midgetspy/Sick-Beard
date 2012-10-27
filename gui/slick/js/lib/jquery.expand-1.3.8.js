/* ---------------------------------------------
expandAll v.1.3.8
http://www.adipalaz.com/experiments/jquery/expand.html
Requires: jQuery v1.3+
Copyright (c) 2009 Adriana Palazova
Dual licensed under the MIT (http://www.adipalaz.com/docs/mit-license.txt) and GPL (http://www.adipalaz.com/docs/gpl-license.txt) licenses
------------------------------------------------ */
(function($) {
$.fn.expandAll = function(options) {
    var o = $.extend({}, $.fn.expandAll.defaults, options);   
    
    return this.each(function(index) {
        var $$ = $(this), $referent, $sw, $cllps, $tr, container, toggleTxt, toggleClass;
               
        // --- functions:
       (o.switchPosition == 'before') ? ($.fn.findSibling = $.fn.prev, $.fn.insrt = $.fn.before) : ($.fn.findSibling = $.fn.next, $.fn.insrt = $.fn.after);
                    
        // --- var container 
        if (this.id.length) { container = '#' + this.id;
        } else if (this.className.length) { container = this.tagName.toLowerCase() + '.' + this.className.split(' ').join('.');
        } else { container = this.tagName.toLowerCase();}
        
        // --- var $referent
        if (o.ref && $$.find(o.ref).length) {
          (o.switchPosition == 'before') ? $referent = $$.find("'" + o.ref + ":first'") : $referent = $$.find("'" + o.ref + ":last'");
        } else { return; }
        
        // end the script if the length of the collapsible element isn't long enough.  
        if (o.cllpsLength && $$.closest(container).find(o.cllpsEl).text().length < o.cllpsLength) {$$.closest(container).find(o.cllpsEl).addClass('dont_touch'); return;}
    
        // --- if expandAll() claims initial state = hidden:
        (o.initTxt == 'show') ? (toggleTxt = o.expTxt, toggleClass='') : (toggleTxt = o.cllpsTxt, toggleClass='open');
        if (o.state == 'hidden') { 
          $$.find(o.cllpsEl + ':not(.shown, .dont_touch)').hide().findSibling().find('> a.open').removeClass('open'); 
        } else {
          $$.find(o.cllpsEl).show().findSibling().find('> a').addClass('open'); 
        }
        
        (o.oneSwitch) ? ($referent.insrt('<p class="switch"><a href="#" class="' + toggleClass + '">' + toggleTxt + '</a></p>')) :
          ($referent.insrt('<p class="switch"><a href="#" class="">' + o.expTxt + '</a>&nbsp;|&nbsp;<a href="#" class="open">' + o.cllpsTxt + '</a></p>'));

        // --- var $sw, $cllps, $tr :
        $sw = $referent.findSibling('p').find('a');
        $cllps = $$.closest(container).find(o.cllpsEl).not('.dont_touch');
        $tr = (o.trigger) ? $$.closest(container).find(o.trigger + ' > a') : $$.closest(container).find('.expand > a');
                
        if (o.child) {
          $$.find(o.cllpsEl + '.shown').show().findSibling().find('> a').addClass('open').text(o.cllpsTxt);
          window.$vrbls = { kt1 : o.expTxt, kt2 : o.cllpsTxt };
        }

        var scrollElem;
        (typeof scrollableElement == 'function') ? (scrollElem = scrollableElement('html', 'body')) : (scrollElem = 'html, body');
        
        $sw.click(function() {
            var $switch = $(this),
                $c = $switch.closest(container).find(o.cllpsEl +':first'),
                cOffset = $c.offset().top;
            if (o.parent) {
              var $swChildren = $switch.parent().nextAll().children('p.switch').find('a');
                  kidTxt1 = $vrbls.kt1, kidTxt2 = $vrbls.kt2,
                  kidTxt = ($switch.text() == o.expTxt) ? kidTxt2 : kidTxt1;
              $swChildren.text(kidTxt);
              if ($switch.text() == o.expTxt) {$swChildren.addClass('open');} else {$swChildren.removeClass('open');}
            }
            if ($switch.text() == o.expTxt) {
              if (o.oneSwitch) {$switch.text(o.cllpsTxt).attr('class', 'open');}
              $tr.addClass('open');
              $cllps[o.showMethod](o.speed);
            } else {
              if (o.oneSwitch) {$switch.text(o.expTxt).attr('class', '');}
              $tr.removeClass('open');
              if (o.speed == 0 || o.instantHide) {$cllps.hide();} else {$cllps[o.hideMethod](o.speed);}
              if (o.scroll && cOffset < $(window).scrollTop()) {$(scrollElem).animate({scrollTop: cOffset},600);}
          }
          return false;
        });
        /* -----------------------------------------------
        To save file size, feel free to remove the following code if you don't use the option: 'localLinks: true'
        -------------------------------------------------- */
        if (o.localLinks) { 
          var localLink = $(container).find(o.localLinks);
          if (localLink.length) {
            // based on http://www.learningjquery.com/2007/10/improved-animated-scrolling-script-for-same-page-links:
            $(localLink).click(function() {
              var $target = $(this.hash);
              $target = $target.length && $target || $('[name=' + this.hash.slice(1) + ']');
              if ($target.length) {
                var tOffset = $target.offset().top;
                $(scrollElem).animate({scrollTop: tOffset},600);
                return false;
              }
            });
          }
        }
        /* -----------------------------------------------
        Feel free to remove the following function if you don't use the options: 'localLinks: true' or 'scroll: true'
        -------------------------------------------------- */
        //http://www.learningjquery.com/2007/10/improved-animated-scrolling-script-for-same-page-links:
        function scrollableElement(els) {
          for (var i = 0, argLength = arguments.length; i < argLength; i++) {
            var el = arguments[i],
                $scrollElement = $(el);
            if ($scrollElement.scrollTop() > 0) {
              return el;
            } else {
              $scrollElement.scrollTop(1);
              var isScrollable = $scrollElement.scrollTop() > 0;
              $scrollElement.scrollTop(0);
              if (isScrollable) {
                return el;
              }
            }
          };
          return [];
        }; 
      /* --- end of the optional code --- */
});};
$.fn.expandAll.defaults = {
        state : 'hidden', // If 'hidden', the collapsible elements are hidden by default, else they are expanded by default 
        initTxt : 'show', // 'show' - if the initial text of the switch is for expanding, 'hide' - if the initial text of the switch is for collapsing
        expTxt : '[Expand All]', // the text of the switch for expanding
        cllpsTxt : '[Collapse All]', // the text of the switch for collapsing
        oneSwitch : true, // true or false - whether both [Expand All] and [Collapse All] are shown, or they swap
        ref : '.expand', // the switch 'Expand All/Collapse All' is inserted in regards to the element specified by 'ref'
        switchPosition: 'before', //'before' or 'after' - specifies the position of the switch 'Expand All/Collapse All' - before or after the collapsible element
        scroll : false, // false or true. If true, the switch 'Expand All/Collapse All' will be dinamically repositioned to remain in view when the collapsible element closes
        showMethod : 'slideDown', // 'show', 'slideDown', 'fadeIn', or custom
        hideMethod : 'slideUp', // 'hide', 'slideUp', 'fadeOut', or custom
        speed : 600, // the speed of the animation in m.s. or 'slow', 'normal', 'fast'
        cllpsEl : '.collapse', // the collapsible element
        trigger : '.expand', // if expandAll() is used in conjunction with toggle() - the elements that contain the trigger of the toggle effect on the individual collapsible sections
        localLinks : null, // null or the selector of the same-page links to which we will apply a smooth-scroll function, e.g. 'a.to_top'
        parent : false, // true, false
        child : false, // true, false
        cllpsLength : null, //null, {Number}. If {Number} (e.g. cllpsLength: 200) - if the number of characters inside the "collapsible element" is less than the given {Number}, the element will be visible all the time
        instantHide : false // {true} fixes hiding content inside hidden elements
};

/* ---------------------------------------------
Toggler - http://www.adipalaz.com/experiments/jquery/expand.html
When using this script, please keep the above url intact.
*** Feel free to remove the Toggler script if you need only the plugin expandAll().
------------------------------------------------ */
$.fn.toggler = function(options) {
    var o = $.extend({}, $.fn.toggler.defaults, options);
    
    var $this = $(this);
    $this.wrapInner('<a style="display:block" href="#" title="Expand/Collapse" />');
    if (o.initShow) {$(o.initShow).addClass('shown');}
    $this.next(o.cllpsEl + ':not(.shown)').hide();
    return this.each(function() {
      var container;
      (o.container) ? container = o.container : container = 'html';
      if ($this.next('div.shown').length) { $this.closest(container).find('.shown').show().prev().find('a').addClass('open'); }
      $(this).click(function() {
        $(this).find('a').toggleClass('open').end().next(o.cllpsEl)[o.method](o.speed);
        return false;
    });
});};
$.fn.toggler.defaults = {
     cllpsEl : 'div.collapse',
     method : 'slideToggle',
     speed : 'slow',
     container : '', //the common container of all groups with collapsible content (optional)
     initShow : '.shown' //the initially expanded sections (optional)
};
/* ---------------------------------------------
Feel free to remove any of the following functions if you don't need it.
------------------------------------------------ */
$.fn.toggleHeight = function(speed, easing, callback) {
    return this.animate({height: 'toggle'}, speed, easing, callback);
};
//http://www.learningjquery.com/2008/02/simple-effects-plugins:
$.fn.fadeToggle = function(speed, easing, callback) {
    return this.animate({opacity: 'toggle'}, speed, easing, callback);
};
$.fn.slideFadeToggle = function(speed, easing, callback) {
    return this.animate({opacity: 'toggle', height: 'toggle'}, speed, easing, callback);
};
/* --- end of the optional code --- */
})(jQuery);
