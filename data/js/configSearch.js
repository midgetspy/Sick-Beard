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
            $('#content_use_nzbs #blackhole_settings').show();
            $('#sabnzbd_settings').hide();
            $('#testSABnzbd').hide();
            $('#testSABnzbd-result').hide();
            $('#nzbget_settings').hide();
        } else if (selectedProvider == "nzbget") {
            $('#content_use_nzbs #blackhole_settings').hide();
            $('#sabnzbd_settings').hide();
            $('#testSABnzbd').hide();
            $('#testSABnzbd-result').hide();
            $('#nzbget_settings').show();
        } else {
            $('#content_use_nzbs #blackhole_settings').hide();
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
            $('#content_use_torrents #blackhole_settings').show();
            $('#utorrent_settings').hide();
            $('#testUTorrent').hide();
            $('#testUTorrent-result').hide();
        } else {
            $('#content_use_torrents #blackhole_settings').hide();
            $('#utorrent_settings').show();
            $('#testUTorrent').show();
            $('#testUTorrent-result').show();
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

    $('#testUTorrent').click(function(){
        $('#testUTorrent-result').html(loading);
        var utorrent_host = $("input=[name='utorrent_host']").val();
        var utorrent_username = $("input=[name='utorrent_username']").val();
        var utorrent_password = $("input=[name='utorrent_password']").val();

        $.get(sbRoot+"/home/testUTorrent", {'host': utorrent_host, 'username': utorrent_username, 'password': utorrent_password},
            function (data){ $('#testUTorrent-result').html(data); });
    });
    
    $('#use_torrents').click(function(){
    	toggle_torrent_title();
    });
    
    toggle_torrent_title();
    
});
