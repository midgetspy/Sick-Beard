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
		return this.click(function(){
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
					$(options.field).val(currentBrowserPath);
					fileBrowserDialog.dialog("close");
				},
				"Cancel": function(){
					fileBrowserDialog.dialog("close");
				}
			});
			
			if ($(options.field).val() != "")
			     browseDir = $(options.field).val()
			else
			     browseDir = '/'
									 
			if(!currentBrowserPath)
				browse(browseDir)
			fileBrowserDialog.dialog('open');
			return false;
		});
	};
})();