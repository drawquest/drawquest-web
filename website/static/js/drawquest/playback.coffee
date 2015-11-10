###
Component and Stroke Classes
###

class Component
    constructor: ->
        @init arguments...

    @LINE: 0
    @CURVE: 1

    @_parse_point: (point_string) ->
        match = /^{(.+), ?(.+)}$/g.exec point_string
        return [parseFloat(match[1]), parseFloat(match[2])]

    init: (@stroke, data) ->
        @type = data['type'];
        @from = Component._parse_point data['fromPoint']
        @to = Component._parse_point data['toPoint']
        if @type is Component.CURVE
            @control_point_1 = Component._parse_point data['controlPoint1']
            @control_point_2 = Component._parse_point data['controlPoint2']

    _draw_dot: (ctx) ->
        @to[0] += .001
        @_draw_line ctx

    _draw_line: (ctx) ->
        ctx.lineTo @to[0], @to[1]

    _draw_curve: (ctx) ->
        ctx.bezierCurveTo @control_point_1[0], @control_point_1[1], @control_point_2[0], @control_point_2[1], @to[0], @to[1]

    draw: (ctx) ->
        unless ctx.canvas.style.opacity is @stroke.alpha
            ctx.canvas.style.opacity = @stroke.alpha

        ctx.save()

        if @stroke.brush_type is Stroke.BRUSH_TYPES.ERASER
            ctx.globalCompositeOperation = 'destination-out'
        else
            ctx.globalCompositeOperation = 'source-over'

        ctx.beginPath()
        ctx.moveTo @from[0], @from[1]

        if @to[0] is @from[0] and @to[1] is @from[1]
            @_draw_dot ctx
        else if @type is Component.LINE
            @_draw_line ctx
        else if @type is Component.CURVE
            @_draw_curve ctx

        ctx.lineWidth = @stroke.line_width
        ctx.strokeStyle = @stroke.color
        ctx.lineCap = @stroke.line_cap
        ctx.lineJoin = @stroke.line_join
        ctx.stroke()

        ctx.restore()

class Stroke
    constructor: ->
        @init arguments...

    @BRUSH_TYPES:
        PEN:1
        MARKER:2
        PAINTBRUSH:3
        ERASER:4
        PAINTBUCKET:7

    @_convert_color: (val) ->
        return Math.round val * 255

    @create_stroke: (data) ->
        return new {
            1: PenStroke
            2: MarkerStroke
            3: PaintbrushStroke
            4: EraserStroke
            7: PaintbucketStroke
        }[data['brushType']](data);

    init: (data) ->
        @brush_type = data['brushType']
        rgb = data['strokeColor']
        if (@brush_type is Stroke.BRUSH_TYPES.ERASER)
            @color = 'rgb(255,255,255)'
        else
            @color = "rgb(#{Stroke._convert_color(rgb.r)}, #{Stroke._convert_color(rgb.g)}, #{Stroke._convert_color(rgb.b)})"

        @components = []
        for component in data['components']
            @components.push new Component @, component

    components_touch: (index_1, index_2) ->
        return false unless 0 <= index_1 < @components.length
        return false unless 0 <= index_2 < @components.length
        c1 = @components[index_1]
        c2 = @components[index_2]
        return true if c1.x is c2.x and c1.y is c2.y
        return false

    line_join: 'round'
    line_cap: 'round'
    alpha: 1

class PenStroke extends Stroke
    brush_type: Stroke.BRUSH_TYPES.PEN
    line_width: 2.9

class MarkerStroke extends Stroke
    brush_type: Stroke.BRUSH_TYPES.MARKER
    line_width: 20

class PaintbrushStroke extends Stroke
    brush_type: Stroke.BRUSH_TYPES.PAINTBRUSH
    line_width: 20.18
    alpha: 0.38

class EraserStroke extends Stroke
    brush_type: Stroke.BRUSH_TYPES.ERASER
    line_width: 15

class PaintbucketStroke extends Stroke
    brush_type: Stroke.BRUSH_TYPES.PAINTBUCKET
    line_width: 5000.00
    alpha: 0.5


###
Playback
###

window.requestAFrame = ((callback) ->
    return window.requestAnimationFrame or window.webkitRequestAnimationFrame or window.mozRequestAnimationFrame or
    window.oRequestAnimationFrame or window.msRequestAnimationFrame or (callback) ->
        window.setTimeout(callback, 1000/60);
)()

playback_drawing = (playback_data, callback=->) ->
    start_time = +new Date()
    WIDTH = 1024
    HEIGHT = 768

    strokes = []
    components_per_frame = 0
    max_strokes_per_frame = 0
    is_done_animating = false

    for stroke_data in playback_data['strokes']
        strokes.push Stroke.create_stroke stroke_data

    unless strokes.length
        return

    $('.drawing').addClass "show_original"

    component_count = 0
    for stroke in strokes
        component_count += stroke.components.length

    target_draw_time = Math.sqrt(component_count/0.00005) + 500
    stroke_index = 0
    component_index = 0
    current_stroke = strokes[stroke_index]
    current_component = current_stroke.components[component_index]

    drawing_canvas = document.getElementById 'playback_drawing'
    drawing_ctx = drawing_canvas.getContext '2d'
    stroke_canvas = document.getElementById 'playback_stroke'
    stroke_ctx = stroke_canvas.getContext '2d'
    drawing_canvas.width = WIDTH
    drawing_canvas.height = HEIGHT
    stroke_canvas.width = WIDTH
    stroke_canvas.height = HEIGHT

    set_dynamic_drawing_speed = (estimated_fps=60) ->
        frame_time = 1000/estimated_fps
        component_time = target_draw_time/component_count # time per component
        drawing_speed = Math.round frame_time/component_time # component per frame
        drawing_speed = Math.max 1, drawing_speed
        components_per_frame = drawing_speed
        max_strokes_per_frame = Math.round drawing_speed/8

    set_dynamic_drawing_speed()

    bake_stroke = ->
        return if current_stroke.brush_type is Stroke.BRUSH_TYPES.ERASER
        drawing_ctx.save()
        drawing_ctx.globalAlpha = current_stroke.alpha
        drawing_ctx.drawImage stroke_canvas, 0, 0
        drawing_ctx.restore()

        stroke_ctx.clearRect 0, 0, WIDTH, HEIGHT

    advance_component = ->
        return false if stroke_index >= strokes.length
        if component_index >= strokes[stroke_index].components.length - 1
            bake_stroke()
            component_index = 0
            stroke_index += 1
            return false if stroke_index is strokes.length
            current_stroke = strokes[stroke_index]
        else
            component_index += 1

        current_component = current_stroke.components[component_index]
        return true

    frame_times = []
    check_actual_fps = (time_per_frame) ->
        # Get an idea of the actual FPS and recalculate components per frame
        # Wait a few frames to get an idea
        FRAME_COUNT = 10
        frame_times.push time_per_frame
        unless frame_times.length is FRAME_COUNT
            return

        average_time_per_frame = (frame_times.reduce (a, b) -> a + b)/FRAME_COUNT
        frame_times = []
        fps = 1000/average_time_per_frame
        set_dynamic_drawing_speed fps


    last_frame = null
    animate = ->
        return callback() if is_done_animating

        frame_stroke_count = 0

        for n in [0...components_per_frame]
            if current_component?
                # Make sure we have a component because stroke might be empty o_0
                if current_stroke.brush_type is Stroke.BRUSH_TYPES.ERASER
                    current_component.draw drawing_ctx
                else
                    current_component.draw stroke_ctx

            unless advance_component()
                is_done_animating = true
                break

            unless current_component?.stroke.components_touch component_index, component_index - 1
                frame_stroke_count += 1
                if frame_stroke_count >= max_strokes_per_frame
                    frame_stroke_count = 0
                    break

        window.requestAFrame ->
            current_frame = +new Date()
            if last_frame
                check_actual_fps current_frame - last_frame
            last_frame = current_frame
            animate()

    animate()

playback_data = null
playback_deferred = null

parse_playback_data = (data) ->
    if data?.playback_data?
        data = JSON.parse data.playback_data
        unless data?.strokes?.length
            return null
        return data
    return null

window.begin_loading_playback_data = (comment_id) ->
    return if playback_deferred
    playback_deferred = dq.api("playback/playback_data", { comment_id: comment_id }).done((data) ->
        playback_data = parse_playback_data data
    )

window.begin_drawing_playback = (comment_id, loaded_callback, animated_callback) ->
    loading_done = ->
        loaded_callback playback_data?
        if playback_data
            playback_drawing playback_data, animated_callback

    if !playback_deferred
        # Handle the user clicking play before we've started loading playback data
        window.begin_loading_playback_data comment_id
        playback_deferred.done loading_done
    else if playback_deferred.state() is "resolved"
        loading_done()
    else if playback_deferred.state() is "rejected"
        loaded_callback false
    else
        playback_deferred.done loading_done
