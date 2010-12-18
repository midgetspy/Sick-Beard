$(document).ready(function(){

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
    
    $('.epSearch').click(function(){
      var t = $(this);
      var p = $("<img/>").attr("src", "/images/indicator.gif");
      t.hide();
      t.parent().append(p);
      
      $.ajax({
        url: t.attr('href'), type: "POST", dataType: "json", async: true,
        success: function(data){
          var img = "/images/", nType;
          if(data.status == "e"){img += "error.png"; nType=2;} 
          else if (data.status == "n"){img += "delete.png"; nType=2;}
          else if (data.status == "f"){img += "save.png"; nType=1;}
          
          t.parent().append($("<img/>").attr({"src": img, "height": "16"}).tooltip({position: 'bottom left', delay: 100, effect: 'fade', tip: '#tooltip', onBeforeShow: function(e){$('#tooltip').html(data.message);}}));
          $("#notification-container").notify("create", nType, {text: data.message},{expires: 10000});
          p.remove();
        },
        error: function(data){
          $("#notification-container").notify("create", 2, {text: "Error while attempting to search, please check your logs."}, {expires: 10000});
          p.hide();
          t.show();
        }
      })
      return false;
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
