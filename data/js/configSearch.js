$(document).ready(function(){

	function toggle_torrent_title(){
		if ($('#use_torrents').prop('checked'))
			$('#no-torrents').show();
		else
			$('#no-torrents').hide();
	}
	
    $.fn.nzb_method_handler = function() {
        
        var selectedProvider = $('#nzb_method :selected').val();

        if (selectedProvider == "blackhole") {
            $('#blackhole_settings').show();
            $('#sabnzbd_settings').hide();
            $('#nzbget_settings').hide();
        } else if (selectedProvider == "nzbget") {
            $('#blackhole_settings').hide();
            $('#sabnzbd_settings').hide();
            $('#nzbget_settings').show();
        } else {
            $('#blackhole_settings').hide();
            $('#sabnzbd_settings').show();
            $('#nzbget_settings').hide();
        }

    }

    $('#nzb_method').change($(this).nzb_method_handler);

    $(this).nzb_method_handler();

    $('#use_torrents').click(function(){
    	toggle_torrent_title();
    });
    
    toggle_torrent_title();
    
});
