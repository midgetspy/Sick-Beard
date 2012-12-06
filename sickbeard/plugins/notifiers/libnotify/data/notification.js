$(document).ready(function(){
    $('#testLibnotify').click(function(){
        $('#testLibnotify-result').html(loading);
        $.get(sbRoot+"/home/testLibnotify",
        function(message){ $('#testLibnotify-result').html(message); });
    });
});
