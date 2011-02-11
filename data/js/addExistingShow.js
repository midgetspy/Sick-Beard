$(document).ready(function() 
{ 
    $("#addRootDirTable").tablesorter({
        sortList: [[1,0]],
        widgets: ['zebra'],
        headers: {
            0: { sorter: false }
        }
    });

    $('#checkAll').click(function(){
    
        var seasCheck = this;

        $('.dirCheck').each(function(){
           this.checked = seasCheck.checked 
        });
    });

});