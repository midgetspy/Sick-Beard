$(document).ready(function(){

    var multiExamples = [["1x02-03", "s01e02-03", "S01E02-03"],
                         ["1x02 - 1x03", "s01e02 - s01e03", "S01E02 - S01E03"],
                         ["1x02x03", "s01e02e03", "S01E02E03"]
                         ]

    $.fn.setExampleText = function() { 

        exampleText = ""
        multiExampleText = ""
        
        if ($('#naming_show_name').attr('checked')) {
            exampleText += "Show Name - ";
            multiExampleText += "Show Name - ";
        }
        
        var numStyleSel = $('#naming_ep_type :selected')
        var multiNumStyleSel = $('#naming_multi_ep_type :selected')
        
        exampleText += numStyleSel.text()
        multiExampleText += multiExamples[multiNumStyleSel.val()][numStyleSel.val()]
        
        exampleText += " - Episode Name"
        multiExampleText += " - Episode Name(s)"
        
        $('#multiExampleText').text(multiExampleText);

        return $('#normalExampleText').text(exampleText); 
    };

  $(this).setExampleText();

  $('#naming_show_name').click(function(){
        $(this).setExampleText();
    });  

  $('#naming_multi_ep_type').change(function(){
        $(this).setExampleText();
    });  

  $('#naming_ep_type').change(function(){
        $(this).setExampleText();
    });  

});