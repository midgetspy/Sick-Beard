$(document).ready(function(){
    var loading = '<img src="' + sbRoot + '/images/loading16.gif" height="16" width="16" />';

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

    };

    $('#nzb_method').change($(this).nzb_method_handler);

    $(this).nzb_method_handler();

    $('#testSABnzbd').click(function(){
        $('#testSABnzbd-result').html(loading);
        var sab_host = $("input=[name='sab_host']").val();
        var sab_username = $("input=[name='sab_username']").val();
        var sab_password = $("input=[name='sab_password']").val();
        var sab_apiKey = $("input=[name='sab_apikey']").val();

        $.get(sbRoot + "/home/testSABnzbd", {'host': sab_host, 'username': sab_username, 'password': sab_password, 'apikey': sab_apiKey}, 
        function (data){ $('#testSABnzbd-result').html(data); });
    });

    $.fn.torrent_method_handler = function(){
        var selectedProvider = $('#torrent_method :selected').val();

        if (selectedProvider == 'blackhole') {
            $('#torrent_blackhole_settings').show();
            $('#transmission_settings').hide();
            $('#testTransmission').hide();
            $('#testTransmissionResult').hide();
        } else if (selectedProvider == 'transmission') {
            $('#torrent_blackhole_settings').hide();
            $('#transmission_settings').show();
            $('#testTransmission').show();
            $('#testTransmissionResult').show();
        }
    }

    $('#torrent_method').change($(this).torrent_method_handler);

    $(this).torrent_method_handler();

    $('#testTransmission').click(function(){
        $('#testTransmission-result').html(loading);
        var transmission_host = $("input=[name='transmission_host']").val();
        var transmission_port = $("input=[name='transmission_port']").val();
        var transmission_rpc_path = $("input=[name='transmission_rpc_path']").val();
        var transmission_username = $("input=[name='transmission_username']").val();
        var transmission_password = $("input=[name='transmission_password']").val();

        $.get(sbRoot + "/home/testTransmission", {'host': transmission_host, 'port': transmission_port, 'rpc_path': transmission_rpc_path, 'username': transmission_username, 'password': transmission_password},
        function (data){ $('#testTransmission-result').html(data); });
    });

});
