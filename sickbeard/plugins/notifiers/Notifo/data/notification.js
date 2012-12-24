$(document).ready(function(){
    $('#testNotifo').click(function(){
        $('#testNotifo-result').html(loading);
        var notifo_username = $("#notifo_username").val();
        var notifo_apisecret = $("#notifo_apisecret").val();
        $.get(sbRoot+"/home/testNotifo", {'username': notifo_username, 'apisecret': notifo_apisecret},
        function (data){ $('#testNotifo-result').html(data); });
    });
});
