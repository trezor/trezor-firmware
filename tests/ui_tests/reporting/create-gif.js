

function createGif() {
    // Finds all the screenshots on the screen, creates a new img
    // element at the top and switches the src attribute every 200ms
    // to create a notion of GIF.
    // Adds some controlling possibilities - buttons, input fields
    // and sliders to enable pausing, stepping back and forth, changing
    // the delay, etc.

    const allImages = document.body.querySelectorAll('img:not(#gif)');

    // When no images there, do nothing
    if (allImages.length === 0) {
        return;
    }

    // Globals that will be changed by individual functions
    let globCurrentIndex = 0;
    let globTimerId = null;

    // Global constants
    const pauseText = 'Pause (Space)';
    const continueText = 'Continue (Space)';
    const prevText = 'Prev (<)';
    const nextText = 'Next (>)';

    const delayText = 'Delay (ms):';
    const sliderText = 'Progress:';

    const defaultDelay = 200;

    const keyboardShortcutPrev = 'ArrowLeft';
    const keyboardShortcutNext = 'ArrowRight';
    const keyboardShortcutPauseContinue = 'Space';

    const pauseColor = '#ffa500'; // Orange
    const continueColor = '#4CAF50'; // Green

    const btnClass = 'gifBtn';

    // Gif itself
    const gif = document.createElement('img');
    gif.id = 'gif';

    // Update the image source and the slider value according to the current index
    // Lazy-loading all the lazy-loaded images
    function updateGifSourceAndSlider() {
        const currentImage = allImages[globCurrentIndex];
        // When the currentImage is not loaded (because of `loading=lazy` attribute), load it
        if (!currentImage.complete) {
            const tempImg = new Image();
            tempImg.src = currentImage.src;
            tempImg.onload = function () {
                currentImage.src = tempImg.src;
            };
        }
        gif.src = currentImage.src;
        slider.value = globCurrentIndex;
    }

    // Switching between running and paused state
    function toggleGif() {
        if (globTimerId) {
            clearInterval(globTimerId);
            globTimerId = null;
            pauseContinueButton.textContent = continueText;
            pauseContinueButton.style.backgroundColor = continueColor;
            delayInput.disabled = false;
            prevButton.disabled = false;
            nextButton.disabled = false;
        } else {
            pauseContinueButton.textContent = pauseText;
            pauseContinueButton.style.backgroundColor = pauseColor;
            delayInput.disabled = true;
            prevButton.disabled = true;
            nextButton.disabled = true;
            globTimerId = runGif();
        }
    }

    // Start the gif, return the timer id
    function runGif() {
        const delay = parseInt(delayInput.value) || defaultDelay;
        return setInterval(() => {
            changeGifFrame(1);
        }, delay);
    }

    // Go to the previous or next frame (when supplied with -1 or 1, respectively)
    function changeGifFrame(delta) {
        globCurrentIndex = (globCurrentIndex + delta + allImages.length) % allImages.length;
        updateGifSourceAndSlider();
    }

    // Pause/continue button
    const pauseContinueButton = document.createElement('button');
    pauseContinueButton.id = 'pauseContinueButton';
    pauseContinueButton.classList.add(btnClass);
    pauseContinueButton.textContent = pauseText;
    pauseContinueButton.style.backgroundColor = pauseColor;
    pauseContinueButton.addEventListener('click', toggleGif);

    // Prev button
    const prevButton = document.createElement('button');
    prevButton.id = 'prevButton';
    prevButton.textContent = prevText;
    prevButton.classList.add(btnClass);
    prevButton.disabled = true; // Disabled until the gif is paused
    prevButton.addEventListener('click', () => changeGifFrame(-1));

    // Next button
    const nextButton = document.createElement('button');
    nextButton.id = 'nextButton';
    nextButton.textContent = nextText;
    nextButton.classList.add(btnClass);
    nextButton.disabled = true; // Disabled until the gif is paused
    nextButton.addEventListener('click', () => changeGifFrame(1));

    // Delay label
    const delayLabel = document.createElement('label');
    delayLabel.id = 'delayLabel';
    delayLabel.textContent = delayText;
    delayLabel.htmlFor = 'delayInput';

    // Delay input
    const delayInput = document.createElement('input');
    delayInput.id = 'delayInput';
    delayInput.type = 'number';
    delayInput.value = defaultDelay;
    delayInput.size = '5';
    delayInput.disabled = true; // Disabled until the gif is paused

    // Slider label
    const sliderLabel = document.createElement('label');
    sliderLabel.id = 'sliderLabel';
    sliderLabel.textContent = sliderText;
    sliderLabel.htmlFor = 'slider';

    // Slider
    const slider = document.createElement('input');
    slider.id = 'slider';
    slider.type = 'range';
    slider.min = '0';
    slider.max = allImages.length - 1;
    slider.value = globCurrentIndex;
    slider.addEventListener('input', () => {
        globCurrentIndex = parseInt(slider.value);
        updateGifSourceAndSlider();
    });

    // Div for buttons
    const buttonContainer = document.createElement('div');
    buttonContainer.id = 'buttonContainer';
    buttonContainer.appendChild(prevButton);
    buttonContainer.appendChild(pauseContinueButton);
    buttonContainer.appendChild(nextButton);

    // Div for input
    const inputContainer = document.createElement('div');
    inputContainer.id = 'inputContainer';
    inputContainer.appendChild(delayLabel);
    inputContainer.appendChild(delayInput);

    // Div for slider
    const sliderContainer = document.createElement('div');
    sliderContainer.id = 'sliderContainer';
    sliderContainer.appendChild(sliderLabel);
    sliderContainer.appendChild(slider);

    // Insert everything above the <hr> or at the top of the page when missing
    const hr = document.querySelector('hr');
    if (hr) {
        hr.parentNode.insertBefore(gif, hr);
        hr.parentNode.insertBefore(buttonContainer, hr);
        hr.parentNode.insertBefore(inputContainer, hr);
        hr.parentNode.insertBefore(sliderContainer, hr);
    } else {
        document.body.insertBefore(gif, document.body.firstChild);
        document.body.insertBefore(buttonContainer, document.body.firstChild);
        document.body.insertBefore(inputContainer, document.body.firstChild);
        document.body.insertBefore(sliderContainer, document.body.firstChild);
    }

    // Add keyboard shortcuts and disable default shortcuts behavior
    document.addEventListener('keydown', (event) => {
        switch (event.code) {
            case keyboardShortcutPauseContinue:
                event.preventDefault();
                toggleGif();
                break;
            case keyboardShortcutPrev:
                if (!prevButton.disabled) {
                    event.preventDefault();
                    changeGifFrame(-1);
                }
                break;
            case keyboardShortcutNext:
                if (!nextButton.disabled) {
                    event.preventDefault();
                    changeGifFrame(1);
                }
                break;
        }
    });

    // Start the gif
    globTimerId = runGif();
}
