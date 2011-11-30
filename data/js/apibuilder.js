// Chained Selects

// Copyright Xin Yang 2004
// Web Site: www.yxScripts.com
// EMail: m_yangxin@hotmail.com
// Last Updated: Jan. 31, 2009

// This script is free as long as the copyright notice remains intact.

var _disable_empty_list=false;
var _hide_empty_list=false;

function goListGroup(apikey, L7, L6, L5, L4, L3, L2, L1){
    var GlobalOptions = "";
    $('.global').each(function(){
        var checked = $(this).prop('checked');
        if(checked) {
            GlobalOptions = GlobalOptions + "&" + $(this).attr('id') + "=1";
        }
    });
        
    var html = "/api/"+ apikey + "/" + L1 + L2 + L3 + L4 + L5 + L6 + L7 + GlobalOptions + "<br/><pre>";
    html += $.ajax({
      url: "/api/" + apikey + "/" + L1 + L2 + L3 + L4 + L5 + L6 + L7 + GlobalOptions,
      async: false,
      dataType: "html",
    }).responseText;

    html += '</pre>';
    $('#apiResponse').html(html);
}

// ------
if (typeof(disable_empty_list)=="undefined") { disable_empty_list=_disable_empty_list; }
if (typeof(hide_empty_list)=="undefined") { hide_empty_list=_hide_empty_list; }

var cs_goodContent=true, cs_M="M", cs_L="L", cs_G="G", cs_EG="EG";
var cs_names=new Array();
var cs_supportDOM=document.createElement;
var cs_nav=navigator.userAgent.toLowerCase();
var cs_isIE7=(cs_nav.indexOf("msie 7")!=-1 || cs_nav.indexOf("msie 8")!=-1);
var cs_isOpera=(cs_nav.indexOf("opera")!=-1);
var cs_isMac=(cs_nav.indexOf("mac")!=-1);

function cs_findOBJ(obj,n) {
  for (var i=0; i<obj.length; i++) {
    if (obj[i].name==n) { return obj[i]; }
  }
  return null;
}
function cs_findContent(n) { return cs_findOBJ(cs_content,n); }
function cs_findSubContent(n) { return cs_findOBJ(cs_subContent,n); }

function cs_findM(m,n) {
  if (m.name==n) { return m; }

  var sm=null;
  for (var i=0; i<m.items.length; i++) {
    if (m.items[i].type==cs_M) {
      sm=cs_findM(m.items[i],n);
      if (sm!=null) { break; }
    }
  }
  return sm;
}

function cs_subContentOBJ(n,list) {
  this.name=n;
  this.list=list;

  this.ifm=document.createElement("IFRAME");
  with (this.ifm.style) {
    position="absolute"; left="-200px"; top="-200px"; visibility="hidden"; width="100px"; height="100px";
  }
  document.body.appendChild(this.ifm);
  this.ifm.src=n;
}; cs_subContent=new Array();

function cs_contentOBJ(n,obj){
  this.name=n;
  this.menu=obj;
  this.lists=new Array();
  this.cookie="";
  this.callback=null;
  this.count=1;
}; cs_content=new Array();

function cs_topmenuOBJ(tm) {
  this.name=tm;
  this.type=cs_M;
  this.items=new Array();
  this.df=",";
  this.oidx=0;

  this.addM=cs_addM; this.addL=cs_addL; this.addG=cs_addG, this.endG=cs_endG;
}
function cs_submenuOBJ(dis,link,sub,label,css) {
  this.name=sub;
  this.type=cs_M;
  this.dis=dis;
  this.link=link;
  this.label=label;
  this.css=css;
  this.df=",";
  this.oidx=0;

  this.addM=cs_addM; this.addL=cs_addL; this.addG=cs_addG, this.endG=cs_endG;

  if (typeof(cs_names[sub])=="undefined") {
      this.items=new Array();
      cs_names[sub] = this;
  }
  else
  {
      this.items = cs_names[sub].items;
  }
}
function cs_linkOBJ(dis,link,label,css) {
  this.type=cs_L;
  this.dis=dis;
  this.link=link;
  this.label=label;
  this.css=css;
}
function cs_groupOBJ(label,css) {
  this.type=cs_G;
  this.dis="";
  this.link="";
  this.label=label;
  this.css=css;
}
function cs_groupOBJ2() {
  this.type=cs_EG;
  this.dis="";
  this.link="";
  this.label="";
}

function cs_addM(dis,link,sub,label,css) {
  var x=new cs_submenuOBJ(dis,link,sub,label,css);
  this.items[this.items.length]=x;
}
function cs_addL(dis,link,label,css) { this.items[this.items.length]=new cs_linkOBJ(dis,link,label,css); }
function cs_addG(label,css) { this.items[this.items.length]=new cs_groupOBJ(label,css); }
function cs_endG() { this.items[this.items.length]=new cs_groupOBJ2(); }

function cs_showMsg(msg) { window.status=msg; }
function cs_badContent(n) { cs_goodContent=false; cs_showMsg("["+n+"] Not Found."); }

function _setCookie(name, value) {
  document.cookie=name+"="+value;
}
function cs_setCookie(name, value) {
  setTimeout("_setCookie('"+name+"','"+value+"')",0);
}

function cs_getCookie(name) {
  var cookieRE=new RegExp(name+"=([^;]+)");
  if (document.cookie.search(cookieRE)!=-1) {
    return RegExp.$1;
  }
  else {
    return "";
  }
}

function cs_optionOBJ(type,text,value,label,css) { this.type=type; this.text=text; this.value=value; this.label=label; this.css=css; }
function cs_getOptions(menu,list) {
  var opt=new Array();
  for (var i=0; i<menu.items.length; i++) {
    opt[i]=new cs_optionOBJ(menu.items[i].type, menu.items[i].dis, menu.items[i].link, menu.items[i].label, menu.items[i].css);
  }
  if (opt.length==0 && menu.name!="") {
    cs_getSubList(menu.name,list);
    opt[0]=new cs_optionOBJ(cs_L, "loading ...", "", "", "");
  }
  return opt;
}
function cs_emptyList(list) {
  if (cs_supportDOM && !cs_isMac && !cs_isIE7) {
    while (list.lastChild) {
      list.removeChild(list.lastChild);
    }
  }
  else {
    for (var i=list.options.length-1; i>=0; i--) {
      list.options[i]=null;
    }
  }
}
function cs_refreshList(list,opt,df,key) {
  var l=list.options.length;
  var optGroup=null, newOpt=null, optCount=0, optPool=list;

  if (cs_isMac) {
    var l=list.options.length;
    var iCount=0;

    for (var i=0; i<opt.length; i++) {
      if (opt[i].type!=cs_G && opt[i].type!=cs_EG) {
        iCount=l+optCount;

        list.options[iCount]=new Option(opt[i].text, opt[i].value, df.indexOf(","+optCount+",")!=-1, df.indexOf(","+optCount+",")!=-1);
        list.options[iCount].oidx=optCount;
        list.options[iCount].idx=i;
        list.options[iCount].key=key;

        if (opt[i].label!="") {
          list.options[iCount].label=opt[i].label;
        }
        if (opt[i].css!="") {
          list.options[iCount].className=opt[i].css;
        }

        optCount++;
      }
    }

    return;
  }

  for (var i=0; i<opt.length; i++) {
    if (opt[i].type==cs_G) {
      optGroup=document.createElement("optgroup");
      optGroup.setAttribute("label", opt[i].label);
      if (opt[i].css!="") {
        optGroup.setAttribute("className", opt[i].css);
      }
      list.appendChild(optGroup);
      optPool=optGroup;
    }
    else if (opt[i].type==cs_EG) {
      optGroup=null;
      optPool=list;
    }
    else {
      newOpt=new Option(opt[i].text,opt[i].value);
      if (cs_supportDOM && !cs_isIE7) {
        optPool.appendChild(newOpt);
      }
      else {
        list.options[l+optCount]=newOpt;
      }

      newOpt.oidx=optCount;
      newOpt.idx=i;
      newOpt.key=key;

      // a workaround for IE, but will screw up with Opera
      if (!cs_isOpera) {
        newOpt.text=opt[i].text;
        newOpt.value=opt[i].value;
      }

      if (df.indexOf(","+optCount+",")!=-1) {
        newOpt.selected=true;
      }
      if (opt[i].label!="") {
        newOpt.label=opt[i].label;
      }
      if (opt[i].css!="") {
        newOpt.className=opt[i].css;
      }

      optCount++;
    }
  }
}

function cs_getList(content,key) {
  var menu=content.menu;

  if (key!="[]") {
    var paths=key.substring(1,key.length-1).split(",");
    for (var i=0; i<paths.length; i++) {
      menu=menu.items[parseInt(paths[i],10)];
    }
  }

  return menu;
}
function cs_getKey(key,idx) {
  return "["+(key=="[]"?"":(key.substring(1,key.length-1)+","))+idx+"]";
}
function cs_getSelected(mode,name,idx,key,df) {
  if (mode) {
    var cookies=cs_getCookie(name+"_"+idx);
    if (cookies!="") {
      var mc=cookies.split("-");
      for (var i=0; i<mc.length; i++) {
        if (mc[i].indexOf(key)!=-1) {
          df=mc[i].substring(key.length);
          break;
        }
      }
    }
  }
  return df;
}

function cs_updateListGroup(content,idx,mode) {
  var menu=null, list=content.lists[idx], options=list.options, has_sublist=false;
  var key="", option=",", cookies="";

  //if (list.selectedIndex<0) {
  //  list.selectedIndex=0;
  //}

  for (var i=0; i<options.length; i++) {
    if (options[i].selected) {
      if (key!=options[i].key) {
        cookies+=key==""?"":((cookies==""?"":"-")+key+option);

        key=options[i].key;
        option=",";
        menu=cs_getList(content,key);
      }

      option+=options[i].oidx+",";

      if (idx+1<content.lists.length) {
        if (menu.items.length > options[i].idx && menu.items[options[i].idx].type==cs_M) {
          if (!has_sublist) {
            has_sublist=true;
            cs_emptyList(content.lists[idx+1]);
          }
          var subkey=cs_getKey(key,options[i].idx), df=cs_getSelected(mode,content.cookie,idx+1,subkey,menu.items[options[i].idx].df);
          cs_refreshList(content.lists[idx+1],cs_getOptions(menu.items[options[i].idx],list),df,subkey);
        }
      }
    }
  }

  if (key!="") {
    cookies+=(cookies==""?"":"-")+key+option;
  }

  if (content.cookie) {
    cs_setCookie(content.cookie+"_"+idx,cookies);
  }

  if (has_sublist && idx+1<content.lists.length) {
    if (disable_empty_list) {
      content.lists[idx+1].disabled=false;
    }
    if (hide_empty_list) {
      content.lists[idx+1].style.display="block";
    }
    cs_updateListGroup(content,idx+1,mode);
  }
  else {
    for (var s=idx+1; s<content.lists.length; s++) {
      cs_emptyList(content.lists[s]);

      if (disable_empty_list) {
        content.lists[s].disabled=true;
      }
      if (hide_empty_list) {
        content.lists[s].style.display="none";
      }

      if (content.cookie) {
        cs_setCookie(content.cookie+"_"+s,"");
      }
    }
  }
}

function cs_initListGroup(content,mode) {
  var key="[]", df=cs_getSelected(mode,content.cookie,0,key,content.menu.df);

  cs_emptyList(content.lists[0]);
  cs_refreshList(content.lists[0],cs_getOptions(content.menu,content.lists[0]),df,key);
  cs_updateListGroup(content,0,mode);
}

function cs_updateList() {
  var content=this.content;
  for (var i=0; i<content.lists.length; i++) {
    if (content.lists[i]==this) {
      cs_updateListGroup(content,i,content.cookie);

      if (content.callback) {
        var opt="";
        for (var j=0; j<this.options.length; j++) {
          if (this.options[j].selected) {
            if (opt!="") {
              opt+=",";
            }
            if (this.options[j].value!="") {
              opt+=this.options[j].value;
            }
            else if (this.options[j].text!="") {
              opt+=this.options[j].text;
            }
            else if (this.options[j].label!="") {
              opt+=this.options[j].label;
            }
          }
        }
        content.callback(this,i+1,content.count,opt);
      }

      if (this.handler) {
        this.handler();
      }

      break;
    }
  }
}

function cs_getSubList(n,list) {
  if (cs_goodContent && cs_supportDOM) {
    var cs_subList=cs_findSubContent(n);
    if (cs_subList==null) {
      cs_subContent[cs_subContent.length]=new cs_subContentOBJ(n,list);
    }
  }
}

function cs_updateSubList(cn,sn) {
  var cc=cs_findContent(cn), sc=cs_findContent(sn);
  if (cc!=null && sc!=null) {
    var cs_sub=cs_findM(cc.menu,sn);
    if (cs_sub!=null) {
      cs_sub.df=sc.menu.df;
      cs_sub.oidx=sc.menu.oidx;
      cs_sub.items=sc.menu.items;
    }
  }

  var cs_subList=cs_findSubContent(sn);
  if (cs_subList!=null) {
    cs_subList.list.onchange();

    cs_subList.ifm.src="";
    document.body.removeChild(cs_subList.ifm);
    cs_subList.ifm=null;
  }
}

// ------
function addListGroup(n,tm) {
  if (cs_goodContent) {
    cs_names[tm]=new cs_topmenuOBJ(tm);

    var c=cs_findContent(n);
    if (c==null) {
      cs_content[cs_content.length]=new cs_contentOBJ(n,cs_names[tm]);
    }
    else {
      delete(c.menu); c.menu=cs_names[tm];
    }
  }
}

function addList(n,dis,link,sub,df,label,css) {
  if (typeof(sub)=="undefined" || sub=="") {
    addOption(n,dis,link||"",df||"",label||"",css||"");
  }
  else if (cs_goodContent) {
    if (typeof(cs_names[n])!="undefined") {
      cs_names[n].addM(dis,link||"",sub+"",label||"",css||"");
      if (typeof(df)!="undefined" && df) {
        cs_names[n].df+=cs_names[n].oidx+",";
      }
      cs_names[n].oidx++;
    }
    else {
      cs_badContent(n);
    }
  }
}

function addOption(n,dis,link,df,label,css) {
  if (cs_goodContent) {
    if (typeof(cs_names[n])!="undefined") {
      cs_names[n].addL(dis,link||"",label||"",css||"");
      if (typeof(df)!="undefined" && df) {
        cs_names[n].df+=cs_names[n].oidx+",";
      }
      cs_names[n].oidx++;
    }
    else {
      cs_badContent(n);
    }
  }
}

function addOptGroup(n,label,css) {
  if (cs_goodContent && cs_supportDOM && !cs_isOpera) {
    if (typeof(cs_names[n])!="undefined") {
      cs_names[n].addG(label,css||"");
    }
    else {
      cs_badContent(n);
    }
  }
}

function endOptGroup(n) {
  if (cs_goodContent && cs_supportDOM && !cs_isOpera) {
    if (typeof(cs_names[n])!="undefined") {
      cs_names[n].endG();
    }
    else {
      cs_badContent(n);
    }
  }
}

function initListGroup(n) {
  var _content=cs_findContent(n), count=0;
  if (_content!=null) {
    var content=new cs_contentOBJ("cs_"+_content.count+"_"+n,_content.menu);
    content.count=_content.count++;
    cs_content[cs_content.length]=content;

    for (var i=1; i<initListGroup.arguments.length; i++) {
      if (typeof(arguments[i])=="object" && arguments[i].tagName && arguments[i].tagName=="SELECT") {
        content.lists[count]=arguments[i];

        arguments[i].handler=arguments[i].onchange;
        arguments[i].onchange=cs_updateList;
        arguments[i].content=content; arguments[i].idx=count++;
      }
      else if (typeof(arguments[i])=="string" && /^[a-zA-Z_]\w*$/.test(arguments[i])) {
        content.cookie=arguments[i];
      }
      else if (typeof(arguments[i])=="function") {
        content.callback=arguments[i];
      }
      else {
        cs_showMsg("Warning: Unexpected argument in initListGroup() for ["+n+"]");
      }
    }

    if (content.lists.length>0) {
      cs_initListGroup(content,content.cookie);
    }
  }
}

function initListGroups(n) {
  var listCount=0;
  for (var i=1; i<initListGroups.arguments.length; i++) {
    // opera takes select array as function
    if ((typeof(arguments[i])=="object" || typeof(arguments[i])=="function") && arguments[i].length && typeof(arguments[i][0])!="undefined" && arguments[i][0].tagName && arguments[i][0].tagName=="SELECT") {
      if (listCount>arguments[i].length || listCount==0) {
        listCount=arguments[i].length;
      }
    }
  }

  var _content=cs_findContent(n), count=0, content=null;
  if (_content!=null) {
    for (var l=0; l<listCount; l++) {
      count=0;
      content=new cs_contentOBJ("cs_"+_content.count+"_"+n,_content.menu);
      content.count=_content.count++;
      cs_content[cs_content.length]=content;

      for (var i=1; i<initListGroups.arguments.length; i++) {
        if ((typeof(arguments[i])=="object" || typeof(arguments[i])=="function") && arguments[i].length && typeof(arguments[i][0])!="undefined" && arguments[i][0].tagName && arguments[i][0].tagName=="SELECT") {
          content.lists[count]=arguments[i][l];

          arguments[i][l].handler=arguments[i][l].onchange;
          arguments[i][l].onchange=cs_updateList;
          arguments[i][l].content=content; arguments[i][l].idx=count++;
        }
        else if (typeof(arguments[i])=="string" && /^[a-zA-Z_]\w*$/.test(arguments[i])) {
          content.cookie=arguments[i]+"_"+l;
        }
        else if (typeof(arguments[i])=="function") {
          content.callback=arguments[i];
        }
        else {
          cs_showMsg("Warning: Unexpected argument in initListGroups() for ["+n+"]");
        }
      }

      if (content.lists.length>0) {
        cs_initListGroup(content,content.cookie);
      }
    }
  }
}

function resetListGroup(n,count) {
  var content=cs_findContent("cs_"+(count||1)+"_"+n);
  if (content!=null && content.lists.length>0) {
    cs_initListGroup(content,"");
  }
}

function selectOptions(n,opts,mode) {
  var content=cs_findContent(n);
  if (content!=null) {
    var optss=opts.split(":"), menu=content.menu, path=true;
    for (var i=0; i<optss.length; i+=2) {
      if (menu.type==cs_M && path) {
        path=false;
        for (var o=0; o<menu.items.length; o++) {
          if (mode==0 && menu.items[o].dis==optss[i] || mode==1 && menu.items[o].link==optss[i] || mode==2 && o==optss[i]) {
            path=true;
            if (optss[i+1]!="-") {
              menu.df=","+o+",";
            }
            menu=menu.items[o];
            break;
          }
        }
      }
    }
  }  
}
// ------
