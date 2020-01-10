import urllib.error
import urllib.request
import zipfile

RECORDS_WEBSITE = "https://firmware.corp.sldev.cz/ui_tests/"


def fetch_recorded(recorded_hash, recorded_path):
    zip_src = RECORDS_WEBSITE + recorded_hash + ".zip"
    zip_dest = recorded_path / "recorded.zip"

    try:
        urllib.request.urlretrieve(zip_src, zip_dest)
    except urllib.error.HTTPError:
        raise RuntimeError("No such recorded collection was found on '%s'." % zip_src)
    except urllib.error.URLError:
        raise RuntimeError(
            "Server firmware.corp.sldev.cz could not be found. Are you on VPN?"
        )

    with zipfile.ZipFile(zip_dest, "r") as z:
        z.extractall(recorded_path)

    zip_dest.unlink()
