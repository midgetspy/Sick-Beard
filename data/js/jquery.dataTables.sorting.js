$(document).ready(function(){ 

	$.fn.dataTableExt.oJUIClasses.sSortAsc = "ui-state-default sortedHeader";
	$.fn.dataTableExt.oJUIClasses.sSortDesc = "ui-state-default sortedHeader";

	function sortize_title(title)
	{
	    var x = title.replace(/^(The|A)\s/i,'');
	    if (x.indexOf('Loading...') == 0)
	        x = x.replace('Loading...','000');
	       
	    return x;
	}
	
	function sortize_quality(quality)
	{
		if (quality == 'Custom')
			return 4;
		else if (quality == 'HD')
			return 3;
		else if (quality == 'Best')
			return 2;
		else if (quality == 'SD')
			return 1;
		else if (quality == 'Any')
			return 0;
	}

	$.fn.dataTableExt.oSort['titles-asc']  = function(a,b) {
	    var x = sortize_title(a);
	    var y = sortize_title(b);
	    return ((x < y) ? -1 : ((x > y) ? 1 : 0));
	};

	$.fn.dataTableExt.oSort['titles-desc'] = function(a,b) {
	    var x = sortize_title(a);
	    var y = sortize_title(b);
	    return ((x < y) ? 1 : ((x > y) ? -1 : 0));
	};
	
	$.fn.dataTableExt.oSort['quality-asc'] = function(a,b) {
		var x = sortize_quality(a);
		var y = sortize_quality(b);
        
	    return ((x < y) ? 1 : ((x > y) ? -1 : 0));
	};
	$.fn.dataTableExt.oSort['quality-desc']  = function(a,b) {
		var x = sortize_quality(a);
		var y = sortize_quality(b);
        
	    return ((x < y) ? -1 : ((x > y) ? 1 : 0));
	};
	
	$.fn.dataTableExt.oSort['alt-string-asc']  = function(a,b) {
	   var x = a.match(/alt="(.*?)"/)[1].toLowerCase();
	   var y = b.match(/alt="(.*?)"/)[1].toLowerCase();
	   return ((x < y) ? -1 : ((x > y) ?  1 : 0));
	};
		 
	$.fn.dataTableExt.oSort['alt-string-desc'] = function(a,b) {
	   var x = a.match(/alt="(.*?)"/)[1].toLowerCase();
	   var y = b.match(/alt="(.*?)"/)[1].toLowerCase();
	   return ((x < y) ?  1 : ((x > y) ? -1 : 0));
	};

	$.fn.dataTableExt.oSort['link-text-asc']  = function(a,b) {
	   var x = a.match(/>\s*(.*?)\s*<\s*\/\s*a\s*>/);
	   var y = b.match(/>\s*(.*?)\s*<\s*\/\s*a\s*>/);

	   x = x != null ? x[1].toLowerCase() : a.toLowerCase();
	   y = y != null ? y[1].toLowerCase() : b.toLowerCase();
	   
	   return ((x < y) ? -1 : ((x > y) ?  1 : 0));
	};
		 
	$.fn.dataTableExt.oSort['link-text-desc'] = function(a,b) {
	   var x = a.match(/>\s*(.*?)\s*<\s*\/\s*a\s*>/);
	   var y = b.match(/>\s*(.*?)\s*<\s*\/\s*a\s*>/);

	   x = x != null ? x[1].toLowerCase() : a.toLowerCase();
	   y = y != null ? y[1].toLowerCase() : b.toLowerCase();
	   
	   return ((x < y) ?  1 : ((x > y) ? -1 : 0));
	};

	$.fn.dataTableExt.oSort['empty-last-asc']  = function(a,b) {
		if (a == "")
			return 1;
		if (b == "")
			return -1;
 		return ((a < b) ? -1 : ((a > b) ?  1 : 0));
	};
	 
	$.fn.dataTableExt.oSort['empty-last-desc'] = function(a,b) {
		if (a == "")
			return 1;
		if (b == "")
			return -1;
 		return ((a < b) ? 1 : ((a > b) ?  -1 : 0));
	};

});