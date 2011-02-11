$(document).ready(function(){

    $('#continue_1').click(function(){
        $('#newShowAccordion').accordion('activate', 1);
    });
    
    $('#continue_2').click(function(){
        $('#newShowAccordion').accordion('activate', 2);
    });
    
    $('#back_2').click(function(){
        $('#newShowAccordion').accordion('activate', 0);
    });
    
    $('#continue_3').click(function(){
        alert('done');
    });
    
    $('#back_3').click(function(){
        $('#newShowAccordion').accordion('activate', 1);
    });
    
    $('#addShowButton').click(function(){
        
        // if they haven't picked a show don't let them submit
        if (!$("input[name='whichSeries']:checked").val()) {
            alert('You must choose a show to continue');
            $('#newShowAccordion').accordion('activate', 0);
            return false;
        }
        return true;

    });
    
    $(function() {
        $("#newShowAccordion").accordion({
            clearStyle: false,
        });
    });
    
    $('#nameToSearch').focus();

});