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

});