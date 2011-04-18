$(document).ready(function(){

    $('.epSearch').click(function(){
      var parent = $(this).parent();
      
      // put the ajax spinner there while we wait
      parent.empty();
      parent.append($("<img/>").attr("src", sbRoot+"/images/loading16.gif"));
      
      $.getJSON($(this).attr('href'), function(data){
	  	  // if they failed then just put the red X
	      if (data.result == 'failure') {
	    	  img_name = 'no16.png';
	      
	      // if the snatch was successful then put the green check and fill in the row appropriately
	      } else {
	    	  img_name = 'yes16.png';
	    	  // color the row
	    	  parent.parent().removeClass('skipped wanted qual good unaired').addClass('good');
	    	  parent.siblings('.status_column').html(data.result);
	      }
	
	      // put the right image into the row
	      parent.empty();
		  parent.append($("<img/>").attr({"src": sbRoot+"/images/"+img_name, "height": "16"}));
      });

      // fon't follow the link
      return false;
    });
      
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

        var status = $('#checkboxControls > input, #'+whichClass).attr('checked')
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
