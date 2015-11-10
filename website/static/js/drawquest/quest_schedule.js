jQuery.fn.sortElements = (function(){
    // http://james.padolsey.com/javascript/sorting-elements-with-jquery/
    var sort = [].sort;

    return function(comparator, getSortable) {
        getSortable = getSortable || function(){return this;};
        var placements = this.map(function(){
            var sortElement = getSortable.call(this),
                parentNode = sortElement.parentNode,
                nextSibling = parentNode.insertBefore(
                    document.createTextNode(''),
                    sortElement.nextSibling
                );

            return function() {
                if (parentNode === this) {
                    throw new Error(
                        "You can't sort elements if any one is a descendant of another."
                    );
                }

                parentNode.insertBefore(this, nextSibling);
                parentNode.removeChild(nextSibling);
            };
        });

        return sort.call(this, comparator).each(function(i){
            placements[i].call(getSortable.call(this));
        });
    };
})();

$(function () {
    var scoped = $('#quest_schedule_form').find;
    var inp = $('#add_thread_input');

    var remove_dupes = function () {
        var seen = {};
        var threads = $('.spotlighted_threads .thread_preview');
        $.each(threads, function (_, thread) {
            thread = $(thread);
            var op_id = thread.data('op_id');
            if (seen[op_id]) {
                thread.remove();
            } else {
                seen[op_id] = true;
            }
        });
    };

    var update_save = function () {
        $('.thread_preview').each(function (_, el) {
            if ($(el).data('dirty')) {
                $('#publish').illuminate({
                    intensity: 0.009,
                    outerGlowSize:'20px',
                    blinkSpeed:'700',
                    outerGlowColor: '#00ff30',
                });
                return false;
            }
        });
    };

    var update_actions_links = function () {
        $('.thread_preview').each(function (_, el) {
            el = $(el);
            var actions = el.find('.actions');
            if (el.find('input[type=number]').val()) {
                actions.show();
            } else {
                actions.hide();
            }
        });
    };

    var sort_threads = function () {
        var threads = $('.spotlighted_threads .thread_preview');
        remove_dupes();
        update_actions_links();
        threads.sortElements(function (a, b) {
            var a_sort = parseInt($(a).find('input[name^=sort_order]').val());
            var b_sort = parseInt($(b).find('input[name^=sort_order]').val());
            return a_sort > b_sort ? 1 : -1;
        });
    };

    var bump_ordinals = function (target) {
        var ordinal = parseInt($(target).val(), 10);
        var last = -Infinity;
        $(target).data('dirty', true);
        $('.spotlighted_threads .thread_preview .ordinal input').not(target).each(function (i, el) {
            var el = $(el);
            var val = parseInt(el.val(), 10);;

            el.closest('.thread_preview').data('dirty', true);

            if(val == ordinal) {
                val = ordinal + 1;
            }

            if(val <= last) {
                val = last + 1;
            }

            last = val;
            el.val(val);
        });
        update_save();
    };

    var select_and_sort = function (event) {
        bump_ordinals(event.target);

        setTimeout(function () {
            var el = $(event.target).closest('.thread_preview');
            if (el.closest('.suggested_threads').length) {
                el.prependTo($('.spotlighted_threads'));
            }
            sort_threads();
        }, 20);
    };

    var add_thread_submit = function () {
        var thread = inp.val();
        inp.val('');
        inp.focus();
        canvas.api.render_thread_preview(thread).done(function (resp) {
            var new_thread = $(resp);
            new_thread.data('dirty', true);
            $('.spotlighted_threads').prepend(new_thread);
            remove_dupes();
            update_actions_links();
            new_thread.find('input[type=number]').val('0');
            bump_ordinals({target: new_thread});
            sort_threads();
            update_save();
        }).fail(function (resp) {
            new canvas.AlertDialog("Error adding thread (" + resp.reason + ")");
            inp.focus();
        });
    };

    $('#add_thread_button').click(function (event) {
        event.preventDefault();
        add_thread_submit();
    });

    $('.suggested_threads').pajinate({
        items_per_page: 6,
    });

    $('#add_thread_input').keypress(function (e) {
        if (e.which == 13) {
            add_thread_submit();
            e.preventDefault();
        }
    });

    $('.spotlighted_threads').delegate('input[name^=sort_order]', 'change', function (event) {
        bump_ordinals(event.target);
        sort_threads();
    });
    $('.suggested_threads input[name^=sort_order]').change(select_and_sort);
    $('.spotlighted_threads').delegate('.remove', 'click', function (event) {
        var el = $(event.target);
        el.data('dirty', true);
        el.closest('.thread_preview').find('input[type=number]').val('');
        el.hide();
        update_save();
        event.preventDefault();
    });
    $('.spotlighted_threads').delegate('.quest_of_the_day', 'click', function (event) {
        var el = $(event.target);
        
        if (confirm("Are you sure? This will alert all users and is not undo-able.")) {
            canvas.apiPOST('/quests/set_current_quest', {'scheduled_quest_id': el.closest('.thread_preview').data('scheduled_quest_id')}, function () {
                document.location.reload(true);
            });
        }
        event.preventDefault();
    });
    $('.spotlighted_threads').delegate('.sponsor', 'click', function (event) {
        var el = $(event.target);
        var username = prompt("Username of sponsor?");
        var copy = prompt("Sponsorship copy?", "Submitted by:");
        dq.api('quests/attribute_to_user', {
            scheduled_quest_id: el.closest('.thread_preview').data('scheduled_quest_id'),
            username: username,
            attribution_copy: copy,
        }).done(function () {
            document.location.reload(true);
        });
    });
    $('.spotlighted_threads').delegate('.clear_sponsorship', 'click', function (event) {
        var el = $(event.target);
        dq.api('quests/clear_attribution', {
            scheduled_quest_id: el.closest('.thread_preview').data('scheduled_quest_id'),
        }).done(function () {
            document.location.reload(true);
        });
    });

    update_actions_links();
});
