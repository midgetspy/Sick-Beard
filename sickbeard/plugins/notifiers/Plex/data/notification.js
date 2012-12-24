$(document).ready(function(){
    $('#testPLEX').click(function(){
        $('#testPLEX-result').html(loading);
        var plex_host = $("#plex_host").val();
        var plex_username = $("#plex_username").val();
        var plex_password = $("#plex_password").val();
        
        $.get(sbRoot+"/home/testPLEX", {'host': plex_host, 'username': plex_username, 'password': plex_password}, 
        function (data){ $('#testPLEX-result').html(data);});
    });
});
