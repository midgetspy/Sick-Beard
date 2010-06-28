$(document).ready(function(){

    $.fn.showHideProviders = function() {
        $('.providerDiv').each(function(){
            var providerName = $(this).attr('id');
            var selectedProvider = $('#editAProvider :selected').val();
            
            if (selectedProvider == providerName)
                $(this).show();
            else
                $(this).hide();
            
        });
    } 

    $.fn.addProvider = function (id, name, url, key, isDefault) {

        if (url.match('/$') == null)
            url = url + '/'

        var newData = [isDefault, [name, url, key]];
        newznabProviders[id] = newData;

        $('#editANewznabProvider').addOption(id, name);
        $(this).populateNewznabSection();

        if ($('#provider_order_list > #'+id).length == 0) {
            var toAdd = '<li class="ui-state-default" id="'+id+'"> <input type="checkbox" id="enable_'+id+'" class="enabler" CHECKED> <a href="'+url+'" class="imgLink" target="_new"><img src="'+sbRoot+'/images/providers/newznab.gif" alt="'+name+'" width="16" height="16"></a> '+name+'</li>'

            $('#provider_order_list').append(toAdd);
            $('#provider_order_list').sortable("refresh");
        }
        
        $(this).makeNewznabProviderString();
    
    }

    $.fn.updateProvider = function (id, url, key) {

        newznabProviders[id][1][1] = url;
        newznabProviders[id][1][2] = key;

        $(this).populateNewznabSection();

        $(this).makeNewznabProviderString();
    
    }

    $.fn.deleteProvider = function (id) {
    
        $('#editANewznabProvider').removeOption(id);
        delete newznabProviders[id];
        $(this).populateNewznabSection();

        $('#provider_order_list > #'+id).remove();

        $(this).makeNewznabProviderString();
    
    }

    $.fn.populateNewznabSection = function() {
    
        var selectedProvider = $('#editANewznabProvider :selected').val();
    
        if (selectedProvider == 'addNewznab') {
            var data = ['','',''];
            var isDefault = 0;
            $('#newznab_add_div').show();
            $('#newznab_update_div').hide();
        } else {
            var data = newznabProviders[selectedProvider][1];
            var isDefault = newznabProviders[selectedProvider][0];
            $('#newznab_add_div').hide();
            $('#newznab_update_div').show();
        }
        
        $('#newznab_name').val(data[0]);
        $('#newznab_url').val(data[1]);
        $('#newznab_key').val(data[2]);
        
        if (selectedProvider == 'addNewznab') {
            $('#newznab_name').removeAttr("disabled");
            $('#newznab_url').removeAttr("disabled");
        } else {

            $('#newznab_name').attr("disabled", "disabled");
            
            if (isDefault) {
                $('#newznab_url').attr("disabled", "disabled");
                $('#newznab_delete').attr("disabled", "disabled");
            } else {
                $('#newznab_url').removeAttr("disabled");
                $('#newznab_delete').removeAttr("disabled");
            }
        }
            
    }
    
    $.fn.makeNewznabProviderString = function() {
        
        var provStrings = new Array();
        
        for (var id in newznabProviders) {
            provStrings.push(newznabProviders[id][1].join('|'));
        }
        
        $('#newznab_string').val(provStrings.join('!!!'))
        
        alert('newznab_string: '+$('#newznab_string').val())
        
    }
    
    $.fn.refreshProviderList = function() {
            var idArr = $("#provider_order_list").sortable('toArray');
            var finalArr = new Array();
            $.each(idArr, function(key, val) {
                    var checked = + $('#enable_'+val).attr('checked') ? '1' : '0';
                    finalArr.push(val + ':' + checked);
            });
            alert('provider list: ' +finalArr.join(' '))
            $("#provider_order").val(finalArr.join(' '));
    }

    var newznabProviders = new Array();
    
    $('#newznab_key').change(function(){
        
        var selectedProvider = $('#editANewznabProvider :selected').val();

        var url = $('#newznab_url').val();
        var key = $('#newznab_key').val();
        
        $(this).updateProvider(selectedProvider, url, key);
        
    });
    
    $('#editAProvider').change(function(){
        $(this).showHideProviders();
    });

    $('#editANewznabProvider').change(function(){
        $(this).populateNewznabSection();
    });
    
    $('.enabler').live('click', function(){
        $(this).refreshProviderList();
    }); 
    

    $('#newznab_add').click(function(){
        
        var selectedProvider = $('#editANewznabProvider :selected').val();
        
        var name = $('#newznab_name').val();
        var url = $('#newznab_url').val();
        var key = $('#newznab_key').val();
        
        var params = { name: name }
        
        // send to the form with ajax, get a return value
        $.getJSON(sbRoot + '/config/providers/canAddNewznabProvider', params,
            function(data){
                if (data.error != undefined) {
                    alert(data.error);
                    return;
                }

                $(this).addProvider(data.success, name, url, key, 0);
        });
        
        
    });

    $('.newznab_delete').click(function(){
    
        var selectedProvider = $('#editANewznabProvider :selected').val();

        $(this).deleteProvider(selectedProvider);

    });


    // initialization stuff

    $(this).showHideProviders();

        $("#provider_order_list").sortable({
            placeholder: 'ui-state-highlight',
            update: function (event, ui) {
                $(this).refreshProviderList();
            }
        });
        $("#provider_order_list").disableSelection();

});