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
            $('#blackhole_settings').show();
            $('#sabnzbd_settings').hide();
            $('#testSABnzbd').hide();
            $('#testSABnzbd-result').hide();
            $('#nzbget_settings').hide();
        } else if (selectedProvider == "nzbget") {
            $('#blackhole_settings').hide();
            $('#sabnzbd_settings').hide();
            $('#testSABnzbd').hide();
            $('#testSABnzbd-result').hide();
            $('#nzbget_settings').show();
        } else {
            $('#blackhole_settings').hide();
            $('#sabnzbd_settings').show();
            $('#testSABnzbd').show();
            $('#testSABnzbd-result').show();
            $('#nzbget_settings').hide();
        }

    }
    $.fn.torrent_method_handler = function() {
        
        var selectedProvider = $('#torrent_method :selected').val();

        if (selectedProvider == "blackhole") {
            $('#t_blackhole_settings').show();
            $('#torrent_settings').hide();
        } else if (selectedProvider == "utorrent"){
            $('#t_blackhole_settings').hide();
            $('#torrent_settings').show();
            $('#torrent_directory').hide();
            $('#host_desc').text('uTorrent Host');
            $('#username_desc').text('uTorrent Username');
            $('#password_desc').text('uTorrent Password');
        } else if (selectedProvider == "transmission"){
            $('#t_blackhole_settings').hide();
            $('#torrent_settings').show();
            $('#torrent_directory').show();
            $('#host_desc').html('Transmission Host');
            $('#username_desc').text('Transmission Username');
            $('#password_desc').text('Transmission Password');
            $('#directory_desc').text('Transmission Directory');
		} else if (selectedProvider == "downloadstation") {
			$('#t_blackhole_settings').hide();
			$('#torrent_settings').show();
			$('#torrent_directory').show();
			$('#host_desc').html('Download Station Host');
			$('#username_desc').text('Synology Username');
			$('#password_desc').text('Synology Password');
			$('#directory_desc').text('Download Station Directory');
        }
    }
    $('#nzb_method').change($(this).nzb_method_handler);

    $(this).nzb_method_handler();

    $('#testSABnzbd').click(function(){
        $('#testSABnzbd-result').html(loading);
        var sab_host = $("input=[name='sab_host']").val();
        var sab_username = $("input=[name='sab_username']").val();
        var sab_password = $("input=[name='sab_password']").val();
        var sab_apiKey = $("input=[name='sab_apikey']").val();
        
        $.get(sbRoot+"/home/testSABnzbd", {'host': sab_host, 'username': sab_username, 'password': sab_password, 'apikey': sab_apiKey}, 
        function (data){ $('#testSABnzbd-result').html(data); });
    });
    
	$('#torrent_method').change($(this).torrent_method_handler);
	$(this).torrent_method_handler(); 
	
	$('#testTorrent').click(function(){
        $('#testTorrent-result').html(loading);
        var torrent_method = $('#torrent_method :selected').val();        
        var torrent_host = $("input=[name='torrent_host']").val();
        var torrent_username = $("input=[name='torrent_username']").val();
        var torrent_password = $("input=[name='torrent_password']").val();
        
        $.get(sbRoot+"/home/testTorrent", {'torrent_method': torrent_method, 'host': torrent_host, 'username': torrent_username, 'password': torrent_password}, 
        function (data){ $('#testTorrent-result').html(data); });
    });
    
});
