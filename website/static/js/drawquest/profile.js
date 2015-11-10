// Scroll the slideshow
var speed = 0.5;
var requestID;
var slideshow_list = document.querySelector('.slideshow ul');
var img_width = 0;
var left = 0;

var anim_loop = function() {
    requestID = window.requestAnimationFrame(function() {
        left -= speed;
        if (left < -img_width) {
            left = 0;
            slideshow_list.appendChild(slideshow_list.removeChild(slideshow_list.querySelector('li')));
        }
        slideshow_list.style.left = left + "px";
        anim_loop();
    }, slideshow_list);
};

var reset_scroll = function() {
    img_width = parseInt(window.getComputedStyle(slideshow_list.querySelector('li img')).getPropertyValue("width"), 10);
    left = 0;
    speed = img_width/450;
};

var no_slideshow_ele = document.querySelector("body > .fixed_width_wrapper.no_slideshow");
var start_animation = function() {
    if (!no_slideshow_ele) {
        reset_scroll();
        anim_loop();
    }
};

start_animation();

window.addEventListener("orientationchange", function() {
    setTimeout(function() {
        window.cancelAnimationFrame(requestID);
        start_animation();
    }, 1);
});

window.addEventListener("resize", function() {
    window.cancelAnimationFrame(requestID);
    start_animation();
});