$(document).ready(function(){
    $('#testXBMC').click(function(){
        $('#testXBMC-result').html(loading);
        var xbmc_host = $("#xbmc_host").val();
        var xbmc_username = $("#xbmc_username").val();
        var xbmc_password = $("#xbmc_password").val();
        
        $.get(sbRoot+"/home/testXBMC", {'host': xbmc_host, 'username': xbmc_username, 'password': xbmc_password}, 
        function (data){ $('#testXBMC-result').html(data); });
    });
});
