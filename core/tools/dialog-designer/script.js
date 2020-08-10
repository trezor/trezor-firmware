var img_confirm = new Image();
img_confirm.src = "screen-confirm.png";

var img_yesno = new Image();
img_yesno.src = "screen-yes-no.png";

var pixelPerfect = true;

function ppMeasureWidth(ctx, text) {
    if (!pixelPerfect) {
        return ctx.measureText(text).width;
    } else {
        var w = 0;
        for (var i = 0; i < text.length; i++) {
            var c = text.charCodeAt(i);
            if (c >= 32 && c < 127) {
                w += ctx.fontAdvances[c - 32];
            } else {
                w += 12; // sane default for unsupported Unicode chars
            }
        }
        return w;
    }
}

function ppFillText(ctx, text, x, y) {
    if (!pixelPerfect) {
        ctx.fillText(text, x, y);
    } else {
        for (var i = 0; i < text.length; i++) {
            var c = text[i];
            ctx.fillText(c, x, y);
            x += ppMeasureWidth(ctx, c);
        }
    }
}

function setFont(ctx, bold, mono) {
    ctx.fillStyle = 'white';
    var font = bold ? 'bold ' : '';
    font += '20px "Roboto';
    font += mono ? ' Mono"' : '"';
    ctx.font = font;
    if (mono) {
        // advance is always 12px for Roboto Mono
        ctx.fontAdvances = Array(126 - 32 + 1).fill(12);
    } else {
        if (bold) {
            // advances taken from font_roboto_bold_20.c (column 3)
            ctx.fontAdvances = [5, 5, 7, 13, 12, 15, 14, 4, 7, 8, 9, 12, 6, 8, 5, 8, 12, 11, 12, 12, 11, 12, 12, 12, 12, 12, 5, 5, 11, 11, 10, 11, 18, 13, 13, 13, 13, 11, 11, 14, 14, 5, 12, 12, 11, 17, 14, 14, 13, 14, 13, 13, 14, 13, 13, 18, 13, 13, 13, 6, 8, 6, 9, 11, 7, 11, 11, 11, 12, 11, 9, 12, 11, 5, 6, 11, 5, 17, 11, 12, 11, 12, 8, 11, 8, 11, 10, 15, 10, 11, 10, 7, 6, 7, 13];
        } else {
            // advances taken from font_roboto_regular_20.c (column 3)
            ctx.fontAdvances = [5, 5, 6, 13, 11, 15, 13, 4, 7, 7, 9, 12, 4, 7, 4, 8, 11, 11, 11, 11, 12, 12, 11, 12, 11, 11, 4, 4, 10, 10, 10, 10, 18, 13, 13, 13, 13, 12, 12, 13, 15, 6, 12, 13, 11, 18, 15, 13, 13, 13, 13, 12, 13, 12, 13, 18, 13, 12, 12, 5, 8, 6, 8, 11, 6, 10, 11, 11, 11, 11, 8, 11, 10, 4, 5, 10, 5, 17, 10, 12, 11, 12, 7, 10, 8, 10, 10, 15, 10, 9, 10, 7, 6, 8, 13];
        }
    }
}

function text(ctx, x, y, text, bold, mono) {
    setFont(ctx, bold, mono);
    ppFillText(ctx, text, x, y);
}

function textCenter(ctx, x, y, text, bold, mono) {
    setFont(ctx, bold, mono);
    var w = ppMeasureWidth(ctx, text);
    ppFillText(ctx, text, x - w / 2, y);
}

function render() {
    var title_str = document.getElementById("title").value;
    var line_str = [];
    var bold = [];
    var mono = [];
    for (var i = 1; i <= 5; i++) {
        line_str[i] = document.getElementById("line" + i).value;
        bold[i] = document.getElementById("bold_line" + i).checked;
        mono[i] = document.getElementById("mono_line" + i).checked;
    }
    var confirm_str = document.getElementById("confirm").value;

    var canvas = document.getElementById('canvas');
    var ctx = canvas.getContext('2d');

    if (confirm_str) {
        ctx.drawImage(img_confirm, 0, 0);
    } else {
        ctx.drawImage(img_yesno, 0, 0);
    }

    text(ctx, 44, 35, title_str, true);
    for (var i = 1; i <= 5; i++) {
        text(ctx, 14, 48 + 26 * i, line_str[i], bold[i], mono[i]);
    }
    textCenter(ctx, 120, 215, confirm_str, true);
}

window.onload = function() {
    document.getElementById("title").onkeyup = render;
    for (var i = 1; i <= 5; i++) {
        document.getElementById("line" + i).onkeyup = render;
        document.getElementById("bold_line" + i).onclick = render;
        document.getElementById("mono_line" + i).onclick = render;
    }
    document.getElementById("confirm").onkeyup = render;
    render();
}
