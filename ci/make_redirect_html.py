import sys

(URL,) = sys.argv[1:]

print(
    rf"""<!DOCTYPE HTML>
<html lang="en-US">
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="refresh" content="0; url={URL}"
    </head>
    <body>
        Redirecting to <a href='{URL}'>{URL}</a>...
    </body>
</html>
"""
)
