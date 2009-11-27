$(document).ready(function(){

  $('.plotLink').click(function(){
  
    var hiddenText = "[+]";
    var shownText = "[-]";
  
    var linkID = $(this).attr('id');
  
    var epInfo = linkID.split('_');

    var epDiv = $('#epDiv_'+epInfo[1]+'_'+epInfo[2]);
    
    if ($(this).text() == hiddenText) {

      //epDiv.text('aa')
      epDiv.css('display', 'block')
      $(this).text(shownText);

    } else if ($(this).text() == shownText) {
      
      //epDiv.text('')
      epDiv.css('display', 'none')
      $(this).text(hiddenText);
      
    } else
      alert('This should never happen.');
    
    return false;
  
  });

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