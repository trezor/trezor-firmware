// BEGIN https://cdn.jsdelivr.net/npm/pixelmatch@5.3.0
const defaultOptions={threshold:.1,includeAA:!1,alpha:.1,aaColor:[255,255,0],diffColor:[255,0,0],diffColorAlt:null,diffMask:!1};function pixelmatch(t,e,r,n,i,a){if(!isPixelData(t)||!isPixelData(e)||r&&!isPixelData(r))throw new Error("Image data: Uint8Array, Uint8ClampedArray or Buffer expected.");if(t.length!==e.length||r&&r.length!==t.length)throw new Error("Image sizes do not match.");if(t.length!==n*i*4)throw new Error("Image data size does not match width/height.");a=Object.assign({},defaultOptions,a);const l=n*i,o=new Uint32Array(t.buffer,t.byteOffset,l),f=new Uint32Array(e.buffer,e.byteOffset,l);let s=!0;for(let t=0;t<l;t++)if(o[t]!==f[t]){s=!1;break}if(s){if(r&&!a.diffMask)for(let e=0;e<l;e++)drawGrayPixel(t,4*e,a.alpha,r);return 0}const d=35215*a.threshold*a.threshold;let u=0;for(let l=0;l<i;l++)for(let o=0;o<n;o++){const f=4*(l*n+o),s=colorDelta(t,e,f,f);Math.abs(s)>d?a.includeAA||!antialiased(t,o,l,n,i,e)&&!antialiased(e,o,l,n,i,t)?(r&&drawPixel(r,f,...s<0&&a.diffColorAlt||a.diffColor),u++):r&&!a.diffMask&&drawPixel(r,f,...a.aaColor):r&&(a.diffMask||drawGrayPixel(t,f,a.alpha,r))}return u}function isPixelData(t){return ArrayBuffer.isView(t)&&1===t.constructor.BYTES_PER_ELEMENT}function antialiased(t,e,r,n,i,a){const l=Math.max(e-1,0),o=Math.max(r-1,0),f=Math.min(e+1,n-1),s=Math.min(r+1,i-1),d=4*(r*n+e);let u,c,h,b,g=e===l||e===f||r===o||r===s?1:0,x=0,y=0;for(let i=l;i<=f;i++)for(let a=o;a<=s;a++){if(i===e&&a===r)continue;const l=colorDelta(t,t,d,4*(a*n+i),!0);if(0===l){if(g++,g>2)return!1}else l<x?(x=l,u=i,c=a):l>y&&(y=l,h=i,b=a)}return 0!==x&&0!==y&&(hasManySiblings(t,u,c,n,i)&&hasManySiblings(a,u,c,n,i)||hasManySiblings(t,h,b,n,i)&&hasManySiblings(a,h,b,n,i))}function hasManySiblings(t,e,r,n,i){const a=Math.max(e-1,0),l=Math.max(r-1,0),o=Math.min(e+1,n-1),f=Math.min(r+1,i-1),s=4*(r*n+e);let d=e===a||e===o||r===l||r===f?1:0;for(let i=a;i<=o;i++)for(let a=l;a<=f;a++){if(i===e&&a===r)continue;const l=4*(a*n+i);if(t[s]===t[l]&&t[s+1]===t[l+1]&&t[s+2]===t[l+2]&&t[s+3]===t[l+3]&&d++,d>2)return!0}return!1}function colorDelta(t,e,r,n,i){let a=t[r+0],l=t[r+1],o=t[r+2],f=t[r+3],s=e[n+0],d=e[n+1],u=e[n+2],c=e[n+3];if(f===c&&a===s&&l===d&&o===u)return 0;f<255&&(f/=255,a=blend(a,f),l=blend(l,f),o=blend(o,f)),c<255&&(c/=255,s=blend(s,c),d=blend(d,c),u=blend(u,c));const h=rgb2y(a,l,o),b=rgb2y(s,d,u),g=h-b;if(i)return g;const x=rgb2i(a,l,o)-rgb2i(s,d,u),y=rgb2q(a,l,o)-rgb2q(s,d,u),M=.5053*g*g+.299*x*x+.1957*y*y;return h>b?-M:M}function rgb2y(t,e,r){return.29889531*t+.58662247*e+.11448223*r}function rgb2i(t,e,r){return.59597799*t-.2741761*e-.32180189*r}function rgb2q(t,e,r){return.21147017*t-.52261711*e+.31114694*r}function blend(t,e){return 255+(t-255)*e}function drawPixel(t,e,r,n,i){t[e+0]=r,t[e+1]=n,t[e+2]=i,t[e+3]=255}function drawGrayPixel(t,e,r,n){const i=blend(rgb2y(t[e+0],t[e+1],t[e+2]),r*t[e+3]/255);drawPixel(n,e,i,i,i)}
// END https://cdn.jsdelivr.net/npm/pixelmatch@5.3.0

function refreshMarkStates() {
    for (let tr of document.body.querySelectorAll("tr[data-actual-hash]")) {
        let mark = window.localStorage.getItem(itemKeyFromIndexEntry(tr))
        tr.className = mark || ""
    }
}


function itemKeyFromOneTest() {
    if (document.body.dataset.index)
        throw new Error("itemKeyFromOneTest() called on index")
    if (!document.body.dataset.actualHash)
        throw new Error("itemKeyFromOneTest() called on no actualHash")

    return window.location.href + "+" + document.body.dataset.actualHash
}


function itemKeyFromIndexEntry(entry) {
    let a = entry.querySelector("a")
    return a.href + "+" + entry.dataset.actualHash
}


async function markState(state) {
    if (state === 'update') {
        let lastIndex = decodeURIComponent(window.location.href).split("/").reverse()[0].lastIndexOf(".")
        let stem = decodeURIComponent(window.location.href).split("/").reverse()[0].slice(0, lastIndex)
        await fetch('http://localhost:8000/fixtures.json', {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                "test": stem,
                "hash": document.body.dataset.actualHash
            })
        })
        window.localStorage.setItem(itemKeyFromOneTest(), 'ok')
    } else {
        window.localStorage.setItem(itemKeyFromOneTest(), state)
    }

    if (window.nextHref) {
        window.location.assign(window.nextHref)
    } else {
        window.close()
    }
}


function resetState(whichState) {
    function shouldReset(value) {
        if (value === whichState) return true
        if (whichState !== "all") return false
        return (value === "bad" || value === "ok")
    }

    let keysToReset = []

    for (let i = 0; i < window.localStorage.length; ++i) {
        let key = window.localStorage.key(i)
        let value = window.localStorage.getItem(key)
        if (shouldReset(value)) keysToReset.push(key)
    }

    for (let key of keysToReset) {
        window.localStorage.removeItem(key)
    }

    refreshMarkStates()
}


function findNextForHref(doc, href) {
    let foundIt = false;
    for (let tr of doc.body.querySelectorAll("tr")) {
        if (!tr.dataset.actualHash) continue
        let a = tr.querySelector("a")
        if (!a) continue
        if (foundIt) return a.href
        else if (a.href === href) foundIt = true
    }
}


function openLink(ev) {
    if (ev.button !== 0 || ev.ctrlKey || ev.metaKey || ev.shiftKey || ev.altKey) {
        // let everything but unmodified left clicks through
        return true;
    }

    // capture other clicks
    ev.preventDefault()
    let href = ev.target.href
    window.open(href)
}


function onLoadIndex() {
    document.getElementById("file-hint").hidden = true

    for (let a of document.body.querySelectorAll("a[href]")) {
        a.onclick = openLink
        a.onauxclick = openLink
    }

    document.body.classList.add("novisit")

    window.onstorage = refreshMarkStates
    refreshMarkStates()
}


function onLoadTestCase() {
    if (window.opener) {
        window.nextHref = findNextForHref(window.opener.document, window.location.href)
        if (window.nextHref) {
            markbox = document.getElementById("markbox")
            par = document.createElement("p")
            par.append("and proceed to ")
            a = document.createElement("a")
            a.append("next case")
            a.href = window.nextHref
            a.onclick = ev => {
                console.log("on click")
                ev.preventDefault()
                window.location.assign(window.nextHref)
            }

            par.append(a)
            markbox.append(par)
        }
    } else {
        window.nextHref = null
    }
}

function onClick(id, handler) {
    const el = document.getElementById(id);
    if (el) {
        el.addEventListener("click", handler);
    }
}

function onLoad() {
    if (window.location.protocol === "file") return

    for (let elem of document.getElementsByClassName("script-hidden")) {
        elem.classList.remove("script-hidden")
    }

    // Comes from create-gif.js, which is loaded in the final HTML
    // Do it only in case of individual tests (which have "UI comparison" written on page),
    // not on the main `index.html` page nor on `differing_screens.html` or other screen pages.
    if (document.body.textContent.includes("UI comparison")) {
        createGif()
    }

    if (document.body.dataset.index) {
        onLoadIndex()
    } else {
        // TODO: this is triggering some exception in console:
        // Uncaught DOMException: Permission denied to access property "document" on cross-origin object
        onLoadTestCase()
    }

    document.querySelectorAll('a.show-all-hidden').forEach(a => {
        a.addEventListener("click", function(e) { return showAllHidden() });
    });
    document.querySelectorAll('.image-link').forEach(img => {
        img.addEventListener('load', async function() { await imageLoaded(this) });
    });
    onClick('reset-state-all', () => resetState('all'));
    onClick('reset-state-ok', () => resetState('ok'));
    onClick('reset-state-bad', () => resetState('bad'));
    onClick('mark-ok', () => markState('ok'));
    onClick('mark-update', () => markState('update'));
    onClick('mark-bad', () => markState('bad'));
}

var module = {};

function waitForImage(image) {
    return image.complete && image.naturalWidth !== 0
        ? Promise.resolve()
        : new Promise((resolve, reject) => {
            image.onload = resolve;
            image.onerror = reject;
        });
}

async function getImageData(image) {
    await waitForImage(image);

    // Get original image size
    const width = image.naturalWidth;
    const height  = image.naturalHeight;

    // Create 2D canvas
    let canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    let context = canvas.getContext("2d");

    // Draw the image
    context.drawImage(image, 0, 0);

    // Return image raw data
    return context.getImageData(0, 0, width, height);
}


async function imageLoaded(img) {
    let row = img.closest("tr");
    await createRowDiff(row);
}

async function createRowDiff(row) {
    // Find an element with recorded image
    recImg = row.querySelector("td:nth-child(1) > img");
    // Find an element with the current image
    curImg = row.querySelector("td:nth-child(2) > img");
    // Skip if we haven't found two images
    if (recImg == null || curImg == null) {
        return;
    }

    // Get images's raw data
    recData = await getImageData(recImg);
    curData = await getImageData(curImg);

    const width = recImg.naturalWidth;
    const height = recImg.naturalHeight;

    // Create canvas for diff result
    let difImg = document.createElement('canvas')
    difImg.width = width;
    difImg.height = height;
    let difCtx = difImg.getContext("2d")

    // Process differences
    const difData = difCtx.createImageData(width, height);
    options = {threshold: 0.0, includeAA: true, diffColor: [0, 255, 0], diffColorAlt: [255, 0, 0]};
    pixelmatch(recData.data, curData.data, difData.data, width, height, options);
    difCtx.putImageData(difData, 0, 0);

    // Put the result into the 3rd column
    row.querySelector("td:nth-child(3)").replaceChildren(difImg)
}

function showAllHidden() {
    for (let elem of Array.from(document.getElementsByClassName("hidden"))) {
        elem.classList.remove("hidden");
    }
    for (let elem of Array.from(document.getElementsByClassName("showLink"))) {
        elem.remove();
    }
    return false;
}

window.onload = onLoad
