$(document).ready(function(){

    $('#addShowButton').click(function(){
        
        // if they haven't picked a show don't let them submit
        if (!$("input[name='whichSeries']:checked").val()) {
            alert('You must choose a show to continue');
            return false;
        }

        $('#addShowForm').submit()

    });
    
    /***********************************************
    * jQuery Form to Form Wizard- (c) Dynamic Drive (www.dynamicdrive.com)
    * This notice MUST stay intact for legal use
    * Visit http://www.dynamicdrive.com/ for this script and 100s more.
    ***********************************************/

    var myform=new formtowizard({
        formid: 'addShowForm',
        revealfx: ['slide', 500]
    })

    $('#nameToSearch').focus();



});