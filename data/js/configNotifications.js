$(document).ready(function(){
    var loading = '<img src="'+sbRoot+'/images/loading16.gif" height="16" width="16" />';

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

    $('#testSMS').click(function(){
        $('#testSMS-result').html(loading);
        var sms_email = $("#sms_email").val();
        var sms_password = $("#sms_password").val();
        var sms_phonenumber = $("#sms_phonenumber").val();
        
        $.get(sbRoot+"/home/testSMS", {'email': sms_email, 'password': sms_password, 'phonenumber': sms_phonenumber}, 
        function (data){ $('#testSMS-result').html(data); });
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

    $('#testLibnotify').click(function(){
        $('#testLibnotify-result').html(loading);
        $.get(sbRoot+"/home/testLibnotify",
        function(message){ $('#testLibnotify-result').html(message); });
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
});
