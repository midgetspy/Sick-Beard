$(document).ready(function(){
    var loading = '<img src="'+sbRoot+'/images/loading16.gif" height="16" width="16" />';
    
	function toggle_torrent_title(){
		if ($('#use_torrents').prop('checked'))
			$('#no-torrents').show();
		else
			$('#no-torrents').hide();
	}
	
    $.fn.nzb_method_handler = function() {
        
        var selectedProvider = $('#nzb_method :selected').val();

        if (selectedProvider == "blackhole") {
            $('#nzb_blackhole_settings').show();
            $('#sabnzbd_settings').hide();
            $('#testSABnzbd').hide();
            $('#testSABnzbd-result').hide();
            $('#nzbget_settings').hide();
        } else if (selectedProvider == "nzbget") {
            $('#nzb_blackhole_settings').hide();
            $('#sabnzbd_settings').hide();
            $('#testSABnzbd').hide();
            $('#testSABnzbd-result').hide();
            $('#nzbget_settings').show();
        } else {
            $('#nzb_blackhole_settings').hide();
            $('#sabnzbd_settings').show();
            $('#testSABnzbd').show();
            $('#testSABnzbd-result').show();
            $('#nzbget_settings').hide();
        }

    }

    $('#nzb_method').change($(this).nzb_method_handler);

    $(this).nzb_method_handler();

    $.fn.torrent_method_handler = function() {
        
        var selectedProvider = $('#torrent_method :selected').val();

        if (selectedProvider == "blackhole") {
            $('#torrent_blackhole_settings').show();
            $('#rtorrent_settings').hide();
        } else {
            $('#torrent_blackhole_settings').hide();
            $('#rtorrent_settings').show();
        }

    }

    $('#torrent_method').change($(this).torrent_method_handler);

    $(this).torrent_method_handler();

    $('#testSABnzbd').click(function(){
        $('#testSABnzbd-result').html(loading);
        var sab_host = $("input=[name='sab_host']").val();
        var sab_username = $("input=[name='sab_username']").val();
        var sab_password = $("input=[name='sab_password']").val();
        var sab_apiKey = $("input=[name='sab_apikey']").val();
        
        $.get(sbRoot+"/home/testSABnzbd", {'host': sab_host, 'username': sab_username, 'password': sab_password, 'apikey': sab_apiKey}, 
        function (data){ $('#testSABnzbd-result').html(data); });
    });
    
    $('#use_torrents').click(function(){
    	toggle_torrent_title();
    });
    
    toggle_torrent_title();
    
});
