(function(){

    var fileBrowserDialog  = null;
    var currentBrowserPath = null;
    var currentRequest     = null;

    function browse(path, endpoint) {
        if(currentBrowserPath == path)
            return;
        currentBrowserPath = path;
        if(currentRequest)
            currentRequest.abort();
        fileBrowserDialog.dialog('option', 'dialogClass', 'browserDialog busy');
        currentRequest = $.getJSON(endpoint, { path: path }, function(data){
            fileBrowserDialog.empty();
            var first_val = data[0];
            var i = 0;
            data = jQuery.grep(data, function(value) {
                return i++ != 0;
            });
            $('<h1>').text(first_val.current_path).appendTo(fileBrowserDialog);
            list = $('<ul>').appendTo(fileBrowserDialog);
            $.each(data, function(i, entry) {
                link = $("<a href='javascript:void(0)' />").click(function(){ browse(entry.path, endpoint); }).text(entry.name);
                $('<span class="ui-icon ui-icon-folder-collapsed"></span>').prependTo(link);
                link.hover(
                    function(){jQuery("span", this).addClass("ui-icon-folder-open");    },
                    function(){jQuery("span", this).removeClass("ui-icon-folder-open"); }
                );
                link.appendTo(list);
            });
            $("a", list).wrap('<li class="ui-state-default ui-corner-all">');
            fileBrowserDialog.dialog('option', 'dialogClass', 'browserDialog');
        });
    }

    $.fn.fileBrowser = function(options){
        options = $.extend({}, $.Browser.defaults, options);
        options.field = $(this);
        if(options.field.autocomplete && options.autocompleteURL)
            options.field.autocomplete(options.autocompleteURL, { matchCase: true });
        if(options.key && options.field.val().length == 0 && (path = $.cookie('fileBrowser-' + options.key)))
            options.field.val(path);
        return options.field.addClass('fileBrowserField').after($('<input type="button" value="Browse&hellip;" class="fileBrowser" />').click(function(){
            if(!fileBrowserDialog) {
                fileBrowserDialog = $('<div id="fileBrowserDialog" style="display:hidden"></div>').appendTo('body').dialog({
                    dialogClass: 'browserDialog',
                    title:       options.title,
                    position:    ['center', 50],
                    width:       600,
                    height:      600,
                    modal:       true,
                    autoOpen:    false
                });
            }
            fileBrowserDialog.dialog('option', 'buttons',
            {
                "Cancel": function(){
                    fileBrowserDialog.dialog("close");
                },
                "Ok": function(){
                    options.field.val(currentBrowserPath);
                    if(options.key)
                        $.cookie('fileBrowser-' + options.key, currentBrowserPath);
                    fileBrowserDialog.dialog("close");
                }
            });
            
            initialDir = options.field.val() || (options.key && $.cookie('fileBrowser-' + options.key)) || '';
            browse(initialDir, options.url)
            fileBrowserDialog.dialog('open');
            return false;
        }));
    };
})();
