/*
   Component and Stroke Classes
   */
var Component, EraserStroke, MarkerStroke, PaintbrushStroke, PaintbucketStroke, PenStroke, Stroke, parse_playback_data, playback_data, playback_deferred, playback_drawing,
__hasProp = {}.hasOwnProperty,
__extends = function(child, parent) { for (var key in parent) { if (__hasProp.call(parent, key)) child[key] = parent[key]; } function ctor() { this.constructor = child; } ctor.prototype = parent.prototype; child.prototype = new ctor(); child.__super__ = parent.prototype; return child; };

Component = (function() {
    function Component() {
        this.init.apply(this, arguments);
    }

    Component.LINE = 0;

    Component.CURVE = 1;

    Component._parse_point = function(point_string) {
        var match;
        match = /^{(.+), ?(.+)}$/g.exec(point_string);
        return [parseFloat(match[1]), parseFloat(match[2])];
    };

    Component.prototype.init = function(stroke, data) {
        this.stroke = stroke;
        this.type = data['type'];
        this.from = Component._parse_point(data['fromPoint']);
        this.to = Component._parse_point(data['toPoint']);
        if (this.type === Component.CURVE) {
            this.control_point_1 = Component._parse_point(data['controlPoint1']);
            return this.control_point_2 = Component._parse_point(data['controlPoint2']);
        }
    };

    Component.prototype._draw_dot = function(ctx) {
        this.to[0] += .001;
        return this._draw_line(ctx);
    };

    Component.prototype._draw_line = function(ctx) {
        return ctx.lineTo(this.to[0], this.to[1]);
    };

    Component.prototype._draw_curve = function(ctx) {
        return ctx.bezierCurveTo(this.control_point_1[0], this.control_point_1[1], this.control_point_2[0], this.control_point_2[1], this.to[0], this.to[1]);
    };

    Component.prototype.draw = function(ctx) {
        if (ctx.canvas.style.opacity !== this.stroke.alpha) {
            ctx.canvas.style.opacity = this.stroke.alpha;
        }
        ctx.save();
        if (this.stroke.brush_type === Stroke.BRUSH_TYPES.ERASER) {
            ctx.globalCompositeOperation = 'destination-out';
        } else {
            ctx.globalCompositeOperation = 'source-over';
        }
        ctx.beginPath();
        ctx.moveTo(this.from[0], this.from[1]);
        if (this.to[0] === this.from[0] && this.to[1] === this.from[1]) {
            this._draw_dot(ctx);
        } else if (this.type === Component.LINE) {
            this._draw_line(ctx);
        } else if (this.type === Component.CURVE) {
            this._draw_curve(ctx);
        }
        ctx.lineWidth = this.stroke.line_width;
        ctx.strokeStyle = this.stroke.color;
        ctx.lineCap = this.stroke.line_cap;
        ctx.lineJoin = this.stroke.line_join;
        ctx.stroke();
        return ctx.restore();
    };

    return Component;

})();

Stroke = (function() {
    function Stroke() {
        this.init.apply(this, arguments);
    }

    Stroke.BRUSH_TYPES = {
        PEN: 1,
        MARKER: 2,
        PAINTBRUSH: 3,
        ERASER: 4,
        PAINTBUCKET: 7
    };

    Stroke._convert_color = function(val) {
        return Math.round(val * 255);
    };

    Stroke.create_stroke = function(data) {
        return new {
            1: PenStroke,
            2: MarkerStroke,
            3: PaintbrushStroke,
            4: EraserStroke,
            7: PaintbucketStroke
        }[data['brushType']](data);
    };

    Stroke.prototype.init = function(data) {
        var component, rgb, _i, _len, _ref, _results;
        this.brush_type = data['brushType'];
        rgb = data['strokeColor'];
        if (this.brush_type === Stroke.BRUSH_TYPES.ERASER) {
            this.color = 'rgb(255,255,255)';
        } else {
            this.color = "rgb(" + (Stroke._convert_color(rgb.r)) + ", " + (Stroke._convert_color(rgb.g)) + ", " + (Stroke._convert_color(rgb.b)) + ")";
        }
        this.components = [];
        _ref = data['components'];
        _results = [];
        for (_i = 0, _len = _ref.length; _i < _len; _i++) {
            component = _ref[_i];
            _results.push(this.components.push(new Component(this, component)));
        }
        return _results;
    };

    Stroke.prototype.components_touch = function(index_1, index_2) {
        var c1, c2;
        if (!((0 <= index_1 && index_1 < this.components.length))) {
            return false;
        }
        if (!((0 <= index_2 && index_2 < this.components.length))) {
            return false;
        }
        c1 = this.components[index_1];
        c2 = this.components[index_2];
        if (c1.x === c2.x && c1.y === c2.y) {
            return true;
        }
        return false;
    };
    Stroke.prototype.line_join = 'round';
    Stroke.prototype.line_cap = 'round';
    Stroke.prototype.alpha = 1;
    return Stroke;

})();

PenStroke = (function(_super) {
    __extends(PenStroke, _super);
    function PenStroke() {
        return PenStroke.__super__.constructor.apply(this, arguments);
    }
    PenStroke.prototype.brush_type = Stroke.BRUSH_TYPES.PEN;
    PenStroke.prototype.line_width = 2.9;
    return PenStroke;
})(Stroke);

MarkerStroke = (function(_super) {
    __extends(MarkerStroke, _super);
    function MarkerStroke() {
        return MarkerStroke.__super__.constructor.apply(this, arguments);
    }
    MarkerStroke.prototype.brush_type = Stroke.BRUSH_TYPES.MARKER;
    MarkerStroke.prototype.line_width = 20;
    return MarkerStroke;
})(Stroke);

PaintbrushStroke = (function(_super) {
    __extends(PaintbrushStroke, _super);
    function PaintbrushStroke() {
        return PaintbrushStroke.__super__.constructor.apply(this, arguments);
    }
    PaintbrushStroke.prototype.brush_type = Stroke.BRUSH_TYPES.PAINTBRUSH;
    PaintbrushStroke.prototype.line_width = 20.18;
    PaintbrushStroke.prototype.alpha = 0.38;
    return PaintbrushStroke;
})(Stroke);

EraserStroke = (function(_super) {
    __extends(EraserStroke, _super);
    function EraserStroke() {
        return EraserStroke.__super__.constructor.apply(this, arguments);
    }
    EraserStroke.prototype.brush_type = Stroke.BRUSH_TYPES.ERASER;
    EraserStroke.prototype.line_width = 15;
    return EraserStroke;
})(Stroke);

PaintbucketStroke = (function(_super) {
    __extends(PaintbucketStroke, _super);
    function PaintbucketStroke() {
        return PaintbucketStroke.__super__.constructor.apply(this, arguments);
    }
    PaintbucketStroke.prototype.brush_type = Stroke.BRUSH_TYPES.PAINTBUCKET;
    PaintbucketStroke.prototype.line_width = 5000.00;
    PaintbucketStroke.prototype.alpha = 0.5;
    return PaintbucketStroke;
})(Stroke);


/*
   Playback
   */

window.requestAFrame = (function(callback) {
    return window.requestAnimationFrame || window.webkitRequestAnimationFrame || window.mozRequestAnimationFrame || window.oRequestAnimationFrame || window.msRequestAnimationFrame || function(callback) {
        return window.setTimeout(callback, 1000 / 60);
    };
})();

playback_drawing = function(playback_data, callback) {
    var HEIGHT, WIDTH, advance_component, animate, bake_stroke, check_actual_fps, component_count, component_index, components_per_frame, current_component, current_stroke, drawing_canvas, drawing_ctx, frame_times, is_done_animating, last_frame, max_strokes_per_frame, set_dynamic_drawing_speed, start_time, stroke, stroke_canvas, stroke_ctx, stroke_data, stroke_index, strokes, target_draw_time, _i, _j, _len, _len1, _ref;
    if (callback == null) {
        callback = function() {};
    }
    start_time = +new Date();
    WIDTH = 1024;
    HEIGHT = 768;
    strokes = [];
    components_per_frame = 0;
    max_strokes_per_frame = 0;
    is_done_animating = false;
    _ref = playback_data['strokes'];
    for (_i = 0, _len = _ref.length; _i < _len; _i++) {
        stroke_data = _ref[_i];
        strokes.push(Stroke.create_stroke(stroke_data));
    }
    if (!strokes.length) {
        return;
    }
    $('.drawing').addClass("show_original");
    component_count = 0;
    for (_j = 0, _len1 = strokes.length; _j < _len1; _j++) {
        stroke = strokes[_j];
        component_count += stroke.components.length;
    }
    target_draw_time = Math.sqrt(component_count / 0.00005) + 500;
    stroke_index = 0;
    component_index = 0;
    current_stroke = strokes[stroke_index];
    current_component = current_stroke.components[component_index];
    drawing_canvas = document.getElementById('playback_drawing');
    drawing_ctx = drawing_canvas.getContext('2d');
    stroke_canvas = document.getElementById('playback_stroke');
    stroke_ctx = stroke_canvas.getContext('2d');
    drawing_canvas.width = WIDTH;
    drawing_canvas.height = HEIGHT;
    stroke_canvas.width = WIDTH;
    stroke_canvas.height = HEIGHT;
    set_dynamic_drawing_speed = function(estimated_fps) {
        var component_time, drawing_speed, frame_time;
        if (estimated_fps == null) {
            estimated_fps = 60;
        }
        frame_time = 1000 / estimated_fps;
        component_time = target_draw_time / component_count;
        drawing_speed = Math.round(frame_time / component_time);
        drawing_speed = Math.max(1, drawing_speed);
        components_per_frame = drawing_speed;
        return max_strokes_per_frame = Math.round(drawing_speed / 8);
    };
    set_dynamic_drawing_speed();
    bake_stroke = function() {
        if (current_stroke.brush_type === Stroke.BRUSH_TYPES.ERASER) {
            return;
        }
        drawing_ctx.save();
        drawing_ctx.globalAlpha = current_stroke.alpha;
        drawing_ctx.drawImage(stroke_canvas, 0, 0);
        drawing_ctx.restore();
        return stroke_ctx.clearRect(0, 0, WIDTH, HEIGHT);
    };
    advance_component = function() {
        if (stroke_index >= strokes.length) {
            return false;
        }
        if (component_index >= strokes[stroke_index].components.length - 1) {
            bake_stroke();
            component_index = 0;
            stroke_index += 1;
            if (stroke_index === strokes.length) {
                return false;
            }
            current_stroke = strokes[stroke_index];
        } else {
            component_index += 1;
        }
        current_component = current_stroke.components[component_index];
        return true;
    };
    frame_times = [];
    check_actual_fps = function(time_per_frame) {
        var FRAME_COUNT, average_time_per_frame, fps;
        FRAME_COUNT = 10;
        frame_times.push(time_per_frame);
        if (frame_times.length !== FRAME_COUNT) {
            return;
        }
        average_time_per_frame = (frame_times.reduce(function(a, b) {
            return a + b;
        })) / FRAME_COUNT;
        frame_times = [];
        fps = 1000 / average_time_per_frame;
        return set_dynamic_drawing_speed(fps);
    };
    last_frame = null;
    animate = function() {
        var frame_stroke_count, n, _k;
        if (is_done_animating) {
            return callback();
        }
        frame_stroke_count = 0;
        for (n = _k = 0; 0 <= components_per_frame ? _k < components_per_frame : _k > components_per_frame; n = 0 <= components_per_frame ? ++_k : --_k) {
            if (current_component != null) {
                if (current_stroke.brush_type === Stroke.BRUSH_TYPES.ERASER) {
                    current_component.draw(drawing_ctx);
                } else {
                    current_component.draw(stroke_ctx);
                }
            }
            if (!advance_component()) {
                is_done_animating = true;
                break;
            }
            if (!(current_component != null ? current_component.stroke.components_touch(component_index, component_index - 1) : void 0)) {
                frame_stroke_count += 1;
                if (frame_stroke_count >= max_strokes_per_frame) {
                    frame_stroke_count = 0;
                    break;
                }
            }
        }
        return window.requestAFrame(function() {
            var current_frame;
            current_frame = +new Date();
            if (last_frame) {
                check_actual_fps(current_frame - last_frame);
            }
            last_frame = current_frame;
            return animate();
        });
    };
    return animate();
};

playback_data = null;

playback_deferred = null;

parse_playback_data = function(data) {
    var _ref;
    if (!data) {
        return null;
    }
    data = JSON.parse(data);
    if (!(data != null ? (_ref = data.strokes) != null ? _ref.length : void 0 : void 0)) {
        return null;
    }
    return data;
};

window.begin_loading_playback_data = function(json_gz_url) {
    if (playback_deferred) {
        return;
    }

    playback_deferred = $.Deferred();

    var req = new XMLHttpRequest();
    req.open('GET', json_gz_url, true);
    req.responseType = 'arraybuffer';
    req.overrideMimeType('text\/plain; charset=x-user-defined');

    req.onload = function () {
        var gzdata = new Uint8Array(req.response);
        var inflated = pako.inflate(gzdata, {to: 'string'});
        playback_deferred.resolve(playback_data = parse_playback_data(inflated));
    };

    req.send(null);

    return playback_deferred.promise();
};

window.begin_drawing_playback = function(json_gz_url, loaded_callback, animated_callback) {
    var loading_done;
    loading_done = function() {
        loaded_callback(playback_data != null);
        if (playback_data) {
            return playback_drawing(playback_data, animated_callback);
        }
    };
    if (!playback_deferred) {
        window.begin_loading_playback_data(json_gz_url);
        return playback_deferred.done(loading_done);
    } else if (playback_deferred.state() === "resolved") {
        return loading_done();
    } else if (playback_deferred.state() === "rejected") {
        return loaded_callback(false);
    } else {
        return playback_deferred.done(loading_done);
    }
};
