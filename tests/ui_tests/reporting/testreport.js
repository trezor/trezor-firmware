

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
}


window.onload = onLoad
