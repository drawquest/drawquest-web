window.share = function(share_type, url, title, img_url, caption) {
    if (share_type == "facebook") {
        obj = {
            method          : 'feed',
            link            : url,
            picture         : img_url,
            name            : title,
            caption         : "DrawQuest is a free drawing community exclusively for iPad. Every day, people come together on DrawQuest to draw the Quest of the Day."
        };
        FB.ui(obj);
    } else if (share_type == "twitter") {
        var message = title + " " + url + " via @DrawQuest";
        window.open('http://twitter.com/intent/tweet?text=' + encodeURIComponent(message), "twitter_share", "width=600, height=400");
    } else if (share_type == "tumblr") {
        var message = title + " " + url;
        window.open('http://www.tumblr.com/share/photo?source=' + encodeURIComponent(img_url + "?tumblr") + '&clickthru=' + encodeURIComponent(url) + '&caption=' + encodeURIComponent(message), "tumblr_share", "width=450, height=400");
    }
};
