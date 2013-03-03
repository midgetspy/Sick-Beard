$(document).ready(function(){
    var loading = '<img src="' + sbRoot + '/images/loading16.gif" height="16" width="16" />';

    $('#testGrowl').click(function(){
        $('#testGrowl-result').html(loading);
        var growl_host = $("#growl_host").val();
        var growl_password = $("#growl_password").val();
        $.get(sbRoot + "/home/testGrowl", {'host': growl_host, 'password': growl_password},
            function (data) { $('#testGrowl-result').html(data); });
    });

    $('#testProwl').click(function() {
        $('#testProwl-result').html(loading);
        var prowl_api = $("#prowl_api").val();
        var prowl_priority = $("#prowl_priority").val();
        $.get(sbRoot + "/home/testProwl", {'prowl_api': prowl_api, 'prowl_priority': prowl_priority},
            function (data) { $('#testProwl-result').html(data); });
    });

    $('#testXBMC').click(function() {
        $("#testXBMC").attr("disabled", true);
        $('#testXBMC-result').html(loading);
        var xbmc_host = $("#xbmc_host").val();
        var xbmc_username = $("#xbmc_username").val();
        var xbmc_password = $("#xbmc_password").val();
        
        $.get(sbRoot + "/home/testXBMC", {'host': xbmc_host, 'username': xbmc_username, 'password': xbmc_password})
            .done(function (data) {
                $('#testXBMC-result').html(data);
                $("#testXBMC").attr("disabled", false);
            });
    });

    $('#testPLEX').click(function() {
        $('#testPLEX-result').html(loading);
        var plex_host = $("#plex_host").val();
        var plex_username = $("#plex_username").val();
        var plex_password = $("#plex_password").val();
        $.get(sbRoot + "/home/testPLEX", {'host': plex_host, 'username': plex_username, 'password': plex_password},
            function (data) { $('#testPLEX-result').html(data); });
    });

    $('#testNotifo').click(function() {
        $('#testNotifo-result').html(loading);
        var notifo_username = $("#notifo_username").val();
        var notifo_apisecret = $("#notifo_apisecret").val();
        $.get(sbRoot + "/home/testNotifo", {'username': notifo_username, 'apisecret': notifo_apisecret},
            function (data) { $('#testNotifo-result').html(data); });
    });

    $('#testBoxcar').click(function() {
        $('#testBoxcar-result').html(loading);
        var boxcar_username = $("#boxcar_username").val();
        $.get(sbRoot + "/home/testBoxcar", {'username': boxcar_username},
            function (data) { $('#testBoxcar-result').html(data); });
    });

    $('#testPushover').click(function() {
        $('#testPushover-result').html(loading);
        var pushover_userkey = $("#pushover_userkey").val();
        $.get(sbRoot + "/home/testPushover", {'userKey': pushover_userkey},
            function (data) { $('#testPushover-result').html(data); });
    });

    $('#testLibnotify').click(function() {
        $('#testLibnotify-result').html(loading);
        $.get(sbRoot + "/home/testLibnotify",
            function (data) { $('#testLibnotify-result').html(data); });
    });
  
    $('#twitterStep1').click(function() {
        $('#testTwitter-result').html(loading);
        $.get(sbRoot + "/home/twitterStep1", function (data) {window.open(data); })
            .done(function () { $('#testTwitter-result').html('<b>Step1:</b> Confirm Authorization'); });
    });

    $('#twitterStep2').click(function() {
        $('#testTwitter-result').html(loading);
        var twitter_key = $("#twitter_key").val();
        $.get(sbRoot + "/home/twitterStep2", {'key': twitter_key},
            function (data) { $('#testTwitter-result').html(data); });
    });

    $('#testTwitter').click(function() {
        $.get(sbRoot + "/home/testTwitter",
            function (data) { $('#testTwitter-result').html(data); });
    });

    $('#settingsNMJ').click(function() {
        if (!$('#nmj_host').val()) {
            alert('Please fill in the Popcorn IP address');
            $('#nmj_host').focus();
            return;
        }
        $('#testNMJ-result').html(loading);
        var nmj_host = $('#nmj_host').val();
        
        $.get(sbRoot + "/home/settingsNMJ", {'host': nmj_host},
            function (data) {
                if (data === null) {
                    $('#nmj_database').removeAttr('readonly');
                    $('#nmj_mount').removeAttr('readonly');
                }
                var JSONData = $.parseJSON(data);
                $('#testNMJ-result').html(JSONData.message);
                $('#nmj_database').val(JSONData.database);
                $('#nmj_mount').val(JSONData.mount);

                if (JSONData.database) {
                    $('#nmj_database').attr('readonly', true);
                } else {
                    $('#nmj_database').removeAttr('readonly');
                }
                if (JSONData.mount) {
                    $('#nmj_mount').attr('readonly', true);
                } else {
                    $('#nmj_mount').removeAttr('readonly');
                }
            });
    });

    $('#testNMJ').click(function() {
        $('#testNMJ-result').html(loading);
        var nmj_host = $("#nmj_host").val();
        var nmj_database = $("#nmj_database").val();
        var nmj_mount = $("#nmj_mount").val();
        
        $.get(sbRoot + "/home/testNMJ", {'host': nmj_host, 'database': nmj_database, 'mount': nmj_mount},
            function (data) { $('#testNMJ-result').html(data); });
    });

	$('#settingsNMJv2').click(function() {
        if (!$('#nmjv2_host').val()) {
            alert('Please fill in the Popcorn IP address');
            $('#nmjv2_host').focus();
            return;
        }
        $('#testNMJv2-result').html(loading);
        var nmjv2_host = $('#nmjv2_host').val();
		var nmjv2_dbloc;
		var radios = document.getElementsByName("nmjv2_dbloc");
		for (var i = 0; i < radios.length; i++) {
			if (radios[i].checked) {
				nmjv2_dbloc=radios[i].value;
				break;
			}
		}

        var nmjv2_dbinstance=$('#NMJv2db_instance').val();
        $.get(sbRoot + "/home/settingsNMJv2", {'host': nmjv2_host,'dbloc': nmjv2_dbloc,'instance': nmjv2_dbinstance}, 
        function (data){
            if (data == null) {
                $('#nmjv2_database').removeAttr('readonly');
            }
            var JSONData = $.parseJSON(data);
            $('#testNMJv2-result').html(JSONData.message);
            $('#nmjv2_database').val(JSONData.database);
            
            if (JSONData.database)
                $('#nmjv2_database').attr('readonly', true);
            else
                $('#nmjv2_database').removeAttr('readonly');
        });
    });

    $('#testNMJv2').click(function() {
        $('#testNMJv2-result').html(loading);
        var nmjv2_host = $("#nmjv2_host").val();
        
        $.get(sbRoot + "/home/testNMJv2", {'host': nmjv2_host}, 
        function (data){ $('#testNMJv2-result').html(data); });
    });

    $('#testTrakt').click(function() {
        $('#testTrakt-result').html(loading);
        var trakt_api = $("#trakt_api").val();
        var trakt_username = $("#trakt_username").val();
        var trakt_password = $("#trakt_password").val();

        $.get(sbRoot + "/home/testTrakt", {'api': trakt_api, 'username': trakt_username, 'password': trakt_password},
            function (data) { $('#testTrakt-result').html(data); });
    });

    $('#testNMA').click(function() {
        $('#testNMA-result').html(loading);
        var nma_api = $("#nma_api").val();
        var nma_priority = $("#nma_priority").val();
        $.get(sbRoot + "/home/testNMA", {'nma_api': nma_api, 'nma_priority': nma_priority},
            function (data) { $('#testNMA-result').html(data); });
    });
});
