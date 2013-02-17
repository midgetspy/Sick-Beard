(function(){

	$.ajaxEpSearch = {
	    defaults: {
	        size:				16,
	        colorRow:         	false,
	        loadingImage:		'loading16_dddddd.gif',
	        noImage:			'no16.png',
	        yesImage:			'yes16.png'
	    }
	};

	$.fn.ajaxEpSearch = function(options){
		options = $.extend({}, $.ajaxEpSearch.defaults, options);
		
	    $('.epSearch').click(function(){
	        var parent = $(this).parent();
	        
	        // put the ajax spinner (for non white bg) placeholder while we wait
	        parent.empty();
	        parent.append($("<img/>").attr({"src": sbRoot+"/images/"+options.loadingImage, "height": options.size, "alt": "", "title": "loading"}));
	        
	        $.getJSON($(this).attr('href'), function(data){
	            // if they failed then just put the red X
	            if (data.result == 'failure') {
	                img_name = options.noImage;
	                img_result = 'failed';

	            // if the snatch was successful then apply the corresponding class and fill in the row appropriately
	            } else {
	                img_name = options.yesImage;
	                img_result = 'success';
	                // color the row
	                if (options.colorRow)
	                	parent.parent().removeClass('skipped wanted qual good unaired').addClass('good');
	                // applying the quality class
                    var rSearchTerm = /(\w+)\s\((.+?)\)/;
	                    HtmlContent = data.result.replace(rSearchTerm,"$1"+' <span class="quality '+data.quality+'">'+"$2"+'</span>');
	                // update the status column if it exists
                    parent.siblings('.status_column').html(HtmlContent)    	                  
	            }

	            // put the corresponding image as the result for the the row
	            parent.empty();
	            parent.append($("<img/>").attr({"src": sbRoot+"/images/"+img_name, "height": options.size, "alt": img_result, "title": img_result}));
	        });

	        // fon't follow the link
	        return false;
	    });
	}
})();
