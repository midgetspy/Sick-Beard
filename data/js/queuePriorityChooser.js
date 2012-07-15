$(document).ready(function(){
	if (use_nzbs && nzb_method != "blackhole") {
		$('#queuePriorities').show();
	}else{
		$('#queuePriorities').hide();
	}
});