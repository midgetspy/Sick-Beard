$(document).ready(function(){
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
});
