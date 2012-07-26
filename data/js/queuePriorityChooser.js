$(document).ready(function(){
	if (display_priorities && use_nzbs && nzb_method != "blackhole") {
		$('#queuePriorities').show();
	}else{
		$('#queuePriorities').hide();
	}
});