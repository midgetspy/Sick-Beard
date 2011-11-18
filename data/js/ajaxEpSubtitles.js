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
				subtitles_td.html(data.subtitles);
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
