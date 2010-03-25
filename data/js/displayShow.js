$(document).ready(function(){

  $('#changeStatus').click(function(){
  
    var epArr = new Array()

    $('.epCheck').each(function() {
      
      if (this.checked == true) {
        epArr.push($(this).attr('id'))
      }
      
    });  

    if (epArr.length == 0)
      return false

    url = 'setStatus?show='+$('#showID').attr('value')+'&eps='+epArr.join('|')+'&status='+$('#statusSelect').attr('value')

    window.location.href = url

  });

  $('.seasonCheck').click(function(){
    
    var seasCheck = this;
    var seasNo = $(seasCheck).attr('id');

    $('.epCheck').each(function(){
      var epParts = $(this).attr('id').split('x')

      if (epParts[0] == seasNo) {
        this.checked = seasCheck.checked 
      } 
    });
  });
  
});
