$(document).ready(function(){
    var loading = '<img src="'+sbRoot+'/images/loading16.gif" height="16" width="16" />';

    $('#testGrowl').click(function(){
        document.getElementById('testGrowl-result').innerHTML = loading;
        var growl_host = $("#growl_host").val();
        var growl_password = $("#growl_password").val();
        var growl_result = $.get(sbRoot+"/home/testGrowl", {'host': growl_host, 'password': growl_password}, 
        function (data){ document.getElementById('testGrowl-result').innerHTML = data;});
    });

    $('#testProwl').click(function(){
        document.getElementById('testProwl-result').innerHTML = loading;
        var prowl_api = $("#prowl_api").val();
        var prowl_priority = $("#prowl_priority").val();
        var prowl_result = $.get(sbRoot+"/home/testProwl", {'prowl_api': prowl_api, 'prowl_priority': prowl_priority}, 
        function (data){ document.getElementById('testProwl-result').innerHTML = data;});
    });

    $('#testXBMC').click(function(){
        document.getElementById('testXBMC-result').innerHTML = loading;
        var xbmc_host = $("#xbmc_host").val();
        var xbmc_username = $("#xbmc_username").val();
        var xbmc_password = $("#xbmc_password").val();
        
        $.get(sbRoot+"/home/testXBMC", {'host': xbmc_host, 'username': xbmc_username, 'password': xbmc_password}, 
        function (data){ document.getElementById('testXBMC-result').innerHTML = data;});
    });

    $('#testNotifo').click(function(){
        document.getElementById('testNotifo-result').innerHTML = loading;
        var notifo_username = $("#notifo_username").val();
        var notifo_apisecret = $("#notifo_apisecret").val();
        $.get(sbRoot+"/home/testNotifo", {'username': notifo_username, 'apisecret': notifo_apisecret},
        function (data){ document.getElementById('testNotifo-result').innerHTML = data; });
    });

    $('#testLibnotify').click(function(){
        $('#testLibnotify-result').html(loading);
        $.get("$sbRoot/home/testLibnotify",
        function(message){ document.getElementById('testLibnotify-result').innerHTML = message; });
    });
  
    $('#twitterStep1').click(function(){
        document.getElementById('testTwitter-result').innerHTML = loading;
        var twitter1_result = $.get(sbRoot+"/home/twitterStep1", function (data){window.open(data)})
        .complete(function() { document.getElementById('testTwitter-result').innerHTML = '<b>Step1:</b> Confirm Authorization'; });
    });

    $('#twitterStep2').click(function(){
        document.getElementById('testTwitter-result').innerHTML = loading;
        var twitter_key = $("#twitter_key").val();
        $.get(sbRoot+"/home/twitterStep2", {'key': twitter_key}, 
        function (data){ document.getElementById('testTwitter-result').innerHTML = data; });
    });

    $('#testTwitter').click(function(){
        $.get(sbRoot+"/home/testTwitter", 
        function (data){ document.getElementById('testTwitter-result').innerHTML = data;});
    });

    $(".enabler").each(function(){
        if (!$(this).attr('checked'))
            $('#content_'+$(this).attr('id')).hide();
    });

    $(".enabler").click(function() {
        if ($(this).attr('checked'))
            $('#content_'+$(this).attr('id')).show();
        else
            $('#content_'+$(this).attr('id')).hide();
  });
});