

function refreshMarkStates() {
    for (let tr of document.body.querySelectorAll("tr[data-actual-hash]")) {
        let a = tr.querySelector("a")
        let mark = window.localStorage.getItem(a.href)
        tr.className = mark || ""
    }
}


function markState(state) {
    window.localStorage.setItem(window.location.href, state)
    if (window.nextHref) {
        window.location.assign(window.nextHref)
    } else {
        window.close()
    }
}


function resetState(whichState) {
    function shouldReset(value) {
        if (value == whichState) return true
        if (whichState != "all") return false
        return (value == "bad" || value == "ok")
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
        else if (a.href == href) foundIt = true
    }
}


function openLink(ev) {
    if (ev.button == 2) {
        // let right click through
        return true;
    }

    // capture other clicks
    ev.preventDefault()
    let href = ev.target.href
    let newWindow = window.open(href)
    newWindow
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
    if (window.location.protocol == "file") return

    for (let elem of document.getElementsByClassName("script-hidden")) {
        elem.classList.remove("script-hidden")
    }

    if (document.body.dataset.index) {
        onLoadIndex()
    } else {
        onLoadTestCase()
    }
}


window.onload = onLoad
