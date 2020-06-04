var img_confirm = new Image();
img_confirm.src = "screen-confirm.png";

var img_yesno = new Image();
img_yesno.src = "screen-yes-no.png";

function setFont(ctx, bold, mono) {
    ctx.fillStyle = 'white';
    var font = bold ? 'bold ' : '';
    font += '20px "Roboto';
    font += mono ? ' Mono"' : '"';
    ctx.font = font;
}

function text(ctx, x, y, text, bold, mono) {
    setFont(ctx, bold, mono);
    ctx.fillText(text, x, y);
}

function textCenter(ctx, x, y, text, bold, mono) {
    setFont(ctx, bold, mono);
    var w = ctx.measureText(text).width;
    ctx.fillText(text, x - w / 2, y);
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
