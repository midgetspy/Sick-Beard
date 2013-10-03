;(function($) {
"use strict";

    $.Browser = {
        defaults: {
            title:             'Choose Directory',
            url:               sbRoot + '/browser/',
            autocompleteURL:   sbRoot + '/browser/complete'
        }
    };

    var fileBrowserDialog, currentBrowserPath, currentRequest = null;

    function browse(path, endpoint) {

        if (currentBrowserPath == path) {
            return;
        }

        currentBrowserPath = path;

        if (currentRequest) {
            currentRequest.abort();
        }

        fileBrowserDialog.dialog('option', 'dialogClass', 'browserDialog busy');

        currentRequest = $.getJSON(endpoint, { path: path }, function (data) {
            fileBrowserDialog.empty();
            var first_val = data[0];
            var i = 0;
            var list, link = null;
            data = $.grep(data, function (value) {
                return i++ != 0;
            });
            $('<h2>').text(first_val.current_path).appendTo(fileBrowserDialog);
            list = $('<ul>').appendTo(fileBrowserDialog);
            $.each(data, function (i, entry) {
                link = $("<a href='javascript:void(0)' />").click(function () { browse(entry.path, endpoint); }).text(entry.name);
                $('<span class="ui-icon ui-icon-folder-collapsed"></span>').prependTo(link);
                link.hover(
                    function () {$("span", this).addClass("ui-icon-folder-open");    },
                    function () {$("span", this).removeClass("ui-icon-folder-open"); }
                );
                link.appendTo(list);
            });
            $("a", list).wrap('<li class="ui-state-default ui-corner-all">');
            fileBrowserDialog.dialog('option', 'dialogClass', 'browserDialog');
        });
    }

    $.fn.nFileBrowser = function (callback, options) {
        options = $.extend({}, $.Browser.defaults, options);

        // make a fileBrowserDialog object if one doesn't exist already
        if (!fileBrowserDialog) {

            // set up the jquery dialog
            fileBrowserDialog = $('<div id="fileBrowserDialog" style="display:hidden"></div>').appendTo('body').dialog({
                dialogClass: 'browserDialog',
                title:       options.title,
                position:    ['center', 40],
                minWidth:    Math.min($(document).width() - 80, 650),
                height:      Math.min($(document).height() - 80, $(window).height() - 80),
                maxHeight:   Math.min($(document).height() - 80, $(window).height() - 80),
                maxWidth:    $(document).width() - 80,
                modal:       true,
                autoOpen:    false,
            });
        }

        fileBrowserDialog.dialog('option', 'buttons', [
                    {
                        text: "Ok",
                        "class": "btn btn-large",
                        click: function() {
                            // store the browsed path to the associated text field
                            callback(currentBrowserPath, options);
                            $(this).dialog("close");
                        }
                    },
                    {
                        text: "Cancel",
                        "class": "btn btn-large",
                        click: function() {
                            $(this).dialog("close");
                        }
                    }
        ]);

        // set up the browser and launch the dialog
        var initialDir = '';
        if (options.initialDir) {
            initialDir = options.initialDir;
        }
        browse(initialDir, options.url);
        fileBrowserDialog.dialog('open');

        return false;
    };

    $.fn.fileBrowser = function (options) {
        options = $.extend({}, $.Browser.defaults, options);
        // text field used for the result
        options.field = $(this);

        if (options.field.autocomplete && options.autocompleteURL) {
            var query = '';
            options.field.autocomplete({
                position: { my : "top", at: "bottom", collision: "flipfit" },
                source: function (request, response) {
                    //keep track of user submitted search term
                    query = $.ui.autocomplete.escapeRegex(request.term);
                    $.ajax({
                        url: options.autocompleteURL,
                        data: request,
                        dataType: "json",
                        success: function (data, item) {
                            //implement a startsWith filter for the results
                            var matcher = new RegExp("^" + query, "i");
                            var a = $.grep(data, function (item, index) {
                                return matcher.test(item);
                            });
                            response(a);
                        }
                    });
                },
                open: function (event, ui) {
                    $(".ui-autocomplete li.ui-menu-item a").removeClass("ui-corner-all");
                    $(".ui-autocomplete li.ui-menu-item:odd a").addClass("ui-menu-item-alternate");
                }
            })
                .data("ui-autocomplete")._renderItem = function (ul, item) {
                    //highlight the matched search term from the item -- note that this is global and will match anywhere
                    var result_item = item.label;
                    var x = new RegExp("(?![^&;]+;)(?!<[^<>]*)(" + query + ")(?![^<>]*>)(?![^&;]+;)", "gi");
                    result_item = result_item.replace(x, function (FullMatch, n) {
                        return '<b>' + FullMatch + '</b>';
                    });
                    return $("<li></li>")
                        .data("ui-autocomplete-item", item)
                        .append("<a class='nowrap'>" + result_item + "</a>")
                        .appendTo(ul);
                };
        }

        var initialDir, path, callback, ls = false;
        // if the text field is empty and we're given a key then populate it with the last browsed value from localStorage
        try { ls = !!(localStorage.getItem); } catch (e) {}
        if (ls && options.key) {
            path = localStorage['fileBrowser-' + options.key];
        }
        if (options.key && options.field.val().length == 0 && (path)) {
            options.field.val(path);
        }

        callback = function (path, options) {
            // store the browsed path to the associated text field
            options.field.val(path);

            // use a localStorage to remember for next time -- no ie6/7
            if (ls && options.key) {
                localStorage['fileBrowser-' + options.key] = path;
            }

        };

        initialDir = options.field.val() || (options.key && path) || '';

        options = $.extend(options, {initialDir: initialDir});

        // append the browse button and give it a click behaviour
        return options.field.addClass('fileBrowserField').after($('<input type="button" value="Browse&hellip;" class="btn fileBrowser" />').click(function () {
            $(this).nFileBrowser(callback, options);
            return false;
        }));
    };

})(jQuery);
