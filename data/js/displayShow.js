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

$(function(){
    $('.plotInfo').tooltip({
        bodyHandler: function(){
            match = this.id.match(/^plot_info_(\d+)_(\d+)$/);
            return $.ajax({
                async:   false,
                data:    { show: $('#showID').attr('value'), episode: match[2], season: match[1] },
                url:     'plotDetails'
            }).responseText;
        },
        showURL: false
    })
})
