$(document).ready(function(){
    var loading = '<img src="'+sbRoot+'/images/loading16.gif" height="16" width="16" />';
    var notify_data = null;

    $('#testGrowl').click(function(){
        $('#testGrowl-result').html(loading);
        var growl_host = $("#growl_host").val();
        var growl_password = $("#growl_password").val();
        var growl_result = $.get(sbRoot+"/home/testGrowl", {'host': growl_host, 'password': growl_password}, 
        function (data){ $('#testGrowl-result').html(data); });
    });

    $('#testProwl').click(function(){
        $('#testProwl-result').html(loading);
        var prowl_api = $("#prowl_api").val();
        var prowl_priority = $("#prowl_priority").val();
        var prowl_result = $.get(sbRoot+"/home/testProwl", {'prowl_api': prowl_api, 'prowl_priority': prowl_priority}, 
        function (data){ $('#testProwl-result').html(data); });
    });

    $('#testXBMC').click(function(){
        $('#testXBMC-result').html(loading);
        var xbmc_host = $("#xbmc_host").val();
        var xbmc_username = $("#xbmc_username").val();
        var xbmc_password = $("#xbmc_password").val();
        
        $.get(sbRoot+"/home/testXBMC", {'host': xbmc_host, 'username': xbmc_username, 'password': xbmc_password}, 
        function (data){ $('#testXBMC-result').html(data); });
    });

    $('#testPLEX').click(function(){
        $('#testPLEX-result').html(loading);
        var plex_host = $("#plex_host").val();
        var plex_username = $("#plex_username").val();
        var plex_password = $("#plex_password").val();
        
        $.get(sbRoot+"/home/testPLEX", {'host': plex_host, 'username': plex_username, 'password': plex_password}, 
        function (data){ $('#testPLEX-result').html(data);});
    });

    $('#testNotifo').click(function(){
        $('#testNotifo-result').html(loading);
        var notifo_username = $("#notifo_username").val();
        var notifo_apisecret = $("#notifo_apisecret").val();
        $.get(sbRoot+"/home/testNotifo", {'username': notifo_username, 'apisecret': notifo_apisecret},
        function (data){ $('#testNotifo-result').html(data); });
    });

    $('#testBoxcar').click(function(){
        $('#testBoxcar-result').html(loading);
        var boxcar_username = $("#boxcar_username").val();
        $.get(sbRoot+"/home/testBoxcar", {'username': boxcar_username},
        function (data){ $('#testBoxcar-result').html(data); });
    });

    $('#testPushover').click(function(){
        $('#testPushover-result').html(loading);
        var pushover_userkey = $("#pushover_userkey").val();
        $.get(sbRoot+"/home/testPushover", {'userKey': pushover_userkey},
        function (data){ $('#testPushover-result').html(data); });
    });

    $('#testLibnotify').click(function(){
        $('#testLibnotify-result').html(loading);
        $.get(sbRoot+"/home/testLibnotify",
        function(message){ $('#testLibnotify-result').html(message); });
    });

    $('#testEmail').click(function () {
        var status, host, port, tls, from, user, pwd, err, to;
        status = $('#testEmail-result');
        status.html(loading);
        host = $("#email_host").val();
        host = host.length > 0 ? host : null;
        port = $("#email_port").val();
        port = port.length > 0 ? port : null;
        tls  = $("#email_tls").attr('checked') !== undefined ? 1 : 0;
        from = $("#email_from").val();
        from = from.length > 0 ? from : 'root@localhost';
        user = $("#email_user").val().trim();
        pwd = $("#email_password").val();
        err = '';
        if (host === null) {
            err += '<li style="color: red;">You must specify an SMTP hostname!</li>';
        }
        if (port === null) {
            err += '<li style="color: red;">You must specify an SMTP port!</li>';
        } else if (port.match(/^\d+$/) === null || parseInt(port, 10) > 65535) {
            err += '<li style="color: red;">SMTP port must be between 0 and 65535!</li>';
        }
        if (err.length > 0) {
            err = '<ol>' + err + '</ol>';
            status.html(err);
        } else {
            to = prompt('Enter an email address to send the test to:', null);
            if (to === null || to.length === 0 || to.match(/.*@.*/) === null) {
                status.html('<p style="color: red;">You must provide a recipient email address!</p>');
            } else {
                $.get(sbRoot + "/home/testEmail", {host: host, port: port, smtp_from: from, use_tls: tls, user: user, pwd: pwd, to: to},
                    function (msg) { $('#testEmail-result').html(msg); });
            }
        }
    });
  
    $('#twitterStep1').click(function(){
        $('#testTwitter-result').html(loading);
        var twitter1_result = $.get(sbRoot+"/home/twitterStep1", function (data){window.open(data)})
        .complete(function() { $('#testTwitter-result').html('<b>Step1:</b> Confirm Authorization'); });
    });

    $('#twitterStep2').click(function(){
        $('#testTwitter-result').html(loading);
        var twitter_key = $("#twitter_key").val();
        $.get(sbRoot+"/home/twitterStep2", {'key': twitter_key}, 
        function (data){ $('#testTwitter-result').html(data); });
    });

    $('#testTwitter').click(function(){
        $.get(sbRoot+"/home/testTwitter", 
        function (data){ $('#testTwitter-result').html(data); });
    });

    $('#settingsNMJ').click(function(){
        if (!$('#nmj_host').val()) {
            alert('Please fill in the Popcorn IP address');
            $('#nmj_host').focus();
            return;
        }
        $('#testNMJ-result').html(loading);
        var nmj_host = $('#nmj_host').val();
        
        $.get(sbRoot+"/home/settingsNMJ", {'host': nmj_host}, 
        function (data){
            if (data == null) {
                $('#nmj_database').removeAttr('readonly');
                $('#nmj_mount').removeAttr('readonly');
            }
            var JSONData = $.parseJSON(data);
            $('#testNMJ-result').html(JSONData.message);
            $('#nmj_database').val(JSONData.database);
            $('#nmj_mount').val(JSONData.mount);
            
            if (JSONData.database)
                $('#nmj_database').attr('readonly', true);
            else
                $('#nmj_database').removeAttr('readonly');
            
            if (JSONData.mount)
                $('#nmj_mount').attr('readonly', true);
            else
                $('#nmj_mount').removeAttr('readonly');
        });
    });

    $('#testNMJ').click(function(){
        $('#testNMJ-result').html(loading);
        var nmj_host = $("#nmj_host").val();
        var nmj_database = $("#nmj_database").val();
        var nmj_mount = $("#nmj_mount").val();
        
        $.get(sbRoot+"/home/testNMJ", {'host': nmj_host, 'database': nmj_database, 'mount': nmj_mount}, 
        function (data){ $('#testNMJ-result').html(data); });
    });

    $('#testTrakt').click(function(){
        $('#testTrakt-result').html(loading);
        var trakt_api = $("#trakt_api").val();
        var trakt_username = $("#trakt_username").val();
        var trakt_password = $("#trakt_password").val();

        $.get(sbRoot+"/home/testTrakt", {'api': trakt_api, 'username': trakt_username, 'password': trakt_password},
        function (data){ $('#testTrakt-result').html(data); });
    });

    $('#testNMA').click(function(){
        $('#testNMA-result').html(loading);
        var nma_api = $("#nma_api").val();
        var nma_priority = $("#nma_priority").val();
        var nma_result = $.get(sbRoot+"/home/testNMA", {'nma_api': nma_api, 'nma_priority': nma_priority}, 
        function (data){ $('#testNMA-result').html(data); });
    });

    $('#email_show').change(function () {
        var key = parseInt($('#email_show').val(), 10);
        $('#email_show_list').val(key >= 0 ? notify_data[key.toString()].list : '');
    });

    // Update the internal data struct anytime settings are saved to the server
    $('#email_show').bind('notify', function () { load_show_notify_lists(); });

    function load_show_notify_lists() {
        $.get(sbRoot + "/home/loadShowNotifyLists", function (data) {
            var list, html, s;
            list = $.parseJSON(data);
            notify_data = list;
            if (list._size === 0) {
                return;
            }
            html = '<option value="-1">-- Select --</option>';
            for (s in list) {
                if (s.charAt(0) !== '_') {
                    html += '<option value="' + list[s].id + '">' + $('<div/>').text(list[s].name).html() + '</option>';
                }
            }
            $('#email_show').html(html);
            $('#email_show_list').val('');
        });
    }
    // Load the per show notify lists everytime this page is loaded
    load_show_notify_lists();
});
