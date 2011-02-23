$(document).ready(function(){

    function showProgressBox(text, numPieces) {
        $('#dialog').dialog({modal: true, closeOnEscape: false, draggable: false, resizable: false, title: text, buttons: {}})
        
        var bar = document.createElement('div')
        $(bar).progressbar({value: 0})
        $(bar).attr('numPieces', numPieces)
        $(bar).attr('id', 'progressBar')
        $('#dialog').append(bar)
    }

    function progressBarUpdate()
    {
        var bar = $('#progressBar')
       
        bar.progressbar('value', bar.progressbar('value') + 100 / bar.attr('numPieces'));
        if (bar.progressbar('value') > 99)
        {
            bar.progressbar('destroy')
            $('#dialog').dialog('close')
        }
    }

    $('#changeStatus').click(function() {
        $('#dialog').dialog({modal: true, title: 'Are you sure you want to mark all selected episodes as wanted?', minheight: '0x', resizable: false, buttons: {"Mark as wanted": function(){
            
            var sbRoot = $('#sbRoot').val()
            var showsArr = new Array()

            $('.epCheck').each(function() {
          
                if (this.checked == true) {
                    var epParts = $(this).attr('id').split('/')
                    if (!(epParts[0] in showsArr)) {
                        showsArr[epParts[0]] = new Array();
                    }
                    showsArr[epParts[0]].push(epParts[1])
                }

            });  

            var count = 0
            for (show in showsArr)
            {
                count++
            }

            if (count == 0)
            {
                $('#dialog').dialog('close')
                return false
            }
      
            showProgressBox('Updating status, please wait...', count) 

            for (show in showsArr)
            {
                url = sbRoot+'/home/setStatus?show='+show+'&eps='+showsArr[show].join('|')+'&status=3'
                $.ajax(url, {complete: function(){ progressBarUpdate() }})
            }

        }, "Cancel": function(){ $(this).dialog('close') }}});
    });

    $('.showCheck').click(function(){
    
        var showCheck = this;
        var showId = $(showCheck).attr('id');

        $('.epCheck:visible').each(function(){
            var epParts = $(this).attr('id').split('/')

            if (epParts[0] == showId) {
                this.checked = showCheck.checked 
            } 
        });
    });

    // selects all visible episode checkboxes.
    $('#globalCheck').click(function(){
        $('.epCheck:visible').each(function(){
                this.checked = true
        });
        $('.showCheck:visible').each(function(){
                this.checked = true
        })
    });

    // clears all visible episode checkboxes and the season selectors
    $('#clearAll').click(function(){
        $('.epCheck:visible').each(function(){
                this.checked = false
        });
        $('.showCheck:visible').each(function(){
                this.checked = false
        });
    });

});
