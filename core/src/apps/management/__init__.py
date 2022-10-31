from trezor import utils


# TODO: decide where to put it
# TODO: will we even use it, or do something else?
# With the coming translations all the text could be centralized
def text_r(text: str) -> str:
    """Replace newlines by spaces for model R.

    Reason being a lot of text has newlines that
    were specially crafted for model T.
    """
    if utils.MODEL == "R":
        return text.replace("\n", " ")
    else:
        return text
