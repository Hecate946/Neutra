$(function(){
    // this will get the full URL at the address bar
    // passes on every "a" tag 
    $(".dropdown-content a").each(function() {
            // checks if its the same on the address bar
        if (window.location.href == this.href || window.location.href == this.href + "?time_range=short_term") { 
            $(this).closest("a").remove();
        }
    });
});