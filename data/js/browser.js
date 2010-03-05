(function(){
	var fileBrowserDialog  = null;
	var currentBrowserPath = null;

	function browse(path) {
		currentBrowserPath = path;
		$.getJSON('/browser/', { path: path }, function(data){
			fileBrowserDialog.empty();
			$('<h1>').text(path).appendTo(fileBrowserDialog);
			list = $('<ul>').appendTo(fileBrowserDialog);
			$.each(data, function(i, entry) {
				link = $("<a />").click(function(){ browse(entry.path); }).text(entry.name);
				$('<span class="ui-icon ui-icon-folder-collapsed"></span>').appendTo(link);
				link.hover(
					function(){jQuery("span", this).addClass("ui-icon-folder-open");    },
					function(){jQuery("span", this).removeClass("ui-icon-folder-open"); }
				);
				link.appendTo(list);
			});
			$("a", list).wrap('<li class="ui-state-default ui-corner-all">');
		});
	}

	$.fn.fileBrowser = function(options){
		field = this;
		return field.addClass('fileBrowserField').after($('<input type="button" value="Browse&hellip;" class="fileBrowser" />').click(function(){
			if(!fileBrowserDialog) {
				fileBrowserDialog = $('<div id="fileBrowserDialog" style="display:hidden"></div>').appendTo('body').dialog({
					title:     options.title || 'Choose Directory',
					position:  ['center', 50],
					width:     600,
					height:    600,
					modal:     true,
					autoOpen:  false,
				});
			}
			fileBrowserDialog.dialog('option', 'buttons',
			{
				"Ok": function(){
					field.val(currentBrowserPath);
					if(options.key)
						$.cookie('fileBrowser-' + options.key, currentBrowserPath);
					fileBrowserDialog.dialog("close");
				},
				"Cancel": function(){
					fileBrowserDialog.dialog("close");
				}
			});
			
			initialDir = field.val() || (options.key && $.cookie('fileBrowser-' + options.key)) || '/';
			browse(initialDir)
			fileBrowserDialog.dialog('open');
			return false;
		}));
	};
})();
