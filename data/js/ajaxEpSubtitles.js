(function(){
	$.fn.ajaxEpSubtitlesSearch = function(){
		$('.epSubtitlesSearch').click(function(){
			var subtitles_td = $(this).parent().siblings('.subtitles_column');
			var subtitles_search_link = $(this);
			// fill with the ajax loading gif
			subtitles_search_link.empty();
			subtitles_search_link.append($("<img/>").attr({"src": sbRoot+"/images/loading16_dddddd.gif", "alt": "", "title": "loading"}));
			$.getJSON($(this).attr('href'), function(data){
				// update the subtitles column with new informations
				var subtitles = data.subtitles.split(',');
				subtitles_td.html("&nbsp;");
				$.each(subtitles,function(index, language){
					if (language != "") {
						subtitles_td.append($("<img/>").attr({"src": sbRoot+"/images/flags/"+language+".png", "alt": language, "width": 16, "height": 11}));
						subtitles_td.append("&nbsp;");
					}
				});
				// don't allow other searches
				subtitles_search_link.remove();
			});
			// don't follow the link
			return false;
		});
	};

	$.fn.ajaxEpMergeSubtitles = function(){
		$('.epMergeSubtitles').click(function(){
			var subtitles_merge_link = $(this);
			// fill with the ajax loading gif
			subtitles_merge_link.empty();
			subtitles_merge_link.append($("<img/>").attr({"src": sbRoot+"/images/loading16_dddddd.gif", "alt": "", "title": "loading"}));
			$.getJSON($(this).attr('href'), function(data){
				// don't allow other merges
				subtitles_merge_link.remove();
			});
			// don't follow the link
			return false;
		});
	}
})();
