$(document).ready(function(){

  $('#submitMassEdit').click(function(){
    var editArr = new Array()
  
    $('.editCheck').each(function() {
      if (this.checked == true) {
        editArr.push($(this).attr('id').split('-')[1])
      }
    });

    if (editArr.length == 0)
        return

    url = 'massEdit?toEdit='+editArr.join('|')
    window.location.href = url
  });


  $('#submitMassUpdate').click(function(){
  
    var updateArr = new Array()
    var refreshArr = new Array()
    var renameArr = new Array()
    var metadataArr = new Array()

    $('.updateCheck').each(function() {
      if (this.checked == true) {
        updateArr.push($(this).attr('id').split('-')[1])
      }
    });

    $('.refreshCheck').each(function() {
      if (this.checked == true) {
        refreshArr.push($(this).attr('id').split('-')[1])
      }
    });  

    $('.renameCheck').each(function() {
      if (this.checked == true) {
        renameArr.push($(this).attr('id').split('-')[1])
      }
    });
/*
    $('.metadataCheck').each(function() {
      if (this.checked == true) {
        metadataArr.push($(this).attr('id').split('-')[1])
      }
    });
*/
    if (updateArr.length+refreshArr.length+renameArr.length+metadataArr.length == 0)
      return false

    url = 'massUpdate?toUpdate='+updateArr.join('|')+'&toRefresh='+refreshArr.join('|')+'&toRename='+renameArr.join('|')+'&toMetadata='+metadataArr.join('|')
    
    window.location.href = url

  });

  $('.bulkCheck').click(function(){
    
    var bulkCheck = this;
    var whichBulkCheck = $(bulkCheck).attr('id');

    $('.'+whichBulkCheck).each(function(){
      this.checked = !this.checked 
    });
  });
  
});
