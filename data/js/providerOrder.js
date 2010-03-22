$(document).ready(function(){

  $('#provider_order_list').click(function(){
  
    var arr = this;
    var resultArr = new Array();
  
    for (i = 0; i < this.length; i++)
      resultArr.push(this[i].value);

    $("#provider_order").val(resultArr.join(" "))

  });
  
});