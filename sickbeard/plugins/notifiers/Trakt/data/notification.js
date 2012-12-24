$(document).ready(function(){
    $('#testTrakt').click(function(){
        $('#testTrakt-result').html(loading);
        var trakt_api = $("#trakt_api").val();
        var trakt_username = $("#trakt_username").val();
        var trakt_password = $("#trakt_password").val();

        $.get(sbRoot+"/home/testTrakt", {'api': trakt_api, 'username': trakt_username, 'password': trakt_password},
        function (data){ $('#testTrakt-result').html(data); });
    });
});
