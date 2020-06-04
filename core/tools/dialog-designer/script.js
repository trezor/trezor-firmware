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

function measureWidth(ctx, text, bold, mono) {
    setFont(ctx, bold, mono);
    return ctx.measureText(text).width;
}

function text(ctx, x, y, text, bold, mono) {
    setFont(ctx, bold, mono);
    ctx.fillText(text, x, y);
}

function render() {
    var title_str = document.getElementById("title").value;
    var line1_str = document.getElementById("line1").value;
    var line2_str = document.getElementById("line2").value;
    var line3_str = document.getElementById("line3").value;
    var line4_str = document.getElementById("line4").value;
    var line5_str = document.getElementById("line5").value;
    var bold1 = document.getElementById("bold_line1").checked;
    var bold2 = document.getElementById("bold_line2").checked;
    var bold3 = document.getElementById("bold_line3").checked;
    var bold4 = document.getElementById("bold_line4").checked;
    var bold5 = document.getElementById("bold_line5").checked;
    var mono1 = document.getElementById("mono_line1").checked;
    var mono2 = document.getElementById("mono_line2").checked;
    var mono3 = document.getElementById("mono_line3").checked;
    var mono4 = document.getElementById("mono_line4").checked;
    var mono5 = document.getElementById("mono_line5").checked;
    var confirm_str = document.getElementById("confirm").value;

    var canvas = document.getElementById('canvas');
    var ctx = canvas.getContext('2d');

    if (confirm_str) {
        ctx.drawImage(img_confirm, 0, 0);
    } else {
        ctx.drawImage(img_yesno, 0, 0);
    }

    text(ctx, 44, 35, title_str, true);
    text(ctx, 14, 48 + 26 * 1, line1_str, bold1, mono1);
    text(ctx, 14, 48 + 26 * 2, line2_str, bold2, mono2);
    text(ctx, 14, 48 + 26 * 3, line3_str, bold3, mono3);
    text(ctx, 14, 48 + 26 * 4, line4_str, bold4, mono4);
    text(ctx, 14, 48 + 26 * 5, line5_str, bold5, mono5);

    var w = measureWidth(ctx, confirm_str);
    text(ctx, 120 - w / 2, 215, confirm_str, true);
}

window.onload = function() {
    document.getElementById("title").onkeyup = render;
    document.getElementById("line1").onkeyup = render;
    document.getElementById("line2").onkeyup = render;
    document.getElementById("line3").onkeyup = render;
    document.getElementById("line4").onkeyup = render;
    document.getElementById("line5").onkeyup = render;
    document.getElementById("bold_line1").onclick = render;
    document.getElementById("bold_line2").onclick = render;
    document.getElementById("bold_line3").onclick = render;
    document.getElementById("bold_line4").onclick = render;
    document.getElementById("bold_line5").onclick = render;
    document.getElementById("mono_line1").onclick = render;
    document.getElementById("mono_line2").onclick = render;
    document.getElementById("mono_line3").onclick = render;
    document.getElementById("mono_line4").onclick = render;
    document.getElementById("mono_line5").onclick = render;
    document.getElementById("confirm").onkeyup = render;
    render();
}
