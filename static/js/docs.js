
$(function() {
    $('.helpbox').on('click', function() {
        if ($(this).children('.dropDownIcon').hasClass("downDropDownIcon")) {
            $(this).children('.dropDownIcon').stop().css({transform: "rotate(-90deg)"})
            .removeClass("downDropDownIcon");
            $(this).children('p').stop().slideUp(500);

        }
        else {
            $(this).children('.dropDownIcon').stop().css({transform: "rotate(0deg)"})
            .addClass("downDropDownIcon");
            $(this).children('p').stop().slideDown(500);
        }
    });
});

$(function() {
    $('#toggle').on('click', function () {
        var change = document.getElementById("label");
        if (change.innerHTML == "Expand All") {
            change.innerHTML = "Collapse All";
            helpBoxes = $('body').children('.helpbox');
            for (i = 0; i < helpBoxes.length; i++) {
                $(helpBoxes[i]).children('p').stop().slideDown(500);
                $(helpBoxes[i]).children('.dropDownIcon').css({transform: "rotate(0deg)"})
                .addClass("downDropDownIcon");
            }
        }
        else {
            change.innerHTML = "Expand All";
            helpBoxes = $('body').children('.helpbox');
            for (i = 0; i < helpBoxes.length; i++) {
                $(helpBoxes[i]).children('p').stop().slideUp(500);
                $(helpBoxes[i]).children('.dropDownIcon').css({transform: "rotate(-90deg)"})
                .removeClass("downDropDownIcon");
            }
        }
    });
});

$(function(){
    // this will get the full URL at the address bar
    // passes on every "a" tag 
    $("#navbar2 a").each(function() {
            // checks if its the same on the address bar
        if(window.location.href == (this.href)) { 
            $(this).closest("a").addClass("active");
        }
    });
});