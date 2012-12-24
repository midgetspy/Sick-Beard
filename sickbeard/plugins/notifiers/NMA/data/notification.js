$(document).ready(function(){
    $('#testNMA').click(function(){
        $('#testNMA-result').html(loading);
        var nma_api = $("#nma_api").val();
        var nma_priority = $("#nma_priority").val();
        var nma_result = $.get(sbRoot+"/home/testNMA", {'nma_api': nma_api, 'nma_priority': nma_priority}, 
        function (data){ $('#testNMA-result').html(data); });
    });
});
