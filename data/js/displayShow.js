$(document).ready(function(){

    $('#sbRoot').ajaxEpSearch({'colorRow': true});

    $('#seasonJump').change(function() {
        var id = $(this).val();
        if (id && id != 'jump') {
            $('html,body').animate({scrollTop: $(id).offset().top},'slow');
            location.hash = id;
        }
        $(this).val('jump');
    });

    $("#prevShow").click(function(){
        $('#pickShow option:selected').prev('option').attr('selected', 'selected');
        $("#pickShow").change();
    });

    $("#nextShow").click(function(){
        $('#pickShow option:selected').next('option').attr('selected', 'selected');
        $("#pickShow").change();
    });

    $('#changeStatus').click(function(){
        var sbRoot = $('#sbRoot').val()
        var epArr = new Array()

        $('.epCheck').each(function() {
      
            if (this.checked == true) {
                epArr.push($(this).attr('id'))
            }

        });  

        if (epArr.length == 0)
            return false

        url = sbRoot+'/home/setStatus?show='+$('#showID').attr('value')+'&eps='+epArr.join('|')+'&status='+$('#statusSelect').attr('value')
        window.location.href = url

    });

    $('.seasonCheck').click(function(){
        var seasCheck = this;
        var seasNo = $(seasCheck).attr('id');

        $('.epCheck:visible').each(function(){
            var epParts = $(this).attr('id').split('x')

            if (epParts[0] == seasNo) {
                this.checked = seasCheck.checked
            }
        });
    });

    var lastCheck = null;
    $('.epCheck').click(function(event) {

      if(!lastCheck || !event.shiftKey) {
        lastCheck = this;
        return;
      }

      var check = this;
      var found = 0;

      $('.epCheck').each(function() {
        switch (found) {
          case 2: return false;
          case 1: this.checked = lastCheck.checked;
        }

        if (this == check || this == lastCheck)
          found++;
      });

      lastClick = this;
    });

    // selects all visible episode checkboxes.
    $('.seriesCheck').click(function(){
        $('.epCheck:visible').each(function(){
                this.checked = true
        });
        $('.seasonCheck:visible').each(function(){
                this.checked = true
        })
    });

    // clears all visible episode checkboxes and the season selectors
    $('.clearAll').click(function(){
        $('.epCheck:visible').each(function(){
                this.checked = false
        });
        $('.seasonCheck:visible').each(function(){
                this.checked = false
        });
    });

    // handle the show selection dropbox
    $('#pickShow').change(function(){
        var sbRoot = $('#sbRoot').val()
        var val = $(this).attr('value')
        if (val == 0)
            return
        url = sbRoot+'/home/displayShow?show='+val
        window.location.href = url
    });

    // show/hide different types of rows when the checkboxes are changed
    $("#checkboxControls input").change(function(e){
        var whichClass = $(this).attr('id')
        $(this).showHideRows(whichClass)
        return
        $('tr.'+whichClass).each(function(i){
            $(this).toggle();
        });
    }); 

    // initially show/hide all the rows according to the checkboxes
    $("#checkboxControls input").each(function(e){
        var status = this.checked;
        $("tr."+$(this).attr('id')).each(function(e){
            if (status) {
                $(this).show();
            } else {
                $(this).hide();
            }
        });
    });
    
    $.fn.showHideRows = function(whichClass){

        var status = $('#checkboxControls > input, #'+whichClass).prop('checked')
        $("tr."+whichClass).each(function(e){
            if (status) {
                $(this).show();
            } else {
                $(this).hide();
            }
        });

        // hide season headers with no episodes under them
        $('tr.seasonheader').each(function(){
            var numRows = 0
            var seasonNo = $(this).attr('id')
            $('tr.'+seasonNo+' :visible').each(function(){
                numRows++
            })
            if (numRows == 0) {
                $(this).hide()
                $('#'+seasonNo+'-cols').hide()
            } else {
                $(this).show()
                $('#'+seasonNo+'-cols').show()
            }

         });
    }

});
