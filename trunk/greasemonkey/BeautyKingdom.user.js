// --------------------------------------------------------------------
// This is a Greasemonkey user script.  To install it, you need
// Greasemonkey 0.3 or later: http://greasemonkey.mozdev.org/
// Then restart Firefox and revisit this script.
// Under Tools, there will be a new menu item to "Install User Script".
// Accept the default configuration and install.
//
// To uninstall, go to Tools/Manage User Scripts,
// select "Beauty Kingdom", and click Uninstall.
// --------------------------------------------------------------------
// <![CDATA[
// ==UserScript==
// @name          Beauty Kingdom
// @description   Remove Baby Kingdom Sticked Threads
// @author        floatingcat@gmail.com
// @version       2009-06-09
// @namespace     http://code.google.com/p/hk-widget/
// @include       http://forum.baby-kingdom.com/*
// ==/UserScript==
( function() {

function XPath(p, context) {
	if (!context) {
		context = document;
	}
	var i, arr = [], xpr = document.evaluate(p, context, null, XPathResult.UNORDERED_NODE_SNAPSHOT_TYPE, null);
	for (i = 0; item = xpr.snapshotItem(i); i++) {
		arr.push(item);
	}
	return arr;
}
// --------------------------------------------------------------------
function main() {
	// find all stickthread rows, and clear their content.
	var tbodies = XPath('//tbody[contains(@id,"stickthread_")]');
	tbodies.forEach(function(tbody){
		tbody.innerHTML = ''; 
	});		
}
main();

} )();

//GM_log('Duration: '+(new Date().getTime()-start_time)+'ms');
// ]]>
